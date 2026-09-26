"""Profile, settings and bodyweight. SPECIFICATIONS.MD Sec 3.4, Sec 4."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.units import to_storage
from app.db import get_db
from app.deps import current_user
from app.domain.enums import Unit
from app.domain.models import User
from app.domain.schemas import (
    BodyweightIn,
    BodyweightOut,
    ProfileOut,
    ProfileUpdate,
    SettingsOut,
)
from app.repo.users import BodyweightRepo, SettingsRepo

router = APIRouter(tags=["profile"])

_PROFILE_FIELDS = (
    "name",
    "age",
    "sex",
    "training_experience",
    "training_goals",
    "preferred_training_days",
    "preferred_session_duration_minutes",
    "injury_notes",
)
_SETTINGS_FIELDS = (
    "unit_preference",
    "timezone",
    "week_start",
    "default_rest_seconds",
    "available_equipment",
    "weight_increments",
)


def build_profile(db: Session, user: User) -> ProfileOut:
    settings = SettingsRepo(db, user.id).get()
    latest = BodyweightRepo(db, user.id).latest()
    return ProfileOut(
        id=user.id,
        email=user.email,
        name=user.name,
        age=user.age,
        sex=user.sex,
        training_experience=user.training_experience,
        training_goals=user.training_goals or [],
        preferred_training_days=user.preferred_training_days or [],
        preferred_session_duration_minutes=user.preferred_session_duration_minutes,
        injury_notes=user.injury_notes,
        created_at=user.created_at,
        settings=SettingsOut.model_validate(settings),
        latest_bodyweight_kg=latest.weight_kg if latest else None,
        is_staff=user.is_staff,
    )


@router.get("/profile", response_model=ProfileOut)
def get_profile(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return build_profile(db, user)


@router.put("/profile", response_model=ProfileOut)
def update_profile(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    data = payload.model_dump(exclude_unset=True)

    for field in _PROFILE_FIELDS:
        if field in data:
            value = data[field]
            if field == "training_goals" and value is not None:
                value = [str(v) for v in value]
            setattr(user, field, value)

    settings_update = {
        field: data[field] for field in _SETTINGS_FIELDS if field in data
    }
    if settings_update:
        if "unit_preference" in settings_update and settings_update["unit_preference"]:
            settings_update["unit_preference"] = str(settings_update["unit_preference"])
        if "week_start" in settings_update and settings_update["week_start"]:
            settings_update["week_start"] = str(settings_update["week_start"])
        if "weight_increments" in settings_update and settings_update["weight_increments"]:
            settings_update["weight_increments"] = {
                k: str(v) for k, v in settings_update["weight_increments"].items()
            }
        SettingsRepo(db, user.id).upsert(**settings_update)

    db.flush()
    return build_profile(db, user)


@router.get("/profile/bodyweight", response_model=list[BodyweightOut])
def list_bodyweight(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return BodyweightRepo(db, user.id).list()


@router.post("/profile/bodyweight", response_model=BodyweightOut, status_code=201)
def add_bodyweight(
    payload: BodyweightIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    settings = SettingsRepo(db, user.id).get()
    unit = payload.unit or Unit(settings.unit_preference)
    return BodyweightRepo(db, user.id).upsert(
        entry_date=payload.date, weight_kg=to_storage(payload.weight, unit)
    )
