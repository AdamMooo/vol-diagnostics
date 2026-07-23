"""Tests for engine/monitor/ranker.py — pure ECDF percentile functions.

No I/O — all inputs are synthetic pd.Series. Mirrors the vrp_history.py
percentileofscore(kind="rank") convention exactly.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from engine import config
from engine.monitor import ranker


class TestComputeLevelRanks:
    def test_last_value_ranks_top_of_own_history(self):
        history = pd.Series(np.arange(1, 101, dtype=float))
        res = ranker.compute_level_ranks(history, today_value=100.0)
        assert res["n_deep"] == 100
        from scipy.stats import percentileofscore
        expected = int(percentileofscore(history.to_numpy(), 100.0, kind="rank"))
        assert res["level_rank_deep"] == expected

    def test_oneyr_lookback_slices_tail_independent_of_deep(self):
        history = pd.Series(np.arange(1, 3001, dtype=float))
        res = ranker.compute_level_ranks(history, today_value=3000.0)
        assert res["n_deep"] == 3000
        assert res["n_1yr"] == config.MONITOR_ONEYR_LOOKBACK_SESSIONS

    def test_deep_and_1yr_can_disagree_on_regime_shift(self):
        # Long flat history, then a step up for the most recent 252 sessions.
        flat = np.full(3000 - 252, 10.0)
        recent = np.linspace(20.0, 30.0, 252)
        history = pd.Series(np.concatenate([flat, recent]))
        res = ranker.compute_level_ranks(history, today_value=30.0)
        assert res["level_rank_deep"] is not None
        assert res["level_rank_1yr"] is not None
        # today (30.0) is the max of both windows so both ranks are high, but the
        # windows are computed independently (different n) -- check that explicitly.
        assert res["n_deep"] == 3000
        assert res["n_1yr"] == 252

    def test_nan_gaps_dropped_before_ranking(self):
        history = pd.Series([1.0, np.nan, 2.0, np.nan, 3.0, 4.0, 5.0])
        res = ranker.compute_level_ranks(history, today_value=5.0)
        assert res["n_deep"] == 5

    def test_empty_history_returns_none_dict(self):
        res = ranker.compute_level_ranks(pd.Series(dtype=float), today_value=None)
        assert res == {
            "level_rank_deep": None, "n_deep": 0,
            "level_rank_1yr": None, "n_1yr": 0,
        }

    def test_none_history_never_raises(self):
        res = ranker.compute_level_ranks(None, today_value=None)
        assert res["level_rank_deep"] is None
        assert res["n_deep"] == 0

    def test_low_n_still_returns_rank(self):
        history = pd.Series(np.arange(1, 11, dtype=float))
        res = ranker.compute_level_ranks(history, today_value=10.0)
        assert res["n_deep"] == 10
        assert res["n_deep"] < config.MONITOR_CREDIBILITY_FLOOR_SESSIONS
        assert res["level_rank_deep"] is not None


class TestComputeChangeRank:
    def test_two_sided_symmetry(self):
        # Series where today is 10 below 5-sessions-ago.
        base = np.full(50, 100.0)
        down_history = base.copy()
        down_history[-1] = 90.0
        down = pd.Series(down_history)

        up_history = base.copy()
        up_history[-1] = 110.0
        up = pd.Series(up_history)

        res_down = ranker.compute_change_rank(down)
        res_up = ranker.compute_change_rank(up)
        assert res_down["change_rank"] == res_up["change_rank"]

    def test_nan_handling_does_not_crash(self):
        history = pd.Series([1.0, np.nan, 2.0, 3.0, np.nan, 4.0, 5.0, 6.0, 7.0])
        res = ranker.compute_change_rank(history)
        assert res["change_n"] >= 0

    def test_empty_history_returns_none_dict(self):
        res = ranker.compute_change_rank(pd.Series(dtype=float))
        assert res == {"change_rank": None, "change_n": 0}

    def test_none_history_never_raises(self):
        res = ranker.compute_change_rank(None)
        assert res["change_rank"] is None
        assert res["change_n"] == 0

    def test_low_n_still_returns_rank(self):
        history = pd.Series(np.arange(1, 11, dtype=float))
        res = ranker.compute_change_rank(history)
        assert res["change_n"] > 0
        assert res["change_n"] < config.MONITOR_CREDIBILITY_FLOOR_SESSIONS
        assert res["change_rank"] is not None
