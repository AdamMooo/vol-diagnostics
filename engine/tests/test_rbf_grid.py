"""Plan 08-01 Task 2: rbf_grid extraction must be numerically identical to the
pre-refactor inline RBF block, with the <6-point NaN guard and non-negative clip."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.interpolate import RBFInterpolator

from engine import config
from engine.gex.analytics import rbf_grid


def _fixed_surface_df(spot: float = 500.0) -> pd.DataFrame:
    """Deterministic OTM scatter spanning several expiries and the ±15% band."""
    rows = []
    for dte in [7, 14, 30, 60, 90, 120]:
        for ks in [0.90, 0.95, 1.0, 1.05, 1.10]:
            rows.append({
                "dte": float(dte),
                "strike": spot * ks,
                "iv_pct": 20.0 + (1.0 - ks) * 12.0 + dte * 0.01,
                "log_moneyness": np.log(ks),
                "moneyness": ks,
            })
    return pd.DataFrame(rows)


def _reference_iv(surface_df, spot, dte_grid, otm_grid, clip, dte_floor=5):
    """Inline log-moneyness recomputation (smoothing=1.5 literal)."""
    log_m = np.log(surface_df["strike"].to_numpy() / spot)
    dte_v = surface_df["dte"].to_numpy()
    iv_v = surface_df["iv_pct"].to_numpy()
    mask = (np.abs(log_m) <= clip) & (dte_v >= dte_floor)
    log_m, dte_v, iv_v = log_m[mask], dte_v[mask], iv_v[mask]
    pts = np.column_stack([dte_v, log_m])
    pts_std = pts.std(axis=0)
    pts_std[pts_std < 1e-6] = 1.0
    rbf = RBFInterpolator(pts / pts_std, iv_v, kernel="thin_plate_spline", smoothing=1.5)
    DTE, OTM = np.meshgrid(dte_grid, otm_grid)
    grid_pts = np.column_stack([DTE.ravel(), OTM.ravel()])
    IV = rbf(grid_pts / pts_std).reshape(DTE.shape)
    return np.clip(IV, 0.0, None)


def test_rbf_grid_matches_inline_recomputation():
    spot = 500.0
    df = _fixed_surface_df(spot)
    clip = config.SURFACE_PLOT_OTM_CLIP
    dte_grid = np.linspace(5.0, 120.0, config.SURFACE_GRID_DTE)
    otm_grid = np.linspace(-clip, clip, config.SURFACE_GRID_LM)

    out = rbf_grid(df, spot, dte_grid, otm_grid, dte_floor=5, clip=clip)
    ref = _reference_iv(df, spot, dte_grid, otm_grid, clip, dte_floor=5)

    assert out.shape == (len(otm_grid), len(dte_grid))
    np.testing.assert_allclose(out, ref, rtol=0, atol=1e-9)


def test_rbf_grid_default_clip_matches_config():
    """clip=None must resolve to config.SURFACE_PLOT_OTM_CLIP (same result)."""
    spot = 500.0
    df = _fixed_surface_df(spot)
    clip = config.SURFACE_PLOT_OTM_CLIP
    dte_grid = np.linspace(5.0, 120.0, config.SURFACE_GRID_DTE)
    otm_grid = np.linspace(-clip, clip, config.SURFACE_GRID_LM)

    out_default = rbf_grid(df, spot, dte_grid, otm_grid)
    out_explicit = rbf_grid(df, spot, dte_grid, otm_grid, clip=clip)
    np.testing.assert_allclose(out_default, out_explicit, rtol=0, atol=1e-12)


def test_rbf_grid_under_six_points_returns_all_nan():
    spot = 500.0
    df = pd.DataFrame([
        {"dte": 30.0, "strike": spot, "iv_pct": 20.0,
         "log_moneyness": 0.0, "moneyness": 1.0}
    ])
    dte_grid = np.linspace(5.0, 90.0, config.SURFACE_GRID_DTE)
    otm_grid = np.linspace(-0.15, 0.15, config.SURFACE_GRID_LM)
    out = rbf_grid(df, spot, dte_grid, otm_grid)
    assert out.shape == (len(otm_grid), len(dte_grid))
    assert np.isnan(out).all()


def test_rbf_grid_never_negative():
    spot = 500.0
    df = _fixed_surface_df(spot)
    clip = config.SURFACE_PLOT_OTM_CLIP
    dte_grid = np.linspace(5.0, 120.0, config.SURFACE_GRID_DTE)
    otm_grid = np.linspace(-clip, clip, config.SURFACE_GRID_LM)
    out = rbf_grid(df, spot, dte_grid, otm_grid)
    assert np.nanmin(out) >= 0.0
