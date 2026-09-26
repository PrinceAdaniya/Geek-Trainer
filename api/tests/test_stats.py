"""Streaks, ranks and headline numbers. SPECIFICATIONS.MD Sec 14."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.core.ranks import next_rank, progress_to_next, rank_for
from app.repo.stats import StatsRepo

API = "/api/v1"


class TestStreakMath:
    """Pure, so it can be tested without inventing months of session history."""

    def _d(self, *offsets: int) -> list[date]:
        base = date(2026, 8, 31)
        return sorted(base - timedelta(days=o) for o in offsets)

    def test_no_history_is_no_streak(self):
        assert StatsRepo.streaks([], date(2026, 8, 31)) == (0, 0)

    def test_consecutive_days_count(self):
        dates = self._d(2, 1, 0)
        assert StatsRepo.streaks(dates, date(2026, 8, 31)) == (3, 3)

    def test_a_rest_day_does_not_break_it(self):
        """Rest is training. Breaking a streak for a sensible day off would
        push people to train when they should not."""
        dates = self._d(4, 2, 0)
        current, longest = StatsRepo.streaks(dates, date(2026, 8, 31))
        assert current == 3

    def test_a_long_gap_does_break_it(self):
        dates = self._d(20, 19, 18)
        current, longest = StatsRepo.streaks(dates, date(2026, 8, 31))
        assert current == 0
        assert longest == 3

    def test_the_longest_streak_is_remembered_after_a_lapse(self):
        dates = self._d(40, 39, 38, 37, 1, 0)
        current, longest = StatsRepo.streaks(dates, date(2026, 8, 31))
        assert current == 2
        assert longest == 4

    def test_training_yesterday_keeps_the_streak_alive(self):
        dates = self._d(1)
        assert StatsRepo.streaks(dates, date(2026, 8, 31))[0] == 1


class TestRanks:
    def test_zero_is_dormant(self):
        assert rank_for(0).name == "No streak"

    def test_the_ladder_only_goes_up(self):
        from app.core.ranks import RANKS

        thresholds = [r.threshold for r in RANKS]
        assert thresholds == sorted(thresholds)
        assert len({r.name for r in RANKS}) == len(RANKS)

    def test_a_streak_lands_on_the_right_rung(self):
        assert rank_for(1).name == "Starter"
        assert rank_for(4).name == "Regular"
        assert rank_for(12).name == "Bronze"
        assert rank_for(999).name == "Diamond"

    def test_progress_runs_zero_to_one_between_rungs(self):
        assert progress_to_next(0) == 0.0
        assert 0 < progress_to_next(2) < 1
        assert progress_to_next(999) == 1.0

    def test_the_top_rung_has_no_next(self):
        assert next_rank(999) is None
        assert next_rank(0) is not None


class TestStatsEndpoint:
    def test_a_new_user_starts_dormant_with_nothing(self, user_client):
        stats = user_client.get(f"{API}/stats").json()
        assert stats["current_streak"] == 0
        assert stats["total_sessions"] == 0
        assert stats["rank"]["name"] == "No streak"
        assert stats["next_rank"]["name"] == "Starter"
        assert stats["volume_this_week_kg"] == "0"

    def test_the_ladder_is_served_so_the_client_never_hardcodes_it(self, user_client):
        ladder = user_client.get(f"{API}/stats").json()["ladder"]
        assert len(ladder) >= 8
        assert ladder[0]["name"] == "No streak"

    def test_finishing_a_session_lights_the_streak(self, user_client):
        vocab = user_client.get(f"{API}/vocabulary").json()
        user_client.put(f"{API}/profile", json={"available_equipment": vocab["equipment"]})

        exercise_id = user_client.get(
            f"{API}/exercises", params={"q": "barbell row"}
        ).json()["data"][0]["id"]
        session = user_client.post(f"{API}/sessions", json={"name": "Day one"}).json()
        se = user_client.post(
            f"{API}/sessions/{session['id']}/exercises",
            json={"exercise_id": exercise_id},
        ).json()["exercises"][0]
        user_client.post(
            f"{API}/sessions/{session['id']}/exercises/{se['id']}/sets",
            json={"weight": 60, "reps": 10},
        )
        user_client.post(f"{API}/sessions/{session['id']}/finish")

        stats = user_client.get(f"{API}/stats").json()
        assert stats["current_streak"] == 1
        assert stats["total_sessions"] == 1
        assert stats["sessions_this_week"] == 1
        assert stats["sets_this_week"] == 1
        assert stats["trained_today"] is True
        assert stats["rank"]["name"] == "Starter"
        assert stats["volume_this_week_kg"] == "600.000"

    def test_warmups_do_not_count_toward_volume(self, user_client):
        """Sec 10.3 - and the number on the dashboard is the first place
        someone would notice if they did."""
        vocab = user_client.get(f"{API}/vocabulary").json()
        user_client.put(f"{API}/profile", json={"available_equipment": vocab["equipment"]})
        exercise_id = user_client.get(
            f"{API}/exercises", params={"q": "barbell row"}
        ).json()["data"][0]["id"]

        session = user_client.post(f"{API}/sessions", json={"name": "Warmups"}).json()
        se = user_client.post(
            f"{API}/sessions/{session['id']}/exercises",
            json={"exercise_id": exercise_id},
        ).json()["exercises"][0]
        for set_type in ("warmup", "working"):
            user_client.post(
                f"{API}/sessions/{session['id']}/exercises/{se['id']}/sets",
                json={"weight": 60, "reps": 10, "set_type": set_type},
            )
        user_client.post(f"{API}/sessions/{session['id']}/finish")

        stats = user_client.get(f"{API}/stats").json()
        assert stats["sets_this_week"] == 1
        assert stats["volume_this_week_kg"] == "600.000"

    def test_stats_are_private(self, client):
        from tests.conftest import register

        register(client)
        client.cookies.clear()
        assert client.get(f"{API}/stats").status_code == 401
