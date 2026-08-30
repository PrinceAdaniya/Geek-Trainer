"""The validation pipeline. SPECIFICATIONS.MD 21.3.

A returned id outside the candidate set is a failure, not a warning.
"""

from __future__ import annotations

import uuid

from app.ai.candidates import CandidateSet
from app.ai.schemas import GeneratedWorkout, SubstitutionResult
from app.core.errors import AppError

MAX_EXERCISES = 20
MINUTES_PER_SET = 3


class AIValidationError(AppError):
    status_code = 422
    code = "ai_validation_failed"


def validate_workout(
    workout: GeneratedWorkout,
    candidates: CandidateSet,
    *,
    session_minutes: int | None = None,
) -> list[str]:
    """Returns the problems. Empty means the proposal is safe to show."""
    problems: list[str] = []
    allowed = candidates.ids

    seen: set[uuid.UUID] = set()
    for row in workout.exercises:
        if row.exercise_id not in allowed:
            problems.append(f"exercise {row.exercise_id} was not in the candidate list")
        if row.exercise_id in seen:
            problems.append(f"exercise {row.exercise_id} appears twice")
        seen.add(row.exercise_id)
        if row.reps_min > row.reps_max:
            problems.append("a rep range runs backwards")

    if len(workout.exercises) > MAX_EXERCISES:
        problems.append(f"{len(workout.exercises)} exercises is more than a session")

    if session_minutes:
        planned = sum(row.sets for row in workout.exercises) * MINUTES_PER_SET
        if planned > session_minutes * 1.25:
            problems.append(
                f"about {planned} minutes of work against a {session_minutes} minute session"
            )
    return problems


def validate_substitutions(
    result: SubstitutionResult, candidates: CandidateSet
) -> list[str]:
    allowed = candidates.ids
    return [
        f"exercise {row.exercise_id} was not in the candidate list"
        for row in result.alternatives
        if row.exercise_id not in allowed
    ]
