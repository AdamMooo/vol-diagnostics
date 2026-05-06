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

TICKERS = ["SPY", "QQQ", "IWM", "NVDA", "TSLA", "AAPL", "XLF", "GLD", "TLT"]

_B = 1e9

plt.rcParams.update({
    "figure.figsize": (13, 5),
    "figure.dpi": 100,
    "figure.facecolor": "none",
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
    padding-bottom: 5px; margin-bottom: 8px; margin-top: 18px;
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
.rc-obs { font-size: 0.72rem; opacity: 0.70; margin-top: 10px; line-height: 1.5; }

.badge {
    display: inline-block; font-size: 0.58rem; font-weight: 700;
    letter-spacing: 0.1em; text-transform: uppercase;
    padding: 2px 8px; border-radius: 3px; margin-top: 8px;
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


def _derive_observations(summary: dict, spot: float, streak: int | None) -> list[str]:
    """Compute factual observations from the data — no opinions, no action items."""
    obs = []
    zgl = summary.get("zero_gamma_level")
    if zgl and spot:
        diff = spot - zgl
        pct = diff / zgl * 100
        direction = "above" if diff > 0 else "below"
        obs.append(f"Spot {abs(diff):.1f} pts {direction} zero-gamma ({abs(pct):.1f}%)")

    cw = summary.get("call_wall")
    pw = summary.get("put_wall")
    if cw and pw:
        spread = cw - pw
        obs.append(f"GEX range {pw:.0f}–{cw:.0f} ({spread:.0f} pts wide)")

    if streak and streak > 1:
        regime = summary.get("gamma_regime", "")
        obs.append(f"{regime.capitalize()} gamma for {streak} consecutive sessions")

    net_vex = summary.get("net_vex")
    net_gex = summary.get("net_gex")
    if net_vex is not None and net_gex and abs(net_gex) > 0:
        ratio = net_vex / net_gex
        if abs(ratio) > 0.3:
            obs.append(f"VEX/GEX ratio {ratio:.2f} — vanna flow material relative to gamma")

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


def render_regime_card(col, summary: dict, spot: float | None = None, streak: int | None = None) -> None:
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

    obs = _derive_observations(summary, spot or 0, streak)
    obs_html = "".join(f"<div>{o}</div>" for o in obs)

    col.markdown(f"""
<div class="rc" style="background:{bg};border-left-color:{color};">
  <div class="rc-ticker" style="color:{color};">{ticker}</div>
  <div class="rc-regime" style="color:{color};">{regime}</div>
  <div class="rc-grid">
    <span class="rc-k">Spot</span>        <span class="rc-v">{spot_str}</span>
    <span class="rc-k">Net GEX</span>     <span class="rc-v">{net_gex_b:+.2f}B</span>
    <span class="rc-k">VEX</span>         <span class="rc-v">{net_vex_b:+.2f}B</span>
    <span class="rc-k">&Delta;-flow</span> <span class="rc-v">{df_str}</span>
    <span class="rc-k">Zero-&gamma;</span> <span class="rc-v">{zgl_str}</span>
  </div>
  <div class="rc-obs">{obs_html}</div>
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
    st.caption("CBOE delayed · 15-min lag")

st.markdown("## GEX Dashboard")
st.caption(f"Dealer gamma exposure · CBOE chains · {datetime.now().strftime('%A %B %d, %Y').replace(' 0', ' ')}")

if not selected:
    st.info("Select at least one ticker in the sidebar.")
    st.stop()

# ── Fetch all tickers ──────────────────────────────────────────────────────────
all_data: list[dict] = []
errors: list[str] = []

fetch_cols = st.columns(len(selected))
for i, ticker in enumerate(selected):
    with fetch_cols[i]:
        with st.spinner(ticker):
            if i > 0:
                time.sleep(0.2)
            try:
                all_data.append(fetch_ticker(ticker))
            except Exception as exc:
                errors.append(f"{ticker}: {exc}")

for err in errors:
    st.error(err)

if not all_data:
    st.warning("No data loaded.")
    st.stop()

# ── Regime grid ───────────────────────────────────────────────────────────────
st.markdown('<div class="sec">Regime Summary</div>', unsafe_allow_html=True)

n_cols = min(len(all_data), 5)
rows = [all_data[i:i+n_cols] for i in range(0, len(all_data), n_cols)]
for row in rows:
    cols = st.columns(n_cols)
    for col, data in zip(cols, row):
        s = data["summary"]
        if s.get("error"):
            col.error(f"{s['ticker']}: {s['error']}")
        else:
            hist = _load_history_cached(s["ticker"], days=30)
            streak = _compute_streak(hist, s.get("gamma_regime", "neutral"))
            render_regime_card(col, s, spot=data.get("spot"), streak=streak)

# ── Cross-asset overview ───────────────────────────────────────────────────────
clean_summaries = [d["summary"] for d in all_data if not d["summary"].get("error")]
if len(clean_summaries) > 1:
    st.markdown('<div class="sec">Cross-Asset GEX</div>', unsafe_allow_html=True)
    fig = plot_overview(clean_summaries)
    st.pyplot(fig)
    plt.close(fig)

# ── Per-ticker detail ──────────────────────────────────────────────────────────
st.markdown('<div class="sec">Detail</div>', unsafe_allow_html=True)

for data in all_data:
    s = data["summary"]
    ticker = s["ticker"]
    if s.get("error"):
        continue

    regime = s.get("gamma_regime", "neutral")
    zgl = s.get("zero_gamma_level")
    cw = s.get("call_wall")
    pw = s.get("put_wall")
    spot = data.get("spot")

    with st.expander(f"{ticker}  ·  {regime.upper()}", expanded=False):
        # Key metrics row
        metrics = {
            "Spot": f"{spot:,.2f}" if spot else "—",
            "Net GEX": f"{(s.get('net_gex') or 0)/_B:+.2f}B",
            "VEX": f"{(s.get('net_vex') or 0)/_B:+.2f}B",
            "CHEX": f"{(s.get('net_chex') or 0)/_B:+.2f}B",
            "Zero-γ": f"{zgl:.2f}" if zgl is not None else "—",
            "Call Wall": f"{cw:.0f}" if cw is not None else "—",
            "Put Wall": f"{pw:.0f}" if pw is not None else "—",
        }
        st.dataframe(pd.DataFrame([metrics]), hide_index=True, use_container_width=True)

        # Charts side by side
        c1, c2 = st.columns([3, 2])
        with c1:
            fig = plot_strike_gex(data["s_df"], spot, ticker, s)
            st.pyplot(fig)
            plt.close(fig)
        with c2:
            fig = plot_gamma_profile(data["p_df"], spot, ticker, s)
            st.pyplot(fig)
            plt.close(fig)

        # Historical context — ZGL vs spot trend
        hist30 = _load_history_cached(ticker, days=30)
        if not hist30.empty:
            st.markdown("**ZGL vs Spot — 30 sessions**")
            chart_df = hist30.sort_values("date")
            fig, ax = plt.subplots(figsize=(12, 3))
            ax.plot(chart_df["date"], chart_df["zero_gamma_level"], label="Zero-γ", linewidth=1.5)
            ax.plot(chart_df["date"], chart_df["spot"], label="Spot", linewidth=1.2, linestyle="--")
            ax.legend(fontsize=8)
            fig.autofmt_xdate()
            fig.tight_layout()
            st.pyplot(fig)
            plt.close(fig)

            # Regime persistence table
            counts = hist30["gamma_regime"].value_counts().reset_index()
            counts.columns = ["Regime", "Sessions"]
            counts["% Days"] = (counts["Sessions"] / counts["Sessions"].sum() * 100).round(1).astype(str) + "%"
            st.dataframe(counts, hide_index=True, use_container_width=True)
