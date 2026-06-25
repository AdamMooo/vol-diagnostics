"""Tests for the idempotency guard in run_daily and the health_check module."""
from __future__ import annotations

import datetime
import pathlib
from unittest.mock import patch, MagicMock

import pandas as pd
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
        # Won't finish (all error), but it should get past the guard
        run(dry_run=True, force=True)
        # If we got here, the guard was bypassed (compute_ticker was called)
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
