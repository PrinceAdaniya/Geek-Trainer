"""Local Postgres without Docker or sudo.

PLAN.md D17. `pgserver` ships real PostgreSQL 16 binaries in a wheel, so a
contributor with Python and nothing else can run the full stack. The data
directory lives in .pgdata/ and persists between runs.

  python scripts/devdb.py url     print the connection URL
  python scripts/devdb.py start   start it and print the URL
  python scripts/devdb.py stop    stop it
  python scripts/devdb.py psql    open a psql shell
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pgserver

DATA_DIR = Path(__file__).resolve().parent.parent / ".pgdata"


def server(cleanup_mode: str | None = None):
    """cleanup_mode=None leaves the server running after this process exits -
    which is the whole point of a dev database."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return pgserver.get_server(str(DATA_DIR), cleanup_mode=cleanup_mode)


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "url"

    if command == "stop":
        server(cleanup_mode="stop").cleanup()
        print("stopped")
        return 0

    db = server()
    uri = db.get_uri()

    if command in ("url", "start"):
        print(uri)
        return 0
    if command == "psql":
        os.execvp("sh", ["sh", "-c", f'"{db.pgbin}/psql" "{uri}"'])
    if command == "sql":
        print(db.psql(sys.argv[2]))
        return 0

    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
