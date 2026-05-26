"""
Pure vol metrics computation functions for the institutional diagnostics pipeline.
No side effects, no I/O, no Streamlit calls.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from gex import config


def compute_skew_25d(df: pd.DataFrame, spot: float) -> dict:
    """
    Per-expiry 25Δ skew bucketed into front_month (≤45 DTE) and second_month (46–90 DTE).

    Returns:
        {
            "front_month": {"put_iv": float, "call_iv": float, "skew": float, "dte": float} | None,
            "second_month": {"put_iv": float, "call_iv": float, "skew": float, "dte": float} | None,
        }

    Selection rules:
        - put_iv: iv of the put whose delta is closest to config.SKEW_PUT_DELTA (-0.25)
        - call_iv: iv of the call whose delta is closest to 0.25 (25Δ call, NOT 50Δ)
        - Returns None for a bucket if fewer than 2 puts or 2 calls qualify, or no expiry in range
    """
    valid = df[(df["T_years"] > 0) & (df["iv"] > 0) & (df["oi"] > 0)].copy()
    valid["dte"] = valid["T_years"] * 365

    result: dict = {"front_month": None, "second_month": None}

    for expiry, grp in valid.groupby("expiry"):
        dte = grp["dte"].iloc[0]

        if dte <= 45:
            bucket = "front_month"
        elif dte <= 90:
            bucket = "second_month"
        else:
            continue

        # only fill first qualifying expiry per bucket
        if result[bucket] is not None:
            continue

        puts = grp[(grp["type"] == "put") & (grp["strike"] < spot)]
        calls = grp[(grp["type"] == "call") & (grp["strike"] >= spot)]

        if len(puts) < 2 or len(calls) < 2:
            result[bucket] = None
            continue

        put_idx = (puts["delta"] - config.SKEW_PUT_DELTA).abs().idxmin()
        call_idx = (calls["delta"] - 0.25).abs().idxmin()

        put_iv = float(puts.loc[put_idx, "iv"] * 100)
        call_iv = float(calls.loc[call_idx, "iv"] * 100)

        result[bucket] = {
            "put_iv": put_iv,
            "call_iv": call_iv,
            "skew": put_iv - call_iv,
            "dte": float(dte),
        }

    return result


def compute_term_structure(df: pd.DataFrame, spot: float) -> dict:
    """
    Build the IV term structure from ATM options and classify the curve shape.

    ATM selection per expiry: OTM call nearest to spot preferred; falls back to put.

    Classification (applied in order):
        flat     — max_iv - min_iv < 1.0 * (max_dte - min_dte) / 30
        humped   — middle-third average ATM IV > both front-third and back-third averages
        inverted — back IV < front IV (negative total slope)
        normal   — otherwise

    Returns:
        {
            "points": [{"dte": float, "atm_iv": float}, ...],
            "classification": str,
            "front_atm_iv": float | None,
            "back_atm_iv": float | None,
        }
    """
    valid = df[(df["T_years"] > 0) & (df["iv"] > 0) & (df["oi"] > 0)].copy()
    valid["dte"] = valid["T_years"] * 365

    points = []
    for expiry, grp in valid.groupby("expiry"):
        dte = float(grp["dte"].iloc[0])
        calls = grp[grp["type"] == "call"]
        candidates = calls if not calls.empty else grp[grp["type"] == "put"]
        if candidates.empty:
            continue
        atm_idx = (candidates["strike"] - spot).abs().idxmin()
        atm_iv = float(candidates.loc[atm_idx, "iv"] * 100)
        points.append({"dte": dte, "atm_iv": atm_iv})

    points.sort(key=lambda p: p["dte"])

    front_atm_iv = points[0]["atm_iv"] if points else None
    back_atm_iv = points[-1]["atm_iv"] if points else None

    classification = _classify_term_structure(points)

    return {
        "points": points,
        "classification": classification,
        "front_atm_iv": front_atm_iv,
        "back_atm_iv": back_atm_iv,
    }


def _classify_term_structure(points: list[dict]) -> str:
    if len(points) < 2:
        return "normal"

    ivs = [p["atm_iv"] for p in points]
    dtes = [p["dte"] for p in points]

    max_iv = max(ivs)
    min_iv = min(ivs)
    max_dte = max(dtes)
    min_dte = min(dtes)
    dte_range = max_dte - min_dte

    # flat: total IV range less than 1 vol point per 30 DTE
    if dte_range > 0 and (max_iv - min_iv) < 1.0 * dte_range / 30:
        return "flat"
    if dte_range == 0:
        return "flat"

    front_iv = ivs[0]
    back_iv = ivs[-1]

    # humped: middle-third average > both ends
    if len(points) >= 3:
        n = len(points)
        third = max(1, n // 3)
        front_avg = sum(ivs[:third]) / third
        back_avg = sum(ivs[n - third:]) / (n - (n - third))
        mid_avg = sum(ivs[third: n - third]) / max(1, len(ivs[third: n - third]))
        if mid_avg > front_avg and mid_avg > back_avg:
            return "humped"

    # inverted: back < front
    if back_iv < front_iv:
        return "inverted"

    return "normal"


def compute_rv20(spot_history: pd.Series) -> float | None:
    """
    20-day realized volatility, annualized.

    Expects spot_history sorted oldest-first (ascending date). Does not sort internally.
    Returns None when fewer than 21 prices are available (need 21 prices for 20 returns).

    Formula: annualized std of log returns, ddof=1, over the most recent 20 returns.
    """
    if len(spot_history) < 21:
        return None

    prices = spot_history.iloc[-21:].to_numpy(dtype=float)
    log_returns = np.log(prices[1:] / prices[:-1])
    return float(np.sqrt(252) * log_returns.std(ddof=1))


def compute_vrp(iv30: float | None, rv20: float | None) -> float | None:
    """
    Volatility risk premium: iv30 - rv20.

    Returns None if either input is None.
    """
    if iv30 is None or rv20 is None:
        return None
    return iv30 - rv20
