"""Derived data, personal records and progress. Sec 13-15.

Acceptance criteria closing here: A6 (a deleted PR set restores the previous
best), A7 (warm-ups excluded from volume, charts and records), A12 (a late
session lands in the right local day and week).
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
    rows = client.get(f"{API}/exercises", params={"q": name, "limit": 10}).json()["data"]
    for row in rows:
        if row["name"] == name:
            return row["id"]
    raise AssertionError(name)


def do_session(client, name, exercise, sets):
    """Log and finish a session. sets = [(weight, reps, set_type), ...]"""
    session = client.post(f"{API}/sessions", json={"name": name}).json()
    se = client.post(
        f"{API}/sessions/{session['id']}/exercises",
        json={"exercise_id": exercise},
    ).json()["exercises"][0]
    ids = []
    for weight, reps, *rest in sets:
        set_type = rest[0] if rest else "working"
        ids.append(
            client.post(
                f"{API}/sessions/{session['id']}/exercises/{se['id']}/sets",
                json={"weight": weight, "reps": reps, "set_type": set_type},
            ).json()["id"]
        )
    client.post(f"{API}/sessions/{session['id']}/finish")
    return session["id"], ids


class TestPersonalRecords:
    def test_records_appear_after_a_session(self, gym):
        row = exercise_id(gym, "Barbell Row")
        do_session(gym, "One", row, [(60, 10), (60, 9)])

        records = {r["record_type"]: r for r in gym.get(f"{API}/records").json()}
        assert records["heaviest_weight"]["value"] == "60.000"
        assert records["best_e1rm"]["value"] == "80.000"  # 60 * (1 + 10/30)
        assert records["highest_session_volume"]["value"] == "1140.000"

    def test_a_better_session_replaces_the_record(self, gym):
        row = exercise_id(gym, "Barbell Row")
        do_session(gym, "One", row, [(60, 10)])
        do_session(gym, "Two", row, [(65, 10)])

        records = {r["record_type"]: r for r in gym.get(f"{API}/records").json()}
        assert records["heaviest_weight"]["value"] == "65.000"

    def test_a6_deleting_the_pr_set_restores_the_previous_best(self, gym):
        """A6, the exact case."""
        row = exercise_id(gym, "Barbell Row")
        do_session(gym, "Solid", row, [(60, 10)])
        session_id, set_ids = do_session(gym, "Typo", row, [(600, 10)])

        records = {r["record_type"]: r for r in gym.get(f"{API}/records").json()}
        assert records["heaviest_weight"]["value"] == "600.000"

        assert gym.delete(
            f"{API}/sessions/{session_id}/sets/{set_ids[0]}"
        ).status_code == 204

        records = {r["record_type"]: r for r in gym.get(f"{API}/records").json()}
        assert records["heaviest_weight"]["value"] == "60.000"
        assert records["best_e1rm"]["value"] == "80.000"

    def test_correcting_a_set_also_revokes_the_record(self, gym):
        row = exercise_id(gym, "Barbell Row")
        do_session(gym, "Solid", row, [(60, 10)])
        session_id, set_ids = do_session(gym, "Typo", row, [(600, 10)])

        gym.put(
            f"{API}/sessions/{session_id}/sets/{set_ids[0]}", json={"weight": 62.5}
        )
        records = {r["record_type"]: r for r in gym.get(f"{API}/records").json()}
        assert records["heaviest_weight"]["value"] == "62.500"

    def test_a7_warmups_never_set_a_record(self, gym):
        """A7 - and this is where a warm-up leaking in would be most visible."""
        row = exercise_id(gym, "Barbell Row")
        do_session(gym, "Warmup heavy", row, [(200, 1, "warmup"), (60, 10, "working")])

        records = {r["record_type"]: r for r in gym.get(f"{API}/records").json()}
        assert records["heaviest_weight"]["value"] == "60.000"

    def test_records_are_per_exercise(self, gym):
        do_session(gym, "Rows", exercise_id(gym, "Barbell Row"), [(60, 10)])
        do_session(gym, "Curls", exercise_id(gym, "Barbell Curl"), [(30, 10)])

        names = {r["exercise_name"] for r in gym.get(f"{API}/records").json()}
        assert names == {"Barbell Row", "Barbell Curl"}

    def test_a_cancelled_session_sets_no_records(self, gym):
        row = exercise_id(gym, "Barbell Row")
        session = gym.post(f"{API}/sessions", json={"name": "Abandoned"}).json()
        se = gym.post(
            f"{API}/sessions/{session['id']}/exercises", json={"exercise_id": row}
        ).json()["exercises"][0]
        gym.post(
            f"{API}/sessions/{session['id']}/exercises/{se['id']}/sets",
            json={"weight": 500, "reps": 10},
        )
        gym.post(f"{API}/sessions/{session['id']}/cancel")
        assert gym.get(f"{API}/records").json() == []

    def test_records_are_private(self, client):
        from tests.conftest import register

        register(client)
        vocab = client.get(f"{API}/vocabulary").json()
        client.put(f"{API}/profile", json={"available_equipment": vocab["equipment"]})
        do_session(client, "Mine", exercise_id(client, "Barbell Row"), [(60, 10)])

        client.cookies.clear()
        register(client)
        assert client.get(f"{API}/records").json() == []


class TestExerciseProgress:
    def test_one_point_per_session(self, gym):
        row = exercise_id(gym, "Barbell Row")
        do_session(gym, "One", row, [(60, 10), (60, 9)])

        progress = gym.get(f"{API}/progress/exercises/{row}").json()
        assert len(progress["points"]) == 1
        point = progress["points"][0]
        assert point["top_weight_kg"] == "60.000"
        assert point["volume_kg"] == "1140.000"
        assert point["sets"] == 2
        assert point["best_e1rm_kg"] == "80.000"

    def test_a7_warmups_are_left_out_of_the_series(self, gym):
        row = exercise_id(gym, "Barbell Row")
        do_session(gym, "Mixed", row, [(20, 10, "warmup"), (60, 10, "working")])

        point = gym.get(f"{API}/progress/exercises/{row}").json()["points"][0]
        assert point["sets"] == 1
        assert point["volume_kg"] == "600.000"

    def test_an_exercise_never_done_has_an_empty_series(self, gym):
        row = exercise_id(gym, "Deadlift")
        progress = gym.get(f"{API}/progress/exercises/{row}").json()
        assert progress["points"] == []
        assert progress["records"] == []

    def test_another_users_exercise_progress_is_a_404(self, gym):
        assert gym.get(
            f"{API}/progress/exercises/00000000-0000-0000-0000-000000000000"
        ).status_code == 404


class TestOverallProgress:
    def test_weekly_buckets_cover_the_whole_window(self, gym):
        progress = gym.get(f"{API}/progress", params={"weeks": 8}).json()
        assert len(progress["weekly"]) == 8
        assert all(point["volume_kg"] == "0" for point in progress["weekly"])

    def test_a_session_lands_in_the_current_week(self, gym):
        do_session(gym, "This week", exercise_id(gym, "Barbell Row"), [(60, 10)])
        progress = gym.get(f"{API}/progress").json()
        assert progress["weekly"][-1]["volume_kg"] == "600.000"
        assert progress["sessions_completed"] == 1
        assert progress["consistency_weeks"] == 1

    def test_muscles_are_counted_by_sets(self, gym):
        do_session(gym, "Back", exercise_id(gym, "Barbell Row"), [(60, 10), (60, 9)])
        do_session(gym, "Arms", exercise_id(gym, "Barbell Curl"), [(30, 10)])

        muscles = {m["muscle"]: m["sets"] for m in gym.get(f"{API}/progress").json()["muscles"]}
        assert muscles == {"lats": 2, "biceps": 1}

    def test_adherence_is_null_rather_than_a_fake_hundred_percent(self, gym):
        """Sec 14 - adherence needs planned sessions as a denominator."""
        assert gym.get(f"{API}/progress").json()["adherence"] is None


class TestA12Timezones:
    def test_a_late_session_lands_in_the_local_day(self, gym):
        """A12: a session logged at 23:30 local belongs to that local day, in
        every view."""
        import uuid

        gym.put(f"{API}/profile", json={"timezone": "Asia/Kolkata"})
        row = exercise_id(gym, "Barbell Row")
        session_id = str(uuid.uuid4())
        se_id = str(uuid.uuid4())

        # 18:00 UTC on the 30th is 23:30 on the 30th in Kolkata.
        gym.post(f"{API}/sync", json={"mutations": [
            {"id": str(uuid.uuid4()), "type": "session.start",
             "payload": {"id": session_id, "name": "Late",
                         "start_time": "2026-08-30T18:00:00+00:00"}},
            {"id": str(uuid.uuid4()), "type": "session_exercise.add",
             "payload": {"session_id": session_id, "id": se_id, "exercise_id": row}},
            {"id": str(uuid.uuid4()), "type": "set.upsert",
             "payload": {"session_id": session_id, "session_exercise_id": se_id,
                         "id": str(uuid.uuid4()), "weight": 60, "reps": 10}},
            {"id": str(uuid.uuid4()), "type": "session.finish",
             "payload": {"session_id": session_id}},
        ]})

        assert gym.get(f"{API}/sessions/{session_id}").json()["date"] == "2026-08-30"
        point = gym.get(f"{API}/progress/exercises/{row}").json()["points"][0]
        assert point["date"] == "2026-08-30"
        assert gym.get(f"{API}/records").json()[0]["achieved_on"] == "2026-08-30"
