"""Load the seed catalogue into the dev database: python scripts/seed.py"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import session_factory  # noqa: E402
from app.ingest.seed import load_seed  # noqa: E402


def main() -> int:
    with session_factory()() as db:
        result = load_seed(db)
        db.commit()
    print(f"seeded: {result['created']} created, {result['updated']} updated, "
          f"{result['total']} in file")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
