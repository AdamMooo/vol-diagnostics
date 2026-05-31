"""Plan 08-01 Task 3 (convex-hull rev): coverage_mask supports interpolation INSIDE the
convex hull of real quotes and holes only extrapolation OUTSIDE it. Between-expiry
interpolation is honest (the kNN-radius mask wrongly holed it)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from gex import config
from gex.analytics import coverage_mask

CLIP = config.SURFACE_PLOT_OTM_CLIP * 100.0


def _chain(dtes, pct_otms, spot=500.0):
    rows = []
    for dte in dtes:
        for p in pct_otms:
            ks = 1.0 + p / 100.0
            rows.append({
                "dte": float(dte),
                "strike": spot * ks,
                "iv_pct": 20.0 + (-p) * 0.3 + dte * 0.01,
                "log_moneyness": np.log(ks),
                "moneyness": ks,
            })
    return pd.DataFrame(rows)


def _grid(dte_lo=5.0, dte_hi=90.0):
    return (np.linspace(dte_lo, dte_hi, config.SURFACE_GRID_DTE),
            np.linspace(-CLIP, CLIP, config.SURFACE_GRID_LM))


def test_dense_chain_is_nearly_all_supported():
    spot = 500.0
    df = _chain(np.arange(5, 95, 5), np.arange(-15, 16, 2.5), spot)
    dte_grid, otm_grid = _grid(5.0, 90.0)
    mask = coverage_mask(df, spot, dte_grid, otm_grid)
    assert mask.shape == (len(otm_grid), len(dte_grid))
    # hull covers all but the boundary ring (grid extent coincides with the quote extent here)
    assert mask.mean() >= 0.85


def test_between_expiry_gap_is_supported():
    """The fix: interpolating across a missing-expiry gap is honest, not fabricated."""
    spot = 500.0
    df = _chain([10, 15, 70, 80], [-8, -4, 0, 4, 8], spot)   # wide gap 15..70
    dte_grid, otm_grid = _grid(5.0, 90.0)
    mask = coverage_mask(df, spot, dte_grid, otm_grid)
    dte_idx = int(np.argmin(np.abs(dte_grid - 45.0)))         # inside the gap, between clusters
    otm_idx = int(np.argmin(np.abs(otm_grid - 0.0)))
    assert mask[otm_idx, dte_idx]                             # interior of hull -> supported


def test_extrapolation_outside_hull_is_holed():
    spot = 500.0
    df = _chain([20, 35, 50, 60], [-6, -3, 0, 3, 6], spot)   # DTE 20-60, %OTM +/-6 only
    dte_grid, otm_grid = _grid(5.0, 90.0)
    mask = coverage_mask(df, spot, dte_grid, otm_grid)
    atm = int(np.argmin(np.abs(otm_grid - 0.0)))
    assert mask[atm, int(np.argmin(np.abs(dte_grid - 40.0)))]          # interior -> supported
    assert not mask[atm, int(np.argmin(np.abs(dte_grid - 85.0)))]     # beyond max expiry -> holed
    assert not mask[int(np.argmin(np.abs(otm_grid - 14.0))),
                    int(np.argmin(np.abs(dte_grid - 40.0)))]          # deep wing -> holed
    assert not mask.all()


def test_under_six_points_all_unsupported():
    spot = 500.0
    df = _chain([30], [0], spot)  # 1 quote
    dte_grid, otm_grid = _grid()
    mask = coverage_mask(df, spot, dte_grid, otm_grid)
    assert mask.shape == (len(otm_grid), len(dte_grid))
    assert not mask.any()


def test_single_expiry_all_unsupported():
    """One expiry is collinear in (DTE, %OTM) — no 2D hull — nothing supported."""
    spot = 500.0
    df = _chain([30], [-10, -5, 0, 5, 10, 12], spot)  # 6 pts, 1 expiry
    dte_grid, otm_grid = _grid()
    mask = coverage_mask(df, spot, dte_grid, otm_grid)
    assert not mask.any()
