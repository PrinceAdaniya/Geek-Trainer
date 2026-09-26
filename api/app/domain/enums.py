"""Canonical vocabularies. SPECIFICATIONS.MD Sec 4, 5.3, 8.1, 10.2, 10.3."""

from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


class Unit(StrEnum):
    KG = "kg"
    LB = "lb"


class WeekStart(StrEnum):
    MONDAY = "monday"
    SUNDAY = "sunday"


class TrainingExperience(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class TrainingGoal(StrEnum):
    STRENGTH = "strength"
    HYPERTROPHY = "hypertrophy"
    ENDURANCE = "endurance"
    GENERAL = "general"
    FAT_LOSS = "fat_loss"


class Difficulty(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class ExerciseType(StrEnum):
    COMPOUND = "compound"
    ISOLATION = "isolation"
    CARDIO = "cardio"
    MOBILITY = "mobility"
    OTHER = "other"


class MetricType(StrEnum):
    """Sec 10.2 - decides which set fields are required and how volume works."""

    WEIGHT_REPS = "weight_reps"
    BODYWEIGHT_REPS = "bodyweight_reps"
    WEIGHTED_BODYWEIGHT = "weighted_bodyweight"
    TIME = "time"
    DISTANCE = "distance"
    TIME_DISTANCE = "time_distance"


class SetType(StrEnum):
    """Sec 10.3. WARMUP is excluded from volume, charts and PRs."""

    WARMUP = "warmup"
    WORKING = "working"
    DROP_SET = "drop_set"
    FAILURE = "failure"
    REST_PAUSE = "rest_pause"
    AMRAP = "amrap"
    BACKOFF = "backoff"
    OTHER = "other"


NON_COUNTING_SET_TYPES = frozenset({SetType.WARMUP})


class SessionStatus(StrEnum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DayOfWeek(StrEnum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class ExerciseSource(StrEnum):
    EXERCISEDB = "exercisedb"
    WGER = "wger"
    CUSTOM = "custom"


class RecordType(StrEnum):
    """Sec 15."""

    HEAVIEST_WEIGHT = "heaviest_weight"
    MOST_REPS_AT_WEIGHT = "most_reps_at_weight"
    HIGHEST_SESSION_VOLUME = "highest_session_volume"
    BEST_E1RM = "best_e1rm"
    LONGEST_DURATION = "longest_duration"
    FURTHEST_DISTANCE = "furthest_distance"


class TicketCategory(StrEnum):
    EQUIPMENT = "equipment"
    CLEANLINESS = "cleanliness"
    STAFF = "staff"
    CLASSES = "classes"
    MEMBERSHIP = "membership"
    FACILITIES = "facilities"
    SAFETY = "safety"
    OTHER = "other"


class TicketPriority(StrEnum):
    NORMAL = "normal"
    URGENT = "urgent"


class TicketStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class LeadKind(StrEnum):
    FREE_PASS = "free_pass"
    TOUR = "tour"
    MEMBERSHIP = "membership"


class LeadStatus(StrEnum):
    NEW = "new"
    CONTACTED = "contacted"
    JOINED = "joined"
    CLOSED = "closed"

# Sec 4 - the canonical equipment list. Everything from an external source must
# map into this through app/ingest/mapping.py.
EQUIPMENT = (
    "dumbbell",
    "barbell",
    "bench",
    "cable",
    "machine",
    "smith-machine",
    "pull-up-bar",
    "dip-bars",
    "kettlebell",
    "resistance-band",
    "ez-bar",
    "medicine-ball",
    "stability-ball",
    "bodyweight",
)
EQUIPMENT_SET = frozenset(EQUIPMENT)

# Sec 4 - always available, cannot be deselected.
IMPLICIT_EQUIPMENT = "bodyweight"


# Sec 4, Sec 6 - canonical body parts and muscles. External sources map into
# these through app/ingest/mapping.py; an unmapped value is a data error.
BODY_PARTS = (
    "chest",
    "back",
    "shoulders",
    "arms",
    "legs",
    "core",
    "full-body",
    "cardio",
)
BODY_PART_SET = frozenset(BODY_PARTS)

MUSCLES = (
    # chest
    "pectorals",
    # back
    "lats", "traps", "rhomboids", "lower-back", "teres-major",
    # shoulders
    "front-delts", "side-delts", "rear-delts", "rotator-cuff",
    # arms
    "biceps", "triceps", "forearms",
    # legs
    "quads", "hamstrings", "glutes", "calves", "adductors", "abductors",
    "hip-flexors",
    # core
    "abs", "obliques", "transverse-abdominis",
    # other
    "neck", "cardiovascular",
)
MUSCLE_SET = frozenset(MUSCLES)

# Which body part a muscle belongs to, so a "train back" request can expand to
# the muscles that means.
MUSCLE_BODY_PART = {
    "pectorals": "chest",
    "lats": "back", "traps": "back", "rhomboids": "back",
    "lower-back": "back", "teres-major": "back",
    "front-delts": "shoulders", "side-delts": "shoulders",
    "rear-delts": "shoulders", "rotator-cuff": "shoulders",
    "biceps": "arms", "triceps": "arms", "forearms": "arms",
    "quads": "legs", "hamstrings": "legs", "glutes": "legs",
    "calves": "legs", "adductors": "legs", "abductors": "legs",
    "hip-flexors": "legs",
    "abs": "core", "obliques": "core", "transverse-abdominis": "core",
    "neck": "full-body", "cardiovascular": "cardio",
}

BODY_PART_MUSCLES: dict[str, tuple[str, ...]] = {}
for _muscle, _part in MUSCLE_BODY_PART.items():
    BODY_PART_MUSCLES[_part] = BODY_PART_MUSCLES.get(_part, ()) + (_muscle,)
