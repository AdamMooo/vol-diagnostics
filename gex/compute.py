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
    compute_gex, strike_gex, strike_oi, gamma_profile, vol_surface_data, compute_skew,
    surface_diagnostics,
)
from gex.analytics import summarise
from gex.vol_metrics import compute_skew_25d, compute_term_structure, compute_rv20, compute_vrp
from gex.validation import load_history


def _fetch_spot_history_yf(ticker: str, days: int = 35) -> "pd.Series | None":
    """Fetch daily closing prices from yfinance (oldest-first) for RV20 computation.

    Falls back gracefully — never raises. Returns None if data is insufficient.
    BRK.B is remapped to BRK-B for yfinance compatibility.
    """
    try:
        import yfinance as yf
        import pandas as pd
        yf_ticker = ticker.replace(".", "-")
        hist = yf.Ticker(yf_ticker).history(period=f"{days}d")
        if hist.empty or "Close" not in hist.columns:
            return None
        closes = hist["Close"].dropna().reset_index(drop=True)
        return closes if len(closes) >= 2 else None
    except Exception as exc:
        print(f"[compute] yf history failed for {ticker}: {exc}")
        return None


def _get_risk_free_rate() -> float:
    """3-month T-bill rate from ^IRX; falls back to config.RISK_FREE_FALLBACK on failure."""
    try:
        import yfinance as yf
        fi = yf.Ticker("^IRX").fast_info
        rate = fi.get("lastPrice") or fi.get("last_price")
        if rate and rate > 0:
            return float(rate) / 100
        print(f"[compute] ^IRX rate fetch returned None; using fallback {config.RISK_FREE_FALLBACK}")
    except Exception as exc:
        print(f"[compute] rate fetch failed ({exc}); using fallback {config.RISK_FREE_FALLBACK}")
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
    s_df = s_df.merge(strike_oi(df), on="strike", how="left")

    r = _get_risk_free_rate()
    p_df = gamma_profile(df, spot=snapshot.spot, r=r)
    surface_df = vol_surface_data(df, spot=snapshot.spot)
    surface_diag = surface_diagnostics(surface_df, snapshot.spot)
    print(f"[diag] {ticker}: coverage {surface_diag['coverage_pct']:.0f}%  "
          f"fit_rmse {surface_diag['fit_rmse']:.1f}pp  cv {surface_diag['cv_rmse']:.1f}pp  "
          f"coherence_violations {surface_diag['coherence_violations']}")
    skew_df = compute_skew(df, spot=snapshot.spot)
    # skew_df is sorted by dte ascending — iloc[0] is shortest qualifying expiry
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
    summary["coverage_pct"] = surface_diag["coverage_pct"]
    summary["fit_rmse"] = surface_diag["fit_rmse"]
    summary["max_resid"] = surface_diag["max_resid"]
    summary["cv_rmse"] = surface_diag["cv_rmse"]
    summary["coherence_calendar"] = surface_diag["coherence_calendar"]
    summary["coherence_butterfly"] = surface_diag["coherence_butterfly"]
    summary["coherence_violations"] = surface_diag["coherence_violations"]

    # OI walls — strike with highest call or put open interest, None-safe
    oi_call_wall = None
    oi_put_wall = None
    if "call_oi" in s_df.columns:
        call_oi = s_df["call_oi"].fillna(0)
        if call_oi.gt(0).any():
            oi_call_wall = float(s_df.loc[call_oi.idxmax(), "strike"])
    if "put_oi" in s_df.columns:
        put_oi = s_df["put_oi"].fillna(0)
        if put_oi.gt(0).any():
            oi_put_wall = float(s_df.loc[put_oi.idxmax(), "strike"])
    summary["oi_call_wall"] = oi_call_wall
    summary["oi_put_wall"] = oi_put_wall

    skew_25d = compute_skew_25d(df, spot=snapshot.spot)
    term_structure = compute_term_structure(df, spot=snapshot.spot)
    hist = load_history(ticker)
    # Use parquet history if we have 21+ rows; otherwise fall back to yfinance daily closes.
    if not hist.empty and "spot" in hist.columns and len(hist) >= 21:
        spot_series = hist["spot"].iloc[::-1].reset_index(drop=True)
    else:
        spot_series = _fetch_spot_history_yf(ticker)
        if spot_series is None and not hist.empty and "spot" in hist.columns:
            spot_series = hist["spot"].iloc[::-1].reset_index(drop=True)
    if spot_series is not None:
        rv20 = compute_rv20(spot_series)
        iv30_decimal = (snapshot.iv30 / 100.0) if snapshot.iv30 else None
        vrp_decimal = compute_vrp(iv30_decimal, rv20)
        vrp = vrp_decimal * 100 if vrp_decimal is not None else None
    else:
        rv20, vrp = None, None
    summary["rv20"] = rv20
    summary["vrp"] = vrp

    return {
        "summary": summary, "s_df": s_df, "p_df": p_df,
        "spot": snapshot.spot, "surface_df": surface_df, "skew_df": skew_df,
        "skew": skew_25d, "term_structure": term_structure,
        "rv20": rv20, "vrp": vrp, "surface_diag": surface_diag,
    }
