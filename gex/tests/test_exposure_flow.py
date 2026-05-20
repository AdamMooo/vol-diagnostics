from __future__ import annotations

import pandas as pd
import pytest

from gex.exposure_engine import compute_gex, strike_gex
from gex.analytics import summarise


def _chain(spot: float = 500.0) -> pd.DataFrame:
    return pd.DataFrame([
        {"strike": spot, "type": "call", "oi": 100, "gamma": 0.01},
        {"strike": spot, "type": "put",  "oi": 100, "gamma": 0.01},
    ])


def _gex_df(net: float = 1e9) -> pd.DataFrame:
    return pd.DataFrame({"strike": [500.0], "gex": [net]})


def _profile_df() -> pd.DataFrame:
    return pd.DataFrame({
        "spot_level": [490.0, 495.0, 500.0, 505.0, 510.0],
        "net_gex":    [-1e9, -0.5e9, 0.0, 0.5e9, 1e9],
    })


def test_strike_gex_equal_oi_call_put_cancel():
    result = strike_gex(compute_gex(_chain(), spot=500.0))
    assert result["gex"].iloc[0] == pytest.approx(0.0)


def test_summarise_defensible_keys_only():
    r = summarise(_gex_df(1e9), _profile_df(), spot=500.0,
                  delta_hedge_flow=8.4e9)
    assert r["net_gex"] == pytest.approx(1e9)
    assert r["delta_hedge_flow"] == 8.4e9
    assert r["zero_gamma_level"] == pytest.approx(500.0)
