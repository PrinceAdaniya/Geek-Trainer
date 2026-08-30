"""Sessions and set logging - the core loop. SPECIFICATIONS.MD Sec 8-11.

Acceptance criteria closing here: A2 (resume), A4 (history immune to plan
edits), A5 (bodyweight and time-based work is recordable).
"""

from __future__ import annotations

import pytest

API = "/api/v1"


@pytest.fixture
def gym(user_client):
    vocab = user_client.get(f"{API}/vocabulary").json()
    user_client.put(f"{API}/profile", json={"available_equipment": vocab["equipment"]})
    return user_client


def exercise_id(client, name: str) -> str:
    payload = client.get(
        f"{API}/exercises", params={"q": name, "limit": 10, "include_incompatible": True}
    ).json()
    for row in payload["data"]:
        if row["name"] == name:
            return row["id"]
    raise AssertionError(f"{name} not found")


def make_plan(client, name="Back + Biceps", exercises=("Barbell Row", "Barbell Curl")):
    plan = client.post(
        f"{API}/workouts", json={"name": name, "day_of_week": "monday"}
    ).json()
    for exercise_name in exercises:
        client.post(
            f"{API}/workouts/{plan['id']}/exercises",
            json={"exercise_id": exercise_id(client, exercise_name),
                  "planned_sets": 3, "planned_reps_min": 8, "planned_reps_max": 12},
        )
    return client.get(f"{API}/workouts/{plan['id']}").json()


def start(client, **body):
    response = client.post(f"{API}/sessions", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def log(client, session, se_index=0, **set_body):
    se = session["exercises"][se_index]
    response = client.post(
        f"{API}/sessions/{session['id']}/exercises/{se['id']}/sets", json=set_body
    )
    return response


class TestStartingASession:
    def test_starting_from_a_plan_copies_its_exercises(self, gym):
        plan = make_plan(gym)
        session = start(gym, workout_id=plan["id"])

        assert session["name"] == "Back + Biceps"
        assert session["status"] == "in_progress"
        assert [e["exercise"]["name"] for e in session["exercises"]] == [
            "Barbell Row", "Barbell Curl"
        ]
        assert session["exercises"][0]["planned_sets"] == 3

    def test_an_ad_hoc_session_needs_no_plan(self, gym):
        """Sec 8.3 - a first-class flow, not a fallback."""
        session = start(gym, name="Whatever I feel like")
        assert session["workout_id"] is None
        assert session["exercises"] == []

        response = gym.post(
            f"{API}/sessions/{session['id']}/exercises",
            json={"exercise_id": exercise_id(gym, "Pull-Up")},
        )
        assert response.status_code == 201
        assert [e["exercise"]["name"] for e in response.json()["exercises"]] == ["Pull-Up"]

    def test_only_one_session_can_be_in_progress(self, gym):
        """Sec 8.2."""
        start(gym, name="First")
        response = gym.post(f"{API}/sessions", json={"name": "Second"})
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "session_already_active"

    def test_finishing_frees_you_to_start_another(self, gym):
        first = start(gym, name="First")
        gym.post(f"{API}/sessions/{first['id']}/finish")
        assert gym.post(f"{API}/sessions", json={"name": "Second"}).status_code == 201

    def test_the_client_may_supply_the_id(self, gym):
        """PLAN.md D3 - an offline start syncs without renaming itself."""
        chosen = "01930000-0000-7000-8000-000000000001"
        session = start(gym, name="Offline start", id=chosen)
        assert session["id"] == chosen

    def test_replaying_the_same_start_is_a_conflict_not_a_duplicate(self, gym):
        chosen = "01930000-0000-7000-8000-000000000002"
        start(gym, name="Once", id=chosen)
        gym.post(f"{API}/sessions/{chosen}/finish")
        again = gym.post(f"{API}/sessions", json={"name": "Once", "id": chosen})
        assert again.status_code == 409
        assert again.json()["error"]["code"] == "duplicate_session"


class TestA2Resume:
    def test_a_session_survives_the_app_being_killed(self, gym):
        """A2: log 3 sets, kill the app, reopen - the session and all 3 sets
        are still there."""
        plan = make_plan(gym)
        session = start(gym, workout_id=plan["id"])
        for reps in (10, 9, 8):
            assert log(gym, session, weight=60, reps=reps).status_code == 201

        # "Killing the app" is the client losing all its state. The only thing
        # that survives is the cookie, so the resume path is what is tested.
        resumed = gym.get(f"{API}/sessions/active").json()
        assert resumed is not None
        assert resumed["id"] == session["id"]
        assert resumed["status"] == "in_progress"
        assert [s["reps"] for s in resumed["exercises"][0]["sets"]] == [10, 9, 8]
        assert [s["set_number"] for s in resumed["exercises"][0]["sets"]] == [1, 2, 3]

    def test_no_active_session_is_null_not_an_error(self, gym):
        assert gym.get(f"{API}/sessions/active").json() is None

    def test_a_finished_session_is_no_longer_active(self, gym):
        session = start(gym, name="Done")
        gym.post(f"{API}/sessions/{session['id']}/finish")
        assert gym.get(f"{API}/sessions/active").json() is None


class TestLoggingSets:
    def test_sets_are_numbered_in_order(self, gym):
        plan = make_plan(gym)
        session = start(gym, workout_id=plan["id"])
        numbers = [log(gym, session, weight=60, reps=10).json()["set_number"] for _ in range(3)]
        assert numbers == [1, 2, 3]

    def test_weight_is_stored_in_kg_whatever_the_user_types_in(self, gym):
        gym.put(f"{API}/profile", json={"unit_preference": "lb"})
        plan = make_plan(gym)
        session = start(gym, workout_id=plan["id"])
        row = log(gym, session, weight=135, reps=5).json()
        assert row["weight_kg"] == "61.235"

    def test_effort_fields_round_trip(self, gym):
        plan = make_plan(gym)
        session = start(gym, workout_id=plan["id"])
        row = log(gym, session, weight=60, reps=8, rir=1, rpe=9, failure=False).json()
        assert row["rir"] == 1
        assert row["rpe"] == "9.0"
        assert row["failure"] is False

    def test_rir_zero_does_not_silently_set_failure(self, gym):
        """Sec 10.4 - related, but not synonymous, and neither writes the other."""
        plan = make_plan(gym)
        session = start(gym, workout_id=plan["id"])
        row = log(gym, session, weight=60, reps=6, rir=0).json()
        assert row["rir"] == 0
        assert row["failure"] is False

    def test_a_client_supplied_set_id_upserts_rather_than_duplicating(self, gym):
        """PLAN.md D3 - the whole point: a retried offline write must not
        invent a second set."""
        plan = make_plan(gym)
        session = start(gym, workout_id=plan["id"])
        set_id = "01930000-0000-7000-8000-0000000000aa"

        first = log(gym, session, id=set_id, weight=60, reps=10)
        replay = log(gym, session, id=set_id, weight=60, reps=10)
        assert first.status_code == 201 and replay.status_code == 201

        fetched = gym.get(f"{API}/sessions/{session['id']}").json()
        assert len(fetched["exercises"][0]["sets"]) == 1

    def test_edit_a_set(self, gym):
        plan = make_plan(gym)
        session = start(gym, workout_id=plan["id"])
        row = log(gym, session, weight=60, reps=10).json()
        updated = gym.put(
            f"{API}/sessions/{session['id']}/sets/{row['id']}",
            json={"reps": 11, "failure": True},
        ).json()
        assert updated["reps"] == 11
        assert updated["failure"] is True

    def test_deleting_a_set_renumbers_the_rest(self, gym):
        plan = make_plan(gym)
        session = start(gym, workout_id=plan["id"])
        ids = [log(gym, session, weight=60, reps=r).json()["id"] for r in (10, 9, 8)]
        assert gym.delete(f"{API}/sessions/{session['id']}/sets/{ids[0]}").status_code == 204

        fetched = gym.get(f"{API}/sessions/{session['id']}").json()
        sets = fetched["exercises"][0]["sets"]
        assert [s["set_number"] for s in sets] == [1, 2]
        assert [s["reps"] for s in sets] == [9, 8]

    def test_cannot_log_into_a_finished_session(self, gym):
        plan = make_plan(gym)
        session = start(gym, workout_id=plan["id"])
        gym.post(f"{API}/sessions/{session['id']}/finish")
        assert log(gym, session, weight=60, reps=10).status_code == 409


class TestA5MetricTypes:
    """A5 - a set of pull-ups and a 90-second plank must both be recordable."""

    def _adhoc_with(self, client, exercise_name):
        session = start(client, name="Metric test")
        updated = client.post(
            f"{API}/sessions/{session['id']}/exercises",
            json={"exercise_id": exercise_id(client, exercise_name)},
        ).json()
        return updated

    def test_bodyweight_reps_needs_reps_and_refuses_a_weight(self, gym):
        session = self._adhoc_with(gym, "Push-Up")
        assert log(gym, session, reps=12).status_code == 201
        assert log(gym, session, weight=20, reps=12).status_code == 422
        assert log(gym, session, weight=None, reps=None).status_code == 422

    def test_weighted_bodyweight_accepts_an_added_load(self, gym):
        session = self._adhoc_with(gym, "Pull-Up")
        assert log(gym, session, reps=8).status_code == 201
        assert log(gym, session, weight=10, reps=5).status_code == 201

    def test_assisted_reps_may_carry_a_negative_load(self, gym):
        session = self._adhoc_with(gym, "Pull-Up")
        row = log(gym, session, weight=-20, reps=8)
        assert row.status_code == 201
        assert row.json()["weight_kg"] == "-20.000"

    def test_a_negative_load_is_nonsense_on_a_barbell(self, gym):
        plan = make_plan(gym)
        session = start(gym, workout_id=plan["id"])
        response = log(gym, session, weight=-60, reps=5)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "negative_weight"

    def test_a_plank_is_recorded_as_a_duration(self, gym):
        session = self._adhoc_with(gym, "Plank")
        assert log(gym, session, duration_seconds=90).json()["duration_seconds"] == 90
        assert log(gym, session, reps=10).status_code == 422

    def test_a_run_records_time_and_distance(self, gym):
        session = self._adhoc_with(gym, "Treadmill Run")
        row = log(gym, session, duration_seconds=1800, distance_m=5000)
        assert row.status_code == 201
        assert row.json()["distance_m"] == "5000.00"
        assert log(gym, session, duration_seconds=1800).status_code == 422

    def test_the_error_says_what_is_missing(self, gym):
        session = self._adhoc_with(gym, "Plank")
        body = log(gym, session).json()["error"]
        assert body["code"] == "set_incomplete"
        assert body["details"]["missing"] == ["duration_seconds"]


class TestA7WarmupSets:
    def test_warmups_are_stored_and_shown_in_the_log(self, gym):
        """A7's first half - the exclusion from volume and PRs is Phase 6."""
        plan = make_plan(gym)
        session = start(gym, workout_id=plan["id"])
        log(gym, session, weight=20, reps=10, set_type="warmup")
        log(gym, session, weight=60, reps=10, set_type="working")

        sets = gym.get(f"{API}/sessions/{session['id']}").json()["exercises"][0]["sets"]
        assert [s["set_type"] for s in sets] == ["warmup", "working"]

    def test_every_set_type_is_accepted(self, gym):
        plan = make_plan(gym)
        session = start(gym, workout_id=plan["id"])
        for set_type in gym.get(f"{API}/vocabulary").json()["set_types"]:
            assert log(gym, session, weight=60, reps=5, set_type=set_type).status_code == 201


class TestA4HistoryIsImmutable:
    def test_editing_the_plan_does_not_change_a_completed_session(self, gym):
        """A4, the exact case."""
        plan = make_plan(gym)
        session = start(gym, workout_id=plan["id"])
        log(gym, session, weight=60, reps=10)
        gym.post(f"{API}/sessions/{session['id']}/finish")

        # Now rewrite the plan completely.
        gym.put(f"{API}/workouts/{plan['id']}", json={"name": "Totally Different"})
        for row in plan["exercises"]:
            gym.delete(f"{API}/workouts/{plan['id']}/exercises/{row['id']}")
        gym.post(
            f"{API}/workouts/{plan['id']}/exercises",
            json={"exercise_id": exercise_id(gym, "Deadlift")},
        )

        after = gym.get(f"{API}/sessions/{session['id']}").json()
        assert after["name"] == "Back + Biceps"
        assert [e["exercise"]["name"] for e in after["exercises"]] == [
            "Barbell Row", "Barbell Curl"
        ]
        assert after["exercises"][0]["sets"][0]["reps"] == 10

    def test_deleting_the_plan_does_not_delete_the_session(self, gym):
        plan = make_plan(gym)
        session = start(gym, workout_id=plan["id"])
        log(gym, session, weight=60, reps=10)
        gym.post(f"{API}/sessions/{session['id']}/finish")

        gym.delete(f"{API}/workouts/{plan['id']}")
        after = gym.get(f"{API}/sessions/{session['id']}")
        assert after.status_code == 200
        assert after.json()["exercises"][0]["sets"][0]["reps"] == 10

    def test_the_snapshot_is_taken_at_start_not_at_finish(self, gym):
        plan = make_plan(gym)
        session = start(gym, workout_id=plan["id"])
        gym.put(f"{API}/workouts/{plan['id']}", json={"name": "Renamed Mid-Session"})
        still = gym.get(f"{API}/sessions/{session['id']}").json()
        assert still["name"] == "Back + Biceps"


class TestPreviousPerformance:
    def test_last_session_is_shown_while_logging(self, gym):
        """Sec 11.2."""
        plan = make_plan(gym)
        first = start(gym, workout_id=plan["id"])
        for reps in (10, 9, 8):
            log(gym, first, weight=60, reps=reps)
        gym.post(f"{API}/sessions/{first['id']}/finish")

        second = start(gym, workout_id=plan["id"])
        previous = second["exercises"][0]["last_performance"]
        assert previous is not None
        assert [s["reps"] for s in previous["sets"]] == [10, 9, 8]
        assert previous["date"] == first["date"]

    def test_the_first_ever_session_has_no_previous(self, gym):
        plan = make_plan(gym)
        session = start(gym, workout_id=plan["id"])
        assert session["exercises"][0]["last_performance"] is None

    def test_an_unfinished_session_is_not_offered_as_history(self, gym):
        plan = make_plan(gym)
        first = start(gym, workout_id=plan["id"])
        log(gym, first, weight=60, reps=10)
        gym.post(f"{API}/sessions/{first['id']}/cancel")

        second = start(gym, workout_id=plan["id"])
        assert second["exercises"][0]["last_performance"] is None


class TestSessionManagement:
    def test_finish_records_a_duration(self, gym):
        session = start(gym, name="Quick one")
        finished = gym.post(f"{API}/sessions/{session['id']}/finish").json()
        assert finished["status"] == "completed"
        assert finished["duration_seconds"] is not None
        assert finished["end_time"] is not None

    def test_cancel_keeps_the_sets_but_leaves_history_alone(self, gym):
        plan = make_plan(gym)
        session = start(gym, workout_id=plan["id"])
        log(gym, session, weight=60, reps=10)
        cancelled = gym.post(f"{API}/sessions/{session['id']}/cancel").json()
        assert cancelled["status"] == "cancelled"
        assert cancelled["exercises"][0]["sets"][0]["reps"] == 10
        assert gym.get(f"{API}/sessions").json() == []

    def test_you_cannot_finish_twice(self, gym):
        session = start(gym, name="Once")
        gym.post(f"{API}/sessions/{session['id']}/finish")
        assert gym.post(f"{API}/sessions/{session['id']}/finish").status_code == 409

    def test_exercises_can_be_added_removed_and_skipped_mid_session(self, gym):
        plan = make_plan(gym)
        session = start(gym, workout_id=plan["id"])

        added = gym.post(
            f"{API}/sessions/{session['id']}/exercises",
            json={"exercise_id": exercise_id(gym, "Face Pull")},
        ).json()
        assert len(added["exercises"]) == 3

        skipped = gym.patch(
            f"{API}/sessions/{session['id']}/exercises/{added['exercises'][1]['id']}",
            json={"skipped": True},
        ).json()
        assert skipped["exercises"][1]["skipped"] is True

        removed = gym.delete(
            f"{API}/sessions/{session['id']}/exercises/{added['exercises'][0]['id']}"
        ).json()
        assert len(removed["exercises"]) == 2
        assert [e["order_index"] for e in removed["exercises"]] == [0, 1]

    def test_a_substitution_records_what_it_replaced(self, gym):
        """Sec 20 - history shows what was planned and what was done."""
        plan = make_plan(gym)
        session = start(gym, workout_id=plan["id"])
        original = session["exercises"][0]["exercise_id"]

        updated = gym.post(
            f"{API}/sessions/{session['id']}/exercises",
            json={
                "exercise_id": exercise_id(gym, "One Arm Dumbbell Row"),
                "replaced_from_exercise_id": original,
            },
        ).json()
        gym.delete(f"{API}/sessions/{session['id']}/exercises/{session['exercises'][0]['id']}")

        after = gym.get(f"{API}/sessions/{session['id']}").json()
        swapped = [e for e in after["exercises"] if e["replaced_from_exercise_id"]][0]
        assert swapped["replaced_from_exercise_id"] == original

    def test_history_lists_completed_sessions_with_counts(self, gym):
        plan = make_plan(gym)
        session = start(gym, workout_id=plan["id"])
        log(gym, session, weight=60, reps=10)
        log(gym, session, weight=60, reps=9)
        gym.post(f"{API}/sessions/{session['id']}/finish")

        history = gym.get(f"{API}/sessions").json()
        assert len(history) == 1
        assert history[0]["set_count"] == 2
        assert history[0]["exercise_count"] == 2


class TestSessionIsolation:
    def test_another_users_session_is_a_404(self, client):
        from tests.conftest import register

        register(client)
        vocab = client.get(f"{API}/vocabulary").json()
        client.put(f"{API}/profile", json={"available_equipment": vocab["equipment"]})
        session = start(client, name="Alice's session")
        client.post(
            f"{API}/sessions/{session['id']}/exercises",
            json={"exercise_id": exercise_id(client, "Pull-Up")},
        )

        client.cookies.clear()
        register(client)
        assert client.get(f"{API}/sessions/{session['id']}").status_code == 404
        assert client.post(f"{API}/sessions/{session['id']}/finish").status_code == 404
        assert client.get(f"{API}/sessions/active").json() is None
        assert client.get(f"{API}/sessions").json() == []

    def test_two_users_can_each_have_an_active_session(self, client):
        """The one-active rule is per user, not global."""
        from tests.conftest import register

        register(client)
        start(client, name="Alice")
        client.cookies.clear()
        register(client)
        assert client.post(f"{API}/sessions", json={"name": "Bob"}).status_code == 201
