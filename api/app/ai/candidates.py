"""Retrieval-constrained generation. PLAN.md D11, SPECIFICATIONS.MD 21.1.

"The AI must not invent exercise names" is unenforceable as a prompt
instruction. Constraining the output space to ids we supplied makes it
structurally impossible, and this module is what supplies them.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.domain.enums import BODY_PART_MUSCLES
from app.domain.models import Exercise
from app.repo import exercises as exercise_repo

MAX_CANDIDATES = 60


@dataclass
class CandidateSet:
    rows: list[Exercise]

    @property
    def ids(self) -> set[uuid.UUID]:
        return {row.id for row in self.rows}

    def as_table(self) -> str:
        """A compact table, because every token here is paid for on every
        request and the model only needs enough to choose."""
        lines = ["id | name | equipment | primary | type | difficulty"]
        for row in self.rows:
            lines.append(
                f"{row.id} | {row.name} | {','.join(row.equipment)} | "
                f"{row.primary_muscle} | {row.type} | {row.difficulty}"
            )
        return "\n".join(lines)


def for_targets(
    db: Session,
    *,
    user_id: uuid.UUID,
    equipment: list[str],
    targets: list[str],
    difficulty: str | None = None,
    limit: int = MAX_CANDIDATES,
) -> CandidateSet:
    """Everything compatible with this user's kit for these muscles or body
    parts, capped so the prompt stays small."""
    muscles: list[str] = []
    for target in targets:
        muscles.extend(BODY_PART_MUSCLES.get(target, (target,)))

    seen: dict[uuid.UUID, Exercise] = {}
    per_muscle = max(4, limit // max(len(muscles), 1))

    for muscle in muscles:
        rows, _ = exercise_repo.search(
            db,
            user_id=user_id,
            filters=exercise_repo.ExerciseFilters(
                muscle=muscle, equipment=equipment, difficulty=difficulty
            ),
            limit=per_muscle,
        )
        for row in rows:
            seen.setdefault(row.id, row)
        if len(seen) >= limit:
            break

    # Compounds first, so a truncated list still contains the movements a plan
    # should be built around.
    ordered = sorted(
        seen.values(), key=lambda r: (0 if r.type == "compound" else 1, r.name)
    )
    return CandidateSet(rows=ordered[:limit])


def alternatives_to(
    db: Session, *, user_id: uuid.UUID, exercise: Exercise, equipment: list[str],
    limit: int = 8,
) -> CandidateSet:
    """Sec 20 - deterministic candidates, so substitution works with the AI
    switched off."""
    rows, _ = exercise_repo.search(
        db,
        user_id=user_id,
        filters=exercise_repo.ExerciseFilters(
            muscle=exercise.primary_muscle, equipment=equipment
        ),
        limit=40,
    )
    others = [row for row in rows if row.id != exercise.id]

    def score(row: Exercise) -> tuple:
        shared = len(set(row.secondary_muscles) & set(exercise.secondary_muscles))
        return (
            0 if row.type == exercise.type else 1,
            0 if row.difficulty == exercise.difficulty else 1,
            -shared,
            row.name,
        )

    return CandidateSet(rows=sorted(others, key=score)[:limit])
