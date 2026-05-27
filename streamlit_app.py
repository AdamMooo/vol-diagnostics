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
    plot_vol_surface, plot_iv_change_surface,
    plot_skew_cross_ticker, plot_skew_term_structure,
    plot_skew_25d_current, plot_term_structure, plot_carry_vrp,
)
from scipy.stats import percentileofscore
from gex.surface_history import load_surface_snapshot, list_available_dates
from gex.report import REGIME_COLOR

INDEX_TICKERS = ["SPY", "QQQ", "IWM"]

_B = 1e9

st.set_page_config(
    page_title="Vol Diagnostics",
    page_icon="assets/gamma-icon-lg.png",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _check_password() -> bool:
    if st.session_state.get("authenticated"):
        return True
    try:
        expected = st.secrets.get("PASSWORD", "")
    except Exception:
        expected = ""
    if not expected:
        return True  # no password configured — open access
    st.markdown("## GEX Dashboard")
    pwd = st.text_input("Password", type="password", placeholder="Enter password")
    if pwd == expected:
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
    cw = summary.get("call_wall")
    pw = summary.get("put_wall")
    if cw is not None and pw is not None:
        obs.append(f"Range {pw:.0f}–{cw:.0f}")

    pct_chg = summary.get("price_change_pct")
    if pct_chg is not None:
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
    color = REGIME_COLOR[sign]
    bg = _SIGN_RGBA.get(sign, "rgba(127,140,141,0.12)")
    net_gex_b = (summary.get("net_gex") or 0) / _B
    zgl = summary.get("zero_gamma_level")
    zgl_str = f"{zgl:.1f}" if zgl is not None else "—"
    spot_str = f"{spot:,.2f}" if spot else "—"
    iv30 = summary.get("iv30")
    iv30_str = f"{iv30:.1f}%" if iv30 else "—"
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
    <span class="rc-k">&gamma;-flip</span>  <span class="rc-v">{zgl_str}</span>
    <span class="rc-k">Skew 25&Delta;</span>  <span class="rc-v">{skew_str}</span>
    <span class="rc-k">IV30</span>           <span class="rc-v">{iv30_str}</span>
  </div>
  <div class="rc-obs">{obs_html}</div>
</div>
""", unsafe_allow_html=True)


def render_regime_cards(tickers: list[str], all_data: dict[str, dict],
                        n_cols: int = 3) -> None:
    data_list = [all_data[t] for t in tickers if t in all_data
                 and not all_data[t]["summary"].get("error")]
    if not data_list:
        st.info("No data loaded.")
        return
    rows = [data_list[i:i + n_cols] for i in range(0, len(data_list), n_cols)]
    for row in rows:
        cols = st.columns(n_cols)
        for col, data in zip(cols, row):
            render_regime_card(col, data["summary"], spot=data.get("spot"))


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
  <span>{_top_date}  ·  CBOE delayed, 15-min lag  ·  OI T-1 (OCC standard)</span>
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
    render_regime_cards(sel_index, all_data)

    tab_surface, tab_skew, tab_term, tab_flow = st.tabs(
        ["Surface", "Skew", "Term Structure", "Flow Context"]
    )

    # ── Surface ──────────────────────────────────────────────────────────────
    with tab_surface:
        sub_today, sub_change = st.tabs(["Today", "∆ Change"])

        with sub_today:
            for ticker in selected_all:
                if ticker not in all_data:
                    continue
                data = all_data[ticker]
                surface_df = data.get("surface_df")
                spot = data.get("spot")
                if surface_df is not None and not surface_df.empty:
                    st.plotly_chart(
                        plot_vol_surface(surface_df, ticker, spot=spot),
                        use_container_width=True,
                    )
                else:
                    st.caption(f"{ticker}: insufficient data for surface.")

        with sub_change:
            for ticker in selected_all:
                if ticker not in all_data:
                    continue
                data = all_data[ticker]
                surface_df_today = data.get("surface_df")
                spot_today = data.get("spot")

                available = list_available_dates(ticker)
                if not available:
                    st.caption(
                        f"{ticker}: no historical snapshots yet — "
                        "accumulates from `run_daily` runs forward."
                    )
                    continue

                prior_date = st.selectbox(
                    f"{ticker} — compare against",
                    options=available,
                    format_func=lambda d: d.strftime("%b %d, %Y"),
                    key=f"surface_prior_{ticker}",
                )
                surface_df_prior, spot_prior = load_surface_snapshot(ticker, prior_date)
                if spot_prior is None:
                    spot_prior = spot_today  # fallback if snapshot predates spot column

                if surface_df_today is not None and not surface_df_today.empty:
                    st.plotly_chart(
                        plot_iv_change_surface(
                            surface_df_today, surface_df_prior,
                            ticker, spot_today, spot_prior,
                            label_prior=prior_date.strftime("%b %d"),
                        ),
                        use_container_width=True,
                    )
                    st.caption(
                        f"DTE range is bounded by the intersection of today's and "
                        f"{prior_date.strftime('%b %d')}'s data — if the surface is "
                        "narrower than today's, the prior snapshot's front expiry has rolled off."
                    )
                else:
                    st.caption(f"{ticker}: insufficient live data for comparison.")

    # ── Skew ─────────────────────────────────────────────────────────────────
    with tab_skew:
        # Cross-ticker comparison — most actionable view when ≥2 tickers loaded
        loaded_tickers = [t for t in selected_all if t in all_data]
        if len(loaded_tickers) >= 2:
            skew_by_ticker = {
                t: all_data[t].get("skew") or {}
                for t in loaded_tickers
            }
            st.plotly_chart(
                plot_skew_cross_ticker(skew_by_ticker),
                use_container_width=True,
            )
            st.caption(
                "25Δ risk reversal = put wing IV − call wing IV. "
                "Higher = market paying more for downside protection. "
                "Divergence across tickers signals where stress is localised."
            )
            st.divider()

        # Per-ticker detail
        cols_skew = st.columns(len(loaded_tickers)) if len(loaded_tickers) > 1 else [st]
        for col, ticker in zip(cols_skew, loaded_tickers):
            data = all_data[ticker]
            skew_data = data.get("skew") or {}
            front = skew_data.get("front_month")
            second = skew_data.get("second_month")

            with col:
                st.plotly_chart(
                    plot_skew_25d_current(skew_data, ticker),
                    use_container_width=True,
                )

                # Metrics with historical percentile context
                hist30 = _load_history_cached(ticker, days=config.HISTORY_DAYS)
                skew_series = (
                    hist30.dropna(subset=["front_skew"])["front_skew"].tolist()
                    if not hist30.empty and "front_skew" in hist30.columns
                    else []
                )

                if front or second:
                    m1, m2 = st.columns(2)
                    with m1:
                        if front:
                            st.metric(
                                f"Front ({front['dte']:.0f} DTE)",
                                f"{front['skew']:+.1f}pp",
                                help="25Δ put IV − 25Δ call IV (symmetric risk reversal)",
                            )
                            if len(skew_series) >= 5:
                                pct = int(percentileofscore(skew_series, front["skew"]))
                                st.caption(f"{pct}th %ile vs {len(skew_series)}-session history")
                        else:
                            st.caption("Front month: insufficient chain data")
                    with m2:
                        if second:
                            st.metric(
                                f"2nd ({second['dte']:.0f} DTE)",
                                f"{second['skew']:+.1f}pp",
                                help="25Δ put IV − 25Δ call IV (symmetric risk reversal)",
                            )
                        else:
                            st.caption("Second month: insufficient chain data")

                # Skew term structure: per-expiry 25Δ RR across the curve
                skew_df = data.get("skew_df")
                if skew_df is not None and not skew_df.empty:
                    st.plotly_chart(
                        plot_skew_term_structure(skew_df, ticker),
                        use_container_width=True,
                    )

                # Rolling skew history
                if hist30.empty:
                    st.caption("No history yet — accumulates from `gex.run_daily` runs.")
                else:
                    chart_df = hist30.sort_values("date")
                    if "front_skew" in chart_df.columns and chart_df["front_skew"].notna().any():
                        skew_hist = chart_df.dropna(subset=["front_skew"])
                        skew_fig = go.Figure()
                        skew_fig.add_trace(go.Scatter(
                            x=skew_hist["date"],
                            y=skew_hist["front_skew"],
                            mode="lines+markers",
                            line=dict(color="#f59e0b", width=1.5),
                            marker=dict(size=5),
                            hovertemplate="%{x|%b %d}<br>Skew: %{y:+.2f}pp<extra></extra>",
                        ))
                        skew_fig.add_hline(
                            y=0, line_color="rgba(255,255,255,0.15)", line_width=0.8,
                        )
                        skew_fig.update_layout(
                            template="plotly_dark",
                            title=f"25Δ RR history — {config.HISTORY_DAYS} sessions",
                            height=240,
                            yaxis_title="Skew (pp)",
                            yaxis_ticksuffix="pp",
                            margin=dict(t=40, b=30, l=60, r=20),
                            showlegend=False,
                        )
                        st.plotly_chart(skew_fig, use_container_width=True)
                    else:
                        st.caption("Skew history empty — accumulates from `gex.run_daily` forward.")

    # ── Term Structure ────────────────────────────────────────────────────────
    with tab_term:
        cols_term = st.columns(len(loaded_tickers)) if len(loaded_tickers) > 1 else [st]
        for col, ticker in zip(cols_term, loaded_tickers):
            data = all_data[ticker]
            ts = data.get("term_structure") or {}
            front_iv = ts.get("front_atm_iv")
            back_iv = ts.get("back_atm_iv")
            with col:
                st.plotly_chart(
                    plot_term_structure(ts, ticker),
                    use_container_width=True,
                )

                # Front/back spread with interpretation
                if front_iv is not None and back_iv is not None:
                    spread = front_iv - back_iv
                    if spread > 2.0:
                        interp = (
                            f"Near-term premium elevated (+{spread:.1f}pp) — "
                            "front-month options carry a premium vs back month. "
                            "Likely event or macro risk priced in near term."
                        )
                    elif spread < -2.0:
                        interp = (
                            f"Normal carry ({spread:.1f}pp) — "
                            "term structure upward-sloping. "
                            "Near-term options cheaper; carry favours selling short-dated vol."
                        )
                    else:
                        interp = (
                            f"Term structure flat (spread {spread:+.1f}pp) — "
                            "little carry advantage across expirations."
                        )
                    st.caption(interp)
                elif ts.get("classification"):
                    st.caption(f"Shape: {ts['classification']}")

                # IV30 percentile vs history
                hist_ts = _load_history_cached(ticker, days=config.HISTORY_DAYS)
                if not hist_ts.empty and "iv30" in hist_ts.columns:
                    iv30_series = hist_ts.dropna(subset=["iv30"])["iv30"].tolist()
                    summary_iv30 = all_data[ticker]["summary"].get("iv30")
                    if len(iv30_series) >= 5 and summary_iv30 is not None:
                        pct = int(percentileofscore(iv30_series, summary_iv30))
                        st.caption(
                            f"IV30 {summary_iv30:.1f}% — "
                            f"{pct}th %ile vs {len(iv30_series)}-session history"
                        )

                # VRP: IV30 vs RV20 — shows the premium currently being sold
                iv30_val = data["summary"].get("iv30")
                rv20 = data.get("rv20")
                vrp = data.get("vrp")
                if iv30_val is not None or rv20 is not None:
                    st.plotly_chart(
                        plot_carry_vrp(
                            iv30_pct=iv30_val,
                            rv20_pct=(rv20 * 100) if rv20 is not None else None,
                            vrp_pp=(vrp * 100) if vrp is not None else None,
                            ticker=ticker,
                        ),
                        use_container_width=True,
                    )

    # ── Flow Context ──────────────────────────────────────────────────────────
    with tab_flow:
        st.markdown(
            "### Microstructure / Execution Context — model-based, not market prices",
            unsafe_allow_html=False,
        )
        st.caption(
            "GEX assumes dealers are net short all options (Garleanu, Pedersen & Poteshman 2009). "
            "Sign and order of magnitude are informative; absolute levels are vendor-dependent."
        )
        for ticker in selected_all:
            if ticker not in all_data:
                continue
            data = all_data[ticker]
            s = data["summary"]
            spot = data.get("spot")
            c1, c2 = st.columns([3, 2])
            with c1:
                st.plotly_chart(
                    plot_strike_gex(data["s_df"], spot, ticker, s),
                    use_container_width=True,
                )
            with c2:
                st.plotly_chart(
                    plot_gamma_profile(data["p_df"], spot, ticker, s),
                    use_container_width=True,
                )
            hist30 = _load_history_cached(ticker, days=config.HISTORY_DAYS)
            if not hist30.empty:
                chart_df = hist30.sort_values("date")
                zgl_fig = go.Figure()
                zgl_fig.add_trace(go.Scatter(
                    x=chart_df["date"],
                    y=chart_df["zero_gamma_level"],
                    name="γ-flip",
                    line=dict(color="#f59e0b", width=1.5),
                ))
                zgl_fig.add_trace(go.Scatter(
                    x=chart_df["date"],
                    y=chart_df["spot"],
                    name="Spot",
                    line=dict(color="white", width=1.2, dash="dash"),
                ))
                zgl_fig.update_layout(
                    template="plotly_dark",
                    title=f"γ-flip vs Spot — {config.HISTORY_DAYS} sessions",
                    height=260,
                    margin=dict(t=40, b=30, l=60, r=20),
                    legend=dict(orientation="h", y=1.15),
                )
                st.plotly_chart(zgl_fig, use_container_width=True)

# ── Methodology & assumptions (consolidated) ──────────────────────────────────
with st.expander("Methodology & Assumptions  ·  read before trading off this", expanded=False):
    st.markdown(
        """
**Data source.** Free CBOE delayed quotes JSON (no auth, no OPRA tick feed).
Spot, IV, and chain mids are ~15-min delayed. **OI reflects prior session close**
(OCC settles contracts end-of-day; this is true for all data vendors including
Bloomberg — no intraday OI update exists). Greeks (γ, Δ, vega, θ) come from
**CBOE's American option pricing model** (accounts for early exercise + dividends);
we do not recompute them locally.

**Risk-free rate.** Live 3-month T-bill (`^IRX` via yfinance) at session start;
falls back to 0.05 if the fetch fails. Used only in the γ-flip BS gamma sweep.

**Filters.** Min OI = 100. IV ≤ 300% (drops obvious bad quotes). 0DTE excluded
(`DTE ≥ 1`) — same-day options expire at zero gamma at close, would distort the
overnight book picture. Vol surface: ±15% of spot displayed (±22% collected), ≤180 DTE
for liquid-region focus.

**Defensible metrics** (academic backing in `research/methodology-deep-review.md`):

- **Net GEX** — `Γ × OI × 100 × S² × 0.01`, calls positive, puts negative.
  SpotGamma/perfiliev/GEXboard convention; derivable from Gatheral/Bergomi
  dollar-gamma. Sign and order of magnitude are load-bearing; absolute levels are
  methodology-dependent across vendors.
- **Hedge Sh / $1** — `Γ_net × OI × 100` = aggregate shares dealers must trade per
  $1 spot move to stay delta-neutral. Mechanism well-supported in Egebjerg &
  Kokholm (2024).
- **Skew (25Δ)** — IV(25Δ put) − IV(25Δ call) (symmetric risk reversal) for nearest expiry ≥7 DTE, in pp.
  **Xing, Zhang & Zhao (2010, JFQA)**: steeper skew predicts subsequent
  underperformance — 10.9% annual alpha. Only metric here with direct
  peer-reviewed predictive backing.
- **IV Surface** — CBOE chain IVs plotted on a % OTM axis `(K/S−1)×100`.
  **OTM convention**: put IV for K<S, call IV for K≥S — the industry standard
  (Gatheral §2.1). OTM options are more liquid and avoid American early-exercise
  distortion. Coarse 25×20 linear interpolation grid; NaN left as holes where
  chain data is absent (no nearest-neighbour fill). Raw chain quotes overlaid as
  scatter so data density is visible. GEX context available in Flow Context tab.
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
