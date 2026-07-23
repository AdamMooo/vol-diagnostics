"""Tests for engine/monitor/calibration.py -- calibration replay engine.

Behavior tests per 26-03-PLAN.md Task 1.
"""
from __future__ import annotations

import pandas as pd

from engine.monitor.calibration import (
    calibrate,
    count_episodes_per_week,
    replay_metric,
)


def _dates(n: int) -> pd.DatetimeIndex:
    return pd.bdate_range("2020-01-01", periods=n)


class TestReplayMetric:
    def test_returns_list_of_events_walking_series_day_by_day(self):
        n = 300
        values = [100.0] * n
        history = pd.Series(values, index=_dates(n))
        events = replay_metric(history, entry=97, escalate=99, exit_=87, credibility_floor=252)
        assert isinstance(events, list)
        # constant series -> percentile always at top of its own history -> may fire,
        # but every event must have the expected shape
        for ev in events:
            assert "date" in ev and "alert_type" in ev and "rank" in ev

    def test_single_spike_produces_one_entry_event_not_one_per_day(self):
        n = 300
        values = [50.0] * n
        # 3-day excursion, comfortably above the 97th percentile of the flat baseline
        values[280] = 1000.0
        values[281] = 1000.0
        values[282] = 1000.0
        history = pd.Series(values, index=_dates(n))
        events = replay_metric(history, entry=97, escalate=99, exit_=87, credibility_floor=252)
        entry_events = [e for e in events if e["alert_type"] == "entry"]
        assert len(entry_events) == 1

    def test_no_lookahead(self):
        n = 300
        values = [float(i % 50) for i in range(n)]
        history = pd.Series(values, index=_dates(n))
        events_a = replay_metric(history, entry=97, escalate=99, exit_=87, credibility_floor=252)

        mutated = history.copy()
        mutated.iloc[290:] = 99999.0
        events_b = replay_metric(mutated, entry=97, escalate=99, exit_=87, credibility_floor=252)

        # Events before index 290 must be identical regardless of what happens after.
        a_before = [e for e in events_a if history.index.get_loc(e["date"]) < 290]
        b_before = [e for e in events_b if history.index.get_loc(e["date"]) < 290]
        assert a_before == b_before


class TestCountEpisodesPerWeek:
    def test_converts_event_count_to_weekly_rate(self):
        events = [{"date": d, "alert_type": "entry", "rank": 98} for d in _dates(5)]
        rate = count_episodes_per_week(events, total_sessions=500)
        assert rate == len(events) / (500 / 5)


class TestCalibrate:
    def test_runs_across_grid_and_returns_sorted_results(self):
        result = calibrate(candidate_bands=[90, 97], hysteresis_gaps=[5, 10])
        assert "results" in result
        results = result["results"]
        assert len(results) == 2 * 2
        for r in results:
            assert set(r.keys()) >= {
                "band_entry", "band_escalate", "band_exit",
                "episodes_per_week", "flicker_ratio",
            }
        # sorted by closeness to 1.0 eps/week ascending
        deltas = [abs(r["episodes_per_week"] - 1.0) for r in results]
        assert deltas == sorted(deltas)

    def test_skips_metrics_with_no_history_without_crashing(self, monkeypatch):
        import engine.monitor.calibration as calib_mod

        def _none_loader(ticker, metric_name):
            return None

        monkeypatch.setattr(calib_mod.metrics, "load_metric_series", _none_loader)
        result = calibrate(candidate_bands=[97], hysteresis_gaps=[10])
        assert result["results"][0]["episodes_per_week"] == 0.0
