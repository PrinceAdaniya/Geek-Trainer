"""Workout plans. SPECIFICATIONS.MD Sec 7.

WorkoutExercise has no user_id of its own - it is reached only through its
plan, and every query here goes through that join. The scoping guard cannot
see the relationship, so the discipline lives in this module: nothing outside
it may query workout_exercises directly.
"""

from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import NotFound
from app.domain.models import WorkoutExercise, WorkoutPlan
from app.repo.base import UserScoped
from app.repo.guard import unscoped

DAY_ORDER = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


class PlanRepo(UserScoped):
    def _base(self):
        return (
            self.scoped(WorkoutPlan)
            .where(WorkoutPlan.is_archived.is_(False))
            .options(
                selectinload(WorkoutPlan.exercises).selectinload(WorkoutExercise.exercise)
            )
        )

    def list(self) -> list[WorkoutPlan]:
        rows = list(self.db.execute(self._base()).unique().scalars())
        # Week order, then the user's own ordering inside a day.
        return sorted(
            rows,
            key=lambda p: (
                DAY_ORDER.get(p.day_of_week or "", 99),
                p.order_index,
                p.created_at,
            ),
        )

    def get(self, plan_id: uuid.UUID) -> WorkoutPlan | None:
        return self.db.execute(
            self._base().where(WorkoutPlan.id == plan_id)
        ).unique().scalar_one_or_none()

    def require(self, plan_id: uuid.UUID) -> WorkoutPlan:
        plan = self.get(plan_id)
        if plan is None:
            # Sec 23.1 - another user's plan is a 404, not a 403.
            raise NotFound("No such workout.")
        return plan

    def create(self, *, name: str, day_of_week: str | None,
               target_muscles: list[str], notes: str | None) -> WorkoutPlan:
        next_index = self.db.execute(
            select(func.coalesce(func.max(WorkoutPlan.order_index), -1) + 1).where(
                WorkoutPlan.user_id == self.user_id
            )
        ).scalar_one()
        plan = WorkoutPlan(
            user_id=self.user_id,
            name=name,
            day_of_week=day_of_week,
            target_muscles=target_muscles,
            notes=notes,
            order_index=next_index,
        )
        self.db.add(plan)
        self.db.flush()
        return plan

    def archive(self, plan: WorkoutPlan) -> None:
        """Sec 7.2 - deleting a plan never deletes sessions performed from it."""
        plan.is_archived = True
        self.db.flush()

    # --- exercises inside a plan -----------------------------------------

    def _exercises_of(self, plan: WorkoutPlan):
        with unscoped("plan exercises are scoped by the plan, which is scoped"):
            return list(
                self.db.execute(
                    select(WorkoutExercise)
                    .where(WorkoutExercise.workout_id == plan.id)
                    .order_by(WorkoutExercise.order_index)
                ).scalars()
            )

    def add_exercise(self, plan: WorkoutPlan, **fields) -> WorkoutExercise:
        existing = self._exercises_of(plan)
        row = WorkoutExercise(
            workout_id=plan.id,
            order_index=len(existing),
            **fields,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def get_exercise(self, plan: WorkoutPlan, we_id: uuid.UUID) -> WorkoutExercise:
        with unscoped("plan exercises are scoped by the plan, which is scoped"):
            row = self.db.execute(
                select(WorkoutExercise).where(
                    WorkoutExercise.id == we_id, WorkoutExercise.workout_id == plan.id
                )
            ).scalar_one_or_none()
        if row is None:
            raise NotFound("That exercise is not in this workout.")
        return row

    def remove_exercise(self, plan: WorkoutPlan, we_id: uuid.UUID) -> None:
        row = self.get_exercise(plan, we_id)
        with unscoped("plan exercises are scoped by the plan, which is scoped"):
            self.db.execute(delete(WorkoutExercise).where(WorkoutExercise.id == row.id))
        self._renumber(plan)

    def reorder(self, plan: WorkoutPlan, ordered_ids: list[uuid.UUID]) -> None:
        rows = {row.id: row for row in self._exercises_of(plan)}
        if set(ordered_ids) != set(rows):
            raise NotFound("The reorder list must name every exercise in the workout.")
        for index, we_id in enumerate(ordered_ids):
            rows[we_id].order_index = index
        self.db.flush()

    def _renumber(self, plan: WorkoutPlan) -> None:
        for index, row in enumerate(self._exercises_of(plan)):
            row.order_index = index
        self.db.flush()
