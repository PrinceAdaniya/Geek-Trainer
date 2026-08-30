"""Workout plans and the weekly schedule. SPECIFICATIONS.MD Sec 7."""

from __future__ import annotations

import pytest

API = "/api/v1"


@pytest.fixture
def gym(user_client):
    vocab = user_client.get(f"{API}/vocabulary").json()
    user_client.put(f"{API}/profile", json={"available_equipment": vocab["equipment"]})
    return user_client


def find_exercise(client, name: str) -> str:
    payload = client.get(f"{API}/exercises", params={"q": name, "limit": 5}).json()
    for row in payload["data"]:
        if row["name"] == name:
            return row["id"]
    raise AssertionError(f"{name} not in catalogue: {[r['name'] for r in payload['data']]}")


def make_plan(client, **overrides) -> dict:
    body = {"name": "Back + Biceps", "day_of_week": "monday",
            "target_muscles": ["lats", "biceps"], **overrides}
    response = client.post(f"{API}/workouts", json=body)
    assert response.status_code == 201, response.text
    return response.json()


class TestPlanCrud:
    def test_create_and_read_back(self, gym):
        plan = make_plan(gym)
        assert plan["name"] == "Back + Biceps"
        assert plan["day_of_week"] == "monday"
        assert plan["exercises"] == []

        fetched = gym.get(f"{API}/workouts/{plan['id']}").json()
        assert fetched["id"] == plan["id"]

    def test_rename_and_move_between_days(self, gym):
        plan = make_plan(gym)
        updated = gym.put(
            f"{API}/workouts/{plan['id']}",
            json={"name": "Pull Day", "day_of_week": "thursday"},
        ).json()
        assert updated["name"] == "Pull Day"
        assert updated["day_of_week"] == "thursday"

    def test_a_plan_can_be_taken_off_the_calendar(self, gym):
        plan = make_plan(gym)
        updated = gym.put(f"{API}/workouts/{plan['id']}", json={"clear_day": True}).json()
        assert updated["day_of_week"] is None
        week = gym.get(f"{API}/week").json()
        assert [p["id"] for p in week["unscheduled"]] == [plan["id"]]

    def test_unknown_muscle_is_rejected(self, gym):
        response = gym.post(
            f"{API}/workouts", json={"name": "Nonsense", "target_muscles": ["gills"]}
        )
        assert response.status_code == 422

    def test_delete_archives_and_disappears_from_the_week(self, gym):
        plan = make_plan(gym)
        assert gym.delete(f"{API}/workouts/{plan['id']}").status_code == 204
        assert gym.get(f"{API}/workouts/{plan['id']}").status_code == 404
        week = gym.get(f"{API}/week").json()
        assert week["days"]["monday"] == []

    def test_week_has_every_day_even_when_empty(self, gym):
        week = gym.get(f"{API}/week").json()
        assert set(week["days"]) == {
            "monday", "tuesday", "wednesday", "thursday",
            "friday", "saturday", "sunday",
        }
        assert all(day == [] for day in week["days"].values())

    def test_two_workouts_on_one_day_keep_their_order(self, gym):
        first = make_plan(gym, name="Morning")
        second = make_plan(gym, name="Evening")
        week = gym.get(f"{API}/week").json()
        assert [p["id"] for p in week["days"]["monday"]] == [first["id"], second["id"]]


class TestPlanExercises:
    def test_add_exercises_in_order(self, gym):
        plan = make_plan(gym)
        for name in ["Pull-Up", "One Arm Dumbbell Row", "Barbell Curl"]:
            response = gym.post(
                f"{API}/workouts/{plan['id']}/exercises",
                json={"exercise_id": find_exercise(gym, name), "planned_sets": 3,
                      "planned_reps_min": 8, "planned_reps_max": 12},
            )
            assert response.status_code == 201, response.text

        fetched = gym.get(f"{API}/workouts/{plan['id']}").json()
        assert [e["exercise"]["name"] for e in fetched["exercises"]] == [
            "Pull-Up", "One Arm Dumbbell Row", "Barbell Curl"
        ]
        assert [e["order_index"] for e in fetched["exercises"]] == [0, 1, 2]

    def test_planned_weight_is_stored_in_kg(self, gym):
        """Sec 3.1 - the user's unit never reaches storage."""
        gym.put(f"{API}/profile", json={"unit_preference": "lb"})
        plan = make_plan(gym)
        row = gym.post(
            f"{API}/workouts/{plan['id']}/exercises",
            json={"exercise_id": find_exercise(gym, "Barbell Row"), "planned_weight": 100},
        ).json()
        assert row["planned_weight_kg"] == "45.359"

    def test_reorder(self, gym):
        plan = make_plan(gym)
        ids = []
        for name in ["Pull-Up", "One Arm Dumbbell Row", "Barbell Curl"]:
            ids.append(
                gym.post(
                    f"{API}/workouts/{plan['id']}/exercises",
                    json={"exercise_id": find_exercise(gym, name)},
                ).json()["id"]
            )

        reversed_ids = list(reversed(ids))
        response = gym.post(
            f"{API}/workouts/{plan['id']}/reorder", json={"exercise_ids": reversed_ids}
        )
        assert response.status_code == 200, response.text
        assert [e["id"] for e in response.json()["exercises"]] == reversed_ids

    def test_reorder_must_name_every_exercise(self, gym):
        plan = make_plan(gym)
        first = gym.post(
            f"{API}/workouts/{plan['id']}/exercises",
            json={"exercise_id": find_exercise(gym, "Pull-Up")},
        ).json()["id"]
        gym.post(
            f"{API}/workouts/{plan['id']}/exercises",
            json={"exercise_id": find_exercise(gym, "Barbell Curl")},
        )
        response = gym.post(
            f"{API}/workouts/{plan['id']}/reorder", json={"exercise_ids": [first]}
        )
        assert response.status_code == 404

    def test_removing_an_exercise_renumbers_the_rest(self, gym):
        plan = make_plan(gym)
        ids = [
            gym.post(
                f"{API}/workouts/{plan['id']}/exercises",
                json={"exercise_id": find_exercise(gym, name)},
            ).json()["id"]
            for name in ["Pull-Up", "One Arm Dumbbell Row", "Barbell Curl"]
        ]
        assert gym.delete(
            f"{API}/workouts/{plan['id']}/exercises/{ids[0]}"
        ).status_code == 204

        fetched = gym.get(f"{API}/workouts/{plan['id']}").json()
        assert [e["order_index"] for e in fetched["exercises"]] == [0, 1]
        assert [e["id"] for e in fetched["exercises"]] == ids[1:]

    def test_update_sets_and_reps(self, gym):
        plan = make_plan(gym)
        row = gym.post(
            f"{API}/workouts/{plan['id']}/exercises",
            json={"exercise_id": find_exercise(gym, "Pull-Up")},
        ).json()
        updated = gym.put(
            f"{API}/workouts/{plan['id']}/exercises/{row['id']}",
            json={"planned_sets": 5, "planned_reps_min": 5, "planned_reps_max": 8,
                  "planned_rir": 2},
        ).json()
        assert updated["planned_sets"] == 5
        assert (updated["planned_reps_min"], updated["planned_reps_max"]) == (5, 8)
        assert updated["planned_rir"] == 2

    def test_backwards_rep_range_is_rejected(self, gym):
        plan = make_plan(gym)
        response = gym.post(
            f"{API}/workouts/{plan['id']}/exercises",
            json={"exercise_id": find_exercise(gym, "Pull-Up"),
                  "planned_reps_min": 12, "planned_reps_max": 8},
        )
        assert response.status_code == 422

    def test_unknown_exercise_is_rejected(self, gym):
        plan = make_plan(gym)
        response = gym.post(
            f"{API}/workouts/{plan['id']}/exercises",
            json={"exercise_id": "00000000-0000-0000-0000-000000000000"},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "unknown_exercise"

    def test_a_plan_shows_when_you_lack_the_equipment(self, user_client):
        """You can plan a barbell day and still be told you have no barbell."""
        user_client.put(f"{API}/profile", json={"available_equipment": ["dumbbell"]})
        plan = make_plan(user_client)
        barbell_id = user_client.get(
            f"{API}/exercises",
            params={"q": "barbell row", "include_incompatible": True},
        ).json()["data"][0]["id"]
        user_client.post(
            f"{API}/workouts/{plan['id']}/exercises", json={"exercise_id": barbell_id}
        )
        fetched = user_client.get(f"{API}/workouts/{plan['id']}").json()
        assert fetched["exercises"][0]["exercise"]["compatible"] is False
        assert fetched["exercises"][0]["exercise"]["missing_equipment"] == ["barbell"]


class TestPlanIsolation:
    def test_another_users_plan_is_a_404(self, client):
        from tests.conftest import register

        register(client)
        plan = make_plan(client)
        client.cookies.clear()
        register(client)

        assert client.get(f"{API}/workouts/{plan['id']}").status_code == 404
        assert client.put(f"{API}/workouts/{plan['id']}", json={"name": "Mine"}).status_code == 404
        assert client.delete(f"{API}/workouts/{plan['id']}").status_code == 404
        assert client.post(
            f"{API}/workouts/{plan['id']}/exercises",
            json={"exercise_id": "00000000-0000-0000-0000-000000000000"},
        ).status_code == 404

    def test_the_week_only_shows_your_own(self, client):
        from tests.conftest import register

        register(client)
        make_plan(client, name="Alice Monday")
        client.cookies.clear()
        register(client)

        week = client.get(f"{API}/week").json()
        assert week["days"]["monday"] == []

    def test_plan_endpoints_require_a_session(self, client):
        client.cookies.clear()
        assert client.get(f"{API}/week").status_code == 401
        assert client.get(f"{API}/workouts").status_code == 401
        assert client.post(f"{API}/workouts", json={"name": "x"}).status_code == 401
