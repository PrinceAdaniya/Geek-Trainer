"""Acceptance criterion A10 - a user cannot read or modify another user's data
through any endpoint - plus the guard that makes it structural rather than
remembered (SPECIFICATIONS.MD 23.1, 24; app/repo/guard.py).
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text

from app.domain.models import BodyweightEntry
from app.repo.guard import UnscopedQueryError, USER_OWNED_TABLES, unscoped
from app.repo.users import BodyweightRepo, SettingsRepo
from tests.conftest import register

API = "/api/v1"


@pytest.fixture
def two_users(client):
    """Two registered users, each with data, and a way to be either of them."""
    from fastapi.testclient import TestClient

    _, alice_creds = register(client, name="Alice")
    client.post(f"{API}/profile/bodyweight", json={"date": "2026-08-01", "weight": 70})
    alice = client.get(f"{API}/profile").json()
    client.cookies.clear()

    _, bob_creds = register(client, name="Bob")
    client.post(f"{API}/profile/bodyweight", json={"date": "2026-08-01", "weight": 90})
    bob = client.get(f"{API}/profile").json()

    return {"client": client, "alice": alice, "bob": bob,
            "alice_creds": alice_creds, "bob_creds": bob_creds}


def _login_as(client, creds):
    client.cookies.clear()
    response = client.post(f"{API}/auth/login", json=creds)
    assert response.status_code == 200, response.text


class TestA10DataIsolation:
    def test_each_user_sees_only_their_own_profile(self, two_users):
        client = two_users["client"]
        assert two_users["alice"]["id"] != two_users["bob"]["id"]

        _login_as(client, two_users["alice_creds"])
        assert client.get(f"{API}/profile").json()["name"] == "Alice"

        _login_as(client, two_users["bob_creds"])
        assert client.get(f"{API}/profile").json()["name"] == "Bob"

    def test_bodyweight_history_does_not_leak(self, two_users):
        client = two_users["client"]

        _login_as(client, two_users["alice_creds"])
        alice_rows = client.get(f"{API}/profile/bodyweight").json()

        _login_as(client, two_users["bob_creds"])
        bob_rows = client.get(f"{API}/profile/bodyweight").json()

        assert [r["weight_kg"] for r in alice_rows] == ["70.000"]
        assert [r["weight_kg"] for r in bob_rows] == ["90.000"]
        assert {r["id"] for r in alice_rows}.isdisjoint({r["id"] for r in bob_rows})

    def test_updating_your_profile_does_not_touch_anyone_elses(self, two_users):
        client = two_users["client"]

        _login_as(client, two_users["bob_creds"])
        client.put(f"{API}/profile", json={"name": "Bob Renamed", "unit_preference": "lb"})

        _login_as(client, two_users["alice_creds"])
        alice = client.get(f"{API}/profile").json()
        assert alice["name"] == "Alice"
        assert alice["settings"]["unit_preference"] == "kg"

    def test_every_user_owned_endpoint_requires_a_session(self, client):
        """The list grows with each phase; an endpoint added without auth fails
        here rather than in production."""
        protected = [
            ("GET", f"{API}/profile"),
            ("PUT", f"{API}/profile"),
            ("GET", f"{API}/profile/bodyweight"),
            ("POST", f"{API}/profile/bodyweight"),
            ("GET", f"{API}/auth/me"),
            ("POST", f"{API}/auth/logout-all"),
        ]
        client.cookies.clear()
        for method, path in protected:
            response = client.request(method, path, json={})
            assert response.status_code == 401, f"{method} {path} -> {response.status_code}"

    def test_repo_cannot_be_built_without_a_user(self, db):
        with pytest.raises(ValueError):
            BodyweightRepo(db, None)
        with pytest.raises(ValueError):
            SettingsRepo(db, None)

    def test_a_repo_bound_to_a_stranger_returns_nothing(self, two_users, db):
        """Even holding a valid session object, a repo scoped to an unrelated
        user id sees no rows - the scoping is in the query, not the route."""
        stranger = BodyweightRepo(db, uuid.uuid4())
        assert stranger.list() == []
        assert stranger.latest() is None


class TestScopingGuard:
    def test_guard_is_installed_in_tests(self):
        from app.repo import guard

        assert guard.is_installed()

    def test_an_unscoped_read_of_a_user_owned_table_raises(self, db):
        """This is the test that would fail if someone wrote a query that
        forgot user_id."""
        with pytest.raises(UnscopedQueryError) as exc:
            db.execute(select(BodyweightEntry)).all()
        assert "bodyweight_log" in str(exc.value)

    def test_a_scoped_read_is_allowed(self, db):
        db.execute(select(BodyweightEntry).where(
            BodyweightEntry.user_id == uuid.uuid4()
        )).all()

    def test_an_explicit_exception_is_allowed_but_must_be_justified(self, db):
        with unscoped("the ingest job legitimately spans users"):
            db.execute(select(BodyweightEntry)).all()

        with pytest.raises(ValueError):
            with unscoped("why"):
                pass

    def test_guard_covers_writes_too(self, db):
        with pytest.raises(UnscopedQueryError):
            db.execute(text("delete from bodyweight_log"))

    def test_every_user_owned_table_is_registered_with_the_guard(self):
        """A new user-owned table that nobody added to USER_OWNED_TABLES would
        be silently unguarded. This fails when that happens."""
        from app.db import Base

        owned = {
            name
            for name, table in Base.metadata.tables.items()
            if "user_id" in table.columns
        }
        # Tables keyed by an opaque token rather than the requesting user are
        # scoped by the token itself and are excluded by design.
        token_scoped = {"auth_sessions", "password_reset_tokens"}
        missing = owned - token_scoped - USER_OWNED_TABLES
        assert not missing, f"unguarded user-owned tables: {sorted(missing)}"
