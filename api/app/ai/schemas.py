"""Structured-output contracts. PLAN.md D10.

These Pydantic models are the schema the model is constrained to, and the
schema the backend validates against - one definition, so the two cannot drift.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class PlannedExercise(BaseModel):
    """The model picks an id from the candidate list; it never names a
    movement (PLAN.md D11)."""

    exercise_id: uuid.UUID
    sets: int = Field(ge=1, le=10)
    reps_min: int = Field(ge=1, le=100)
    reps_max: int = Field(ge=1, le=100)
    rationale: str = Field(max_length=200)


class GeneratedWorkout(BaseModel):
    name: str = Field(max_length=80)
    target_muscles: list[str] = Field(default_factory=list, max_length=6)
    exercises: list[PlannedExercise] = Field(min_length=1, max_length=20)
    notes: str = Field(default="", max_length=500)


class RankedSubstitution(BaseModel):
    exercise_id: uuid.UUID
    why: str = Field(max_length=200)


class SubstitutionResult(BaseModel):
    alternatives: list[RankedSubstitution] = Field(min_length=1, max_length=8)


class AnalysisResult(BaseModel):
    """Sec 19 - observation and interpretation are separated in the schema, so
    the model cannot blur them in prose."""

    observed: list[str] = Field(min_length=1, max_length=8)
    interpretation: list[str] = Field(default_factory=list, max_length=6)
    suggestion: str = Field(default="", max_length=400)
    enough_data: bool = True
