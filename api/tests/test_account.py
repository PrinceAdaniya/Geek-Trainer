"""Export and deletion. SPECIFICATIONS.MD Sec 25."""

from __future__ import annotations

import csv
import io
import json

import pytest

API = "/api/v1"


@pytest.fixture
def trained(user_client):
    vocab = user_client.get(f"{API}/vocabulary").json()
    user_client.put(f"{API}/profile", json={"available_equipment": vocab["equipment"]})
    user_client.post(f"{API}/profile/bodyweight", json={"date": "2026-08-01", "weight": 75})

    row_id = [
        r["id"]
        for r in user_client.get(f"{API}/exercises", params={"q": "barbell row"}).json()["data"]
        if r["name"] == "Barbell Row"
    ][0]
    plan = user_client.post(f"{API}/workouts", json={"name": "Pull", "day_of_week": "monday"}).json()
    user_client.post(f"{API}/workouts/{plan['id']}/exercises", json={"exercise_id": row_id})

    session = user_client.post(f"{API}/sessions", json={"workout_id": plan["id"]}).json()
    se = session["exercises"][0]
    for reps in (10, 9):
        user_client.post(
            f"{API}/sessions/{session['id']}/exercises/{se['id']}/sets",
            json={"weight": 60, "reps": reps},
        )
    user_client.post(f"{API}/sessions/{session['id']}/finish")
    return user_client


class TestExport:
    def test_json_export_contains_everything(self, trained):
        response = trained.get(f"{API}/account/export")
        assert response.status_code == 200
        assert "attachment" in response.headers["content-disposition"]

        data = json.loads(response.content)
        assert data["profile"]["email"]
        assert len(data["sets"]) == 2
        assert len(data["sessions"]) == 1
        assert len(data["plans"]) == 1
        assert data["bodyweight"][0]["weight_kg"] == "75.000"

    def test_the_export_is_readable_without_this_app(self, trained):
        """Sec 25 - names, not just ids."""
        response = trained.get(f"{API}/account/export.csv")
        assert response.status_code == 200
        rows = list(csv.DictReader(io.StringIO(response.text)))
        assert len(rows) == 2
        assert rows[0]["exercise"] == "Barbell Row"
        assert rows[0]["weight_kg"] == "60.000"
        assert rows[0]["reps"] == "10"

    def test_export_requires_a_session(self, client):
        client.cookies.clear()
        assert client.get(f"{API}/account/export").status_code == 401
        assert client.get(f"{API}/account/export.csv").status_code == 401

    def test_an_export_holds_only_your_own_data(self, client):
        from tests.conftest import register

        register(client)
        client.post(f"{API}/profile/bodyweight", json={"date": "2026-08-01", "weight": 70})
        client.cookies.clear()
        _, bob = register(client)

        data = json.loads(client.get(f"{API}/account/export").content)
        assert data["bodyweight"] == []
        assert data["profile"]["email"] == bob["email"]


class TestDeletion:
    def test_deletion_needs_the_password(self, trained):
        assert trained.post(
            f"{API}/account/delete", json={"password": "not-my-password"}
        ).status_code == 401
        assert trained.get(f"{API}/profile").status_code == 200

    def test_deletion_removes_everything_and_ends_the_session(self, trained):
        creds = trained.creds
        assert trained.post(
            f"{API}/account/delete", json={"password": creds["password"]}
        ).status_code == 204

        assert trained.get(f"{API}/profile").status_code == 401
        trained.cookies.clear()
        assert trained.post(f"{API}/auth/login", json=creds).status_code == 401

    def test_the_shared_catalogue_survives(self, trained):
        before = trained.get(f"{API}/exercises", params={"limit": 1}).json()["total"]
        trained.post(f"{API}/account/delete", json={"password": trained.creds["password"]})

        from tests.conftest import register

        trained.cookies.clear()
        register(trained)
        vocab = trained.get(f"{API}/vocabulary").json()
        trained.put(f"{API}/profile", json={"available_equipment": vocab["equipment"]})
        after = trained.get(f"{API}/exercises", params={"limit": 1}).json()["total"]
        assert after >= before

    def test_a_custom_exercise_goes_with_its_owner(self, trained):
        created = trained.post(
            f"{API}/exercises",
            json={"name": "My Odd Machine", "primary_muscle": "quads",
                  "equipment": ["machine"], "metric_type": "weight_reps"},
        ).json()
        trained.post(f"{API}/account/delete", json={"password": trained.creds["password"]})

        from tests.conftest import register

        trained.cookies.clear()
        register(trained)
        assert trained.get(f"{API}/exercises/{created['id']}").status_code == 404

    def test_deletion_requires_a_session(self, client):
        client.cookies.clear()
        assert client.post(
            f"{API}/account/delete", json={"password": "x"}
        ).status_code == 401
