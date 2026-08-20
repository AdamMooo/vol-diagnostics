"""Tests for engine/monitor/monitor_store.py -- parquet stores + orchestration.

Uses store param-overrides for testability, mirroring engine/data/validation.py's
`store` param-override pattern.
"""
from __future__ import annotations

import datetime

import pandas as pd
import pytest

from engine.monitor import monitor_store


@pytest.fixture
def ranks_store(tmp_path):
    return tmp_path / "ranks.parquet"


@pytest.fixture
def events_store(tmp_path):
    return tmp_path / "alert_events.parquet"


class TestSaveMonitorRow:
    def test_idempotent_on_date_ticker_metric(self, ranks_store):
        row = {
            "date": datetime.date(2026, 1, 5), "ticker": "SPY", "metric": "vrp",
            "value": 1.2, "level_rank_deep": 90, "n_deep": 300,
            "level_rank_1yr": 88, "n_1yr": 252, "change_rank": 50, "change_n": 247,
            "band_state_deep": "out", "band_state_1yr": "out", "band_state_change": "out",
        }
        monitor_store.save_monitor_row(row, store=ranks_store)
        monitor_store.save_monitor_row(row, store=ranks_store)
        hist = pd.read_parquet(ranks_store)
        assert len(hist) == 1


class TestSaveAlertEvent:
    def test_rewriting_the_same_transition_does_not_duplicate_it(self, events_store):
        """Re-running a day (run_daily --force) recomputes the same transition,
        because load_prior_monitor_row looks strictly BEFORE today and still sees
        yesterday's state. This previously appended, and stored history showed two
        events written nine times each -- which would have sent nine emails for one
        event once alerting was wired up."""
        event = {
            "date": datetime.date(2026, 1, 5), "ticker": "SPY", "metric": "vrp",
            "rank_kind": "level_deep", "alert_type": "entry",
            "rank_at_transition": 98, "prior_state": "out",
        }
        for _ in range(9):
            monitor_store.save_alert_event(dict(event), store=events_store)
        assert len(pd.read_parquet(events_store)) == 1

    def test_distinct_transitions_are_all_kept(self, events_store):
        base = {
            "date": datetime.date(2026, 1, 5), "ticker": "SPY", "metric": "vrp",
            "rank_kind": "level_deep", "alert_type": "entry",
            "rank_at_transition": 98, "prior_state": "out",
        }
        monitor_store.save_alert_event(dict(base), store=events_store)
        monitor_store.save_alert_event(dict(base, ticker="QQQ"), store=events_store)
        monitor_store.save_alert_event(dict(base, alert_type="escalation"), store=events_store)
        monitor_store.save_alert_event(dict(base, date=datetime.date(2026, 1, 6)), store=events_store)
        assert len(pd.read_parquet(events_store)) == 4

    def test_a_corrected_rerun_updates_the_stored_row(self, events_store):
        base = {
            "date": datetime.date(2026, 1, 5), "ticker": "SPY", "metric": "vrp",
            "rank_kind": "level_deep", "alert_type": "entry",
            "rank_at_transition": 98, "prior_state": "out",
        }
        monitor_store.save_alert_event(dict(base), store=events_store)
        monitor_store.save_alert_event(dict(base, rank_at_transition=91), store=events_store)
        hist = pd.read_parquet(events_store)
        assert len(hist) == 1 and hist.iloc[0]["rank_at_transition"] == 91


class TestLoadPriorMonitorRow:
    def test_returns_most_recent_row_before_date(self, ranks_store):
        rows = [
            {
                "date": d, "ticker": "SPY", "metric": "vrp",
                "value": 1.0, "level_rank_deep": 50, "n_deep": 300,
                "level_rank_1yr": 50, "n_1yr": 252, "change_rank": 50, "change_n": 247,
                "band_state_deep": "in_entry", "band_state_1yr": "out", "band_state_change": "out",
            }
            for d in (datetime.date(2026, 1, 3), datetime.date(2026, 1, 4))
        ]
        for r in rows:
            monitor_store.save_monitor_row(r, store=ranks_store)
        result = monitor_store.load_prior_monitor_row("SPY", "vrp", datetime.date(2026, 1, 5), store=ranks_store)
        assert result is not None
        assert result["date"] == datetime.date(2026, 1, 4)
        assert result["band_state_deep"] == "in_entry"

    def test_returns_none_when_store_absent(self, ranks_store):
        assert monitor_store.load_prior_monitor_row("SPY", "vrp", datetime.date(2026, 1, 5), store=ranks_store) is None


class TestComputeAndSaveMonitorRows:
    def test_never_raises_when_metric_history_missing(self, monkeypatch, tmp_path):
        monkeypatch.setattr(monitor_store, "RANKS_STORE", tmp_path / "ranks.parquet")
        monkeypatch.setattr(monitor_store, "ALERT_EVENTS_STORE", tmp_path / "alert_events.parquet")
        monkeypatch.setattr(monitor_store.metrics, "load_metric_series", lambda ticker, metric: None)

        written = monitor_store.compute_and_save_monitor_rows(
            "SPY", {"ticker": "SPY"}, datetime.date(2026, 1, 5),
            band_entry=97, band_escalate=99, band_exit=87,
        )
        assert isinstance(written, int)
        assert written >= 0

    def test_writes_row_per_metric_for_ticker(self, monkeypatch, tmp_path):
        monkeypatch.setattr(monitor_store, "RANKS_STORE", tmp_path / "ranks.parquet")
        monkeypatch.setattr(monitor_store, "ALERT_EVENTS_STORE", tmp_path / "alert_events.parquet")

        history = pd.Series(range(1, 301), dtype=float)

        def fake_loader(ticker, metric):
            return history

        monkeypatch.setattr(monitor_store.metrics, "load_metric_series", fake_loader)
        monkeypatch.setattr(monitor_store, "save_monitor_row", lambda row: pd.DataFrame())

        # patch save_monitor_row/save_alert_event to write to tmp stores directly
        def save_row(row, store=None):
            path = store if store is not None else monitor_store.RANKS_STORE
            path.parent.mkdir(parents=True, exist_ok=True)
            df = pd.DataFrame([row])
            if path.exists():
                df = pd.concat([pd.read_parquet(path), df], ignore_index=True)
            df.to_parquet(path, index=False)

        def save_event(event, store=None):
            path = store if store is not None else monitor_store.ALERT_EVENTS_STORE
            path.parent.mkdir(parents=True, exist_ok=True)
            df = pd.DataFrame([event])
            if path.exists():
                df = pd.concat([pd.read_parquet(path), df], ignore_index=True)
            df.to_parquet(path, index=False)

        monkeypatch.setattr(monitor_store, "save_monitor_row", save_row)
        monkeypatch.setattr(monitor_store, "save_alert_event", save_event)

        written = monitor_store.compute_and_save_monitor_rows(
            "SPY", {"ticker": "SPY"}, datetime.date(2026, 1, 5),
            band_entry=97, band_escalate=99, band_exit=87,
        )
        # SPY has 7 metrics in METRIC_INVENTORY: vrp, skew_25d, fly_25d,
        # surface_level, surface_rms, term_9d_30, term_30_3m
        assert written == 7

    def test_stale_history_skips_value_and_warns(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(monitor_store, "RANKS_STORE", tmp_path / "ranks.parquet")
        monkeypatch.setattr(monitor_store, "ALERT_EVENTS_STORE", tmp_path / "alert_events.parquet")

        today = datetime.date(2026, 1, 5)
        stale_last = today - datetime.timedelta(days=1)
        dates = pd.date_range(end=stale_last, periods=300, freq="D").date
        history = pd.Series(range(1, 301), index=dates, dtype=float)

        monkeypatch.setattr(monitor_store.metrics, "load_metric_series", lambda ticker, metric: history)

        saved_rows = []
        monkeypatch.setattr(monitor_store, "save_monitor_row", lambda row, store=None: saved_rows.append(row))
        monkeypatch.setattr(monitor_store, "save_alert_event", lambda event, store=None: None)

        written = monitor_store.compute_and_save_monitor_rows(
            "SPY", {"ticker": "SPY"}, today,
            band_entry=97, band_escalate=99, band_exit=87,
        )

        assert written == 7
        assert len(saved_rows) == 7
        assert all(row["value"] is None for row in saved_rows)
        # CR-03: a stale day must not fabricate a change rank from history's own
        # last diff — every rank is None when there is no reading today.
        assert all(row["change_rank"] is None for row in saved_rows)
        assert all(row["level_rank_deep"] is None for row in saved_rows)
        captured = capsys.readouterr()
        assert "stale" in captured.out

    def test_stale_day_does_not_fire_change_alert(self, monkeypatch, tmp_path):
        # CR-03 integration: flat history with a single large jump in the final
        # k-window makes the fabricated change (abs_changes.iloc[-1]) rank ~100 and
        # fire an "entry" from "out" under the buggy code. With the fix, no reading
        # today => no change rank => no alert.
        monkeypatch.setattr(monitor_store, "RANKS_STORE", tmp_path / "ranks.parquet")
        monkeypatch.setattr(monitor_store, "ALERT_EVENTS_STORE", tmp_path / "alert_events.parquet")

        today = datetime.date(2026, 1, 5)
        stale_last = today - datetime.timedelta(days=1)
        dates = pd.date_range(end=stale_last, periods=300, freq="D").date
        values = [100.0] * 299 + [1100.0]  # flat, then a lone spike in the last k-window
        history = pd.Series(values, index=dates, dtype=float)
        monkeypatch.setattr(monitor_store.metrics, "load_metric_series", lambda ticker, metric: history)

        events = []
        monkeypatch.setattr(monitor_store, "save_alert_event", lambda event, store=None: events.append(event))

        monitor_store.compute_and_save_monitor_rows(
            "SPY", {"ticker": "SPY"}, today,
            band_entry=97, band_escalate=99, band_exit=87,
        )
        assert not any(e["rank_kind"] == "change" for e in events)

    def test_stale_day_holds_active_level_alert(self, monkeypatch, tmp_path):
        # CR-02 integration: an in_escalate alert from a prior day must be HELD on
        # a stale day, not collapsed to "out" by the credibility-floor gate.
        monkeypatch.setattr(monitor_store, "RANKS_STORE", tmp_path / "ranks.parquet")
        monkeypatch.setattr(monitor_store, "ALERT_EVENTS_STORE", tmp_path / "alert_events.parquet")

        today = datetime.date(2026, 1, 5)
        prior_row = {
            "date": today - datetime.timedelta(days=1), "ticker": "SPY", "metric": "vrp",
            "value": 1.0, "level_rank_deep": 99, "n_deep": 300,
            "level_rank_1yr": 99, "n_1yr": 252, "change_rank": 50, "change_n": 247,
            "band_state_deep": "in_escalate", "band_state_1yr": "out", "band_state_change": "out",
        }
        monitor_store.save_monitor_row(prior_row, store=monitor_store.RANKS_STORE)

        stale_last = today - datetime.timedelta(days=1)
        dates = pd.date_range(end=stale_last, periods=300, freq="D").date
        history = pd.Series(range(1, 301), index=dates, dtype=float)
        monkeypatch.setattr(monitor_store.metrics, "load_metric_series", lambda ticker, metric: history)
        monkeypatch.setattr(monitor_store, "save_alert_event", lambda event, store=None: None)

        monitor_store.compute_and_save_monitor_rows(
            "SPY", {"ticker": "SPY"}, today,
            band_entry=97, band_escalate=99, band_exit=87,
        )

        saved = pd.read_parquet(monitor_store.RANKS_STORE)
        vrp_today = saved[(saved["metric"] == "vrp") & (saved["date"] == today)].iloc[0]
        assert vrp_today["band_state_deep"] == "in_escalate"
