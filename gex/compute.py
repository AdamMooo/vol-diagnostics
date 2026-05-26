"""
Shared GEX compute pipeline — single source of truth for both run_daily and streamlit_app.

Both callers wrap this function:
  - run_daily.process_ticker()  → adds error handling
  - streamlit_app.fetch_ticker() → adds @st.cache_data
"""
from __future__ import annotations

from gex import config
from gex.data_loader import load_chain
from gex.greeks_engine import add_greeks
from gex.exposure_engine import (
    compute_gex, strike_gex, gamma_profile, vol_surface_data, compute_skew,
)
from gex.analytics import summarise
from gex.vol_metrics import compute_skew_25d, compute_term_structure, compute_rv20, compute_vrp
from gex.validation import load_history


def _get_risk_free_rate() -> float:
    """3-month T-bill rate from ^IRX; falls back to config.RISK_FREE_FALLBACK on failure."""
    try:
        import yfinance as yf
        rate = yf.Ticker("^IRX").fast_info.get("lastPrice")
        if rate and rate > 0:
            return float(rate) / 100
    except Exception:
        pass
    return config.RISK_FREE_FALLBACK


def compute_ticker(ticker: str) -> dict:
    """
    Full pipeline for one ticker.

    Returns:
        {
          "summary":        dict — net_gex, zero_gamma_level, call/put_wall, iv30, rv20, vrp, day %
          "s_df":           DataFrame — strike-level GEX
          "p_df":           DataFrame — gamma profile
          "spot":           float
          "surface_df":     DataFrame — vol surface
          "skew_df":        DataFrame — per-expiry skew (feeds parquet history columns)
          "skew":           dict | None — 25d skew buckets (front_month, second_month)
          "term_structure": dict | None — classification + ATM IV points
          "rv20":           float | None — 20-day annualized realized vol
          "vrp":            float | None — IV30 − RV20
        }
    """
    snapshot = load_chain(ticker)
    df = add_greeks(snapshot.chains, spot=snapshot.spot, today=snapshot.as_of)
    df = compute_gex(df, spot=snapshot.spot)

    s_df = strike_gex(df)

    r = _get_risk_free_rate()
    p_df = gamma_profile(df, spot=snapshot.spot, r=r)
    surface_df = vol_surface_data(df, spot=snapshot.spot)
    skew_df = compute_skew(df)
    front_skew = float(skew_df["skew_pp"].iloc[0]) if not skew_df.empty else None

    net_gex_scalar = float(s_df["gex"].sum())
    # Shares dealers must trade per $1 spot move to stay delta-neutral.
    # Derived by cancelling the S²×0.01 normalization from GEX: Γ_net × OI × 100.
    if snapshot.spot <= 0:
        raise ValueError(f"Invalid spot price {snapshot.spot} for {ticker}")
    delta_hedge_flow = net_gex_scalar / (snapshot.spot ** 2 * 0.01)

    summary = summarise(
        s_df, p_df,
        spot=snapshot.spot,
        delta_hedge_flow=delta_hedge_flow,
    )
    summary["ticker"] = ticker
    summary["iv30"] = snapshot.iv30
    summary["price_change_pct"] = snapshot.price_change_pct
    summary["front_skew"] = front_skew

    skew_25d = compute_skew_25d(df, spot=snapshot.spot)
    term_structure = compute_term_structure(df, spot=snapshot.spot)
    hist = load_history(ticker)
    if hist.empty or "spot" not in hist.columns:
        rv20, vrp = None, None
    else:
        spot_series = hist["spot"].iloc[::-1]   # reverse to oldest-first (load_history returns descending)
        rv20 = compute_rv20(spot_series)
        iv30_decimal = (snapshot.iv30 / 100.0) if snapshot.iv30 is not None else None
        vrp = compute_vrp(iv30_decimal, rv20)
    summary["rv20"] = rv20
    summary["vrp"] = vrp

    return {
        "summary": summary, "s_df": s_df, "p_df": p_df,
        "spot": snapshot.spot, "surface_df": surface_df, "skew_df": skew_df,
        "skew": skew_25d, "term_structure": term_structure,
        "rv20": rv20, "vrp": vrp,
    }
