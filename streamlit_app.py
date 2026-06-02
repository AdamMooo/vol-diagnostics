from __future__ import annotations

import time
from datetime import datetime, date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from gex import config
from gex.card_model import CardField, build_card_fields
from gex.validation import load_prior_snapshot
from gex.compute import compute_ticker
from gex.analytics import (
    plot_gamma_profile,
    plot_vol_surface, plot_iv_change_surface,
    plot_oi_by_strike,
)
from scipy.stats import percentileofscore
from gex.surface_history import (
    load_surface_snapshot, list_available_dates, nth_trading_day_back,
)
from gex.surface_evolution import load_evolution
from gex.vol_metrics import vrp_headline

INDEX_TICKERS = ["SPY", "QQQ", "IWM"]

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



def _trust_readout_strings(surface_diag: dict | None) -> tuple[str, str, str]:
    """Raw-number surface trust readout (VALID-06): Coverage / Fit RMS / Max resid.
    No thresholds, no badge — the PM reads the number and judges; '—' for missing/nan.
    (Surface PASS/FAIL flags stay headless per D-11 — intentionally not shown here.)"""
    import math
    d = surface_diag or {}

    def _num(key, suffix, prec):
        v = d.get(key)
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return "—"
        return f"{v:.{prec}f}{suffix}"

    return (
        f"Coverage {_num('coverage_pct', '%', 0)}",
        f"Fit RMS {_num('fit_rmse', 'pp', 1)}",
        f"Max {_num('max_resid', 'pp', 1)}",
    )


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
    """Accent bar / background reflect the sign of net gex; no categorical regime label."""
    ticker = summary["ticker"]
    sign = _sign_key(summary.get("net_gex"))
    _palette_sign = {"positive": config.PALETTE["positive"], "negative": config.PALETTE["negative"], "zero": config.PALETTE["neutral"]}
    color = _palette_sign[sign]
    bg = _SIGN_RGBA.get(sign, "rgba(127,140,141,0.12)")

    prior_row = load_prior_snapshot(ticker=ticker, before_date=date.today())
    fields = build_card_fields(today_summary=summary, prior_summary=prior_row)
    grid_html = "".join(
        f'<span class="rc-k">{f.label}</span>'
        f'<span class="rc-v">{f.value}</span>'
        for f in fields
    )

    col.markdown(f"""
<div class="rc" style="background:{bg};border-left-color:{color};">
  <div class="rc-ticker" style="color:{color};">{ticker}</div>
  <div class="rc-grid">{grid_html}</div>
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

    tab_surface, tab_evolution, tab_positioning = st.tabs(
        ["Surface", "Evolution", "Positioning"]
    )

    # ── Surface ──────────────────────────────────────────────────────────────
    with tab_surface:
        sub_today, sub_compare = st.tabs(["Today", "Compare"])

        with sub_today:
            for ticker in selected_all:
                if ticker not in all_data:
                    continue
                data = all_data[ticker]
                surface_df = data.get("surface_df")
                spot = data.get("spot")
                if surface_df is not None and not surface_df.empty:
                    cov, rms, mx = _trust_readout_strings(data.get("surface_diag"))
                    st.markdown(f"**{ticker}**  ·  {cov}  ·  {rms}  ·  {mx}")
                    st.plotly_chart(
                        plot_vol_surface(surface_df, ticker, spot=spot),
                        width='stretch',
                    )
                else:
                    st.caption(f"{ticker}: insufficient data for surface.")

        with sub_compare:
            _horizon_options = {
                "live": 0,
                "1d": 1,
                "5d": 5,
                "10d": 10,
                "20d": 20,
                "30d": 30,
                "60d": 60,
            }
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

                # Determine which horizon keys have enough stored history
                anchor = available[0]
                available_keys = ["live"]
                for label, n in _horizon_options.items():
                    if label == "live":
                        continue
                    if nth_trading_day_back(ticker, anchor, n) is not None:
                        available_keys.append(label)

                # Default: live vs 5d (or first available if 5d not ready)
                default_b = "5d" if "5d" in available_keys else (available_keys[1] if len(available_keys) > 1 else "live")

                col_a, col_b = st.columns([1, 1])
                with col_a:
                    sel_a = st.selectbox(
                        f"{ticker} — Date A",
                        options=available_keys,
                        index=0,
                        key=f"compare_a_{ticker}",
                    )
                with col_b:
                    default_b_idx = available_keys.index(default_b) if default_b in available_keys else 0
                    sel_b = st.selectbox(
                        f"{ticker} — Date B",
                        options=available_keys,
                        index=default_b_idx,
                        key=f"compare_b_{ticker}",
                    )

                # Resolve A
                if sel_a == "live":
                    surface_df_a = surface_df_today
                    spot_a = spot_today
                    label_a = "live"
                else:
                    n_a = _horizon_options[sel_a]
                    date_a = nth_trading_day_back(ticker, anchor, n_a)
                    if date_a is None:
                        st.caption(f"{ticker}: insufficient history for {sel_a}")
                        continue
                    surface_df_a, spot_a = load_surface_snapshot(ticker, date_a)
                    if spot_a is None:
                        spot_a = spot_today
                    label_a = date_a.strftime("%b %d")

                # Resolve B
                if sel_b == "live":
                    surface_df_b = surface_df_today
                    spot_b = spot_today
                    label_b = "live"
                else:
                    n_b = _horizon_options[sel_b]
                    date_b = nth_trading_day_back(ticker, anchor, n_b)
                    if date_b is None:
                        st.caption(f"{ticker}: insufficient history for {sel_b}")
                        continue
                    surface_df_b, spot_b = load_surface_snapshot(ticker, date_b)
                    if spot_b is None:
                        spot_b = spot_today
                    label_b = date_b.strftime("%b %d")

                if surface_df_a is not None and not surface_df_a.empty:
                    st.plotly_chart(
                        plot_iv_change_surface(
                            surface_df_a, surface_df_b,
                            ticker, spot_a, spot_b,
                            label_prior=label_b,
                        ),
                        width='stretch',
                    )
                    st.caption(
                        f"DTE range is bounded by the intersection of {label_a}'s and "
                        f"{label_b}'s data — if the surface is narrower than today's, "
                        "the prior snapshot's front expiry has rolled off."
                    )
                else:
                    st.caption(f"{ticker}: insufficient data for comparison.")

    # ── Evolution ─────────────────────────────────────────────────────────────
    with tab_evolution:
        for ticker in selected_all:
            if ticker not in all_data:
                continue
            data = all_data[ticker]
            s = data["summary"]
            spot = data.get("spot")

            st.markdown(f'<div class="sec">{ticker} · VRP · Skew · Term</div>', unsafe_allow_html=True)

            hist = _load_history_cached(ticker, days=config.HISTORY_DAYS)

            # VRP headline
            iv30_summary = s.get("iv30")  # percentage points (e.g. 18.5)
            rv20_raw = data.get("rv20")   # decimal fraction (e.g. 0.158)
            vrp_raw = data.get("vrp")     # decimal fraction (e.g. 0.027)

            iv30_pct_val = iv30_summary
            rv20_pct_val = (rv20_raw * 100) if rv20_raw is not None else None
            vrp_pp_val = (vrp_raw * 100) if vrp_raw is not None else None

            # Compute percentile from history
            vrp_percentile = None
            if not hist.empty and "vrp" in hist.columns and vrp_pp_val is not None:
                vrp_hist_series = hist.dropna(subset=["vrp"])["vrp"] * 100
                if len(vrp_hist_series) >= 5:
                    vrp_percentile = int(percentileofscore(vrp_hist_series.tolist(), vrp_pp_val))

            vrp_plain = vrp_headline(iv30_pct_val, rv20_pct_val, vrp_pp_val, vrp_percentile)

            vrp_display = f"{vrp_pp_val:+.1f}pp" if vrp_pp_val is not None else "—"
            m_col, _ = st.columns([1, 2])
            with m_col:
                st.metric(
                    label="VRP (IV30 − RV20)",
                    value=vrp_display,
                    help="Volatility risk premium: implied minus realized vol. Positive = options pricing more vol than realized.",
                )
            st.caption(vrp_plain)

            # VRP sparkline
            if not hist.empty and "vrp" in hist.columns:
                vrp_chart_df = hist.dropna(subset=["vrp"]).sort_values("date")
                if not vrp_chart_df.empty:
                    vrp_fig = go.Figure()
                    vrp_fig.add_trace(go.Scatter(
                        x=vrp_chart_df["date"],
                        y=vrp_chart_df["vrp"] * 100,
                        mode="lines",
                        line=dict(color=config.PALETTE["accent"], width=1.5),
                        hovertemplate="%{x|%b %d}<br>VRP: %{y:+.2f}pp<extra></extra>",
                    ))
                    vrp_fig.add_hline(y=0, line_color="rgba(255,255,255,0.15)", line_width=0.8)
                    vrp_fig.update_layout(
                        template="plotly_dark",
                        title=f"{ticker} · VRP — {config.HISTORY_DAYS}-session",
                        height=160,
                        margin=dict(t=30, b=20, l=50, r=10),
                        yaxis_title="VRP (pp)",
                        showlegend=False,
                    )
                    st.plotly_chart(vrp_fig, width='stretch')

            # Scalar strip
            front_skew_val = s.get("front_skew")
            ts = data.get("term_structure") or {}
            front_iv = ts.get("front_atm_iv")
            back_iv = ts.get("back_atm_iv")
            term_spread_val = (front_iv - back_iv) if (front_iv is not None and back_iv is not None) else None

            skew_series = []
            term_series = []
            if not hist.empty:
                if "front_skew" in hist.columns:
                    skew_series = hist.dropna(subset=["front_skew"])["front_skew"].tolist()

            sc1, sc2 = st.columns(2)
            with sc1:
                skew_display = f"{front_skew_val:+.1f}pp" if front_skew_val is not None else "—"
                st.metric(
                    label="Front Skew (25Δ RR)",
                    value=skew_display,
                    help="25Δ put IV − 25Δ call IV for front expiry ≥7 DTE.",
                )
                if len(skew_series) >= 5 and front_skew_val is not None:
                    skew_pct = int(percentileofscore(skew_series, front_skew_val))
                    st.caption(f"{skew_pct}th %ile vs {len(skew_series)}-session history")
            with sc2:
                term_display = f"{term_spread_val:+.1f}pp" if term_spread_val is not None else "—"
                st.metric(
                    label="Term Spread (front − back ATM IV)",
                    value=term_display,
                    help="Front-month ATM IV minus back-month ATM IV.",
                )

        st.markdown('<div class="sec">Surface Evolution</div>', unsafe_allow_html=True)
        selected_horizon = st.radio(
            "Horizon", options=[5, 10, 20], index=0, horizontal=True, key="evol_horizon",
        )

        _evol_ticker_colors = {
            "SPY": config.PALETTE["call"],
            "QQQ": config.PALETTE["accent"],
            "IWM": config.PALETTE["positive"],
        }

        # Load evolution data for all three tickers
        evol_by_ticker: dict[str, pd.DataFrame] = {}
        for ticker in INDEX_TICKERS:
            evol_by_ticker[ticker] = load_evolution(ticker, horizon=selected_horizon, days=60)

        all_empty = all(df.empty for df in evol_by_ticker.values())

        if all_empty:
            st.caption("No evolution data yet — accumulates from `run_daily` runs forward.")
        else:
            for metric in ["level", "rms", "skew_change", "term_change"]:
                fig = go.Figure()
                any_data = False
                for ticker in INDEX_TICKERS:
                    df = evol_by_ticker[ticker]
                    if df.empty or metric not in df.columns:
                        continue
                    metric_df = df.dropna(subset=[metric]).sort_values("date")
                    if metric_df.empty:
                        continue
                    any_data = True
                    fig.add_trace(go.Scatter(
                        x=metric_df["date"],
                        y=metric_df[metric],
                        name=ticker,
                        mode="lines",
                        line=dict(color=_evol_ticker_colors.get(ticker, config.PALETTE["neutral"]), width=1.5),
                        hovertemplate=f"%{{x|%b %d}}<br>{ticker} {metric}: %{{y:+.3f}}<extra></extra>",
                    ))
                if any_data:
                    fig.add_hline(y=0, line_color="rgba(255,255,255,0.15)", line_width=0.8)
                    fig.update_layout(
                        template="plotly_dark",
                        title=f"{metric} ({selected_horizon}d horizon)",
                        height=220,
                        margin=dict(t=40, b=30, l=65, r=20),
                        yaxis_title=f"{metric} (pp)",
                        legend=dict(orientation="h", y=1.15),
                    )
                    st.plotly_chart(fig, width='stretch')

            # Per-ticker cold-start captions for tickers with no data
            for ticker in INDEX_TICKERS:
                if evol_by_ticker[ticker].empty:
                    st.caption(f"{ticker}: no evolution data yet — accumulates from `run_daily` runs forward.")

    # ── Positioning ───────────────────────────────────────────────────────────
    with tab_positioning:
        st.markdown(
            "OI is assumption-free — no dealer model needed. "
            "GEX-derived levels (γ-flip, walls) assume dealers net short all options "
            "(Garleanu et al. 2009) and are labelled as model constructs.",
            unsafe_allow_html=False,
        )

        for ticker in selected_all:
            if ticker not in all_data:
                continue
            data = all_data[ticker]
            s = data["summary"]
            spot = data.get("spot")

            st.markdown(f"**{ticker}**")

            c1, c2 = st.columns([3, 2])
            with c1:
                st.plotly_chart(
                    plot_oi_by_strike(data["s_df"], spot, ticker, s),
                    width='stretch',
                )
                st.caption(
                    "Call OI = blue, Put OI = red. "
                    "Call wall / put wall are GEX-defined (model · assumes dealers net short)."
                )
            with c2:
                hist42 = _load_history_cached(ticker, days=42)
                if not hist42.empty:
                    chart_df = hist42.sort_values("date")
                    levels_fig = go.Figure()

                    spot_df = chart_df.dropna(subset=["spot"])
                    if not spot_df.empty:
                        levels_fig.add_trace(go.Scatter(
                            x=spot_df["date"],
                            y=spot_df["spot"],
                            name="Spot",
                            mode="lines",
                            line=dict(color="white", dash="dot", width=1.2),
                            hovertemplate="%{x|%b %d}<br>Spot: %{y:,.0f}<extra></extra>",
                        ))

                    zgl_df = chart_df.dropna(subset=["zero_gamma_level"])
                    if not zgl_df.empty:
                        levels_fig.add_trace(go.Scatter(
                            x=zgl_df["date"],
                            y=zgl_df["zero_gamma_level"],
                            name="γ-flip",
                            mode="lines",
                            line=dict(color=config.PALETTE["accent"], width=1.5),
                            hovertemplate="%{x|%b %d}<br>γ-flip: %{y:,.0f}<extra></extra>",
                        ))

                    cw_df = chart_df.dropna(subset=["call_wall"])
                    if not cw_df.empty:
                        levels_fig.add_trace(go.Scatter(
                            x=cw_df["date"],
                            y=cw_df["call_wall"],
                            name="call wall",
                            mode="lines",
                            line=dict(color=config.PALETTE["call"], dash="dot", width=1.0),
                            hovertemplate="%{x|%b %d}<br>call wall: %{y:,.0f}<extra></extra>",
                        ))

                    pw_df = chart_df.dropna(subset=["put_wall"])
                    if not pw_df.empty:
                        levels_fig.add_trace(go.Scatter(
                            x=pw_df["date"],
                            y=pw_df["put_wall"],
                            name="put wall",
                            mode="lines",
                            line=dict(color=config.PALETTE["put"], dash="dot", width=1.0),
                            hovertemplate="%{x|%b %d}<br>put wall: %{y:,.0f}<extra></extra>",
                        ))

                    levels_fig.update_layout(
                        template="plotly_dark",
                        title=f"{ticker} · Spot vs Levels — 42 sessions",
                        height=260,
                        margin=dict(t=40, b=30, l=60, r=20),
                        legend=dict(orientation="h", y=1.15),
                    )
                    st.plotly_chart(levels_fig, width='stretch')
                else:
                    st.caption(
                        f"{ticker}: no history yet — "
                        "accumulates from `run_daily` runs forward."
                    )

            with st.expander("γ-flip & walls — model derivation", expanded=False):
                st.plotly_chart(
                    plot_gamma_profile(data["p_df"], spot, ticker, s),
                    width='stretch',
                )
                st.markdown(
                    "**Gamma profile.** Net GEX swept across ±15% spot range in 200 steps "
                    "(Black-Scholes gamma, dealer net-short assumption). The profile shows "
                    "how aggregate dealer hedging pressure varies with spot. "
                    "**Zero-gamma level (γ-flip):** strike where cumulative net GEX crosses zero — "
                    "by convention, above it dealers are long gamma (stabilising); below it, short gamma (amplifying). "
                    "**Walls:** strikes with maximum one-sided GEX concentration. "
                    "**Model assumption:** dealers net short all options (Garleanu, Pedersen & Poteshman 2009)."
                )

        st.caption(
            "IWM: OI data is the more reliable signal — "
            "GEX-derived levels may be less reliable due to thinner dealer positioning in small-caps."
        )

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
  distortion. Coarse 25×20 linear interpolation grid; convex-hull coverage mask applied —
  unsupported cells (outside the interpolation support region) rendered as honest NaN holes.
  Coverage % and fit RMS visible in the Surface tab. Raw chain quotes overlaid as
  scatter so data density is visible. GEX context available in the Positioning tab.
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
