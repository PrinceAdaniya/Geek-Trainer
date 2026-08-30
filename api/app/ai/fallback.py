"""The deterministic twin of every AI feature. PLAN.md D12, Sec 18.1, 21.6.

Written first and shipped in an earlier phase than the AI path, so the AI is a
ranking-and-explaining layer over something that already works. This is what
makes "the app is completely usable with AI unavailable" true rather than
aspirational.
"""

from __future__ import annotations

from app.ai.candidates import CandidateSet
from app.ai.schemas import (
    AnalysisResult,
    GeneratedWorkout,
    PlannedExercise,
    RankedSubstitution,
    SubstitutionResult,
)

GOAL_REPS = {
    "strength": (3, 6),
    "hypertrophy": (8, 12),
    "endurance": (12, 20),
    "fat_loss": (10, 15),
    "general": (8, 12),
}
MINUTES_PER_SET = 3


def generate_workout(
    candidates: CandidateSet,
    *,
    targets: list[str],
    goal: str = "general",
    session_minutes: int = 60,
    avoid_exercise_ids: set | None = None,
) -> GeneratedWorkout:
    """Rules, not a model: filter to the candidates, order compound before
    isolation, spread across the target muscles, cap by session length."""
    reps_min, reps_max = GOAL_REPS.get(goal, GOAL_REPS["general"])
    sets_each = 4 if goal == "strength" else 3
    budget = max(1, (session_minutes // MINUTES_PER_SET) // sets_each)
    avoid = avoid_exercise_ids or set()

    picked = []
    used_muscles: dict[str, int] = {}
    for row in candidates.rows:
        if row.id in avoid:
            continue
        # Two exercises per muscle keeps a session from becoming six rows.
        if used_muscles.get(row.primary_muscle, 0) >= 2:
            continue
        picked.append(row)
        used_muscles[row.primary_muscle] = used_muscles.get(row.primary_muscle, 0) + 1
        if len(picked) >= budget:
            break

    return GeneratedWorkout(
        name=" + ".join(t.title() for t in targets[:2]) or "Workout",
        target_muscles=targets[:6],
        exercises=[
            PlannedExercise(
                exercise_id=row.id,
                sets=sets_each,
                reps_min=reps_min,
                reps_max=reps_max,
                rationale=(
                    f"{'Compound' if row.type == 'compound' else 'Isolation'} work "
                    f"for {row.primary_muscle.replace('-', ' ')}."
                ),
            )
            for row in picked
        ],
        notes="Built from your equipment and target muscles without AI.",
    )


def rank_substitutions(candidates: CandidateSet, *, replacing: str) -> SubstitutionResult:
    return SubstitutionResult(
        alternatives=[
            RankedSubstitution(
                exercise_id=row.id,
                why=(
                    f"Same primary muscle as {replacing}, "
                    f"using {', '.join(row.equipment)}."
                ),
            )
            for row in candidates.rows
        ]
        or [],
    )


def analyse(series: list[dict], *, exercise_name: str, unit: str = "kg") -> AnalysisResult:
    """The non-AI reading of a series: state the movement, refuse a trend on
    fewer than three sessions (Sec 19)."""
    if len(series) < 3:
        return AnalysisResult(
            observed=[
                f"You have logged {exercise_name} {len(series)} time"
                f"{'' if len(series) == 1 else 's'}."
            ],
            interpretation=[],
            suggestion="Log a few more sessions and this will have something to say.",
            enough_data=False,
        )

    first, last = series[0], series[-1]
    observed = [
        f"Top set went from {first['top_weight']} {unit} × {first['top_reps']} "
        f"on {first['date']} to {last['top_weight']} {unit} × {last['top_reps']} "
        f"on {last['date']}.",
        f"Session volume went from {round(first['volume'])} to "
        f"{round(last['volume'])} {unit} over {len(series)} sessions.",
    ]

    change = float(last["e1rm"] or 0) - float(first["e1rm"] or 0)
    if change > 0.5:
        interpretation = ["Estimated one-rep max is rising, so the current progression is working."]
        suggestion = "Keep adding load in small steps while the reps hold."
    elif change < -0.5:
        interpretation = ["Estimated one-rep max is lower than where it started."]
        suggestion = "Check sleep, food and how close to failure these sets are before adding load."
    else:
        interpretation = ["Estimated one-rep max is roughly flat."]
        suggestion = "Consider adding a set, or a small load increase, and hold the rep range."

    return AnalysisResult(
        observed=observed, interpretation=interpretation, suggestion=suggestion,
        enough_data=True,
    )
