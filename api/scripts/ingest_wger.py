"""Fetch the WGER catalogue into the local mirror: python scripts/ingest_wger.py"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import session_factory  # noqa: E402
from app.ingest.wger import fetch, load  # noqa: E402


def main() -> int:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 900
    print(f"fetching up to {limit} exercises from wger.de …")
    staged = fetch(limit=limit)
    print(f"  staged {len(staged.rows)} rows")
    print("  " + staged.report.summary().replace("\n", "\n  "))

    with session_factory()() as db:
        result = load(db, staged)
        db.commit()
    print(
        f"loaded: {result['created']} created, {result['updated']} updated, "
        f"{result['media_attached']} seed images attached, "
        f"{result['rejected']} rejected"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
