"""Export and deletion. SPECIFICATIONS.MD Sec 25."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.errors import NotAuthenticated
from app.core.security import verify_password
from app.db import get_db
from app.deps import current_user
from app.domain.models import (
    BodyweightEntry,
    Exercise,
    PersonalRecord,
    SessionExercise,
    SetRecord,
    User,
    WorkoutPlan,
    WorkoutSession,
)
from app.repo.guard import unscoped
from app.repo.users import SettingsRepo, revoke_all_auth_sessions

router = APIRouter(tags=["account"])


class DeleteRequest(BaseModel):
    password: str


def _collect(db: Session, user: User) -> dict:
    settings = SettingsRepo(db, user.id).get()
    sessions = db.execute(
        select(WorkoutSession).where(
            WorkoutSession.user_id == user.id, WorkoutSession.deleted_at.is_(None)
        )
    ).scalars().all()
    plans = db.execute(
        select(WorkoutPlan).where(WorkoutPlan.user_id == user.id)
    ).scalars().all()
    sets = db.execute(
        select(SetRecord).where(SetRecord.user_id == user.id)
    ).scalars().all()
    bodyweight = db.execute(
        select(BodyweightEntry).where(BodyweightEntry.user_id == user.id)
    ).scalars().all()

    return {
        "exported_at": utcnow().isoformat(),
        "profile": {
            "id": str(user.id), "email": user.email, "name": user.name,
            "created_at": user.created_at.isoformat(),
            "training_goals": list(user.training_goals or []),
            "settings": {
                "unit_preference": settings.unit_preference if settings else "kg",
                "timezone": settings.timezone if settings else "UTC",
                "week_start": settings.week_start if settings else "monday",
                "available_equipment": list(settings.available_equipment) if settings else [],
            },
        },
        "bodyweight": [
            {"date": row.date.isoformat(), "weight_kg": str(row.weight_kg),
             "source": row.source}
            for row in bodyweight
        ],
        "plans": [
            {"id": str(p.id), "name": p.name, "day_of_week": p.day_of_week,
             "target_muscles": list(p.target_muscles), "notes": p.notes,
             "archived": p.is_archived}
            for p in plans
        ],
        "sessions": [
            {"id": str(s.id), "name": s.name, "date": s.date.isoformat(),
             "status": s.status, "duration_seconds": s.duration_seconds,
             "notes": s.notes, "plan_snapshot": s.plan_snapshot}
            for s in sessions
        ],
        "sets": [
            {"id": str(row.id), "session_id": str(row.session_id),
             "exercise_id": str(row.exercise_id), "set_number": row.set_number,
             "weight_kg": str(row.weight_kg) if row.weight_kg is not None else None,
             "reps": row.reps, "duration_seconds": row.duration_seconds,
             "distance_m": str(row.distance_m) if row.distance_m is not None else None,
             "rir": row.rir, "rpe": str(row.rpe) if row.rpe is not None else None,
             "failure": row.failure, "set_type": row.set_type,
             "performed_at": row.performed_at.isoformat(),
             "deleted": row.deleted_at is not None}
            for row in sets
        ],
    }


@router.get("/account/export")
def export_json(db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Sec 25 - everything, in a format that is readable without this app."""
    payload = json.dumps(_collect(db, user), indent=1)
    stamp = utcnow().strftime("%Y-%m-%d")
    return StreamingResponse(
        io.BytesIO(payload.encode("utf-8")),
        media_type="application/json",
        headers={
            "content-disposition": f'attachment; filename="geek-trainer-{stamp}.json"'
        },
    )


@router.get("/account/export.csv")
def export_csv(db: Session = Depends(get_db), user: User = Depends(current_user)):
    """The set log as a spreadsheet, which is what people actually want."""
    rows = db.execute(
        select(SetRecord, WorkoutSession, Exercise)
        .join(WorkoutSession, SetRecord.session_id == WorkoutSession.id)
        .join(Exercise, SetRecord.exercise_id == Exercise.id)
        .where(SetRecord.user_id == user.id, SetRecord.deleted_at.is_(None))
        .order_by(WorkoutSession.date, SetRecord.performed_at)
    ).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["date", "session", "exercise", "set", "weight_kg", "reps",
         "duration_seconds", "distance_m", "rir", "rpe", "failure", "set_type"]
    )
    for row, session, exercise in rows:
        writer.writerow([
            session.date, session.name, exercise.name, row.set_number,
            row.weight_kg or "", row.reps or "", row.duration_seconds or "",
            row.distance_m or "", row.rir if row.rir is not None else "",
            row.rpe or "", "yes" if row.failure else "no", row.set_type,
        ])

    stamp = utcnow().strftime("%Y-%m-%d")
    return StreamingResponse(
        io.BytesIO(buffer.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={
            "content-disposition": f'attachment; filename="geek-trainer-sets-{stamp}.csv"'
        },
    )


@router.post("/account/delete", status_code=204)
def delete_account(
    payload: DeleteRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Sec 25 - confirmed by re-entering the password, and immediate.

    Everything the user owns goes. Their custom exercises go with them; the
    shared catalogue does not.
    """
    if not verify_password(user.password_hash, payload.password):
        raise NotAuthenticated("That password is not right.")

    user_id = user.id
    revoke_all_auth_sessions(db, user_id)

    with unscoped("account deletion removes every row this user owns"):
        session_ids = db.execute(
            select(WorkoutSession.id).where(WorkoutSession.user_id == user_id)
        ).scalars().all()
        db.execute(delete(PersonalRecord).where(PersonalRecord.user_id == user_id))
        db.execute(delete(SetRecord).where(SetRecord.user_id == user_id))
        if session_ids:
            db.execute(
                delete(SessionExercise).where(SessionExercise.session_id.in_(session_ids))
            )
        db.execute(delete(WorkoutSession).where(WorkoutSession.user_id == user_id))
        db.execute(delete(WorkoutPlan).where(WorkoutPlan.user_id == user_id))
        db.execute(delete(Exercise).where(Exercise.owner_user_id == user_id))
        db.execute(delete(User).where(User.id == user_id))
    db.flush()
