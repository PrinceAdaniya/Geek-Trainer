"""Compile seeds/catalogue.py into seeds/exercises.json.

Validates every row against the canonical vocabularies before writing, so a
typo in the catalogue fails here rather than in the app. PLAN.md D5.
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

API_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(API_DIR))
sys.path.insert(0, str(API_DIR / "seeds"))

import catalogue  # noqa: E402
from app.domain.enums import MUSCLE_BODY_PART  # noqa: E402
from app.ingest.mapping import normalize_name, validate_canonical  # noqa: E402

# Stable ids: the same exercise keeps the same id across rebuilds, so test
# fixtures and any already-logged set survive a re-seed.
SEED_NAMESPACE = uuid.UUID("6f0f9b1e-4a2f-5d3c-8e7a-1b2c3d4e5f60")

DIFFICULTY = {"b": "beginner", "i": "intermediate", "a": "advanced"}
TYPE = {"c": "compound", "i": "isolation", "cardio": "cardio", "mobility": "mobility"}
METRIC = {
    "wr": "weight_reps",
    "br": "bodyweight_reps",
    "wb": "weighted_bodyweight",
    "t": "time",
    "d": "distance",
    "td": "time_distance",
}
DEFAULT_REST = {"compound": 180, "isolation": 90, "cardio": 60, "mobility": 30}


def build() -> list[dict]:
    rows: list[dict] = []
    problems: list[str] = []
    seen: set[str] = set()

    for group, entries in catalogue.ALL_GROUPS.items():
        for (
            name, primary, secondary, equipment, difficulty, kind, metric, factor, cue
        ) in entries:
            normalized = normalize_name(name)
            if normalized in seen:
                problems.append(f"{name}: duplicate")
                continue
            seen.add(normalized)

            body_part = MUSCLE_BODY_PART.get(primary)
            if body_part is None:
                problems.append(f"{name}: primary muscle {primary!r} has no body part")
                continue

            issues = validate_canonical(
                body_part=body_part,
                primary=primary,
                secondary=list(secondary),
                equipment=list(equipment),
            )
            if difficulty not in DIFFICULTY:
                issues.append(f"bad difficulty code {difficulty!r}")
            if kind not in TYPE:
                issues.append(f"bad type code {kind!r}")
            if metric not in METRIC:
                issues.append(f"bad metric code {metric!r}")

            metric_full = METRIC.get(metric)
            # Sec 13.1/13.2 - a bodyweight movement without a load factor would
            # silently score zero volume, so the catalogue must not contain one.
            if metric_full in ("bodyweight_reps", "weighted_bodyweight") and factor is None:
                issues.append("bodyweight movement is missing bodyweight_load_factor")
            if metric_full == "weight_reps" and factor is not None:
                issues.append("bodyweight_load_factor set on a weight_reps movement")

            if issues:
                problems.append(f"{name}: " + "; ".join(issues))
                continue

            kind_full = TYPE[kind]
            rows.append(
                {
                    "id": str(uuid.uuid5(SEED_NAMESPACE, normalized)),
                    "source": "custom",
                    "source_id": f"seed:{normalized.replace(' ', '-')}",
                    "source_version": "seed-1",
                    "name": name,
                    "name_normalized": normalized,
                    "aliases": [],
                    "body_part": body_part,
                    "primary_muscle": primary,
                    "secondary_muscles": list(secondary),
                    "equipment": sorted(set(equipment)),
                    "difficulty": DIFFICULTY[difficulty],
                    "type": kind_full,
                    "metric_type": metric_full,
                    "bodyweight_load_factor": str(factor) if factor is not None else None,
                    "default_rest_seconds": DEFAULT_REST[kind_full],
                    "instructions": [cue],
                    "image_url": None,
                    "gif_url": None,
                    "video_url": None,
                    "media_licence": None,
                    "group": group,
                }
            )

    if problems:
        print("SEED VALIDATION FAILED", file=sys.stderr)
        for problem in problems:
            print("  -", problem, file=sys.stderr)
        raise SystemExit(1)

    return rows


def main() -> int:
    rows = build()
    out = API_DIR / "seeds" / "exercises.json"
    out.write_text(json.dumps(rows, indent=1, ensure_ascii=False) + "\n")

    by_part: dict[str, int] = {}
    for row in rows:
        by_part[row["body_part"]] = by_part.get(row["body_part"], 0) + 1
    print(f"wrote {len(rows)} exercises -> {out.relative_to(API_DIR)}")
    for part, count in sorted(by_part.items()):
        print(f"  {part:<10} {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
