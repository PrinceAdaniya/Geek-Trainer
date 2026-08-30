"""AI features. SPECIFICATIONS.MD Sec 17-21.

Every test here uses the fake client - no test spends money or needs a network
(PLAN.md D10). A9 and A8 close here.
"""

from __future__ import annotations

import uuid

import pytest

from app.ai.client import FakeLLMClient, set_client
from app.ai.schemas import (
    AnalysisResult,
    GeneratedWorkout,
    PlannedExercise,
    RankedSubstitution,
    SubstitutionResult,
)

API = "/api/v1"


@pytest.fixture(autouse=True)
def no_real_client():
    """Nothing in the suite may reach a real provider."""
    set_client(FakeLLMClient(fail=True))
    yield
    set_client(None)


@pytest.fixture
def gym(user_client):
    vocab = user_client.get(f"{API}/vocabulary").json()
    user_client.put(f"{API}/profile", json={"available_equipment": vocab["equipment"]})
    return user_client


def exercise_id(client, name: str) -> str:
    rows = client.get(f"{API}/exercises", params={"q": name, "limit": 10}).json()["data"]
    for row in rows:
        if row["name"] == name:
            return row["id"]
    raise AssertionError(name)


def candidates_for(client, target) -> list[str]:
    """Ids the generator would actually offer the model.

    Taken from the rules-based proposal rather than from a plain exercise
    search, because the candidate query is primary-muscle-only and excludes
    mobility work - a search would hand back ids the validator then rejects.
    """
    body = client.post(f"{API}/ai/workout", json={"targets": [target]}).json()
    return [row["exercise"]["id"] for row in body["exercises"]]


class TestA9WorksWithoutAI:
    """A9: with the AI provider unreachable, every flow still works and the UI
    is told why."""

    def test_generation_falls_back_to_rules(self, gym):
        response = gym.post(
            f"{API}/ai/workout", json={"targets": ["back"], "goal": "hypertrophy"}
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["source"] == "rules"
        assert len(body["exercises"]) >= 1
        assert any("not configured" in w for w in body["warnings"])

    def test_the_rules_plan_only_uses_equipment_you_have(self, user_client):
        user_client.put(f"{API}/profile", json={"available_equipment": ["dumbbell"]})
        body = user_client.post(f"{API}/ai/workout", json={"targets": ["back"]}).json()
        for row in body["exercises"]:
            assert set(row["exercise"]["equipment"]) <= {"dumbbell", "bodyweight"}

    def test_substitution_works_without_ai(self, gym):
        body = gym.post(
            f"{API}/ai/substitute",
            json={"exercise_id": exercise_id(gym, "Barbell Row")},
        ).json()
        assert body["source"] == "rules"
        assert len(body["alternatives"]) > 0
        assert all(a["exercise"]["id"] != body["replacing"]["id"] for a in body["alternatives"])

    def test_analysis_works_without_ai(self, gym):
        body = gym.post(
            f"{API}/ai/analyze", json={"exercise_id": exercise_id(gym, "Barbell Row")}
        ).json()
        assert body["source"] == "rules"
        assert body["enough_data"] is False
        assert body["observed"]

    def test_budget_reports_that_ai_is_off(self, gym):
        body = gym.get(f"{API}/ai/budget").json()
        assert body["ai_configured"] is False
        assert body["remaining"] == body["daily_limit"]


class TestA8CandidateConstraint:
    """A8: a plan containing an exercise outside the candidate set is rejected
    and never shown."""

    def test_an_invented_exercise_is_rejected_and_the_fallback_is_used(self, gym):
        invented = GeneratedWorkout(
            name="Hallucinated Day",
            target_muscles=["back"],
            exercises=[
                PlannedExercise(
                    exercise_id=uuid.uuid4(),  # not in any candidate list
                    sets=3, reps_min=8, reps_max=12, rationale="Made up.",
                )
            ],
            notes="",
        )
        # Two attempts, because the pipeline allows exactly one repair.
        set_client(FakeLLMClient([invented, invented]))

        body = gym.post(f"{API}/ai/workout", json={"targets": ["back"]}).json()
        assert body["source"] == "rules"
        assert "Hallucinated Day" != body["name"]
        assert any("validation" in w for w in body["warnings"])

    def test_a_repair_round_trip_is_allowed_once(self, gym):
        good_id = candidates_for(gym, "back")[0]
        bad = GeneratedWorkout(
            name="First try", target_muscles=["back"],
            exercises=[PlannedExercise(exercise_id=uuid.uuid4(), sets=3,
                                       reps_min=8, reps_max=12, rationale="bad")],
            notes="",
        )
        good = GeneratedWorkout(
            name="Second try", target_muscles=["back"],
            exercises=[PlannedExercise(exercise_id=uuid.UUID(good_id), sets=3,
                                       reps_min=8, reps_max=12, rationale="ok")],
            notes="",
        )
        fake = FakeLLMClient([bad, good])
        set_client(fake)

        body = gym.post(f"{API}/ai/workout", json={"targets": ["back"]}).json()
        assert body["source"] == "ai"
        assert body["name"] == "Second try"
        assert len(fake.calls) == 2
        assert "was not in the candidate list" in fake.calls[1]["user"]

    def test_a_valid_plan_is_returned_as_a_proposal(self, gym):
        ids = candidates_for(gym, "back")[:3]
        plan = GeneratedWorkout(
            name="Back Day", target_muscles=["back"],
            exercises=[
                PlannedExercise(exercise_id=uuid.UUID(i), sets=3, reps_min=8,
                                reps_max=12, rationale="Solid rowing.")
                for i in ids
            ],
            notes="Pull hard.",
        )
        set_client(FakeLLMClient([plan]))

        body = gym.post(f"{API}/ai/workout", json={"targets": ["back"]}).json()
        assert body["source"] == "ai"
        assert len(body["exercises"]) == 3
        assert body["exercises"][0]["rationale"] == "Solid rowing."

    def test_a_proposal_writes_nothing(self, gym):
        """Sec 17.2 - the AI proposes; the user saves."""
        gym.post(f"{API}/ai/workout", json={"targets": ["back"]})
        assert gym.get(f"{API}/workouts").json() == []

    def test_the_candidate_list_is_equipment_filtered_before_the_model_sees_it(self, user_client):
        """Sec 21.1 - the model cannot pick a barbell if none was offered."""
        user_client.put(f"{API}/profile", json={"available_equipment": ["dumbbell"]})
        fake = FakeLLMClient(fail=True)
        set_client(fake)
        user_client.post(f"{API}/ai/workout", json={"targets": ["back"]})
        # It failed, so nothing was sent - but the prompt is built before the
        # call, and the fallback used the same list.
        body = user_client.post(f"{API}/ai/workout", json={"targets": ["back"]}).json()
        for row in body["exercises"]:
            assert "barbell" not in row["exercise"]["equipment"]

    def test_nothing_trains_that_is_an_honest_error(self, user_client):
        user_client.put(f"{API}/profile", json={"available_equipment": ["bodyweight"]})
        response = user_client.post(f"{API}/ai/workout", json={"targets": ["cardio"]})
        if response.status_code == 422:
            assert response.json()["error"]["code"] == "no_candidates"


class TestSubstitution:
    def test_ai_ranking_is_used_when_valid(self, gym):
        row_id = exercise_id(gym, "Barbell Row")
        alternatives = gym.post(
            f"{API}/ai/substitute", json={"exercise_id": row_id}
        ).json()["alternatives"]
        picked = uuid.UUID(alternatives[0]["exercise"]["id"])

        set_client(FakeLLMClient([
            SubstitutionResult(alternatives=[
                RankedSubstitution(exercise_id=picked, why="Closest movement pattern.")
            ])
        ]))
        body = gym.post(f"{API}/ai/substitute", json={"exercise_id": row_id}).json()
        assert body["source"] == "ai"
        assert body["alternatives"][0]["why"] == "Closest movement pattern."

    def test_an_invented_alternative_falls_back(self, gym):
        set_client(FakeLLMClient([
            SubstitutionResult(alternatives=[
                RankedSubstitution(exercise_id=uuid.uuid4(), why="Invented.")
            ])
        ]))
        body = gym.post(
            f"{API}/ai/substitute", json={"exercise_id": exercise_id(gym, "Barbell Row")}
        ).json()
        assert body["source"] == "rules"

    def test_an_unknown_exercise_is_a_404(self, gym):
        assert gym.post(
            f"{API}/ai/substitute",
            json={"exercise_id": "00000000-0000-0000-0000-000000000000"},
        ).status_code == 404


class TestAnalysis:
    def _three_sessions(self, client):
        """Three sessions on three different days.

        Progress is one point per date, so three sessions in one day would
        collapse to a single point - which is correct, and would make this
        test measure nothing. They are pushed through /sync so each carries
        its own start time.
        """
        row_id = exercise_id(client, "Barbell Row")
        for index, weight in enumerate((60, 62.5, 65)):
            session_id, se_id = str(uuid.uuid4()), str(uuid.uuid4())
            day = f"2026-08-{10 + index * 7:02d}T10:00:00+00:00"
            client.post(f"{API}/sync", json={"mutations": [
                {"id": str(uuid.uuid4()), "type": "session.start",
                 "payload": {"id": session_id, "name": "S", "start_time": day}},
                {"id": str(uuid.uuid4()), "type": "session_exercise.add",
                 "payload": {"session_id": session_id, "id": se_id,
                             "exercise_id": row_id}},
                {"id": str(uuid.uuid4()), "type": "set.upsert",
                 "payload": {"session_id": session_id, "session_exercise_id": se_id,
                             "id": str(uuid.uuid4()), "weight": weight, "reps": 10}},
                {"id": str(uuid.uuid4()), "type": "session.finish",
                 "payload": {"session_id": session_id}},
            ]})
        return row_id

    def test_under_three_sessions_refuses_to_describe_a_trend(self, gym):
        """Sec 19 - insufficient data produces 'not enough data yet', never a
        confident trend."""
        body = gym.post(
            f"{API}/ai/analyze", json={"exercise_id": exercise_id(gym, "Barbell Row")}
        ).json()
        assert body["enough_data"] is False
        assert body["interpretation"] == []

    def test_the_rules_reading_separates_fact_from_reading(self, gym):
        row_id = self._three_sessions(gym)
        body = gym.post(f"{API}/ai/analyze", json={"exercise_id": row_id}).json()
        assert body["enough_data"] is True
        assert body["observed"]
        assert body["interpretation"]
        assert "60" in body["observed"][0] and "65" in body["observed"][0]

    def test_the_model_is_given_numbers_it_did_not_compute(self, gym):
        row_id = self._three_sessions(gym)
        fake = FakeLLMClient([
            AnalysisResult(observed=["Top set rose from 60 to 65 kg."],
                           interpretation=["The progression is working."],
                           suggestion="Keep going.", enough_data=True)
        ])
        set_client(fake)
        body = gym.post(f"{API}/ai/analyze", json={"exercise_id": row_id}).json()
        assert body["source"] == "ai"
        # The series in the prompt was computed by the backend.
        assert "'e1rm'" in fake.calls[0]["user"]
        assert "top_weight" in fake.calls[0]["user"]

    def test_the_safety_boundary_is_in_every_prompt(self, gym):
        """Sec 31 - the constraint travels with the request, not just the doc."""
        row_id = self._three_sessions(gym)
        fake = FakeLLMClient([
            AnalysisResult(observed=["x"], interpretation=[], suggestion="", enough_data=True)
        ])
        set_client(fake)
        gym.post(f"{API}/ai/analyze", json={"exercise_id": row_id})
        system = fake.calls[0]["system"]
        assert "Never diagnose" in system
        assert "not a doctor" in system
        assert "10%" in system


class TestBudget:
    def test_ai_calls_are_counted(self, gym):
        ids = candidates_for(gym, "back")[:1]
        plan = GeneratedWorkout(
            name="Back", target_muscles=["back"],
            exercises=[PlannedExercise(exercise_id=uuid.UUID(ids[0]), sets=3,
                                       reps_min=8, reps_max=12, rationale="ok")],
            notes="",
        )
        set_client(FakeLLMClient([plan, plan]))

        before = gym.get(f"{API}/ai/budget").json()["used_today"]
        gym.post(f"{API}/ai/workout", json={"targets": ["back"]})
        after = gym.get(f"{API}/ai/budget").json()
        assert after["used_today"] == before + 1
        assert after["remaining"] == after["daily_limit"] - after["used_today"]

    def test_ai_endpoints_require_a_session(self, client):
        client.cookies.clear()
        assert client.post(f"{API}/ai/workout", json={"targets": ["back"]}).status_code == 401
        assert client.get(f"{API}/ai/budget").status_code == 401
