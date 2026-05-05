"""
Black-Scholes gamma calculation.

Gamma = N'(d1) / (S * sigma * sqrt(T))
where d1 = (ln(S/K) + (r + sigma^2/2)*T) / (sigma*sqrt(T))

N'(d1) is the standard normal PDF.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm


def bs_gamma(spot: float | np.ndarray, strike: float | np.ndarray,
             iv: float | np.ndarray, T: float | np.ndarray,
             r: float = 0.05) -> float | np.ndarray:
    """
    Returns gamma per share (identical for calls and puts under BS).

    T:  time to expiry in years
    r:  continuously compounded risk-free rate
    iv: annualized implied volatility (0.20 = 20%)

    Returns 0 where T <= 0 or iv <= 0.
    """
    strike = np.asarray(strike, dtype=float)
    iv = np.asarray(iv, dtype=float)
    T = np.asarray(T, dtype=float)
    spot = np.broadcast_to(np.asarray(spot, dtype=float), strike.shape).copy()

    valid = (T > 0) & (iv > 0) & (strike > 0) & (spot > 0)
    gamma = np.zeros(strike.shape, dtype=float)

    s, k, v, t = spot[valid], strike[valid], iv[valid], T[valid]
    d1 = (np.log(s / k) + (r + 0.5 * v**2) * t) / (v * np.sqrt(t))
    gamma[valid] = norm.pdf(d1) / (s * v * np.sqrt(t))

    return gamma if gamma.ndim > 0 else float(gamma)


def add_greeks(df: pd.DataFrame, spot: float, today=None,
               r: float = 0.05) -> pd.DataFrame:
    """
    Vectorised: add T_years and gamma columns to a chains DataFrame.
    Modifies a copy and returns it.
    """
    import datetime
    if today is None:
        today = datetime.date.today()

    df = df.copy()
    df["T_years"] = (pd.to_datetime(df["expiry"]) - pd.Timestamp(today)).dt.days / 365.0
    df["gamma"] = bs_gamma(
        spot=spot,
        strike=df["strike"].to_numpy(),
        iv=df["iv"].to_numpy(),
        T=df["T_years"].to_numpy(),
        r=r,
    )
    return df
