"""Grant (or revoke) gym-staff access for an existing account.

  python scripts/make_staff.py someone@yourgym.com
  python scripts/make_staff.py someone@yourgym.com --revoke

Staff see every member's support tickets and the free-pass / tour enquiries.
There is deliberately no API for this - it is a decision made by whoever runs
the server.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.db import session_factory  # noqa: E402
from app.domain.models import User  # noqa: E402


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__)
        return 1
    revoke = "--revoke" in sys.argv
    email = args[0].strip().lower()

    with session_factory()() as db:
        user = db.execute(select(User).where(User.email == email)).scalars().first()
        if user is None:
            print(f"no account for {email} - register it in the app first")
            return 1
        user.is_staff = not revoke
        db.commit()
    print(f"{email}: staff access {'revoked' if revoke else 'granted'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
