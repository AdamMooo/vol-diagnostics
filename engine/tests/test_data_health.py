"""Tests for the idempotency guard in run_daily and the health_check module."""
from __future__ import annotations

import datetime
import pathlib
import sys
import unittest.mock as mock
from unittest.mock import patch, MagicMock

import pandas as pd
import pandas_market_calendars as mcal
import pytest


# ---------------------------------------------------------------------------
# run_daily idempotency tests
# ---------------------------------------------------------------------------

class TestAlreadyCollectedToday:
    """Tests for _already_collected_today() in run_daily."""

    def test_returns_false_when_store_missing(self, tmp_path):
        """No store file → not collected."""
        from engine.run_daily import _already_collected_today
        with patch("engine.run_daily.SNAPSHOT_STORE", tmp_path / "nonexistent.parquet"):
            assert _already_collected_today(datetime.date(2026, 6, 25)) is False

    def test_returns_false_when_partial_collection(self, tmp_path):
        """Store has today for SPY/QQQ but not IWM → not complete."""
        from engine.run_daily import _already_collected_today
        store = tmp_path / "gex_snapshots.parquet"
        df = pd.DataFrame({
            "date": [datetime.date(2026, 6, 25)] * 2,
            "ticker": ["SPY", "QQQ"],
            "spot": [550.0, 480.0],
        })
        df.to_parquet(store, index=False)
        with patch("engine.run_daily.SNAPSHOT_STORE", store):
            assert _already_collected_today(datetime.date(2026, 6, 25)) is False

    def test_returns_true_when_all_tickers_present(self, tmp_path):
        """Store has today for all 3 tickers → already collected."""
        from engine.run_daily import _already_collected_today
        store = tmp_path / "gex_snapshots.parquet"
        df = pd.DataFrame({
            "date": [datetime.date(2026, 6, 25)] * 3,
            "ticker": ["SPY", "QQQ", "IWM"],
            "spot": [550.0, 480.0, 210.0],
        })
        df.to_parquet(store, index=False)
        with patch("engine.run_daily.SNAPSHOT_STORE", store):
            assert _already_collected_today(datetime.date(2026, 6, 25)) is True

    def test_returns_false_for_different_date(self, tmp_path):
        """Store has data for yesterday, not today → not collected."""
        from engine.run_daily import _already_collected_today
        store = tmp_path / "gex_snapshots.parquet"
        df = pd.DataFrame({
            "date": [datetime.date(2026, 6, 24)] * 3,
            "ticker": ["SPY", "QQQ", "IWM"],
            "spot": [550.0, 480.0, 210.0],
        })
        df.to_parquet(store, index=False)
        with patch("engine.run_daily.SNAPSHOT_STORE", store):
            assert _already_collected_today(datetime.date(2026, 6, 25)) is False


class TestRunIdempotencyGuard:
    """Integration test: run() skips when data already collected."""

    @patch("engine.run_daily.is_trading_day", return_value=True)
    @patch("engine.run_daily._already_collected_today", return_value=True)
    def test_skips_when_already_collected(self, mock_collected, mock_trading, capsys):
        from engine.run_daily import run
        run(dry_run=True, force=False)
        captured = capsys.readouterr()
        assert "already collected" in captured.out

    @patch("engine.run_daily.is_trading_day", return_value=True)
    @patch("engine.run_daily._already_collected_today", return_value=True)
    @patch("engine.run_daily.refresh_vol_indices")
    @patch("engine.run_daily.compute_ticker")
    def test_force_overrides_guard(self, mock_compute, mock_refresh,
                                   mock_collected, mock_trading):
        """--force should bypass the idempotency guard."""
        from engine.run_daily import run
        mock_compute.return_value = {"summary": {"ticker": "SPY", "error": "test"}}
        # All tickers error → run() exits non-zero, but only AFTER bypassing the
        # guard and calling compute_ticker — which is what --force must do.
        with pytest.raises(SystemExit):
            run(dry_run=True, force=True)
        assert mock_compute.called


# ---------------------------------------------------------------------------
# health_check tests
# ---------------------------------------------------------------------------

class TestHealthCheck:
    """Tests for the health_check module."""

    @patch("engine.health_check.list_available_dates", return_value=[])
    @patch("engine.health_check.load_history")
    def test_missing_data_reports_unhealthy(self, mock_hist, mock_dates):
        """No data at all → unhealthy."""
        from engine.health_check import check_health
        mock_hist.return_value = pd.DataFrame()
        result = check_health(verbose=False)
        assert result["healthy"] is False
        for ticker_info in result["tickers"].values():
            assert ticker_info["status"] == "MISSING"

    @patch("engine.health_check._last_expected_session")
    @patch("engine.health_check.list_available_dates")
    @patch("engine.health_check.load_history")
    def test_current_data_reports_healthy(self, mock_hist, mock_dates, mock_expected):
        """Data as of last expected session → healthy."""
        from engine.health_check import check_health
        today = datetime.date(2026, 6, 25)
        mock_expected.return_value = today
        mock_dates.return_value = [today]
        mock_hist.return_value = pd.DataFrame({"date": [today], "ticker": ["SPY"]})
        result = check_health(verbose=False)
        assert result["healthy"] is True

    @patch("engine.health_check._last_expected_session")
    @patch("engine.health_check.list_available_dates")
    @patch("engine.health_check.load_history")
    def test_stale_data_reports_gap(self, mock_hist, mock_dates, mock_expected):
        """Data 2 days old → STALE with gap count."""
        from engine.health_check import check_health
        expected = datetime.date(2026, 6, 25)
        actual = datetime.date(2026, 6, 23)
        mock_expected.return_value = expected
        mock_dates.return_value = [actual]
        mock_hist.return_value = pd.DataFrame({"date": [actual], "ticker": ["SPY"]})
        result = check_health(verbose=False)
        assert result["healthy"] is False
        # At least one ticker should show STALE
        assert any("STALE" in info["status"] for info in result["tickers"].values())


# ---------------------------------------------------------------------------
# full-history gap scan tests
# ---------------------------------------------------------------------------

class TestFullHistoryGapScan:
    """Tests for the full-history gap scanner (D-03/D-04/D-05)."""

    def _surface_df(self, dates, ticker="SPY"):
        return pd.DataFrame({
            "date": dates,
            "ticker": [ticker] * len(dates),
            "spot": [500.0] * len(dates),
            "dte": [30.0] * len(dates),
            "strike": [500.0] * len(dates),
            "moneyness": [1.0] * len(dates),
            "log_moneyness": [0.0] * len(dates),
            "iv_pct": [20.0] * len(dates),
        })

    def test_no_false_positives_on_complete_history(self, tmp_path, monkeypatch):
        """A complete daily history for a 2-week NYSE window has zero gaps."""
        import engine.data.surface_history as sh_mod
        monkeypatch.setattr(sh_mod, "STORE_DIR", tmp_path)

        nyse = mcal.get_calendar("NYSE")
        sched = nyse.schedule(start_date="2026-06-01", end_date="2026-06-14")
        sessions = sorted(d.date() for d in sched.index)

        df = self._surface_df(sessions)
        df.to_parquet(tmp_path / "surface_SPY.parquet", index=False)

        from engine.health_check import _series_dates, _full_history_scan
        dates = _series_dates("SPY", "surface_history")
        dates_by_series = {"surface_history": dates}
        scan = _full_history_scan(dates, dates_by_series, "surface_history")
        assert scan["gap_count"] == 0

    def test_detects_gap_in_middle_of_history(self, tmp_path, monkeypatch):
        """A session dropped from the middle of the range (not the tail) is flagged."""
        import engine.data.surface_history as sh_mod
        monkeypatch.setattr(sh_mod, "STORE_DIR", tmp_path)

        nyse = mcal.get_calendar("NYSE")
        sched = nyse.schedule(start_date="2026-06-01", end_date="2026-06-14")
        sessions = sorted(d.date() for d in sched.index)
        assert len(sessions) >= 5

        dropped_date = sessions[len(sessions) // 2]
        kept_sessions = [d for d in sessions if d != dropped_date]

        df = self._surface_df(kept_sessions)
        df.to_parquet(tmp_path / "surface_SPY.parquet", index=False)

        from engine.health_check import _series_dates, _full_history_scan
        dates = _series_dates("SPY", "surface_history")
        dates_by_series = {"surface_history": dates}
        scan = _full_history_scan(dates, dates_by_series, "surface_history")
        assert scan["gap_count"] == 1
        assert str(dropped_date) in [g["date"] for g in scan["gaps"]]

    def test_vol_index_holiday_not_flagged_when_no_other_series_collected(self):
        """A session missing from ALL series (CBOE/NYSE holiday) is not a vol_index gap."""
        from engine.health_check import _full_history_scan, get_nyse_sessions
        sessions = sorted(get_nyse_sessions(datetime.date(2026, 6, 1), datetime.date(2026, 6, 10)))
        assert len(sessions) >= 4
        d1, d2, d3, d4 = sessions[0], sessions[1], sessions[2], sessions[3]

        # d3 is missing from every series — simulates a day nothing was published.
        other_dates = {d1, d2, d4}
        dates_by_series = {
            "vol_index": other_dates,
            "gex_snapshots": other_dates,
            "surface_history": other_dates,
            "oi_history": other_dates,
        }
        scan = _full_history_scan(other_dates, dates_by_series, "vol_index")
        gap_dates = [g["date"] for g in scan["gaps"]]
        assert str(d3) not in gap_dates

    def test_vol_index_flagged_when_other_series_collected(self):
        """A session missing ONLY from vol_index (other 3 series collected it) is flagged."""
        from engine.health_check import _full_history_scan, get_nyse_sessions
        sessions = sorted(get_nyse_sessions(datetime.date(2026, 6, 1), datetime.date(2026, 6, 10)))
        assert len(sessions) >= 4
        d1, d2, d3, d4 = sessions[0], sessions[1], sessions[2], sessions[3]

        vol_index_dates = {d1, d2, d4}  # d3 missing from vol_index only
        full_dates = {d1, d2, d3, d4}
        dates_by_series = {
            "vol_index": vol_index_dates,
            "gex_snapshots": full_dates,
            "surface_history": full_dates,
            "oi_history": full_dates,
        }
        scan = _full_history_scan(vol_index_dates, dates_by_series, "vol_index")
        gap_reasons = {g["date"]: g["reason"] for g in scan["gaps"]}
        assert str(d3) in gap_reasons
        assert "other series collected" in gap_reasons[str(d3)]

    def test_series_dates_gex_snapshots_filters_by_ticker(self, tmp_path):
        """_series_dates('SPY', 'gex_snapshots') returns only SPY's dates, not QQQ's."""
        store = tmp_path / "gex_snapshots.parquet"
        df = pd.DataFrame({
            "date": [datetime.date(2026, 6, 1), datetime.date(2026, 6, 2), datetime.date(2026, 6, 1)],
            "ticker": ["SPY", "SPY", "QQQ"],
        })
        df.to_parquet(store, index=False)

        with mock.patch("engine.data.validation.STORE", store):
            from engine.health_check import _series_dates
            result = _series_dates("SPY", "gex_snapshots")

        assert result == {datetime.date(2026, 6, 1), datetime.date(2026, 6, 2)}


# ---------------------------------------------------------------------------
# combined --strict gate tests
# ---------------------------------------------------------------------------

class TestHealthCheckStrict:
    """Tests for main()'s operational freshness --strict gate."""

    def test_strict_ignores_full_history_gaps_when_tail_check_is_healthy(self, monkeypatch):
        from engine.health_check import main
        monkeypatch.setattr(
            "engine.health_check.check_health",
            lambda verbose=True: {"healthy": True, "expected": "2026-06-01", "tickers": {}},
        )
        monkeypatch.setattr(
            "engine.health_check.full_history_report",
            lambda verbose=True: {"clean": False, "series": {}},
        )
        monkeypatch.setattr(sys, "argv", ["health_check", "--strict"])
        main()  # should not raise SystemExit

    def test_strict_exits_zero_when_both_clean(self, monkeypatch):
        from engine.health_check import main
        monkeypatch.setattr(
            "engine.health_check.check_health",
            lambda verbose=True: {"healthy": True, "expected": "2026-06-01", "tickers": {}},
        )
        monkeypatch.setattr(
            "engine.health_check.full_history_report",
            lambda verbose=True: {"clean": True, "series": {}},
        )
        monkeypatch.setattr(sys, "argv", ["health_check", "--strict"])
        main()  # should not raise SystemExit

    def test_strict_exits_nonzero_when_tail_check_is_unhealthy(self, monkeypatch):
        from engine.health_check import main
        monkeypatch.setattr(
            "engine.health_check.check_health",
            lambda verbose=True: {"healthy": False, "expected": "2026-06-01", "tickers": {}},
        )
        monkeypatch.setattr(
            "engine.health_check.full_history_report",
            lambda verbose=True: {"clean": True, "series": {}},
        )
        monkeypatch.setattr(sys, "argv", ["health_check", "--strict"])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# model-readiness depth audit tests (Plan 23-04, SCHEMA-01/02)
# ---------------------------------------------------------------------------

class TestModelReadinessAudit:
    """Tests for depth_audit() -- current data depth vs. model-ready targets."""

    def test_reports_meets_when_depth_at_or_above_target(self):
        from engine.health_check import depth_audit
        import datetime as dt

        def fake_series_dates(ticker, series):
            if series == "surface_history":
                return {dt.date(2020, 1, 1) + dt.timedelta(days=i) for i in range(251)}
            return set()

        with patch("engine.health_check._series_dates", side_effect=fake_series_dates):
            result = depth_audit(verbose=False)

        for ticker in ("SPY", "QQQ", "IWM"):
            assert result["series"][ticker]["surface_history"]["meets_target"] is True

    def test_reports_short_when_depth_below_target(self):
        from engine.health_check import depth_audit
        import datetime as dt

        def fake_series_dates(ticker, series):
            if series == "gex_snapshots":
                return {dt.date(2020, 1, 1) + dt.timedelta(days=i) for i in range(10)}
            return set()

        with patch("engine.health_check._series_dates", side_effect=fake_series_dates):
            result = depth_audit(verbose=False)

        for ticker in ("SPY", "QQQ", "IWM"):
            info = result["series"][ticker]["gex_snapshots"]
            assert info["meets_target"] is False
            assert info["depth"] == 10

    def test_all_four_series_all_three_tickers_present(self):
        from engine.health_check import depth_audit, SERIES_NAMES
        import datetime as dt

        fixed = {dt.date(2020, 1, 1) + dt.timedelta(days=i) for i in range(300)}
        with patch("engine.health_check._series_dates", return_value=fixed):
            result = depth_audit(verbose=False)

        assert set(result["series"].keys()) == {"SPY", "QQQ", "IWM"}
        for ticker in ("SPY", "QQQ", "IWM"):
            assert set(result["series"][ticker].keys()) == set(SERIES_NAMES)

    def test_vol_index_target_matches_config_constant(self):
        from engine.health_check import MODEL_READY_TARGETS
        from engine.config import VRP_DEEP_LOOKBACK_SESSIONS

        assert MODEL_READY_TARGETS["vol_index"] == VRP_DEEP_LOOKBACK_SESSIONS

    def test_all_ready_false_when_any_series_short(self):
        from engine.health_check import depth_audit
        import datetime as dt

        def fake_series_dates(ticker, series):
            if series == "gex_snapshots" and ticker == "SPY":
                return {dt.date(2020, 1, 1)}  # far short of target
            return {dt.date(2020, 1, 1) + dt.timedelta(days=i) for i in range(3000)}

        with patch("engine.health_check._series_dates", side_effect=fake_series_dates):
            result = depth_audit(verbose=False)

        assert result["all_ready"] is False
