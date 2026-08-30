"""Time helpers. PLAN.md D8 - the date a workout belongs to is decided when it
happens, in the user's timezone, and then stored."""

from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def resolve_tz(name: str | None) -> ZoneInfo:
    if not name:
        return ZoneInfo("UTC")
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def local_date(moment: datetime, tz_name: str | None) -> date:
    """SPECIFICATIONS.MD 3.3 - 'today' is evaluated in the user's timezone."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(resolve_tz(tz_name)).date()
