"""Display-boundary conversion. Storage is always kg (SPECIFICATIONS.MD 3.1)."""

from __future__ import annotations

from decimal import Decimal

from app.core.formulas import kg_to_lb, lb_to_kg
from app.domain.enums import Unit


def to_display(weight_kg: Decimal | None, unit: Unit) -> Decimal | None:
    if weight_kg is None:
        return None
    return weight_kg if unit is Unit.KG else kg_to_lb(weight_kg)


def to_storage(value: Decimal | None, unit: Unit) -> Decimal | None:
    if value is None:
        return None
    return Decimal(value) if unit is Unit.KG else lb_to_kg(value)
