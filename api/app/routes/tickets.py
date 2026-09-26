"""Member support tickets, public enquiries (free pass, tour, membership),
and the staff inbox."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db import get_db
from app.deps import current_user
from app.domain.enums import (
    LeadKind,
    LeadStatus,
    TicketCategory,
    TicketPriority,
    TicketStatus,
)
from app.domain.models import User
from app.repo.tickets import StaffInbox, TicketRepo, create_lead, referral_code

router = APIRouter(tags=["support"])


class Forbidden(AppError):
    status_code = 403
    code = "forbidden"


def current_staff(user: User = Depends(current_user)) -> User:
    if not user.is_staff:
        raise Forbidden("This area is for gym staff.")
    return user


def _clean(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


# --- schemas ----------------------------------------------------------------


class TicketIn(BaseModel):
    category: TicketCategory
    area: str | None = Field(default=None, max_length=60)
    subject: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=10, max_length=4000)
    priority: TicketPriority = TicketPriority.NORMAL

    @field_validator("subject", "description")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


class TicketOut(BaseModel):
    id: uuid.UUID
    category: TicketCategory
    area: str | None
    subject: str
    description: str
    priority: TicketPriority
    status: TicketStatus
    staff_response: str | None
    responded_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class StaffTicketOut(TicketOut):
    member_name: str
    member_email: str


class TicketUpdate(BaseModel):
    status: TicketStatus | None = None
    staff_response: str | None = Field(default=None, max_length=4000)


class LeadIn(BaseModel):
    kind: LeadKind
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=40)
    preferred_date: date | None = None
    plan: str | None = Field(default=None, max_length=40)
    message: str | None = Field(default=None, max_length=2000)
    referral_code: str | None = Field(default=None, max_length=16)
    # Honeypot. Hidden from people; bots fill every field they find.
    website: str | None = Field(default=None, max_length=200)


class LeadAck(BaseModel):
    received: bool = True


class LeadOut(BaseModel):
    id: uuid.UUID
    kind: LeadKind
    name: str
    email: str
    phone: str | None
    preferred_date: date | None
    plan: str | None
    message: str | None
    status: LeadStatus
    referred_by_name: str | None
    created_at: datetime


class LeadUpdate(BaseModel):
    status: LeadStatus


class ReferralOut(BaseModel):
    code: str


def _ticket_out(ticket) -> TicketOut:
    return TicketOut.model_validate(ticket, from_attributes=True)


def _staff_ticket_out(ticket) -> StaffTicketOut:
    return StaffTicketOut(
        **_ticket_out(ticket).model_dump(),
        member_name=ticket.user.name,
        member_email=ticket.user.email,
    )


def _lead_out(lead) -> LeadOut:
    return LeadOut(
        id=lead.id, kind=lead.kind, name=lead.name, email=lead.email,
        phone=lead.phone, preferred_date=lead.preferred_date, plan=lead.plan,
        message=lead.message,
        status=lead.status, created_at=lead.created_at,
        referred_by_name=lead.referred_by.name if lead.referred_by else None,
    )


# --- member -----------------------------------------------------------------


@router.get("/tickets", response_model=list[TicketOut])
def list_tickets(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return [_ticket_out(t) for t in TicketRepo(db, user.id).list()]


@router.post("/tickets", response_model=TicketOut, status_code=201)
def create_ticket(body: TicketIn, db: Session = Depends(get_db),
                  user: User = Depends(current_user)):
    ticket = TicketRepo(db, user.id).create(
        category=body.category.value,
        area=_clean(body.area),
        subject=body.subject,
        description=body.description,
        priority=body.priority.value,
    )
    return _ticket_out(ticket)


@router.get("/tickets/{ticket_id}", response_model=TicketOut)
def get_ticket(ticket_id: uuid.UUID, db: Session = Depends(get_db),
               user: User = Depends(current_user)):
    return _ticket_out(TicketRepo(db, user.id).require(ticket_id))


@router.post("/tickets/{ticket_id}/close", response_model=TicketOut)
def close_ticket(ticket_id: uuid.UUID, db: Session = Depends(get_db),
                 user: User = Depends(current_user)):
    repo = TicketRepo(db, user.id)
    return _ticket_out(repo.close(repo.require(ticket_id)))


@router.get("/referral", response_model=ReferralOut)
def my_referral(user: User = Depends(current_user)):
    return ReferralOut(code=referral_code(user))


# --- public -----------------------------------------------------------------


@router.post("/leads", response_model=LeadAck, status_code=201)
def create_enquiry(body: LeadIn, db: Session = Depends(get_db)):
    """Free-pass claims, tour bookings and membership enquiries from the
    public site. No login - these people are not members yet."""
    if body.website:
        # A bot filled the honeypot. Say yes and store nothing.
        return LeadAck()
    create_lead(
        db,
        kind=body.kind.value,
        name=body.name.strip(),
        email=str(body.email).lower(),
        phone=_clean(body.phone),
        preferred_date=body.preferred_date,
        plan=_clean(body.plan),
        message=_clean(body.message),
        referral_code=body.referral_code,
    )
    return LeadAck()


# --- staff ------------------------------------------------------------------


@router.get("/staff/tickets", response_model=list[StaffTicketOut])
def staff_tickets(status: TicketStatus | None = None, db: Session = Depends(get_db),
                  _: User = Depends(current_staff)):
    inbox = StaffInbox(db)
    return [_staff_ticket_out(t) for t in inbox.tickets(status.value if status else None)]


@router.patch("/staff/tickets/{ticket_id}", response_model=StaffTicketOut)
def staff_update_ticket(ticket_id: uuid.UUID, body: TicketUpdate,
                        db: Session = Depends(get_db), _: User = Depends(current_staff)):
    inbox = StaffInbox(db)
    ticket = inbox.update_ticket(
        inbox.ticket(ticket_id),
        status=body.status.value if body.status else None,
        staff_response=_clean(body.staff_response) if body.staff_response is not None else None,
    )
    return _staff_ticket_out(ticket)


@router.get("/staff/leads", response_model=list[LeadOut])
def staff_leads(status: LeadStatus | None = None, db: Session = Depends(get_db),
                _: User = Depends(current_staff)):
    return [_lead_out(lead) for lead in StaffInbox(db).leads(status.value if status else None)]


@router.patch("/staff/leads/{lead_id}", response_model=LeadOut)
def staff_update_lead(lead_id: uuid.UUID, body: LeadUpdate,
                      db: Session = Depends(get_db), _: User = Depends(current_staff)):
    lead = StaffInbox(db).lead(lead_id)
    lead.status = body.status.value
    db.flush()
    return _lead_out(lead)
