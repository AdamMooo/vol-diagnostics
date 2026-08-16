"""
Second-order Greeks: Vanna and Volga for volatility surface deformation tracking.

These are essential for understanding how the surface responds to simultaneous
spot and volatility shocks — critical for monitoring surface stability during
market dislocations.

Public API
----------
compute_vanna(spot, strike, dte, iv_pct, rate) -> float
    ∂²C/∂S∂σ: How delta changes with volatility (gamma-vega convexity).
    Units: delta points per 1% IV change.

compute_volga(spot, strike, dte, iv_pct, rate) -> float
    ∂²C/∂σ²: How vega changes with volatility (vega convexity).
    Units: vega points per 1% IV change.

vanna_profile(spot, strikes, dte, ivs, rate) -> ndarray
    Vectorized vanna computation across a strike array.

volga_profile(spot, strikes, dte, ivs, rate) -> ndarray
    Vectorized volga computation across a strike array.

estimate_surface_deformation(IV_grid, strike_grid, dte_grid, spot, rate) -> dict
    Comprehensive second-order sensitivity analysis of the vol surface.
    Returns: vanna map, volga map, spot-gamma interactions, vol-of-vol metrics.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import norm

from engine import config


# ─────────────────────────────────────────────────────────────────────────────
# Black-Scholes Greeks Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _bs_d1_d2(S: float | np.ndarray, K: float | np.ndarray, T: float,
              r: float, sigma: float) -> tuple:
    """Compute d1 and d2 for Black-Scholes."""
    sigma = np.maximum(sigma, 0.0001)  # Floor to avoid divide-by-zero
    T = np.maximum(T, 1.0 / 365.0)
    sqrt_T = np.sqrt(T)
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T
    return d1, d2


def _bs_call_price(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Black-Scholes call option price."""
    d1, d2 = _bs_d1_d2(S, K, T, r, sigma)
    return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)


def _bs_delta(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Call delta: ∂C/∂S."""
    d1, _ = _bs_d1_d2(S, K, T, r, sigma)
    return norm.cdf(d1)


def _bs_vega(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Call vega (per 1% IV change): ∂C/∂σ / 100."""
    d1, _ = _bs_d1_d2(S, K, T, r, sigma)
    return S * norm.pdf(d1) * np.sqrt(T) / 100.0


# ─────────────────────────────────────────────────────────────────────────────
# Vanna: ∂²C/∂S∂σ
# ─────────────────────────────────────────────────────────────────────────────

def compute_vanna(spot: float, strike: float, dte: float, iv_pct: float,
                  rate: float = 0.05) -> float:
    """
    Vanna = ∂²C/∂S∂σ: The cross-gamma of delta w.r.t. volatility.

    **Intuition:** How much delta changes when volatility shifts.
    - Positive vanna: Higher vol → higher delta (long gamma exposure moves into higher delta)
    - Negative vanna: Higher vol → lower delta (short gamma exposure moves into lower delta)

    **Practical use:** Track vanna to understand position sensitivity to vol-spot correlation shocks.

    **Formula (Black-Scholes):**
        vanna = -S * PDF(d1) * d2 / σ
        where d1, d2 are BS parameters, PDF is the standard normal PDF

    Units: delta change per 1% IV move (e.g., +0.05 means delta increases by 0.05 if IV rises by 1%)

    Parameters
    ----------
    spot : float
        Current spot price
    strike : float
        Strike price
    dte : float
        Days to expiration
    iv_pct : float
        Implied volatility (e.g., 20.5 for 20.5%)
    rate : float
        Risk-free rate (annualized, default 0.05)

    Returns
    -------
    float
        Vanna in delta points per 1% IV change
    """
    T = max(dte / 365.0, 1.0 / 365.0)
    sigma = max(iv_pct / 100.0, 0.0001)

    d1, d2 = _bs_d1_d2(spot, strike, T, rate, sigma)

    # vanna = -PDF(d1) * d2 / sigma (per 1% vol change: divide by 100)
    vanna = -norm.pdf(d1) * d2 / sigma / 100.0

    return float(vanna)


def vanna_profile(spot: float, strikes: np.ndarray, dte: float, ivs: np.ndarray,
                  rate: float = 0.05) -> np.ndarray:
    """Vectorized vanna across a strike array."""
    T = max(dte / 365.0, 1.0 / 365.0)
    sigmas = np.maximum(ivs / 100.0, 0.0001)

    d1, d2 = _bs_d1_d2(spot, strikes, T, rate, sigmas)
    vanna = -norm.pdf(d1) * d2 / sigmas / 100.0

    return vanna


# ─────────────────────────────────────────────────────────────────────────────
# Volga (Vegaomka): ∂²C/∂σ²
# ─────────────────────────────────────────────────────────────────────────────

def compute_volga(spot: float, strike: float, dte: float, iv_pct: float,
                  rate: float = 0.05) -> float:
    """
    Volga = ∂²C/∂σ²: The convexity of vega w.r.t. volatility.

    Also known as "vegaomka" or "vega gamma" — measures how vega changes as volatility changes.

    **Intuition:** The curvature of the vega surface.
    - Positive volga: Long vega (higher IV → more vega premium)
    - Negative volga: Short vega (higher IV → less vega premium)

    **Practical use:** Essential for vol-of-vol hedging; traders use volga to size vol straddles.

    **Formula (Black-Scholes):**
        volga = vega * (d1 * d2 / σ)
              = S * PDF(d1) * √T * (d1 * d2 / σ)

    Units: vega change per 1% IV move squared (per 1pp of IV vol)

    Parameters
    ----------
    spot : float
        Current spot price
    strike : float
        Strike price
    dte : float
        Days to expiration
    iv_pct : float
        Implied volatility (e.g., 20.5 for 20.5%)
    rate : float
        Risk-free rate (annualized, default 0.05)

    Returns
    -------
    float
        Volga in vega points per 1pp IV vol
    """
    T = max(dte / 365.0, 1.0 / 365.0)
    sigma = max(iv_pct / 100.0, 0.0001)

    d1, d2 = _bs_d1_d2(spot, strike, T, rate, sigma)

    # volga = vega * (d1 * d2 / sigma)
    # vega is per 1% change, so divide by 100
    vega = spot * norm.pdf(d1) * np.sqrt(T) / 100.0
    volga = vega * d1 * d2 / sigma

    return float(volga)


def volga_profile(spot: float, strikes: np.ndarray, dte: float, ivs: np.ndarray,
                  rate: float = 0.05) -> np.ndarray:
    """Vectorized volga across a strike array."""
    T = max(dte / 365.0, 1.0 / 365.0)
    sigmas = np.maximum(ivs / 100.0, 0.0001)

    d1, d2 = _bs_d1_d2(spot, strikes, T, rate, sigmas)

    vega = spot * norm.pdf(d1) * np.sqrt(T) / 100.0
    volga = vega * d1 * d2 / sigmas

    return volga


# ─────────────────────────────────────────────────────────────────────────────
# Surface Deformation Analysis
# ─────────────────────────────────────────────────────────────────────────────

def estimate_surface_deformation(
    IV_grid: np.ndarray,
    moneyness_grid: np.ndarray,
    dte_grid: np.ndarray,
    spot: float,
    rate: float = 0.05,
) -> dict:
    """
    Comprehensive second-order sensitivity analysis of the vol surface.

    Computes vanna and volga grids to understand how the surface deforms under
    spot and volatility shocks. Useful for:
    1. **Spot-vol correlation tracking:** Monitor vanna to understand if the market
       prices in spot-vol correlation (typical for equities: higher spot → lower vol).
    2. **Vol-of-vol hedging:** Monitor volga to size vol straddles.
    3. **Surface stability:** Detect regions where the surface is unstable (high curvature).

    Parameters
    ----------
    IV_grid : ndarray of shape (n_moneyness, n_dte)
        Interpolated IV surface (percentages)
    moneyness_grid : ndarray of shape (n_moneyness,)
        Log-moneyness ln(K/S)
    dte_grid : ndarray of shape (n_dte,)
        Days to expiration
    spot : float
        Current spot price
    rate : float
        Risk-free rate (annualized)

    Returns
    -------
    dict with keys:
        - vanna_grid (ndarray): Vanna surface (delta change per 1% IV)
        - volga_grid (ndarray): Volga surface (vega convexity)
        - vanna_summary: {mean, std, min, max} across valid grid
        - volga_summary: {mean, std, min, max} across valid grid
        - spot_vol_correlation_signal (float): Mean vanna (negative = typical inverse relationship)
        - vol_of_vol_magnitude (float): Mean |volga| (higher = market prices vol-of-vol risk)
        - surface_stability_metric (float): RMS curvature of the surface
        - deformation_summary (str): Qualitative assessment
    """
    n_moneyness, n_dte = IV_grid.shape
    vanna_grid = np.full_like(IV_grid, np.nan)
    volga_grid = np.full_like(IV_grid, np.nan)

    for j in range(n_dte):
        dte = dte_grid[j]
        iv_row = IV_grid[:, j]

        for i in range(n_moneyness):
            if np.isnan(iv_row[i]):
                continue

            strike = spot * np.exp(moneyness_grid[i])
            vanna_grid[i, j] = compute_vanna(spot, strike, dte, iv_row[i], rate)
            volga_grid[i, j] = compute_volga(spot, strike, dte, iv_row[i], rate)

    # Summaries
    vanna_valid = vanna_grid[~np.isnan(vanna_grid)]
    volga_valid = volga_grid[~np.isnan(volga_grid)]

    vanna_summary = {
        "mean": float(np.mean(vanna_valid)) if len(vanna_valid) > 0 else np.nan,
        "std": float(np.std(vanna_valid)) if len(vanna_valid) > 0 else np.nan,
        "min": float(np.min(vanna_valid)) if len(vanna_valid) > 0 else np.nan,
        "max": float(np.max(vanna_valid)) if len(vanna_valid) > 0 else np.nan,
    }

    volga_summary = {
        "mean": float(np.mean(volga_valid)) if len(volga_valid) > 0 else np.nan,
        "std": float(np.std(volga_valid)) if len(volga_valid) > 0 else np.nan,
        "min": float(np.min(volga_valid)) if len(volga_valid) > 0 else np.nan,
        "max": float(np.max(volga_valid)) if len(volga_valid) > 0 else np.nan,
    }

    # Spot-vol correlation signal (negative vanna = typical inverse relationship)
    spot_vol_corr = vanna_summary["mean"]

    # Vol-of-vol magnitude (higher = market prices volatility risk)
    vol_of_vol_mag = np.mean(np.abs(volga_valid)) if len(volga_valid) > 0 else 0.0

    # Surface stability: RMS curvature
    iv_grad = np.gradient(IV_grid, axis=1)  # Gradient along DTE
    curvature = np.gradient(iv_grad, axis=1)  # Second derivative
    stability_metric = float(np.sqrt(np.nanmean(curvature**2)))

    # Qualitative assessment
    deformation_summary = ""
    if spot_vol_corr < -0.02:
        deformation_summary += "Strong inverse spot-vol correlation (typical). "
    elif spot_vol_corr > 0.02:
        deformation_summary += "Unusual positive spot-vol correlation (watch for stress). "

    if vol_of_vol_mag > 0.5:
        deformation_summary += "High vol-of-vol pricing; market is hedging volatility risk. "
    elif vol_of_vol_mag < 0.1:
        deformation_summary += "Low vol-of-vol pricing; complacency or low realized vol. "

    if stability_metric > 1.0:
        deformation_summary += "Surface shows high curvature; watch for instability."

    if not deformation_summary:
        deformation_summary = "Normal surface deformation profile."

    return {
        "vanna_grid": vanna_grid,
        "volga_grid": volga_grid,
        "vanna_summary": vanna_summary,
        "volga_summary": volga_summary,
        "spot_vol_correlation_signal": float(spot_vol_corr),
        "vol_of_vol_magnitude": float(vol_of_vol_mag),
        "surface_stability_metric": stability_metric,
        "deformation_summary": deformation_summary,
    }
