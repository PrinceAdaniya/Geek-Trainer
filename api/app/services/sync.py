"""Offline mutation replay. SPECIFICATIONS.MD Sec 12, PLAN.md D3.

The contract:
  - every mutation carries a client-generated id
  - applying the same id twice is a no-op, not a duplicate
  - a rejected mutation is reported back, never dropped silently
  - one bad mutation does not fail the batch

A3 is the acceptance criterion this exists to satisfy: a full session logged
offline, then reconnected with every mutation force-replayed, produces exactly
that session server-side.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import local_date, utcnow
from app.core.errors import AppError
from app.core.formulas import quantize_distance, quantize_rpe
from app.core.units import to_storage
from app.domain.enums import SessionStatus, Unit
from app.domain.models import SyncMutation, User
from app.repo import exercises as exercise_repo
from app.repo.plans import PlanRepo
from app.repo.sessions import SessionRepo
from app.repo.users import SettingsRepo
from app.services.sets import validate_set

MUTATION_TYPES = (
    "session.start",
    "session.update",
    "session.finish",
    "session.cancel",
    "session_exercise.add",
    "session_exercise.update",
    "session_exercise.delete",
    "set.upsert",
    "set.delete",
)


@dataclass
class SyncOutcome:
    applied: list[uuid.UUID] = field(default_factory=list)
    duplicates: list[uuid.UUID] = field(default_factory=list)
    rejected: list[dict] = field(default_factory=list)


class SyncService:
    def __init__(self, db: Session, user: User) -> None:
        self.db = db
        self.user = user
        self.sessions = SessionRepo(db, user.id)
        settings = SettingsRepo(db, user.id).get()
        self.unit = Unit(settings.unit_preference) if settings else Unit.KG
        self.timezone = settings.timezone if settings else "UTC"

    # --- idempotency ------------------------------------------------------

    def _already_applied(self, mutation_id: uuid.UUID) -> bool:
        return (
            self.db.execute(
                select(SyncMutation).where(
                    SyncMutation.id == mutation_id,
                    SyncMutation.user_id == self.user.id,
                )
            ).scalar_one_or_none()
            is not None
        )

    def _record(self, mutation_id: uuid.UUID, type_: str, result: str) -> None:
        self.db.add(
            SyncMutation(
                id=mutation_id, user_id=self.user.id, type=type_, result=result
            )
        )
        self.db.flush()

    # --- entry point ------------------------------------------------------

    def apply(self, mutations: list[dict]) -> SyncOutcome:
        outcome = SyncOutcome()
        # Order matters: a set cannot be applied before the session that holds
        # it, and the client may have queued them out of order after a retry.
        ordered = sorted(mutations, key=lambda m: (m.get("at") or "", m.get("id") or ""))

        for mutation in ordered:
            try:
                mutation_id = uuid.UUID(str(mutation["id"]))
            except (KeyError, ValueError):
                outcome.rejected.append(
                    {"id": mutation.get("id"), "code": "bad_mutation_id",
                     "message": "Every mutation needs a UUID id."}
                )
                continue

            if self._already_applied(mutation_id):
                outcome.duplicates.append(mutation_id)
                continue

            type_ = mutation.get("type")
            if type_ not in MUTATION_TYPES:
                # Recorded, like any other rejection, so a client that keeps
                # the row in its queue does not resend it forever.
                self._record(mutation_id, str(type_)[:40], "rejected")
                outcome.rejected.append(
                    {"id": str(mutation_id), "code": "unknown_type",
                     "message": f"Unknown mutation type {type_!r}."}
                )
                continue

            savepoint = self.db.begin_nested()
            try:
                getattr(self, "_" + type_.replace(".", "_"))(mutation.get("payload") or {})
                savepoint.commit()
                self._record(mutation_id, type_, "applied")
                outcome.applied.append(mutation_id)
            except AppError as exc:
                savepoint.rollback()
                # Recorded so a retry does not loop forever on the same bad row.
                self._record(mutation_id, type_, "rejected")
                outcome.rejected.append(
                    {"id": str(mutation_id), "code": exc.code, "message": exc.message}
                )
            except Exception as exc:  # noqa: BLE001 - one bad row must not fail the batch
                savepoint.rollback()
                self._record(mutation_id, type_, "rejected")
                outcome.rejected.append(
                    {"id": str(mutation_id), "code": "mutation_failed",
                     "message": str(exc)[:200]}
                )

        return outcome

    # --- handlers ---------------------------------------------------------

    def _session(self, payload: dict):
        return self.sessions.require(uuid.UUID(str(payload["session_id"])))

    def _session_start(self, payload: dict) -> None:
        session_id = uuid.UUID(str(payload["id"]))
        existing = self.sessions.get(session_id)
        if existing is not None:
            return  # already there; the mutation id guard usually catches this

        plan = None
        snapshot = None
        name = payload.get("name")
        if payload.get("workout_id"):
            from app.routes.sessions import _snapshot

            plan = PlanRepo(self.db, self.user.id).require(
                uuid.UUID(str(payload["workout_id"]))
            )
            snapshot = _snapshot(plan)
            name = name or plan.name

        # The client's own start time decides the date, so a session logged at
        # 23:50 offline does not land on the next day when it syncs (Sec 3.3).
        started = payload.get("start_time")
        moment = datetime.fromisoformat(started) if started else utcnow()

        session = self.sessions.create(
            session_id=session_id,
            name=name or "Workout",
            local_date=local_date(moment, self.timezone),
            workout_id=plan.id if plan else None,
            plan_snapshot=snapshot,
        )
        session.start_time = moment
        if plan:
            for row in plan.exercises:
                self.sessions.add_exercise(
                    session,
                    exercise_id=row.exercise_id,
                    planned_sets=row.planned_sets,
                    planned_reps_min=row.planned_reps_min,
                    planned_reps_max=row.planned_reps_max,
                    superset_group=row.superset_group,
                )
        self.db.flush()

    def _session_update(self, payload: dict) -> None:
        session = self._session(payload)
        for key in ("name", "notes"):
            if key in payload:
                setattr(session, key, payload[key])
        self.db.flush()

    def _session_finish(self, payload: dict) -> None:
        session = self._session(payload)
        if session.status != SessionStatus.IN_PROGRESS.value:
            return
        self.sessions.finish(session)

    def _session_cancel(self, payload: dict) -> None:
        session = self._session(payload)
        if session.status != SessionStatus.IN_PROGRESS.value:
            return
        self.sessions.cancel(session)

    def _session_exercise_add(self, payload: dict) -> None:
        session = self._session(payload)
        se_id = uuid.UUID(str(payload["id"]))
        try:
            self.sessions.get_exercise(session, se_id)
            return
        except AppError:
            pass

        exercise = exercise_repo.get(
            self.db, user_id=self.user.id,
            exercise_id=uuid.UUID(str(payload["exercise_id"])),
        )
        if exercise is None:
            raise AppError("No such exercise.", code="unknown_exercise")

        self.sessions.add_exercise(
            session,
            se_id=se_id,
            exercise_id=exercise.id,
            replaced_from_exercise_id=(
                uuid.UUID(str(payload["replaced_from_exercise_id"]))
                if payload.get("replaced_from_exercise_id")
                else None
            ),
            superset_group=payload.get("superset_group"),
            notes=payload.get("notes"),
        )

    def _session_exercise_update(self, payload: dict) -> None:
        session = self._session(payload)
        row = self.sessions.get_exercise(session, uuid.UUID(str(payload["id"])))
        for key in ("skipped", "superset_group", "notes"):
            if key in payload:
                setattr(row, key, payload[key])
        self.db.flush()

    def _session_exercise_delete(self, payload: dict) -> None:
        session = self._session(payload)
        try:
            self.sessions.remove_exercise(session, uuid.UUID(str(payload["id"])))
        except AppError:
            return  # already gone - deleting twice is not an error

    def _set_upsert(self, payload: dict) -> None:
        session = self._session(payload)
        session_exercise = self.sessions.get_exercise(
            session, uuid.UUID(str(payload["session_exercise_id"]))
        )
        validate_set(session_exercise.exercise.metric_type, payload)

        self.sessions.upsert_set(
            set_id=uuid.UUID(str(payload["id"])),
            session=session,
            session_exercise=session_exercise,
            weight_kg=to_storage(payload.get("weight"), self.unit),
            reps=payload.get("reps"),
            duration_seconds=payload.get("duration_seconds"),
            distance_m=quantize_distance(payload.get("distance_m")),
            rir=payload.get("rir"),
            rpe=quantize_rpe(payload.get("rpe")),
            failure=bool(payload.get("failure", False)),
            set_type=payload.get("set_type", "working"),
            rest_seconds=payload.get("rest_seconds"),
            notes=payload.get("notes"),
        )

    def _set_delete(self, payload: dict) -> None:
        row = self.sessions.get_set(uuid.UUID(str(payload["id"])))
        if row is None:
            return  # tombstoned already, or never arrived - both are fine
        self.sessions.delete_set(row)
