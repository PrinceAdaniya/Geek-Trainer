"""AI endpoints. SPECIFICATIONS.MD Sec 17-21.

Two rules hold everywhere in this file:
  - the AI proposes; nothing here writes to the database (Sec 17.2)
  - every feature has a deterministic path, taken whenever the model is
    unavailable, over budget, or produces something that fails validation
"""

from __future__ import annotations

import logging
import uuid
from datetime import timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai import fallback, prompts
from app.ai.candidates import alternatives_to, for_targets
from app.ai.client import LLMUnavailable, get_client
from app.ai.schemas import AnalysisResult, GeneratedWorkout, SubstitutionResult
from app.ai.validate import validate_substitutions, validate_workout
from app.core.clock import utcnow
from app.core.errors import NotFound, RateLimited, ValidationFailed
from app.core.formulas import epley_1rm
from app.db import get_db
from app.deps import current_user
from app.domain.enums import NON_COUNTING_SET_TYPES, SessionStatus
from app.domain.models import Exercise, SetRecord, SyncMutation, User, WorkoutSession
from app.domain.schemas import ExerciseOut
from app.repo import exercises as exercise_repo
from app.repo.users import SettingsRepo

log = logging.getLogger("geektrainer.ai")
router = APIRouter(prefix="/ai", tags=["ai"])

# Sec 21.5. Deliberately conservative until Sec 32 Q2 is answered.
DAILY_REQUEST_BUDGET = 40
_EXCLUDED = [t.value for t in NON_COUNTING_SET_TYPES]


class ProposedExercise(BaseModel):
    exercise: ExerciseOut
    sets: int
    reps_min: int
    reps_max: int
    rationale: str


class WorkoutProposal(BaseModel):
    """A proposal, not a workout. Sec 17.2 - the user saves it or does not."""

    name: str
    target_muscles: list[str]
    exercises: list[ProposedExercise]
    notes: str
    source: str = Field(description="'ai' or 'rules'")
    warnings: list[str] = Field(default_factory=list)


class GenerateRequest(BaseModel):
    targets: list[str] = Field(min_length=1, max_length=6)
    goal: str = "general"
    session_minutes: int = Field(default=60, ge=10, le=240)
    equipment: list[str] | None = None


class SubstituteRequest(BaseModel):
    exercise_id: uuid.UUID


class Alternative(BaseModel):
    exercise: ExerciseOut
    why: str


class SubstituteResponse(BaseModel):
    replacing: ExerciseOut
    alternatives: list[Alternative]
    source: str


class AnalyseRequest(BaseModel):
    exercise_id: uuid.UUID
    days: int = Field(default=90, ge=7, le=730)


class AnalyseResponse(BaseModel):
    exercise_name: str
    sessions: int
    observed: list[str]
    interpretation: list[str]
    suggestion: str
    enough_data: bool
    source: str


class BudgetResponse(BaseModel):
    ai_configured: bool
    used_today: int
    daily_limit: int
    remaining: int


def _available(db: Session, user: User) -> list[str]:
    settings = SettingsRepo(db, user.id).get()
    return list(settings.available_equipment) if settings else []


def _spend(db: Session, user: User) -> int:
    """Sec 21.5 - counted from the same table sync uses, so there is one
    record of what a user has asked the server to do."""
    since = utcnow() - timedelta(days=1)
    used = db.execute(
        select(func.count())
        .select_from(SyncMutation)
        .where(
            SyncMutation.user_id == user.id,
            SyncMutation.type.like("ai.%"),
            SyncMutation.applied_at >= since,
        )
    ).scalar_one()
    if used >= DAILY_REQUEST_BUDGET:
        raise RateLimited(
            "You have reached today's limit for generated workouts. Try again tomorrow.",
            code="ai_budget_exhausted",
        )
    db.add(
        SyncMutation(id=uuid.uuid4(), user_id=user.id, type="ai.request", result="applied")
    )
    db.flush()
    return int(used) + 1


@router.get("/budget", response_model=BudgetResponse)
def budget(db: Session = Depends(get_db), user: User = Depends(current_user)):
    since = utcnow() - timedelta(days=1)
    used = int(
        db.execute(
            select(func.count())
            .select_from(SyncMutation)
            .where(
                SyncMutation.user_id == user.id,
                SyncMutation.type.like("ai.%"),
                SyncMutation.applied_at >= since,
            )
        ).scalar_one()
    )
    return BudgetResponse(
        ai_configured=get_client().available,
        used_today=used,
        daily_limit=DAILY_REQUEST_BUDGET,
        remaining=max(0, DAILY_REQUEST_BUDGET - used),
    )


@router.post("/workout", response_model=WorkoutProposal)
def generate(
    payload: GenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    equipment = payload.equipment if payload.equipment is not None else _available(db, user)
    candidates = for_targets(
        db, user_id=user.id, equipment=equipment, targets=payload.targets
    )
    if not candidates.rows:
        raise ValidationFailed(
            "Nothing in your equipment trains that. Add equipment, or pick "
            "another target.",
            code="no_candidates",
        )

    warnings: list[str] = []
    workout: GeneratedWorkout | None = None
    source = "rules"

    client = get_client()
    if client.available:
        _spend(db, user)
        user_message = (
            f"Goal: {payload.goal}\n"
            f"Target muscles: {', '.join(payload.targets)}\n"
            f"Session length: {payload.session_minutes} minutes\n\n"
            f"Candidates:\n{candidates.as_table()}"
        )
        for attempt in range(2):
            try:
                proposed = client.structured(
                    system=prompts.GENERATE, user=user_message, schema=GeneratedWorkout
                )
            except LLMUnavailable as exc:
                # Operator detail, not member-facing: the plan below still gets built.
                log.warning("workout generation fell back to rules: %s", exc)
                break

            problems = validate_workout(
                proposed, candidates, session_minutes=payload.session_minutes
            )
            if not problems:
                workout, source = proposed, "ai"
                break
            if attempt == 0:
                # Sec 21.3 - exactly one repair round-trip, then the fallback.
                user_message += (
                    "\n\nYour previous answer was rejected:\n- "
                    + "\n- ".join(problems)
                    + "\nAnswer again, choosing only from the candidate list."
                )
            else:
                log.warning("generated workout failed validation twice; using rules")

    if workout is None:
        workout = fallback.generate_workout(
            candidates,
            targets=payload.targets,
            goal=payload.goal,
            session_minutes=payload.session_minutes,
        )

    by_id = {row.id: row for row in candidates.rows}
    return WorkoutProposal(
        name=workout.name,
        target_muscles=workout.target_muscles or payload.targets,
        exercises=[
            ProposedExercise(
                exercise=ExerciseOut.model_validate(by_id[row.exercise_id]),
                sets=row.sets,
                reps_min=row.reps_min,
                reps_max=row.reps_max,
                rationale=row.rationale,
            )
            for row in workout.exercises
            if row.exercise_id in by_id
        ],
        notes=workout.notes,
        source=source,
        warnings=warnings,
    )


@router.post("/substitute", response_model=SubstituteResponse)
def substitute(
    payload: SubstituteRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    exercise = exercise_repo.get(db, user_id=user.id, exercise_id=payload.exercise_id)
    if exercise is None:
        raise NotFound("No such exercise.")

    candidates = alternatives_to(
        db, user_id=user.id, exercise=exercise, equipment=_available(db, user)
    )
    if not candidates.rows:
        return SubstituteResponse(
            replacing=ExerciseOut.model_validate(exercise), alternatives=[], source="rules"
        )

    ranked = None
    source = "rules"
    client = get_client()
    if client.available:
        try:
            _spend(db, user)
            proposed = client.structured(
                system=prompts.SUBSTITUTE,
                user=(
                    f"Replacing: {exercise.name} "
                    f"({exercise.primary_muscle}, {','.join(exercise.equipment)})\n\n"
                    f"Candidates:\n{candidates.as_table()}"
                ),
                schema=SubstitutionResult,
            )
            if not validate_substitutions(proposed, candidates):
                ranked, source = proposed, "ai"
        except LLMUnavailable:
            ranked = None

    if ranked is None:
        ranked = fallback.rank_substitutions(candidates, replacing=exercise.name)

    by_id = {row.id: row for row in candidates.rows}
    return SubstituteResponse(
        replacing=ExerciseOut.model_validate(exercise),
        alternatives=[
            Alternative(exercise=ExerciseOut.model_validate(by_id[row.exercise_id]), why=row.why)
            for row in ranked.alternatives
            if row.exercise_id in by_id
        ],
        source=source,
    )


@router.post("/analyze", response_model=AnalyseResponse)
def analyse(
    payload: AnalyseRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    exercise = exercise_repo.get(db, user_id=user.id, exercise_id=payload.exercise_id)
    if exercise is None:
        raise NotFound("No such exercise.")

    rows = db.execute(
        select(
            WorkoutSession.date,
            func.max(SetRecord.weight_kg),
            func.max(SetRecord.reps),
            func.coalesce(func.sum(SetRecord.weight_kg * SetRecord.reps), Decimal(0)),
        )
        .join(WorkoutSession, SetRecord.session_id == WorkoutSession.id)
        .where(
            SetRecord.user_id == user.id,
            SetRecord.exercise_id == exercise.id,
            SetRecord.deleted_at.is_(None),
            SetRecord.set_type.notin_(_EXCLUDED),
            WorkoutSession.status == SessionStatus.COMPLETED.value,
            WorkoutSession.date >= (utcnow().date() - timedelta(days=payload.days)),
        )
        .group_by(WorkoutSession.date)
        .order_by(WorkoutSession.date)
    ).all()

    # Sec 19 - every number in the payload is computed here, never by the model.
    series = [
        {
            "date": day.isoformat(),
            "top_weight": float(weight or 0),
            "top_reps": int(reps or 0),
            "volume": float(volume or 0),
            "e1rm": float(epley_1rm(weight, reps) or 0) if weight and reps else 0.0,
        }
        for day, weight, reps, volume in rows
    ]

    result: AnalysisResult | None = None
    source = "rules"
    client = get_client()
    if client.available and len(series) >= 3:
        try:
            _spend(db, user)
            result = client.structured(
                system=prompts.ANALYSE,
                user=(
                    f"Exercise: {exercise.name}\nUnit: kg\n"
                    f"Sessions: {len(series)}\n\n{series}"
                ),
                schema=AnalysisResult,
            )
            source = "ai"
        except LLMUnavailable:
            result = None

    if result is None:
        result = fallback.analyse(series, exercise_name=exercise.name)

    return AnalyseResponse(
        exercise_name=exercise.name,
        sessions=len(series),
        observed=result.observed,
        interpretation=result.interpretation,
        suggestion=result.suggestion,
        enough_data=result.enough_data,
        source=source,
    )
