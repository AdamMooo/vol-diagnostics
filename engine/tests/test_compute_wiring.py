"""Tests for compute.py — wiring of vol_metrics and dead-code removal."""
from __future__ import annotations

import importlib
import ast
import pathlib
import unittest.mock as mock

import pytest

COMPUTE_SRC = pathlib.Path(__file__).resolve().parents[2] / "engine" / "compute.py"


# ---------------------------------------------------------------------------
# Dead-code removal assertions (static)
# ---------------------------------------------------------------------------

class TestDeadCodeRemoved:
    def test_compute_surface_slopes_not_imported(self):
        src = COMPUTE_SRC.read_text(encoding="utf-8")
        assert "compute_surface_slopes" not in src, (
            "compute_surface_slopes must be removed from compute.py"
        )

    def test_strike_slope_not_in_summary(self):
        src = COMPUTE_SRC.read_text(encoding="utf-8")
        assert "strike_slope" not in src, (
            "summary['strike_slope'] assignment must be removed from compute.py"
        )

    def test_term_slope_not_in_summary(self):
        src = COMPUTE_SRC.read_text(encoding="utf-8")
        assert "term_slope" not in src, (
            "summary['term_slope'] assignment must be removed from compute.py"
        )


# ---------------------------------------------------------------------------
# New import assertions (static)
# ---------------------------------------------------------------------------

class TestNewImports:
    def test_vol_metrics_imported(self):
        src = COMPUTE_SRC.read_text(encoding="utf-8")
        assert "from engine.vol.vol_metrics import" in src

    def test_load_history_imported(self):
        src = COMPUTE_SRC.read_text(encoding="utf-8")
        assert "from engine.data.validation import load_history" in src


# ---------------------------------------------------------------------------
# Return dict key assertions (via mocked pipeline)
# ---------------------------------------------------------------------------

class TestComputeTickerReturnKeys:
    """Verify compute_ticker() return dict has the four new vol_metrics keys."""

    @pytest.fixture
    def mock_result(self):
        """Patch every I/O call in compute_ticker, return dict, and collect result."""
        import pandas as pd
        from engine import compute as compute_mod

        fake_skew_df = pd.DataFrame([
            {"expiry": "2024-06-21", "dte": 37.0, "put_25d_iv": 22.0,
             "call_25d_iv": 18.0, "skew_pp": 4.0},
        ])
        fake_s_df = pd.DataFrame({"strike": [500.0], "gex": [1e9]})
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

        with mock.patch.object(compute_mod, "load_chain", return_value=fake_snapshot), \
             mock.patch.object(compute_mod, "add_greeks", return_value=fake_df), \
             mock.patch.object(compute_mod, "compute_gex", return_value=fake_df), \
             mock.patch.object(compute_mod, "strike_gex", return_value=fake_s_df), \
             mock.patch.object(compute_mod, "strike_oi", return_value=fake_oi_df), \
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

    def test_return_dict_has_skew_key(self, mock_result):
        assert "skew" in mock_result

    def test_return_dict_has_term_structure_key(self, mock_result):
        assert "term_structure" in mock_result

    def test_return_dict_has_rv20_key(self, mock_result):
        assert "rv20" in mock_result

    def test_return_dict_has_vrp_key(self, mock_result):
        assert "vrp" in mock_result

    def test_summary_has_rv20_key(self, mock_result):
        assert "rv20" in mock_result["summary"]

    def test_summary_has_vrp_key(self, mock_result):
        assert "vrp" in mock_result["summary"]

    def test_cold_start_rv20_and_vrp_are_none(self, mock_result):
        """Cold start: rv20 None (empty history) and vrp None (engine returns None-dict).

        VRP-03: vrp now derives from vrp_percentile (vol_index − RV20), not the
        spot_series path — so its None-ness comes from the engine, here mocked
        to the None-dict it returns on empty/failed data.
        """
        assert mock_result["rv20"] is None
        assert mock_result["vrp"] is None
        assert mock_result["summary"]["rv20"] is None
        assert mock_result["summary"]["vrp"] is None
        assert mock_result["summary"]["vrp_pct"] is None
        assert mock_result["summary"]["vrp_pct_n"] == 0

    def test_summary_has_oi_call_wall(self, mock_result):
        assert "oi_call_wall" in mock_result["summary"]

    def test_summary_has_oi_put_wall(self, mock_result):
        assert "oi_put_wall" in mock_result["summary"]

    def test_oi_walls_none_when_no_calls(self):
        """s_df with only put OI (call_oi=0 everywhere) → oi_call_wall is None."""
        import pandas as pd
        from engine import compute as compute_mod

        fake_skew_df = pd.DataFrame([
            {"expiry": "2024-06-21", "dte": 37.0, "put_25d_iv": 22.0,
             "call_25d_iv": 18.0, "skew_pp": 4.0},
        ])
        fake_s_df = pd.DataFrame({"strike": [480.0, 520.0], "gex": [-1e9, 1e9]})
        # All call_oi = 0, only put_oi populated
        fake_oi_df = pd.DataFrame({
            "strike":  [480.0, 520.0],
            "call_oi": [0.0,   0.0],
            "put_oi":  [200.0, 100.0],
            "oi":      [200.0, 100.0],
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
            {"strike": 480.0, "type": "put", "oi": 200, "iv": 0.22,
             "delta": -0.25, "expiry": "2024-06-21", "T_years": 0.10, "gamma": 0.01, "gex": -1e6},
            {"strike": 520.0, "type": "put", "oi": 100, "iv": 0.20,
             "delta": -0.25, "expiry": "2024-06-21", "T_years": 0.10, "gamma": 0.01, "gex": -0.5e6},
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

        with mock.patch.object(compute_mod, "load_chain", return_value=fake_snapshot), \
             mock.patch.object(compute_mod, "add_greeks", return_value=fake_df), \
             mock.patch.object(compute_mod, "compute_gex", return_value=fake_df), \
             mock.patch.object(compute_mod, "strike_gex", return_value=fake_s_df), \
             mock.patch.object(compute_mod, "strike_oi", return_value=fake_oi_df), \
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

        assert result["summary"]["oi_call_wall"] is None
        assert result["summary"]["oi_put_wall"] == 480.0

    def test_oi_call_wall_selects_max_oi_strike(self):
        """Two call rows: strike 490 has call_oi=100, strike 510 has call_oi=200 → wall=510."""
        import pandas as pd
        from engine import compute as compute_mod

        fake_skew_df = pd.DataFrame([
            {"expiry": "2024-06-21", "dte": 37.0, "put_25d_iv": 22.0,
             "call_25d_iv": 18.0, "skew_pp": 4.0},
        ])
        fake_s_df = pd.DataFrame({"strike": [490.0, 510.0], "gex": [1e9, 2e9]})
        fake_oi_df = pd.DataFrame({
            "strike":  [490.0, 510.0],
            "call_oi": [100.0, 200.0],
            "put_oi":  [50.0,  30.0],
            "oi":      [150.0, 230.0],
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
            {"strike": 490.0, "type": "call", "oi": 100, "iv": 0.20,
             "delta": 0.25, "expiry": "2024-06-21", "T_years": 0.10, "gamma": 0.01, "gex": 1e6},
            {"strike": 510.0, "type": "call", "oi": 200, "iv": 0.18,
             "delta": 0.25, "expiry": "2024-06-21", "T_years": 0.10, "gamma": 0.01, "gex": 2e6},
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

        with mock.patch.object(compute_mod, "load_chain", return_value=fake_snapshot), \
             mock.patch.object(compute_mod, "add_greeks", return_value=fake_df), \
             mock.patch.object(compute_mod, "compute_gex", return_value=fake_df), \
             mock.patch.object(compute_mod, "strike_gex", return_value=fake_s_df), \
             mock.patch.object(compute_mod, "strike_oi", return_value=fake_oi_df), \
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

        assert result["summary"]["oi_call_wall"] == 510.0
