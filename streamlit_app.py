from __future__ import annotations

import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from gex.data_loader import load_chain
from gex.greeks_engine import add_greeks
from gex.exposure_engine import (
    compute_gex, strike_gex, gamma_profile,
    compute_vex, compute_chex, strike_vex, strike_chex,
)
from gex.analytics import summarise, plot_overview, plot_strike_gex, plot_gamma_profile
from gex.validation import load_yesterday, _classify_vs_yesterday
from gex.report import REGIME_COLOR, REGIME_BG

TICKERS = ["SPY", "QQQ", "IWM"]

st.set_page_config(page_title="GEX Dashboard", layout="wide")


@st.cache_data(ttl=300, show_spinner=False)
def fetch_ticker(ticker: str) -> dict:
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

    summary = summarise(s_df, p_df, spot=snapshot.spot,
                        net_vex=net_vex, net_chex=net_chex,
                        delta_hedge_flow=delta_hedge_flow)
    summary["ticker"] = ticker

    prior = load_yesterday(ticker)
    summary["vs_yesterday"] = (
        _classify_vs_yesterday(summary["net_gex"], summary["gamma_regime"], prior)
        if prior is not None else None
    )

    return {"summary": summary, "s_df": s_df, "p_df": p_df, "spot": snapshot.spot}


def render_regime_card(col, summary: dict) -> None:
    ticker = summary["ticker"]
    regime = summary.get("gamma_regime", "neutral")
    color = REGIME_COLOR.get(regime, "#999")
    bg = REGIME_BG.get(regime, "#eee")
    net_gex_b = (summary.get("net_gex") or 0) / 1e9
    net_vex_b = (summary.get("net_vex") or 0) / 1e9
    df_val = summary.get("delta_hedge_flow")
    df_str = f"${abs(df_val) / 1e9:.1f}B/1%" if df_val is not None else "—"
    vs_yest = summary.get("vs_yesterday") or "—"

    col.markdown(
        f"""
<div style="background:{bg};border-left:4px solid {color};
            border-radius:6px;padding:12px 16px;margin-bottom:8px;">
  <div style="font-weight:bold;font-size:15px;color:{color};">{ticker}</div>
  <div style="font-size:12px;color:{color};font-weight:600;
              text-transform:uppercase;">{regime}</div>
  <div style="font-size:13px;margin-top:6px;">
    GEX: <b>{net_gex_b:+.2f}B</b><br>
    VEX: <b>{net_vex_b:+.2f}B</b><br>
    &Delta;-flow: <b>{df_str}</b><br>
    vs-Yesterday: <b>{vs_yest}</b>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


# Sidebar
with st.sidebar:
    st.title("GEX Dashboard")
    selected = st.multiselect("Tickers", TICKERS, default=TICKERS)
    if st.button("Refresh"):
        fetch_ticker.clear()
        st.rerun()

st.title("GEX — Dealer Gamma Exposure")

if not selected:
    st.info("Select at least one ticker in the sidebar.")
    st.stop()

# Fetch (serial with rate-limit guard)
all_data: list[dict] = []
for i, ticker in enumerate(selected):
    if i > 0:
        time.sleep(0.3)
    with st.spinner(f"Loading {ticker}..."):
        try:
            data = fetch_ticker(ticker)
            all_data.append(data)
        except Exception as exc:
            st.warning(f"{ticker} failed: {exc}")

if not all_data:
    st.warning("No data loaded.")
    st.stop()

# Cross-asset overview chart
results = [d["summary"] for d in all_data if not d["summary"].get("error")]
if results:
    st.subheader("Cross-Asset Overview")
    fig = plot_overview(results)
    st.pyplot(fig)
    plt.close(fig)

# Regime cards
st.subheader("Regime Summary")
cols = st.columns(len(all_data))
for col, data in zip(cols, all_data):
    s = data["summary"]
    if s.get("error"):
        col.error(f"{s['ticker']}: {s['error']}")
    else:
        render_regime_card(col, s)

# Per-ticker expanders
st.subheader("Per-Ticker Detail")
for data in all_data:
    s = data["summary"]
    ticker = s["ticker"]
    if s.get("error"):
        continue
    with st.expander(f"{ticker} — detail", expanded=False):
        col_l, col_r = st.columns(2)
        with col_l:
            fig = plot_strike_gex(data["s_df"], data["spot"], ticker, s)
            st.pyplot(fig)
            plt.close(fig)
        with col_r:
            fig = plot_gamma_profile(data["p_df"], data["spot"], ticker, s)
            st.pyplot(fig)
            plt.close(fig)

        zgl = s.get("zero_gamma_level")
        cw = s.get("call_wall")
        pw = s.get("put_wall")
        summary_df = pd.DataFrame([{
            "Net GEX": f"{(s.get('net_gex') or 0) / 1e9:+.2f}B",
            "VEX": f"{(s.get('net_vex') or 0) / 1e9:+.2f}B",
            "CHEX": f"{(s.get('net_chex') or 0) / 1e9:+.2f}B",
            "Zero-Gamma": f"{zgl:.2f}" if zgl is not None else "—",
            "Call Wall": f"{cw:.0f}" if cw is not None else "—",
            "Put Wall": f"{pw:.0f}" if pw is not None else "—",
        }])
        st.dataframe(summary_df, hide_index=True)
