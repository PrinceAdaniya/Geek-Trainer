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
    text,
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


class WorkoutPlan(Base, TimestampMixin):
    """A recurring template. SPECIFICATIONS.MD 7.1, 7.2.

    A plan is not a session. Sessions copy the plan at start time, which is
    what makes "history must not be overwritten when future workouts are
    edited" (Sec 16.1) actually true.
    """

    __tablename__ = "workout_plans"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # Null means an unscheduled plan - a workout you own but have not put on a day.
    day_of_week: Mapped[str | None] = mapped_column(String(10))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    target_muscles: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default="{}"
    )
    notes: Mapped[str | None] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    # Sec 7.2 - a plan referenced by a session is archived, never hard-deleted.
    is_archived: Mapped[bool] = mapped_column(nullable=False, server_default="false")

    exercises: Mapped[list["WorkoutExercise"]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="WorkoutExercise.order_index",
    )

    __table_args__ = (
        Index("ix_workout_plans_user", "user_id"),
        Index("ix_workout_plans_user_day", "user_id", "day_of_week"),
    )


class WorkoutExercise(Base, TimestampMixin):
    """One exercise inside a plan. Sec 7.2."""

    __tablename__ = "workout_exercises"

    id: Mapped[uuid.UUID] = _uuid_pk()
    workout_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("workout_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Sec 22 - never cascade from an exercise into anything a user built.
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("exercises.id", ondelete="RESTRICT"), nullable=False
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    planned_sets: Mapped[int] = mapped_column(Integer, nullable=False, server_default="3")
    planned_reps_min: Mapped[int | None] = mapped_column(Integer)
    planned_reps_max: Mapped[int | None] = mapped_column(Integer)
    planned_weight_kg: Mapped[Decimal | None] = mapped_column(WeightKg)
    planned_rir: Mapped[int | None] = mapped_column(Integer)
    # Sec 10.5 - exercises sharing a group are performed alternating.
    superset_group: Mapped[str | None] = mapped_column(String(8))
    notes: Mapped[str | None] = mapped_column(Text)

    plan: Mapped[WorkoutPlan] = relationship(back_populates="exercises")
    exercise: Mapped["Exercise"] = relationship(lazy="joined")

    __table_args__ = (
        Index("ix_workout_exercises_plan", "workout_id", "order_index"),
        CheckConstraint(
            "planned_sets >= 1 and planned_sets <= 20", name="ck_we_sets"
        ),
        CheckConstraint(
            "planned_reps_min is null or planned_reps_max is null "
            "or planned_reps_min <= planned_reps_max",
            name="ck_we_rep_range",
        ),
    )


class WorkoutSession(Base, TimestampMixin):
    """One performance, on one date. SPECIFICATIONS.MD Sec 8.

    workout_id is nullable: an ad-hoc session with no plan is a first-class
    flow (Sec 8.3). plan_snapshot holds the plan exactly as it was at start,
    which is what keeps history immutable when the plan is later edited
    (Sec 7.1, Sec 16.1).
    """

    __tablename__ = "workout_sessions"

    # Client-generated UUIDv7 (PLAN.md D3) so an offline start syncs cleanly.
    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    workout_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workout_plans.id", ondelete="SET NULL")
    )
    plan_snapshot: Mapped[dict | None] = mapped_column(JSONB)

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # Sec 3.3 / PLAN.md D8 - the local calendar date, decided when it happens.
    date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="in_progress"
    )
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    exercises: Mapped[list["SessionExercise"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="SessionExercise.order_index",
    )

    __table_args__ = (
        Index("ix_sessions_user_date", "user_id", "date"),
        # Sec 8.2 - at most one session in progress per user.
        Index(
            "uq_sessions_one_active",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'in_progress' and deleted_at is null"),
        ),
    )


class SessionExercise(Base, TimestampMixin):
    """An exercise inside a session. Sec 9."""

    __tablename__ = "session_exercises"

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("workout_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("exercises.id", ondelete="RESTRICT"), nullable=False
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    planned_sets: Mapped[int | None] = mapped_column(Integer)
    planned_reps_min: Mapped[int | None] = mapped_column(Integer)
    planned_reps_max: Mapped[int | None] = mapped_column(Integer)
    # Sec 20 - history shows what was planned and what was actually done.
    replaced_from_exercise_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("exercises.id", ondelete="RESTRICT")
    )
    superset_group: Mapped[str | None] = mapped_column(String(8))
    skipped: Mapped[bool] = mapped_column(nullable=False, server_default="false")
    notes: Mapped[str | None] = mapped_column(Text)

    session: Mapped[WorkoutSession] = relationship(back_populates="exercises")
    exercise: Mapped["Exercise"] = relationship(
        lazy="joined", foreign_keys=[exercise_id]
    )
    sets: Mapped[list["SetRecord"]] = relationship(
        back_populates="session_exercise",
        cascade="all, delete-orphan",
        order_by="SetRecord.set_number",
    )

    __table_args__ = (Index("ix_session_exercises_session", "session_id", "order_index"),)


class SetRecord(Base, TimestampMixin):
    """One set. Sec 10.

    Every set is independently recorded, and the id comes from the client so a
    retried offline write cannot create a duplicate (PLAN.md D3).
    """

    __tablename__ = "sets"

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("workout_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_exercise_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("session_exercises.id", ondelete="CASCADE"),
        nullable=False,
    )
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("exercises.id", ondelete="RESTRICT"), nullable=False
    )

    set_number: Mapped[int] = mapped_column(Integer, nullable=False)
    weight_kg: Mapped[Decimal | None] = mapped_column(WeightKg)
    reps: Mapped[int | None] = mapped_column(Integer)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    distance_m: Mapped[Decimal | None] = mapped_column(Numeric(9, 2))

    rir: Mapped[int | None] = mapped_column(Integer)
    rpe: Mapped[Decimal | None] = mapped_column(Numeric(3, 1))
    failure: Mapped[bool] = mapped_column(nullable=False, server_default="false")
    set_type: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="working"
    )
    rest_seconds: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    performed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    session_exercise: Mapped[SessionExercise] = relationship(back_populates="sets")

    __table_args__ = (
        # Sec 22 - the index behind "my history for this exercise".
        Index("ix_sets_user_exercise", "user_id", "exercise_id", "performed_at"),
        Index("ix_sets_session", "session_id"),
        CheckConstraint("reps is null or (reps >= 0 and reps <= 1000)", name="ck_sets_reps"),
        CheckConstraint("rir is null or (rir >= 0 and rir <= 10)", name="ck_sets_rir"),
        CheckConstraint("rpe is null or (rpe >= 1 and rpe <= 10)", name="ck_sets_rpe"),
        CheckConstraint(
            "duration_seconds is null or duration_seconds >= 0", name="ck_sets_duration"
        ),
    )
