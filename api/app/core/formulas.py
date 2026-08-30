"""Pure training-math. No I/O, no ORM, no framework imports.

PLAN.md D7 pins every formula here so the server and the client cannot
disagree about the user's numbers. SPECIFICATIONS.MD Sec 13 is the source of
truth for the definitions.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.domain.enums import MetricType

# Sec 3.1 - exact, by definition of the international pound.
LB_PER_KG = Decimal("0.45359237")

# Sec 13.3 - Epley is unreliable above 12 reps, so we refuse to guess.
E1RM_MAX_REPS = 12

# Sec 13.2 - fallback when an exercise carries no curated factor.
DEFAULT_BODYWEIGHT_LOAD_FACTOR = Decimal("1.0")

WEIGHT_QUANT = Decimal("0.001")  # NUMERIC(7,3)


def _q(value: Decimal) -> Decimal:
    return value.quantize(WEIGHT_QUANT, rounding=ROUND_HALF_UP)


FACTOR_QUANT = Decimal("0.001")   # NUMERIC(4,3)
RPE_QUANT = Decimal("0.1")        # NUMERIC(3,1)
DISTANCE_QUANT = Decimal("0.01")  # NUMERIC(9,2)


def quantize(value: Decimal | None, exponent: Decimal) -> Decimal | None:
    """Match a NUMERIC column's precision at the write boundary.

    Every NUMERIC column needs this, not just the ones that happened to have a
    test - see ERRORS-AND-FIXES.md E5 and E7. Without it a value reads back
    differently than it was written, and the offline client in Phase 5 would
    see a phantom conflict.
    """
    if value is None:
        return None
    return Decimal(value).quantize(exponent, rounding=ROUND_HALF_UP)


def quantize_factor(value: Decimal | None) -> Decimal | None:
    return quantize(value, FACTOR_QUANT)


def quantize_rpe(value: Decimal | None) -> Decimal | None:
    return quantize(value, RPE_QUANT)


def quantize_distance(value: Decimal | None) -> Decimal | None:
    return quantize(value, DISTANCE_QUANT)


def quantize_kg(value: Decimal) -> Decimal:
    """Match NUMERIC(7,3) exactly, so a value reads the same before and after a
    database round-trip. Without this the API returns 72.5 on write and 72.500
    on read, and the client has to normalize what the server should have."""
    return _q(Decimal(value))


def lb_to_kg(pounds: Decimal) -> Decimal:
    return _q(Decimal(pounds) * LB_PER_KG)


def kg_to_lb(kilograms: Decimal) -> Decimal:
    return _q(Decimal(kilograms) / LB_PER_KG)


def round_to_increment(value: Decimal, increment: Decimal) -> Decimal:
    """Sec 3.2 - never suggest a load the user cannot physically build."""
    if increment <= 0:
        raise ValueError("increment must be positive")
    steps = (Decimal(value) / increment).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return _q(steps * increment)


def epley_1rm(weight_kg: Decimal, reps: int) -> Decimal | None:
    """Sec 13.3. Returns None where the estimate would not be trustworthy."""
    if weight_kg is None or reps is None:
        return None
    if reps < 1 or reps > E1RM_MAX_REPS:
        return None
    if weight_kg <= 0:
        return None
    return _q(Decimal(weight_kg) * (1 + Decimal(reps) / Decimal(30)))


def effective_load(
    *,
    bodyweight_kg: Decimal | None,
    factor: Decimal | None,
    added_kg: Decimal | None,
) -> Decimal | None:
    """Sec 13.2. None when bodyweight is unknown - reported as unavailable,
    never as zero."""
    if bodyweight_kg is None:
        return None
    f = DEFAULT_BODYWEIGHT_LOAD_FACTOR if factor is None else Decimal(factor)
    added = Decimal(0) if added_kg is None else Decimal(added_kg)
    return _q(Decimal(bodyweight_kg) * f + added)


def set_volume(
    *,
    metric_type: MetricType,
    weight_kg: Decimal | None,
    reps: int | None,
    bodyweight_kg: Decimal | None = None,
    bodyweight_factor: Decimal | None = None,
) -> Decimal | None:
    """Sec 13.1. Volume is defined per metric type; None means 'not defined for
    this kind of set', which is different from zero."""
    if metric_type in (MetricType.TIME, MetricType.DISTANCE, MetricType.TIME_DISTANCE):
        return None
    if reps is None or reps <= 0:
        return None

    if metric_type is MetricType.WEIGHT_REPS:
        if weight_kg is None:
            return None
        return _q(Decimal(weight_kg) * reps)

    load = effective_load(
        bodyweight_kg=bodyweight_kg,
        factor=bodyweight_factor,
        added_kg=weight_kg if metric_type is MetricType.WEIGHTED_BODYWEIGHT else None,
    )
    if load is None:
        return None
    return _q(load * reps)
