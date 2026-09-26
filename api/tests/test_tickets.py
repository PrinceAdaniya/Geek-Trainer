"""Member support tickets, free-pass / tour enquiries and the staff inbox."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.conftest import register

API = "/api/v1"

TICKET = {
    "category": "equipment",
    "area": "Free weights",
    "subject": "Broken cable on the lat pulldown",
    "description": "The cable on the second lat pulldown is fraying near the pulley.",
}


def _login_as_new_user(app, *, staff: bool = False) -> TestClient:
    client = TestClient(app)
    response, creds = register(client)
    assert response.status_code == 201, response.text
    client.profile = response.json()
    if staff:
        from app.db import session_factory
        from app.domain.models import User

        with session_factory()() as db:
            user = db.execute(select(User).where(User.email == creds["email"])).scalars().one()
            user.is_staff = True
            db.commit()
    return client


class TestMemberTickets:
    def test_create_and_list(self, user_client):
        created = user_client.post(f"{API}/tickets", json=TICKET)
        assert created.status_code == 201, created.text
        body = created.json()
        assert body["status"] == "open"
        assert body["priority"] == "normal"
        assert body["staff_response"] is None

        listed = user_client.get(f"{API}/tickets").json()
        assert [t["id"] for t in listed] == [body["id"]]

    def test_validation(self, user_client):
        bad = user_client.post(f"{API}/tickets", json={**TICKET, "category": "vibes"})
        assert bad.status_code == 422
        short = user_client.post(f"{API}/tickets", json={**TICKET, "description": "bad"})
        assert short.status_code == 422

    def test_member_can_close_their_ticket(self, user_client):
        ticket = user_client.post(f"{API}/tickets", json=TICKET).json()
        closed = user_client.post(f"{API}/tickets/{ticket['id']}/close").json()
        assert closed["status"] == "closed"
        assert closed["resolved_at"] is not None

    def test_tickets_are_private(self, app, user_client):
        ticket = user_client.post(f"{API}/tickets", json=TICKET).json()
        other = _login_as_new_user(app)
        assert other.get(f"{API}/tickets").json() == []
        assert other.get(f"{API}/tickets/{ticket['id']}").status_code == 404
        assert other.post(f"{API}/tickets/{ticket['id']}/close").status_code == 404

    def test_requires_login(self, client):
        assert client.post(f"{API}/tickets", json=TICKET).status_code == 401

    def test_tickets_are_in_the_export(self, user_client):
        user_client.post(f"{API}/tickets", json=TICKET)
        export = user_client.get(f"{API}/account/export").json()
        assert export["support_tickets"][0]["subject"] == TICKET["subject"]


class TestStaffInbox:
    def test_members_cannot_see_the_inbox(self, user_client):
        assert user_client.get(f"{API}/staff/tickets").status_code == 403
        assert user_client.get(f"{API}/staff/leads").status_code == 403

    def test_profile_reports_staff_flag(self, app, user_client):
        assert user_client.get(f"{API}/auth/me").json()["is_staff"] is False
        staff = _login_as_new_user(app, staff=True)
        assert staff.get(f"{API}/auth/me").json()["is_staff"] is True

    def test_staff_reply_reaches_the_member(self, app, user_client):
        ticket = user_client.post(f"{API}/tickets", json=TICKET).json()
        staff = _login_as_new_user(app, staff=True)

        inbox = staff.get(f"{API}/staff/tickets").json()
        assert [t["id"] for t in inbox] == [ticket["id"]]
        assert inbox[0]["member_email"] == user_client.creds["email"]

        replied = staff.patch(
            f"{API}/staff/tickets/{ticket['id']}",
            json={"staff_response": "Cable replaced this morning - thanks for flagging."},
        ).json()
        # A reply on an open ticket moves it along without an explicit status.
        assert replied["status"] == "in_progress"
        assert replied["responded_at"] is not None

        resolved = staff.patch(
            f"{API}/staff/tickets/{ticket['id']}", json={"status": "resolved"}
        ).json()
        assert resolved["resolved_at"] is not None

        seen = user_client.get(f"{API}/tickets/{ticket['id']}").json()
        assert seen["status"] == "resolved"
        assert seen["staff_response"].startswith("Cable replaced")

    def test_urgent_tickets_come_first(self, app, user_client):
        user_client.post(f"{API}/tickets", json=TICKET)
        urgent = user_client.post(
            f"{API}/tickets", json={**TICKET, "category": "safety", "priority": "urgent"}
        ).json()
        staff = _login_as_new_user(app, staff=True)
        assert staff.get(f"{API}/staff/tickets").json()[0]["id"] == urgent["id"]

    def test_filter_by_status(self, app, user_client):
        ticket = user_client.post(f"{API}/tickets", json=TICKET).json()
        user_client.post(f"{API}/tickets/{ticket['id']}/close")
        staff = _login_as_new_user(app, staff=True)
        assert staff.get(f"{API}/staff/tickets", params={"status": "open"}).json() == []
        assert len(staff.get(f"{API}/staff/tickets", params={"status": "closed"}).json()) == 1


class TestLeads:
    LEAD = {"kind": "free_pass", "name": "Sam Visitor", "email": "Sam@Example.com"}

    def test_public_enquiry_reaches_staff(self, app, client):
        response = client.post(f"{API}/leads", json={**self.LEAD, "phone": "555 0100"})
        assert response.status_code == 201

        staff = _login_as_new_user(app, staff=True)
        leads = staff.get(f"{API}/staff/leads").json()
        assert len(leads) == 1
        assert leads[0]["email"] == "sam@example.com"
        assert leads[0]["status"] == "new"

        updated = staff.patch(
            f"{API}/staff/leads/{leads[0]['id']}", json={"status": "joined"}
        ).json()
        assert updated["status"] == "joined"

    def test_honeypot_is_accepted_but_not_stored(self, app, client):
        response = client.post(f"{API}/leads", json={**self.LEAD, "website": "spam.example"})
        assert response.status_code == 201
        staff = _login_as_new_user(app, staff=True)
        assert staff.get(f"{API}/staff/leads").json() == []

    def test_referral_code_credits_the_member(self, app, user_client):
        code = user_client.get(f"{API}/referral").json()["code"]
        assert len(code) == 8

        anonymous = TestClient(app)
        anonymous.post(f"{API}/leads", json={**self.LEAD, "kind": "tour", "referral_code": code})
        anonymous.post(f"{API}/leads", json={**self.LEAD, "referral_code": "zzzzzzzz"})

        staff = _login_as_new_user(app, staff=True)
        by_kind = {lead["kind"]: lead for lead in staff.get(f"{API}/staff/leads").json()}
        assert by_kind["tour"]["referred_by_name"] == user_client.profile["name"]
        assert by_kind["free_pass"]["referred_by_name"] is None

    def test_membership_enquiry_records_the_plan(self, app, client):
        client.post(f"{API}/leads", json={**self.LEAD, "kind": "membership", "plan": "Unlimited"})
        staff = _login_as_new_user(app, staff=True)
        lead = staff.get(f"{API}/staff/leads").json()[0]
        assert (lead["kind"], lead["plan"]) == ("membership", "Unlimited")
