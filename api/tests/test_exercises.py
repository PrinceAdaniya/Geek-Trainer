"""Exercise discovery. SPECIFICATIONS.MD Sec 5.4, Sec 6.

Acceptance criterion A1 lives here: the equipment filter is set containment,
not intersection.
"""

from __future__ import annotations

import pytest

API = "/api/v1"


def _equip(client, *items):
    response = client.put(f"{API}/profile", json={"available_equipment": list(items)})
    assert response.status_code == 200, response.text


def _equip_everything(client):
    """A fully-equipped gym, for tests that are about a filter other than
    equipment."""
    vocab = client.get(f"{API}/vocabulary").json()
    _equip(client, *vocab["equipment"])


def _names(payload) -> set[str]:
    return {row["name"] for row in payload["data"]}


def _all_names(client, **params) -> set[str]:
    """Walk every page, so a result is never missed because of pagination."""
    names, cursor = set(), None
    while True:
        query = {**params, "limit": 100}
        if cursor:
            query["cursor"] = cursor
        payload = client.get(f"{API}/exercises", params=query).json()
        names |= _names(payload)
        cursor = payload["next_cursor"]
        if not cursor:
            return names


class TestA1EquipmentFilter:
    def test_a_barbell_only_user_is_not_offered_barbell_plus_bench(self, user_client):
        """A1, the exact case. Bench press needs barbell AND bench."""
        _equip(user_client, "barbell")
        names = _all_names(user_client)
        assert "Barbell Row" in names          # barbell alone - compatible
        assert "Barbell Bench Press" not in names   # barbell + bench - not
        assert "Deadlift" in names

    def test_adding_the_bench_unlocks_it(self, user_client):
        _equip(user_client, "barbell", "bench")
        names = _all_names(user_client)
        assert "Barbell Bench Press" in names

    def test_a_dumbbell_user_never_sees_a_barbell_exercise(self, user_client):
        """A1: 'a user with only dumbbell selected never sees a barbell-only
        exercise'."""
        _equip(user_client, "dumbbell")
        names = _all_names(user_client)
        assert not any("Barbell" in name for name in names), sorted(names)
        assert "Dumbbell Curl" in names

    def test_bodyweight_is_always_available(self, user_client):
        _equip(user_client, "dumbbell")
        assert "Push-Up" in _all_names(user_client)

    def test_owning_more_never_removes_an_option(self, user_client):
        """Set containment is monotonic - more equipment can only add."""
        _equip(user_client, "dumbbell")
        fewer = _all_names(user_client)
        _equip(user_client, "dumbbell", "bench", "barbell")
        more = _all_names(user_client)
        assert fewer <= more

    def test_incompatible_can_be_shown_with_the_reason_named(self, user_client):
        """Sec 6.1 - greyed with the missing equipment named, never silently
        hidden with no explanation."""
        _equip(user_client, "barbell")
        payload = user_client.get(
            f"{API}/exercises",
            params={"q": "bench press", "include_incompatible": True, "limit": 100},
        ).json()
        rows = {row["name"]: row for row in payload["data"]}
        assert "Barbell Bench Press" in rows
        row = rows["Barbell Bench Press"]
        assert row["compatible"] is False
        assert row["missing_equipment"] == ["bench"]

    def test_compatible_rows_say_so(self, user_client):
        _equip(user_client, "barbell")
        payload = user_client.get(f"{API}/exercises", params={"q": "barbell row"}).json()
        row = payload["data"][0]
        assert row["compatible"] is True
        assert row["missing_equipment"] == []

    def test_equipment_can_be_overridden_per_query(self, user_client):
        """'What could I do today with only dumbbells?'"""
        _equip(user_client, "barbell", "bench", "dumbbell")
        names = _all_names(user_client, equipment=["dumbbell"])
        assert not any("Barbell" in name for name in names)


class TestFilters:
    @pytest.fixture(autouse=True)
    def _gym(self, user_client):
        _equip_everything(user_client)

    def test_by_muscle_includes_secondary(self, user_client):
        payload = user_client.get(
            f"{API}/exercises", params={"muscle": "triceps", "limit": 100}
        ).json()
        names = _names(payload)
        assert "Triceps Pushdown" in names       # primary
        assert "Barbell Bench Press" in names    # secondary

    def test_by_body_part(self, user_client):
        payload = user_client.get(
            f"{API}/exercises", params={"body_part": "back", "limit": 100}
        ).json()
        assert all(row["body_part"] == "back" for row in payload["data"])
        assert "Pull-Up" in _names(payload)

    def test_by_difficulty_and_type(self, user_client):
        payload = user_client.get(
            f"{API}/exercises",
            params={"difficulty": "advanced", "type": "compound", "limit": 100},
        ).json()
        assert payload["total"] >= 1
        for row in payload["data"]:
            assert row["difficulty"] == "advanced"
            assert row["type"] == "compound"

    def test_search_is_accent_and_punctuation_insensitive(self, user_client):
        assert "Pull-Up" in _names(
            user_client.get(f"{API}/exercises", params={"q": "pull up"}).json()
        )
        assert "Bulgarian Split Squat" in _names(
            user_client.get(f"{API}/exercises", params={"q": "split-squat"}).json()
        )

    def test_unknown_search_returns_an_empty_page_not_an_error(self, user_client):
        payload = user_client.get(f"{API}/exercises", params={"q": "zzzznope"}).json()
        assert payload["data"] == []
        assert payload["total"] == 0
        assert payload["next_cursor"] is None


class TestPagination:
    @pytest.fixture(autouse=True)
    def _gym(self, user_client):
        _equip_everything(user_client)

    def test_pages_do_not_overlap_or_skip(self, user_client):
        first = user_client.get(f"{API}/exercises", params={"limit": 10}).json()
        assert len(first["data"]) == 10
        assert first["next_cursor"]

        second = user_client.get(
            f"{API}/exercises", params={"limit": 10, "cursor": first["next_cursor"]}
        ).json()
        assert not (_names(first) & _names(second))

    def test_walking_every_page_reaches_the_total(self, user_client):
        total = user_client.get(f"{API}/exercises", params={"limit": 1}).json()["total"]
        assert len(_all_names(user_client)) == total

    def test_a_garbage_cursor_does_not_500(self, user_client):
        response = user_client.get(f"{API}/exercises", params={"cursor": "!!!not-b64"})
        assert response.status_code == 200


class TestCatalogueIntegrity:
    def test_bodyweight_movements_all_carry_a_load_factor(self, user_client):
        """Sec 13.1 - without this a set of pull-ups scores zero volume."""
        offenders = [
            row["name"]
            for row in _pages(user_client)
            if row["metric_type"] in ("bodyweight_reps", "weighted_bodyweight")
            and row["bodyweight_load_factor"] is None
        ]
        assert offenders == []

    def test_weight_based_movements_have_no_load_factor(self, user_client):
        offenders = [
            row["name"]
            for row in _pages(user_client)
            if row["metric_type"] == "weight_reps"
            and row["bodyweight_load_factor"] is not None
        ]
        assert offenders == []

    def test_every_exercise_has_an_instruction(self, user_client):
        assert all(row["instructions"] for row in _pages(user_client))

    def test_time_and_distance_movements_exist(self, user_client):
        """A5 needs something to log: a plank and a run must be in the
        catalogue, not just representable in theory."""
        metrics = {row["metric_type"] for row in _pages(user_client)}
        assert "time" in metrics
        assert "time_distance" in metrics
        names = {row["name"] for row in _pages(user_client)}
        assert "Plank" in names


def _pages(client) -> list[dict]:
    rows, cursor = [], None
    while True:
        params = {"limit": 100, "include_incompatible": True}
        if cursor:
            params["cursor"] = cursor
        payload = client.get(f"{API}/exercises", params=params).json()
        rows.extend(payload["data"])
        cursor = payload["next_cursor"]
        if not cursor:
            return rows


class TestVocabulary:
    def test_client_can_discover_every_list(self, user_client):
        vocab = user_client.get(f"{API}/vocabulary").json()
        assert "dumbbell" in vocab["equipment"]
        assert "back" in vocab["body_parts"]
        assert "lats" in vocab["muscles"]
        assert "lats" in vocab["body_part_muscles"]["back"]
        assert "warmup" in vocab["set_types"]
        assert "weighted_bodyweight" in vocab["metric_types"]


class TestCustomExercises:
    """Sec 5.4 - no external catalogue covers every gym."""

    def _make(self, client, **overrides):
        payload = {
            "name": "Iso-Lateral Row (Hammer)",
            "primary_muscle": "lats",
            "secondary_muscles": ["biceps"],
            "equipment": ["machine"],
            "metric_type": "weight_reps",
            "type": "compound",
            "instructions": ["Row one arm at a time."],
            **overrides,
        }
        return client.post(f"{API}/exercises", json=payload)

    def test_create_and_find(self, user_client):
        _equip_everything(user_client)
        response = self._make(user_client)
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["is_custom"] is True
        assert body["body_part"] == "back"
        assert "Iso-Lateral Row (Hammer)" in _all_names(user_client)

    def test_a_bodyweight_custom_exercise_gets_a_load_factor(self, user_client):
        """Sec 13.2 - otherwise it would score zero volume forever."""
        response = self._make(
            user_client,
            name="Ring Row",
            metric_type="bodyweight_reps",
            equipment=["bodyweight"],
        )
        assert response.json()["bodyweight_load_factor"] == "1.000"

    def test_a_weight_based_custom_exercise_gets_none(self, user_client):
        response = self._make(user_client, name="Plate Press", bodyweight_load_factor=0.5)
        assert response.json()["bodyweight_load_factor"] is None

    def test_unknown_muscle_or_equipment_is_rejected(self, user_client):
        assert self._make(user_client, primary_muscle="gills").status_code == 422
        assert self._make(user_client, equipment=["trapeze"]).status_code == 422
        assert self._make(user_client, equipment=[]).status_code == 422

    def test_duplicate_name_is_a_conflict(self, user_client):
        self._make(user_client)
        second = self._make(user_client)
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "exercise_name_taken"

    def test_cannot_shadow_a_catalogue_name(self, user_client):
        response = self._make(user_client, name="Barbell Row")
        assert response.status_code == 409

    def test_edit_your_own(self, user_client):
        created = self._make(user_client).json()
        response = user_client.put(
            f"{API}/exercises/{created['id']}",
            json={"name": "Iso Row", "default_rest_seconds": 60},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Iso Row"
        assert response.json()["default_rest_seconds"] == 60

    def test_cannot_edit_a_catalogue_exercise(self, user_client):
        _equip_everything(user_client)
        catalogue_id = user_client.get(
            f"{API}/exercises", params={"q": "barbell row"}
        ).json()["data"][0]["id"]
        response = user_client.put(f"{API}/exercises/{catalogue_id}", json={"name": "Mine"})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "not_editable"

    def test_delete_archives_rather_than_removes(self, user_client):
        """Sec 16.1 - deleting an exercise must never break a past session."""
        created = self._make(user_client).json()
        assert user_client.delete(f"{API}/exercises/{created['id']}").status_code == 204
        assert "Iso-Lateral Row (Hammer)" not in _all_names(user_client)
        # Still there, just archived - history can still resolve it.
        assert user_client.get(f"{API}/exercises/{created['id']}").status_code == 404

    def test_a_custom_exercise_is_private(self, client):
        """Sec 5.4 - never enters another user's search."""
        from tests.conftest import register

        _, alice = register(client)
        created = client.post(
            f"{API}/exercises",
            json={
                "name": "Alice's Secret Machine",
                "primary_muscle": "quads",
                "equipment": ["machine"],
                "metric_type": "weight_reps",
            },
        ).json()

        client.cookies.clear()
        register(client, name="Bob")
        _equip_everything(client)
        assert "Alice's Secret Machine" not in _all_names(client)
        # And addressing it directly is a 404, not a 403 (Sec 23.1).
        assert client.get(f"{API}/exercises/{created['id']}").status_code == 404
        assert client.put(
            f"{API}/exercises/{created['id']}", json={"name": "Bob's now"}
        ).status_code == 404
        assert client.delete(f"{API}/exercises/{created['id']}").status_code == 404
