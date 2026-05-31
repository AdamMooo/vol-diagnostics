"""Tests for validation.py parquet schema extension — rv20 and vrp columns."""
from __future__ import annotations

import pathlib
import tempfile
import datetime
import unittest.mock as mock

import pandas as pd
import pytest

from gex.validation import _FLOAT_COLS, save_snapshot, load_history


# ---------------------------------------------------------------------------
# _FLOAT_COLS schema tests
# ---------------------------------------------------------------------------

class TestFloatColsSchema:
    def test_rv20_in_float_cols(self):
        assert "rv20" in _FLOAT_COLS

    def test_vrp_in_float_cols(self):
        assert "vrp" in _FLOAT_COLS

    def test_diagnostics_in_float_cols(self):
        assert {"coverage_pct", "fit_rmse", "max_resid", "cv_rmse",
                "coherence_violations"} <= set(_FLOAT_COLS)


# ---------------------------------------------------------------------------
# save_snapshot row dict tests
# ---------------------------------------------------------------------------

class TestSaveSnapshotRowDict:
    """Verify save_snapshot writes rv20 and vrp from summary dict."""

    @pytest.fixture
    def summary_with_metrics(self):
        return {
            "spot": 500.0,
            "net_gex": 1e9,
            "zero_gamma_level": 498.0,
            "call_wall": 510.0,
            "put_wall": 490.0,
            "front_skew": 4.0,
            "iv30": 20.0,
            "strike_slope": None,
            "term_slope": None,
            "rv20": 15.5,
            "vrp": 4.5,
        }

    def test_rv20_persisted(self, summary_with_metrics, tmp_path):
        store = tmp_path / "test_snapshots.parquet"
        with mock.patch("gex.validation.STORE", store):
            save_snapshot(summary_with_metrics, "SPY")
        hist = pd.read_parquet(store)
        assert "rv20" in hist.columns
        assert float(hist["rv20"].iloc[0]) == pytest.approx(15.5)

    def test_vrp_persisted(self, summary_with_metrics, tmp_path):
        store = tmp_path / "test_snapshots.parquet"
        with mock.patch("gex.validation.STORE", store):
            save_snapshot(summary_with_metrics, "SPY")
        hist = pd.read_parquet(store)
        assert "vrp" in hist.columns
        assert float(hist["vrp"].iloc[0]) == pytest.approx(4.5)

    def test_rv20_none_written_as_null(self, tmp_path):
        summary = {
            "spot": 500.0,
            "net_gex": 1e9,
            "zero_gamma_level": None,
            "call_wall": None,
            "put_wall": None,
            "front_skew": None,
            "iv30": None,
            "strike_slope": None,
            "term_slope": None,
            "rv20": None,
            "vrp": None,
        }
        store = tmp_path / "test_snapshots.parquet"
        with mock.patch("gex.validation.STORE", store):
            save_snapshot(summary, "SPY")
        hist = pd.read_parquet(store)
        assert "rv20" in hist.columns
        assert pd.isna(hist["rv20"].iloc[0])

    def test_diagnostics_persisted(self, tmp_path):
        """08-03: coverage_pct/fit_rmse/max_resid/cv_rmse + coherence flags persist."""
        summary = {
            "spot": 500.0, "net_gex": 1e9,
            "coverage_pct": 87.0, "fit_rmse": 0.9, "max_resid": 2.1,
            "cv_rmse": 1.3, "coherence_violations": 0,
            "coherence_calendar": True, "coherence_butterfly": True,
        }
        store = tmp_path / "diag_snapshots.parquet"
        with mock.patch("gex.validation.STORE", store):
            save_snapshot(summary, "SPY")
        hist = pd.read_parquet(store)
        assert float(hist["coverage_pct"].iloc[0]) == pytest.approx(87.0)
        assert float(hist["fit_rmse"].iloc[0]) == pytest.approx(0.9)
        assert float(hist["max_resid"].iloc[0]) == pytest.approx(2.1)
        assert int(hist["coherence_violations"].iloc[0]) == 0
        assert bool(hist["coherence_calendar"].iloc[0]) is True


# ---------------------------------------------------------------------------
# Old snapshot forward-compat tests
# ---------------------------------------------------------------------------

class TestOldSnapshotCompat:
    """Old parquet files without rv20/vrp columns load as NaN (no crash)."""

    def test_load_history_old_snapshot_no_crash(self, tmp_path):
        """A parquet file without rv20/vrp should load without error."""
        old_row = {
            "date": datetime.date.today(),
            "ticker": "SPY",
            "spot": 500.0,
            "net_gex": 1e9,
            "zero_gamma_level": 498.0,
            "call_wall": 510.0,
            "put_wall": 490.0,
            "front_skew": 4.0,
            "put_25d_iv": 22.0,
            "call_25d_iv": 18.0,
            "iv30": 20.0,
            "strike_slope": None,
            "term_slope": None,
            # deliberately omitting rv20 and vrp
        }
        store = tmp_path / "old_snapshots.parquet"
        pd.DataFrame([old_row]).to_parquet(store, index=False)

        with mock.patch("gex.validation.STORE", store):
            hist = load_history("SPY")

        assert not hist.empty
        # rv20 and vrp should be absent or NaN — no KeyError or crash

    def test_load_history_snapshot_without_diagnostics_columns(self, tmp_path):
        """A snapshot predating the 08-03 diagnostic columns loads without error."""
        row = {
            "date": datetime.date.today(), "ticker": "SPY", "spot": 500.0,
            "net_gex": 1e9, "iv30": 20.0, "rv20": 15.0, "vrp": 4.0,
            # no coverage_pct / fit_rmse / max_resid / cv_rmse / coherence_*
        }
        store = tmp_path / "pre_diag_snapshots.parquet"
        pd.DataFrame([row]).to_parquet(store, index=False)
        with mock.patch("gex.validation.STORE", store):
            hist = load_history("SPY")
        assert not hist.empty
