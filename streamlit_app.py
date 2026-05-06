from __future__ import annotations

import time
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from gex.compute import compute_ticker
from gex.analytics import plot_overview, plot_strike_gex, plot_gamma_profile
from gex.report import REGIME_COLOR

TICKERS = ["SPY", "QQQ", "IWM"]
_B = 1e9

# Dark-mode-compatible chart style — transparent bg, light text
plt.rcParams.update({
    "figure.figsize": (13, 5),
    "figure.dpi": 100,
    "figure.facecolor": "none",      # transparent → inherits page background
    "axes.facecolor": "none",
    "axes.edgecolor": "#4b5563",
    "axes.grid": True,
    "grid.color": "#374151",
    "grid.linewidth": 0.6,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "text.color": "#e5e7eb",
    "axes.labelcolor": "#9ca3af",
    "xtick.color": "#9ca3af",
    "ytick.color": "#9ca3af",
    "font.family": "sans-serif",
    "font.size": 11,
    "axes.titlesize": 12,
    "axes.labelsize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
})

st.set_page_config(page_title="GEX Dashboard", layout="wide", initial_sidebar_state="expanded")


def _check_password() -> bool:
    if st.session_state.get("authenticated"):
        return True
    st.markdown("## GEX Dashboard")
    pwd = st.text_input("Password", type="password", placeholder="Enter password")
    if pwd == st.secrets.get("PASSWORD", ""):
        st.session_state.authenticated = True
        st.rerun()
    elif pwd:
        st.error("Incorrect password")
    return False

if not _check_password():
    st.stop()

# Semi-transparent regime backgrounds — work on both light and dark themes
_REGIME_RGBA = {
    "positive": "rgba(26, 122, 74, 0.18)",
    "negative": "rgba(192, 57, 43, 0.18)",
    "neutral":  "rgba(127, 140, 141, 0.12)",
}

_CSS = """
<style>
.block-container { padding-top: 1.25rem; padding-bottom: 2rem; max-width: 1400px; }

.sec {
    font-size: 0.62rem; font-weight: 700; letter-spacing: 0.14em;
    text-transform: uppercase; color: #64748b;
    border-bottom: 1px solid rgba(148,163,184,0.25);
    padding-bottom: 5px; margin-bottom: 8px;
}

/* Regime card — semi-transparent so it works on any theme bg */
.rc {
    border-radius: 8px; padding: 16px 20px; margin-bottom: 4px;
    border-left: 5px solid;
}
.rc-ticker { font-size: 1.1rem; font-weight: 700; letter-spacing: 0.03em; }
.rc-regime  { font-size: 0.6rem; font-weight: 700; letter-spacing: 0.14em;
              text-transform: uppercase; margin: 3px 0 12px; opacity: 0.85; }

.rc-grid { display: grid; grid-template-columns: auto 1fr; gap: 5px 18px; font-size: 0.83rem; }
.rc-k { opacity: 0.55; }
.rc-v { font-weight: 700; font-variant-numeric: tabular-nums; text-align: right; }

.badge {
    display: inline-block; font-size: 0.58rem; font-weight: 700;
    letter-spacing: 0.1em; text-transform: uppercase;
    padding: 2px 8px; border-radius: 3px; margin-top: 10px;
    background: rgba(148,163,184,0.15); opacity: 0.8;
}
.badge-flip { background: rgba(220,38,38,0.18); color: #f87171; opacity: 1; }
.badge-int  { background: rgba(217,119,6,0.18); color: #fbbf24; opacity: 1; }
.badge-ease { background: rgba(37,99,235,0.18); color: #60a5fa; opacity: 1; }
</style>
"""

_VS_CLASS = {
    "FLIPPED": "badge badge-flip",
    "INTENSIFIED": "badge badge-int",
    "EASED": "badge badge-ease",
}


def _vs_badge(vs: str | None) -> str:
    if not vs:
        return ""
    return f'<span class="{_VS_CLASS.get(vs, "badge")}">{vs}</span>'


@st.cache_data(ttl=300, show_spinner=False)
def fetch_ticker(ticker: str) -> dict:
    return compute_ticker(ticker)


def render_regime_card(col, summary: dict, spot: float | None = None) -> None:
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

    col.markdown(f"""
<div class="rc" style="background:{bg};border-left-color:{color};">
  <div class="rc-ticker" style="color:{color};">{ticker}</div>
  <div class="rc-regime" style="color:{color};">{regime}</div>
  <div class="rc-grid">
    <span class="rc-k">Spot</span>       <span class="rc-v">{spot_str}</span>
    <span class="rc-k">Net GEX</span>    <span class="rc-v">{net_gex_b:+.2f}B</span>
    <span class="rc-k">VEX</span>        <span class="rc-v">{net_vex_b:+.2f}B</span>
    <span class="rc-k">&Delta;-flow</span><span class="rc-v">{df_str}</span>
    <span class="rc-k">Zero-&gamma;</span><span class="rc-v">{zgl_str}</span>
  </div>
  {_vs_badge(vs)}
</div>
""", unsafe_allow_html=True)


# ── Boot ──────────────────────────────────────────────────────────────────────

st.markdown(_CSS, unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### GEX Monitor")
    selected = st.multiselect("Tickers", TICKERS, default=TICKERS)
    st.caption(f"Cache: 5 min · {datetime.now().strftime('%H:%M')} local")
    st.divider()
    if st.button("Refresh data", use_container_width=True):
        fetch_ticker.clear()
        st.rerun()
    st.caption("yfinance · SPY / QQQ / IWM")

st.markdown("## GEX Dashboard")
st.caption("Dealer gamma, vanna, and charm exposure")

if not selected:
    st.info("Select at least one ticker in the sidebar.")
    st.stop()

# ── Fetch ─────────────────────────────────────────────────────────────────────
all_data: list[dict] = []
errors: list[str] = []
for i, ticker in enumerate(selected):
    if i > 0:
        time.sleep(0.3)
    with st.spinner(f"Loading {ticker}…"):
        try:
            all_data.append(fetch_ticker(ticker))
        except Exception as exc:
            errors.append(f"{ticker}: {exc}")

for err in errors:
    st.error(err)

if not all_data:
    st.warning("No data loaded. Check your connection or click Refresh.")
    st.stop()

# ── Regime cards ──────────────────────────────────────────────────────────────
st.markdown('<div class="sec">Regime Summary</div>', unsafe_allow_html=True)
cols = st.columns(len(all_data))
for col, data in zip(cols, all_data):
    s = data["summary"]
    if s.get("error"):
        col.error(f"{s['ticker']}: {s['error']}")
    else:
        render_regime_card(col, s, spot=data.get("spot"))

st.divider()

# ── Cross-asset overview ──────────────────────────────────────────────────────
clean = [d["summary"] for d in all_data if not d["summary"].get("error")]
if clean:
    st.markdown('<div class="sec">Cross-Asset Overview</div>', unsafe_allow_html=True)
    fig = plot_overview(clean)
    st.pyplot(fig)
    plt.close(fig)
    st.divider()

# ── Per-ticker detail — full width charts, stacked ────────────────────────────
st.markdown('<div class="sec">Per-Ticker Detail</div>', unsafe_allow_html=True)
for data in all_data:
    s = data["summary"]
    ticker = s["ticker"]
    if s.get("error"):
        continue
    regime = s.get("gamma_regime", "neutral")
    with st.expander(f"{ticker}  ·  {regime.upper()}", expanded=True):
        zgl = s.get("zero_gamma_level")
        cw = s.get("call_wall")
        pw = s.get("put_wall")
        summary_df = pd.DataFrame([{
            "Spot": f"{data['spot']:,.2f}" if data.get("spot") else "—",
            "Net GEX": f"{(s.get('net_gex') or 0) / _B:+.2f}B",
            "VEX": f"{(s.get('net_vex') or 0) / _B:+.2f}B",
            "CHEX": f"{(s.get('net_chex') or 0) / _B:+.2f}B",
            "Zero-γ": f"{zgl:.2f}" if zgl is not None else "—",
            "Call Wall": f"{cw:.0f}" if cw is not None else "—",
            "Put Wall": f"{pw:.0f}" if pw is not None else "—",
        }])
        st.dataframe(summary_df, hide_index=True, use_container_width=True)

        fig = plot_strike_gex(data["s_df"], data["spot"], ticker, s)
        st.pyplot(fig)
        plt.close(fig)

        fig = plot_gamma_profile(data["p_df"], data["spot"], ticker, s)
        st.pyplot(fig)
        plt.close(fig)
