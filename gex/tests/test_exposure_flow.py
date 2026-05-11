from __future__ import annotations

import pandas as pd
import pytest

from gex.exposure_engine import compute_vex, compute_chex, strike_vex, strike_chex
from gex.analytics import summarise
from gex.validation import load_yesterday


# ── Helpers ──────────────────────────────────────────────────────────────────

def _chain(calls: int = 1, puts: int = 1, spot: float = 500.0) -> pd.DataFrame:
    rows = []
    for _ in range(calls):
        rows.append({"strike": spot, "type": "call", "oi": 100, "vanna": 0.05, "charm": 0.02, "gamma": 0.01})
    for _ in range(puts):
        rows.append({"strike": spot, "type": "put",  "oi": 100, "vanna": 0.05, "charm": 0.02, "gamma": 0.01})
    return pd.DataFrame(rows)


def _gex_df(net: float = 1e9) -> pd.DataFrame:
    return pd.DataFrame({"strike": [500.0], "gex": [net]})


def _profile_df() -> pd.DataFrame:
    return pd.DataFrame({
        "spot_level": [490.0, 495.0, 500.0, 505.0, 510.0],
        "net_gex":    [-1e9, -0.5e9, 0.0, 0.5e9, 1e9],
    })


# ── compute_vex spot scaling guard ───────────────────────────────────────────

def test_compute_vex_spot_not_squared():
    df = pd.DataFrame({"strike": [500.0], "type": ["call"], "oi": [1], "vanna": [1.0], "charm": [0.0], "gamma": [0.0]})
    result = compute_vex(df, spot=500.0)
    wrong = 1.0 * 1 * 100 * 500.0 ** 2 * 0.01
    assert abs(result["vex"].iloc[0]) != pytest.approx(abs(wrong))


def test_compute_chex_spot_not_squared():
    df = pd.DataFrame({"strike": [500.0], "type": ["call"], "oi": [1], "charm": [1.0], "vanna": [0.0], "gamma": [0.0]})
    result = compute_chex(df, spot=500.0)
    wrong = 1.0 * 1 * 100 * 500.0 ** 2 * 0.01
    assert abs(result["chex"].iloc[0]) != pytest.approx(abs(wrong))


# ── strike_vex equal-OI offset ───────────────────────────────────────────────

def test_strike_vex_equal_oi_call_put_cancel():
    df = _chain(calls=1, puts=1, spot=500.0)
    result = strike_vex(compute_vex(df, spot=500.0))
    assert result["vex"].iloc[0] == pytest.approx(0.0)


def test_strike_chex_equal_oi_call_put_cancel():
    df = _chain(calls=1, puts=1, spot=500.0)
    result = strike_chex(compute_chex(df, spot=500.0))
    assert result["chex"].iloc[0] == pytest.approx(0.0)


# ── summarise() backward and forward compat ───────────────────────────────────

def test_summarise_backward_compat_new_keys_none():
    r = summarise(_gex_df(1e9), _profile_df(), spot=500.0)
    assert r["net_vex"] is None
    assert r["net_chex"] is None
    assert r["delta_hedge_flow"] is None


def test_summarise_backward_compat_existing_keys_present():
    r = summarise(_gex_df(1e9), _profile_df(), spot=500.0)
    for key in ("net_gex", "gamma_regime", "spot", "zero_gamma_level", "call_wall", "put_wall"):
        assert key in r


def test_summarise_forward_compat_passes_through():
    r = summarise(_gex_df(1e9), _profile_df(), spot=500.0,
                  net_vex=2e9, net_chex=-1e9, delta_hedge_flow=8.4e9)
    assert r["net_vex"] == 2e9
    assert r["net_chex"] == -1e9
    assert r["delta_hedge_flow"] == 8.4e9


# ── load_yesterday absent-store guard ─────────────────────────────────────────

def test_load_yesterday_returns_none_when_store_absent(monkeypatch, tmp_path):
    import gex.validation as val
    monkeypatch.setattr(val, "STORE", tmp_path / "nonexistent.parquet")
    assert load_yesterday("SPY") is None
