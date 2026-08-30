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

_STATEMENT = re.compile(r"^\s*(select|insert|update|delete)\b", re.IGNORECASE)
_WHITESPACE = re.compile(r"\s+")
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
    return {t for t in USER_OWNED_TABLES if t in sql}


def _predicate_mentions_user(sql: str, touched: set[str]) -> bool:
    """Look for user_id in the *predicate*, not anywhere in the statement.

    Checking the whole statement is useless: every `SELECT` of a user-owned
    table lists `user_id` among its columns, so a substring test passes
    everything. See ERRORS-AND-FIXES.md E3.
    """
    kind = _STATEMENT.match(sql).group(1).lower()

    if kind == "insert":
        # The scoping is the inserted user_id column itself.
        head, _, _ = sql.partition(" values")
        columns = head[head.find("(") + 1 : head.rfind(")")] if "(" in head else ""
        return "user_id" in columns

    if " where " not in sql:
        return False
    predicate = sql.split(" where ", 1)[1]

    if "user_id" in predicate:
        return True

    # A single row addressed by its own primary key. The ORM emits this shape
    # for every flush of a loaded object, and the object can only have been
    # loaded through a scoped read - so re-scoping here would mean fighting the
    # unit of work on every write in the app.
    #
    # This is a deliberate limit, not an oversight: the guard defends against
    # queries that fan out across users. A statement addressing one row by a
    # primary key the caller already holds is the IDOR question instead, and
    # that is covered by the endpoint tests for A10 in tests/test_ownership.py.
    return any(f"{table}.id =" in predicate for table in touched)


def _check(raw_sql: str) -> None:
    if getattr(_state, "allow", None):
        return
    if not _STATEMENT.match(raw_sql):
        return

    sql = _WHITESPACE.sub(" ", raw_sql).lower()
    touched = _tables_in(sql)
    if not touched:
        return
    if _predicate_mentions_user(sql, touched):
        return

    raise UnscopedQueryError(
        "Statement touches user-owned table(s) "
        f"{sorted(touched)} without a user_id predicate. Scope it to the "
        "current user, or wrap it in repo.guard.unscoped('reason') if it is "
        "genuinely cross-user.\n"
        f"SQL: {raw_sql[:400]}"
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
