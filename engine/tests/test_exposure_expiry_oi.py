"""Tests for expiry_oi() in exposure_engine.py (Task 2, 16.5-01)."""
from __future__ import annotations

import pandas as pd
import pytest

from engine.gex.exposure_engine import expiry_oi
from engine import config


def _make_chain_df(n_expiries: int = 3, dte_per_expiry: float = 30.0) -> pd.DataFrame:
    """Minimal greeks-enriched chain DataFrame for testing."""
    rows = []
    for i in range(n_expiries):
        expiry = f"2024-0{i+1}-19"
        dte = dte_per_expiry * (i + 1)
        t_years = dte / 365.0
        for side in ("call", "put"):
            rows.append({
                "expiry": expiry,
                "strike": 500.0,
                "type": side,
                "oi": 1000 * (i + 1) + (100 if side == "call" else 0),
                "T_years": t_years,
                "iv": 0.20,
                "gamma": 0.01,
                "delta": 0.25 if side == "call" else -0.25,
            })
    return pd.DataFrame(rows)


class TestExpiryOiColumns:
    def test_returns_expected_columns(self):
        df = _make_chain_df(3)
        result = expiry_oi(df)
        required = {"expiry", "dte", "call_oi", "put_oi", "oi", "pct_of_total", "put_call_ratio"}
        assert required.issubset(set(result.columns))

    def test_sorted_by_oi_descending(self):
        df = _make_chain_df(3)
        result = expiry_oi(df)
        assert list(result["oi"]) == sorted(result["oi"].tolist(), reverse=True)

    def test_one_row_per_expiry(self):
        df = _make_chain_df(3)
        result = expiry_oi(df)
        assert len(result) == 3
        assert result["expiry"].nunique() == 3


class TestExpiryOiValues:
    def test_oi_equals_call_plus_put(self):
        df = _make_chain_df(3)
        result = expiry_oi(df)
        assert (result["oi"] == result["call_oi"] + result["put_oi"]).all()

    def test_pct_of_total_sums_to_100(self):
        df = _make_chain_df(3)
        result = expiry_oi(df)
        assert abs(result["pct_of_total"].sum() - 100.0) < 1e-6

    def test_put_call_ratio_positive(self):
        df = _make_chain_df(3)
        result = expiry_oi(df)
        assert (result["put_call_ratio"] > 0).all()

    def test_dte_column_populated(self):
        df = _make_chain_df(3)
        result = expiry_oi(df)
        assert result["dte"].notna().all()
        assert (result["dte"] > 0).all()

    def test_put_call_ratio_no_div_zero(self):
        """Put-only expiry (zero call OI): ratio is undefined (NaN), not a
        ZeroDivisionError and not a near-inf garbage value."""
        df = pd.DataFrame([
            {"expiry": "2024-06-19", "strike": 500.0, "type": "put",
             "oi": 500, "T_years": 30/365, "iv": 0.20, "gamma": 0.01, "delta": -0.25},
        ])
        result = expiry_oi(df)
        assert len(result) == 1
        assert pd.isna(result["put_call_ratio"].iloc[0])


class TestExpiryOiDteFilter:
    def test_filters_to_gte90_dte(self):
        """Expiry with DTE > GEX_MAX_DTE must be excluded."""
        df = _make_chain_df(4, dte_per_expiry=30.0)  # DTEs: 30, 60, 90, 120
        result = expiry_oi(df)
        # 120-day expiry (DTE > 90) must be excluded
        assert (result["dte"] <= config.GEX_MAX_DTE).all()

    def test_returns_empty_df_when_all_beyond_dte_cap(self):
        """All options beyond GEX_MAX_DTE: should return empty or all-filtered result."""
        df = pd.DataFrame([
            {"expiry": "2025-06-19", "strike": 500.0, "type": "call",
             "oi": 1000, "T_years": 200/365, "iv": 0.20, "gamma": 0.01, "delta": 0.25},
            {"expiry": "2025-06-19", "strike": 500.0, "type": "put",
             "oi": 800, "T_years": 200/365, "iv": 0.20, "gamma": 0.01, "delta": -0.25},
        ])
        result = expiry_oi(df)
        assert result.empty


class TestExpiryOiTotalZero:
    def test_pct_of_total_zero_when_oi_is_zero(self):
        """Defensive: if all OI is 0, pct_of_total should be 0, not NaN."""
        df = pd.DataFrame([
            {"expiry": "2024-06-19", "strike": 500.0, "type": "call",
             "oi": 0, "T_years": 30/365, "iv": 0.20, "gamma": 0.01, "delta": 0.25},
        ])
        result = expiry_oi(df)
        if not result.empty:
            assert (result["pct_of_total"] == 0).all()

class TestExpiryOiPrimaryTenor:
    def test_respects_explicit_max_dte_argument(self):
        """Caller can request a narrower tenor (e.g., primary 14 DTE lens)."""
        df = _make_chain_df(3, dte_per_expiry=7.0)  # DTEs: 7, 14, 21
        result = expiry_oi(df, max_dte=14)
        assert not result.empty
        assert (result["dte"] <= 14).all()
        assert len(result) == 2

