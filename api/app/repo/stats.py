"""Streaks and headline numbers.

SPECIFICATIONS.MD Sec 14 defines adherence and consistency; this is the part of
that the dashboard needs, brought forward from Phase 6 because a training app
with no visible progress is not motivating enough to keep using.

Everything here is computed from the set log (PLAN.md D6), never stored, so it
can never disagree with what the user actually did.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as Date
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, select

from app.domain.enums import NON_COUNTING_SET_TYPES, SessionStatus
from app.domain.models import SetRecord, WorkoutSession
from app.repo.base import UserScoped

# Sec 14 - a streak is measured in days trained, but rest days are training.
# Breaking a streak because someone sensibly took Sunday off would be wrong, so
# the streak survives a gap of up to REST_TOLERANCE_DAYS.
REST_TOLERANCE_DAYS = 2


@dataclass
class Stats:
    current_streak: int = 0
    longest_streak: int = 0
    total_sessions: int = 0
    sessions_this_week: int = 0
    sets_this_week: int = 0
    volume_this_week_kg: Decimal = Decimal(0)
    total_volume_kg: Decimal = Decimal(0)
    last_session_date: Date | None = None
    trained_today: bool = False
    active_days: list[str] = field(default_factory=list)


class StatsRepo(UserScoped):
    def _training_dates(self) -> list[Date]:
        stmt = (
            self.scoped(WorkoutSession)
            .where(
                WorkoutSession.status == SessionStatus.COMPLETED.value,
                WorkoutSession.deleted_at.is_(None),
            )
            .with_only_columns(WorkoutSession.date)
            .distinct()
            .order_by(WorkoutSession.date)
        )
        return list(self.db.execute(stmt).scalars())

    @staticmethod
    def streaks(dates: list[Date], today: Date) -> tuple[int, int]:
        """Returns (current, longest), counting distinct training days and
        allowing a rest gap of REST_TOLERANCE_DAYS."""
        if not dates:
            return 0, 0

        longest = run = 1
        for previous, current in zip(dates, dates[1:]):
            if (current - previous).days <= REST_TOLERANCE_DAYS + 1:
                run += 1
            else:
                run = 1
            longest = max(longest, run)

        # The current streak only counts if the last session is recent enough
        # that the streak has not lapsed.
        if (today - dates[-1]).days > REST_TOLERANCE_DAYS + 1:
            return 0, longest

        current = 1
        for previous, following in zip(reversed(dates[:-1]), reversed(dates[1:])):
            if (following - previous).days <= REST_TOLERANCE_DAYS + 1:
                current += 1
            else:
                break
        return current, longest

    def week_start(self, today: Date, week_start: str) -> Date:
        """Sec 3.3 - the user's week, not the calendar's."""
        offset = today.weekday() if week_start == "monday" else (today.weekday() + 1) % 7
        return today - timedelta(days=offset)

    def compute(self, *, today: Date, week_start: str) -> Stats:
        dates = self._training_dates()
        current, longest = self.streaks(dates, today)
        since = self.week_start(today, week_start)

        counting = self.scoped(SetRecord).where(
            SetRecord.deleted_at.is_(None),
            SetRecord.set_type.notin_([t.value for t in NON_COUNTING_SET_TYPES]),
        )

        week_sets = self.db.execute(
            counting.join(WorkoutSession, SetRecord.session_id == WorkoutSession.id)
            .where(WorkoutSession.date >= since)
            .with_only_columns(
                func.count(SetRecord.id),
                func.coalesce(
                    func.sum(SetRecord.weight_kg * SetRecord.reps), Decimal(0)
                ),
            )
        ).one()

        total_volume = self.db.execute(
            counting.with_only_columns(
                func.coalesce(func.sum(SetRecord.weight_kg * SetRecord.reps), Decimal(0))
            )
        ).scalar_one()

        return Stats(
            current_streak=current,
            longest_streak=longest,
            total_sessions=len(dates),
            sessions_this_week=sum(1 for d in dates if d >= since),
            sets_this_week=int(week_sets[0] or 0),
            volume_this_week_kg=Decimal(week_sets[1] or 0),
            total_volume_kg=Decimal(total_volume or 0),
            last_session_date=dates[-1] if dates else None,
            trained_today=bool(dates) and dates[-1] == today,
            active_days=[d.isoformat() for d in dates[-84:]],
        )
