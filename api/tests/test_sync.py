"""Offline sync. SPECIFICATIONS.MD Sec 12, PLAN.md D3.

Acceptance criterion A3: a full session logged with the network disabled, then
reconnected, produces exactly that session server-side - no duplicates, after a
forced retry of every mutation.
"""

from __future__ import annotations

import uuid

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


def mid() -> str:
    return str(uuid.uuid4())


def offline_session(client, *, sets=((60, 10), (60, 9), (60, 8))) -> tuple[str, list[dict]]:
    """Build the queue a client would accumulate with no network at all."""
    session_id = str(uuid.uuid4())
    se_id = str(uuid.uuid4())
    row_id = exercise_id(client, "Barbell Row")

    queue = [
        {"id": mid(), "type": "session.start", "at": "2026-08-31T10:00:00+00:00",
         "payload": {"id": session_id, "name": "Offline Pull",
                     "start_time": "2026-08-31T10:00:00+00:00"}},
        {"id": mid(), "type": "session_exercise.add", "at": "2026-08-31T10:00:05+00:00",
         "payload": {"session_id": session_id, "id": se_id, "exercise_id": row_id}},
    ]
    for index, (weight, reps) in enumerate(sets):
        queue.append(
            {"id": mid(), "type": "set.upsert",
             "at": f"2026-08-31T10:0{index + 1}:00+00:00",
             "payload": {"session_id": session_id, "session_exercise_id": se_id,
                         "id": str(uuid.uuid4()), "weight": weight, "reps": reps}}
        )
    queue.append(
        {"id": mid(), "type": "session.finish", "at": "2026-08-31T10:30:00+00:00",
         "payload": {"session_id": session_id}}
    )
    return session_id, queue


class TestA3OfflineReplay:
    def test_a_whole_session_syncs(self, gym):
        session_id, queue = offline_session(gym)
        response = gym.post(f"{API}/sync", json={"mutations": queue})
        assert response.status_code == 200, response.text
        body = response.json()
        assert len(body["applied"]) == len(queue)
        assert body["rejected"] == []

        session = gym.get(f"{API}/sessions/{session_id}").json()
        assert session["status"] == "completed"
        assert [s["reps"] for s in session["exercises"][0]["sets"]] == [10, 9, 8]

    def test_a_forced_replay_of_every_mutation_changes_nothing(self, gym):
        """A3, the exact case: reconnect and force-retry the whole queue."""
        session_id, queue = offline_session(gym)
        gym.post(f"{API}/sync", json={"mutations": queue})

        replay = gym.post(f"{API}/sync", json={"mutations": queue}).json()
        assert replay["applied"] == []
        assert len(replay["duplicates"]) == len(queue)

        session = gym.get(f"{API}/sessions/{session_id}").json()
        assert len(session["exercises"]) == 1
        assert [s["reps"] for s in session["exercises"][0]["sets"]] == [10, 9, 8]
        assert len(gym.get(f"{API}/sessions").json()) == 1

    def test_replaying_only_part_of_the_queue_is_also_safe(self, gym):
        """A partial flush is the normal case on a flaky connection."""
        session_id, queue = offline_session(gym)
        gym.post(f"{API}/sync", json={"mutations": queue[:3]})
        gym.post(f"{API}/sync", json={"mutations": queue})

        session = gym.get(f"{API}/sessions/{session_id}").json()
        assert len(session["exercises"][0]["sets"]) == 3

    def test_mutations_arriving_out_of_order_still_apply(self, gym):
        session_id, queue = offline_session(gym)
        scrambled = list(reversed(queue))
        body = gym.post(f"{API}/sync", json={"mutations": scrambled}).json()
        assert body["rejected"] == []
        session = gym.get(f"{API}/sessions/{session_id}").json()
        assert len(session["exercises"][0]["sets"]) == 3

    def test_the_same_set_id_twice_is_one_set(self, gym):
        """The core of D3 - a retried write must not inflate volume."""
        session_id, queue = offline_session(gym, sets=((60, 10),))
        set_mutation = [m for m in queue if m["type"] == "set.upsert"][0]
        duplicate = {**set_mutation, "id": mid()}  # new mutation id, same set id

        gym.post(f"{API}/sync", json={"mutations": queue + [duplicate]})
        session = gym.get(f"{API}/sessions/{session_id}").json()
        assert len(session["exercises"][0]["sets"]) == 1

    def test_the_offline_start_time_decides_the_date(self, gym):
        """Sec 3.3 - a session logged at 23:50 must not move a day when it
        syncs the next morning."""
        gym.put(f"{API}/profile", json={"timezone": "Asia/Kolkata"})
        session_id = str(uuid.uuid4())
        gym.post(
            f"{API}/sync",
            json={"mutations": [
                {"id": mid(), "type": "session.start", "at": "2026-08-30T18:20:00+00:00",
                 "payload": {"id": session_id, "name": "Late one",
                             "start_time": "2026-08-30T18:20:00+00:00"}}
            ]},
        )
        # 18:20 UTC is 23:50 in Kolkata, so it belongs to the 30th, not the 31st.
        assert gym.get(f"{API}/sessions/{session_id}").json()["date"] == "2026-08-30"


class TestRejection:
    def test_one_bad_mutation_does_not_fail_the_batch(self, gym):
        """Sec 12.2 - a failed sync never discards local data, and the good
        rows must still land."""
        session_id, queue = offline_session(gym)
        poison = {
            "id": mid(), "type": "set.upsert", "at": "2026-08-31T10:05:00+00:00",
            "payload": {"session_id": session_id,
                        "session_exercise_id": str(uuid.uuid4()),
                        "id": str(uuid.uuid4()), "weight": 60, "reps": 10},
        }
        body = gym.post(f"{API}/sync", json={"mutations": queue + [poison]}).json()

        assert len(body["applied"]) == len(queue)
        assert len(body["rejected"]) == 1
        assert body["rejected"][0]["id"] == poison["id"]

        session = gym.get(f"{API}/sessions/{session_id}").json()
        assert len(session["exercises"][0]["sets"]) == 3

    def test_a_rejected_mutation_is_reported_not_dropped(self, gym):
        body = gym.post(
            f"{API}/sync",
            json={"mutations": [{"id": mid(), "type": "nonsense.type", "payload": {}}]},
        ).json()
        assert body["applied"] == []
        assert body["rejected"][0]["code"] == "unknown_type"

    def test_a_set_that_fails_validation_is_reported(self, gym):
        session_id, queue = offline_session(gym, sets=())
        gym.post(f"{API}/sync", json={"mutations": queue[:2]})
        se_id = queue[1]["payload"]["id"]

        body = gym.post(
            f"{API}/sync",
            json={"mutations": [
                {"id": mid(), "type": "set.upsert",
                 "payload": {"session_id": session_id, "session_exercise_id": se_id,
                             "id": str(uuid.uuid4()), "reps": 10}}  # no weight
            ]},
        ).json()
        assert body["rejected"][0]["code"] == "set_incomplete"

    def test_a_rejected_mutation_is_not_retried_forever(self, gym):
        bad = {"id": mid(), "type": "nonsense.type", "payload": {}}
        gym.post(f"{API}/sync", json={"mutations": [bad]})
        again = gym.post(f"{API}/sync", json={"mutations": [bad]}).json()
        assert again["duplicates"] == [bad["id"]]

    def test_a_mutation_without_a_uuid_is_rejected_cleanly(self, gym):
        response = gym.post(
            f"{API}/sync", json={"mutations": [{"id": "not-a-uuid", "type": "set.upsert"}]}
        )
        assert response.status_code == 422


class TestSyncIsolation:
    def test_sync_cannot_touch_another_users_session(self, client):
        from tests.conftest import register

        register(client)
        vocab = client.get(f"{API}/vocabulary").json()
        client.put(f"{API}/profile", json={"available_equipment": vocab["equipment"]})
        session_id, queue = offline_session(client)
        client.post(f"{API}/sync", json={"mutations": queue})

        client.cookies.clear()
        register(client)
        body = client.post(
            f"{API}/sync",
            json={"mutations": [
                {"id": mid(), "type": "session.update",
                 "payload": {"session_id": session_id, "name": "Stolen"}}
            ]},
        ).json()
        assert body["applied"] == []
        assert body["rejected"][0]["code"] == "not_found"

    def test_sync_requires_a_session(self, client):
        client.cookies.clear()
        assert client.post(f"{API}/sync", json={"mutations": []}).status_code == 401

    def test_the_response_carries_the_servers_view_back(self, gym):
        session_id = str(uuid.uuid4())
        body = gym.post(
            f"{API}/sync",
            json={"mutations": [
                {"id": mid(), "type": "session.start",
                 "payload": {"id": session_id, "name": "Still going"}}
            ]},
        ).json()
        assert body["active_session"]["id"] == session_id
