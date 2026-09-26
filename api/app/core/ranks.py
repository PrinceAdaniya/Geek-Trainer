"""Streak levels.

A streak on its own is a number. Attaching a rank to it gives the number a
shape - you can see the next one coming, which is the whole point of a streak.

Thresholds are in consecutive training days (app/repo/stats.py defines what
counts). Kept server-side so the client cannot drift from it, and exposed
through /stats so the UI never hardcodes the ladder.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rank:
    level: int
    name: str
    threshold: int
    band: int          # 0-3, picks the accent
    color: str
    blurb: str


# Four accents, not ten. A ten-hue ladder cannot pass a colourblind-separation
# check - purple against magenta is a Delta E of 0.4 for a protan viewer, which
# is invisible. So the ladder escalates through four validated accents, and the
# level number and rank name are always rendered beside the colour, so identity
# never rests on hue alone. Validated against the #101114 surface: CVD Delta E
# 8.5, normal-vision 17.3, all four above 3:1 contrast.
BAND_COLORS = ("#7dd3a0", "#6ba9ff", "#fbbf24", "#f87171")
DORMANT_COLOR = "#5f6368"

RANKS: tuple[Rank, ...] = (
    Rank(0, "No streak", 0, 0, DORMANT_COLOR, "Log a workout to start your streak."),
    Rank(1, "Starter", 1, 0, BAND_COLORS[0], "Your streak has started."),
    Rank(2, "Regular", 3, 0, BAND_COLORS[0], "3 consecutive training days."),
    Rank(3, "Committed", 5, 1, BAND_COLORS[1], "5 consecutive training days."),
    Rank(4, "Consistent", 8, 1, BAND_COLORS[1], "8 consecutive training days."),
    Rank(5, "Bronze", 12, 2, BAND_COLORS[2], "12 consecutive training days."),
    Rank(6, "Silver", 18, 2, BAND_COLORS[2], "18 consecutive training days."),
    Rank(7, "Gold", 25, 3, BAND_COLORS[3], "25 consecutive training days."),
    Rank(8, "Platinum", 35, 3, BAND_COLORS[3], "35 consecutive training days."),
    Rank(9, "Diamond", 50, 3, BAND_COLORS[3], "50 consecutive training days. The highest level."),
)

# Sequential single-hue ramp for the training-day heatmap - magnitude, not
# identity. Monotone lightness, gaps >= 0.06, light end clears the surface.
HEATMAP_RAMP = ("#5a1f45", "#8a2a5e", "#c23a78", "#f25897", "#ffa3c8")


def rank_for(streak: int) -> Rank:
    current = RANKS[0]
    for rank in RANKS:
        if streak >= rank.threshold:
            current = rank
    return current


def next_rank(streak: int) -> Rank | None:
    for rank in RANKS:
        if rank.threshold > streak:
            return rank
    return None


def progress_to_next(streak: int) -> float:
    """0.0-1.0 toward the next rank. 1.0 at the top of the ladder."""
    current = rank_for(streak)
    upcoming = next_rank(streak)
    if upcoming is None:
        return 1.0
    span = upcoming.threshold - current.threshold
    if span <= 0:
        return 1.0
    return min(1.0, max(0.0, (streak - current.threshold) / span))
