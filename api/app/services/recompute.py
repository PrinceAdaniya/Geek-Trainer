"""Derived data. SPECIFICATIONS.MD Sec 13.4, PLAN.md D6.

The rule: derived values are **recomputed, never patched in place**. The same
set history always produces the same summaries and the same records, which is
what makes A6 possible - deleting the set that set a PR restores the previous
best everywhere, because the record was never an independent fact.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.formulas import epley_1rm, set_volume
from app.domain.enums import (
    NON_COUNTING_SET_TYPES,
    MetricType,
    RecordType,
    SessionStatus,
)
from app.domain.models import (
    BodyweightEntry,
    Exercise,
    PersonalRecord,
    SessionSummary,
    SetRecord,
    WorkoutSession,
)
from app.repo.guard import unscoped

_EXCLUDED = tuple(t.value for t in NON_COUNTING_SET_TYPES)


def _bodyweight_on(db: Session, user_id: uuid.UUID, when) -> Decimal | None:
    return db.execute(
        select(BodyweightEntry.weight_kg)
        .where(BodyweightEntry.user_id == user_id, BodyweightEntry.date <= when)
        .order_by(BodyweightEntry.date.desc())
        .limit(1)
    ).scalar_one_or_none()


def _counting_sets(db: Session, user_id: uuid.UUID, *, exercise_id=None, session_id=None):
    """Sec 10.3 - warm-ups are stored but never counted, and only completed
    sessions contribute."""
    stmt = (
        select(SetRecord, WorkoutSession, Exercise)
        .join(WorkoutSession, SetRecord.session_id == WorkoutSession.id)
        .join(Exercise, SetRecord.exercise_id == Exercise.id)
        .where(
            SetRecord.user_id == user_id,
            SetRecord.deleted_at.is_(None),
            SetRecord.set_type.notin_(_EXCLUDED),
            WorkoutSession.status == SessionStatus.COMPLETED.value,
            WorkoutSession.deleted_at.is_(None),
        )
    )
    if exercise_id:
        stmt = stmt.where(SetRecord.exercise_id == exercise_id)
    if session_id:
        stmt = stmt.where(SetRecord.session_id == session_id)
    return db.execute(stmt.order_by(WorkoutSession.date, SetRecord.performed_at)).all()


def volume_of(db: Session, user_id: uuid.UUID, row: SetRecord, session, exercise) -> Decimal | None:
    bodyweight = None
    if exercise.metric_type in (
        MetricType.BODYWEIGHT_REPS.value,
        MetricType.WEIGHTED_BODYWEIGHT.value,
    ):
        bodyweight = _bodyweight_on(db, user_id, session.date)
    return set_volume(
        metric_type=MetricType(exercise.metric_type),
        weight_kg=row.weight_kg,
        reps=row.reps,
        bodyweight_kg=bodyweight,
        bodyweight_factor=exercise.bodyweight_load_factor,
    )


# --- session summaries ----------------------------------------------------


def recompute_session_summary(db: Session, user_id: uuid.UUID, session_id: uuid.UUID) -> None:
    rows = _counting_sets(db, user_id, session_id=session_id)

    exercises: set[uuid.UUID] = set()
    muscles: dict[str, int] = {}
    total_reps = 0
    volume = Decimal(0)
    duration = 0
    distance = Decimal(0)

    for row, session, exercise in rows:
        exercises.add(row.exercise_id)
        muscles[exercise.primary_muscle] = muscles.get(exercise.primary_muscle, 0) + 1
        total_reps += row.reps or 0
        duration += row.duration_seconds or 0
        distance += row.distance_m or Decimal(0)
        contribution = volume_of(db, user_id, row, session, exercise)
        if contribution is not None:
            volume += contribution

    with unscoped("the summary row is keyed by a session already scoped"):
        db.execute(delete(SessionSummary).where(SessionSummary.session_id == session_id))
    db.add(
        SessionSummary(
            session_id=session_id,
            user_id=user_id,
            total_exercises=len(exercises),
            total_sets=len(rows),
            total_reps=total_reps,
            total_volume_kg=volume,
            total_duration_seconds=duration,
            total_distance_m=distance,
            muscles_trained=muscles,
        )
    )
    db.flush()


# --- personal records -----------------------------------------------------


def recompute_records(
    db: Session, user_id: uuid.UUID, exercise_id: uuid.UUID
) -> list[PersonalRecord]:
    """Rebuild every record for one exercise from the log.

    Deliberately a full rebuild rather than an incremental update: an
    incremental record cannot be revoked when the set behind it is deleted,
    and one mistyped 600 kg would poison every chart axis forever (Sec 15).
    """
    rows = _counting_sets(db, user_id, exercise_id=exercise_id)

    db.execute(
        delete(PersonalRecord).where(
            PersonalRecord.user_id == user_id,
            PersonalRecord.exercise_id == exercise_id,
        )
    )
    db.flush()
    if not rows:
        return []

    best: dict[tuple[str, Decimal], dict] = {}

    def offer(record_type: RecordType, qualifier: Decimal, value: Decimal, row, session):
        key = (record_type.value, qualifier)
        current = best.get(key)
        if current is None or value > current["value"]:
            best[key] = {
                "value": value,
                "row": row,
                "session": session,
                "reps": row.reps,
                "weight_kg": row.weight_kg,
            }

    session_volume: dict[uuid.UUID, tuple[Decimal, object, object]] = {}

    for row, session, exercise in rows:
        if row.weight_kg is not None and row.reps:
            offer(RecordType.HEAVIEST_WEIGHT, Decimal(0), row.weight_kg, row, session)
            offer(RecordType.MOST_REPS_AT_WEIGHT, row.weight_kg, Decimal(row.reps), row, session)
            estimate = epley_1rm(row.weight_kg, row.reps)
            if estimate is not None:
                offer(RecordType.BEST_E1RM, Decimal(0), estimate, row, session)
        if row.duration_seconds:
            offer(RecordType.LONGEST_DURATION, Decimal(0), Decimal(row.duration_seconds), row, session)
        if row.distance_m:
            offer(RecordType.FURTHEST_DISTANCE, Decimal(0), row.distance_m, row, session)

        contribution = volume_of(db, user_id, row, session, exercise)
        if contribution is not None:
            previous = session_volume.get(session.id)
            total = (previous[0] if previous else Decimal(0)) + contribution
            session_volume[session.id] = (total, row, session)

    for total, row, session in session_volume.values():
        offer(RecordType.HIGHEST_SESSION_VOLUME, Decimal(0), total, row, session)

    created = []
    for (record_type, qualifier), entry in best.items():
        record = PersonalRecord(
            user_id=user_id,
            exercise_id=exercise_id,
            record_type=record_type,
            qualifier=qualifier,
            value=entry["value"],
            reps=entry["reps"],
            weight_kg=entry["weight_kg"],
            set_id=entry["row"].id,
            session_id=entry["session"].id,
            achieved_on=entry["session"].date,
        )
        db.add(record)
        created.append(record)
    db.flush()
    return created


def recompute_for_session(db: Session, user_id: uuid.UUID, session_id: uuid.UUID) -> int:
    """Everything a finished, edited or deleted session touches."""
    recompute_session_summary(db, user_id, session_id)

    exercise_ids = db.execute(
        select(SetRecord.exercise_id)
        .where(SetRecord.user_id == user_id, SetRecord.session_id == session_id)
        .distinct()
    ).scalars()

    prs_here = 0
    for exercise_id in list(exercise_ids):
        for record in recompute_records(db, user_id, exercise_id):
            if record.session_id == session_id:
                prs_here += 1

    summary = db.execute(
        select(SessionSummary).where(
            SessionSummary.user_id == user_id, SessionSummary.session_id == session_id
        )
    ).scalar_one_or_none()
    if summary is not None:
        summary.prs_achieved = prs_here
    db.flush()
    return prs_here
