"""Tests for compute.py OI wiring: expiry_oi_df key + is_top_decile on s_df (16.5-01 Task 2)."""
from __future__ import annotations

import unittest.mock as mock
import pandas as pd
import pytest

from engine import compute as compute_mod


def _make_mock_result(fake_oi_df=None):
    """Run compute_ticker with all I/O mocked. Returns the result dict."""
    fake_skew_df = pd.DataFrame([
        {"expiry": "2024-06-21", "dte": 37.0, "put_25d_iv": 22.0,
         "call_25d_iv": 18.0, "skew_pp": 4.0},
    ])
    fake_s_df = pd.DataFrame({"strike": [500.0], "gex": [1e9]})
    if fake_oi_df is None:
        fake_oi_df = pd.DataFrame({
            "strike":   [500.0],
            "call_oi":  [150.0],
            "put_oi":   [80.0],
            "oi":       [230.0],
        })
    fake_p_df = pd.DataFrame({
        "spot_level": [490.0, 495.0, 500.0, 505.0, 510.0],
        "net_gex":    [-1e9, -0.5e9, 0.0, 0.5e9, 1e9],
    })
    fake_surface_df = pd.DataFrame({
        "strike": [490.0, 500.0, 510.0],
        "expiry": ["2024-06-21"] * 3,
        "T_years": [0.1] * 3,
        "iv": [0.20, 0.18, 0.19],
    })
    fake_df = pd.DataFrame([
        {"strike": 480.0, "type": "put",  "oi": 100, "iv": 0.22,
         "delta": -0.25, "expiry": "2024-06-21", "T_years": 0.10, "gamma": 0.01, "gex": -1e6},
        {"strike": 520.0, "type": "call", "oi": 100, "iv": 0.18,
         "delta":  0.25, "expiry": "2024-06-21", "T_years": 0.10, "gamma": 0.01, "gex":  1e6},
    ])
    fake_snapshot = mock.MagicMock()
    fake_snapshot.spot = 500.0
    fake_snapshot.iv30 = 20.0
    fake_snapshot.price_change_pct = -0.5
    fake_snapshot.as_of = None
    fake_snapshot.chains = fake_df
    fake_diag = {
        "coverage_pct": 80.0, "fit_rmse": 0.4, "max_resid": 1.2,
        "cv_rmse": 0.6, "coherence_calendar": True,
        "coherence_butterfly": True, "coherence_violations": 0,
    }
    # expiry_oi returns the expiry-level DataFrame
    fake_expiry_oi_df = pd.DataFrame({
        "expiry": ["2024-06-21"],
        "dte": [37.0],
        "call_oi": [150.0],
        "put_oi": [80.0],
        "oi": [230.0],
        "pct_of_total": [100.0],
        "put_call_ratio": [0.53],
    })

    with mock.patch.object(compute_mod, "load_chain", return_value=fake_snapshot), \
         mock.patch.object(compute_mod, "add_greeks", return_value=fake_df), \
         mock.patch.object(compute_mod, "compute_gex", return_value=fake_df), \
         mock.patch.object(compute_mod, "strike_gex", return_value=fake_s_df), \
         mock.patch.object(compute_mod, "strike_oi", return_value=fake_oi_df), \
         mock.patch.object(compute_mod, "expiry_oi", return_value=fake_expiry_oi_df), \
         mock.patch.object(compute_mod, "_get_risk_free_rate", return_value=0.05), \
         mock.patch.object(compute_mod, "gamma_profile", return_value=fake_p_df), \
         mock.patch.object(compute_mod, "vol_surface_data", return_value=fake_surface_df), \
         mock.patch.object(compute_mod, "surface_diagnostics", return_value=fake_diag), \
         mock.patch.object(compute_mod, "compute_skew", return_value=fake_skew_df), \
         mock.patch.object(compute_mod, "compute_skew_25d", return_value={"front_month": None, "second_month": None}), \
         mock.patch.object(compute_mod, "compute_term_structure", return_value={"points": [], "classification": "normal", "front_atm_iv": None, "back_atm_iv": None}), \
         mock.patch.object(compute_mod, "load_history", return_value=pd.DataFrame()), \
         mock.patch.object(compute_mod, "_fetch_spot_history_yf", return_value=None), \
         mock.patch.object(compute_mod, "vrp_percentile", return_value={"vrp": None, "pct": None, "n": 0}):
        result = compute_mod.compute_ticker("SPY")

    return result


class TestExpiryOiDfKey:
    def test_return_dict_has_expiry_oi_df_key(self):
        result = _make_mock_result()
        assert "expiry_oi_df" in result

    def test_expiry_oi_df_is_dataframe(self):
        result = _make_mock_result()
        assert isinstance(result["expiry_oi_df"], pd.DataFrame)

    def test_expiry_oi_df_not_empty(self):
        result = _make_mock_result()
        assert not result["expiry_oi_df"].empty


class TestIsTopDecile:
    def test_s_df_has_is_top_decile_column(self):
        result = _make_mock_result()
        assert "is_top_decile" in result["s_df"].columns

    def test_is_top_decile_is_bool_dtype(self):
        result = _make_mock_result()
        assert result["s_df"]["is_top_decile"].dtype == bool

    def test_is_top_decile_all_false_when_oi_zero(self):
        """When all OI values are 0 (NaN-filled), is_top_decile must be all False."""
        fake_oi_df_zero = pd.DataFrame({
            "strike":   [500.0, 510.0],
            "call_oi":  [0.0, 0.0],
            "put_oi":   [0.0, 0.0],
            "oi":       [0.0, 0.0],
        })
        result = _make_mock_result(fake_oi_df=fake_oi_df_zero)
        assert not result["s_df"]["is_top_decile"].any()

    def test_is_top_decile_marks_high_oi_strikes(self):
        """Strike with much higher OI than others should be in top decile.

        Uses strike=500 to match the single-row fake_s_df in _make_mock_result.
        """
        fake_oi_df_with_match = pd.DataFrame({
            "strike":   [500.0],
            "call_oi":  [1000.0],
            "put_oi":   [500.0],
            "oi":       [1500.0],
        })
        result = _make_mock_result(fake_oi_df=fake_oi_df_with_match)
        # The single strike has oi=1500 > 0, so quantile(0.9) = 1500, 1500>=1500 is True
        assert result["s_df"]["is_top_decile"].any()
