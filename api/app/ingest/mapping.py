"""Normalising an external catalogue into our canonical vocabulary.

SPECIFICATIONS.MD Sec 4: "An unmapped value is a data error surfaced in a
report, never silently dropped." That is the whole design of this module - it
returns unmapped values rather than guessing, and the ingest job counts them.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from app.domain.enums import (
    BODY_PART_SET,
    EQUIPMENT_SET,
    MUSCLE_BODY_PART,
    MUSCLE_SET,
)

# ExerciseDB / WGER equipment names -> our canonical ids.
EQUIPMENT_ALIASES: dict[str, str] = {
    "body weight": "bodyweight", "bodyweight": "bodyweight", "none": "bodyweight",
    "assisted": "bodyweight",
    "barbell": "barbell", "olympic barbell": "barbell", "trap bar": "barbell",
    "dumbbell": "dumbbell", "dumbbells": "dumbbell",
    "kettlebell": "kettlebell", "kettlebells": "kettlebell",
    "cable": "cable", "cable machine": "cable", "pulley": "cable",
    "leverage machine": "machine", "machine": "machine", "sled machine": "machine",
    "weighted": "machine",
    "smith machine": "smith-machine",
    "ez barbell": "ez-bar", "ez bar": "ez-bar", "ez-curl bar": "ez-bar",
    "band": "resistance-band", "resistance band": "resistance-band",
    "elastic band": "resistance-band",
    "bench": "bench", "flat bench": "bench", "incline bench": "bench",
    "stability ball": "stability-ball", "swiss ball": "stability-ball",
    "exercise ball": "stability-ball",
    "medicine ball": "medicine-ball", "med ball": "medicine-ball",
    "wall ball": "medicine-ball",
    "pull up bar": "pull-up-bar", "pull-up bar": "pull-up-bar",
    "chin up bar": "pull-up-bar",
    "dip bar": "dip-bars", "dip bars": "dip-bars", "parallel bars": "dip-bars",
}

# ExerciseDB target/body-part names -> our canonical muscles.
MUSCLE_ALIASES: dict[str, str] = {
    "pectorals": "pectorals", "chest": "pectorals", "pecs": "pectorals",
    "lats": "lats", "latissimus dorsi": "lats",
    "upper back": "rhomboids", "rhomboids": "rhomboids",
    "traps": "traps", "trapezius": "traps",
    "spine": "lower-back", "lower back": "lower-back", "erector spinae": "lower-back",
    "teres major": "teres-major",
    "delts": "side-delts", "deltoids": "side-delts", "shoulders": "side-delts",
    "front delts": "front-delts", "anterior deltoid": "front-delts",
    "side delts": "side-delts", "lateral deltoid": "side-delts",
    "rear delts": "rear-delts", "posterior deltoid": "rear-delts",
    "rotator cuff": "rotator-cuff",
    "biceps": "biceps", "brachialis": "biceps",
    "triceps": "triceps",
    "forearms": "forearms", "wrists": "forearms",
    "quads": "quads", "quadriceps": "quads",
    "hamstrings": "hamstrings",
    "glutes": "glutes", "gluteus maximus": "glutes",
    "calves": "calves", "soleus": "calves",
    "adductors": "adductors", "inner thighs": "adductors",
    "abductors": "abductors", "outer thighs": "abductors",
    "hip flexors": "hip-flexors",
    "abs": "abs", "abdominals": "abs", "rectus abdominis": "abs",
    "obliques": "obliques",
    "transverse abdominis": "transverse-abdominis", "core": "transverse-abdominis",
    "levator scapulae": "neck", "neck": "neck",
    "cardiovascular system": "cardiovascular", "cardio": "cardiovascular",
}


def normalize_name(name: str) -> str:
    """Search key: accent-folded, lower-cased, punctuation collapsed."""
    folded = unicodedata.normalize("NFKD", name)
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    folded = folded.lower().replace("&", " and ")
    folded = re.sub(r"[^a-z0-9]+", " ", folded)
    return re.sub(r"\s+", " ", folded).strip()


def _key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def map_equipment(raw: str) -> str | None:
    key = _key(raw)
    if key in EQUIPMENT_SET:
        return key
    return EQUIPMENT_ALIASES.get(key)


def map_muscle(raw: str) -> str | None:
    key = _key(raw)
    if key in MUSCLE_SET:
        return key
    return MUSCLE_ALIASES.get(key)


def body_part_for(muscle: str) -> str | None:
    return MUSCLE_BODY_PART.get(muscle)


@dataclass
class MappingReport:
    """What could not be mapped, so it can be reported rather than dropped."""

    unmapped_equipment: dict[str, int] = field(default_factory=dict)
    unmapped_muscles: dict[str, int] = field(default_factory=dict)
    rejected_rows: list[str] = field(default_factory=list)

    def note_equipment(self, raw: str) -> None:
        self.unmapped_equipment[raw] = self.unmapped_equipment.get(raw, 0) + 1

    def note_muscle(self, raw: str) -> None:
        self.unmapped_muscles[raw] = self.unmapped_muscles.get(raw, 0) + 1

    def reject(self, why: str) -> None:
        self.rejected_rows.append(why)

    @property
    def clean(self) -> bool:
        return not (self.unmapped_equipment or self.unmapped_muscles or self.rejected_rows)

    def summary(self) -> str:
        if self.clean:
            return "mapping clean"
        lines = []
        if self.unmapped_equipment:
            lines.append(f"unmapped equipment: {self.unmapped_equipment}")
        if self.unmapped_muscles:
            lines.append(f"unmapped muscles: {self.unmapped_muscles}")
        if self.rejected_rows:
            lines.append(f"rejected {len(self.rejected_rows)} rows")
            lines.extend(f"  - {r}" for r in self.rejected_rows[:20])
        return "\n".join(lines)


def validate_canonical(*, body_part: str, primary: str, secondary: list[str],
                       equipment: list[str]) -> list[str]:
    """Returns the problems with a normalized row. Empty means it is clean."""
    problems = []
    if body_part not in BODY_PART_SET:
        problems.append(f"unknown body_part {body_part!r}")
    if primary not in MUSCLE_SET:
        problems.append(f"unknown primary_muscle {primary!r}")
    for muscle in secondary:
        if muscle not in MUSCLE_SET:
            problems.append(f"unknown secondary muscle {muscle!r}")
    for item in equipment:
        if item not in EQUIPMENT_SET:
            problems.append(f"unknown equipment {item!r}")
    if not equipment:
        problems.append("no equipment (use 'bodyweight')")
    return problems
