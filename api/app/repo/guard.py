"""The user_id guard.

SPECIFICATIONS.MD Sec 24 requires that every user-owned query be scoped to the
requesting user, and Sec 23.1 puts that enforcement in the data-access layer
rather than in route handlers - "ownership is not something a route can
forget".

This is the mechanism that makes that testable. Every statement that touches a
user-owned table is inspected before execution; if it carries no user_id
predicate, it raises. Queries that legitimately span users (login by email,
session-token lookup, the ingest job) must say so explicitly with
`unscoped("why")`, which both documents the exception and makes it greppable.

Enabled in tests and development. In production it is off by default - the
tests are the gate, and a guard that raises in production would turn a scoping
bug into an outage instead of a caught mistake.
"""

from __future__ import annotations

import contextlib
import re
import threading
from collections.abc import Iterator

from sqlalchemy import event
from sqlalchemy.engine import Engine

# Grows as each phase adds tables. A table listed here may only be read or
# written through a statement that also filters on user_id.
USER_OWNED_TABLES: set[str] = {
    "user_settings",
    "bodyweight_log",
}

_MUTATING = re.compile(r"^\s*(select|insert|update|delete)\b", re.IGNORECASE)
_state = threading.local()


class UnscopedQueryError(RuntimeError):
    """A user-owned table was queried without a user_id predicate."""


@contextlib.contextmanager
def unscoped(reason: str) -> Iterator[None]:
    """Explicitly allow a cross-user statement. The reason is required so the
    exceptions can be read and audited, not just counted."""
    if not reason or len(reason) < 8:
        raise ValueError("unscoped() needs a real reason")
    previous = getattr(_state, "allow", None)
    _state.allow = reason
    try:
        yield
    finally:
        _state.allow = previous


def _tables_in(sql: str) -> set[str]:
    lowered = sql.lower()
    return {t for t in USER_OWNED_TABLES if t in lowered}


def _check(sql: str) -> None:
    if getattr(_state, "allow", None):
        return
    if not _MUTATING.match(sql):
        return
    touched = _tables_in(sql)
    if not touched:
        return
    if "user_id" in sql.lower():
        return
    raise UnscopedQueryError(
        "Statement touches user-owned table(s) "
        f"{sorted(touched)} without a user_id predicate. Scope it to the "
        "current user, or wrap it in repo.guard.unscoped('reason') if it is "
        "genuinely cross-user.\n"
        f"SQL: {sql[:400]}"
    )


_installed = False


def install() -> None:
    """Attach the guard to every engine. Idempotent."""
    global _installed
    if _installed:
        return

    @event.listens_for(Engine, "before_cursor_execute")
    def _before(conn, cursor, statement, parameters, context, executemany):
        _check(statement)

    _installed = True


def is_installed() -> bool:
    return _installed
