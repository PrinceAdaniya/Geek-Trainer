"""SPECIFICATIONS.MD Sec 13 and Sec 3, PLAN.md D7.

Includes acceptance criterion A5 (bodyweight and time-based work), and the
storage half of A11 (switching display units changes no stored value).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.core.formulas import (
    effective_load,
    epley_1rm,
    kg_to_lb,
    lb_to_kg,
    round_to_increment,
    set_volume,
)
from app.core.units import to_display, to_storage
from app.domain.enums import MetricType, Unit


def D(x) -> Decimal:
    return Decimal(str(x))


class TestUnits:
    def test_pound_conversion_is_exact_both_ways(self):
        assert lb_to_kg(D(100)) == D("45.359")
        assert kg_to_lb(D("45.359237")) == D(100)

    def test_a11_display_unit_does_not_change_storage(self):
        """A11: switching kg to lb changes no stored value."""
        stored = D("60.000")
        assert to_display(stored, Unit.KG) == stored
        assert to_display(stored, Unit.LB) == kg_to_lb(stored)
        # And the stored value is untouched by having been displayed.
        assert stored == D("60.000")

    def test_round_trip_through_pounds_is_stable(self):
        original = D("60.000")
        assert to_storage(to_display(original, Unit.LB), Unit.LB) == original

    @pytest.mark.parametrize(
        "value,increment,expected",
        [
            ("61.3", "1.25", "61.25"),
            ("61.9", "1.25", "62.5"),
            ("62.4", "2.5", "62.5"),
            ("60.2", "0.5", "60.0"),
        ],
    )
    def test_increments_are_loads_you_can_actually_build(self, value, increment, expected):
        assert round_to_increment(D(value), D(increment)) == D(expected)

    def test_increment_must_be_positive(self):
        with pytest.raises(ValueError):
            round_to_increment(D(60), D(0))


class TestEpley:
    def test_known_values(self):
        assert epley_1rm(D(60), 10) == D("80.000")
        assert epley_1rm(D(100), 1) == D("103.333")

    def test_refuses_above_twelve_reps(self):
        """Sec 13.3 - above 12 the estimate is not reliable, so we do not show
        one rather than showing a bad one."""
        assert epley_1rm(D(60), 12) is not None
        assert epley_1rm(D(60), 13) is None

    def test_refuses_nonsense(self):
        assert epley_1rm(D(60), 0) is None
        assert epley_1rm(D(0), 5) is None
        assert epley_1rm(None, 5) is None


class TestVolume:
    def test_weight_reps(self):
        assert set_volume(
            metric_type=MetricType.WEIGHT_REPS, weight_kg=D(60), reps=10
        ) == D("600.000")

    def test_a5_bodyweight_reps_are_not_zero_volume(self):
        """A5: 12 pull-ups must produce non-zero volume."""
        volume = set_volume(
            metric_type=MetricType.BODYWEIGHT_REPS,
            weight_kg=None,
            reps=12,
            bodyweight_kg=D(75),
            bodyweight_factor=D(1),
        )
        assert volume == D("900.000")
        assert volume > 0

    def test_bodyweight_factor_is_applied(self):
        """A push-up is not a pull-up."""
        assert set_volume(
            metric_type=MetricType.BODYWEIGHT_REPS,
            weight_kg=None,
            reps=10,
            bodyweight_kg=D(75),
            bodyweight_factor=D("0.64"),
        ) == D("480.000")

    def test_weighted_bodyweight_adds_the_belt(self):
        assert set_volume(
            metric_type=MetricType.WEIGHTED_BODYWEIGHT,
            weight_kg=D(20),
            reps=5,
            bodyweight_kg=D(75),
            bodyweight_factor=D(1),
        ) == D("475.000")

    def test_assisted_reps_use_negative_added_weight(self):
        assert set_volume(
            metric_type=MetricType.WEIGHTED_BODYWEIGHT,
            weight_kg=D(-20),
            reps=5,
            bodyweight_kg=D(75),
            bodyweight_factor=D(1),
        ) == D("275.000")

    def test_a5_time_based_work_has_no_volume_but_is_representable(self):
        """A5: a 90-second plank is recordable; volume is simply not defined
        for it, which is different from being zero."""
        assert set_volume(metric_type=MetricType.TIME, weight_kg=None, reps=None) is None
        assert set_volume(
            metric_type=MetricType.DISTANCE, weight_kg=None, reps=None
        ) is None

    def test_unknown_bodyweight_is_unavailable_not_zero(self):
        """Sec 13.2 - reporting zero would silently understate the user's work."""
        assert set_volume(
            metric_type=MetricType.BODYWEIGHT_REPS,
            weight_kg=None,
            reps=10,
            bodyweight_kg=None,
        ) is None


class TestEffectiveLoad:
    def test_defaults_to_full_bodyweight(self):
        assert effective_load(bodyweight_kg=D(75), factor=None, added_kg=None) == D("75.000")

    def test_none_without_a_bodyweight(self):
        assert effective_load(bodyweight_kg=None, factor=D(1), added_kg=D(10)) is None
