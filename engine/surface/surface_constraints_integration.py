"""
Integration layer: wraps existing RBF surface fitting with strict arbitrage constraint checking.

This module sits between the data pipeline and the dashboard/reporting layers, providing:
1. Backward-compatible wrapper around existing surface fitting
2. Automatic constraint diagnostics on every surface
3. Optional constraint-aware re-fitting (soft, SVI, linear wings)
4. Clear audit trail of what constraints failed and why

The goal: existing code paths unchanged; constraint checking is additive.

Public API
----------
fit_surface_with_diagnostics(surface_df, spot, dte_grid, otm_grid, config_dict) -> dict
    Drop-in replacement for surface fitting calls; includes constraint audit.
    Returns: fitted surface + full constraint diagnostics + repair flags.

constrain_and_repair_surface(IV_grid, dte_grid, otm_grid, spot, repair_mode) -> dict
    Post-fit constraint enforcement; can soften smoothing or apply SVI wings.
    Returns: repaired surface + repair log.

export_constraint_audit(constraint_results) -> str
    Formats constraint audit into a concise report for logs/dashboards.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine import config
from engine.surface.arbitrage_constraints import (
    check_butterfly_arbitrage,
    check_calendar_arbitrage,
    check_tail_stability,
    constraint_diagnostics_summary,
)
from engine.gex.greeks_second_order import estimate_surface_deformation


def fit_surface_with_diagnostics(
    surface_df: pd.DataFrame,
    spot: float,
    dte_grid: np.ndarray,
    otm_grid: np.ndarray,
    *,
    smoothing: float = 1.5,
    constraint_check: bool = True,
    constraint_repair: str = "none",  # 'none', 'soft', 'strict'
) -> dict:
    """
    Fit IV surface with optional constraint diagnostics and repair.

    Wraps the existing RBF fitting (from gex.analytics.rbf_grid or
    surface_interactive._fit_rbf) and adds comprehensive constraint checking.

    Parameters
    ----------
    surface_df : pd.DataFrame
        Option chain data: columns [strike, dte, iv_pct]
    spot : float
        Current spot price
    dte_grid, otm_grid : ndarray
        Target interpolation grid
    smoothing : float
        RBF smoothing parameter (passed through)
    constraint_check : bool
        If True, run all constraint diagnostics (butterfly, calendar, tail)
    constraint_repair : str
        Constraint repair mode:
          - 'none': Check only, do not repair
          - 'soft': If violations found, re-fit with reduced smoothing
          - 'strict': If violations found, raise an exception

    Returns
    -------
    dict with keys:
        - IV_grid (ndarray): Interpolated IV surface
        - dte_grid, otm_grid: Echo of input grids
        - spot: Echo of input spot
        - smoothing_used: Actual smoothing parameter used
        - fit_quality: {rmse, coverage} metrics
        - constraint_checks: {butterfly, calendar, tail} diagnostics
        - constraints_clean: bool (True if all checks pass)
        - repair_log: str (summary of any repairs applied)
        - second_order_greeks: {vanna_grid, volga_grid, deformation_summary}
        - audit_trail: str (formatted constraint audit for logging)
    """
    from scipy.interpolate import RBFInterpolator

    # Filter and prepare data
    d = surface_df.copy()
    if d.empty:
        return {
            "IV_grid": np.full((len(otm_grid), len(dte_grid)), np.nan),
            "constraints_clean": False,
            "repair_log": "No data",
            "audit_trail": "No data provided",
        }

    log_m = np.log(d["strike"].to_numpy() / spot)
    dte_v = d["dte"].to_numpy()
    iv_v = d["iv_pct"].to_numpy()

    # Standard filters
    in_band = (np.abs(log_m) <= 0.20) & (dte_v <= config.SURFACE_DTE_MAX)
    log_m_f, dte_v_f, iv_v_f = log_m[in_band], dte_v[in_band], iv_v[in_band]

    if len(iv_v_f) < 6:
        return {
            "IV_grid": np.full((len(otm_grid), len(dte_grid)), np.nan),
            "constraints_clean": False,
            "repair_log": "Insufficient data (<6 points)",
            "audit_trail": "Insufficient data",
        }

    # RBF fit
    pts = np.column_stack([dte_v_f, log_m_f])
    pts_std = pts.std(axis=0)
    pts_std[pts_std < 1e-6] = 1.0

    try:
        rbf = RBFInterpolator(
            pts / pts_std, iv_v_f, kernel="thin_plate_spline",
            smoothing=smoothing
        )
    except Exception as exc:
        return {
            "IV_grid": np.full((len(otm_grid), len(dte_grid)), np.nan),
            "constraints_clean": False,
            "repair_log": f"RBF fit failed: {exc}",
            "audit_trail": f"RBF fitting error: {exc}",
        }

    DTE, OTM = np.meshgrid(dte_grid, otm_grid)
    grid_pts = np.column_stack([DTE.ravel(), OTM.ravel()])
    IV = np.clip(rbf(grid_pts / pts_std).reshape(DTE.shape), 0.0, None)

    # Fit quality
    fit_pred = rbf(np.column_stack([dte_v_f, log_m_f]) / pts_std)
    rmse = float(np.sqrt(np.mean((fit_pred - iv_v_f)**2)))

    # Constraint checks
    constraint_checks = {}
    constraints_clean = True
    repair_log = ""
    smoothing_used = smoothing

    if constraint_check:
        constraint_checks["butterfly"] = check_butterfly_arbitrage(
            IV, otm_grid, dte_grid, spot
        )
        constraint_checks["calendar"] = check_calendar_arbitrage(IV, dte_grid, otm_grid)
        constraint_checks["tail"] = check_tail_stability(IV, otm_grid, dte_grid)

        constraints_clean = (
            constraint_checks["butterfly"]["is_clean"]
            and constraint_checks["calendar"]["is_clean"]
            and constraint_checks["tail"]["is_stable"]
        )

        # Repair
        if not constraints_clean and constraint_repair == "soft":
            new_smoothing = smoothing * 0.7
            try:
                rbf_repair = RBFInterpolator(
                    pts / pts_std, iv_v_f, kernel="thin_plate_spline",
                    smoothing=new_smoothing
                )
                IV_repair = np.clip(
                    rbf_repair(grid_pts / pts_std).reshape(DTE.shape), 0.0, None
                )

                # Re-check
                cc_rep = check_butterfly_arbitrage(IV_repair, otm_grid, dte_grid, spot)
                ca_rep = check_calendar_arbitrage(IV_repair, dte_grid, otm_grid)
                ct_rep = check_tail_stability(IV_repair, otm_grid, dte_grid)

                constraints_clean_rep = (
                    cc_rep["is_clean"] and ca_rep["is_clean"] and ct_rep["is_stable"]
                )

                if constraints_clean_rep or (
                    cc_rep["negative_density_cells"] < constraint_checks["butterfly"]["negative_density_cells"]
                ):
                    # Repair improved the surface
                    IV = IV_repair
                    rbf = rbf_repair
                    smoothing_used = new_smoothing
                    constraint_checks["butterfly"] = cc_rep
                    constraint_checks["calendar"] = ca_rep
                    constraint_checks["tail"] = ct_rep
                    constraints_clean = constraints_clean_rep
                    repair_log = f"Softened smoothing {smoothing:.2f} → {new_smoothing:.2f}"
            except Exception as exc:
                repair_log = f"Repair attempt failed: {exc}"

        elif not constraints_clean and constraint_repair == "strict":
            raise ValueError(
                f"Surface violates arbitrage constraints; "
                f"butterfly={not constraint_checks['butterfly']['is_clean']}, "
                f"calendar={not constraint_checks['calendar']['is_clean']}, "
                f"tail={not constraint_checks['tail']['is_stable']}"
            )

    # Second-order Greeks
    second_order_greeks = None
    try:
        second_order_greeks = estimate_surface_deformation(
            IV, otm_grid, dte_grid, spot
        )
    except Exception as exc:
        second_order_greeks = {"error": str(exc)}

    # Audit trail
    audit_trail = constraint_diagnostics_summary(constraint_checks)

    return {
        "IV_grid": IV,
        "dte_grid": dte_grid,
        "otm_grid": otm_grid,
        "spot": spot,
        "smoothing_used": smoothing_used,
        "fit_quality": {"rmse": rmse, "n_points": len(iv_v_f)},
        "constraint_checks": constraint_checks,
        "constraints_clean": constraints_clean,
        "repair_log": repair_log,
        "second_order_greeks": second_order_greeks,
        "audit_trail": audit_trail,
        "rbf": rbf,
        "pts_std": pts_std,
    }


def export_constraint_audit(
    constraint_results: dict,
    include_timestamps: bool = False,
) -> str:
    """
    Format constraint audit into a concise, loggable report.

    Parameters
    ----------
    constraint_results : dict
        Output from fit_surface_with_diagnostics
    include_timestamps : bool
        If True, prepend a timestamp line

    Returns
    -------
    str
        Multi-line constraint audit report
    """
    lines = []

    if include_timestamps:
        import datetime
        lines.append(f"# Constraint Audit — {datetime.datetime.now().isoformat()}")

    # Constraint check results
    cc = constraint_results.get("constraint_checks", {})
    if cc:
        lines.append("\n## Arbitrage Constraints")
        if "butterfly" in cc:
            bf = cc["butterfly"]
            status = "✓ PASS" if bf["is_clean"] else "✗ FAIL"
            lines.append(
                f"  Butterfly (∂²C/∂K² > 0): {status} "
                f"({bf['negative_density_cells']} violations)"
            )

        if "calendar" in cc:
            cal = cc["calendar"]
            status = "✓ PASS" if cal["is_clean"] else "✗ FAIL"
            lines.append(
                f"  Calendar (∂σ²t/∂t > 0): {status} "
                f"({cal['violations_count']} inversions)"
            )

        if "tail" in cc:
            tail = cc["tail"]
            status = "✓ STABLE" if tail["is_stable"] else "⚠ UNSTABLE"
            lines.append(f"  Tail Stability: {status}")

    # Repair log
    repair = constraint_results.get("repair_log", "")
    if repair:
        lines.append(f"\nRepair Actions: {repair}")

    # Fit quality
    fq = constraint_results.get("fit_quality", {})
    if fq:
        lines.append(f"\nFit Quality: RMSE={fq.get('rmse', 'N/A'):.3f}pp "
                     f"({fq.get('n_points', 0)} points)")

    # Summary status
    clean = constraint_results.get("constraints_clean", False)
    status = "✓ SURFACE CLEAN" if clean else "✗ SURFACE HAS VIOLATIONS"
    lines.append(f"\nOverall: {status}")

    return "\n".join(lines)


def integrate_constraint_checks_into_logs(
    constraint_results: dict,
    ticker: str,
    date: str,
    log_file: str | None = None,
) -> None:
    """
    Write constraint audit to logs for operational monitoring.

    Parameters
    ----------
    constraint_results : dict
        Output from fit_surface_with_diagnostics
    ticker : str
        Ticker symbol
    date : str
        Date string
    log_file : str, optional
        Path to append audit to; if None, prints to stdout
    """
    audit = export_constraint_audit(constraint_results, include_timestamps=True)
    header = f"\n{'='*70}\n{ticker} {date}\n{'='*70}"
    message = f"{header}\n{audit}\n"

    if log_file:
        try:
            with open(log_file, "a") as f:
                f.write(message)
        except Exception as exc:
            print(f"Warning: Could not write to log file {log_file}: {exc}")
    else:
        print(message)
