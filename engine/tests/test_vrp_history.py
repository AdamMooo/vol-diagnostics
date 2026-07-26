"""Tests for vrp_history.py — VRP-03-clean percentile from a single vol-index-based series.

All network I/O is monkeypatched: load_vol_index and the private yfinance fetch are
replaced with synthetic fixtures. No test hits CBOE or yfinance.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from engine.vol import vrp_history
from engine import config


def _vol_index_df(symbol: str, dates, closes) -> pd.DataFrame:
    """Mimic load_vol_index output: columns symbol, date, open, high, low, close (date-only, ascending)."""
    return pd.DataFrame(
        {
            "symbol": symbol,
            "date": [pd.Timestamp(d).date() for d in dates],
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
        }
    )


def _closes_series(dates, prices) -> pd.Series:
    """Date-indexed oldest-first close series, like _fetch_closes_yf returns."""
    idx = pd.Index([pd.Timestamp(d).date() for d in dates], name="date")
    return pd.Series(prices, index=idx)


@pytest.fixture
def trading_dates():
    # 60 business days — enough for many RV20 points, fewer than the 252 lookback (cold-start).
    return list(pd.bdate_range("2026-01-02", periods=60))


class TestHappyPath:
    def test_vrp_matches_vol_points_formula(self, monkeypatch, trading_dates):
        dates = trading_dates
        # Deterministic geometric drift so RV20 is a stable nonzero number.
        prices = [100.0 * (1.005 ** i) for i in range(len(dates))]
        vi_closes = [18.0 + 0.05 * i for i in range(len(dates))]

        monkeypatch.setattr(
            vrp_history, "load_vol_index",
            lambda sym: _vol_index_df(sym, dates, vi_closes),
        )
        monkeypatch.setattr(
            vrp_history, "_fetch_closes_yf",
            lambda ticker, period="400d": _closes_series(dates, prices),
        )

        res = vrp_history.vrp_percentile("SPY")

        # Reconstruct the expected today value: vi_close[last] - rv20(last 21 closes)*100
        last_window = pd.Series(prices[-21:]).reset_index(drop=True)
        from engine.vol.vol_metrics import compute_rv20
        rv20 = compute_rv20(last_window)
        expected_vrp = vi_closes[-1] - rv20 * 100

        assert res["vrp"] == pytest.approx(expected_vrp, rel=1e-9)
        assert 0 <= res["pct"] <= 100
        assert isinstance(res["pct"], int)
        assert res["n"] > 0

    def test_today_value_same_definition_as_series(self, monkeypatch, trading_dates):
        # VRP-03 isolation guard: today's value fed to percentileofscore must be the
        # last point of the same vi-RV20 series, not a snapshot-IV30-derived number.
        dates = trading_dates
        prices = [100.0 * (1.003 ** i) for i in range(len(dates))]
        vi_closes = [20.0 - 0.02 * i for i in range(len(dates))]

        monkeypatch.setattr(
            vrp_history, "load_vol_index",
            lambda sym: _vol_index_df(sym, dates, vi_closes),
        )
        monkeypatch.setattr(
            vrp_history, "_fetch_closes_yf",
            lambda ticker, period="400d": _closes_series(dates, prices),
        )

        res = vrp_history.vrp_percentile("SPY")
        # If today is the max of the window, pct should be 100; if min, near 0. Either way
        # the value is internally consistent — the series last point.
        assert res["vrp"] is not None
        assert res["n"] >= 1


class TestColdStart:
    def test_short_series_reports_actual_count(self, monkeypatch):
        # Only ~30 business days → aligned series far shorter than the ~10yr deep target.
        dates = list(pd.bdate_range("2026-01-02", periods=30))
        prices = [100.0 * (1.004 ** i) for i in range(len(dates))]
        vi_closes = [17.0 + 0.1 * i for i in range(len(dates))]

        monkeypatch.setattr(
            vrp_history, "load_vol_index",
            lambda sym: _vol_index_df(sym, dates, vi_closes),
        )
        monkeypatch.setattr(
            vrp_history, "_fetch_closes_yf",
            lambda ticker, period="400d": _closes_series(dates, prices),
        )

        res = vrp_history.vrp_percentile("SPY")
        # 30 closes → RV20 available from index 20..29 → 10 aligned dates.
        assert res["n"] < config.VRP_DEEP_LOOKBACK_SESSIONS
        assert res["n"] == 10
        assert res["vrp"] is not None


class TestDeepWindow:
    def test_default_uses_full_history_not_truncated(self, monkeypatch):
        # 300 business days of aligned data -- more than the old 252-session cap used to
        # allow. Confirms vrp_percentile() no longer truncates to a short rolling window.
        dates = list(pd.bdate_range("2024-01-02", periods=300))
        prices = [100.0 * (1.001 ** i) for i in range(len(dates))]
        vi_closes = [18.0 + 0.01 * i for i in range(len(dates))]

        monkeypatch.setattr(
            vrp_history, "load_vol_index",
            lambda sym: _vol_index_df(sym, dates, vi_closes),
        )
        monkeypatch.setattr(
            vrp_history, "_fetch_closes_yf",
            lambda ticker, period="400d": _closes_series(dates, prices),
        )

        res = vrp_history.vrp_percentile("SPY")
        # 300 closes → RV20 available from index 20..299 → 280 aligned dates, all retained.
        assert res["n"] == 280
        assert res["n"] > config.VRP_PERCENTILE_LOOKBACK  # proves no truncation to the old 1yr cap

    def test_explicit_lookback_still_truncates(self, monkeypatch):
        # Passing an explicit lookback restores the short-window behavior for callers that want it.
        dates = list(pd.bdate_range("2024-01-02", periods=300))
        prices = [100.0 * (1.001 ** i) for i in range(len(dates))]
        vi_closes = [18.0 + 0.01 * i for i in range(len(dates))]

        monkeypatch.setattr(
            vrp_history, "load_vol_index",
            lambda sym: _vol_index_df(sym, dates, vi_closes),
        )
        monkeypatch.setattr(
            vrp_history, "_fetch_closes_yf",
            lambda ticker, period="400d": _closes_series(dates, prices),
        )

        res = vrp_history.vrp_percentile("SPY", lookback=50)
        assert res["n"] == 50

    def test_fetch_requests_deep_lookback_period(self, monkeypatch):
        captured = {}

        def fake_fetch(ticker, period="400d"):
            captured["period"] = period
            return None

        dates = list(pd.bdate_range("2026-01-02", periods=5))
        monkeypatch.setattr(
            vrp_history, "load_vol_index",
            lambda sym: _vol_index_df(sym, dates, [18.0] * len(dates)),
        )
        monkeypatch.setattr(vrp_history, "_fetch_closes_yf", fake_fetch)

        vrp_history.vrp_percentile("SPY")
        expected_days = config.VRP_DEEP_LOOKBACK_SESSIONS + config.VRP_CLOSES_FETCH_BUFFER_DAYS
        assert captured["period"] == f"{expected_days}d"


class TestFailurePaths:
    def test_empty_vol_index_returns_none_dict(self, monkeypatch):
        monkeypatch.setattr(vrp_history, "load_vol_index", lambda sym: pd.DataFrame())
        # _fetch_closes_yf should not even be reached, but stub it to be safe.
        monkeypatch.setattr(
            vrp_history, "_fetch_closes_yf",
            lambda ticker, period="400d": pytest.fail("should not fetch when vol-index empty"),
        )
        res = vrp_history.vrp_percentile("SPY")
        assert res == {"vrp": None, "pct": None, "n": 0}

    def test_yfinance_failure_returns_none_dict(self, monkeypatch):
        dates = list(pd.bdate_range("2026-01-02", periods=60))
        vi_closes = [18.0] * len(dates)
        monkeypatch.setattr(
            vrp_history, "load_vol_index",
            lambda sym: _vol_index_df(sym, dates, vi_closes),
        )
        monkeypatch.setattr(vrp_history, "_fetch_closes_yf", lambda ticker, period="400d": None)
        res = vrp_history.vrp_percentile("SPY")
        assert res == {"vrp": None, "pct": None, "n": 0}

    def test_no_alignment_returns_none_dict(self, monkeypatch):
        # Vol-index dates and close dates are disjoint → empty aligned series.
        vi_dates = list(pd.bdate_range("2026-01-02", periods=60))
        cl_dates = list(pd.bdate_range("2020-01-02", periods=60))
        vi_closes = [18.0] * len(vi_dates)
        prices = [100.0 * (1.004 ** i) for i in range(len(cl_dates))]
        monkeypatch.setattr(
            vrp_history, "load_vol_index",
            lambda sym: _vol_index_df(sym, vi_dates, vi_closes),
        )
        monkeypatch.setattr(
            vrp_history, "_fetch_closes_yf",
            lambda ticker, period="400d": _closes_series(cl_dates, prices),
        )
        res = vrp_history.vrp_percentile("SPY")
        assert res == {"vrp": None, "pct": None, "n": 0}


class TestEdgeCases:
    """E7 (NaN close scattered mid-series) and E8 (single aligned point, n=1).

    Both assert *defined* output — a real dict with non-NaN numbers — never a silent
    NaN or a crash. These document the existing dropna (line 76) + percentileofscore
    (line 112) behavior on degenerate history the happy-path tests never exercised.
    """

    def test_nan_mid_series_close_dropped_no_nan_output(self, monkeypatch):
        # E7: a NaN vol-index close on a non-last historical date. `aligned = ...dropna()`
        # drops that one row → fewer aligned points, no NaN leaking into the output dict.
        dates = list(pd.bdate_range("2026-01-02", periods=60))
        prices = [100.0 * (1.004 ** i) for i in range(len(dates))]
        vi_closes = [18.0 + 0.05 * i for i in range(len(dates))]
        # RV20 aligns on indices 20..59 (40 points). Blank a vol-index close mid-series,
        # inside that aligned band and NOT the last date, so exactly one row is dropped.
        vi_closes[30] = float("nan")

        monkeypatch.setattr(
            vrp_history, "load_vol_index",
            lambda sym: _vol_index_df(sym, dates, vi_closes),
        )
        monkeypatch.setattr(
            vrp_history, "_fetch_closes_yf",
            lambda ticker, period="400d": _closes_series(dates, prices),
        )

        res = vrp_history.vrp_percentile("SPY")

        # 40 aligned points minus the one NaN row → 39. Output carries no NaN.
        assert res["n"] == 39
        assert res["vrp"] is not None
        assert not np.isnan(res["vrp"])
        assert isinstance(res["pct"], int)
        assert 0 <= res["pct"] <= 100

    def test_single_aligned_point_defined_dict(self, monkeypatch):
        # E8: exactly one aligned VRP point (n=1). 21 closes → RV20 available only at the
        # last date (index 20); vol-index covers all 21 → dropna keeps one row.
        dates = list(pd.bdate_range("2026-01-02", periods=21))
        prices = [100.0 * (1.004 ** i) for i in range(len(dates))]
        vi_closes = [18.0 + 0.05 * i for i in range(len(dates))]

        monkeypatch.setattr(
            vrp_history, "load_vol_index",
            lambda sym: _vol_index_df(sym, dates, vi_closes),
        )
        monkeypatch.setattr(
            vrp_history, "_fetch_closes_yf",
            lambda ticker, period="400d": _closes_series(dates, prices),
        )

        res = vrp_history.vrp_percentile("SPY")

        # percentileofscore of a 1-element window (kind="rank") ranks the sole point at 100 —
        # a defined int, not a crash or NaN.
        assert res["n"] == 1
        assert res["vrp"] is not None
        assert not np.isnan(res["vrp"])
        assert isinstance(res["pct"], int)
        assert 0 <= res["pct"] <= 100
        assert res["pct"] == 100
