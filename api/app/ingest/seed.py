"""Load seeds/exercises.json into the exercises table.

Idempotent: matches on (source, source_id) and updates in place, so re-running
it never duplicates a row and never orphans a logged set. PLAN.md D5.
"""

from __future__ import annotations

import json
import uuid
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.domain.models import Exercise, IngestRun
from app.repo.guard import unscoped

SEED_FILE = Path(__file__).resolve().parent.parent.parent / "seeds" / "exercises.json"

_FIELDS = (
    "name", "name_normalized", "aliases", "body_part", "primary_muscle",
    "secondary_muscles", "equipment", "difficulty", "type", "metric_type",
    "default_rest_seconds", "instructions", "image_url", "gif_url",
    "video_url", "media_licence", "source_version",
)


def load_seed(db: Session, *, path: Path | None = None) -> dict[str, int]:
    rows = json.loads((path or SEED_FILE).read_text())

    run = IngestRun(source="custom", rows_seen=len(rows), notes="seed catalogue")
    db.add(run)
    db.flush()

    created = updated = 0
    with unscoped("the exercise catalogue is shared, not user-owned"):
        for row in rows:
            existing = db.execute(
                select(Exercise).where(
                    Exercise.source == row["source"],
                    Exercise.source_id == row["source_id"],
                )
            ).scalar_one_or_none()

            values = {field: row[field] for field in _FIELDS}
            values["bodyweight_load_factor"] = (
                Decimal(row["bodyweight_load_factor"])
                if row["bodyweight_load_factor"] is not None
                else None
            )
            values["ingested_at"] = utcnow()

            if existing is None:
                db.add(
                    Exercise(
                        id=uuid.UUID(row["id"]),
                        source=row["source"],
                        source_id=row["source_id"],
                        is_custom=False,
                        owner_user_id=None,
                        **values,
                    )
                )
                created += 1
            else:
                for key, value in values.items():
                    setattr(existing, key, value)
                updated += 1

        db.flush()

    run.finished_at = utcnow()
    run.status = "succeeded"
    run.rows_written = created + updated
    db.flush()

    return {"created": created, "updated": updated, "total": len(rows)}
