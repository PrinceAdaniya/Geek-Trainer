"""Profile, settings and bodyweight. SPECIFICATIONS.MD Sec 3, Sec 4."""

from __future__ import annotations

API = "/api/v1"


class TestSettings:
    def test_defaults_are_sane(self, user_client):
        settings = user_client.get(f"{API}/profile").json()["settings"]
        assert settings["unit_preference"] == "kg"
        assert settings["week_start"] == "monday"
        assert settings["default_rest_seconds"] == 120
        assert settings["available_equipment"] == ["bodyweight"]

    def test_update_round_trips(self, user_client):
        response = user_client.put(
            f"{API}/profile",
            json={
                "name": "Prince",
                "unit_preference": "lb",
                "week_start": "sunday",
                "default_rest_seconds": 90,
                "training_goals": ["hypertrophy"],
                "available_equipment": ["dumbbell", "bench"],
            },
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["name"] == "Prince"
        assert body["training_goals"] == ["hypertrophy"]
        assert body["settings"]["unit_preference"] == "lb"
        assert body["settings"]["week_start"] == "sunday"
        # Persisted, not just echoed.
        assert user_client.get(f"{API}/profile").json()["settings"]["week_start"] == "sunday"

    def test_bodyweight_is_always_available(self, user_client):
        """Sec 4 - it cannot be deselected."""
        body = user_client.put(
            f"{API}/profile", json={"available_equipment": ["dumbbell"]}
        ).json()
        assert "bodyweight" in body["settings"]["available_equipment"]

    def test_unknown_equipment_is_rejected(self, user_client):
        response = user_client.put(
            f"{API}/profile", json={"available_equipment": ["dumbbell", "trapeze"]}
        )
        assert response.status_code == 422
        assert "trapeze" in response.text

    def test_unknown_timezone_is_rejected(self, user_client):
        response = user_client.put(f"{API}/profile", json={"timezone": "Mars/Olympus"})
        assert response.status_code == 422

    def test_a_real_timezone_is_accepted(self, user_client):
        response = user_client.put(f"{API}/profile", json={"timezone": "Asia/Kolkata"})
        assert response.status_code == 200
        assert response.json()["settings"]["timezone"] == "Asia/Kolkata"

    def test_partial_update_leaves_other_fields_alone(self, user_client):
        user_client.put(f"{API}/profile", json={"name": "First", "default_rest_seconds": 45})
        body = user_client.put(f"{API}/profile", json={"name": "Second"}).json()
        assert body["name"] == "Second"
        assert body["settings"]["default_rest_seconds"] == 45


class TestBodyweight:
    def test_records_in_kg_by_default(self, user_client):
        response = user_client.post(
            f"{API}/profile/bodyweight", json={"date": "2026-08-01", "weight": 72.5}
        )
        assert response.status_code == 201, response.text
        assert response.json()["weight_kg"] == "72.500"

    def test_a11_pounds_are_converted_at_the_boundary(self, user_client):
        """A11 - the user's unit choice never reaches storage."""
        user_client.put(f"{API}/profile", json={"unit_preference": "lb"})
        response = user_client.post(
            f"{API}/profile/bodyweight", json={"date": "2026-08-02", "weight": 160}
        )
        assert response.json()["weight_kg"] == "72.575"

    def test_explicit_unit_overrides_the_preference(self, user_client):
        response = user_client.post(
            f"{API}/profile/bodyweight",
            json={"date": "2026-08-03", "weight": 160, "unit": "lb"},
        )
        assert response.json()["weight_kg"] == "72.575"

    def test_one_entry_per_day_the_latest_wins(self, user_client):
        user_client.post(f"{API}/profile/bodyweight", json={"date": "2026-08-04", "weight": 70})
        user_client.post(f"{API}/profile/bodyweight", json={"date": "2026-08-04", "weight": 71})
        rows = user_client.get(f"{API}/profile/bodyweight").json()
        assert len(rows) == 1
        assert rows[0]["weight_kg"] == "71.000"

    def test_history_is_newest_first(self, user_client):
        for day, weight in [("2026-08-01", 70), ("2026-08-08", 71), ("2026-08-15", 72)]:
            user_client.post(f"{API}/profile/bodyweight", json={"date": day, "weight": weight})
        rows = user_client.get(f"{API}/profile/bodyweight").json()
        assert [r["date"] for r in rows] == ["2026-08-15", "2026-08-08", "2026-08-01"]

    def test_latest_appears_on_the_profile(self, user_client):
        user_client.post(f"{API}/profile/bodyweight", json={"date": "2026-08-20", "weight": 73})
        assert user_client.get(f"{API}/profile").json()["latest_bodyweight_kg"] == "73.000"

    def test_impossible_weights_are_rejected(self, user_client):
        assert user_client.post(
            f"{API}/profile/bodyweight", json={"date": "2026-08-01", "weight": 0}
        ).status_code == 422
        assert user_client.post(
            f"{API}/profile/bodyweight", json={"date": "2026-08-01", "weight": 5000}
        ).status_code == 422
