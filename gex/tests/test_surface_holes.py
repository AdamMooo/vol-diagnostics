"""Plan 08-02: plot_vol_surface applies coverage_mask so unsupported cells render
as honest NaN holes — present where quotes are absent, near-zero where dense."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from gex import config
from gex.analytics import plot_vol_surface


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


def _z(fig):
    return np.array(fig.data[0].z, dtype=float)


def test_dense_chain_has_few_holes():
    spot = 500.0
    df = _chain(np.arange(5, 95, 5), np.arange(-15, 16, 2.5), spot)
    fig = plot_vol_surface(df, "SPY", spot)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1 and type(fig.data[0]).__name__ == "Surface"
    z = _z(fig)
    assert np.isnan(z).mean() < 0.05


def test_missing_expiry_gap_creates_nan_holes():
    spot = 500.0
    # two DTE clusters (7-14 and 80-90) with a wide internal gap; full %OTM span
    df = _chain([7, 10, 14, 80, 85, 90], [-15, -7.5, 0, 7.5, 15], spot)
    fig = plot_vol_surface(df, "SPY", spot)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1 and type(fig.data[0]).__name__ == "Surface"
    z = _z(fig)

    # holes exist
    assert np.isnan(z).any()

    # the mid-DTE gap (~45 DTE, no quotes) is mostly NaN
    clip = config.SURFACE_PLOT_OTM_CLIP * 100.0
    dte_grid = np.linspace(5.0, 90.0, config.SURFACE_GRID_DTE)
    mid_idx = int(np.argmin(np.abs(dte_grid - 45.0)))
    assert np.isnan(z[:, mid_idx]).mean() > 0.5

    # a near-cluster column (~10 DTE) retains real (non-NaN) values
    near_idx = int(np.argmin(np.abs(dte_grid - 10.0)))
    assert (~np.isnan(z[:, near_idx])).any()


def test_surface_still_one_valid_figure():
    """No regression to the Plan-06 strip: empty df still returns a valid Figure."""
    fig = plot_vol_surface(pd.DataFrame(), "SPY", spot=500.0)
    assert isinstance(fig, go.Figure)
