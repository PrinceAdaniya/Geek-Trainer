"""Exercise discovery. SPECIFICATIONS.MD Sec 6, Sec 5.4, Sec 23."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.errors import Conflict, NotFound, ValidationFailed
from app.core.formulas import quantize_factor
from app.db import get_db
from app.deps import current_user
from app.domain.enums import (
    BODY_PART_MUSCLES,
    BODY_PARTS,
    EQUIPMENT,
    MUSCLES,
    Difficulty,
    ExerciseType,
    MetricType,
    SetType,
)
from app.domain.models import Exercise, User
from app.domain.schemas import (
    CustomExerciseIn,
    CustomExerciseUpdate,
    ExerciseOut,
    ExercisePage,
    VocabularyOut,
)
from app.repo import exercises as repo
from app.repo.users import SettingsRepo

router = APIRouter(tags=["exercises"])


def _available_equipment(db: Session, user: User) -> list[str]:
    settings = SettingsRepo(db, user.id).get()
    return list(settings.available_equipment) if settings else []


def _to_out(exercise: Exercise, available: list[str]) -> ExerciseOut:
    missing = repo.missing_equipment(exercise, available)
    out = ExerciseOut.model_validate(exercise)
    out.compatible = not missing
    out.missing_equipment = missing
    return out


@router.get("/vocabulary", response_model=VocabularyOut)
def vocabulary():
    """So the client never hardcodes our canonical lists."""
    return VocabularyOut(
        equipment=list(EQUIPMENT),
        body_parts=list(BODY_PARTS),
        muscles=list(MUSCLES),
        body_part_muscles={k: list(v) for k, v in BODY_PART_MUSCLES.items()},
        difficulties=[d.value for d in Difficulty],
        types=[t.value for t in ExerciseType],
        metric_types=[m.value for m in MetricType],
        set_types=[s.value for s in SetType],
    )


@router.get("/exercises", response_model=ExercisePage)
def list_exercises(
    q: str | None = None,
    body_part: str | None = None,
    muscle: str | None = None,
    difficulty: Difficulty | None = None,
    type: ExerciseType | None = None,
    include_incompatible: bool = False,
    equipment: list[str] | None = Query(default=None),
    cursor: str | None = None,
    limit: int = Query(default=repo.DEFAULT_PAGE_SIZE, ge=1, le=repo.MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """`equipment` overrides the profile for this query - used by the planner to
    ask 'what could I do with only dumbbells today'."""
    available = equipment if equipment is not None else _available_equipment(db, user)

    filters = repo.ExerciseFilters(
        q=q,
        body_part=body_part,
        muscle=muscle,
        equipment=available,
        difficulty=difficulty.value if difficulty else None,
        type=type.value if type else None,
        include_incompatible=include_incompatible,
    )
    rows, next_cursor = repo.search(
        db, user_id=user.id, filters=filters, cursor=cursor, limit=limit
    )
    return ExercisePage(
        data=[_to_out(row, available) for row in rows],
        next_cursor=next_cursor,
        total=repo.count(db, user_id=user.id, filters=filters),
    )


@router.get("/exercises/{exercise_id}", response_model=ExerciseOut)
def get_exercise(
    exercise_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    exercise = repo.get(db, user_id=user.id, exercise_id=exercise_id)
    if exercise is None:
        # Sec 23.1 - another user's custom exercise is 404, not 403.
        raise NotFound("No such exercise.")
    return _to_out(exercise, _available_equipment(db, user))


@router.post("/exercises", response_model=ExerciseOut, status_code=201)
def create_exercise(
    payload: CustomExerciseIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if repo.name_taken(db, user_id=user.id, name=payload.name):
        raise Conflict(
            "You already have an exercise with that name.", code="exercise_name_taken"
        )

    data = payload.model_dump()
    metric = data["metric_type"]
    if metric in (MetricType.BODYWEIGHT_REPS, MetricType.WEIGHTED_BODYWEIGHT):
        # Sec 13.2 - a missing factor would report zero volume forever, so it
        # defaults to the full bodyweight rather than to nothing.
        data["bodyweight_load_factor"] = quantize_factor(
            data.get("bodyweight_load_factor") or 1
        )
    else:
        data["bodyweight_load_factor"] = None

    body_part = None
    from app.domain.enums import MUSCLE_BODY_PART

    body_part = MUSCLE_BODY_PART.get(data["primary_muscle"])
    if body_part is None:
        raise ValidationFailed("That muscle has no body part mapping.")

    exercise = repo.create_custom(
        db,
        user_id=user.id,
        body_part=body_part,
        difficulty=data["difficulty"].value if hasattr(data["difficulty"], "value") else data["difficulty"],
        type=data["type"].value if hasattr(data["type"], "value") else data["type"],
        metric_type=metric.value if hasattr(metric, "value") else metric,
        name=data["name"],
        primary_muscle=data["primary_muscle"],
        secondary_muscles=data["secondary_muscles"],
        equipment=data["equipment"],
        bodyweight_load_factor=data["bodyweight_load_factor"],
        default_rest_seconds=data["default_rest_seconds"],
        instructions=data["instructions"],
    )
    return _to_out(exercise, _available_equipment(db, user))


@router.put("/exercises/{exercise_id}", response_model=ExerciseOut)
def update_exercise(
    exercise_id: uuid.UUID,
    payload: CustomExerciseUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    exercise = repo.get(db, user_id=user.id, exercise_id=exercise_id)
    if exercise is None:
        raise NotFound("No such exercise.")
    if not exercise.is_custom or exercise.owner_user_id != user.id:
        raise ValidationFailed(
            "Only your own exercises can be edited.", code="not_editable"
        )

    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"]:
        from app.ingest.mapping import normalize_name

        if repo.name_taken(db, user_id=user.id, name=data["name"], exclude_id=exercise.id):
            raise Conflict("You already have an exercise with that name.",
                           code="exercise_name_taken")
        exercise.name_normalized = normalize_name(data["name"])

    if data.get("bodyweight_load_factor") is not None:
        data["bodyweight_load_factor"] = quantize_factor(data["bodyweight_load_factor"])

    for key, value in data.items():
        setattr(exercise, key, value.value if hasattr(value, "value") else value)
    db.flush()
    return _to_out(exercise, _available_equipment(db, user))


@router.delete("/exercises/{exercise_id}", status_code=204)
def delete_exercise(
    exercise_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Sec 16.1 - archived, not deleted, so past sessions never break."""
    exercise = repo.get(db, user_id=user.id, exercise_id=exercise_id)
    if exercise is None:
        raise NotFound("No such exercise.")
    if not exercise.is_custom or exercise.owner_user_id != user.id:
        raise ValidationFailed("Only your own exercises can be deleted.",
                               code="not_editable")
    exercise.is_archived = True
    db.flush()
