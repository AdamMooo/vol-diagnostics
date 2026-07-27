"""Tests for engine/monitor/monitor_reader.py -- bulk/trail/event read adapters.

Cold-start (sparse/absent stores) is the PRIMARY tested path here, not an edge
case: the real out/monitor store today holds 0-2 dates, so the board and evidence
panels must render off placeholder rows without ever raising. Mirrors
test_store.py's tmp_path + store-override fixtures.
"""
from __future__ import annotations

import datetime

import pandas as pd
import pytest

from engine.monitor import monitor_reader
from engine.monitor.schema import METRIC_INVENTORY


@pytest.fixture
def ranks_store(tmp_path):
    return tmp_path / "ranks.parquet"


@pytest.fixture
def events_store(tmp_path):
    return tmp_path / "alert_events.parquet"


def _row(date, ticker, metric, level_deep=90, value=1.0):
    return {
        "date": date, "ticker": ticker, "metric": metric,
        "value": value, "level_rank_deep": level_deep, "n_deep": 300,
        "level_rank_1yr": 88, "n_1yr": 252, "change_rank": 50, "change_n": 247,
        "band_state_deep": "out", "band_state_1yr": "out", "band_state_change": "out",
    }


class TestLoadAllCurrentRanks:
    def test_full_inventory_against_sparse_two_date_store(self, ranks_store):
        # Store holds only 2 dates for a single pair -> every other pair must
        # still appear as a placeholder row so the board renders all 17 tiles.
        rows = [
            _row(datetime.date(2026, 1, 3), "SPY", "vrp"),
            _row(datetime.date(2026, 1, 4), "SPY", "vrp"),
        ]
        pd.DataFrame(rows).to_parquet(ranks_store, index=False)

        result = monitor_reader.load_all_current_ranks(store=ranks_store)
        assert len(result) == len(METRIC_INVENTORY)
        pairs = set(zip(result["ticker"], result["metric"]))
        assert pairs == {(t, m) for (m, t) in METRIC_INVENTORY}

    def test_latest_per_pair_not_global_latest(self, ranks_store):
        rows = [
            _row(datetime.date(2026, 1, 3), "SPY", "vrp", level_deep=10),
            _row(datetime.date(2026, 1, 5), "SPY", "vrp", level_deep=95),
            # QQQ vrp only has an earlier date; must still return THAT pair's latest.
            _row(datetime.date(2026, 1, 4), "QQQ", "vrp", level_deep=42),
        ]
        pd.DataFrame(rows).to_parquet(ranks_store, index=False)

        result = monitor_reader.load_all_current_ranks(store=ranks_store)
        spy = result[(result["ticker"] == "SPY") & (result["metric"] == "vrp")].iloc[0]
        qqq = result[(result["ticker"] == "QQQ") & (result["metric"] == "vrp")].iloc[0]
        assert spy["level_rank_deep"] == 95  # latest SPY date, not global
        assert qqq["level_rank_deep"] == 42  # QQQ's own latest, an earlier date

    def test_absent_store_returns_placeholder_rows(self, ranks_store):
        result = monitor_reader.load_all_current_ranks(store=ranks_store)
        assert len(result) == len(METRIC_INVENTORY)
        assert result["level_rank_deep"].isna().all()
        assert result["value"].isna().all()
        assert (result["n_deep"] == 0).all()

    def test_all_nan_latest_row_passes_through_without_crash(self, ranks_store):
        rows = [
            {
                "date": datetime.date(2026, 1, 5), "ticker": "SPY", "metric": "vrp",
                "value": None, "level_rank_deep": None, "n_deep": 0,
                "level_rank_1yr": None, "n_1yr": 0, "change_rank": None, "change_n": 0,
                "band_state_deep": "out", "band_state_1yr": "out", "band_state_change": "out",
            }
        ]
        pd.DataFrame(rows).to_parquet(ranks_store, index=False)
        result = monitor_reader.load_all_current_ranks(store=ranks_store)
        spy = result[(result["ticker"] == "SPY") & (result["metric"] == "vrp")].iloc[0]
        assert pd.isna(spy["level_rank_deep"])
        assert len(result) == len(METRIC_INVENTORY)

    def test_corrupt_store_degrades_to_placeholders(self, ranks_store, capsys):
        ranks_store.write_bytes(b"not a parquet file")
        result = monitor_reader.load_all_current_ranks(store=ranks_store)
        assert len(result) == len(METRIC_INVENTORY)
        assert "[CORRUPT]" in capsys.readouterr().out


class TestLoadRankTrail:
    def test_returns_pair_rows_ascending_tail_n(self, ranks_store):
        rows = [
            _row(datetime.date(2026, 1, d), "SPY", "vrp", level_deep=d)
            for d in range(1, 13)
        ]
        pd.DataFrame(rows).to_parquet(ranks_store, index=False)
        trail = monitor_reader.load_rank_trail("SPY", "vrp", n=10, store=ranks_store)
        assert len(trail) == 10
        assert list(trail["date"]) == sorted(trail["date"])  # ascending
        assert trail["date"].iloc[-1] == datetime.date(2026, 1, 12)  # latest last

    def test_n_none_returns_full_history(self, ranks_store):
        rows = [
            _row(datetime.date(2026, 1, d), "SPY", "vrp") for d in range(1, 13)
        ]
        pd.DataFrame(rows).to_parquet(ranks_store, index=False)
        trail = monitor_reader.load_rank_trail("SPY", "vrp", n=None, store=ranks_store)
        assert len(trail) == 12

    def test_empty_dataframe_when_pair_absent(self, ranks_store):
        rows = [_row(datetime.date(2026, 1, 3), "SPY", "vrp")]
        pd.DataFrame(rows).to_parquet(ranks_store, index=False)
        trail = monitor_reader.load_rank_trail("IWM", "fly_25d", store=ranks_store)
        assert isinstance(trail, pd.DataFrame)
        assert trail.empty

    def test_empty_dataframe_when_store_absent(self, ranks_store):
        trail = monitor_reader.load_rank_trail("SPY", "vrp", store=ranks_store)
        assert isinstance(trail, pd.DataFrame)
        assert trail.empty


class TestLoadRecentAlertEvents:
    def test_absent_store_returns_empty_dataframe(self, events_store):
        result = monitor_reader.load_recent_alert_events(store=events_store)
        assert isinstance(result, pd.DataFrame)
        assert result.empty
        # Columns still present so downstream code can select safely.
        assert "rank_kind" in result.columns

    def test_filters_to_recent_days_sorted(self, events_store):
        today = datetime.date.today()
        events = [
            {
                "date": today - datetime.timedelta(days=5), "ticker": "SPY", "metric": "vrp",
                "rank_kind": "level_deep", "alert_type": "entry",
                "rank_at_transition": 98, "prior_state": "out",
            },
            {
                "date": today, "ticker": "QQQ", "metric": "skew_25d",
                "rank_kind": "change", "alert_type": "escalation",
                "rank_at_transition": 99, "prior_state": "in_entry",
            },
        ]
        pd.DataFrame(events).to_parquet(events_store, index=False)
        result = monitor_reader.load_recent_alert_events(days=1, store=events_store)
        assert len(result) == 1
        assert result.iloc[0]["ticker"] == "QQQ"

    def test_corrupt_store_degrades_to_empty(self, events_store, capsys):
        events_store.write_bytes(b"garbage")
        result = monitor_reader.load_recent_alert_events(store=events_store)
        assert result.empty
        assert "[CORRUPT]" in capsys.readouterr().out
