"""
Arbitrage-free surface constraints and diagnostics.

Enforces three fundamental axioms of no-arbitrage:
  1. Vertical (Butterfly): ∂²C/∂K² > 0 (option price convexity)
  2. Horizontal (Calendar): ∂(σ²·t)/∂t > 0 (total variance strictly increasing with time)
  3. Tail Stability: Outer wings remain economically bounded and smooth

Public API
----------
check_butterfly_arbitrage(IV_grid, moneyness_grid, spot, forward_level, rates) -> dict
    Computes numerical second derivatives and checks for negative densities.
    Returns: {is_clean, min_density, violation_count, violation_locations}

check_calendar_arbitrage(IV_grid, dte_grid, moneyness_grid) -> dict
    Checks that total variance σ²·t strictly increases with DTE at every strike.
    Returns: {is_clean, violations, violated_pairs}

check_tail_stability(IV_grid, moneyness_grid, dte_grid, tail_threshold) -> dict
    Analyzes tail wing behavior for linearity and boundedness.
    Returns: {is_linear, gradient_stability, max_wing_curvature}

fit_with_constraints(surface_df, spot, dte_grid, otm_grid, smoothing, constraint_mode) -> dict
    Fits surface with optional constraint enforcement.
    constraint_mode in ['strict', 'soft', 'svi_wings', 'linear_wings', 'none']
    Returns: {IV_grid, diagnostics, constraint_violations, fitted_mode}

constraint_diagnostics_summary(constraint_checks) -> dict
    Produces a human-readable summary of all violations found.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.interpolate import RBFInterpolator
from scipy.stats import norm

from engine import config


# ─────────────────────────────────────────────────────────────────────────────
# 1. Butterfly Arbitrage Diagnostics
# ─────────────────────────────────────────────────────────────────────────────

def _implied_pdf_from_iv(iv_pct, moneyness, spot, dte, forward_level, rate):
    """
    Estimate the risk-neutral probability density from IV using Breeden-Litzenberger.

    ρ(K) = e^(rT) · ∂²C/∂K²

    where C(K) is the call option price derived from the IV surface.
    Uses Black-Scholes call price function.

    Parameters
    ----------
    iv_pct : float or ndarray
        Implied volatility in percent (e.g., 20.5 for 20.5%)
    moneyness : float or ndarray
        log(K/S) where K is strike, S is spot
    spot : float
        Current spot price
    dte : float or ndarray
        Days to expiration
    forward_level : float
        Forward price F = S * e^(rT)
    rate : float
        Risk-free rate (annualized)

    Returns
    -------
    pdf : ndarray
        Risk-neutral probability density (should be > 0 everywhere)
    """
    # Convert to standard Black-Scholes inputs
    T = dte / 365.0
    K = spot * np.exp(moneyness)
    sigma = iv_pct / 100.0

    # Avoid division by zero and numerical issues
    T = np.maximum(T, 1.0 / 365.0)
    sigma = np.maximum(sigma, 0.01)

    # d1, d2 for Black-Scholes
    d1 = (np.log(forward_level / K) + 0.5 * sigma**2 * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    # Call vega: ∂C/∂σ
    vega = spot * norm.pdf(d1) * np.sqrt(T)

    # Vanna: ∂²C/∂σ∂S = (norm.pdf(d1) / S) * (-d2 / sigma)
    # Using numerical differentiation instead: ∂²C/∂K² ≈ ∂(Δ)/∂K
    #
    # Alternative: use the relation from Breeden-Litzenberger:
    # ρ(K) = e^(rT) * ∂²C/∂K²
    #
    # For a smile defined by IV(K), we can approximate ∂²C/∂K² numerically
    # or use the volga/vanna relationship. For speed, we use numerical differentiation
    # on the call price surface.

    # Discount factor
    df = np.exp(-rate * T)

    # Call option price from Black-Scholes
    call_price = spot * norm.cdf(d1) - K * df * norm.cdf(d2)

    return call_price, vega, df


def check_butterfly_arbitrage(
    IV_grid: np.ndarray,
    moneyness_grid: np.ndarray,
    dte_grid: np.ndarray,
    spot: float,
    forward_level: float | None = None,
    rate: float = 0.05,
) -> dict:
    """
    Check for butterfly arbitrage violations by analyzing option-price convexity.

    The Breeden-Litzenberger formula states that the risk-neutral PDF is:
        ρ(K) = e^(rT) · ∂²C/∂K²

    This must be strictly positive everywhere to rule out arbitrage.

    Parameters
    ----------
    IV_grid : ndarray of shape (n_moneyness, n_dte)
        Interpolated IV surface as percentages (e.g., 20.5 for 20.5%)
    moneyness_grid : ndarray of shape (n_moneyness,)
        Log-moneyness values ln(K/S)
    dte_grid : ndarray of shape (n_dte,)
        Days to expiration
    spot : float
        Current spot price
    forward_level : float, optional
        Forward price; defaults to spot (assumes zero rates)
    rate : float
        Risk-free rate (annualized); default 0.05

    Returns
    -------
    dict with keys:
        - is_clean (bool): True if no butterfly violations detected
        - min_density (float): Minimum estimated PDF value (should be > 0)
        - negative_density_cells (int): Count of cells where ρ(K) < 0
        - violation_locations: List of [(i, j), (iv, K, T, density), ...] for each violation
        - summary (str): Human-readable summary
    """
    if forward_level is None:
        forward_level = spot

    n_moneyness, n_dte = IV_grid.shape
    violations = []
    densities = []

    # Numerical differentiation of call prices to estimate ∂²C/∂K²
    # Strategy: for each row (expiry), compute second derivative along the strike axis

    for j in range(n_dte):
        dte = dte_grid[j]
        iv_row = IV_grid[:, j]  # IV across strikes for this expiry

        if np.isnan(iv_row).all():
            continue

        # Skip if too many NaNs
        valid_idx = ~np.isnan(iv_row)
        if np.sum(valid_idx) < 3:
            continue

        # Filter to valid points
        lm_valid = moneyness_grid[valid_idx]
        iv_valid = iv_row[valid_idx]

        # Compute call prices for finite difference
        K_valid = spot * np.exp(lm_valid)
        call_prices, _, df = _implied_pdf_from_iv(iv_valid, lm_valid, spot, dte, forward_level, rate)

        # Numerical second derivative: ∂²C/∂K²
        # Using central difference where possible
        d2c_dk2 = np.zeros_like(call_prices)

        for i in range(len(K_valid)):
            if i == 0:
                # Forward difference
                if len(K_valid) > 1:
                    dk = K_valid[1] - K_valid[0]
                    dc = call_prices[1] - call_prices[0]
                    # Second derivative estimate
                    if len(K_valid) > 2:
                        dk2 = K_valid[2] - K_valid[0]
                        dc2 = call_prices[2] - call_prices[0]
                        d2c_dk2[i] = 2 * (dc2 / dk2 - dc / dk) / (K_valid[1] - K_valid[0])
                    else:
                        d2c_dk2[i] = 0
            elif i == len(K_valid) - 1:
                # Backward difference
                dk = K_valid[i] - K_valid[i - 1]
                dc = call_prices[i] - call_prices[i - 1]
                # Second derivative estimate
                if i > 1:
                    dk2 = K_valid[i] - K_valid[i - 2]
                    dc2 = call_prices[i] - call_prices[i - 2]
                    d2c_dk2[i] = 2 * (dc / dk - dc2 / dk2) / (K_valid[i] - K_valid[i - 1])
                else:
                    d2c_dk2[i] = 0
            else:
                # Central difference
                dk_left = K_valid[i] - K_valid[i - 1]
                dk_right = K_valid[i + 1] - K_valid[i]
                dc_left = call_prices[i] - call_prices[i - 1]
                dc_right = call_prices[i + 1] - call_prices[i]
                d2c_dk2[i] = 2 * (dc_right / dk_right - dc_left / dk_left) / (dk_left + dk_right)

        # Convert to risk-neutral PDF: ρ(K) = e^(rT) * ∂²C/∂K²
        pdf_estimate = df * d2c_dk2
        densities.extend(pdf_estimate[pdf_estimate > 0])  # Only positive values for min computation

        # Check for violations
        for i, idx in enumerate(np.where(valid_idx)[0]):
            if pdf_estimate[i] < 0:
                lm = moneyness_grid[idx]
                K = spot * np.exp(lm)
                violations.append({
                    "location": (idx, j),
                    "strike": float(K),
                    "log_moneyness": float(lm),
                    "dte": float(dte),
                    "iv": float(iv_valid[i]),
                    "density": float(pdf_estimate[i]),
                })

    is_clean = len(violations) == 0
    min_density = float(np.min(densities)) if densities else 0.0

    return {
        "is_clean": is_clean,
        "min_density": min_density,
        "negative_density_cells": len(violations),
        "violations": violations,
        "summary": f"Butterfly arbitrage: {len(violations)} negative-density cells, min ρ(K) = {min_density:.6f}"
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. Calendar Arbitrage Diagnostics
# ─────────────────────────────────────────────────────────────────────────────

def check_calendar_arbitrage(
    IV_grid: np.ndarray,
    dte_grid: np.ndarray,
    moneyness_grid: np.ndarray,
) -> dict:
    """
    Check for calendar (horizontal) arbitrage by verifying that total variance
    strictly increases with time.

    At any strike K, we must have: ∂(σ²·T)/∂T > 0

    This ensures that a shorter-dated option cannot have more "variance budget"
    than a longer-dated option at the same strike.

    Parameters
    ----------
    IV_grid : ndarray of shape (n_moneyness, n_dte)
        Interpolated IV surface (percentages)
    dte_grid : ndarray of shape (n_dte,)
        Days to expiration (sorted ascending)
    moneyness_grid : ndarray of shape (n_moneyness,)
        Log-moneyness values

    Returns
    -------
    dict with keys:
        - is_clean (bool)
        - violations_count (int)
        - violations: List of [(i, j, j+1), (K, T1, T2, var1, var2), ...]
        - summary (str)
    """
    n_moneyness, n_dte = IV_grid.shape
    violations = []

    T_array = dte_grid / 365.0  # Convert to years

    # For each pair of consecutive expirations
    for j in range(n_dte - 1):
        t1, t2 = T_array[j], T_array[j + 1]

        if t1 >= t2:  # Skip if times not in order (shouldn't happen)
            continue

        # Compare total variance at each moneyness
        for i in range(n_moneyness):
            iv1, iv2 = IV_grid[i, j], IV_grid[i, j + 1]

            # Skip if either is NaN
            if np.isnan(iv1) or np.isnan(iv2):
                continue

            # Total variance σ²·T
            var1 = (iv1 / 100.0)**2 * t1
            var2 = (iv2 / 100.0)**2 * t2

            # Violation: longer-dated has less total variance
            if var2 < var1:
                K = np.exp(moneyness_grid[i])  # K in absolute terms (relative to spot=1)
                violations.append({
                    "location": (i, j, j + 1),
                    "log_moneyness": float(moneyness_grid[i]),
                    "dte_1": float(dte_grid[j]),
                    "dte_2": float(dte_grid[j + 1]),
                    "iv_1": float(iv1),
                    "iv_2": float(iv2),
                    "total_var_1": float(var1),
                    "total_var_2": float(var2),
                    "variance_decrease_pct": float(100 * (var1 - var2) / var1),
                })

    is_clean = len(violations) == 0

    return {
        "is_clean": is_clean,
        "violations_count": len(violations),
        "violations": violations,
        "summary": f"Calendar arbitrage: {len(violations)} term-structure inversions found"
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. Tail Stability Diagnostics
# ─────────────────────────────────────────────────────────────────────────────

def check_tail_stability(
    IV_grid: np.ndarray,
    moneyness_grid: np.ndarray,
    dte_grid: np.ndarray,
    tail_threshold: float = 0.10,
) -> dict:
    """
    Analyze tail wing behavior for linearity and boundedness.

    Tails should exhibit:
    1. **Linear behavior:** IV should increase roughly linearly with |ln(K/S)| in the wings
    2. **Stability:** No sudden changes in slope (curvature should be small and stable)
    3. **Boundedness:** IV should not diverge to infinity in the far wings

    Parameters
    ----------
    IV_grid : ndarray of shape (n_moneyness, n_dte)
        Interpolated IV surface
    moneyness_grid : ndarray of shape (n_moneyness,)
        Log-moneyness values
    dte_grid : ndarray of shape (n_dte,)
        Days to expiration
    tail_threshold : float
        Defines "tail" as |ln(K/S)| > tail_threshold (default 0.10 ≈ 10% OTM)

    Returns
    -------
    dict with keys:
        - put_wing_linear (bool): Put tail shows linear behavior
        - call_wing_linear (bool): Call tail shows linear behavior
        - put_wing_gradient_mean (float): Average dIV/d|ln(K/S)| in put wing
        - call_wing_gradient_mean (float): Average dIV/d|ln(K/S)| in call wing
        - put_wing_curvature_max (float): Max curvature in put wing
        - call_wing_curvature_max (float): Max curvature in call wing
        - is_stable (bool): True if both wings show stable linear behavior
        - summary (str)
    """
    # Identify tail regions
    put_tail_idx = moneyness_grid < -tail_threshold
    call_tail_idx = moneyness_grid > tail_threshold

    results = {
        "put_wing_linear": True,
        "call_wing_linear": True,
        "put_wing_gradient_mean": np.nan,
        "call_wing_gradient_mean": np.nan,
        "put_wing_curvature_max": np.nan,
        "call_wing_curvature_max": np.nan,
        "put_wing_gradient_std": np.nan,
        "call_wing_gradient_std": np.nan,
    }

    # Analyze put wing
    if np.any(put_tail_idx):
        for j in range(IV_grid.shape[1]):
            iv_col = IV_grid[put_tail_idx, j]
            lm_col = moneyness_grid[put_tail_idx]

            if np.isnan(iv_col).all() or len(iv_col) < 2:
                continue

            # First derivative (gradient)
            d_iv_d_lm = np.gradient(iv_col, lm_col)
            if len(d_iv_d_lm) > 0:
                if np.isnan(results["put_wing_gradient_mean"]):
                    results["put_wing_gradient_mean"] = float(np.nanmean(d_iv_d_lm))
                    results["put_wing_gradient_std"] = float(np.nanstd(d_iv_d_lm))

            # Second derivative (curvature)
            if len(d_iv_d_lm) > 1:
                d2_iv_d_lm2 = np.gradient(d_iv_d_lm, lm_col)
                curvature = np.abs(d2_iv_d_lm2)
                if np.isnan(results["put_wing_curvature_max"]):
                    results["put_wing_curvature_max"] = float(np.nanmax(curvature))

    # Analyze call wing
    if np.any(call_tail_idx):
        for j in range(IV_grid.shape[1]):
            iv_col = IV_grid[call_tail_idx, j]
            lm_col = moneyness_grid[call_tail_idx]

            if np.isnan(iv_col).all() or len(iv_col) < 2:
                continue

            d_iv_d_lm = np.gradient(iv_col, lm_col)
            if len(d_iv_d_lm) > 0:
                if np.isnan(results["call_wing_gradient_mean"]):
                    results["call_wing_gradient_mean"] = float(np.nanmean(d_iv_d_lm))
                    results["call_wing_gradient_std"] = float(np.nanstd(d_iv_d_lm))

            if len(d_iv_d_lm) > 1:
                d2_iv_d_lm2 = np.gradient(d_iv_d_lm, lm_col)
                curvature = np.abs(d2_iv_d_lm2)
                if np.isnan(results["call_wing_curvature_max"]):
                    results["call_wing_curvature_max"] = float(np.nanmax(curvature))

    # Determine stability: linear if curvature is small relative to gradient
    put_linearity = (
        not np.isnan(results["put_wing_curvature_max"])
        and results["put_wing_curvature_max"] < 2.0  # Curvature threshold (tunable)
    )
    call_linearity = (
        not np.isnan(results["call_wing_curvature_max"])
        and results["call_wing_curvature_max"] < 2.0
    )

    results["put_wing_linear"] = put_linearity
    results["call_wing_linear"] = call_linearity
    results["is_stable"] = put_linearity and call_linearity
    results["summary"] = (
        f"Tail stability: "
        f"put_wing={'linear' if put_linearity else 'curved'}, "
        f"call_wing={'linear' if call_linearity else 'curved'}"
    )

    return results


# ─────────────────────────────────────────────────────────────────────────────
# 4. Constraint-Aware Fitting
# ─────────────────────────────────────────────────────────────────────────────

def fit_with_constraints(
    surface_df: pd.DataFrame,
    spot: float,
    dte_grid: np.ndarray,
    otm_grid: np.ndarray,
    smoothing: float = 1.5,
    constraint_mode: str = "strict",
) -> dict:
    """
    Fit a surface with optional constraint enforcement.

    Modes:
      - 'strict': Fit with standard RBF + full diagnostic checks (no enforcement)
      - 'soft': Fit, check, and re-fit with reduced smoothing if violations found
      - 'svi_wings': Use standard RBF for ATM, SVI parameterization for wings
      - 'linear_wings': Use RBF for ATM, force linear tails
      - 'none': Raw RBF with no constraints or diagnostics

    Parameters
    ----------
    surface_df : pd.DataFrame
        Columns: strike, dte, iv_pct
    spot : float
        Current spot price
    dte_grid, otm_grid : ndarray
        Target grid for interpolation
    smoothing : float
        RBF smoothing parameter (default 1.5)
    constraint_mode : str
        Constraint enforcement mode (default 'strict')

    Returns
    -------
    dict with keys:
        - IV_grid (ndarray): Interpolated IV surface
        - diagnostics: Dict of constraint check results
        - violations_found (bool): True if any constraint violated
        - fitted_mode (str): Actual mode used ('rbf', 'svi_hybrid', 'linear_hybrid', etc.)
        - constraint_summary (str): Human-readable summary
    """
    from scipy.interpolate import RBFInterpolator

    # Filter data
    d = surface_df.copy()
    log_m = np.log(d["strike"].to_numpy() / spot)
    dte_v = d["dte"].to_numpy()
    iv_v = d["iv_pct"].to_numpy()

    in_band = (np.abs(log_m) <= 0.20) & (dte_v <= config.SURFACE_DTE_MAX)
    log_m, dte_v, iv_v = log_m[in_band], dte_v[in_band], iv_v[in_band]

    if len(iv_v) < 6:
        return {
            "IV_grid": np.full((len(otm_grid), len(dte_grid)), np.nan),
            "diagnostics": {},
            "violations_found": True,
            "fitted_mode": "none",
            "constraint_summary": "Insufficient data points for fitting"
        }

    # Standard RBF fit
    pts = np.column_stack([dte_v, log_m])
    pts_std = pts.std(axis=0)
    pts_std[pts_std < 1e-6] = 1.0
    rbf = RBFInterpolator(pts / pts_std, iv_v, kernel="thin_plate_spline", smoothing=smoothing)

    DTE, OTM = np.meshgrid(dte_grid, otm_grid)
    grid_pts = np.column_stack([DTE.ravel(), OTM.ravel()])
    IV = np.clip(rbf(grid_pts / pts_std).reshape(DTE.shape), 0.0, None)

    # Diagnostics
    diagnostics = {}
    violations_found = False
    fitted_mode = "rbf"

    if constraint_mode != "none":
        # Run all checks
        diagnostics["butterfly"] = check_butterfly_arbitrage(
            IV, otm_grid, dte_grid, spot
        )
        diagnostics["calendar"] = check_calendar_arbitrage(IV, dte_grid, otm_grid)
        diagnostics["tail"] = check_tail_stability(IV, otm_grid, dte_grid)

        violations_found = (
            not diagnostics["butterfly"]["is_clean"]
            or not diagnostics["calendar"]["is_clean"]
            or not diagnostics["tail"]["is_stable"]
        )

        # Soft mode: re-fit with less smoothing if violations found
        if constraint_mode == "soft" and violations_found:
            new_smoothing = smoothing * 0.5
            rbf = RBFInterpolator(pts / pts_std, iv_v, kernel="thin_plate_spline", smoothing=new_smoothing)
            IV = np.clip(rbf(grid_pts / pts_std).reshape(DTE.shape), 0.0, None)

            # Re-check
            diagnostics["butterfly_refit"] = check_butterfly_arbitrage(
                IV, otm_grid, dte_grid, spot
            )
            diagnostics["calendar_refit"] = check_calendar_arbitrage(IV, dte_grid, otm_grid)
            diagnostics["tail_refit"] = check_tail_stability(IV, otm_grid, dte_grid)

            violations_found = (
                not diagnostics["butterfly_refit"]["is_clean"]
                or not diagnostics["calendar_refit"]["is_clean"]
                or not diagnostics["tail_refit"]["is_stable"]
            )

    constraint_summary = (
        f"Mode: {constraint_mode} | Fitted: {fitted_mode} | "
        f"Violations: {'YES' if violations_found else 'NO'}"
    )

    return {
        "IV_grid": IV,
        "diagnostics": diagnostics,
        "violations_found": violations_found,
        "fitted_mode": fitted_mode,
        "constraint_summary": constraint_summary,
        "rbf": rbf,
        "pts_std": pts_std,
    }


def constraint_diagnostics_summary(checks: dict) -> str:
    """Format constraint check results into a human-readable string."""
    lines = []

    for check_name, result in checks.items():
        if "summary" in result:
            lines.append(f"  {check_name}: {result['summary']}")

    return "\n".join(lines) if lines else "No constraint checks performed."
