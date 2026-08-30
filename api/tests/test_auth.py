"""SPECIFICATIONS.MD Sec 24, PLAN.md D9."""

from __future__ import annotations

import pytest

from tests.conftest import register

API = "/api/v1"


class TestRegistration:
    def test_register_logs_you_in_and_returns_the_profile(self, client):
        response, _ = register(client, name="Prince")
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["name"] == "Prince"
        assert body["settings"]["unit_preference"] == "kg"
        assert "gt_session" in response.cookies

    def test_password_hash_is_never_returned(self, client):
        response, _ = register(client)
        assert "password" not in response.text.lower()

    def test_short_password_is_rejected(self, client):
        response, _ = register(client, password="short")
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_failed"

    def test_common_password_is_rejected(self, client):
        response, _ = register(client, password="password123")
        assert response.status_code == 422

    def test_duplicate_email_does_not_confirm_the_account_exists(self, client):
        """Sec 24 - no account enumeration."""
        _, creds = register(client, email="taken@example.com")
        second = client.post(
            f"{API}/auth/register",
            json={
                "email": "taken@example.com",
                "password": "another-good-password",
                "name": "Someone Else",
                "timezone": "UTC",
            },
        )
        assert second.status_code == 422
        message = second.json()["error"]["message"].lower()
        assert "already" not in message and "taken" not in message
        assert "exists" not in message

    def test_email_is_stored_lower_cased(self, client):
        response, _ = register(client, email="MiXeD@Example.COM")
        assert response.json()["email"] == "mixed@example.com"


class TestLogin:
    def test_login_then_me(self, client):
        _, creds = register(client)
        client.cookies.clear()
        login = client.post(f"{API}/auth/login", json=creds)
        assert login.status_code == 200, login.text
        me = client.get(f"{API}/auth/me")
        assert me.status_code == 200
        assert me.json()["email"] == creds["email"]

    def test_wrong_password_is_401(self, client):
        _, creds = register(client)
        client.cookies.clear()
        response = client.post(
            f"{API}/auth/login", json={**creds, "password": "wrong-password-here"}
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "not_authenticated"

    def test_unknown_email_looks_exactly_like_a_wrong_password(self, client):
        _, creds = register(client)
        client.cookies.clear()
        wrong_pw = client.post(
            f"{API}/auth/login", json={**creds, "password": "wrong-password-here"}
        )
        unknown = client.post(
            f"{API}/auth/login",
            json={"email": "nobody@example.com", "password": "wrong-password-here"},
        )
        assert wrong_pw.status_code == unknown.status_code == 401
        assert wrong_pw.json() == unknown.json()

    def test_me_requires_a_session(self, client):
        response = client.get(f"{API}/auth/me")
        assert response.status_code == 401

    def test_rate_limited_after_repeated_failures(self, client):
        _, creds = register(client)
        client.cookies.clear()
        statuses = []
        for _ in range(12):
            statuses.append(
                client.post(
                    f"{API}/auth/login", json={**creds, "password": "still-wrong-pw"}
                ).status_code
            )
        assert 429 in statuses, statuses
        assert statuses.index(429) >= 10


class TestLogout:
    def test_logout_revokes_the_session(self, user_client):
        assert user_client.get(f"{API}/auth/me").status_code == 200
        assert user_client.post(f"{API}/auth/logout").status_code == 200
        assert user_client.get(f"{API}/auth/me").status_code == 401

    def test_a_revoked_token_stays_dead(self, client):
        _, creds = register(client)
        token = client.cookies.get("gt_session")
        client.post(f"{API}/auth/logout")
        client.cookies.set("gt_session", token)
        assert client.get(f"{API}/auth/me").status_code == 401

    def test_logout_all_kills_other_sessions(self, client):
        """Sec 24 - 'log out of all devices' is why this is not a JWT."""
        _, creds = register(client)
        first_token = client.cookies.get("gt_session")
        client.cookies.clear()
        client.post(f"{API}/auth/login", json=creds)
        client.post(f"{API}/auth/logout-all")

        client.cookies.set("gt_session", first_token)
        assert client.get(f"{API}/auth/me").status_code == 401


class TestPasswordReset:
    def _sender(self):
        from app.mail.sender import get_sender

        return get_sender()

    def test_reset_flow(self, client):
        _, creds = register(client)
        sender = self._sender()
        sender.sent.clear()

        response = client.post(
            f"{API}/auth/password/reset-request", json={"email": creds["email"]}
        )
        assert response.status_code == 200
        assert len(sender.sent) == 1
        token = sender.sent[0]["body"].split("token=")[1].split()[0]

        confirmed = client.post(
            f"{API}/auth/password/reset",
            json={"token": token, "password": "a-brand-new-password"},
        )
        assert confirmed.status_code == 200

        client.cookies.clear()
        assert client.post(f"{API}/auth/login", json=creds).status_code == 401
        assert client.post(
            f"{API}/auth/login",
            json={"email": creds["email"], "password": "a-brand-new-password"},
        ).status_code == 200

    def test_reset_request_for_unknown_email_says_the_same_thing(self, client):
        _, creds = register(client)
        known = client.post(
            f"{API}/auth/password/reset-request", json={"email": creds["email"]}
        )
        unknown = client.post(
            f"{API}/auth/password/reset-request", json={"email": "nobody@example.com"}
        )
        assert known.json() == unknown.json()

    def test_token_is_single_use(self, client):
        _, creds = register(client)
        sender = self._sender()
        sender.sent.clear()
        client.post(f"{API}/auth/password/reset-request", json={"email": creds["email"]})
        token = sender.sent[0]["body"].split("token=")[1].split()[0]

        first = client.post(
            f"{API}/auth/password/reset", json={"token": token, "password": "new-password-one"}
        )
        second = client.post(
            f"{API}/auth/password/reset", json={"token": token, "password": "new-password-two"}
        )
        assert first.status_code == 200
        assert second.status_code == 422

    def test_reset_ends_every_existing_session(self, client):
        _, creds = register(client)
        old_token = client.cookies.get("gt_session")
        sender = self._sender()
        sender.sent.clear()
        client.post(f"{API}/auth/password/reset-request", json={"email": creds["email"]})
        token = sender.sent[0]["body"].split("token=")[1].split()[0]
        client.post(
            f"{API}/auth/password/reset", json={"token": token, "password": "yet-another-password"}
        )

        client.cookies.clear()
        client.cookies.set("gt_session", old_token)
        assert client.get(f"{API}/auth/me").status_code == 401

    def test_garbage_token_is_rejected(self, client):
        response = client.post(
            f"{API}/auth/password/reset",
            json={"token": "not-a-real-token-at-all", "password": "some-good-password"},
        )
        assert response.status_code == 422
