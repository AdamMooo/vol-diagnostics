"""
Shared GEX compute pipeline — single source of truth for both run_daily and streamlit_app.

Both callers wrap this function:
  - run_daily.process_ticker()  → adds error handling
  - streamlit_app.fetch_ticker() → adds @st.cache_data
"""
from __future__ import annotations

from gex.data_loader import load_chain
from gex.greeks_engine import add_greeks
from gex.exposure_engine import (
    compute_gex, compute_vex, compute_chex,
    strike_gex, strike_vex, strike_chex,
    gamma_profile,
)
from gex.analytics import summarise
from gex.validation import load_yesterday, _classify_vs_yesterday


def compute_ticker(ticker: str) -> dict:
    """
    Full pipeline for one ticker.

    Returns:
        {
          "summary": dict  — analytics + regime + vs_yesterday
          "s_df":   DataFrame — strike-level GEX
          "p_df":   DataFrame — gamma profile
          "spot":   float
        }
    """
    snapshot = load_chain(ticker)
    df = add_greeks(snapshot.chains, spot=snapshot.spot, today=snapshot.as_of)
    df = compute_gex(df, spot=snapshot.spot)
    df = compute_vex(df, spot=snapshot.spot)
    df = compute_chex(df, spot=snapshot.spot)

    s_df = strike_gex(df)
    v_df = strike_vex(df)
    c_df = strike_chex(df)
    p_df = gamma_profile(df, spot=snapshot.spot)

    net_vex = float(v_df["vex"].sum())
    net_chex = float(c_df["chex"].sum())
    net_gex_scalar = float(s_df["gex"].sum())
    delta_hedge_flow = net_gex_scalar / (snapshot.spot * 0.01)

    summary = summarise(
        s_df, p_df,
        spot=snapshot.spot,
        net_vex=net_vex,
        net_chex=net_chex,
        delta_hedge_flow=delta_hedge_flow,
    )
    summary["ticker"] = ticker
    summary["iv30"] = snapshot.iv30
    summary["price_change_pct"] = snapshot.price_change_pct

    prior = load_yesterday(ticker)
    summary["vs_yesterday"] = (
        _classify_vs_yesterday(summary["net_gex"], summary["gamma_regime"], prior)
        if prior is not None else None
    )

    return {"summary": summary, "s_df": s_df, "p_df": p_df, "spot": snapshot.spot}
