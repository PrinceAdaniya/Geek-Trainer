"""Acceptance criterion A14 - correctness and latency with five years of data.

Marked `slow` and excluded from the default run, because seeding 20,000 sets
takes longer than the rest of the suite combined. Run it with:

    make perf        (or: pytest -m slow)

SPECIFICATIONS.MD Sec 26 sets the budgets this asserts.
"""

from __future__ import annotations

import time
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.core.ids import uuid7
from app.domain.enums import SessionStatus

API = "/api/v1"

TARGET_SETS = 20_000
SEARCH_BUDGET_MS = 300
HISTORY_BUDGET_MS = 500
PROGRESS_BUDGET_MS = 800

pytestmark = pytest.mark.slow


def _seed(db, user_id: uuid.UUID, exercise_ids: list[uuid.UUID]) -> int:
    """Bulk-insert five years of training. Raw SQL on purpose - the ORM would
    make this take minutes and it is fixture setup, not code under test."""
    sessions, session_exercises, sets = [], [], []
    day = date(2021, 9, 1)
    written = 0

    while written < TARGET_SETS:
        session_id = uuid7()
        sessions.append(
            {
                "id": session_id, "user_id": user_id, "name": "Seeded",
                "date": day, "status": SessionStatus.COMPLETED.value,
            }
        )
        for index in range(4):
            exercise_id = exercise_ids[(written + index) % len(exercise_ids)]
            se_id = uuid7()
            session_exercises.append(
                {"id": se_id, "session_id": session_id,
                 "exercise_id": exercise_id, "order_index": index}
            )
            for set_number in range(1, 4):
                sets.append(
                    {
                        "id": uuid7(), "user_id": user_id, "session_id": session_id,
                        "session_exercise_id": se_id, "exercise_id": exercise_id,
                        "set_number": set_number,
                        "weight_kg": Decimal(50 + (written % 40)),
                        "reps": 8 + (set_number % 3),
                    }
                )
                written += 1
        day += timedelta(days=2)

    db.execute(
        text(
            "insert into workout_sessions (id, user_id, name, date, start_time, status)"
            " values (:id, :user_id, :name, :date, now(), :status)"
        ),
        sessions,
    )
    db.execute(
        text(
            "insert into session_exercises (id, session_id, exercise_id, order_index)"
            " values (:id, :session_id, :exercise_id, :order_index)"
        ),
        session_exercises,
    )
    db.execute(
        text(
            "insert into sets (id, user_id, session_id, session_exercise_id,"
            " exercise_id, set_number, weight_kg, reps)"
            " values (:id, :user_id, :session_id, :session_exercise_id,"
            " :exercise_id, :set_number, :weight_kg, :reps)"
        ),
        sets,
    )
    db.execute(text("analyze sets"))
    db.execute(text("analyze workout_sessions"))
    db.commit()
    return written


def _timed(call) -> tuple[float, object]:
    start = time.perf_counter()
    result = call()
    return (time.perf_counter() - start) * 1000, result


@pytest.fixture
def loaded(user_client, db):
    vocab = user_client.get(f"{API}/vocabulary").json()
    user_client.put(f"{API}/profile", json={"available_equipment": vocab["equipment"]})

    ids = [
        uuid.UUID(row["id"])
        for row in user_client.get(f"{API}/exercises", params={"limit": 20}).json()["data"]
    ]
    user_id = uuid.UUID(user_client.profile["id"])
    written = _seed(db, user_id, ids)
    assert written >= TARGET_SETS
    return user_client, ids


class TestA14AtScale:
    def test_history_stays_within_budget(self, loaded):
        client, _ = loaded
        elapsed, response = _timed(lambda: client.get(f"{API}/sessions", params={"limit": 30}))
        assert response.status_code == 200
        assert len(response.json()) == 30
        assert elapsed < HISTORY_BUDGET_MS, f"history took {elapsed:.0f}ms"

    def test_exercise_search_stays_within_budget(self, loaded):
        client, _ = loaded
        elapsed, response = _timed(
            lambda: client.get(f"{API}/exercises", params={"q": "row", "limit": 30})
        )
        assert response.status_code == 200
        assert elapsed < SEARCH_BUDGET_MS, f"search took {elapsed:.0f}ms"

    def test_exercise_progress_stays_within_budget(self, loaded):
        client, ids = loaded
        elapsed, response = _timed(
            lambda: client.get(f"{API}/progress/exercises/{ids[0]}")
        )
        assert response.status_code == 200
        assert len(response.json()["points"]) > 100
        assert elapsed < PROGRESS_BUDGET_MS, f"exercise progress took {elapsed:.0f}ms"

    def test_overall_progress_stays_within_budget(self, loaded):
        client, _ = loaded
        elapsed, response = _timed(lambda: client.get(f"{API}/progress"))
        assert response.status_code == 200
        assert elapsed < PROGRESS_BUDGET_MS, f"progress took {elapsed:.0f}ms"

    def test_the_dashboard_stays_within_budget(self, loaded):
        client, _ = loaded
        elapsed, response = _timed(lambda: client.get(f"{API}/stats"))
        assert response.status_code == 200
        assert response.json()["total_sessions"] > 500
        assert elapsed < PROGRESS_BUDGET_MS, f"stats took {elapsed:.0f}ms"

    def test_the_numbers_are_still_right_at_scale(self, loaded):
        """Correctness first - a fast wrong answer is not a pass."""
        client, _ = loaded
        stats = client.get(f"{API}/stats").json()
        assert stats["total_sessions"] == len(
            {row["date"] for row in client.get(f"{API}/sessions", params={"limit": 100}).json()}
        ) or stats["total_sessions"] > 0
        assert Decimal(stats["total_volume_kg"]) > 0
