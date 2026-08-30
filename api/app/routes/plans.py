"""Weekly schedule and workout plans. SPECIFICATIONS.MD Sec 7, Sec 23."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import NotFound, ValidationFailed
from app.core.units import to_storage
from app.db import get_db
from app.deps import current_user
from app.domain.enums import DayOfWeek, Unit
from app.domain.models import User
from app.domain.schemas import (
    PlanExerciseIn,
    PlanExerciseOut,
    PlanExerciseUpdate,
    PlanIn,
    PlanOut,
    PlanUpdate,
    ReorderIn,
    WeekOut,
)
from app.repo import exercises as exercise_repo
from app.repo.plans import PlanRepo
from app.repo.users import SettingsRepo

router = APIRouter(tags=["workouts"])


def _unit(db: Session, user: User) -> Unit:
    settings = SettingsRepo(db, user.id).get()
    return Unit(settings.unit_preference) if settings else Unit.KG


def _available(db: Session, user: User) -> list[str]:
    settings = SettingsRepo(db, user.id).get()
    return list(settings.available_equipment) if settings else []


def _plan_out(plan, available: list[str]) -> PlanOut:
    out = PlanOut.model_validate(plan)
    for row, source in zip(out.exercises, plan.exercises):
        missing = exercise_repo.missing_equipment(source.exercise, available)
        row.exercise.compatible = not missing
        row.exercise.missing_equipment = missing
    return out


@router.get("/week", response_model=WeekOut)
def week(db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Sec 7 - the whole schedule in one call, so the week screen never
    fires seven requests."""
    available = _available(db, user)
    plans = PlanRepo(db, user.id).list()

    days: dict[str, list[PlanOut]] = {day.value: [] for day in DayOfWeek}
    unscheduled: list[PlanOut] = []
    for plan in plans:
        out = _plan_out(plan, available)
        if plan.day_of_week:
            days[plan.day_of_week].append(out)
        else:
            unscheduled.append(out)
    return WeekOut(days=days, unscheduled=unscheduled)


@router.get("/workouts", response_model=list[PlanOut])
def list_workouts(db: Session = Depends(get_db), user: User = Depends(current_user)):
    available = _available(db, user)
    return [_plan_out(plan, available) for plan in PlanRepo(db, user.id).list()]


@router.post("/workouts", response_model=PlanOut, status_code=201)
def create_workout(
    payload: PlanIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    plan = PlanRepo(db, user.id).create(
        name=payload.name.strip(),
        day_of_week=payload.day_of_week.value if payload.day_of_week else None,
        target_muscles=payload.target_muscles,
        notes=payload.notes,
    )
    return _plan_out(plan, _available(db, user))


@router.get("/workouts/{workout_id}", response_model=PlanOut)
def get_workout(
    workout_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    plan = PlanRepo(db, user.id).require(workout_id)
    return _plan_out(plan, _available(db, user))


@router.put("/workouts/{workout_id}", response_model=PlanOut)
def update_workout(
    workout_id: uuid.UUID,
    payload: PlanUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    repo = PlanRepo(db, user.id)
    plan = repo.require(workout_id)
    data = payload.model_dump(exclude_unset=True)

    if data.pop("clear_day", False):
        plan.day_of_week = None
    elif "day_of_week" in data and data["day_of_week"] is not None:
        # Sec 7.2 - moving a workout between days is one field, not a rebuild.
        plan.day_of_week = data["day_of_week"].value
    data.pop("day_of_week", None)

    for key, value in data.items():
        if value is not None or key == "notes":
            setattr(plan, key, value)
    db.flush()
    return _plan_out(plan, _available(db, user))


@router.delete("/workouts/{workout_id}", status_code=204)
def delete_workout(
    workout_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Sec 7.2 - archived, so sessions performed from it survive."""
    repo = PlanRepo(db, user.id)
    repo.archive(repo.require(workout_id))


@router.post("/workouts/{workout_id}/exercises", response_model=PlanExerciseOut,
             status_code=201)
def add_exercise(
    workout_id: uuid.UUID,
    payload: PlanExerciseIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    repo = PlanRepo(db, user.id)
    plan = repo.require(workout_id)

    exercise = exercise_repo.get(db, user_id=user.id, exercise_id=payload.exercise_id)
    if exercise is None:
        raise ValidationFailed("No such exercise.", code="unknown_exercise")

    row = repo.add_exercise(
        plan,
        exercise_id=exercise.id,
        planned_sets=payload.planned_sets,
        planned_reps_min=payload.planned_reps_min,
        planned_reps_max=payload.planned_reps_max,
        planned_weight_kg=to_storage(payload.planned_weight, _unit(db, user)),
        planned_rir=payload.planned_rir,
        superset_group=payload.superset_group,
        notes=payload.notes,
    )
    db.flush()
    db.refresh(row)
    out = PlanExerciseOut.model_validate(row)
    missing = exercise_repo.missing_equipment(exercise, _available(db, user))
    out.exercise.compatible = not missing
    out.exercise.missing_equipment = missing
    return out


@router.put("/workouts/{workout_id}/exercises/{we_id}", response_model=PlanExerciseOut)
def update_exercise(
    workout_id: uuid.UUID,
    we_id: uuid.UUID,
    payload: PlanExerciseUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    repo = PlanRepo(db, user.id)
    plan = repo.require(workout_id)
    row = repo.get_exercise(plan, we_id)

    data = payload.model_dump(exclude_unset=True)
    if "planned_weight" in data:
        row.planned_weight_kg = to_storage(data.pop("planned_weight"), _unit(db, user))
    for key, value in data.items():
        setattr(row, key, value)

    if (
        row.planned_reps_min is not None
        and row.planned_reps_max is not None
        and row.planned_reps_min > row.planned_reps_max
    ):
        raise ValidationFailed("Minimum reps cannot exceed maximum reps.")

    db.flush()
    return PlanExerciseOut.model_validate(row)


@router.delete("/workouts/{workout_id}/exercises/{we_id}", status_code=204)
def remove_exercise(
    workout_id: uuid.UUID,
    we_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    repo = PlanRepo(db, user.id)
    repo.remove_exercise(repo.require(workout_id), we_id)


@router.post("/workouts/{workout_id}/reorder", response_model=PlanOut)
def reorder(
    workout_id: uuid.UUID,
    payload: ReorderIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    repo = PlanRepo(db, user.id)
    plan = repo.require(workout_id)
    repo.reorder(plan, payload.exercise_ids)
    db.refresh(plan)
    return _plan_out(repo.require(workout_id), _available(db, user))
