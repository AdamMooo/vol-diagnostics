from __future__ import annotations

import time
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from gex import config
from gex.compute import compute_ticker
from gex.analytics import (
    plot_strike_gex, plot_gamma_profile,
    plot_vol_surface, plot_skew_term_structure,
)
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
.block-container { padding-top: 2.5rem; padding-bottom: 2rem; max-width: 1500px; }

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

.top-bar {
    display: flex; justify-content: space-between; align-items: baseline;
    font-size: 0.78rem; opacity: 0.55; letter-spacing: 0.04em;
    padding-bottom: 10px; margin-bottom: 22px;
    border-bottom: 1px solid rgba(148,163,184,0.15);
}
.top-bar-tickers { font-weight: 600; }
</style>
"""


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


@st.cache_data(ttl=config.CACHE_TTL_TICKER, show_spinner=False)
def fetch_ticker(ticker: str) -> dict:
    return compute_ticker(ticker)


@st.cache_data(ttl=config.CACHE_TTL_HISTORY, show_spinner=False)
def _load_history_cached(ticker: str, days: int = config.HISTORY_DAYS) -> pd.DataFrame:
    from gex.validation import load_history
    return load_history(ticker, days)


def _sign_key(net_gex: float | None) -> str:
    if net_gex is None or net_gex == 0:
        return "zero"
    return "positive" if net_gex > 0 else "negative"


def render_regime_card(col, summary: dict, spot: float | None = None) -> None:
    """Card content — only outputs we can defend with our lives. Accent bar /
    background reflect the sign of net gex; no categorical regime label."""
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
    skew = summary.get("front_skew")
    skew_str = f"{skew:+.1f}pp" if skew is not None else "—"

    obs = _derive_observations(summary, spot or 0)
    obs_html = "".join(f"<div>{o}</div>" for o in obs)

    col.markdown(f"""
<div class="rc" style="background:{bg};border-left-color:{color};">
  <div class="rc-ticker" style="color:{color};">{ticker}</div>
  <div class="rc-grid">
    <span class="rc-k">Spot</span>           <span class="rc-v">{spot_str}</span>
    <span class="rc-k">Net GEX</span>        <span class="rc-v">{net_gex_b:+.2f}B</span>
    <span class="rc-k">Hedge Sh / $1</span> <span class="rc-v">{df_str}</span>
    <span class="rc-k">&gamma;-flip</span>  <span class="rc-v">{zgl_str}</span>
    <span class="rc-k">Skew 25&Delta;</span>  <span class="rc-v">{skew_str}</span>
    <span class="rc-k">IV30</span>           <span class="rc-v">{iv30:.1f}%</span>
  </div>
  <div class="rc-obs">{obs_html}</div>
</div>
""", unsafe_allow_html=True)


def render_section(tickers: list[str], all_data: dict[str, dict],
                   n_cols: int = 5) -> None:
    data_list = [all_data[t] for t in tickers if t in all_data and not all_data[t]["summary"].get("error")]

    if not data_list:
        st.info("No data loaded for this section.")
        return

    rows = [data_list[i:i + n_cols] for i in range(0, len(data_list), n_cols)]
    for row in rows:
        cols = st.columns(n_cols)
        for col, data in zip(cols, row):
            render_regime_card(col, data["summary"], spot=data.get("spot"))

    for data in data_list:
        s = data["summary"]
        ticker = s["ticker"]
        spot = data.get("spot")
        iv30 = s.get("iv30", 0.0)

        net_b = (s.get("net_gex") or 0) / _B
        spot_str = f"${spot:,.2f}" if spot else "—"
        label = f"{ticker}   ·   {spot_str}   ·   Net {net_b:+.2f}B"

        with st.expander(label, expanded=False):
            tab_strikes, tab_vol, tab_history = st.tabs(["Strikes", "Vol", "History"])

            with tab_strikes:
                c1, c2 = st.columns([3, 2])
                with c1:
                    st.plotly_chart(plot_strike_gex(data["s_df"], spot, ticker, s),
                                    use_container_width=True)
                with c2:
                    st.plotly_chart(plot_gamma_profile(data["p_df"], spot, ticker, s),
                                    use_container_width=True)

            with tab_vol:
                surface_df = data.get("surface_df")
                if surface_df is not None and not surface_df.empty:
                    st.plotly_chart(
                        plot_vol_surface(
                            surface_df, ticker, spot=spot, iv30=iv30,
                            gamma_flip=s.get("zero_gamma_level"),
                            call_wall=s.get("call_wall"),
                            put_wall=s.get("put_wall"),
                        ),
                        use_container_width=True,
                    )
                strike_slope = s.get("strike_slope")
                term_slope = s.get("term_slope")
                if strike_slope is not None or term_slope is not None:
                    slope_hist = _load_history_cached(ticker, days=90)
                    _ss_hist = (slope_hist["strike_slope"].dropna()
                                if "strike_slope" in slope_hist.columns else pd.Series(dtype=float))
                    _ts_hist = (slope_hist["term_slope"].dropna()
                                if "term_slope" in slope_hist.columns else pd.Series(dtype=float))

                    def _pctile_label(val: float, hist: pd.Series, name: str) -> str:
                        n = len(hist)
                        if n >= 10:
                            pct = int((hist < val).mean() * 100)
                            return f"{val:+.1f}  ({pct}th pctile, {n}d)"
                        return f"{val:+.1f}  ({n}d, building context)"

                    sm1, sm2, _ = st.columns([1, 1, 2])
                    with sm1:
                        if strike_slope is not None:
                            st.metric(
                                "Strike Slope (pp / 10% K/S)",
                                _pctile_label(strike_slope, _ss_hist, "strike_slope"),
                                help=(
                                    "∂IV/∂(log K) at front expiry (≤45 DTE), scaled to pp per 10% K/S move. "
                                    "Negative = put skew dominant (normal). More negative = steeper. "
                                    "Percentile rank vs trailing 90 sessions once N≥10. "
                                    "Model construct — no peer-reviewed predictive backing."
                                ),
                            )
                    with sm2:
                        if term_slope is not None:
                            st.metric(
                                "Term Slope (pp / 30 DTE)",
                                _pctile_label(term_slope, _ts_hist, "term_slope"),
                                help=(
                                    "∂IV/∂(DTE) at ATM (|log K/S| < 5%), scaled to pp per 30 DTE. "
                                    "Positive = contango (normal). Negative = backwardation (short-end stress/event premium). "
                                    "Percentile rank vs trailing 90 sessions once N≥10. "
                                    "Model construct — no peer-reviewed predictive backing."
                                ),
                            )

                skew_df = data.get("skew_df")
                if skew_df is not None and not skew_df.empty:
                    st.plotly_chart(
                        plot_skew_term_structure(skew_df, ticker),
                        use_container_width=True,
                    )

            with tab_history:
                hist30 = _load_history_cached(ticker, days=config.HISTORY_DAYS)
                if hist30.empty:
                    st.caption("No history yet — daily snapshots accumulate from `gex.run_daily`.")
                else:
                    chart_df = hist30.sort_values("date")
                    zgl_fig = go.Figure()
                    zgl_fig.add_trace(go.Scatter(
                        x=chart_df["date"], y=chart_df["zero_gamma_level"],
                        name="γ-flip", line=dict(color="#f59e0b", width=1.5),
                    ))
                    zgl_fig.add_trace(go.Scatter(
                        x=chart_df["date"], y=chart_df["spot"],
                        name="Spot", line=dict(color="white", width=1.2, dash="dash"),
                    ))
                    zgl_fig.update_layout(
                        template="plotly_dark",
                        title=f"γ-flip vs Spot — {config.HISTORY_DAYS} sessions",
                        height=260,
                        margin=dict(t=40, b=30, l=60, r=20),
                        legend=dict(orientation="h", y=1.15),
                    )
                    st.plotly_chart(zgl_fig, use_container_width=True)

                    if "front_skew" in chart_df.columns and chart_df["front_skew"].notna().any():
                        skew_hist = chart_df.dropna(subset=["front_skew"])
                        skew_fig = go.Figure()
                        skew_fig.add_trace(go.Scatter(
                            x=skew_hist["date"], y=skew_hist["front_skew"],
                            name="Skew (25Δ)",
                            mode="lines+markers",
                            line=dict(color="#f59e0b", width=1.5),
                            marker=dict(size=5),
                            hovertemplate="%{x|%b %d}<br>Skew: %{y:+.2f}pp<extra></extra>",
                        ))
                        skew_fig.add_hline(y=0, line_color="rgba(255,255,255,0.15)", line_width=0.8)
                        skew_fig.update_layout(
                            template="plotly_dark",
                            title=f"Skew (25Δ put − 50Δ call) — {config.HISTORY_DAYS} sessions",
                            height=240,
                            yaxis_title="Skew (pp)",
                            yaxis_ticksuffix="pp",
                            margin=dict(t=40, b=30, l=60, r=20),
                            showlegend=False,
                        )
                        st.plotly_chart(skew_fig, use_container_width=True)
                    else:
                        st.caption(
                            "Skew history empty — accumulates from today's `gex.run_daily` run forward. "
                            "Existing snapshots predate the skew metric and will show NaN."
                        )


# ── Boot ──────────────────────────────────────────────────────────────────────

st.markdown(_CSS, unsafe_allow_html=True)

with st.sidebar:
    sel_index = st.multiselect(
        "Tickers", INDEX_TICKERS, default=INDEX_TICKERS, key="sel_index",
    )
    if st.button("Refresh", use_container_width=True):
        fetch_ticker.clear()
        st.rerun()
    st.caption(f"{datetime.now().strftime('%a %b %d, %Y')} · CBOE delayed, 15-min lag")

selected_all = sel_index
if not selected_all:
    st.info("Select at least one ticker in the sidebar.")
    st.stop()

_top_tickers = " · ".join(selected_all)
_top_date = datetime.now().strftime("%a %b %d, %Y").replace(" 0", " ")
st.markdown(
    f"""<div class="top-bar">
  <span class="top-bar-tickers">{_top_tickers}</span>
  <span>{_top_date}  ·  CBOE delayed, 15-min lag  ·  OI as of prior session</span>
</div>""",
    unsafe_allow_html=True,
)

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

if sel_index:
    render_section(sel_index, all_data, n_cols=min(len(sel_index), 3))

# ── Methodology & assumptions (consolidated) ──────────────────────────────────
with st.expander("Methodology & Assumptions  ·  read before trading off this", expanded=False):
    st.markdown(
        """
**Data source.** Free CBOE delayed quotes JSON (no auth, no OPRA tick feed).
Spot, IV, and chain mids are ~15-min delayed. **OI is T-1** — settled at prior
session close, does not update intraday. Greeks (γ, Δ, vega, θ) come from
**CBOE's American option pricing model** (accounts for early exercise + dividends);
we do not recompute them locally.

**Risk-free rate.** Live 3-month T-bill (`^IRX` via yfinance) at session start;
falls back to 0.05 if the fetch fails. Used only in the γ-flip BS gamma sweep.

**Filters.** Min OI = 100. IV ≤ 300% (drops obvious bad quotes). 0DTE excluded
(`DTE ≥ 1`) — same-day options expire at zero gamma at close, would distort the
overnight book picture. Vol surface additionally filtered to ±18% of spot, ≤180 DTE
for liquid-region focus.

**Defensible metrics** (academic backing in `research/methodology-deep-review.md`):

- **Net GEX** — `Γ × OI × 100 × S² × 0.01`, calls positive, puts negative.
  SpotGamma/perfiliev/GEXboard convention; derivable from Gatheral/Bergomi
  dollar-gamma. Sign and order of magnitude are load-bearing; absolute levels are
  methodology-dependent across vendors.
- **Hedge Sh / $1** — `Γ_net × OI × 100` = aggregate shares dealers must trade per
  $1 spot move to stay delta-neutral. Mechanism well-supported in Egebjerg &
  Kokholm (2024).
- **Skew (25Δ)** — IV(25Δ put) − IV(50Δ call) for nearest expiry ≥7 DTE, in pp.
  **Xing, Zhang & Zhao (2010, JFQA)**: steeper skew predicts subsequent
  underperformance — 10.9% annual alpha. Only metric here with direct
  peer-reviewed predictive backing.
- **IV Surface** — CBOE chain IVs in log-moneyness `log(K/S)` (academic convention
  per Cont & da Fonseca 2002, Gatheral). **OTM convention**: put IV for K<S,
  call IV for K≥S — the industry standard (Gatheral §2.1). OTM options are
  more liquid and avoid American early-exercise distortion. Linear interpolation
  onto a 50×40 grid (no overshoot artifacts). Annotated with **γ-flip, call
  wall, and put wall meridians** so the smile shape can be read against the
  dealer positioning state — the cross-product between vol structure and GEX.
- **IV30** — CBOE-computed 30-day constant-maturity vol, taken directly from
  the delayed payload.

**Model constructs (interpret carefully).**

- **γ-flip (formerly "Zero-γ Level")** — spot at which cumulative net GEX would
  cross zero, computed by BS gamma sweep ±15% in 200 steps. **Zero peer-reviewed
  papers test this as a price level.** Defensible only as a property of the
  current model output, not as a price target or support/resistance.
- **Call Wall / Put Wall** — strikes with max one-sided GEX. Trader lore as
  support/resistance; **no peer-reviewed backtest**. Defensible only as
  "where the largest gamma-weighted OI concentration sits today."

**Dealer positioning assumption.** GEX assumes dealers are net short all options
(retail buys, dealers sell). **Garleanu, Pedersen & Poteshman (2009, RFS)**
confirms empirically for index options in aggregate. Can be wrong at individual
strikes with covered-call programs, vol sellers, or institutional flow dominant.
Hu, Kirilova, Muravyev & Ryu (2023) further note only ~10% of OMMs continuously
delta-hedge — the assumed continuous rebalancing is itself a simplification.

**Universe.** SPY / QQQ / IWM only. Single-name extension would require
revisiting the dealer positioning assumption per ticker.

**No realized-vol attribution.** This is a positioning monitor, not a forecaster.
No event study, base rate, or backtest is shown — the live history is too short
for inference.
        """
    )
