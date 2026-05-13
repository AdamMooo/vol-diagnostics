from __future__ import annotations

import time
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from gex.compute import compute_ticker
from gex.analytics import plot_overview, plot_strike_gex, plot_gamma_profile
from gex.report import REGIME_COLOR

INDEX_TICKERS = ["SPY", "QQQ", "IWM"]

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

_SIGN_RGBA = {
    "positive": "rgba(26, 122, 74, 0.18)",
    "negative": "rgba(192, 57, 43, 0.18)",
    "zero":     "rgba(127, 140, 141, 0.12)",
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
.rc-ticker { font-size: 1.05rem; font-weight: 700; letter-spacing: 0.03em; margin-bottom: 10px; }
.rc-grid { display: grid; grid-template-columns: auto 1fr; gap: 4px 16px; font-size: 0.80rem; }
.rc-k { opacity: 0.55; }
.rc-v { font-weight: 700; font-variant-numeric: tabular-nums; text-align: right; }
.rc-obs { font-size: 0.72rem; opacity: 0.70; margin-top: 10px; line-height: 1.6; }

.iv-pill {
    display: inline-block; font-size: 0.65rem; font-weight: 700;
    letter-spacing: 0.06em; padding: 3px 10px; border-radius: 12px;
    margin-top: 10px; background: rgba(148,163,184,0.12);
}
</style>
"""


def _iv_pill(iv30: float, show: bool = True) -> str:
    if not show or not iv30:
        return ""
    return f'<span class="iv-pill">IV30 &nbsp; {iv30:.1f}%</span>'


def _derive_observations(summary: dict, spot: float) -> list[str]:
    """Only observations we can defend rigorously: pure arithmetic over net gex,
    spot, zgl, and wall strikes — no derived ratios, streaks, or vanna-based
    flags, all of which depend on inputs we don't fully trust."""
    obs = []
    zgl = summary.get("zero_gamma_level")
    if zgl and spot:
        pct = (spot - zgl) / zgl * 100
        obs.append(f"{pct:+.1f}% vs ZGL")

    cw = summary.get("call_wall")
    pw = summary.get("put_wall")
    if cw and pw:
        obs.append(f"Range {pw:.0f}–{cw:.0f}")

    pct_chg = summary.get("price_change_pct")
    if pct_chg:
        obs.append(f"{pct_chg:+.2f}% today")

    return obs


@st.cache_data(ttl=300, show_spinner=False)
def fetch_ticker(ticker: str) -> dict:
    return compute_ticker(ticker)


@st.cache_data(ttl=1800, show_spinner=False)
def _load_history_cached(ticker: str, days: int = 30) -> pd.DataFrame:
    from gex.validation import load_history
    return load_history(ticker, days)


def _sign_key(net_gex: float | None) -> str:
    if net_gex is None or net_gex == 0:
        return "zero"
    return "positive" if net_gex > 0 else "negative"


def render_regime_card(col, summary: dict, spot: float | None = None,
                       show_iv30: bool = False) -> None:
    """Card content — only outputs we can defend with our lives:
    spot, net gex value, δ-flow, zero-γ level, iv30. The accent bar / background
    reflect the *sign* of net gex; no categorical regime label is shown (the
    $200M neutral floor is hand-tuned and non-stationary)."""
    ticker = summary["ticker"]
    sign = _sign_key(summary.get("net_gex"))
    color = REGIME_COLOR.get(sign, "#999")
    bg = _SIGN_RGBA.get(sign, "rgba(127,140,141,0.12)")
    net_gex_b = (summary.get("net_gex") or 0) / _B
    df_val = summary.get("delta_hedge_flow")
    if df_val is not None:
        v = abs(df_val)
        df_str = f"{v / 1e6:.1f}M sh/$1" if v >= 1e6 else f"{v / 1e3:.0f}K sh/$1"
    else:
        df_str = "—"
    zgl = summary.get("zero_gamma_level")
    zgl_str = f"{zgl:.1f}" if zgl is not None else "—"
    spot_str = f"{spot:,.2f}" if spot else "—"
    iv30 = summary.get("iv30", 0.0)

    obs = _derive_observations(summary, spot or 0)
    obs_html = "".join(f"<div>{o}</div>" for o in obs)

    col.markdown(f"""
<div class="rc" style="background:{bg};border-left-color:{color};">
  <div class="rc-ticker" style="color:{color};">{ticker}</div>
  <div class="rc-grid">
    <span class="rc-k">Spot</span>         <span class="rc-v">{spot_str}</span>
    <span class="rc-k">Net GEX</span>      <span class="rc-v">{net_gex_b:+.2f}B</span>
    <span class="rc-k">Hedge Shares/$1</span>  <span class="rc-v">{df_str}</span>
    <span class="rc-k">Zero-&gamma;</span>  <span class="rc-v">{zgl_str}</span>
  </div>
  <div class="rc-obs">{obs_html}</div>
  {_iv_pill(iv30, show=show_iv30)}
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
            render_regime_card(col, data["summary"], spot=data.get("spot"),
                               show_iv30=show_iv30)

    if show_overview and len(data_list) > 1:
        summaries = [d["summary"] for d in data_list]
        fig = plot_overview(summaries)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="sec">Detail</div>', unsafe_allow_html=True)
    for data in data_list:
        s = data["summary"]
        ticker = s["ticker"]
        spot = data.get("spot")
        zgl = s.get("zero_gamma_level")
        cw = s.get("call_wall")
        pw = s.get("put_wall")
        iv30 = s.get("iv30", 0.0)

        label = ticker
        if show_iv30 and iv30:
            label += f"  ·  IV30 {iv30:.1f}%"

        with st.expander(label, expanded=False):
            row = {
                "Spot": f"{spot:,.2f}" if spot else "—",
                "Net GEX": f"{(s.get('net_gex') or 0) / _B:+.2f}B",
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

            # 30-session ZGL-vs-spot history — defensible because both series
            # are observable each day, no derived label or category overlaid.
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


# ── Boot ──────────────────────────────────────────────────────────────────────

st.markdown(_CSS, unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### GEX Monitor")
    st.markdown("**Equity Index Dealer Flow**")
    sel_index = st.multiselect("", INDEX_TICKERS, default=INDEX_TICKERS, key="sel_index", label_visibility="collapsed")
    st.caption(f"Cache: 5 min · {datetime.now().strftime('%H:%M')} local")
    st.divider()
    if st.button("Refresh data", use_container_width=True):
        fetch_ticker.clear()
        st.rerun()
    st.caption("CBOE delayed · 15-min lag")
    st.caption("OI as of: prior session close")
    st.caption("Full-chain (≥1 DTE) · 0DTE excluded for math consistency across GEX/VEX/CHEX")

st.markdown("## GEX Dashboard")
st.caption(f"Equity Index Dealer Flow: SPY · QQQ · IWM  ·  {datetime.now().strftime('%A %B %d, %Y').replace(' 0', ' ')}")

selected_all = sel_index
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
    render_section(sel_index, all_data, n_cols=min(len(sel_index), 3), show_iv30=True, show_overview=True)

# ── Methodology footer ────────────────────────────────────────────────────────
st.divider()
st.caption(
    "**Defensible outputs only** — this dashboard intentionally shows only what survives "
    "a rigorous methodology audit: **Net GEX sign + magnitude**, **Zero-γ level**, "
    "**Call/Put wall strikes** (single max one-sided GEX strike, no cluster smoothing), "
    "**Hedge Shares/$1** (shares dealers trade per $1 spot move = Γ_net × OI × 100), **IV30**. "
    "Vanna/charm exposures, hand-tuned regime labels, vs-yesterday classifiers, streaks, and "
    "event-study means have been removed — they could not be defended at a quant PM's level of scrutiny."
)
st.caption(
    "**Dealer positioning assumption** · GEX assumes dealers are net short all options "
    "(retail buys, dealers sell). Holds empirically in aggregate for SPY/QQQ/IWM; "
    "may be wrong at individual strikes with covered-call, vol-selling, or institutional flow dominant."
)
st.caption(
    "**Data limitations** · OI is T-1 (prior session close) — ZGL and walls describe "
    "yesterday's positioning. Spot/IV/chain quotes are ~15-min delayed. Full-chain ≥1 DTE "
    "(0DTE excluded for math consistency). Absolute Net GEX magnitude is methodology-dependent "
    "across commercial sources — treat sign and order of magnitude as load-bearing, absolute "
    "levels as conventions. **No realized-vol attribution.** This is a positioning monitor, "
    "not a forecaster."
)
st.caption(
    "**Universe** · SPY / QQQ / IWM only — the standard dealer positioning convention "
    "(long calls, short puts) is empirically defensible for these names."
)
