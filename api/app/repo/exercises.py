"""Exercise catalogue queries.

The catalogue is shared, so this is not a UserScoped repo - but a user's own
custom exercises are private (Sec 5.4), which makes visibility part of every
query here rather than something a route decides.
"""

from __future__ import annotations

import base64
import uuid
from dataclasses import dataclass

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import Session

from app.domain.enums import BODY_PART_MUSCLES, IMPLICIT_EQUIPMENT
from app.domain.models import Exercise
from app.ingest.mapping import normalize_name

DEFAULT_PAGE_SIZE = 30
MAX_PAGE_SIZE = 100


def encode_cursor(exercise: Exercise) -> str:
    raw = f"{exercise.name_normalized}\x1f{exercise.id}"
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[str, uuid.UUID] | None:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        name, _, ident = base64.urlsafe_b64decode(padded).decode().partition("\x1f")
        return name, uuid.UUID(ident)
    except Exception:
        return None


@dataclass
class ExerciseFilters:
    q: str | None = None
    body_part: str | None = None
    muscle: str | None = None
    equipment: list[str] | None = None      # the user's available equipment
    difficulty: str | None = None
    type: str | None = None
    include_incompatible: bool = False
    include_secondary: bool = True


def visible_to(user_id: uuid.UUID) -> Select:
    """Sec 5.4 - the shared catalogue plus this user's own exercises, and
    nobody else's."""
    return select(Exercise).where(
        Exercise.is_archived.is_(False),
        or_(Exercise.is_custom.is_(False), Exercise.owner_user_id == user_id),
    )


def compatible_clause(available: list[str]):
    """A1 / Sec 6.1 - set containment, not intersection.

    An exercise needing barbell + bench is NOT compatible for a user who owns
    only a barbell. `<@` is 'is contained by', which is exactly that rule; an
    overlap operator here is the single most common bug in this feature.
    """
    equipment = sorted(set(available) | {IMPLICIT_EQUIPMENT})
    return Exercise.equipment.contained_by(equipment)


def _apply(stmt: Select, filters: ExerciseFilters) -> Select:
    if filters.body_part:
        muscles = BODY_PART_MUSCLES.get(filters.body_part, ())
        stmt = stmt.where(
            or_(
                Exercise.body_part == filters.body_part,
                Exercise.primary_muscle.in_(muscles) if muscles else False,
            )
        )

    if filters.muscle:
        if filters.include_secondary:
            stmt = stmt.where(
                or_(
                    Exercise.primary_muscle == filters.muscle,
                    Exercise.secondary_muscles.any(filters.muscle),
                )
            )
        else:
            stmt = stmt.where(Exercise.primary_muscle == filters.muscle)

    if filters.difficulty:
        stmt = stmt.where(Exercise.difficulty == filters.difficulty)

    if filters.type:
        stmt = stmt.where(Exercise.type == filters.type)

    if filters.q:
        needle = f"%{normalize_name(filters.q)}%"
        stmt = stmt.where(
            or_(
                Exercise.name_normalized.like(needle),
                func.array_to_string(Exercise.aliases, " ").ilike(needle),
            )
        )

    if filters.equipment is not None and not filters.include_incompatible:
        stmt = stmt.where(compatible_clause(filters.equipment))

    return stmt


def search(
    db: Session,
    *,
    user_id: uuid.UUID,
    filters: ExerciseFilters,
    cursor: str | None = None,
    limit: int = DEFAULT_PAGE_SIZE,
) -> tuple[list[Exercise], str | None]:
    limit = max(1, min(limit, MAX_PAGE_SIZE))
    stmt = _apply(visible_to(user_id), filters)

    if cursor:
        decoded = decode_cursor(cursor)
        if decoded:
            name, ident = decoded
            stmt = stmt.where(
                or_(
                    Exercise.name_normalized > name,
                    and_(Exercise.name_normalized == name, Exercise.id > ident),
                )
            )

    stmt = stmt.order_by(Exercise.name_normalized, Exercise.id).limit(limit + 1)
    rows = list(db.execute(stmt).scalars())

    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        next_cursor = encode_cursor(rows[-1])
    return rows, next_cursor


def count(db: Session, *, user_id: uuid.UUID, filters: ExerciseFilters) -> int:
    stmt = _apply(visible_to(user_id), filters).with_only_columns(func.count(Exercise.id))
    return int(db.execute(stmt.order_by(None)).scalar_one())


def get(db: Session, *, user_id: uuid.UUID, exercise_id: uuid.UUID) -> Exercise | None:
    return db.execute(
        visible_to(user_id).where(Exercise.id == exercise_id)
    ).scalar_one_or_none()


def get_many(db: Session, *, user_id: uuid.UUID, ids: list[uuid.UUID]) -> list[Exercise]:
    if not ids:
        return []
    return list(db.execute(visible_to(user_id).where(Exercise.id.in_(ids))).scalars())


def missing_equipment(exercise: Exercise, available: list[str]) -> list[str]:
    """Sec 6.1 - incompatible exercises are shown with the reason named, never
    silently hidden."""
    have = set(available) | {IMPLICIT_EQUIPMENT}
    return sorted(set(exercise.equipment) - have)


def name_taken(db: Session, *, user_id: uuid.UUID, name: str,
               exclude_id: uuid.UUID | None = None) -> bool:
    stmt = visible_to(user_id).where(Exercise.name_normalized == normalize_name(name))
    if exclude_id:
        stmt = stmt.where(Exercise.id != exclude_id)
    return db.execute(stmt.limit(1)).scalar_one_or_none() is not None


def create_custom(db: Session, *, user_id: uuid.UUID, **fields) -> Exercise:
    exercise = Exercise(
        source="custom",
        source_id=f"user:{user_id}:{normalize_name(fields['name'])}",
        is_custom=True,
        owner_user_id=user_id,
        name_normalized=normalize_name(fields["name"]),
        **fields,
    )
    db.add(exercise)
    db.flush()
    return exercise
