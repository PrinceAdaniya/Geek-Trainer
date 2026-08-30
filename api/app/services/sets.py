"""What a set must contain, per metric type. SPECIFICATIONS.MD 10.2.

Kept out of the route so the same rules can be reused by the sync handler in
Phase 5 and by AI-proposed sessions in Phase 7.
"""

from __future__ import annotations

from decimal import Decimal

from app.core.errors import ValidationFailed
from app.domain.enums import MetricType

REQUIRED: dict[MetricType, tuple[str, ...]] = {
    MetricType.WEIGHT_REPS: ("weight", "reps"),
    MetricType.BODYWEIGHT_REPS: ("reps",),
    MetricType.WEIGHTED_BODYWEIGHT: ("reps",),
    MetricType.TIME: ("duration_seconds",),
    MetricType.DISTANCE: ("distance_m",),
    MetricType.TIME_DISTANCE: ("duration_seconds", "distance_m"),
}

FORBIDDEN: dict[MetricType, tuple[str, ...]] = {
    # A plain bodyweight movement has no external load to record; recording one
    # would make its volume wrong (Sec 13.1).
    MetricType.BODYWEIGHT_REPS: ("weight",),
    MetricType.TIME: ("weight", "reps"),
    MetricType.DISTANCE: ("weight", "reps"),
    MetricType.TIME_DISTANCE: ("weight", "reps"),
}

LABEL = {
    "weight": "a weight",
    "reps": "a rep count",
    "duration_seconds": "a duration",
    "distance_m": "a distance",
}


def validate_set(metric_type: str, values: dict) -> None:
    metric = MetricType(metric_type)

    missing = [
        field for field in REQUIRED[metric] if values.get(field) in (None, "")
    ]
    if missing:
        raise ValidationFailed(
            "This exercise needs " + " and ".join(LABEL[f] for f in missing) + ".",
            code="set_incomplete",
            details={"metric_type": metric.value, "missing": missing},
        )

    extra = [
        field for field in FORBIDDEN.get(metric, ()) if values.get(field) is not None
    ]
    if extra:
        raise ValidationFailed(
            "This exercise does not record " + " or ".join(LABEL[f] for f in extra) + ".",
            code="set_has_extra_fields",
            details={"metric_type": metric.value, "unexpected": extra},
        )

    # A negative load only means something for assisted bodyweight work.
    weight = values.get("weight")
    if (
        weight is not None
        and Decimal(weight) < 0
        and metric is not MetricType.WEIGHTED_BODYWEIGHT
    ):
        raise ValidationFailed(
            "Weight cannot be negative for this exercise.", code="negative_weight"
        )
