"""Pydantic request/response models.

These double as the OpenAPI contract that generates the frontend's types
(PLAN.md D13), so field names here are the field names the client sees.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.domain.enums import (
    BODY_PART_SET,
    EQUIPMENT_SET,
    IMPLICIT_EQUIPMENT,
    MUSCLE_SET,
    Difficulty,
    ExerciseType,
    MetricType,
    TrainingExperience,
    TrainingGoal,
    Unit,
    WeekStart,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- auth -----------------------------------------------------------------


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=120)
    timezone: str = Field(default="UTC", max_length=64)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=10)
    password: str = Field(min_length=1)


class MessageResponse(BaseModel):
    message: str


# --- profile --------------------------------------------------------------


class SettingsOut(ORMModel):
    unit_preference: Unit
    timezone: str
    week_start: WeekStart
    default_rest_seconds: int
    available_equipment: list[str]
    weight_increments: dict


class ProfileOut(ORMModel):
    id: uuid.UUID
    email: EmailStr
    name: str
    age: int | None = None
    sex: str | None = None
    training_experience: TrainingExperience | None = None
    training_goals: list[TrainingGoal] = []
    preferred_training_days: list[str] = []
    preferred_session_duration_minutes: int | None = None
    injury_notes: str | None = None
    created_at: datetime
    settings: SettingsOut
    latest_bodyweight_kg: Decimal | None = None


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    age: int | None = Field(default=None, ge=10, le=120)
    sex: str | None = Field(default=None, max_length=20)
    training_experience: TrainingExperience | None = None
    training_goals: list[TrainingGoal] | None = None
    preferred_training_days: list[str] | None = None
    preferred_session_duration_minutes: int | None = Field(default=None, ge=5, le=600)
    injury_notes: str | None = Field(default=None, max_length=4000)

    unit_preference: Unit | None = None
    timezone: str | None = Field(default=None, max_length=64)
    week_start: WeekStart | None = None
    default_rest_seconds: int | None = Field(default=None, ge=0, le=3600)
    available_equipment: list[str] | None = None
    weight_increments: dict[str, Decimal] | None = None

    @field_validator("available_equipment")
    @classmethod
    def _canonical_equipment(cls, value: list[str] | None) -> list[str] | None:
        """Sec 4 - canonical ids only, and bodyweight is always available."""
        if value is None:
            return None
        unknown = sorted(set(value) - EQUIPMENT_SET)
        if unknown:
            raise ValueError(f"unknown equipment: {', '.join(unknown)}")
        return sorted(set(value) | {IMPLICIT_EQUIPMENT})

    @field_validator("timezone")
    @classmethod
    def _known_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"unknown timezone: {value}") from exc
        return value


# --- bodyweight -----------------------------------------------------------


class BodyweightIn(BaseModel):
    date: date
    weight: Decimal = Field(gt=0, lt=2000)
    unit: Unit | None = None  # defaults to the user's preference


class BodyweightOut(ORMModel):
    id: uuid.UUID
    date: date
    weight_kg: Decimal
    source: str


# --- exercises ------------------------------------------------------------


class ExerciseOut(ORMModel):
    id: uuid.UUID
    name: str
    body_part: str
    primary_muscle: str
    secondary_muscles: list[str]
    equipment: list[str]
    difficulty: Difficulty
    type: ExerciseType
    metric_type: MetricType
    bodyweight_load_factor: Decimal | None = None
    default_rest_seconds: int
    instructions: list[str]
    image_url: str | None = None
    gif_url: str | None = None
    video_url: str | None = None
    is_custom: bool

    # Sec 6.1 - an incompatible exercise is shown with the reason named.
    compatible: bool = True
    missing_equipment: list[str] = []


class ExercisePage(BaseModel):
    data: list[ExerciseOut]
    next_cursor: str | None = None
    total: int


class CustomExerciseIn(BaseModel):
    """Sec 5.4 - metric_type and equipment are required, because guessing them
    silently breaks volume (Sec 13.1)."""

    name: str = Field(min_length=2, max_length=200)
    primary_muscle: str
    secondary_muscles: list[str] = []
    equipment: list[str]
    metric_type: MetricType
    difficulty: Difficulty = Difficulty.BEGINNER
    type: ExerciseType = ExerciseType.COMPOUND
    bodyweight_load_factor: Decimal | None = Field(default=None, ge=0, le=2)
    default_rest_seconds: int = Field(default=120, ge=0, le=3600)
    instructions: list[str] = []

    @field_validator("primary_muscle")
    @classmethod
    def _known_primary(cls, value: str) -> str:
        if value not in MUSCLE_SET:
            raise ValueError(f"unknown muscle: {value}")
        return value

    @field_validator("secondary_muscles")
    @classmethod
    def _known_secondary(cls, value: list[str]) -> list[str]:
        unknown = sorted(set(value) - MUSCLE_SET)
        if unknown:
            raise ValueError(f"unknown muscles: {', '.join(unknown)}")
        return value

    @field_validator("equipment")
    @classmethod
    def _known_equipment(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("at least one equipment item (use 'bodyweight')")
        unknown = sorted(set(value) - EQUIPMENT_SET)
        if unknown:
            raise ValueError(f"unknown equipment: {', '.join(unknown)}")
        return sorted(set(value))


class CustomExerciseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    secondary_muscles: list[str] | None = None
    equipment: list[str] | None = None
    difficulty: Difficulty | None = None
    default_rest_seconds: int | None = Field(default=None, ge=0, le=3600)
    instructions: list[str] | None = None
    bodyweight_load_factor: Decimal | None = Field(default=None, ge=0, le=2)


class VocabularyOut(BaseModel):
    """Everything the client needs to build filter controls without hardcoding
    our vocabularies."""

    equipment: list[str]
    body_parts: list[str]
    muscles: list[str]
    body_part_muscles: dict[str, list[str]]
    difficulties: list[str]
    types: list[str]
    metric_types: list[str]
    set_types: list[str]
