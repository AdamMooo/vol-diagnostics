"""
Compute Gamma Exposure (GEX) from a greeks-enriched chains DataFrame.

Convention (SpotGamma/retail standard):
    GEX_per_option = gamma * OI * multiplier * spot^2 * 0.01

    Calls contribute positive GEX, puts negative.
    Positive net GEX = dealers net long gamma (stabilising: sell rallies, buy dips).
    Negative net GEX = dealers net short gamma (destabilising: accelerates moves).

Assumptions baked in:
    - Retail buys options, dealers sell them (dealer short net = retail long net).
    - Standard US equity multiplier = 100 shares/contract.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

MULTIPLIER = 100  # shares per contract


def compute_gex(df: pd.DataFrame, spot: float) -> pd.DataFrame:
    """
    Add gex column to a greeks-enriched DataFrame.
    Returns a copy.
    """
    df = df.copy()
    sign = np.where(df["type"] == "call", 1.0, -1.0)
    df["gex"] = sign * df["gamma"] * df["oi"] * MULTIPLIER * spot**2 * 0.01
    return df


def strike_gex(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate GEX by strike (sum across all expiries and sides)."""
    return (
        df.groupby("strike")["gex"]
        .sum()
        .reset_index()
        .sort_values("strike")
        .reset_index(drop=True)
    )


def expiry_gex(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate GEX by expiry."""
    return (
        df.groupby("expiry")["gex"]
        .sum()
        .reset_index()
        .sort_values("expiry")
        .reset_index(drop=True)
    )


def gamma_profile(df: pd.DataFrame, spot: float,
                  n_points: int = 200, width_pct: float = 0.15,
                  r: float = 0.05) -> pd.DataFrame:
    """
    Recompute net GEX across a grid of hypothetical spot levels.
    Used to find the zero-gamma level and visualise the profile.

    Returns DataFrame with columns: spot_level, net_gex.
    """
    from gex.greeks_engine import bs_gamma

    lo = spot * (1 - width_pct)
    hi = spot * (1 + width_pct)
    spot_grid = np.linspace(lo, hi, n_points)

    net_gex = np.zeros(n_points)
    for i, s in enumerate(spot_grid):
        gamma = bs_gamma(s, df["strike"].to_numpy(), df["iv"].to_numpy(),
                         df["T_years"].to_numpy(), r=r)
        sign = np.where(df["type"] == "call", 1.0, -1.0)
        net_gex[i] = (sign * gamma * df["oi"].to_numpy() * MULTIPLIER * s**2 * 0.01).sum()

    return pd.DataFrame({"spot_level": spot_grid, "net_gex": net_gex})
