"""Plan 08-01 Task 3: coverage_mask flags grid cells with no nearby real quote.
kNN over real quote locations, data-adaptive radius (k × median NN distance)."""
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
    assert mask.mean() > 0.95


def test_missing_expiry_gap_creates_holes():
    spot = 500.0
    # quotes clustered at the short end only; grid spans to 90 DTE
    df = _chain([7, 10, 14], [-10, -5, 0, 5, 10], spot)
    dte_grid, otm_grid = _grid(5.0, 90.0)
    mask = coverage_mask(df, spot, dte_grid, otm_grid)

    # holes must exist somewhere
    assert not mask.all()

    # a cell at DTE=10, ATM (a real quote sits there) must be supported
    dte_idx = int(np.argmin(np.abs(dte_grid - 10.0)))
    otm_idx = int(np.argmin(np.abs(otm_grid - 0.0)))
    assert mask[otm_idx, dte_idx]

    # the far-DTE region (~75 DTE, no quotes near) must be overwhelmingly unsupported
    far_idx = int(np.argmin(np.abs(dte_grid - 75.0)))
    assert mask[:, far_idx].mean() < 0.2


def test_under_six_points_all_unsupported():
    spot = 500.0
    df = _chain([30], [0], spot)  # 1 quote
    dte_grid, otm_grid = _grid()
    mask = coverage_mask(df, spot, dte_grid, otm_grid)
    assert mask.shape == (len(otm_grid), len(dte_grid))
    assert not mask.any()


def test_radius_is_data_adaptive_not_fixed():
    """Scaling DTE values AND the DTE grid by a constant must leave the mask
    unchanged — the radius scales with the data, so it's adaptive, not a fixed cutoff."""
    spot = 500.0
    df = _chain(np.arange(5, 95, 5), np.arange(-15, 16, 2.5), spot)
    dte_grid, otm_grid = _grid(5.0, 90.0)
    base = coverage_mask(df, spot, dte_grid, otm_grid)

    c = 2.0
    df_scaled = df.copy()
    df_scaled["dte"] = df_scaled["dte"] * c
    scaled = coverage_mask(df_scaled, spot, dte_grid * c, otm_grid)

    assert np.array_equal(base, scaled)
