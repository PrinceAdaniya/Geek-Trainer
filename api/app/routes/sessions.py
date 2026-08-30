"""Workout sessions and set logging. SPECIFICATIONS.MD Sec 8-11.

This is the core loop. Every decision here is subordinate to Sec 1.1: it has
to be usable one-handed, mid-set, on a phone.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.clock import local_date, utcnow
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.core.formulas import quantize_distance, quantize_rpe
from app.core.ids import uuid7
from app.core.units import to_storage
from app.db import get_db
from app.deps import current_user
from app.domain.enums import SessionStatus, Unit
from app.domain.models import User
from app.domain.schemas import (
    LastPerformance,
    SessionExerciseIn,
    SessionExerciseOut,
    SessionExerciseUpdate,
    SessionOut,
    SessionStart,
    SessionSummaryOut,
    SessionUpdate,
    SetIn,
    SetOut,
    SetUpdate,
)
from app.repo import exercises as exercise_repo
from app.repo.plans import PlanRepo
from app.repo.sessions import SessionRepo
from app.repo.users import SettingsRepo
from app.services.recompute import recompute_for_session
from app.services.sets import validate_set

router = APIRouter(tags=["sessions"])


def _settings(db: Session, user: User):
    return SettingsRepo(db, user.id).get()


def _unit(db: Session, user: User) -> Unit:
    settings = _settings(db, user)
    return Unit(settings.unit_preference) if settings else Unit.KG


def _available(db: Session, user: User) -> list[str]:
    settings = _settings(db, user)
    return list(settings.available_equipment) if settings else []


def _session_out(
    db: Session, user: User, session, *, with_history: bool = True
) -> SessionOut:
    repo = SessionRepo(db, user.id)
    available = _available(db, user)
    out = SessionOut.model_validate(session)

    for row, source in zip(out.exercises, session.exercises):
        missing = exercise_repo.missing_equipment(source.exercise, available)
        row.exercise.compatible = not missing
        row.exercise.missing_equipment = missing
        # Sec 12.4 - deleted sets are tombstoned, so they must be filtered out
        # of anything the user sees.
        row.sets = [
            SetOut.model_validate(s)
            for s in sorted(
                (s for s in source.sets if s.deleted_at is None),
                key=lambda s: s.set_number,
            )
        ]
        if with_history:
            previous = repo.last_performance(
                source.exercise_id, exclude_session=session.id
            )
            if previous:
                past_session, past_sets = previous
                row.last_performance = LastPerformance(
                    date=past_session.date,
                    sets=[SetOut.model_validate(s) for s in past_sets],
                )
    return out


def _snapshot(plan) -> dict:
    """Sec 7.1 - the plan exactly as it was at start. This copy is what keeps
    history immutable when the plan is edited later."""
    return {
        "workout_id": str(plan.id),
        "name": plan.name,
        "day_of_week": plan.day_of_week,
        "target_muscles": list(plan.target_muscles),
        "notes": plan.notes,
        "captured_at": utcnow().isoformat(),
        "exercises": [
            {
                "exercise_id": str(row.exercise_id),
                "name": row.exercise.name,
                "order_index": row.order_index,
                "planned_sets": row.planned_sets,
                "planned_reps_min": row.planned_reps_min,
                "planned_reps_max": row.planned_reps_max,
                "planned_weight_kg": (
                    str(row.planned_weight_kg) if row.planned_weight_kg else None
                ),
                "planned_rir": row.planned_rir,
                "superset_group": row.superset_group,
            }
            for row in plan.exercises
        ],
    }


@router.get("/sessions/active", response_model=SessionOut | None)
def active_session(db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Sec 8.2 - opening the app resumes what you were doing."""
    session = SessionRepo(db, user.id).active()
    return _session_out(db, user, session) if session else None


@router.post("/sessions", response_model=SessionOut, status_code=201)
def start_session(
    payload: SessionStart,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    repo = SessionRepo(db, user.id)
    settings = _settings(db, user)
    today = local_date(utcnow(), settings.timezone if settings else "UTC")

    plan = None
    snapshot = None
    name = payload.name
    if payload.workout_id:
        plan = PlanRepo(db, user.id).require(payload.workout_id)
        snapshot = _snapshot(plan)
        name = name or plan.name
    if not name:
        name = "Workout"

    session = repo.create(
        session_id=payload.id or uuid7(),
        name=name,
        local_date=today,
        workout_id=plan.id if plan else None,
        plan_snapshot=snapshot,
    )

    if plan:
        for row in plan.exercises:
            repo.add_exercise(
                session,
                exercise_id=row.exercise_id,
                planned_sets=row.planned_sets,
                planned_reps_min=row.planned_reps_min,
                planned_reps_max=row.planned_reps_max,
                superset_group=row.superset_group,
            )
    db.flush()
    db.refresh(session)
    return _session_out(db, user, repo.require(session.id))


@router.get("/sessions", response_model=list[SessionSummaryOut])
def list_sessions(
    limit: int = Query(default=30, ge=1, le=100),
    include_cancelled: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    repo = SessionRepo(db, user.id)
    statuses = (SessionStatus.COMPLETED.value,)
    if include_cancelled:
        statuses = statuses + (SessionStatus.CANCELLED.value,)

    out = []
    for session in repo.history(limit=limit, statuses=statuses):
        summary = SessionSummaryOut.model_validate(session)
        summary.exercise_count = len(session.exercises)
        summary.set_count = sum(
            1
            for exercise in session.exercises
            for row in exercise.sets
            if row.deleted_at is None
        )
        out.append(summary)
    return out


@router.get("/sessions/{session_id}", response_model=SessionOut)
def get_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    return _session_out(db, user, SessionRepo(db, user.id).require(session_id))


@router.patch("/sessions/{session_id}", response_model=SessionOut)
def update_session(
    session_id: uuid.UUID,
    payload: SessionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    repo = SessionRepo(db, user.id)
    session = repo.require(session_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(session, key, value)
    db.flush()
    return _session_out(db, user, session)


@router.post("/sessions/{session_id}/finish", response_model=SessionOut)
def finish_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    repo = SessionRepo(db, user.id)
    session = repo.finish(repo.require(session_id))
    # Sec 13.4 - derived data is rebuilt from the log, never patched.
    recompute_for_session(db, user.id, session.id)
    return _session_out(db, user, session)


@router.post("/sessions/{session_id}/cancel", response_model=SessionOut)
def cancel_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    repo = SessionRepo(db, user.id)
    session = repo.cancel(repo.require(session_id))
    return _session_out(db, user, session)


# --- exercises inside a session -------------------------------------------


@router.post("/sessions/{session_id}/exercises", response_model=SessionOut,
             status_code=201)
def add_session_exercise(
    session_id: uuid.UUID,
    payload: SessionExerciseIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    repo = SessionRepo(db, user.id)
    session = repo.require(session_id)
    exercise = exercise_repo.get(db, user_id=user.id, exercise_id=payload.exercise_id)
    if exercise is None:
        raise ValidationFailed("No such exercise.", code="unknown_exercise")

    repo.add_exercise(
        session,
        se_id=payload.id,
        exercise_id=exercise.id,
        replaced_from_exercise_id=payload.replaced_from_exercise_id,
        superset_group=payload.superset_group,
        notes=payload.notes,
    )
    db.flush()
    return _session_out(db, user, repo.require(session_id))


@router.patch("/sessions/{session_id}/exercises/{se_id}", response_model=SessionOut)
def update_session_exercise(
    session_id: uuid.UUID,
    se_id: uuid.UUID,
    payload: SessionExerciseUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    repo = SessionRepo(db, user.id)
    session = repo.require(session_id)
    row = repo.get_exercise(session, se_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.flush()
    return _session_out(db, user, repo.require(session_id))


@router.delete("/sessions/{session_id}/exercises/{se_id}", response_model=SessionOut)
def remove_session_exercise(
    session_id: uuid.UUID,
    se_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    repo = SessionRepo(db, user.id)
    session = repo.require(session_id)
    repo.remove_exercise(session, se_id)
    return _session_out(db, user, repo.require(session_id))


# --- sets ------------------------------------------------------------------


@router.post("/sessions/{session_id}/exercises/{se_id}/sets", response_model=SetOut,
             status_code=201)
def log_set(
    session_id: uuid.UUID,
    se_id: uuid.UUID,
    payload: SetIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    repo = SessionRepo(db, user.id)
    session = repo.require(session_id)
    if session.status != SessionStatus.IN_PROGRESS.value:
        raise Conflict("That session is finished.", code="session_not_in_progress")

    session_exercise = repo.get_exercise(session, se_id)
    values = payload.model_dump()
    validate_set(session_exercise.exercise.metric_type, values)

    row = repo.upsert_set(
        set_id=payload.id or uuid7(),
        session=session,
        session_exercise=session_exercise,
        weight_kg=to_storage(payload.weight, _unit(db, user)),
        reps=payload.reps,
        duration_seconds=payload.duration_seconds,
        distance_m=quantize_distance(payload.distance_m),
        rir=payload.rir,
        rpe=quantize_rpe(payload.rpe),
        failure=payload.failure,
        set_type=payload.set_type.value,
        rest_seconds=payload.rest_seconds,
        notes=payload.notes,
    )
    return SetOut.model_validate(row)


@router.put("/sessions/{session_id}/sets/{set_id}", response_model=SetOut)
def update_set(
    session_id: uuid.UUID,
    set_id: uuid.UUID,
    payload: SetUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    repo = SessionRepo(db, user.id)
    session = repo.require(session_id)
    row = repo.get_set(set_id)
    if row is None or row.session_id != session.id:
        raise NotFound("No such set.")

    session_exercise = repo.get_exercise(session, row.session_exercise_id)
    data = payload.model_dump(exclude_unset=True)

    merged = {
        "weight": data.get("weight", row.weight_kg),
        "reps": data.get("reps", row.reps),
        "duration_seconds": data.get("duration_seconds", row.duration_seconds),
        "distance_m": data.get("distance_m", row.distance_m),
    }
    validate_set(session_exercise.exercise.metric_type, merged)

    if "weight" in data:
        row.weight_kg = to_storage(data.pop("weight"), _unit(db, user))
    if "rpe" in data:
        data["rpe"] = quantize_rpe(data["rpe"])
    if "distance_m" in data:
        data["distance_m"] = quantize_distance(data["distance_m"])
    for key, value in data.items():
        setattr(row, key, value.value if hasattr(value, "value") else value)
    db.flush()
    # A correction to a past set must move every number that depended on it,
    # including revoking a record it no longer deserves (A6).
    if session.status == SessionStatus.COMPLETED.value:
        recompute_for_session(db, user.id, session.id)
    return SetOut.model_validate(row)


@router.delete("/sessions/{session_id}/sets/{set_id}", status_code=204)
def delete_set(
    session_id: uuid.UUID,
    set_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    repo = SessionRepo(db, user.id)
    session = repo.require(session_id)
    row = repo.get_set(set_id)
    if row is None or row.session_id != session.id:
        raise NotFound("No such set.")
    repo.delete_set(row)
    if session.status == SessionStatus.COMPLETED.value:
        recompute_for_session(db, user.id, session.id)
