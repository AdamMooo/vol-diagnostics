"""
Pure vol metrics computation functions for the institutional diagnostics pipeline.
No side effects, no I/O, no Streamlit calls.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine import config


def _em_none_payload(front_expiry: object, em_dte: int | None) -> dict:
    return {
        "expected_move_pct": None,
        "expected_move_abs": None,
        "em_expiry": str(front_expiry) if front_expiry is not None else None,
        "em_dte": em_dte,
    }


def compute_model_free_em(df: pd.DataFrame, spot: float, front_expiry: object) -> dict:
    """Compute front-expiry expected move using model-free variance (CBOE VIX style)."""
    if df is None or df.empty or front_expiry is None or spot is None or spot <= 0:
        return _em_none_payload(front_expiry, None)

    expiry_mask = df["expiry"].astype(str) == str(front_expiry)
    expiry_df = df.loc[expiry_mask].copy()
    if expiry_df.empty:
        return _em_none_payload(front_expiry, None)

    t_years = pd.to_numeric(expiry_df.get("T_years"), errors="coerce").dropna()
    if t_years.empty:
        return _em_none_payload(front_expiry, None)
    t = float(t_years.iloc[0])
    em_dte = int(round(t * 365))
    if t <= 0:
        return _em_none_payload(front_expiry, em_dte)
    disc = float(np.exp(config.RISK_FREE_FALLBACK * t))  # e^{rT} — CBOE variance discounts Q(K)

    expiry_df["strike"] = pd.to_numeric(expiry_df.get("strike"), errors="coerce")
    expiry_df["bid"] = pd.to_numeric(expiry_df.get("bid"), errors="coerce")
    expiry_df["ask"] = pd.to_numeric(expiry_df.get("ask"), errors="coerce")
    expiry_df["mid"] = 0.5 * (expiry_df["bid"] + expiry_df["ask"])
    expiry_df = expiry_df[
        expiry_df["strike"].notna()
        & (expiry_df["strike"] > 0)
        & expiry_df["type"].isin(["call", "put"])
    ]
    if expiry_df.empty:
        return _em_none_payload(front_expiry, em_dte)

    mids = (
        expiry_df.pivot_table(index="strike", columns="type", values="mid", aggfunc="mean")
        .rename(columns={"call": "call_mid", "put": "put_mid"})
        .sort_index()
    )
    if mids.empty:
        return _em_none_payload(front_expiry, em_dte)

    call_put = mids.dropna(subset=["call_mid", "put_mid"])
    call_put = call_put[(call_put["call_mid"] > 0) & (call_put["put_mid"] > 0)]
    if call_put.empty:
        fwd = float(spot)
    else:
        atm_idx = (call_put["call_mid"] - call_put["put_mid"]).abs().idxmin()
        fwd = float(atm_idx + disc * (call_put.loc[atm_idx, "call_mid"] - call_put.loc[atm_idx, "put_mid"]))

    strikes = mids.index.to_numpy(dtype=float)
    if strikes.size == 0:
        return _em_none_payload(front_expiry, em_dte)

    leq = strikes[strikes <= fwd]
    k0 = float(leq.max()) if leq.size else float(strikes.min())

    q_rows: list[tuple[float, float]] = []
    for i, k in enumerate(strikes):
        if i == 0:
            delta_k = strikes[i + 1] - strikes[i] if strikes.size > 1 else np.nan
        elif i == strikes.size - 1:
            delta_k = strikes[i] - strikes[i - 1]
        else:
            delta_k = 0.5 * (strikes[i + 1] - strikes[i - 1])

        if not np.isfinite(delta_k) or delta_k <= 0:
            continue

        row = mids.loc[k]
        call_mid = row.get("call_mid", np.nan)
        put_mid = row.get("put_mid", np.nan)

        q_mid = np.nan
        if k < k0:
            q_mid = put_mid
        elif k > k0:
            q_mid = call_mid
        else:
            vals = [v for v in (call_mid, put_mid) if pd.notna(v)]
            if vals:
                q_mid = float(sum(vals) / len(vals))

        if pd.isna(q_mid) or not np.isfinite(q_mid) or q_mid <= 0:
            continue
        q_rows.append((float(k), float(delta_k), float(q_mid)))

    if len(q_rows) < 3:
        return _em_none_payload(front_expiry, em_dte)

    integral = disc * sum((dk / (k * k)) * q for k, dk, q in q_rows)
    variance = (2.0 / t) * integral - (1.0 / t) * ((fwd / k0) - 1.0) ** 2
    if not np.isfinite(variance) or variance <= 0:
        return _em_none_payload(front_expiry, em_dte)

    expected_move_pct = float(np.sqrt(variance * t) * 100.0)
    expected_move_abs = float(spot * expected_move_pct / 100.0)

    return {
        "expected_move_pct": expected_move_pct,
        "expected_move_abs": expected_move_abs,
        "em_expiry": str(front_expiry),
        "em_dte": em_dte,
    }


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

        atm_candidates = calls if not calls.empty else grp[grp["type"] == "put"]
        if atm_candidates.empty:
            result[bucket] = None
            continue
        atm_idx = (atm_candidates["strike"] - spot).abs().idxmin()
        atm_iv = float(atm_candidates.loc[atm_idx, "iv"] * 100)

        result[bucket] = {
            "put_iv": put_iv,
            "call_iv": call_iv,
            "atm_iv": atm_iv,
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
    as_of = date_val if date_val is not None else None

    return {
        "level": _safe("level"),
        "rms": _safe("rms"),
        "skew_change": _safe("skew_change"),
        "term_change": _safe("term_change"),
        "as_of": as_of,
    }


# ── VIX Term-Structure Ratios ─────────────────────────────────────────────

# Ticker → vol-index symbols needed for term ratios.
# Only SPY has 9D/3M siblings on CBOE; QQQ/IWM have only the 30-day level.
_TERM_SYMBOLS: dict[str, tuple[str, str, str] | None] = {
    "SPY": ("VIX9D", "VIX", "VIX3M"),
    "QQQ": None,
    "IWM": None,
}


def compute_term_ratios(ticker: str) -> dict:
    """Compute VIX term-structure ratios from the vol-index store.

    SPY: returns VIX9D/VIX and VIX/VIX3M (latest available close).
    QQQ/IWM: returns None/None (no CBOE siblings exist).

    Returns {"term_ratio_9d_30d": float|None, "term_ratio_30d_3m": float|None}
    """
    from engine.data.vol_index import load_vol_index

    symbols = _TERM_SYMBOLS.get(ticker)
    if symbols is None:
        return {"term_ratio_9d_30d": None, "term_ratio_30d_3m": None}

    sym_9d, sym_30d, sym_3m = symbols

    def _latest_close(symbol: str) -> float | None:
        df = load_vol_index(symbol)
        if df.empty:
            return None
        return float(df.iloc[-1]["close"])

    close_9d = _latest_close(sym_9d)
    close_30d = _latest_close(sym_30d)
    close_3m = _latest_close(sym_3m)

    ratio_9d_30d = (close_9d / close_30d) if (close_9d and close_30d) else None
    ratio_30d_3m = (close_30d / close_3m) if (close_30d and close_3m) else None

    return {"term_ratio_9d_30d": ratio_9d_30d, "term_ratio_30d_3m": ratio_30d_3m}


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


# ── VVIX (Vol-of-Vol) ─────────────────────────────────────────────────────

def compute_vvix_level() -> float | None:
    """Latest VVIX close from the vol-index store. Returns None if unavailable."""
    from engine.data.vol_index import load_vol_index
    df = load_vol_index("VVIX")
    if df.empty:
        return None
    return float(df.iloc[-1]["close"])


# ── Net Delta Exposure ─────────────────────────────────────────────────────

def compute_net_delta(gex_df: pd.DataFrame) -> float | None:
    """Dealer delta-hedge position in shares: Σ(delta × OI × 100) over the book.

    Convention (codebase-wide dealer-net-short assumption): a dealer short a
    +delta call is short delta and hedges by BUYING shares (+); a dealer short a
    −delta put is long delta and hedges by SELLING shares (−). Both collapse to
    the signed sum Σ(delta × OI × 100): calls add (delta > 0), puts subtract
    (delta < 0). Positive = net shares dealers are long as a hedge. None if
    delta/OI unavailable.
    """
    if gex_df is None or gex_df.empty:
        return None
    if "delta" not in gex_df.columns or "oi" not in gex_df.columns:
        return None

    MULTIPLIER = 100
    calls = gex_df[gex_df["type"] == "call"]
    puts = gex_df[gex_df["type"] == "put"]

    call_hedge = (calls["delta"] * calls["oi"] * MULTIPLIER).sum()
    # put delta < 0, so abs()-then-subtract == adding the (negative) put delta:
    # equals Σ(put_delta × OI × 100), keeping the whole result a signed Σ(δ·OI·100).
    put_hedge = (puts["delta"].abs() * puts["oi"] * MULTIPLIER).sum()
    return float(call_hedge - put_hedge)
