"""Tests for engine/surface/surface_interactive.py — payload builders + HTML renderers.

Hermetic: a synthetic surface_df (no network, no parquet). Covers the surface, the ΔIV
compare, and the day-by-day movie (level + change modes), plus that each renderer's
str.format() actually fills (catches brace bugs in the embedded HTML/JS).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from engine import config
from engine.surface.surface_interactive import (
    GRID_DTE, GRID_LM,
    build_surface_payload, render_surface_html,
    build_diff_payload, render_diff_html,
    build_movie_payload, render_movie_html,
)


def _surface_df(spot: float = 100.0, base_iv: float = 16.0) -> pd.DataFrame:
    """Synthetic vol surface: 1 + 5 expiries × strikes within ±20% with a convex smile."""
    rows = []
    for dte in (1, 7, 14, 30, 60, 90):
        for strike in range(82, 121, 2):
            log_m = np.log(strike / spot)
            iv = base_iv + 45.0 * log_m**2 + 2.0 * (30.0 / max(dte, 5))  # smile + mild term
            rows.append({
                "dte": float(dte), "strike": float(strike),
                "moneyness": strike / spot, "log_moneyness": log_m, "iv_pct": iv,
            })
    return pd.DataFrame(rows)


# ── surface payload ─────────────────────────────────────────────────────────

class TestSurfacePayload:
    def setup_method(self):
        self.p = build_surface_payload(_surface_df(), 100.0, ticker="SPY")

    def test_not_none(self):
        assert self.p is not None

    def test_grid_dimensions(self):
        assert len(self.p["dte_grid"]) == GRID_DTE
        assert len(self.p["otm_grid"]) == GRID_LM
        assert len(self.p["ks_grid"]) == GRID_LM

    def test_iv_grid_shape_is_otm_by_dte(self):
        assert len(self.p["IV"]) == GRID_LM
        assert all(len(row) == GRID_DTE for row in self.p["IV"])

    def test_coverage_in_range(self):
        assert 0.0 <= self.p["coverage"] <= 100.0

    def test_near_layer_present_from_1dte(self):
        # fit_floor=5 excludes 1DTE from the fit, near_max=5 captures it as the near layer
        assert self.p["near"] is not None
        assert self.p["near"]["dte"] == 1.0

    def test_smile_and_term_slices_per_grid_line(self):
        assert len(self.p["smile_fit"]) == GRID_DTE
        assert len(self.p["term_fit"]) == GRID_LM

    def test_none_on_empty(self):
        assert build_surface_payload(pd.DataFrame(), 100.0) is None

    def test_none_on_single_expiry(self):
        one = _surface_df()
        one = one[one["dte"] == 30.0]
        assert build_surface_payload(one, 100.0) is None

    def test_render_fills_and_uses_gl3d_bundle(self):
        html = render_surface_html(self.p)
        assert "plotly-gl3d" in html
        assert "Plotly.newPlot" in html
        assert "SPY" in html
        assert "{payload}" not in html and "{ticker}" not in html  # format actually filled


# ── ΔIV compare payload ──────────────────────────────────────────────────────

class TestDiffPayload:
    def setup_method(self):
        self.p = build_diff_payload(
            _surface_df(base_iv=18.0), 100.0, _surface_df(base_iv=15.0), 100.0,
            ticker="SPY", label_a="today", label_b="5d",
        )

    def test_not_none(self):
        assert self.p is not None

    def test_has_both_dates_slices(self):
        assert len(self.p["smile_a"]) == GRID_DTE
        assert len(self.p["smile_b"]) == GRID_DTE
        assert len(self.p["term_a"]) == GRID_LM
        assert len(self.p["term_b"]) == GRID_LM

    def test_diff_grid_shape(self):
        assert len(self.p["IVd"]) == GRID_LM
        assert all(len(row) == GRID_DTE for row in self.p["IVd"])

    def test_cap_positive(self):
        assert self.p["cap"] > 0

    def test_none_when_one_side_empty(self):
        assert build_diff_payload(_surface_df(), 100.0, pd.DataFrame(), 100.0) is None

    def test_render_fills(self):
        html = render_diff_html(self.p)
        assert "Plotly.newPlot" in html
        assert "today" in html and "5d" in html
        assert "{payload}" not in html


# ── movie payload ────────────────────────────────────────────────────────────

def _snaps(n: int = 3):
    return [(f"Jun {10+i}", _surface_df(base_iv=14.0 + i), 100.0) for i in range(n)]


class TestMoviePayloadLevel:
    def setup_method(self):
        self.p = build_movie_payload(_snaps(3), ticker="SPY", mode="level")

    def test_frames_match_sessions(self):
        assert len(self.p["frames"]) == 3

    def test_level_uses_plasma_and_pct(self):
        assert self.p["colorscale"] == "Plasma"
        assert self.p["atm_suffix"] == "%"
        assert self.p["ref_date"] is None

    def test_frame_has_atm_and_iv_grid(self):
        f = self.p["frames"][0]
        assert "atm" in f and "IV" in f
        assert len(f["IV"]) == GRID_LM

    def test_none_below_two_sessions(self):
        assert build_movie_payload(_snaps(1), mode="level") is None

    def test_render_fills(self):
        html = render_movie_html(self.p)
        assert "Plotly.newPlot" in html and "addFrames" in html
        assert "{payload}" not in html and "{modelabel}" not in html


# ── adversarial / degenerate inputs (25-02 hardening) ────────────────────────

class TestSurfaceEdgeCases:
    """E17 singular fit, E18 spot<=0, E19 missing column — defined results, never silently-wrong."""

    @staticmethod
    def _dup_chain() -> pd.DataFrame:
        # Exact-duplicate (dte, log_moneyness) rows → near-singular RBF design matrix.
        # smoothing=0.0 (below) removes the regulariser so the singularity is deterministic.
        d = _surface_df()
        dup = d[d["dte"] == 7.0].iloc[[0]]  # dte>=fit_floor so it survives into the fit set
        return pd.concat([d, dup, dup, dup], ignore_index=True)

    def test_singular_fit_surface_is_none(self):
        # E17: pre-fix this raised scipy LinAlgError; post-fix it degrades to None.
        assert build_surface_payload(self._dup_chain(), 100.0, smoothing=0.0) is None

    def test_singular_fit_diff_is_none(self):
        # E17: either side triggering a singular fit degrades the whole diff to None.
        assert build_diff_payload(
            self._dup_chain(), 100.0, _surface_df(base_iv=15.0), 100.0, smoothing=0.0,
        ) is None

    def test_spot_non_positive_defined_no_raise(self):
        # E18: spot<=0 yields a defined result (None here), never an uncaught crash mid-render.
        for bad_spot in (0.0, -5.0):
            res = build_surface_payload(_surface_df(), bad_spot)
            assert res is None or isinstance(res, dict)

    def test_missing_column_raises_keyerror(self):
        # E19: a corrupt schema (missing structural column) must fail loudly, not silently.
        broken = _surface_df().drop(columns=["log_moneyness"])
        with pytest.raises(KeyError):
            build_surface_payload(broken, 100.0)


class TestMoviePayloadChange:
    def setup_method(self):
        self.p = build_movie_payload(_snaps(3), ticker="SPY", mode="change")

    def test_change_is_diverging_and_pp(self):
        assert isinstance(self.p["colorscale"], list)  # explicit blue→white→red
        assert self.p["atm_suffix"] == "pp"

    def test_change_ref_is_first_session(self):
        assert self.p["ref_date"] == "Jun 10"

    def test_change_scale_symmetric_around_zero(self):
        assert self.p["z_floor"] == pytest.approx(-self.p["z_cap"], abs=0.2)
