"""Tests for VEX/CHEX exposure functions in exposure_engine.py."""
import numpy as np
import pandas as pd
import pytest

from gex.exposure_engine import compute_vex, compute_chex, strike_vex, strike_chex


@pytest.fixture
def greek_df():
    """Minimal greeks-enriched DataFrame with vanna and charm columns."""
    return pd.DataFrame({
        "strike": [490.0, 490.0, 500.0, 500.0],
        "type":   ["call", "put", "call", "put"],
        "oi":     [100,    200,   150,    250],
        "vanna":  [0.05,   0.04,  0.06,   0.03],
        "charm":  [0.02,   0.015, 0.025,  0.01],
    })


class TestComputeVex:
    def test_returns_copy_with_vex_column(self, greek_df):
        result = compute_vex(greek_df, spot=500.0)
        assert "vex" in result.columns
        assert result is not greek_df

    def test_calls_positive_vex(self, greek_df):
        result = compute_vex(greek_df, spot=500.0)
        call_vex = result[result["type"] == "call"]["vex"]
        assert (call_vex > 0).all()

    def test_puts_negative_vex(self, greek_df):
        result = compute_vex(greek_df, spot=500.0)
        put_vex = result[result["type"] == "put"]["vex"]
        assert (put_vex < 0).all()

    def test_formula_spot_not_spot_squared(self, greek_df):
        """VEX uses spot * 0.01, not spot**2 * 0.01."""
        spot = 500.0
        result = compute_vex(greek_df, spot=spot)
        # For first call row: sign=+1, vanna=0.05, oi=100, mult=100, spot=500, 0.01
        expected_first_call = 1.0 * 0.05 * 100 * 100 * 500.0 * 0.01
        assert abs(result.iloc[0]["vex"] - expected_first_call) < 1e-9

    def test_original_df_unchanged(self, greek_df):
        _ = compute_vex(greek_df, spot=500.0)
        assert "vex" not in greek_df.columns


class TestComputeChex:
    def test_returns_copy_with_chex_column(self, greek_df):
        result = compute_chex(greek_df, spot=500.0)
        assert "chex" in result.columns
        assert result is not greek_df

    def test_calls_positive_chex(self, greek_df):
        result = compute_chex(greek_df, spot=500.0)
        call_chex = result[result["type"] == "call"]["chex"]
        assert (call_chex > 0).all()

    def test_puts_negative_chex(self, greek_df):
        result = compute_chex(greek_df, spot=500.0)
        put_chex = result[result["type"] == "put"]["chex"]
        assert (put_chex < 0).all()

    def test_formula_uses_charm_not_vanna(self, greek_df):
        spot = 500.0
        result = compute_chex(greek_df, spot=spot)
        # For first call row: sign=+1, charm=0.02, oi=100, mult=100, spot=500, 0.01
        expected_first_call = 1.0 * 0.02 * 100 * 100 * 500.0 * 0.01
        assert abs(result.iloc[0]["chex"] - expected_first_call) < 1e-9

    def test_original_df_unchanged(self, greek_df):
        _ = compute_chex(greek_df, spot=500.0)
        assert "chex" not in greek_df.columns


class TestStrikeVex:
    def test_aggregates_by_strike(self, greek_df):
        enriched = compute_vex(greek_df, spot=500.0)
        result = strike_vex(enriched)
        assert list(result.columns) == ["strike", "vex"]
        assert len(result) == 2  # two unique strikes

    def test_sorted_by_strike(self, greek_df):
        enriched = compute_vex(greek_df, spot=500.0)
        result = strike_vex(enriched)
        assert list(result["strike"]) == sorted(result["strike"].tolist())

    def test_sums_calls_and_puts_per_strike(self, greek_df):
        spot = 500.0
        enriched = compute_vex(greek_df, spot=spot)
        result = strike_vex(enriched)
        # Strike 490: call vex + put vex
        row_490 = result[result["strike"] == 490.0]["vex"].values[0]
        call_490 = 1.0 * 0.05 * 100 * 100 * spot * 0.01
        put_490 = -1.0 * 0.04 * 200 * 100 * spot * 0.01
        assert abs(row_490 - (call_490 + put_490)) < 1e-9


class TestStrikeChex:
    def test_aggregates_by_strike(self, greek_df):
        enriched = compute_chex(greek_df, spot=500.0)
        result = strike_chex(enriched)
        assert list(result.columns) == ["strike", "chex"]
        assert len(result) == 2

    def test_sorted_by_strike(self, greek_df):
        enriched = compute_chex(greek_df, spot=500.0)
        result = strike_chex(enriched)
        assert list(result["strike"]) == sorted(result["strike"].tolist())
