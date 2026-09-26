"""Support tickets and free-pass / tour leads.

Members reach their own tickets through `TicketRepo`, scoped like every other
user-owned table. Staff read across members through `StaffInbox`, which is the
one place that says so with `unscoped()`.
"""

from __future__ import annotations

import uuid

from sqlalchemy import String, cast, select

from app.core.clock import utcnow
from app.core.errors import NotFound
from app.domain.enums import TicketStatus
from app.domain.models import Lead, SupportTicket, User
from app.repo.base import UserScoped
from app.repo.guard import unscoped

CLOSED_STATES = {TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value}


class TicketRepo(UserScoped):
    def list(self) -> list[SupportTicket]:
        return list(
            self.db.execute(
                self.scoped(SupportTicket).order_by(SupportTicket.created_at.desc())
            ).scalars().unique()
        )

    def require(self, ticket_id: uuid.UUID) -> SupportTicket:
        ticket = self.db.execute(
            self.scoped(SupportTicket).where(SupportTicket.id == ticket_id)
        ).scalars().first()
        if ticket is None:
            raise NotFound("Ticket not found.")
        return ticket

    def create(self, **fields) -> SupportTicket:
        ticket = SupportTicket(user_id=self.user_id, **fields)
        self.db.add(ticket)
        self.db.flush()
        self.db.refresh(ticket)
        return ticket

    def close(self, ticket: SupportTicket) -> SupportTicket:
        ticket.status = TicketStatus.CLOSED.value
        ticket.resolved_at = ticket.resolved_at or utcnow()
        self.db.flush()
        return ticket


class StaffInbox:
    """Cross-member reads for gym staff. Callers must already have checked
    `user.is_staff` - see app/routes/tickets.py `current_staff`."""

    def __init__(self, db) -> None:
        self.db = db

    def tickets(self, status: str | None = None) -> list[SupportTicket]:
        stmt = select(SupportTicket).order_by(
            # Urgent first, then oldest first: the longest-waiting member is
            # the one most likely to leave.
            (SupportTicket.priority == "urgent").desc(),
            SupportTicket.created_at.asc(),
        )
        if status:
            stmt = stmt.where(SupportTicket.status == status)
        with unscoped("staff inbox lists every member's tickets"):
            return list(self.db.execute(stmt).scalars().unique())

    def ticket(self, ticket_id: uuid.UUID) -> SupportTicket:
        with unscoped("staff read one member's ticket by id"):
            ticket = self.db.get(SupportTicket, ticket_id)
        if ticket is None:
            raise NotFound("Ticket not found.")
        return ticket

    def update_ticket(self, ticket: SupportTicket, *, status: str | None,
                      staff_response: str | None) -> SupportTicket:
        now = utcnow()
        if staff_response is not None and staff_response != ticket.staff_response:
            ticket.staff_response = staff_response
            ticket.responded_at = now
            # Replying to an untouched ticket means someone is on it.
            if status is None and ticket.status == TicketStatus.OPEN.value:
                ticket.status = TicketStatus.IN_PROGRESS.value
        if status is not None:
            ticket.status = status
        if ticket.status in CLOSED_STATES:
            ticket.resolved_at = ticket.resolved_at or now
        else:
            ticket.resolved_at = None
        with unscoped("staff update of a ticket loaded through the inbox"):
            self.db.flush()
        return ticket

    def leads(self, status: str | None = None) -> list[Lead]:
        stmt = select(Lead).order_by(Lead.created_at.desc())
        if status:
            stmt = stmt.where(Lead.status == status)
        return list(self.db.execute(stmt).scalars().unique())

    def lead(self, lead_id: uuid.UUID) -> Lead:
        lead = self.db.get(Lead, lead_id)
        if lead is None:
            raise NotFound("Enquiry not found.")
        return lead


def create_lead(db, *, referral_code: str | None, **fields) -> Lead:
    lead = Lead(referred_by_user_id=referrer_for(db, referral_code), **fields)
    db.add(lead)
    db.flush()
    return lead


def referral_code(user: User) -> str:
    """The first block of the member's id - short enough to say out loud,
    and needs no extra column."""
    return str(user.id).split("-")[0]


def referrer_for(db, code: str | None) -> uuid.UUID | None:
    code = (code or "").strip().lower()
    if len(code) != 8 or not all(c in "0123456789abcdef" for c in code):
        return None
    return db.execute(
        select(User.id).where(
            cast(User.id, String).like(f"{code}-%"), User.deleted_at.is_(None)
        )
    ).scalars().first()
