"""Plan 08-02 (convex-hull rev): plot_vol_surface NaN-masks cells OUTSIDE the quote hull
(extrapolation) — present in the deep wings where strikes are absent, near-zero for a chain
that fills the displayed band."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from engine import config
from engine.gex.analytics import plot_vol_surface

SPOT = 500.0


def _chain(dtes, pct_otms, spot=SPOT):
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


def _z(fig):
    return np.array(fig.data[0].z, dtype=float)


def test_dense_chain_has_few_holes():
    df = _chain(np.arange(5, 95, 5), np.arange(-15, 16, 2.5))
    fig = plot_vol_surface(df, "SPY", SPOT)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1 and type(fig.data[0]).__name__ == "Surface"
    z = _z(fig)
    assert np.isnan(z).mean() < 0.15


def test_wing_extrapolation_creates_nan_holes():
    # quotes only to +/-8% but the plot grid spans +/-15% -> the wings are extrapolation -> holes
    df = _chain([10, 20, 40, 70, 90], [-8, -4, 0, 4, 8])
    fig = plot_vol_surface(df, "SPY", SPOT)
    z = _z(fig)
    assert np.isnan(z).any()

    otm_grid = np.linspace(-config.SURFACE_PLOT_OTM_CLIP,
                           config.SURFACE_PLOT_OTM_CLIP, config.SURFACE_GRID_LM)
    wing_idx = int(np.argmin(np.abs(otm_grid - np.log(1.14))))   # beyond +/-8% quotes
    atm_idx = int(np.argmin(np.abs(otm_grid - 0.0)))
    assert np.isnan(z[wing_idx, :]).mean() > 0.5         # deep wing mostly NaN
    assert (~np.isnan(z[atm_idx, :])).any()              # ATM column retains real values


def test_surface_still_one_valid_figure():
    fig = plot_vol_surface(pd.DataFrame(), "SPY", spot=SPOT)
    assert isinstance(fig, go.Figure)
