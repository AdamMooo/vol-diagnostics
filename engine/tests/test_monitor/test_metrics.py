"""Tests for engine/monitor/metrics.py — per-metric history loader dispatch.

All store reads are monkeypatched at the module boundary (pd.read_parquet or the
underlying loader function) — no test touches out/ on disk.
"""
from __future__ import annotations

import datetime

import pandas as pd
import pytest

from engine.monitor import metrics
from engine.vol import vrp_history


def _gex_snapshots_df():
    dates = list(pd.bdate_range("2026-01-02", periods=10))
    return pd.DataFrame({
        "date": dates,
        "ticker": ["SPY"] * 10,
        "front_skew": [1.0 + i * 0.1 for i in range(10)],
        "butterfly": [0.5 + i * 0.05 for i in range(10)],
    })


def _evolution_df(horizon=5):
    dates = list(pd.bdate_range("2026-01-02", periods=10))
    return pd.DataFrame({
        "date": dates,
        "ticker": ["SPY"] * 10,
        "horizon": [horizon] * 10,
        "level": [0.1 * i for i in range(10)],
        "rms": [0.2 * i for i in range(10)],
    })


def _vol_index_df(symbol, dates, closes):
    return pd.DataFrame({
        "symbol": symbol,
        "date": [pd.Timestamp(d).date() for d in dates],
        "open": closes, "high": closes, "low": closes, "close": closes,
    })


class TestSkewFly:
    def test_skew_25d_reads_front_skew(self, monkeypatch):
        monkeypatch.setattr(metrics, "_load_gex_snapshots", lambda: _gex_snapshots_df())
        series = metrics.load_metric_series("SPY", "skew_25d")
        assert series is not None
        assert len(series) == 10
        assert series.index.is_monotonic_increasing

    def test_fly_25d_reads_butterfly(self, monkeypatch):
        monkeypatch.setattr(metrics, "_load_gex_snapshots", lambda: _gex_snapshots_df())
        series = metrics.load_metric_series("SPY", "fly_25d")
        assert series is not None
        assert len(series) == 10


class TestSurfaceEvolution:
    def test_surface_level_filters_horizon_5(self, monkeypatch):
        monkeypatch.setattr(metrics, "_load_surface_evolution", lambda: _evolution_df(horizon=5))
        series = metrics.load_metric_series("SPY", "surface_level")
        assert series is not None
        assert len(series) == 10

    def test_surface_rms_filters_horizon_5(self, monkeypatch):
        monkeypatch.setattr(metrics, "_load_surface_evolution", lambda: _evolution_df(horizon=5))
        series = metrics.load_metric_series("SPY", "surface_rms")
        assert series is not None
        assert len(series) == 10

    def test_wrong_horizon_excluded(self, monkeypatch):
        monkeypatch.setattr(metrics, "_load_surface_evolution", lambda: _evolution_df(horizon=10))
        series = metrics.load_metric_series("SPY", "surface_level")
        assert series is None or len(series) == 0


class TestTermRatios:
    def test_term_9d_30_builds_ratio(self, monkeypatch):
        dates = list(pd.bdate_range("2026-01-02", periods=10))

        def fake_load_vol_index(symbol):
            if symbol == "VIX9D":
                return _vol_index_df(symbol, dates, [15.0] * 10)
            if symbol == "VIX":
                return _vol_index_df(symbol, dates, [20.0] * 10)
            return pd.DataFrame()

        monkeypatch.setattr(metrics, "load_vol_index", fake_load_vol_index)
        series = metrics.load_metric_series("SPY", "term_9d_30")
        assert series is not None
        assert len(series) == 10
        assert series.iloc[0] == pytest.approx(15.0 / 20.0)

    def test_term_30_3m_builds_ratio(self, monkeypatch):
        dates = list(pd.bdate_range("2026-01-02", periods=10))

        def fake_load_vol_index(symbol):
            if symbol == "VIX":
                return _vol_index_df(symbol, dates, [20.0] * 10)
            if symbol == "VIX3M":
                return _vol_index_df(symbol, dates, [22.0] * 10)
            return pd.DataFrame()

        monkeypatch.setattr(metrics, "load_vol_index", fake_load_vol_index)
        series = metrics.load_metric_series("SPY", "term_30_3m")
        assert series is not None
        assert series.iloc[0] == pytest.approx(20.0 / 22.0)

    def test_qqq_term_ratio_returns_none(self):
        assert metrics.load_metric_series("QQQ", "term_9d_30") is None
        assert metrics.load_metric_series("IWM", "term_9d_30") is None


class TestVrpDelegation:
    def test_vrp_delegates_to_vrp_history_series(self, monkeypatch):
        sentinel = pd.Series([1.0, 2.0, 3.0])
        monkeypatch.setattr(vrp_history, "vrp_history_series", lambda ticker: sentinel)
        series = metrics.load_metric_series("SPY", "vrp")
        assert series is sentinel


class TestUnknownAndFailure:
    def test_unknown_metric_returns_none(self):
        assert metrics.load_metric_series("SPY", "not_a_real_metric") is None

    def test_missing_store_returns_none(self, monkeypatch):
        monkeypatch.setattr(metrics, "_load_gex_snapshots", lambda: pd.DataFrame())
        assert metrics.load_metric_series("SPY", "skew_25d") is None
