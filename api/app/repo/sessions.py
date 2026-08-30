"""Sessions, session exercises and sets. SPECIFICATIONS.MD Sec 8-10.

Sessions and sets carry user_id and are scoped by the guard. SessionExercise
does not - it is reached only through its session, and every query for one
lives in this module.
"""

from __future__ import annotations

import uuid
from datetime import date as Date

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.clock import utcnow
from app.core.errors import Conflict, NotFound
from app.domain.enums import SessionStatus
from app.domain.models import (
    Exercise,
    SessionExercise,
    SetRecord,
    WorkoutSession,
)
from app.repo.base import UserScoped
from app.repo.guard import unscoped


class SessionRepo(UserScoped):
    # --- sessions ---------------------------------------------------------

    def _base(self):
        return (
            self.scoped(WorkoutSession)
            .where(WorkoutSession.deleted_at.is_(None))
            .options(
                selectinload(WorkoutSession.exercises)
                .selectinload(SessionExercise.sets),
                selectinload(WorkoutSession.exercises)
                .selectinload(SessionExercise.exercise),
            )
        )

    def get(self, session_id: uuid.UUID) -> WorkoutSession | None:
        return self.db.execute(
            self._base().where(WorkoutSession.id == session_id)
        ).unique().scalar_one_or_none()

    def require(self, session_id: uuid.UUID) -> WorkoutSession:
        found = self.get(session_id)
        if found is None:
            raise NotFound("No such session.")
        return found

    def active(self) -> WorkoutSession | None:
        """Sec 8.2 - opening the app resumes an in-progress session."""
        return self.db.execute(
            self._base()
            .where(WorkoutSession.status == SessionStatus.IN_PROGRESS.value)
            .order_by(WorkoutSession.start_time.desc())
        ).unique().scalars().first()

    def history(
        self,
        *,
        limit: int = 30,
        before: Date | None = None,
        statuses: tuple[str, ...] = (SessionStatus.COMPLETED.value,),
    ) -> list[WorkoutSession]:
        stmt = self._base().where(WorkoutSession.status.in_(statuses))
        if before:
            stmt = stmt.where(WorkoutSession.date < before)
        stmt = stmt.order_by(
            WorkoutSession.date.desc(), WorkoutSession.start_time.desc()
        ).limit(limit)
        return list(self.db.execute(stmt).unique().scalars())

    def create(
        self,
        *,
        session_id: uuid.UUID,
        name: str,
        local_date: Date,
        workout_id: uuid.UUID | None,
        plan_snapshot: dict | None,
    ) -> WorkoutSession:
        if self.active() is not None:
            # Sec 8.2 - the database enforces this too; this is the readable error.
            raise Conflict(
                "You already have a workout in progress. Finish it first.",
                code="session_already_active",
            )
        if self.get(session_id) is not None:
            raise Conflict("That session already exists.", code="duplicate_session")

        session = WorkoutSession(
            id=session_id,
            user_id=self.user_id,
            workout_id=workout_id,
            plan_snapshot=plan_snapshot,
            name=name,
            date=local_date,
            start_time=utcnow(),
            status=SessionStatus.IN_PROGRESS.value,
        )
        self.db.add(session)
        self.db.flush()
        return session

    def finish(self, session: WorkoutSession) -> WorkoutSession:
        if session.status != SessionStatus.IN_PROGRESS.value:
            raise Conflict("That session is not in progress.", code="not_in_progress")
        session.end_time = utcnow()
        session.status = SessionStatus.COMPLETED.value
        session.duration_seconds = int(
            (session.end_time - session.start_time).total_seconds()
        )
        self.db.flush()
        return session

    def cancel(self, session: WorkoutSession) -> WorkoutSession:
        if session.status != SessionStatus.IN_PROGRESS.value:
            raise Conflict("That session is not in progress.", code="not_in_progress")
        session.end_time = utcnow()
        session.status = SessionStatus.CANCELLED.value
        self.db.flush()
        return session

    # --- session exercises ------------------------------------------------

    def _exercises_of(self, session: WorkoutSession) -> list[SessionExercise]:
        with unscoped("session exercises are scoped by their session"):
            return list(
                self.db.execute(
                    select(SessionExercise)
                    .where(SessionExercise.session_id == session.id)
                    .order_by(SessionExercise.order_index)
                ).scalars()
            )

    def add_exercise(
        self, session: WorkoutSession, *, se_id: uuid.UUID | None = None, **fields
    ) -> SessionExercise:
        existing = self._exercises_of(session)
        row = SessionExercise(
            id=se_id or uuid.uuid4(),
            session_id=session.id,
            order_index=len(existing),
            **fields,
        )
        self.db.add(row)
        self.db.flush()
        # The session in the identity map still holds the old collection; a
        # re-query would return it unchanged and the caller would render a
        # session without the exercise it just added.
        self.db.expire(session, ["exercises"])
        return row

    def get_exercise(self, session: WorkoutSession, se_id: uuid.UUID) -> SessionExercise:
        with unscoped("session exercises are scoped by their session"):
            row = self.db.execute(
                select(SessionExercise).where(
                    SessionExercise.id == se_id,
                    SessionExercise.session_id == session.id,
                )
            ).scalar_one_or_none()
        if row is None:
            raise NotFound("That exercise is not in this session.")
        return row

    def remove_exercise(self, session: WorkoutSession, se_id: uuid.UUID) -> None:
        row = self.get_exercise(session, se_id)
        with unscoped("session exercises are scoped by their session"):
            self.db.execute(delete(SessionExercise).where(SessionExercise.id == row.id))
        self.db.expire(session, ["exercises"])
        self.renumber(session)

    def reorder(self, session: WorkoutSession, ordered: list[uuid.UUID]) -> None:
        rows = {row.id: row for row in self._exercises_of(session)}
        if set(ordered) != set(rows):
            raise NotFound("The reorder list must name every exercise in the session.")
        for index, se_id in enumerate(ordered):
            rows[se_id].order_index = index
        self.db.flush()
        self.db.expire(session, ["exercises"])

    def renumber(self, session: WorkoutSession) -> None:
        for index, row in enumerate(self._exercises_of(session)):
            row.order_index = index
        self.db.flush()

    # --- sets -------------------------------------------------------------

    def sets_for(self, session_exercise: SessionExercise) -> list[SetRecord]:
        stmt = (
            self.scoped(SetRecord)
            .where(
                SetRecord.session_exercise_id == session_exercise.id,
                SetRecord.deleted_at.is_(None),
            )
            .order_by(SetRecord.set_number)
        )
        return list(self.db.execute(stmt).scalars())

    def get_set(self, set_id: uuid.UUID) -> SetRecord | None:
        return self.db.execute(
            self.scoped(SetRecord).where(
                SetRecord.id == set_id, SetRecord.deleted_at.is_(None)
            )
        ).scalar_one_or_none()

    def upsert_set(
        self,
        *,
        set_id: uuid.UUID,
        session: WorkoutSession,
        session_exercise: SessionExercise,
        **fields,
    ) -> SetRecord:
        """Upsert by client-supplied id - a replayed offline write is a no-op
        rather than a duplicate (PLAN.md D3)."""
        existing = self.get_set(set_id)
        if existing is not None:
            for key, value in fields.items():
                setattr(existing, key, value)
            self.db.flush()
            return existing

        current = self.sets_for(session_exercise)
        row = SetRecord(
            id=set_id,
            user_id=self.user_id,
            session_id=session.id,
            session_exercise_id=session_exercise.id,
            exercise_id=session_exercise.exercise_id,
            set_number=len(current) + 1,
            **fields,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def delete_set(self, row: SetRecord) -> None:
        """Tombstoned, not removed - Sec 12.4, so sync can reconcile it."""
        row.deleted_at = utcnow()
        self.db.flush()
        self._renumber_sets(row.session_exercise_id)

    def _renumber_sets(self, session_exercise_id: uuid.UUID) -> None:
        stmt = (
            self.scoped(SetRecord)
            .where(
                SetRecord.session_exercise_id == session_exercise_id,
                SetRecord.deleted_at.is_(None),
            )
            .order_by(SetRecord.set_number, SetRecord.performed_at)
        )
        for index, row in enumerate(self.db.execute(stmt).scalars(), start=1):
            row.set_number = index
        self.db.flush()

    # --- previous performance --------------------------------------------

    def last_performance(
        self, exercise_id: uuid.UUID, *, exclude_session: uuid.UUID | None = None
    ) -> tuple[WorkoutSession, list[SetRecord]] | None:
        """Sec 11.2 - the last session's sets for this exercise, always visible
        while logging."""
        stmt = (
            self.scoped(SetRecord)
            .join(WorkoutSession, SetRecord.session_id == WorkoutSession.id)
            .where(
                SetRecord.exercise_id == exercise_id,
                SetRecord.deleted_at.is_(None),
                WorkoutSession.status == SessionStatus.COMPLETED.value,
            )
        )
        if exclude_session:
            stmt = stmt.where(SetRecord.session_id != exclude_session)

        last_session_id = self.db.execute(
            stmt.with_only_columns(SetRecord.session_id)
            .order_by(SetRecord.performed_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        if last_session_id is None:
            return None

        session = self.get(last_session_id)
        if session is None:
            return None
        rows = list(
            self.db.execute(
                self.scoped(SetRecord)
                .where(
                    SetRecord.session_id == last_session_id,
                    SetRecord.exercise_id == exercise_id,
                    SetRecord.deleted_at.is_(None),
                )
                .order_by(SetRecord.set_number)
            ).scalars()
        )
        return session, rows

    def exercise_counts(self, session: WorkoutSession) -> dict[uuid.UUID, int]:
        stmt = (
            self.scoped(SetRecord)
            .where(SetRecord.session_id == session.id, SetRecord.deleted_at.is_(None))
            .with_only_columns(SetRecord.session_exercise_id, func.count(SetRecord.id))
            .group_by(SetRecord.session_exercise_id)
        )
        return {row[0]: row[1] for row in self.db.execute(stmt)}
