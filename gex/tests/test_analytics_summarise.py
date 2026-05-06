"""Tests for the extended summarise() signature in analytics.py."""
import pandas as pd
import pytest

from gex.analytics import summarise


@pytest.fixture
def gex_df():
    return pd.DataFrame({"strike": [500.0], "gex": [1e9]})


@pytest.fixture
def profile_df():
    return pd.DataFrame({
        "spot_level": [490.0, 500.0, 510.0],
        "net_gex": [-1e9, 0.0, 1e9],
    })


class TestSummariseExtension:
    def test_existing_keys_present(self, gex_df, profile_df):
        r = summarise(gex_df, profile_df, spot=500.0)
        for key in ("net_gex", "zero_gamma_level", "call_wall", "put_wall", "gamma_regime", "spot"):
            assert key in r

    def test_new_keys_present_with_none_defaults(self, gex_df, profile_df):
        r = summarise(gex_df, profile_df, spot=500.0)
        assert "net_vex" in r
        assert "net_chex" in r
        assert "delta_hedge_flow" in r
        assert r["net_vex"] is None
        assert r["net_chex"] is None
        assert r["delta_hedge_flow"] is None

    def test_new_kwargs_populate_return_dict(self, gex_df, profile_df):
        r = summarise(gex_df, profile_df, spot=500.0,
                      net_vex=2e9, net_chex=-1e9, delta_hedge_flow=8e9)
        assert r["net_vex"] == 2e9
        assert r["net_chex"] == -1e9
        assert r["delta_hedge_flow"] == 8e9

    def test_existing_callers_unaffected(self, gex_df, profile_df):
        """Old call pattern with no new kwargs still returns valid dict."""
        r = summarise(gex_df, profile_df, 500.0)
        assert r["net_gex"] == pytest.approx(1e9)
        assert r["spot"] == 500.0

    def test_partial_kwargs(self, gex_df, profile_df):
        """Passing only one new kwarg leaves others None."""
        r = summarise(gex_df, profile_df, spot=500.0, net_vex=5e8)
        assert r["net_vex"] == 5e8
        assert r["net_chex"] is None
        assert r["delta_hedge_flow"] is None
