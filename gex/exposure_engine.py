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


def oi_vol_surface_data(df: pd.DataFrame, spot: float,
                        dte_max: int = 180,
                        moneyness_band: float = 0.18) -> pd.DataFrame:
    """
    Extract (dte, strike, iv_pct) points for vol surface interpolation.

    Weighting: OI × vega at each (expiry, strike) pair — combines calls and puts.
    Avellaneda et al. (2020, arXiv 2002.00085) shows OI×vega weighting is the
    empirically-supported choice for vol surface aggregation.

    Filtered to the liquid near-money region (±18% of spot, ≤180 DTE).
    Returns DataFrame: dte (days), strike, iv_pct (IV as %).
    """
    lo = spot * (1 - moneyness_band)
    hi = spot * (1 + moneyness_band)
    valid = df[
        (df["T_years"] > 0) &
        (df["iv"] > 0) &
        (df["vega"] > 0) &
        (df["oi"] > 0) &
        (df["strike"] >= lo) &
        (df["strike"] <= hi)
    ].copy()
    valid["dte"] = valid["T_years"] * 365
    valid = valid[valid["dte"] <= dte_max].copy()
    valid["weight"] = valid["oi"] * valid["vega"]
    valid["wiv"] = valid["weight"] * valid["iv"]

    agg = (
        valid.groupby(["expiry", "strike"])
        .agg(
            dte=pd.NamedAgg(column="dte", aggfunc="first"),
            weight_sum=pd.NamedAgg(column="weight", aggfunc="sum"),
            wiv_sum=pd.NamedAgg(column="wiv", aggfunc="sum"),
        )
        .reset_index()
    )
    agg = agg[agg["weight_sum"] > 0].copy()
    agg["iv_pct"] = agg["wiv_sum"] / agg["weight_sum"] * 100
    return (
        agg[["dte", "strike", "iv_pct"]]
        .dropna()
        .sort_values("dte")
        .reset_index(drop=True)
    )


def compute_skew(df: pd.DataFrame, min_dte: int = 7) -> pd.DataFrame:
    """
    Per-expiry IV skew: IV(25Δ put) − IV(50Δ call), in percentage points.

    Uses delta-based selection (CBOE-supplied). Front-month defined as nearest
    expiry with DTE >= min_dte to avoid expiry-day gamma noise.

    Methodology: Xing, Zhang & Zhao (2010, JFQA) — steeper skew predicts
    subsequent underperformance (10.9% annual alpha).

    Returns DataFrame: expiry, dte, put_25d_iv, call_50d_iv, skew_pp.
    """
    valid = df[(df["T_years"] > 0) & (df["iv"] > 0) & (df["oi"] > 0)].copy()
    valid["dte"] = valid["T_years"] * 365

    rows = []
    for expiry, grp in valid.groupby("expiry"):
        dte = grp["dte"].iloc[0]
        if dte < min_dte:
            continue
        puts = grp[grp["type"] == "put"]
        calls = grp[grp["type"] == "call"]
        if puts.empty or calls.empty:
            continue
        put_idx = (puts["delta"] - (-0.25)).abs().idxmin()
        call_idx = (calls["delta"] - 0.50).abs().idxmin()
        put_iv = puts.loc[put_idx, "iv"] * 100
        call_iv = calls.loc[call_idx, "iv"] * 100
        rows.append({
            "expiry": expiry,
            "dte": dte,
            "put_25d_iv": put_iv,
            "call_50d_iv": call_iv,
            "skew_pp": put_iv - call_iv,
        })

    return pd.DataFrame(rows).sort_values("dte").reset_index(drop=True)


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
