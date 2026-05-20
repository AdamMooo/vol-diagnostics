"""Tests for GEX exposure in exposure_engine.py."""
import pandas as pd
import pytest

from gex.exposure_engine import compute_gex, strike_gex


@pytest.fixture
def greek_df():
    return pd.DataFrame({
        "strike": [490.0, 490.0, 500.0, 500.0],
        "type":   ["call", "put", "call", "put"],
        "oi":     [100,    200,   150,    250],
        "gamma":  [0.01,   0.012, 0.015,  0.008],
    })


class TestComputeGex:
    def test_returns_copy_with_gex_column(self, greek_df):
        result = compute_gex(greek_df, spot=500.0)
        assert "gex" in result.columns
        assert result is not greek_df

    def test_calls_positive(self, greek_df):
        result = compute_gex(greek_df, spot=500.0)
        assert (result[result["type"] == "call"]["gex"] > 0).all()

    def test_puts_negative(self, greek_df):
        result = compute_gex(greek_df, spot=500.0)
        assert (result[result["type"] == "put"]["gex"] < 0).all()

    def test_formula_spot_squared(self, greek_df):
        spot = 500.0
        result = compute_gex(greek_df, spot=spot)
        expected_first_call = 1.0 * 0.01 * 100 * 100 * spot ** 2 * 0.01
        assert abs(result.iloc[0]["gex"] - expected_first_call) < 1e-9

    def test_original_df_unchanged(self, greek_df):
        _ = compute_gex(greek_df, spot=500.0)
        assert "gex" not in greek_df.columns


class TestStrikeGex:
    def test_aggregates_by_strike(self, greek_df):
        result = strike_gex(compute_gex(greek_df, spot=500.0))
        assert list(result.columns) == ["strike", "gex"]
        assert len(result) == 2

    def test_sorted_by_strike(self, greek_df):
        result = strike_gex(compute_gex(greek_df, spot=500.0))
        assert list(result["strike"]) == sorted(result["strike"].tolist())
