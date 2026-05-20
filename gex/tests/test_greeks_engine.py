from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from gex.greeks_engine import add_greeks, bs_gamma, T_MIN


def test_t_min_value():
    assert abs(T_MIN - 1.0 / 365.0) < 1e-12


def test_bs_gamma_atm_positive():
    g = bs_gamma(100.0, 100.0, 0.20, 0.25)
    assert np.isfinite(g)
    assert g > 0


def test_bs_gamma_zero_T():
    assert bs_gamma(100.0, 100.0, 0.20, 0.0) == 0.0


def test_bs_gamma_zero_iv():
    assert bs_gamma(100.0, 100.0, 0.0, 0.25) == 0.0


def test_bs_gamma_array_shape():
    strikes = np.array([90.0, 95.0, 100.0, 105.0, 110.0])
    ivs = np.full_like(strikes, 0.20)
    Ts = np.full_like(strikes, 0.25)
    result = bs_gamma(100.0, strikes, ivs, Ts)
    assert result.shape == (5,)
    assert np.isfinite(result).all()


def _make_chain(expiry: str = "2026-09-19") -> pd.DataFrame:
    return pd.DataFrame({
        "strike": [90.0, 95.0, 100.0, 105.0, 110.0],
        "iv": [0.25, 0.22, 0.20, 0.22, 0.25],
        "expiry": [expiry] * 5,
        "gamma": [0.01, 0.02, 0.03, 0.02, 0.01],
    })


def test_add_greeks_adds_t_years():
    result = add_greeks(_make_chain(), spot=100.0)
    assert "T_years" in result.columns
    assert (result["T_years"] > 0).all()


def test_add_greeks_does_not_mutate_input():
    df = _make_chain()
    original_cols = set(df.columns)
    add_greeks(df, spot=100.0)
    assert set(df.columns) == original_cols


def test_add_greeks_row_count_unchanged():
    df = _make_chain()
    result = add_greeks(df, spot=100.0)
    assert len(result) == len(df)
