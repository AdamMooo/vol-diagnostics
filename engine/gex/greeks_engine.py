"""
Greeks computation for US equity options (American-style).

Gamma, delta, vega, theta: taken directly from CBOE's delayed quotes.
CBOE computes these using their own American option model (accounts for
early exercise and dividend yield) — more accurate than Black-Scholes
European approximation, especially for single-name equity options.

Only gamma is currently surfaced downstream — delta/vega/theta pass through
the chain df unchanged for any future use, but no greeks are computed locally.

`bs_gamma` below is used only by `gamma_profile()` when sweeping spot across
a hypothetical grid (CBOE's gamma is fixed at the live spot).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm


T_MIN = 1.0 / 365.0


def bs_gamma(spot: float | np.ndarray, strike: float | np.ndarray,
             iv: float | np.ndarray, T: float | np.ndarray,
             r: float = 0.05) -> float | np.ndarray:
    """
    Returns gamma per share (identical for calls and puts under BS).

    T:  time to expiry in years
    r:  continuously compounded risk-free rate
    iv: annualized implied volatility (0.20 = 20%)

    Returns 0 where T <= 0 or iv <= 0. Applies T_MIN floor (1/365) to prevent
    singularity at ATM as T → 0 — used by gamma_profile() when sweeping spot
    across an option grid that may contain very-near-expiry options.
    """
    strike = np.asarray(strike, dtype=float)
    iv = np.asarray(iv, dtype=float)
    T = np.asarray(T, dtype=float)
    spot = np.broadcast_to(np.asarray(spot, dtype=float), strike.shape).copy()

    valid = (T > 0) & (iv > 0) & (strike > 0) & (spot > 0)
    gamma = np.zeros(strike.shape, dtype=float)

    s, k, v, t = spot[valid], strike[valid], iv[valid], T[valid]
    t_guarded = np.maximum(t, T_MIN)
    d1 = (np.log(s / k) + (r + 0.5 * v**2) * t_guarded) / (v * np.sqrt(t_guarded))
    gamma[valid] = norm.pdf(d1) / (s * v * np.sqrt(t_guarded))

    return gamma if gamma.ndim > 0 else float(gamma)


def add_greeks(df: pd.DataFrame, spot: float, today=None,
               r: float = 0.05) -> pd.DataFrame:
    """
    Add T_years column. Gamma already lives on the chain df (from CBOE);
    nothing else is computed locally.
    """
    import datetime
    if today is None:
        today = datetime.date.today()

    df = df.copy()
    df["T_years"] = (pd.to_datetime(df["expiry"]) - pd.Timestamp(today)).dt.days / 365.0
    return df
