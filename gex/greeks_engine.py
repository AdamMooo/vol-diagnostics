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


T_MIN = 1.0 / 365.0


def bs_vanna(spot: float | np.ndarray, strike: float | np.ndarray,
             iv: float | np.ndarray, T: float | np.ndarray,
             r: float = 0.05) -> float | np.ndarray:
    # Vanna = N'(d1) * (d2 / sigma)  [q=0 simplification for equity indices]
    # Unsigned — sign convention (calls positive, puts negative) applied in Phase 2 compute_vex()
    # Returns 0 where T <= 0 or iv <= 0.
    strike = np.asarray(strike, dtype=float)
    iv = np.broadcast_to(np.asarray(iv, dtype=float), strike.shape).copy()
    T = np.broadcast_to(np.asarray(T, dtype=float), strike.shape).copy()
    spot = np.broadcast_to(np.asarray(spot, dtype=float), strike.shape).copy()

    valid = (T > 0) & (iv > 0) & (strike > 0) & (spot > 0)
    vanna = np.zeros(strike.shape, dtype=float)

    s, k, v, t = spot[valid], strike[valid], iv[valid], T[valid]
    d1 = (np.log(s / k) + (r + 0.5 * v**2) * t) / (v * np.sqrt(t))
    d2 = d1 - v * np.sqrt(t)
    vanna[valid] = norm.pdf(d1) * (d2 / v)

    return vanna if vanna.ndim > 0 else float(vanna)


def bs_charm(spot: float | np.ndarray, strike: float | np.ndarray,
             iv: float | np.ndarray, T: float | np.ndarray,
             r: float = 0.05) -> float | np.ndarray:
    # Charm = ∂Δ/∂t  [delta decay over time]
    # Formula (q=0): -N'(d1) * (2*r*T - d2*sigma*sqrt(T)) / (2*T*sigma*sqrt(T))
    # T_MIN guard: rows where original T < 1/365 return 0.0 (delta locked at expiration).
    # Returns 0 where T <= 0 or iv <= 0.
    strike = np.asarray(strike, dtype=float)
    iv = np.broadcast_to(np.asarray(iv, dtype=float), strike.shape).copy()
    T = np.broadcast_to(np.asarray(T, dtype=float), strike.shape).copy()
    spot = np.broadcast_to(np.asarray(spot, dtype=float), strike.shape).copy()

    valid = (T > 0) & (iv > 0) & (strike > 0) & (spot > 0)
    charm = np.zeros(strike.shape, dtype=float)

    s, k, v, t = spot[valid], strike[valid], iv[valid], T[valid]

    t_guarded = np.maximum(t, T_MIN)
    d1 = (np.log(s / k) + (r + 0.5 * v**2) * t_guarded) / (v * np.sqrt(t_guarded))
    d2 = d1 - v * np.sqrt(t_guarded)

    numerator = 2 * r * t_guarded - d2 * v * np.sqrt(t_guarded)
    denominator = 2 * t_guarded * v * np.sqrt(t_guarded)
    charm[valid] = -norm.pdf(d1) * (numerator / denominator)

    # Explicit zero for rows where original T was below T_MIN
    too_close = t < T_MIN
    charm_valid = charm[valid]
    charm_valid[too_close] = 0.0
    charm[valid] = charm_valid

    return charm if charm.ndim > 0 else float(charm)


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

    df["vanna"] = bs_vanna(
        spot=spot,
        strike=df["strike"].to_numpy(),
        iv=df["iv"].to_numpy(),
        T=df["T_years"].to_numpy(),
        r=r,
    )
    df["charm"] = bs_charm(
        spot=spot,
        strike=df["strike"].to_numpy(),
        iv=df["iv"].to_numpy(),
        T=df["T_years"].to_numpy(),
        r=r,
    )
    return df
