"""Progress, records and history detail. SPECIFICATIONS.MD Sec 12, Sec 14, Sec 15."""

from __future__ import annotations

import uuid
from datetime import date as Date
from datetime import timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.clock import local_date, utcnow
from app.core.errors import NotFound
from app.db import get_db
from app.deps import current_user
from app.domain.enums import NON_COUNTING_SET_TYPES, RecordType, SessionStatus
from app.domain.models import (
    Exercise,
    PersonalRecord,
    SessionSummary,
    SetRecord,
    User,
    WorkoutSession,
)
from app.repo import exercises as exercise_repo
from app.repo.stats import StatsRepo
from app.repo.users import SettingsRepo

router = APIRouter(tags=["progress"])

_EXCLUDED = [t.value for t in NON_COUNTING_SET_TYPES]


class RecordOut(BaseModel):
    record_type: RecordType
    qualifier: Decimal
    value: Decimal
    reps: int | None
    weight_kg: Decimal | None
    achieved_on: Date
    session_id: uuid.UUID | None
    exercise_id: uuid.UUID
    exercise_name: str


class SessionPoint(BaseModel):
    date: Date
    session_id: uuid.UUID
    top_weight_kg: Decimal | None
    top_reps: int | None
    best_e1rm_kg: Decimal | None
    volume_kg: Decimal
    sets: int


class ExerciseProgressOut(BaseModel):
    exercise_id: uuid.UUID
    exercise_name: str
    metric_type: str
    points: list[SessionPoint]
    records: list[RecordOut]


class VolumePoint(BaseModel):
    week_start: Date
    volume_kg: Decimal
    sets: int
    sessions: int


class MuscleVolume(BaseModel):
    muscle: str
    sets: int


class ProgressOut(BaseModel):
    weekly: list[VolumePoint]
    muscles: list[MuscleVolume]
    sessions_completed: int
    adherence: float | None
    consistency_weeks: int


def _record_out(row: PersonalRecord) -> RecordOut:
    return RecordOut(
        record_type=RecordType(row.record_type),
        qualifier=row.qualifier,
        value=row.value,
        reps=row.reps,
        weight_kg=row.weight_kg,
        achieved_on=row.achieved_on,
        session_id=row.session_id,
        exercise_id=row.exercise_id,
        exercise_name=row.exercise.name,
    )


@router.get("/records", response_model=list[RecordOut])
def records(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    rows = db.execute(
        select(PersonalRecord)
        .where(PersonalRecord.user_id == user.id)
        # One row per weight would bury the headline records, so the
        # most-reps-at-a-weight family is only shown per exercise.
        .where(PersonalRecord.record_type != RecordType.MOST_REPS_AT_WEIGHT.value)
        .order_by(PersonalRecord.achieved_on.desc())
        .limit(limit)
    ).scalars()
    return [_record_out(row) for row in rows]


@router.get("/progress/exercises/{exercise_id}", response_model=ExerciseProgressOut)
def exercise_progress(
    exercise_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    exercise = exercise_repo.get(db, user_id=user.id, exercise_id=exercise_id)
    if exercise is None:
        raise NotFound("No such exercise.")

    rows = db.execute(
        select(
            WorkoutSession.date,
            WorkoutSession.id,
            func.max(SetRecord.weight_kg),
            func.max(SetRecord.reps),
            func.coalesce(func.sum(SetRecord.weight_kg * SetRecord.reps), Decimal(0)),
            func.count(SetRecord.id),
        )
        .join(WorkoutSession, SetRecord.session_id == WorkoutSession.id)
        .where(
            SetRecord.user_id == user.id,
            SetRecord.exercise_id == exercise_id,
            SetRecord.deleted_at.is_(None),
            SetRecord.set_type.notin_(_EXCLUDED),
            WorkoutSession.status == SessionStatus.COMPLETED.value,
        )
        .group_by(WorkoutSession.date, WorkoutSession.id)
        .order_by(WorkoutSession.date)
    ).all()

    from app.core.formulas import epley_1rm

    points = []
    for day, session_id, top_weight, top_reps, volume, count in rows:
        points.append(
            SessionPoint(
                date=day,
                session_id=session_id,
                top_weight_kg=top_weight,
                top_reps=top_reps,
                best_e1rm_kg=epley_1rm(top_weight, top_reps) if top_weight and top_reps else None,
                volume_kg=volume or Decimal(0),
                sets=count,
            )
        )

    pr_rows = db.execute(
        select(PersonalRecord).where(
            PersonalRecord.user_id == user.id,
            PersonalRecord.exercise_id == exercise_id,
        )
    ).scalars()

    return ExerciseProgressOut(
        exercise_id=exercise.id,
        exercise_name=exercise.name,
        metric_type=exercise.metric_type,
        points=points,
        records=[_record_out(row) for row in pr_rows],
    )


@router.get("/progress", response_model=ProgressOut)
def progress(
    weeks: int = Query(default=12, ge=1, le=104),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    settings = SettingsRepo(db, user.id).get()
    timezone = settings.timezone if settings else "UTC"
    week_start_pref = settings.week_start if settings else "monday"
    today = local_date(utcnow(), timezone)
    stats = StatsRepo(db, user.id)
    first_week = stats.week_start(today, week_start_pref) - timedelta(weeks=weeks - 1)

    rows = db.execute(
        select(
            WorkoutSession.date,
            func.coalesce(func.sum(SetRecord.weight_kg * SetRecord.reps), Decimal(0)),
            func.count(SetRecord.id),
            func.count(func.distinct(SetRecord.session_id)),
        )
        .join(WorkoutSession, SetRecord.session_id == WorkoutSession.id)
        .where(
            SetRecord.user_id == user.id,
            SetRecord.deleted_at.is_(None),
            SetRecord.set_type.notin_(_EXCLUDED),
            WorkoutSession.status == SessionStatus.COMPLETED.value,
            WorkoutSession.date >= first_week,
        )
        .group_by(WorkoutSession.date)
        .order_by(WorkoutSession.date)
    ).all()

    # Bucket by the user's week, not the calendar's (Sec 3.3).
    buckets: dict[Date, dict] = {}
    for index in range(weeks):
        buckets[first_week + timedelta(weeks=index)] = {
            "volume": Decimal(0), "sets": 0, "sessions": 0
        }
    for day, volume, sets_count, sessions in rows:
        key = stats.week_start(day, week_start_pref)
        if key in buckets:
            buckets[key]["volume"] += volume or Decimal(0)
            buckets[key]["sets"] += sets_count
            buckets[key]["sessions"] += sessions

    muscle_rows = db.execute(
        select(Exercise.primary_muscle, func.count(SetRecord.id))
        .join(Exercise, SetRecord.exercise_id == Exercise.id)
        .join(WorkoutSession, SetRecord.session_id == WorkoutSession.id)
        .where(
            SetRecord.user_id == user.id,
            SetRecord.deleted_at.is_(None),
            SetRecord.set_type.notin_(_EXCLUDED),
            WorkoutSession.status == SessionStatus.COMPLETED.value,
            WorkoutSession.date >= first_week,
        )
        .group_by(Exercise.primary_muscle)
        .order_by(func.count(SetRecord.id).desc())
    ).all()

    completed = sum(b["sessions"] for b in buckets.values())
    active_weeks = sum(1 for b in buckets.values() if b["sessions"] > 0)

    return ProgressOut(
        weekly=[
            VolumePoint(
                week_start=key, volume_kg=value["volume"],
                sets=value["sets"], sessions=value["sessions"],
            )
            for key, value in sorted(buckets.items())
        ],
        muscles=[MuscleVolume(muscle=m, sets=c) for m, c in muscle_rows],
        sessions_completed=completed,
        # Sec 14 - adherence needs a denominator of planned sessions, which
        # only exists once the schedule is used; null rather than a fake 100%.
        adherence=None,
        consistency_weeks=active_weeks,
    )
