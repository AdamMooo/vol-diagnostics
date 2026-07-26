"""Tests for Phase 17: VIX term-structure ratios."""
from __future__ import annotations

from unittest.mock import patch, MagicMock
import pandas as pd
import pytest

from engine.vol.vol_metrics import compute_term_ratios
from engine.report.card_model import build_card_fields, _fmt_term_ratios


# ── compute_term_ratios ───────────────────────────────────────────────────

def _mock_vol_index(symbol: str) -> pd.DataFrame:
    """Return mock vol-index DataFrames with known closes."""
    data = {
        "VIX9D": 15.0,
        "VIX": 18.0,
        "VIX3M": 20.0,
    }
    if symbol not in data:
        return pd.DataFrame()
    return pd.DataFrame([{"symbol": symbol, "date": "2026-06-23", "close": data[symbol]}])


@patch("engine.data.vol_index.load_vol_index", side_effect=_mock_vol_index)
def test_compute_term_ratios_spy(mock_load):
    result = compute_term_ratios("SPY")
    assert result["term_ratio_9d_30d"] == pytest.approx(15.0 / 18.0)
    assert result["term_ratio_30d_3m"] == pytest.approx(18.0 / 20.0)


@patch("engine.data.vol_index.load_vol_index", side_effect=_mock_vol_index)
def test_compute_term_ratios_qqq_graceful(mock_load):
    result = compute_term_ratios("QQQ")
    assert result["term_ratio_9d_30d"] is None
    assert result["term_ratio_30d_3m"] is None


@patch("engine.data.vol_index.load_vol_index", side_effect=_mock_vol_index)
def test_compute_term_ratios_iwm_graceful(mock_load):
    result = compute_term_ratios("IWM")
    assert result["term_ratio_9d_30d"] is None
    assert result["term_ratio_30d_3m"] is None


@patch("engine.data.vol_index.load_vol_index", return_value=pd.DataFrame())
def test_compute_term_ratios_missing_data(mock_load):
    """When vol-index store is empty, returns None for both ratios."""
    result = compute_term_ratios("SPY")
    assert result["term_ratio_9d_30d"] is None
    assert result["term_ratio_30d_3m"] is None


def _mock_nan_close(symbol: str) -> pd.DataFrame:
    """Last-row close is NaN — simulates a partial/corrupt CBOE fetch."""
    return pd.DataFrame([{"symbol": symbol, "date": "2026-06-23", "close": float("nan")}])


def _mock_zero_close(symbol: str) -> pd.DataFrame:
    """Last-row close is 0.0 — a nonsensical vol-index quote."""
    return pd.DataFrame([{"symbol": symbol, "date": "2026-06-23", "close": 0.0}])


@patch("engine.data.vol_index.load_vol_index", side_effect=_mock_nan_close)
def test_compute_term_ratios_nan_close_is_none(mock_load):
    """E13: a NaN last-row close yields None (not a truthy NaN float)."""
    result = compute_term_ratios("SPY")
    assert result["term_ratio_9d_30d"] is None
    assert result["term_ratio_30d_3m"] is None


@patch("engine.data.vol_index.load_vol_index", side_effect=_mock_zero_close)
def test_compute_term_ratios_zero_close_is_none(mock_load):
    """E14: a 0.0 last-row close yields None (division would be undefined/degenerate)."""
    result = compute_term_ratios("SPY")
    assert result["term_ratio_9d_30d"] is None
    assert result["term_ratio_30d_3m"] is None


# ── _fmt_term_ratios ──────────────────────────────────────────────────────

def test_fmt_term_ratios_both_contango():
    # Both < 1 = contango
    result = _fmt_term_ratios(0.85, 0.92)
    assert "contango" in result
    assert "9D/30" in result
    assert "30/3M" in result


def test_fmt_term_ratios_backwardation():
    result = _fmt_term_ratios(1.05, 1.02)
    assert "backwardation" in result


def test_fmt_term_ratios_none_none():
    result = _fmt_term_ratios(None, None)
    assert result == ""


def test_fmt_term_ratios_partial():
    result = _fmt_term_ratios(0.90, None)
    assert "9D/30" in result
    assert "30/3M" not in result


# ── CardField integration ─────────────────────────────────────────────────

def test_card_field_vix_term_spy_present():
    """SPY summary with term ratios produces a VIX Term field."""
    summary = {
        "spot": 550.0, "price_change_pct": 0.5, "iv30": 18.0,
        "expected_move_pct": 1.2, "em_expiry": "2026-06-27", "em_dte": 4,
        "zero_gamma_level": 545.0, "net_gex": 1e9, "delta_hedge_flow": 50000,
        "front_skew": -3.5, "butterfly": 1.2, "butterfly_pct": 60, "butterfly_pct_n": 100,
        "vrp": 2.5, "vrp_pct": 70, "vrp_pct_n": 252,
        "term_ratio_9d_30d": 0.85, "term_ratio_30d_3m": 0.92,
        "call_wall": 560.0, "put_wall": 540.0,
        "oi_call_wall": 565.0, "oi_put_wall": 535.0,
    }
    fields = build_card_fields(summary, None)
    labels = [f.label for f in fields]
    assert "VIX Term" in labels
    vix_field = next(f for f in fields if f.label == "VIX Term")
    assert "contango" in vix_field.value
    assert vix_field.trust_tag == "market"


def test_card_field_vix_term_qqq_omitted():
    """QQQ summary without term ratios omits the VIX Term field."""
    summary = {
        "spot": 480.0, "price_change_pct": -0.3, "iv30": 22.0,
        "expected_move_pct": 1.5, "em_expiry": "2026-06-27", "em_dte": 4,
        "zero_gamma_level": 475.0, "net_gex": -5e8, "delta_hedge_flow": 30000,
        "front_skew": -4.0, "butterfly": 1.5, "butterfly_pct": None, "butterfly_pct_n": 5,
        "vrp": 3.0, "vrp_pct": 80, "vrp_pct_n": 252,
        "term_ratio_9d_30d": None, "term_ratio_30d_3m": None,
        "call_wall": 490.0, "put_wall": 470.0,
        "oi_call_wall": 495.0, "oi_put_wall": 465.0,
    }
    fields = build_card_fields(summary, None)
    labels = [f.label for f in fields]
    assert "VIX Term" not in labels
