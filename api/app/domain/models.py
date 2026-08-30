"""SQLAlchemy models.

Conventions from SPECIFICATIONS.MD Sec 22, binding on every table:
  - every user-owned table carries user_id and is indexed on it
  - created_at / updated_at everywhere, deleted_at on user data
  - loads are NUMERIC, never float
  - no ON DELETE cascade from a plan or an exercise into logged history
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.domain.enums import ExerciseSource, MetricType, Unit, WeekStart

# NUMERIC(7,3) kg - SPECIFICATIONS.MD 3.1. Never Float.
WeightKg = Numeric(7, 3)


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _uuid_pk()
    # Stored lower-cased; uniqueness is on the lower-cased value.
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    age: Mapped[int | None] = mapped_column(Integer)
    sex: Mapped[str | None] = mapped_column(String(20))
    training_experience: Mapped[str | None] = mapped_column(String(20))
    training_goals: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default="{}"
    )
    preferred_training_days: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default="{}"
    )
    preferred_session_duration_minutes: Mapped[int | None] = mapped_column(Integer)
    injury_notes: Mapped[str | None] = mapped_column(Text)

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    settings: Mapped["UserSettings"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("age IS NULL OR (age >= 10 AND age <= 120)", name="ck_users_age"),
    )


class UserSettings(Base, TimestampMixin):
    """Split from User because these change often and are read on every render."""

    __tablename__ = "user_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    unit_preference: Mapped[str] = mapped_column(
        String(4), nullable=False, server_default=Unit.KG.value
    )
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default="UTC"
    )
    week_start: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default=WeekStart.MONDAY.value
    )
    default_rest_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="120"
    )
    available_equipment: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default="{bodyweight}"
    )
    # Sec 3.2 - {equipment_id: increment} in the user's display unit.
    weight_increments: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )

    user: Mapped[User] = relationship(back_populates="settings")


class BodyweightEntry(Base, TimestampMixin):
    """Sec 3.4 - bodyweight is a time series, not a profile field."""

    __tablename__ = "bodyweight_log"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    weight_kg: Mapped[Decimal] = mapped_column(WeightKg, nullable=False)
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="manual"
    )

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_bodyweight_user_date"),
        CheckConstraint("weight_kg > 0 AND weight_kg < 1000", name="ck_bodyweight_range"),
        Index("ix_bodyweight_user_date", "user_id", "date"),
    )


class AuthSession(Base):
    """Sec 24 - opaque token, stored hashed. PLAN.md D9 explains why not a JWT."""

    __tablename__ = "auth_sessions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_agent: Mapped[str | None] = mapped_column(String(400))

    __table_args__ = (Index("ix_auth_sessions_user", "user_id"),)


class PasswordResetToken(Base):
    """Sec 24 - single-use, 15 minute expiry, stored hashed."""

    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("ix_reset_tokens_user", "user_id"),)


class LoginAttempt(Base):
    """Sec 24 - login rate limiting, per account and per IP."""

    __tablename__ = "login_attempts"

    id: Mapped[uuid.UUID] = _uuid_pk()
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    ip: Mapped[str] = mapped_column(String(64), nullable=False)
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    succeeded: Mapped[bool] = mapped_column(nullable=False, server_default="false")

    __table_args__ = (
        Index("ix_login_attempts_email_at", "email", "at"),
        Index("ix_login_attempts_ip_at", "ip", "at"),
    )


class Exercise(Base, TimestampMixin):
    """SPECIFICATIONS.MD 5.3.

    exercise_id is ours, not the provider's (5.3), so a change of data source
    does not orphan a single logged set. Provider identity lives in
    (source, source_id).
    """

    __tablename__ = "exercises"

    id: Mapped[uuid.UUID] = _uuid_pk()

    source: Mapped[str] = mapped_column(String(20), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(120))
    source_version: Mapped[str | None] = mapped_column(String(40))
    ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_normalized: Mapped[str] = mapped_column(String(200), nullable=False)
    aliases: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default="{}"
    )

    body_part: Mapped[str] = mapped_column(String(40), nullable=False)
    primary_muscle: Mapped[str] = mapped_column(String(40), nullable=False)
    secondary_muscles: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default="{}"
    )
    equipment: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default="{}"
    )

    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    metric_type: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=MetricType.WEIGHT_REPS.value
    )
    # Sec 13.2 - what fraction of bodyweight the movement actually loads.
    bodyweight_load_factor: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    default_rest_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="120"
    )

    instructions: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default="{}"
    )
    image_url: Mapped[str | None] = mapped_column(Text)
    gif_url: Mapped[str | None] = mapped_column(Text)
    video_url: Mapped[str | None] = mapped_column(Text)
    media_licence: Mapped[str | None] = mapped_column(String(120))

    # Sec 5.4 - a user's own exercise. Private, and never in anyone else's search.
    is_custom: Mapped[bool] = mapped_column(nullable=False, server_default="false")
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )

    # Sec 16.1 - an exercise referenced by history is retired, never removed.
    is_archived: Mapped[bool] = mapped_column(nullable=False, server_default="false")

    __table_args__ = (
        UniqueConstraint("source", "source_id", name="uq_exercise_source"),
        CheckConstraint(
            "(is_custom = false and owner_user_id is null) or "
            "(is_custom = true and owner_user_id is not null)",
            name="ck_exercise_custom_owner",
        ),
        CheckConstraint(
            "bodyweight_load_factor is null or "
            "(bodyweight_load_factor >= 0 and bodyweight_load_factor <= 2)",
            name="ck_exercise_bw_factor",
        ),
        Index("ix_exercises_primary_muscle", "primary_muscle"),
        Index("ix_exercises_body_part", "body_part"),
        Index("ix_exercises_owner", "owner_user_id"),
        Index("ix_exercises_name_normalized", "name_normalized"),
        Index("ix_exercises_equipment", "equipment", postgresql_using="gin"),
        Index("ix_exercises_secondary", "secondary_muscles", postgresql_using="gin"),
    )


class IngestRun(Base):
    """Sec 5.1 - every exercise row is traceable to the run that wrote it, and a
    partial ingest never replaces a good dataset."""

    __tablename__ = "ingest_runs"

    id: Mapped[uuid.UUID] = _uuid_pk()
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="running"
    )
    rows_seen: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    rows_written: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    rows_rejected: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    notes: Mapped[str | None] = mapped_column(Text)
