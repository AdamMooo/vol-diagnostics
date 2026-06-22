"""
Sensitivity sweep for the vol-surface smoothing parameter (VALID-03, D-12).

Re-runnable proof artifact — keeps SURFACE_SMOOTHING justified and live rather than frozen.
Sweeps smoothing, scored on fit RMSE / max-residual / leave-one-expiry-out CV (pp): lower fit
RMSE = closer fit; too little smoothing overfits quote noise (cv_rmse rises). Also reports the
convex-hull coverage on the standard grid for context (the coverage gate is parameter-free —
support = inside the quote hull — so there is nothing to sweep there).

Usage:
    python -m engine.surface.surface_sweep                # SPY (most recent stored day, else live)
    python -m engine.surface.surface_sweep --ticker QQQ

Reads the most recent stored day from engine.data.surface_history; falls back to a live
compute_ticker() fetch if the store is empty. NEVER edits config.py — the human
reads the table and decides.
"""
from __future__ import annotations

import argparse

import numpy as np

from engine import config

SMOOTHING_CANDIDATES = (0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0)
_DTE_FLOOR = 5


def _in_band(surface_df, spot):
    clip = config.SURFACE_PLOT_OTM_CLIP
    log_m = np.log(surface_df["strike"].to_numpy() / spot)
    dte_v = surface_df["dte"].to_numpy()
    iv_v = surface_df["iv_pct"].to_numpy()
    m = (np.abs(log_m) <= clip) & (dte_v >= _DTE_FLOOR)
    return dte_v[m], log_m[m], iv_v[m]


def _residuals(surface_df, spot, smoothing):
    """fit_rmse, max_resid, cv_rmse (pp) at a given smoothing; None if too sparse."""
    from scipy.interpolate import RBFInterpolator
    dte_v, log_m, iv_v = _in_band(surface_df, spot)
    if len(iv_v) < 6 or len(np.unique(dte_v)) < 2:
        return None
    pts = np.column_stack([dte_v, log_m])
    std = pts.std(axis=0)
    std[std < 1e-6] = 1.0
    rbf = RBFInterpolator(pts / std, iv_v, kernel="thin_plate_spline", smoothing=smoothing)
    resid = rbf(pts / std) - iv_v
    fit_rmse = float(np.sqrt(np.mean(resid ** 2)))
    max_resid = float(np.max(np.abs(resid)))
    cv_sq = []
    for e in np.unique(dte_v):
        hold = dte_v == e
        train = ~hold
        if train.sum() < 4 or len(np.unique(dte_v[train])) < 2:
            continue
        tp = np.column_stack([dte_v[train], log_m[train]])
        ts = tp.std(axis=0)
        ts[ts < 1e-6] = 1.0
        rbf_cv = RBFInterpolator(tp / ts, iv_v[train], kernel="thin_plate_spline", smoothing=smoothing)
        hp = np.column_stack([dte_v[hold], log_m[hold]])
        cv_sq.extend(((rbf_cv(hp / ts) - iv_v[hold]) ** 2).tolist())
    cv_rmse = float(np.sqrt(np.mean(cv_sq))) if cv_sq else float("nan")
    return {"fit_rmse": fit_rmse, "max_resid": max_resid, "cv_rmse": cv_rmse}


def _standard_grid(surface_df, spot):
    clip = config.SURFACE_PLOT_OTM_CLIP
    dte_v, _, _ = _in_band(surface_df, spot)
    dte_max = (min(float(dte_v.max()), float(config.SURFACE_DTE_MAX))
               if len(dte_v) else _DTE_FLOOR + 1.0)
    dte_grid = np.linspace(_DTE_FLOOR, max(dte_max, _DTE_FLOOR + 1.0), config.SURFACE_GRID_DTE)
    otm_grid = np.linspace(-clip, clip, config.SURFACE_GRID_LM)
    return dte_grid, otm_grid


def sweep_smoothing(surface_df, spot, candidates=SMOOTHING_CANDIDATES):
    """One row per smoothing candidate: smoothing, fit_rmse, max_resid, cv_rmse (pp)."""
    rows = []
    for s in candidates:
        r = _residuals(surface_df, spot, s)
        if r is None:
            rows.append({"smoothing": s, "fit_rmse": float("nan"),
                         "max_resid": float("nan"), "cv_rmse": float("nan")})
        else:
            rows.append({"smoothing": s, **r})
    return rows


def hull_coverage(surface_df, spot):
    """Convex-hull coverage % on the standard grid (parameter-free — for context only)."""
    from engine.gex.analytics import coverage_mask
    dte_grid, otm_grid = _standard_grid(surface_df, spot)
    return 100.0 * float(coverage_mask(surface_df, spot, dte_grid, otm_grid).mean())


def _load_surface(ticker):
    from engine.data.surface_history import list_available_dates, load_surface_snapshot
    dates = list_available_dates(ticker)
    if dates:
        df, spot = load_surface_snapshot(ticker, dates[0])
        if df is not None and not df.empty and spot:
            return df, spot, f"stored snapshot {dates[0]}"
    try:
        from engine.compute import compute_ticker
        data = compute_ticker(ticker)
        return data.get("surface_df"), data.get("spot"), "live compute_ticker()"
    except Exception as exc:  # network/data failure — sweep stays safe to run
        return None, None, f"unavailable ({exc})"


def main(ticker="SPY"):
    surface_df, spot, source = _load_surface(ticker)
    print(f"[surface_sweep] {ticker}: data source = {source}")
    if surface_df is None or surface_df.empty or not spot:
        print("[surface_sweep] no surface data available — nothing to sweep. "
              "Run `python -m engine.run_daily` to accumulate snapshots, then retry.")
        return 0

    print(f"\n=== smoothing sweep ({ticker}, spot {spot:.2f}) — fit vs over-smoothing ===")
    print(f"{'smoothing':>10} {'fit_rmse':>10} {'max_resid':>10} {'cv_rmse':>10}   (pp)")
    for r in sweep_smoothing(surface_df, spot):
        print(f"{r['smoothing']:>10.1f} {r['fit_rmse']:>10.2f} {r['max_resid']:>10.2f} {r['cv_rmse']:>10.2f}")

    print(f"\n=== coverage ({ticker}) — convex-hull support on the standard grid ===")
    print(f"  coverage {hull_coverage(surface_df, spot):.1f}%  "
          f"(interpolation inside the quote hull; corners beyond the data are honest holes)")

    print(f"\n[surface_sweep] configured: SURFACE_SMOOTHING={config.SURFACE_SMOOTHING} "
          f"— kept unless the table clearly argues otherwise. Coverage is parameter-free (convex hull).")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sweep vol-surface smoothing; report hull coverage.")
    parser.add_argument("--ticker", default="SPY")
    args = parser.parse_args()
    raise SystemExit(main(ticker=args.ticker))
