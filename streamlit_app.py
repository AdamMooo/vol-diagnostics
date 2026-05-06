from __future__ import annotations

import time
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from gex.compute import compute_ticker
from gex.analytics import plot_overview, plot_strike_gex, plot_gamma_profile
from gex.report import REGIME_COLOR

INDEX_TICKERS = ["SPY", "QQQ", "IWM", "XLF", "GLD", "TLT"]

PURPOSE_TICKERS = ["NVDA", "TSLA", "AAPL", "AMD", "META", "AMZN",
                   "GOOGL", "MSFT", "AVGO", "COIN", "COST", "NFLX", "PLTR", "UNH"]

ALL_TICKERS = INDEX_TICKERS + PURPOSE_TICKERS

_B = 1e9

st.set_page_config(
    page_title="GEX Dashboard",
    page_icon="assets/gamma-icon-lg.png",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _check_password() -> bool:
    if st.session_state.get("authenticated"):
        return True
    st.markdown("## GEX Dashboard")
    pwd = st.text_input("Password", type="password", placeholder="Enter password")
    try:
        expected = st.secrets.get("PASSWORD", "")
    except Exception:
        expected = None
    if expected and pwd == expected:
        st.session_state.authenticated = True
        st.rerun()
    elif pwd:
        st.error("Incorrect password")
    return False

if not _check_password():
    st.stop()

_REGIME_RGBA = {
    "positive": "rgba(26, 122, 74, 0.18)",
    "negative": "rgba(192, 57, 43, 0.18)",
    "neutral":  "rgba(127, 140, 141, 0.12)",
}

_CSS = """
<style>
.block-container { padding-top: 1.25rem; padding-bottom: 2rem; max-width: 1500px; }

.sec {
    font-size: 0.62rem; font-weight: 700; letter-spacing: 0.14em;
    text-transform: uppercase; color: #64748b;
    border-bottom: 1px solid rgba(148,163,184,0.25);
    padding-bottom: 5px; margin-bottom: 10px; margin-top: 22px;
}

.rc {
    border-radius: 8px; padding: 14px 16px; margin-bottom: 4px;
    border-left: 5px solid;
}
.rc-ticker { font-size: 1.05rem; font-weight: 700; letter-spacing: 0.03em; }
.rc-regime  { font-size: 0.58rem; font-weight: 700; letter-spacing: 0.14em;
              text-transform: uppercase; margin: 3px 0 10px; opacity: 0.85; }
.rc-grid { display: grid; grid-template-columns: auto 1fr; gap: 4px 16px; font-size: 0.80rem; }
.rc-k { opacity: 0.55; }
.rc-v { font-weight: 700; font-variant-numeric: tabular-nums; text-align: right; }
.rc-obs { font-size: 0.72rem; opacity: 0.70; margin-top: 10px; line-height: 1.6; }

.iv-pill {
    display: inline-block; font-size: 0.65rem; font-weight: 700;
    letter-spacing: 0.06em; padding: 3px 10px; border-radius: 12px;
    margin-top: 10px; background: rgba(148,163,184,0.12);
}
.badge {
    display: inline-block; font-size: 0.58rem; font-weight: 700;
    letter-spacing: 0.1em; text-transform: uppercase;
    padding: 2px 8px; border-radius: 3px; margin-top: 6px;
    background: rgba(148,163,184,0.15); opacity: 0.8;
}
.badge-flip { background: rgba(220,38,38,0.18); color: #f87171; opacity: 1; }
.badge-int  { background: rgba(217,119,6,0.18);  color: #fbbf24; opacity: 1; }
.badge-ease { background: rgba(37,99,235,0.18);  color: #60a5fa; opacity: 1; }
</style>
"""

_VS_CLASS = {
    "FLIPPED":     "badge badge-flip",
    "INTENSIFIED": "badge badge-int",
    "EASED":       "badge badge-ease",
}


def _vs_badge(vs: str | None) -> str:
    if not vs:
        return ""
    return f'<span class="{_VS_CLASS.get(vs, "badge")}">{vs}</span>'


def _iv_pill(iv30: float, show: bool = True) -> str:
    if not show or not iv30:
        return ""
    return f'<span class="iv-pill">IV30 &nbsp; {iv30:.1f}%</span>'


def _derive_observations(summary: dict, spot: float, streak: int | None) -> list[str]:
    obs = []
    zgl = summary.get("zero_gamma_level")
    if zgl and spot:
        pct = (spot - zgl) / zgl * 100
        obs.append(f"{pct:+.1f}% vs ZGL")

    cw = summary.get("call_wall")
    pw = summary.get("put_wall")
    if cw and pw:
        obs.append(f"Range {pw:.0f}–{cw:.0f}")

    if streak and streak > 1:
        obs.append(f"{streak}d streak")

    net_vex = summary.get("net_vex")
    net_gex = summary.get("net_gex")
    if net_vex and net_gex and abs(net_gex) > 0:
        ratio = net_vex / net_gex
        if abs(ratio) > 0.5:
            obs.append(f"VEX/GEX {ratio:.2f}")

    pct_chg = summary.get("price_change_pct")
    if pct_chg:
        obs.append(f"{pct_chg:+.2f}% today")

    ee_strikes = summary.get("early_exercise_strikes", 0)
    ee_oi = summary.get("early_exercise_oi", 0)
    if ee_strikes > 0:
        obs.append(f"EE: {ee_strikes} strikes ({ee_oi:,} OI)")

    return obs


@st.cache_data(ttl=300, show_spinner=False)
def fetch_ticker(ticker: str) -> dict:
    return compute_ticker(ticker)


@st.cache_data(ttl=1800, show_spinner=False)
def _load_history_cached(ticker: str, days: int = 30) -> pd.DataFrame:
    from gex.validation import load_history
    return load_history(ticker, days)


def _compute_streak(hist_df: pd.DataFrame, current_regime: str) -> int | None:
    if hist_df.empty:
        return None
    count = 0
    for regime in hist_df["gamma_regime"]:
        if regime == current_regime:
            count += 1
        else:
            break
    return count if count > 0 else None


def render_regime_card(col, summary: dict, spot: float | None = None,
                       streak: int | None = None, show_iv30: bool = False) -> None:
    ticker = summary["ticker"]
    regime = summary.get("gamma_regime", "neutral")
    color = REGIME_COLOR.get(regime, "#999")
    bg = _REGIME_RGBA.get(regime, "rgba(127,140,141,0.12)")
    net_gex_b = (summary.get("net_gex") or 0) / _B
    net_vex_b = (summary.get("net_vex") or 0) / _B
    df_val = summary.get("delta_hedge_flow")
    df_str = f"${abs(df_val) / _B:.1f}B/1%" if df_val is not None else "—"
    zgl = summary.get("zero_gamma_level")
    zgl_str = f"{zgl:.1f}" if zgl is not None else "—"
    spot_str = f"{spot:,.2f}" if spot else "—"
    vs = summary.get("vs_yesterday")
    iv30 = summary.get("iv30", 0.0)

    obs = _derive_observations(summary, spot or 0, streak)
    obs_html = "".join(f"<div>{o}</div>" for o in obs)

    col.markdown(f"""
<div class="rc" style="background:{bg};border-left-color:{color};">
  <div class="rc-ticker" style="color:{color};">{ticker}</div>
  <div class="rc-regime" style="color:{color};">{regime}</div>
  <div class="rc-grid">
    <span class="rc-k">Spot</span>         <span class="rc-v">{spot_str}</span>
    <span class="rc-k">Net GEX</span>      <span class="rc-v">{net_gex_b:+.2f}B</span>
    <span class="rc-k">VEX</span>          <span class="rc-v">{net_vex_b:+.2f}B</span>
    <span class="rc-k">&Delta;-flow</span>  <span class="rc-v">{df_str}</span>
    <span class="rc-k">Zero-&gamma;</span>  <span class="rc-v">{zgl_str}</span>
  </div>
  <div class="rc-obs">{obs_html}</div>
  {_iv_pill(iv30, show=show_iv30)}
  {_vs_badge(vs)}
</div>
""", unsafe_allow_html=True)


def render_section(tickers: list[str], all_data: dict[str, dict],
                   n_cols: int = 5, show_iv30: bool = False,
                   show_overview: bool = True) -> None:
    data_list = [all_data[t] for t in tickers if t in all_data and not all_data[t]["summary"].get("error")]

    if not data_list:
        st.info("No data loaded for this section.")
        return

    rows = [data_list[i:i + n_cols] for i in range(0, len(data_list), n_cols)]
    for row in rows:
        cols = st.columns(n_cols)
        for col, data in zip(cols, row):
            s = data["summary"]
            hist = _load_history_cached(s["ticker"], days=30)
            streak = _compute_streak(hist, s.get("gamma_regime", "neutral"))
            render_regime_card(col, s, spot=data.get("spot"), streak=streak, show_iv30=show_iv30)

    if show_overview and len(data_list) > 1:
        summaries = [d["summary"] for d in data_list]
        fig = plot_overview(summaries)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="sec">Detail</div>', unsafe_allow_html=True)
    for data in data_list:
        s = data["summary"]
        ticker = s["ticker"]
        regime = s.get("gamma_regime", "neutral")
        spot = data.get("spot")
        zgl = s.get("zero_gamma_level")
        cw = s.get("call_wall")
        pw = s.get("put_wall")
        iv30 = s.get("iv30", 0.0)

        label = f"{ticker}  ·  {regime.upper()}"
        if show_iv30 and iv30:
            label += f"  ·  IV30 {iv30:.1f}%"

        with st.expander(label, expanded=False):
            row = {
                "Spot": f"{spot:,.2f}" if spot else "—",
                "Net GEX": f"{(s.get('net_gex') or 0) / _B:+.2f}B",
                "VEX": f"{(s.get('net_vex') or 0) / _B:+.2f}B",
                "CHEX": f"{(s.get('net_chex') or 0) / _B:+.2f}B",
                "Zero-γ": f"{zgl:.2f}" if zgl is not None else "—",
                "Call Wall": f"{cw:.0f}" if cw is not None else "—",
                "Put Wall": f"{pw:.0f}" if pw is not None else "—",
            }
            if show_iv30 and iv30:
                row["IV30"] = f"{iv30:.1f}%"
            st.dataframe(pd.DataFrame([row]), hide_index=True, use_container_width=True)

            c1, c2 = st.columns([3, 2])
            with c1:
                st.plotly_chart(plot_strike_gex(data["s_df"], spot, ticker, s),
                                use_container_width=True)
            with c2:
                st.plotly_chart(plot_gamma_profile(data["p_df"], spot, ticker, s),
                                use_container_width=True)

            hist30 = _load_history_cached(ticker, days=30)
            if not hist30.empty:
                chart_df = hist30.sort_values("date")
                zgl_fig = go.Figure()
                zgl_fig.add_trace(go.Scatter(
                    x=chart_df["date"], y=chart_df["zero_gamma_level"],
                    name="Zero-γ", line=dict(color="#f59e0b", width=1.5),
                ))
                zgl_fig.add_trace(go.Scatter(
                    x=chart_df["date"], y=chart_df["spot"],
                    name="Spot", line=dict(color="white", width=1.2, dash="dash"),
                ))
                zgl_fig.update_layout(
                    template="plotly_dark",
                    title="ZGL vs Spot — 30 sessions",
                    height=220,
                    margin=dict(t=40, b=30, l=60, r=20),
                    legend=dict(orientation="h", y=1.15),
                )
                st.plotly_chart(zgl_fig, use_container_width=True)

                counts = hist30["gamma_regime"].value_counts().reset_index()
                counts.columns = ["Regime", "Sessions"]
                counts["% Days"] = (counts["Sessions"] / counts["Sessions"].sum() * 100).round(1).astype(str) + "%"
                st.dataframe(counts, hide_index=True, use_container_width=True)


# ── Boot ──────────────────────────────────────────────────────────────────────

st.markdown(_CSS, unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### GEX Monitor")
    st.markdown("**Index**")
    sel_index = st.multiselect("", INDEX_TICKERS, default=INDEX_TICKERS, key="sel_index", label_visibility="collapsed")
    st.markdown("**Purpose Yield Shares**")
    sel_purpose = st.multiselect("", PURPOSE_TICKERS, default=PURPOSE_TICKERS, key="sel_purpose", label_visibility="collapsed")
    st.caption(f"Cache: 5 min · {datetime.now().strftime('%H:%M')} local")
    st.divider()
    if st.button("Refresh data", use_container_width=True):
        fetch_ticker.clear()
        st.rerun()
    st.caption("CBOE delayed · 15-min lag")

st.markdown("## GEX Dashboard")
st.caption(f"Dealer gamma exposure · CBOE chains · {datetime.now().strftime('%A %B %d, %Y').replace(' 0', ' ')}")

selected_all = sel_index + sel_purpose
if not selected_all:
    st.info("Select at least one ticker in the sidebar.")
    st.stop()

# ── Fetch all tickers ──────────────────────────────────────────────────────────
all_data: dict[str, dict] = {}
errors: list[str] = []

with st.spinner("Loading chains from CBOE..."):
    for i, ticker in enumerate(selected_all):
        if i > 0:
            time.sleep(0.15)
        try:
            all_data[ticker] = fetch_ticker(ticker)
        except Exception as exc:
            errors.append(f"{ticker}: {exc}")

for err in errors:
    st.error(err)

if not all_data:
    st.warning("No data loaded.")
    st.stop()

# ── Index section ──────────────────────────────────────────────────────────────
if sel_index:
    st.markdown('<div class="sec">Index</div>', unsafe_allow_html=True)
    render_section(sel_index, all_data, n_cols=min(len(sel_index), 6), show_iv30=True, show_overview=True)

# ── Purpose Yield Shares section ───────────────────────────────────────────────
if sel_purpose:
    st.markdown('<div class="sec">Purpose Yield Shares</div>', unsafe_allow_html=True)
    st.caption("Underlyings for weekly options writing. IV30 = CBOE 30-day implied vol.")
    render_section(sel_purpose, all_data, n_cols=5, show_iv30=True, show_overview=True)
