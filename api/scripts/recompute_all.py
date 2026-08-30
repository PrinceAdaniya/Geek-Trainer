"""Rebuild every derived number from the log.

Maintenance command, and the thing that proves PLAN.md D6: derived data is a
pure function of the set history, so throwing it away and recomputing must be
safe at any time.

    python scripts/recompute_all.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.db import session_factory  # noqa: E402
from app.domain.enums import SessionStatus  # noqa: E402
from app.domain.models import WorkoutSession  # noqa: E402
from app.repo.guard import unscoped  # noqa: E402
from app.services.recompute import recompute_for_session  # noqa: E402


def main() -> int:
    with session_factory()() as db:
        with unscoped("maintenance recompute spans every user by design"):
            sessions = db.execute(
                select(WorkoutSession.user_id, WorkoutSession.id).where(
                    WorkoutSession.status == SessionStatus.COMPLETED.value,
                    WorkoutSession.deleted_at.is_(None),
                )
            ).all()
            for user_id, session_id in sessions:
                recompute_for_session(db, user_id, session_id)
        db.commit()
    print(f"recomputed {len(sessions)} completed session(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
