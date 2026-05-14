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
          "summary": dict — net_gex, zero_gamma_level, call/put_wall, hedge_shares, iv30, day %
          "s_df":   DataFrame — strike-level GEX
          "p_df":   DataFrame — gamma profile
          "spot":   float
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

    return {"summary": summary, "s_df": s_df, "p_df": p_df,
            "spot": snapshot.spot, "surface_df": surface_df, "skew_df": skew_df}
