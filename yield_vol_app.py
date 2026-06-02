"""
Purpose Yield ETF underlying vol diagnostics.
Run: streamlit run yield_vol_app.py
"""
from __future__ import annotations

from datetime import datetime

import streamlit as st

from gex import config
from gex.compute import compute_ticker
from gex.analytics import plot_vol_surface, plot_iv_change_surface
from gex.surface_history import load_surface_snapshot, list_available_dates, nth_trading_day_back

# CBOE ticker → Purpose ETF display label
# JPM is the underlying for the "Yield Shares (JPYS) Purpose ETF"
YIELD_TICKERS: dict[str, str] = {
    "AMD":   "AMD (AMD) Yield Shares Purpose ETF",
    "META":  "META (META) Yield Shares Purpose ETF",
    "AAPL":  "Apple (AAPL) Yield Shares Purpose ETF",
    "AMZN":  "Amazon (AMZN) Yield Shares Purpose ETF",
    "TSLA":  "Tesla (TSLA) Yield Shares Purpose ETF",
    "BRK":   "Berkshire Hathaway (BRK) Yield Shares Purpose ETF",
    "GOOGL": "Alphabet (GOOGL) Yield Shares Purpose ETF",
    "MSFT":  "Microsoft (MSFT) Yield Shares Purpose ETF",
    "NVDA":  "NVIDIA (NVDA) Yield Shares Purpose ETF",
    "AVGO":  "Broadcom (AVGO) Yield Shares Purpose ETF",
    "COIN":  "Coinbase (COIN) Yield Shares Purpose ETF",
    "COST":  "Costco (COST) Yield Shares Purpose ETF",
    "JPM":   "Yield Shares (JPYS) Purpose ETF",
    "NFLX":  "Netflix (NFLX) Yield Shares Purpose ETF",
    "PLTR":  "Palantir (PLTR) Yield Shares Purpose ETF",
    "UNH":   "UnitedHealth Group (UNH) Yield Shares Purpose ETF",
}

_HORIZON_OPTIONS = {"1d": 1, "5d": 5, "10d": 10, "20d": 20, "30d": 30}

st.set_page_config(
    page_title="Purpose Yield — Vol Diagnostics",
    page_icon="assets/gamma-icon-lg.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

_CSS = """
<style>
.block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 1400px; }
.metric-row { display: flex; gap: 32px; margin-bottom: 18px; flex-wrap: wrap; }
.metric-box { display: flex; flex-direction: column; }
.metric-label {
    font-size: 0.62rem; font-weight: 700; letter-spacing: 0.12em;
    text-transform: uppercase; color: #64748b;
}
.metric-value { font-size: 1.35rem; font-weight: 700; font-variant-numeric: tabular-nums; }
.metric-sub { font-size: 0.72rem; color: #94a3b8; margin-top: 1px; }
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)


@st.cache_data(ttl=config.CACHE_TTL_TICKER, show_spinner=False)
def _fetch(ticker: str) -> dict:
    return compute_ticker(ticker)


def _metric(label: str, value: str, sub: str = "") -> str:
    sub_html = f'<div class="metric-sub">{sub}</div>' if sub else ""
    return (
        f'<div class="metric-box">'
        f'<div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div>'
        f'{sub_html}</div>'
    )


def _fmt_iv(v) -> str:
    return f"{v:.1f}%" if v else "—"


def _fmt_rr(v) -> str:
    if v is None or not isinstance(v, (int, float)):
        return "—"
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.1f}pp"


# ── Sidebar ───────────────────────────────────────────────────────────────────

ticker_keys = list(YIELD_TICKERS.keys())
ticker_labels = list(YIELD_TICKERS.values())

with st.sidebar:
    sel_label = st.selectbox("Underlying", ticker_labels, index=0)
    sel_ticker = ticker_keys[ticker_labels.index(sel_label)]

    if st.button("Refresh", use_container_width=True):
        _fetch.clear()

    st.caption(f"{datetime.now().strftime('%a %b %d, %Y')} · CBOE delayed, 15-min lag")

# ── Fetch ─────────────────────────────────────────────────────────────────────

with st.spinner(f"Loading {sel_ticker} chain from CBOE..."):
    try:
        data = _fetch(sel_ticker)
    except Exception as exc:
        st.error(f"Failed to load {sel_ticker}: {exc}")
        st.stop()

summary = data["summary"]
spot = data["spot"]
surface_df = data.get("surface_df")
surface_diag = data.get("surface_diag") or {}
skew = data.get("skew")
rv20 = data.get("rv20")

# ── Header metrics ─────────────────────────────────────────────────────────────

iv30 = summary.get("iv30")
pct_chg = summary.get("price_change_pct")
front_rr = (skew.get("front_month") or {}).get("skew") if skew else None

chg_color = "#22c55e" if (pct_chg or 0) >= 0 else "#ef4444"
chg_str = f"{pct_chg:+.2f}%" if pct_chg is not None else "—"
spot_sub = f'<span style="color:{chg_color};font-weight:600;">{chg_str} today</span>'

metrics_html = (
    '<div class="metric-row">'
    + _metric("Spot", f"${spot:,.2f}", spot_sub)
    + _metric("IV30", _fmt_iv(iv30))
    + _metric("25Δ RR (front)", _fmt_rr(front_rr))
    + _metric("RV20", _fmt_iv(rv20 * 100 if rv20 else None))
    + "</div>"
)

st.markdown(f"### {sel_label}")
st.markdown(metrics_html, unsafe_allow_html=True)

cov = surface_diag.get("coverage_pct")
rms = surface_diag.get("fit_rmse")
mx = surface_diag.get("max_resid")
trust_parts = []
if cov is not None:
    trust_parts.append(f"Coverage {cov:.0f}%")
if rms is not None:
    trust_parts.append(f"Fit RMS {rms:.1f}pp")
if mx is not None:
    trust_parts.append(f"Max {mx:.1f}pp")
if trust_parts:
    st.caption("  ·  ".join(trust_parts))

# ── Tabs ───────────────────────────────────────────────────────────────────────

tab_surface, tab_compare = st.tabs(["Surface", "Compare (∆IV)"])

with tab_surface:
    if surface_df is not None and not surface_df.empty:
        st.plotly_chart(
            plot_vol_surface(surface_df, sel_ticker, spot=spot),
            width="stretch",
        )
    else:
        st.info(f"{sel_ticker}: insufficient data for vol surface.")

with tab_compare:
    available = list_available_dates(sel_ticker)
    if not available:
        st.info(
            f"No historical snapshots for {sel_ticker} yet — "
            "accumulates from `run_daily_yield` runs forward."
        )
    else:
        anchor = available[0]
        available_keys = [k for k, n in _HORIZON_OPTIONS.items()
                          if nth_trading_day_back(sel_ticker, anchor, n) is not None]

        if not available_keys:
            st.info("Not enough history yet — check back after more daily runs.")
        else:
            sel_horizon = st.radio(
                "Compare to",
                available_keys,
                horizontal=True,
                format_func=lambda x: f"{x} ago",
            )

            n_back = _HORIZON_OPTIONS[sel_horizon]
            prior_date = nth_trading_day_back(sel_ticker, anchor, n_back)
            if prior_date is None:
                st.warning(f"No snapshot {n_back} trading days back.")
            elif surface_df is None or surface_df.empty:
                st.info("No surface data for today.")
            else:
                prior_surface_df, prior_spot = load_surface_snapshot(sel_ticker, prior_date)
                if prior_surface_df.empty:
                    st.warning(f"Snapshot for {prior_date} is empty.")
                else:
                    if prior_spot is None:
                        prior_spot = spot
                    fig = plot_iv_change_surface(
                        df_today=surface_df,
                        df_prior=prior_surface_df,
                        ticker=sel_ticker,
                        spot_today=spot,
                        spot_prior=prior_spot,
                        label_prior=str(prior_date),
                    )
                    st.plotly_chart(fig, width="stretch")
