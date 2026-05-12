"""
Shared GEX compute pipeline — single source of truth for both run_daily and streamlit_app.

Both callers wrap this function:
  - run_daily.process_ticker()  → adds error handling
  - streamlit_app.fetch_ticker() → adds @st.cache_data
"""
from __future__ import annotations

from gex.data_loader import load_chain
from gex.greeks_engine import add_greeks
from gex.exposure_engine import compute_gex, strike_gex, gamma_profile
from gex.analytics import summarise


def compute_ticker(ticker: str) -> dict:
    """
    Full pipeline for one ticker.

    Returns:
        {
          "summary": dict — net_gex, zero_gamma_level, call/put_wall, δ-flow, iv30, day %
          "s_df":   DataFrame — strike-level GEX
          "p_df":   DataFrame — gamma profile
          "spot":   float
        }
    """
    snapshot = load_chain(ticker)
    df = add_greeks(snapshot.chains, spot=snapshot.spot, today=snapshot.as_of)
    df = compute_gex(df, spot=snapshot.spot)

    s_df = strike_gex(df)
    p_df = gamma_profile(df, spot=snapshot.spot)

    net_gex_scalar = float(s_df["gex"].sum())
    delta_hedge_flow = net_gex_scalar / (snapshot.spot * 0.01)

    summary = summarise(
        s_df, p_df,
        spot=snapshot.spot,
        delta_hedge_flow=delta_hedge_flow,
    )
    summary["ticker"] = ticker
    summary["iv30"] = snapshot.iv30
    summary["price_change_pct"] = snapshot.price_change_pct

    return {"summary": summary, "s_df": s_df, "p_df": p_df, "spot": snapshot.spot}
