"""Tests for analytics.summarise()."""
import pandas as pd
import pytest

from engine.gex.analytics import summarise


@pytest.fixture
def gex_df():
    return pd.DataFrame({"strike": [500.0], "gex": [1e9]})


@pytest.fixture
def profile_df():
    return pd.DataFrame({
        "spot_level": [490.0, 500.0, 510.0],
        "net_gex":    [-1e9, 0.0, 1e9],
    })


def test_summarise_keys_present(gex_df, profile_df):
    r = summarise(gex_df, profile_df, spot=500.0)
    for key in ("net_gex", "zero_gamma_level", "call_wall", "put_wall",
                "spot", "delta_hedge_flow"):
        assert key in r


def test_summarise_defaults(gex_df, profile_df):
    r = summarise(gex_df, profile_df, spot=500.0)
    assert r["delta_hedge_flow"] is None
    assert r["spot"] == 500.0
    assert r["net_gex"] == pytest.approx(1e9)


def test_summarise_passes_delta_flow(gex_df, profile_df):
    r = summarise(gex_df, profile_df, spot=500.0, delta_hedge_flow=8e9)
    assert r["delta_hedge_flow"] == 8e9


def test_summarise_no_regime_key(gex_df, profile_df):
    """gamma_regime was removed — categorical label is no longer produced."""
    r = summarise(gex_df, profile_df, spot=500.0)
    assert "gamma_regime" not in r
    assert "net_vex" not in r
    assert "net_chex" not in r
