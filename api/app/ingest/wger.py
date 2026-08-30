"""WGER ingest. SPECIFICATIONS.MD 5.1.

Runs offline, never on a request path. Writes into a staging list, validates,
and only then touches the exercises table - a partial or broken fetch leaves
the existing catalogue alone.

WGER is used rather than ExerciseDB because it needs no API key and its data is
openly licensed, which also gives the catalogue real demonstration images.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.domain.enums import MUSCLE_BODY_PART, MetricType
from app.domain.models import Exercise, IngestRun
from app.ingest.mapping import MappingReport, normalize_name
from app.repo.guard import unscoped

BASE = "https://wger.de/api/v2"
USER_AGENT = "geek-trainer-ingest/0.1 (+local development)"
LICENCE = "wger.de — CC-BY-SA 4.0"

# WGER category -> our body part.
CATEGORY_BODY_PART = {
    "Abs": "core", "Arms": "arms", "Back": "back", "Calves": "legs",
    "Chest": "chest", "Legs": "legs", "Shoulders": "shoulders",
    "Cardio": "cardio",
}

# WGER muscle (English name) -> our canonical muscle.
WGER_MUSCLES = {
    "Chest": "pectorals", "Pectorals": "pectorals",
    "Lats": "lats", "Latissimus dorsi": "lats",
    "Trapezius": "traps", "Rhomboids": "rhomboids",
    "Erector spinae": "lower-back", "Lower back": "lower-back",
    "Teres major": "teres-major",
    "Anterior deltoid": "front-delts", "Shoulders": "side-delts",
    "Lateral deltoid": "side-delts", "Posterior deltoid": "rear-delts",
    "Rotator cuff": "rotator-cuff",
    "Biceps": "biceps", "Biceps brachii": "biceps", "Brachialis": "biceps",
    "Triceps": "triceps", "Triceps brachii": "triceps",
    "Forearms": "forearms", "Brachioradialis": "forearms",
    "Quadriceps": "quads", "Quadriceps femoris": "quads", "Quads": "quads",
    "Hamstrings": "hamstrings", "Biceps femoris": "hamstrings",
    "Glutes": "glutes", "Gluteus maximus": "glutes",
    "Calves": "calves", "Gastrocnemius": "calves", "Soleus": "calves",
    "Adductors": "adductors", "Abductors": "abductors",
    "Abs": "abs", "Rectus abdominis": "abs", "Obliques": "obliques",
    "Obliquus externus abdominis": "obliques",
    "Serratus anterior": "pectorals",
}

WGER_EQUIPMENT = {
    "Barbell": "barbell", "Dumbbell": "dumbbell", "Kettlebell": "kettlebell",
    "SZ-Bar": "ez-bar", "Bench": "bench", "Pull-up bar": "pull-up-bar",
    "none (bodyweight exercise)": "bodyweight", "Gym mat": "bodyweight",
    "Swiss Ball": "stability-ball", "Incline bench": "bench",
    "Resistance band": "resistance-band", "Cable": "cable",
    "Machine": "machine", "Cable machine": "cable",
}


def _get(url: str, timeout: int = 45) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                   "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _paged(path: str, *, limit: int, page_size: int = 100) -> list[dict]:
    rows: list[dict] = []
    url = f"{BASE}/{path}?format=json&limit={page_size}"
    while url and len(rows) < limit:
        payload = _get(url)
        rows.extend(payload.get("results", []))
        url = payload.get("next")
    return rows[:limit]


@dataclass
class Staged:
    rows: list[dict] = field(default_factory=list)
    report: MappingReport = field(default_factory=MappingReport)


def fetch(*, limit: int = 900) -> Staged:
    """Fetch and normalise. Nothing here touches the database."""
    staged = Staged()

    images: dict[int, str] = {}
    try:
        for row in _paged("exerciseimage", limit=1000):
            base_id = row.get("exercise_base") or row.get("exercise")
            if base_id and row.get("image") and base_id not in images:
                images[int(base_id)] = row["image"]
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        staged.report.reject(f"image fetch failed: {exc}")

    for entry in _paged("exerciseinfo", limit=limit):
        english = next(
            (t for t in entry.get("translations", []) if t.get("language") == 2), None
        )
        if not english or not english.get("name"):
            continue

        name = english["name"].strip()
        category = (entry.get("category") or {}).get("name")
        body_part = CATEGORY_BODY_PART.get(category)

        primaries = [
            WGER_MUSCLES.get(m.get("name_en") or m.get("name"))
            for m in entry.get("muscles", [])
        ]
        primaries = [m for m in primaries if m]
        secondaries = [
            WGER_MUSCLES.get(m.get("name_en") or m.get("name"))
            for m in entry.get("muscles_secondary", [])
        ]
        secondaries = [m for m in secondaries if m]

        if not primaries:
            for raw in entry.get("muscles", []):
                staged.report.note_muscle(raw.get("name_en") or raw.get("name") or "?")
            # Fall back to the category, which is always present.
            if body_part is None:
                staged.report.reject(f"{name}: no muscle and no category")
                continue
            primaries = [
                m for m, part in MUSCLE_BODY_PART.items() if part == body_part
            ][:1]
            if not primaries:
                staged.report.reject(f"{name}: category {category!r} has no muscle")
                continue

        primary = primaries[0]
        body_part = MUSCLE_BODY_PART.get(primary, body_part)

        equipment: list[str] = []
        for item in entry.get("equipment", []):
            mapped = WGER_EQUIPMENT.get(item.get("name"))
            if mapped:
                equipment.append(mapped)
            else:
                staged.report.note_equipment(item.get("name") or "?")
        if not equipment:
            equipment = ["bodyweight"]

        metric = (
            MetricType.BODYWEIGHT_REPS.value
            if equipment == ["bodyweight"]
            else MetricType.WEIGHT_REPS.value
        )

        description = (english.get("description") or "").strip()
        instructions = _to_steps(description)

        staged.rows.append(
            {
                "source": "wger",
                "source_id": str(entry.get("id")),
                "source_version": entry.get("last_update") or "",
                "name": name,
                "name_normalized": normalize_name(name),
                "aliases": [],
                "body_part": body_part,
                "primary_muscle": primary,
                "secondary_muscles": sorted(set(secondaries) - {primary}),
                "equipment": sorted(set(equipment)),
                "difficulty": "intermediate",
                "type": "compound" if len(secondaries) >= 2 else "isolation",
                "metric_type": metric,
                "bodyweight_load_factor": "0.65" if metric != "weight_reps" else None,
                "default_rest_seconds": 120,
                "instructions": instructions,
                "image_url": images.get(int(entry.get("id", 0))),
                "gif_url": None,
                "video_url": None,
                "media_licence": LICENCE if images.get(int(entry.get("id", 0))) else None,
            }
        )

    return staged


def _to_steps(html: str) -> list[str]:
    """WGER descriptions are small HTML fragments. Strip to plain sentences."""
    import re

    text = re.sub(r"<li>", "\n• ", html)
    text = re.sub(r"<[^>]+>", " ", text)
    text = (
        text.replace("&nbsp;", " ").replace("&amp;", "&")
        .replace("&quot;", '"').replace("&#39;", "'")
    )
    lines = [re.sub(r"\s+", " ", line).strip(" •") for line in text.split("\n")]
    return [line for line in lines if len(line) > 12][:6]


def load(db: Session, staged: Staged, *, attach_media_to_seed: bool = True) -> dict:
    """Upsert the staged rows. Existing ids are never reassigned, so no logged
    set is ever orphaned (Sec 5.3)."""
    if not staged.rows:
        raise RuntimeError("refusing to load an empty ingest - the catalogue stands")

    run = IngestRun(source="wger", rows_seen=len(staged.rows), notes=staged.report.summary())
    db.add(run)
    db.flush()

    created = updated = media_attached = 0

    with unscoped("the exercise catalogue is shared, not user-owned"):
        # Back-fill demonstration images onto the hand-written seed catalogue
        # where the names agree, so the movements people actually log get a
        # picture rather than only the imported long tail.
        if attach_media_to_seed:
            by_name = {row["name_normalized"]: row for row in staged.rows if row["image_url"]}
            seeds = db.execute(
                select(Exercise).where(Exercise.source == "custom", Exercise.is_custom.is_(False))
            ).scalars()
            for seed in seeds:
                match = by_name.get(seed.name_normalized)
                if match and not seed.image_url:
                    seed.image_url = match["image_url"]
                    seed.media_licence = LICENCE
                    media_attached += 1
            db.flush()

        for row in staged.rows:
            existing = db.execute(
                select(Exercise).where(
                    Exercise.source == "wger", Exercise.source_id == row["source_id"]
                )
            ).scalar_one_or_none()

            # Do not shadow a hand-written seed entry with an import of the
            # same movement - the seed rows have better metric types.
            clash = db.execute(
                select(Exercise).where(
                    Exercise.name_normalized == row["name_normalized"],
                    Exercise.source != "wger",
                )
            ).scalar_one_or_none()
            if clash is not None and existing is None:
                continue

            values = dict(row)
            values["ingested_at"] = utcnow()
            values.pop("source", None)
            values.pop("source_id", None)

            if existing is None:
                db.add(Exercise(source="wger", source_id=row["source_id"],
                                is_custom=False, owner_user_id=None, **values))
                created += 1
            else:
                for key, value in values.items():
                    setattr(existing, key, value)
                updated += 1
        db.flush()

    run.finished_at = utcnow()
    run.status = "succeeded"
    run.rows_written = created + updated
    run.rows_rejected = len(staged.report.rejected_rows)
    db.flush()

    return {
        "created": created,
        "updated": updated,
        "media_attached": media_attached,
        "rejected": len(staged.report.rejected_rows),
    }
