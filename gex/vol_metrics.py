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
        calls = grp[(grp["type"] == "call") & (grp["strike"] >= spot)]
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
    if np.any(np.isnan(prices)) or np.any(prices <= 0):
        return None
    log_returns = np.log(prices[1:] / prices[:-1])
    return float(np.sqrt(252) * log_returns.std(ddof=1))


def compute_vrp(iv30: float | None, rv20: float | None) -> float | None:
    """
    Volatility risk premium: iv30 - rv20.

    Both arguments must be decimal fractions (e.g., 0.18 for 18% vol, not 18.0).
    The caller is responsible for normalising iv30 from percentage to decimal before
    calling this function.

    Returns None if either input is None.
    Result is in decimal fraction units (e.g., 0.022 for ~2.2 vol points).
    """
    if iv30 is None or rv20 is None:
        return None
    return iv30 - rv20


# ── Phase 11 email plug-in points (D-15) ─────────────────────────────────────
# Pure functions — no I/O, no Streamlit calls, plain Python return types.


def vrp_headline(
    iv30_pct: float | None,
    rv20_pct: float | None,
    vrp_pp: float | None,
    percentile: int | None,
) -> str:
    """Plain-read VRP string for dashboard and Phase 11 email.

    Args:
        iv30_pct: IV30 as percentage points (e.g. 18.5 for 18.5% vol)
        rv20_pct: RV20 as percentage points (e.g. 15.8)
        vrp_pp:   IV30 − RV20 in percentage points (e.g. 2.7)
        percentile: historical percentile of VRP vs 30-session lookback (0–100)

    Returns:
        Plain-language read. Cold-start string when vrp_pp or percentile is None.
    """
    if vrp_pp is None or percentile is None:
        return "VRP: insufficient history (accumulates from run_daily)"

    if abs(vrp_pp) < 0.5:
        return f"vol near fair ({vrp_pp:+.1f}pp, {percentile}th %ile)"

    if vrp_pp > 0:
        return (
            f"vol rich +{vrp_pp:.1f}pp, {percentile}th %ile"
            " — premium-selling favored, protection is expensive"
        )

    return (
        f"vol cheap {vrp_pp:.1f}pp, {percentile}th %ile"
        " — protection cheap relative to realized"
    )


def evolution_5d_summary(evol_df: pd.DataFrame) -> dict:
    """Extract the most recent row of a 5-day evolution DataFrame.

    evol_df: output of load_evolution(ticker, horizon=5) — columns include
        level, rms, skew_change, term_change, date. Sorted descending by date
        (most recent row first).

    Returns dict with keys: level, rms, skew_change, term_change, as_of.
    All values are None when evol_df is empty.
    """
    if evol_df is None or evol_df.empty:
        return {
            "level": None,
            "rms": None,
            "skew_change": None,
            "term_change": None,
            "as_of": None,
        }

    row = evol_df.iloc[0]

    def _safe(key: str) -> float | None:
        val = row.get(key) if hasattr(row, "get") else (row[key] if key in evol_df.columns else None)
        if val is None:
            return None
        try:
            f = float(val)
            return None if (f != f) else f  # NaN guard
        except (TypeError, ValueError):
            return None

    date_val = row.get("date") if hasattr(row, "get") else (row["date"] if "date" in evol_df.columns else None)
    as_of = str(date_val) if date_val is not None else None

    return {
        "level": _safe("level"),
        "rms": _safe("rms"),
        "skew_change": _safe("skew_change"),
        "term_change": _safe("term_change"),
        "as_of": as_of,
    }


def positioning_levels(summary: dict, hist_df: pd.DataFrame) -> dict:
    """Extract GEX-derived positioning levels and distances from spot.

    summary: dict from compute_ticker — keys call_wall, put_wall,
        zero_gamma_level, spot, net_gex.
    hist_df: output of load_history — spot column used for context only
        (this function uses summary['spot'] for distance calculations).

    Returns dict with structural levels and signed distance-from-spot in percent.
    Distances are (level - spot) / spot * 100. Returns None for any distance
    where the level or spot is None or spot == 0. No dealer-assumption language
    here — the caller (email or dashboard) adds that context per D-07.
    """
    spot = summary.get("spot")
    call_wall = summary.get("call_wall")
    put_wall = summary.get("put_wall")
    gamma_flip = summary.get("zero_gamma_level")
    net_gex = summary.get("net_gex")

    def _dist(level: float | None) -> float | None:
        if level is None or spot is None or spot == 0:
            return None
        return (level - spot) / spot * 100

    return {
        "call_wall": call_wall,
        "put_wall": put_wall,
        "gamma_flip": gamma_flip,
        "spot": spot,
        "dist_call_wall_pct": _dist(call_wall),
        "dist_put_wall_pct": _dist(put_wall),
        "dist_gamma_flip_pct": _dist(gamma_flip),
        "net_gex_b": (net_gex / 1e9) if net_gex is not None else None,
    }
