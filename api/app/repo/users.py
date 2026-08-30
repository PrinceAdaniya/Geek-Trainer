"""User and settings access."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.domain.models import (
    AuthSession,
    BodyweightEntry,
    LoginAttempt,
    PasswordResetToken,
    User,
    UserSettings,
)
from app.repo.base import UserScoped
from app.repo.guard import unscoped


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_by_email(db: Session, email: str) -> User | None:
    with unscoped("login and registration look users up by email"):
        return db.execute(
            select(User).where(
                User.email == normalize_email(email), User.deleted_at.is_(None)
            )
        ).scalar_one_or_none()


def get_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    with unscoped("identity lookup by primary key is already user-scoped"):
        return db.execute(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        ).scalar_one_or_none()


def create(
    db: Session, *, email: str, password_hash: str, name: str, timezone_name: str
) -> User:
    user = User(email=normalize_email(email), password_hash=password_hash, name=name)
    db.add(user)
    db.flush()
    db.add(UserSettings(user_id=user.id, timezone=timezone_name))
    db.flush()
    return user


class SettingsRepo(UserScoped):
    def get(self) -> UserSettings | None:
        return self.db.execute(self.scoped(UserSettings)).scalar_one_or_none()

    def upsert(self, **fields) -> UserSettings:
        settings = self.get()
        if settings is None:
            settings = UserSettings(user_id=self.user_id)
            self.db.add(settings)
        for key, value in fields.items():
            if value is not None:
                setattr(settings, key, value)
        self.db.flush()
        return settings


class BodyweightRepo(UserScoped):
    def list(self, limit: int = 365) -> list[BodyweightEntry]:
        stmt = (
            self.scoped(BodyweightEntry)
            .order_by(BodyweightEntry.date.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars())

    def latest(self) -> BodyweightEntry | None:
        stmt = self.scoped(BodyweightEntry).order_by(BodyweightEntry.date.desc()).limit(1)
        return self.db.execute(stmt).scalar_one_or_none()

    def on_or_before(self, when) -> BodyweightEntry | None:
        """Sec 13.2 - the bodyweight in effect on a session's date."""
        stmt = (
            self.scoped(BodyweightEntry)
            .where(BodyweightEntry.date <= when)
            .order_by(BodyweightEntry.date.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def upsert(self, *, entry_date, weight_kg, source: str = "manual") -> BodyweightEntry:
        existing = self.db.execute(
            self.scoped(BodyweightEntry).where(BodyweightEntry.date == entry_date)
        ).scalar_one_or_none()
        if existing is not None:
            existing.weight_kg = weight_kg
            existing.source = source
            self.db.flush()
            return existing
        entry = BodyweightEntry(
            user_id=self.user_id, date=entry_date, weight_kg=weight_kg, source=source
        )
        self.db.add(entry)
        self.db.flush()
        return entry


# --- auth-session storage -------------------------------------------------
# These tables are keyed by an opaque token, not by the requesting user, so
# they sit outside UserScoped by design.


def create_auth_session(
    db: Session, *, user_id: uuid.UUID, token_hash: str, ttl_days: int, user_agent=None
) -> AuthSession:
    row = AuthSession(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=utcnow() + timedelta(days=ttl_days),
        user_agent=(user_agent or "")[:400] or None,
    )
    db.add(row)
    db.flush()
    return row


def get_auth_session(db: Session, token_hash: str) -> AuthSession | None:
    return db.execute(
        select(AuthSession).where(AuthSession.token_hash == token_hash)
    ).scalar_one_or_none()


def revoke_auth_session(db: Session, token_hash: str) -> None:
    row = get_auth_session(db, token_hash)
    if row is not None and row.revoked_at is None:
        row.revoked_at = utcnow()
        db.flush()


def revoke_all_auth_sessions(db: Session, user_id: uuid.UUID) -> int:
    rows = db.execute(
        select(AuthSession).where(
            AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None)
        )
    ).scalars()
    count = 0
    for row in rows:
        row.revoked_at = utcnow()
        count += 1
    db.flush()
    return count


def touch_auth_session(db: Session, row: AuthSession, ttl_days: int) -> None:
    """Sliding expiry (Sec 24). Only written when it moves meaningfully, so a
    burst of requests does not become a burst of writes."""
    now = utcnow()
    if (now - row.last_seen_at).total_seconds() > 3600:
        row.last_seen_at = now
        row.expires_at = now + timedelta(days=ttl_days)
        db.flush()


# --- password reset -------------------------------------------------------


def create_reset_token(
    db: Session, *, user_id: uuid.UUID, token_hash: str, ttl_minutes: int
) -> PasswordResetToken:
    row = PasswordResetToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=utcnow() + timedelta(minutes=ttl_minutes),
    )
    db.add(row)
    db.flush()
    return row


def get_reset_token(db: Session, token_hash: str) -> PasswordResetToken | None:
    return db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    ).scalar_one_or_none()


# --- login rate limiting --------------------------------------------------


def record_login_attempt(_db: Session, *, email: str, ip: str, succeeded: bool) -> None:
    """Written in its own transaction on purpose.

    A failed login raises, and the request transaction is then rolled back - so
    an attempt recorded on the request session would vanish along with it and
    rate limiting would never fire. See ERRORS-AND-FIXES.md E1.
    """
    from app.db import session_factory

    with session_factory()() as own:
        own.add(
            LoginAttempt(
                email=normalize_email(email), ip=ip or "unknown", succeeded=succeeded
            )
        )
        own.commit()


def recent_failed_attempts(db: Session, *, email: str, ip: str, within_seconds: int) -> int:
    since = utcnow() - timedelta(seconds=within_seconds)
    stmt = select(func.count()).select_from(LoginAttempt).where(
        LoginAttempt.at >= since,
        LoginAttempt.succeeded.is_(False),
        (LoginAttempt.email == normalize_email(email)) | (LoginAttempt.ip == (ip or "unknown")),
    )
    return int(db.execute(stmt).scalar_one())
