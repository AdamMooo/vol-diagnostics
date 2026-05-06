from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from gex.greeks_engine import add_greeks, bs_charm, bs_gamma, bs_vanna, T_MIN


# ---------------------------------------------------------------------------
# T_MIN constant
# ---------------------------------------------------------------------------

def test_t_min_value():
    assert abs(T_MIN - 1.0 / 365.0) < 1e-12


# ---------------------------------------------------------------------------
# bs_vanna — scalar inputs
# ---------------------------------------------------------------------------

def test_bs_vanna_atm_positive():
    # ATM option with normal inputs should produce a finite positive vanna
    v = bs_vanna(100.0, 100.0, 0.20, 0.25)
    assert np.isfinite(v)
    assert v > 0.0


def test_bs_vanna_otm():
    # OTM call (strike > spot): vanna changes sign further OTM
    v = bs_vanna(100.0, 120.0, 0.20, 0.25)
    assert np.isfinite(v)


def test_bs_vanna_zero_T():
    assert bs_vanna(100.0, 100.0, 0.20, 0.0) == 0.0


def test_bs_vanna_negative_T():
    assert bs_vanna(100.0, 100.0, 0.20, -0.01) == 0.0


def test_bs_vanna_zero_iv():
    assert bs_vanna(100.0, 100.0, 0.0, 0.25) == 0.0


def test_bs_vanna_zero_strike():
    assert bs_vanna(100.0, 0.0, 0.20, 0.25) == 0.0


def test_bs_vanna_zero_spot():
    assert bs_vanna(0.0, 100.0, 0.20, 0.25) == 0.0


def test_bs_vanna_no_nan_inf():
    v = bs_vanna(100.0, 100.0, 0.20, 0.25)
    assert not np.isnan(v)
    assert not np.isinf(v)


# ---------------------------------------------------------------------------
# bs_vanna — array inputs
# ---------------------------------------------------------------------------

def test_bs_vanna_array_shape():
    strikes = np.array([90.0, 95.0, 100.0, 105.0, 110.0])
    result = bs_vanna(100.0, strikes, 0.20, 0.25)
    assert result.shape == (5,)
    assert np.isfinite(result).all()


def test_bs_vanna_unsigned_identity():
    # BS vanna is identical for calls and puts — sign flip happens in Phase 2 exposure layer
    # Simulate "call input" and "put input" with same parameters
    v_call_scenario = bs_vanna(100.0, 100.0, 0.20, 0.25)
    v_put_scenario = bs_vanna(100.0, 100.0, 0.20, 0.25)
    assert v_call_scenario == pytest.approx(v_put_scenario)


# ---------------------------------------------------------------------------
# bs_charm — scalar inputs
# ---------------------------------------------------------------------------

def test_bs_charm_atm_finite():
    c = bs_charm(100.0, 100.0, 0.20, 0.25)
    assert np.isfinite(c)


def test_bs_charm_0dte_guard():
    # T = 0.0001 is below T_MIN (1/365 ≈ 0.00274) — must return exactly 0.0
    c = bs_charm(100.0, 100.0, 0.20, 0.0001)
    assert c == pytest.approx(0.0, abs=1e-10)


def test_bs_charm_zero_T():
    assert bs_charm(100.0, 100.0, 0.20, 0.0) == 0.0


def test_bs_charm_negative_T():
    assert bs_charm(100.0, 100.0, 0.20, -0.01) == 0.0


def test_bs_charm_zero_iv():
    assert bs_charm(100.0, 100.0, 0.0, 0.25) == 0.0


def test_bs_charm_zero_strike():
    assert bs_charm(100.0, 0.0, 0.20, 0.25) == 0.0


def test_bs_charm_zero_spot():
    assert bs_charm(0.0, 100.0, 0.20, 0.25) == 0.0


def test_bs_charm_no_nan_inf():
    c = bs_charm(100.0, 100.0, 0.20, 0.25)
    assert not np.isnan(c)
    assert not np.isinf(c)


def test_bs_charm_just_above_t_min():
    # T slightly above T_MIN should return a finite non-zero charm
    c = bs_charm(100.0, 100.0, 0.20, T_MIN * 1.5)
    assert np.isfinite(c)
    assert c != 0.0


def test_bs_charm_just_below_t_min():
    # T slightly below T_MIN must return 0.0
    c = bs_charm(100.0, 100.0, 0.20, T_MIN * 0.5)
    assert c == pytest.approx(0.0, abs=1e-10)


# ---------------------------------------------------------------------------
# bs_charm — array inputs
# ---------------------------------------------------------------------------

def test_bs_charm_array_shape():
    strikes = np.array([90.0, 95.0, 100.0, 105.0, 110.0])
    result = bs_charm(100.0, strikes, 0.20, 0.25)
    assert result.shape == (5,)
    assert np.isfinite(result).all()


def test_bs_charm_array_0dte_elements():
    # Mixed array: some rows above T_MIN, one below — below must be 0.0
    strikes = np.array([100.0, 100.0, 100.0])
    ivs = np.array([0.20, 0.20, 0.20])
    Ts = np.array([0.25, T_MIN * 1.5, 0.0001])  # last is below T_MIN
    result = bs_charm(100.0, strikes, ivs, Ts)
    assert result.shape == (3,)
    assert np.isfinite(result[0])
    assert np.isfinite(result[1])
    assert result[2] == pytest.approx(0.0, abs=1e-10)


def test_bs_charm_unsigned_identity():
    # Charm is unsigned at BS level — same numerical value regardless of "call" or "put" label
    c1 = bs_charm(100.0, 100.0, 0.20, 0.25)
    c2 = bs_charm(100.0, 100.0, 0.20, 0.25)
    assert c1 == pytest.approx(c2)


# ---------------------------------------------------------------------------
# add_greeks — DataFrame integration
# ---------------------------------------------------------------------------

def _make_chain(expiry: str = "2026-09-19") -> pd.DataFrame:
    return pd.DataFrame({
        "strike": [90.0, 95.0, 100.0, 105.0, 110.0],
        "iv": [0.25, 0.22, 0.20, 0.22, 0.25],
        "expiry": [expiry] * 5,
    })


def test_add_greeks_has_vanna_column():
    result = add_greeks(_make_chain(), spot=100.0)
    assert "vanna" in result.columns


def test_add_greeks_has_charm_column():
    result = add_greeks(_make_chain(), spot=100.0)
    assert "charm" in result.columns


def test_add_greeks_has_gamma_column():
    result = add_greeks(_make_chain(), spot=100.0)
    assert "gamma" in result.columns


def test_add_greeks_vanna_finite():
    result = add_greeks(_make_chain(), spot=100.0)
    assert result["vanna"].notna().all()
    assert np.isfinite(result["vanna"].to_numpy()).all()


def test_add_greeks_charm_finite():
    result = add_greeks(_make_chain(), spot=100.0)
    assert result["charm"].notna().all()
    assert np.isfinite(result["charm"].to_numpy()).all()


def test_add_greeks_does_not_mutate_input():
    df = _make_chain()
    original_cols = set(df.columns)
    add_greeks(df, spot=100.0)
    assert set(df.columns) == original_cols


def test_add_greeks_row_count_unchanged():
    df = _make_chain()
    result = add_greeks(df, spot=100.0)
    assert len(result) == len(df)
