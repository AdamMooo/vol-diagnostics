from __future__ import annotations

from datetime import datetime, date
from pathlib import Path

import pandas as pd
import pandas_market_calendars as mcal
import pytz
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env", encoding="utf-8-sig", override=True)

from engine import config
from engine.surface.surface_interactive import (
    build_surface_payload, render_surface_html,
    build_diff_payload, render_diff_html,
    build_movie_payload, render_movie_html,
)
from engine.report.card_model import (
    format_oi_impact, _ordinal, build_card_fields,
)
from engine.data.oi_history import prior_oi_snapshot, load_oi_history
from engine.compute import compute_ticker
from engine.gex.analytics import (
    plot_vol_surface, plot_iv_change_surface,
)
from scipy.stats import percentileofscore
from engine.data.surface_history import (
    load_surface_snapshot, list_available_dates, nth_trading_day_back,
)
from engine.surface.surface_evolution import load_evolution
from engine.session import latest_session, DATA_CUTOFF_HOUR, DATA_CUTOFF_MIN


INDEX_TICKERS = ["SPY", "QQQ", "IWM"]

ET = pytz.timezone("America/New_York")

st.set_page_config(
    page_title="Index Vol Diagnostics",
    page_icon="assets/gamma-icon-lg.png",
    layout="wide",
    initial_sidebar_state="expanded",
)


_CSS = """
<style>
.block-container { padding-top: 2.5rem; padding-bottom: 2rem; max-width: 1500px; }

.sec {
    font-size: 0.62rem; font-weight: 700; letter-spacing: 0.14em;
    text-transform: uppercase; color: #64748b;
    border-bottom: 1px solid rgba(148,163,184,0.25);
    padding-bottom: 5px; margin-bottom: 10px; margin-top: 22px;
}

.top-bar {
    display: flex; justify-content: space-between; align-items: baseline;
    font-size: 0.78rem; opacity: 0.55; letter-spacing: 0.04em;
    padding-bottom: 10px; margin-bottom: 22px;
    border-bottom: 1px solid rgba(148,163,184,0.15);
}
.top-bar-tickers { font-weight: 600; }

.fresh {
    font-size: 0.74rem; font-weight: 600; letter-spacing: 0.03em;
    border-radius: 6px; padding: 6px 12px; margin: -12px 0 18px 0;
    border-left: 4px solid;
}
.fresh-bad { background: rgba(234,88,12,0.12);   border-color: #ea580c; color: #ea580c; }

/* Freshness in the current-data case shrinks to a compact inline dot — a stall is
   loud (.fresh-bad above), a healthy feed is quiet. */
.fresh-dot {
    font-size: 0.72rem; color: #64748b; letter-spacing: 0.02em;
    margin: -8px 0 14px 0;
}
.fresh-dot .dot { color: #16a34a; font-size: 0.85rem; vertical-align: middle; }

/* Net-GEX state chip — a sign indicator, not a ranked row. Color set inline. */
.gex-chip {
    display: inline-block; font-size: 0.74rem; font-weight: 600;
    letter-spacing: 0.02em; border-radius: 6px; padding: 3px 11px;
    margin: 0 6px 10px 0; border: 1px solid;
}
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
def _fetch_shared_ticker_inputs() -> tuple[float, float | None]:
    """Risk-free rate + VVIX are identical across SPY/QQQ/IWM (~4-5s yfinance call for
    the rate) — fetch once here instead of once per ticker inside compute_ticker()."""
    from engine.compute import _get_risk_free_rate
    from engine.vol.vol_metrics import compute_vvix_level
    return _get_risk_free_rate(), compute_vvix_level()


@st.cache_data(ttl=config.CACHE_TTL_TICKER, show_spinner=False)
def fetch_ticker(ticker: str, risk_free_rate: float, vvix: float | None) -> dict:
    # skip_cv=True: cv_rmse is never displayed on the dashboard, only persisted to
    # the snapshot history by run_daily — skipping it here cuts ~12s/ticker of
    # cross-validation RBF refits that would otherwise be wasted work.
    return compute_ticker(ticker, risk_free_rate=risk_free_rate, vvix=vvix, skip_cv=True)


@st.cache_data(ttl=config.CACHE_TTL_HISTORY, show_spinner=False)
def _load_history_cached(ticker: str, days: int = config.HISTORY_DAYS) -> pd.DataFrame:
    from engine.data.validation import load_history
    return load_history(ticker, days)


@st.cache_data(ttl=config.CACHE_TTL_HISTORY, show_spinner="Building surface video…")
def _movie_payload_cached(ticker: str, mode: str = "level") -> dict | None:
    snaps = []
    for d in sorted(_available_dates_cached(ticker))[-config.SURFACE_MOVIE_MAX_SESSIONS:]:
        sdf, sp = load_surface_snapshot(ticker, d)
        if sdf is not None and not sdf.empty and sp is not None:
            snaps.append((d.strftime("%b %d"), sdf, sp))
    return build_movie_payload(snaps, ticker=ticker, mode=mode)


@st.cache_data(ttl=config.CACHE_TTL_HISTORY, show_spinner=False)
def _latest_evolution_row_cached(ticker: str) -> dict | None:
    evo = load_evolution(ticker, horizon=5, days=400)
    if evo.empty:
        return None
    cols = ["level", "rms", "skew_change", "term_change"]
    latest = evo.sort_values("date").tail(1)
    if latest.empty:
        return None
    row = latest.iloc[0]
    out = {k: row[k] if k in latest.columns else None for k in cols}
    return out


@st.cache_data(ttl=config.CACHE_TTL_HISTORY, show_spinner=False)
def _load_evolution_cached(ticker: str, horizon: int, days: int = 400) -> pd.DataFrame:
    return load_evolution(ticker, horizon=horizon, days=days)


@st.cache_data(ttl=config.CACHE_TTL_HISTORY, show_spinner=False)
def _prior_oi_cached(ticker: str, before_date: date) -> pd.DataFrame:
    return prior_oi_snapshot(ticker, before_date)


@st.cache_data(ttl=config.CACHE_TTL_HISTORY, show_spinner=False)
def _oi_history_cached(ticker: str, days: int) -> pd.DataFrame:
    return load_oi_history(ticker, days=days)


@st.cache_data(ttl=config.CACHE_TTL_HISTORY, show_spinner=False)
def _available_dates_cached(ticker: str) -> list:
    return list(list_available_dates(ticker))


@st.cache_data(ttl=config.CACHE_TTL_HISTORY, show_spinner=False)
def _prior_snapshot_cached(ticker: str, before_date: date) -> "pd.Series | None":
    from engine.data.validation import load_prior_snapshot
    return load_prior_snapshot(ticker=ticker, before_date=before_date)


def _evolution_largest_move_summary(metrics: dict | None) -> str:
    import math
    if not metrics:
        return "Largest move: — (history building)."

    defs = {
        "level": ("surface level", "rose", "fell"),
        "rms": ("surface dispersion", "widened", "compressed"),
        "skew_change": ("front skew", "steepened", "flattened"),
        "term_change": ("term slope", "steepened", "flattened"),
    }
    ranked: list[tuple[float, str, float]] = []
    for key in ("level", "rms", "skew_change", "term_change"):
        v = metrics.get(key)
        if v is None or (isinstance(v, float) and math.isnan(v)):
            continue
        ranked.append((abs(float(v)), key, float(v)))

    if not ranked:
        return "Largest move: — (history building)."

    _, key, value = max(ranked, key=lambda x: x[0])
    label, up_word, down_word = defs[key]
    direction = up_word if value >= 0 else down_word
    return f"Largest move: {label} {direction} ({value:+.2f}pp)."


def _net_gex_chip(summary: dict) -> str:
    """Net-GEX sign rendered as a compact state chip (NOT a ranked row).

    Reuses the exact net_gex sign→label→color logic the Positioning tab uses:
    net_gex >= 0 → Stabilizing (green), < 0 → Amplifying (red). Returns an HTML
    <span> for inline markdown; degrades to a muted em-dash chip when net_gex is
    absent (cold-start / errored summary)."""
    ticker = summary.get("ticker", "?")
    ng = summary.get("net_gex")
    if ng is None:
        return (
            f"<span class='gex-chip' style='border-color:#334155;color:#64748b;'>"
            f"{ticker} net-GEX —</span>"
        )
    sign = "Stabilizing" if ng >= 0 else "Amplifying"
    color = "#4ade80" if ng >= 0 else "#f87171"
    return (
        f"<span class='gex-chip' style='border-color:{color};color:{color};'>"
        f"{ticker} {sign} {ng / 1e9:+.2f}B</span>"
    )


def _regime_headline(s: dict) -> str:
    """One plain-English sentence: VRP premium band + dealer-gamma sign. The VRP
    band shows only when it cleared the credibility floor; the dealer clause is a
    move-MAGNITUDE statement, never direction (Baltussen 2021, Egebjerg 2024,
    Anderegg 2022 support the former, not the latter)."""
    vrp_pct, vrp_pct_n = s.get("vrp_pct"), s.get("vrp_pct_n")
    net_gex = s.get("net_gex")
    if vrp_pct is not None and (vrp_pct_n or 0) >= config.CARD_READ_MIN_SESSIONS:
        band = "rich" if vrp_pct >= 67 else "cheap" if vrp_pct <= 33 else "fair"
        premium = f"Premium {band} ({_ordinal(vrp_pct)} %ile)"
    else:
        premium = "Premium history building"
    if net_gex is None:
        return premium + "."
    if net_gex >= 0:
        return f"{premium}. Moves tend contained — a short-premium posture sits easier."
    return f"{premium}. Moves tend larger in either direction — size down, widen strikes."


def _hist_series(hist: pd.DataFrame, col: str) -> list | None:
    """Ascending, NaN-free value list for a metric sparkline (None if <2 points)."""
    if hist.empty or col not in hist.columns:
        return None
    ser = hist.sort_values("date")[col].dropna()
    return ser.tolist() if len(ser) >= 2 else None


def _iv30_5d_delta(hist: pd.DataFrame) -> str | None:
    """IV30 change over ~5 sessions, as a signed delta string (None if too short)."""
    if hist.empty or "iv30" not in hist.columns:
        return None
    ser = hist.sort_values("date")["iv30"].dropna()
    if len(ser) < 6:
        return None
    return f"{ser.iloc[-1] - ser.iloc[-6]:+.1f}pp 5d"


def _render_regime_cards(selected_all: list[str], all_data: dict[str, dict]) -> None:
    """Front-door per-ticker read: a plain-English headline sentence, then a
    bordered KPI row (VRP / IV30 / skew) with trend sparklines. VRP carries the
    rich/cheap color; IV/skew stay neutral. Full field detail is opt-in below.
    card_model.build_card_fields stays the single source shared with the email."""
    cols = st.columns(len(selected_all)) if len(selected_all) > 1 else [st.container()]
    for col, ticker in zip(cols, selected_all):
        data = all_data.get(ticker)
        if not data:
            continue
        s = data.get("summary") or {}
        with col:
            if s.get("error"):
                st.error(f"{ticker}: {s.get('error')}")
                continue

            spot = s.get("spot")
            day_pct = s.get("price_change_pct")
            day_str = f"&nbsp;&nbsp;{day_pct:+.2f}%" if day_pct is not None else ""
            spot_str = f"{spot:,.2f}" if spot is not None else "—"
            st.markdown(
                f"<div style='font-size:1.0rem;font-weight:700;'>{ticker}"
                f"<span style='font-weight:400;opacity:0.65;'>&nbsp;&nbsp;{spot_str}{day_str}"
                f"</span></div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div style='font-size:0.9rem;line-height:1.45;margin:6px 0 12px;'>"
                f"{_regime_headline(s)}</div>",
                unsafe_allow_html=True,
            )

            hist = _load_history_cached(ticker, days=config.HISTORY_DAYS)

            vrp = s.get("vrp")
            vrp_pct, vrp_pct_n = s.get("vrp_pct"), s.get("vrp_pct_n")
            if vrp_pct is not None and (vrp_pct_n or 0) >= config.CARD_READ_MIN_SESSIONS:
                vrp_delta = f"{_ordinal(vrp_pct)} %ile"
                vrp_color = "green" if vrp_pct >= 67 else "red" if vrp_pct <= 33 else "gray"
            else:
                vrp_delta, vrp_color = "building", "gray"

            skew = s.get("front_skew")
            skew_delta = (
                None if skew is None
                else "puts pricier" if skew > 0
                else "calls pricier" if skew < 0
                else "flat"
            )
            iv30 = s.get("iv30")

            with st.container(horizontal=True):
                st.metric(
                    "VRP",
                    f"{vrp:+.1f}pp" if vrp is not None else "—",
                    vrp_delta, delta_color=vrp_color, delta_arrow="off",
                    chart_data=_hist_series(hist, "vrp"), border=True,
                    help="IV − RV vol-point spread, ranked vs ~10yr CBOE vol-index history.",
                )
                st.metric(
                    "IV30",
                    f"{iv30:.1f}%" if iv30 else "—",
                    _iv30_5d_delta(hist), delta_color="gray",
                    chart_data=_hist_series(hist, "iv30"), border=True,
                    help="30-day at-the-money implied volatility.",
                )
                st.metric(
                    "Skew (25Δ)",
                    f"{skew:+.1f}pp" if skew is not None else "—",
                    skew_delta, delta_color="gray", delta_arrow="off",
                    chart_data=_hist_series(hist, "front_skew"), border=True,
                    help="25Δ put IV − call IV for the front expiry.",
                )

            em_pct = s.get("expected_move_pct")
            fly = s.get("butterfly")
            bits = []
            if em_pct is not None:
                bits.append(f"Expected move ±{em_pct:.1f}%")
            if fly is not None:
                bits.append(f"25Δ fly {fly:+.1f}pp")
            if bits:
                st.caption(" · ".join(bits))

            prior_row = _prior_snapshot_cached(ticker=ticker, before_date=date.today())
            fields = build_card_fields(today_summary=s, prior_summary=prior_row)
            with st.expander("All fields"):
                grid_html = "".join(
                    f"<span style='opacity:0.6;'>{f.label}</span>"
                    f"<span style='font-weight:600;text-align:right;"
                    f"font-variant-numeric:tabular-nums;'>{f.value}</span>"
                    for f in fields
                )
                st.markdown(
                    f"<div style='display:grid;grid-template-columns:auto 1fr;gap:3px 14px;"
                    f"font-size:0.74rem;'>{grid_html}</div>",
                    unsafe_allow_html=True,
                )


def _expected_latest_session(now_et: datetime) -> date:
    """Most recent NYSE session that should already be collected (post-close lens)."""
    return latest_session(now_et, DATA_CUTOFF_HOUR, DATA_CUTOFF_MIN)


def _sessions_missing(latest: date, expected: date) -> int:
    """NYSE trading days after `latest` up to and including `expected`."""
    if expected <= latest:
        return 0
    nyse = mcal.get_calendar("NYSE")
    sched = nyse.schedule(
        start_date=latest.strftime("%Y-%m-%d"),
        end_date=expected.strftime("%Y-%m-%d"),
    )
    return sum(1 for d in sched.index if d.date() > latest)


def _render_freshness_banner() -> None:
    """A missed daily CBOE collection is lost forever (no historical chain
    archive), so surface a stall loudly. Latest stored snapshot vs the NYSE
    calendar — green when current, amber when sessions are missing."""
    latest_per_ticker = [
        max(d) for t in INDEX_TICKERS if (d := _available_dates_cached(t))
    ]
    if not latest_per_ticker:
        st.markdown(
            '<div class="fresh fresh-bad">no stored snapshots found — '
            "daily collection has not run</div>",
            unsafe_allow_html=True,
        )
        return
    latest = min(latest_per_ticker)  # oldest of the per-ticker latests
    expected = _expected_latest_session(datetime.now(ET))
    missing = _sessions_missing(latest, expected)
    latest_str = latest.strftime("%a %b %d").replace(" 0", " ")
    if missing <= 0:
        st.markdown(
            f'<div class="fresh-dot"><span class="dot">●</span> '
            f"current through {latest_str}</div>",
            unsafe_allow_html=True,
        )
    else:
        plural = "s" if missing != 1 else ""
        st.markdown(
            f'<div class="fresh fresh-bad">data stale: last collection {latest_str} · '
            f"{missing} trading day{plural} missing</div>",
            unsafe_allow_html=True,
        )


def _methods_deep_markdown() -> str:
    return """
**Data and timing**
- Chains come from free CBOE delayed quotes JSON (~15-minute delay).
- OI is prior-session close (T-1) by market structure; there is no intraday OI tape.
- Greeks are from CBOE's American pricing model in the feed (not recomputed locally).

**Core definitions**
- **VRP:** CBOE index-vol close (VIX/VXN/RVX) minus `RV20×100` (yfinance closes).
- **Net GEX:** `Γ × OI × 100 × S² × 0.01`, calls positive, puts negative.
- **Skew (25Δ):** IV(25Δ put) − IV(25Δ call) for the nearest expiry ≥7 DTE.
- **Surface:** OTM convention (put IV for K<S, call IV for K≥S) on %OTM × DTE.

**Filters and scope**
- Min OI = 100, IV ≤ 300%, and 0DTE excluded (`DTE ≥ 1`).
- Positioning context is capped at ≤90 DTE (`config.GEX_MAX_DTE`).
- Universe is SPY / QQQ / IWM; Explore tickers are snapshot-only.

**Model constructs and caveats**
- Dealer-gamma **sign** drives only a move-size regime (a position-sizing input) — never a price level or a direction call. γ-flip and walls are not surfaced.
- Dealer net-short is an aggregate assumption that can fail at strike level.
- For single names it is weaker still — the Explore tab drops gamma entirely for raw OI.

Full citations and counter-evidence: `research/methodology-deep-review.md`.
    """


# ── Boot ──────────────────────────────────────────────────────────────────────

st.markdown(_CSS, unsafe_allow_html=True)

with st.sidebar:
    sel_index = st.multiselect(
        "Tickers", INDEX_TICKERS, default=INDEX_TICKERS, key="sel_index",
    )
    if st.button("Refresh", width="stretch"):
        st.cache_data.clear()
        st.rerun()
    st.caption(f"{datetime.now().strftime('%a %b %d, %Y')}")

    with st.popover("Methodology & assumptions", width="stretch"):
        st.markdown(
            "**Scope:** descriptive context for an option-writing program — "
            "no forecast, no direction call, no trade signal.\n\n"
            "**Evidence tiers used on this page**\n"
            "- **VRP (premium rich/cheap):** strong for IV > RV persistence; "
            "percentile is ranked on ~10 years of CBOE vol-index history.\n"
            "- **Skew (25Δ):** present-tense pricing tilt (puts vs calls), shown "
            "descriptively.\n"
            "- **Move-size regime (dealer-gamma sign):** moderate evidence for move "
            "**magnitude**, none for direction — used only as a position-sizing "
            "input, capped at ≤90 DTE.\n"
            "- **Open interest:** raw, prior-session (T-1) — assignment / pin-risk "
            "context, no dealer assumption.\n\n"
            "**Validation discipline:** a prior soft trade lean was removed after "
            "a null forward-return timing test (p=0.74)."
        )

    with st.expander("Full methodology & citations"):
        st.markdown(_methods_deep_markdown())

selected_all = sel_index
if not selected_all:
    st.info("Select at least one ticker in the sidebar.")
    st.stop()

_top_tickers = " · ".join(selected_all)
_top_date = datetime.now().strftime("%a %b %d, %Y").replace(" 0", " ")
st.markdown(
    f"""<div class="top-bar">
  <span class="top-bar-tickers">{_top_tickers}</span>
  <span>{_top_date}  ·  CBOE delayed, 15-min lag  ·  OI T-1</span>
</div>""",
    unsafe_allow_html=True,
)

_render_freshness_banner()

# ── Fetch all tickers ──────────────────────────────────────────────────────────
all_data: dict[str, dict] = {}
errors: list[str] = []

with st.spinner("Loading chains from CBOE..."):
    shared_rate, shared_vvix = _fetch_shared_ticker_inputs()
    # Sequential, not threaded: measured on the Oracle E2.1.Micro (1 vCPU) box —
    # threading made this slower (35.2s vs 26.4s sequential), since the GIL only
    # releases during network I/O and most of this pipeline's time is CPU-bound
    # (surface fitting, coherence diagnostics), which just fights over the one core.
    for ticker in selected_all:
        try:
            all_data[ticker] = fetch_ticker(ticker, shared_rate, shared_vvix)
        except Exception as exc:
            errors.append(f"{ticker}: {exc}")

for err in errors:
    st.error(err)

if not all_data:
    st.warning("No data loaded.")
    st.stop()


def _render_surface_momentum(selected_all: list[str], all_data: dict) -> None:
    """Trend-first momentum strip: 5d/10d/20d surface level change for the primary ticker.
    Horizons match the evolution engine (5/10/20); 1d excluded by design decision."""
    import math
    primary = selected_all[0] if selected_all else None
    if not primary or primary not in all_data:
        return

    horizons = [5, 10, 20]
    values: dict[int, float | None] = {}
    for h in horizons:
        evo = _load_evolution_cached(primary, horizon=h, days=400)
        if evo.empty or "level" not in evo.columns:
            values[h] = None
            continue
        latest = evo.dropna(subset=["level"]).sort_values("date").tail(1)
        values[h] = float(latest.iloc[0]["level"]) if not latest.empty else None

    filled = [(h, v) for h, v in values.items() if v is not None and not math.isnan(v)]
    if not filled:
        st.caption(f"{primary}: surface momentum builds as daily snapshots accumulate (need ≥5 sessions).")
        return

    rising = sum(1 for _, v in filled if v > 0)
    trend = "rising" if rising > len(filled) / 2 else "falling" if rising < len(filled) / 2 else "mixed"
    trend_color = "#f87171" if trend == "rising" else "#4ade80" if trend == "falling" else "#94a3b8"

    st.markdown(
        f"<span style='font-size:0.92rem;'><strong style='color:{trend_color};'>"
        f"Surface {trend}</strong> — {primary} level change across horizons</span>",
        unsafe_allow_html=True,
    )

    cols = st.columns(len(horizons))
    for col, h in zip(cols, horizons):
        v = values.get(h)
        if v is None:
            col.metric(f"{h}d", f"need {h}+ sessions")
        else:
            arrow = "↑" if v > 0.05 else "↓" if v < -0.05 else "—"
            col.metric(f"{h}d", f"{v:+.2f}pp {arrow}")


def _render_vanna_volga_metrics(selected_all: list[str], all_data: dict) -> None:
    """Surface deformation metrics: vanna (spot-vol correlation) and volga (vol-of-vol).
    Shows the second-order Greeks that describe how the surface responds to market shocks."""
    primary = selected_all[0] if selected_all else None
    if not primary or primary not in all_data:
        return

    data = all_data.get(primary)
    if not data:
        return

    greeks = data.get("second_order_greeks")
    if not greeks or "error" in greeks:
        return

    summary = greeks.get("deformation_summary", "")
    spot_vol = greeks.get("spot_vol_correlation_signal")
    vol_of_vol = greeks.get("vol_of_vol_magnitude")
    stability = greeks.get("surface_stability_metric")

    if spot_vol is None or vol_of_vol is None:
        return

    st.markdown("**Surface deformation: Second-order Greeks**")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(
            "Spot-Vol correlation",
            f"{spot_vol:+.4f}",
            "inverse" if spot_vol < -0.002 else "flat" if abs(spot_vol) <= 0.002 else "positive",
            delta_color="gray", delta_arrow="off",
            help="Vanna: δ(delta)/δ(vol). Negative = typical inverse spot-vol relationship (higher spot → lower vol)."
        )
    with c2:
        st.metric(
            "Vol-of-Vol magnitude",
            f"{vol_of_vol:.4f}",
            "high" if vol_of_vol > 0.015 else "moderate" if vol_of_vol > 0.005 else "low",
            delta_color="gray", delta_arrow="off",
            help="Volga: Convexity in the volatility dimension. Higher = market prices vol-of-vol risk."
        )
    with c3:
        if stability is not None:
            st.metric(
                "Surface stability",
                f"{stability:.3f}",
                "stable" if stability < 0.08 else "elevated",
                delta_color="gray", delta_arrow="off",
                help="RMS curvature. Lower = smoother, more stable surface."
            )

    if summary:
        st.caption(summary)


@st.fragment
def _surface_today_section(sel_tkr: str, all_data: dict) -> None:
    for ticker in [sel_tkr]:  # one heavy surface at a time (perf)
        if ticker not in all_data:
            continue
        data = all_data[ticker]
        surface_df = data.get("surface_df")
        spot = data.get("spot")
        if surface_df is not None and not surface_df.empty:
            cov, rms, mx = _trust_readout_strings(data.get("surface_diag"))
            st.markdown(f"**{ticker}**  ·  {cov}  ·  {rms}  ·  {mx}")
            payload = build_surface_payload(surface_df, spot, ticker=ticker)
            if payload is not None:
                # Interactive: 3D surface + mouse-driven smile/term slices.
                # components.html embeds client-side plotly.js (smooth hover).
                components.html(render_surface_html(payload), height=640, scrolling=False)
            else:
                st.plotly_chart(
                    plot_vol_surface(surface_df, ticker, spot=spot),
                    width='stretch',
                )
        else:
            st.caption(f"{ticker}: insufficient data for surface.")


@st.fragment
def _surface_compare_section(sel_tkr: str, all_data: dict) -> None:
    _horizon_options = {
        "live": 0,
        "1d": 1,
        "5d": 5,
        "10d": 10,
        "20d": 20,
        "30d": 30,
        "60d": 60,
    }
    for ticker in [sel_tkr]:  # one heavy surface at a time (perf)
        if ticker not in all_data:
            continue
        data = all_data[ticker]
        surface_df_today = data.get("surface_df")
        spot_today = data.get("spot")

        available = _available_dates_cached(ticker)
        if not available:
            st.caption(f"{ticker}: no stored snapshots yet.")
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
            label_a = anchor.strftime("%b %d") + " (live)"
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
            diff = build_diff_payload(
                surface_df_a, spot_a, surface_df_b, spot_b,
                ticker=ticker, label_a=label_a, label_b=label_b,
            )
            if diff is not None:
                components.html(render_diff_html(diff), height=640, scrolling=False)
            else:
                st.plotly_chart(
                    plot_iv_change_surface(
                        surface_df_a, surface_df_b,
                        ticker, spot_a, spot_b,
                        label_prior=label_b, label_today=label_a,
                    ),
                    width='stretch',
                )
            st.caption(
                f"DTE range = {label_a} ∩ {label_b} (a narrower band means the prior front expiry rolled off)."
            )
        else:
            st.caption(f"{ticker}: insufficient data for comparison.")


@st.fragment
def _evolution_section(sel_tkr: str, all_data: dict) -> None:
    evo_tkr = sel_tkr
    st.caption("Surface by session — play or scrub the slider.")
    evo_mode_label = st.segmented_control(
        "Mode", ["Level (IV)", "Change vs ref"],
        default="Level (IV)", required=True,
        key="evo_mode", label_visibility="collapsed",
    )
    evo_mode = "change" if evo_mode_label.startswith("Change") else "level"

    summary_line = _evolution_largest_move_summary(_latest_evolution_row_cached(evo_tkr))
    st.caption(summary_line)

    # Headline data for the selected ticker (VRP / skew / term).
    if evo_tkr in all_data:
        data = all_data[evo_tkr]
        s = data["summary"]
        hist = _load_history_cached(evo_tkr, days=config.HISTORY_DAYS)

        vrp_val, vrp_pct = s.get("vrp"), s.get("vrp_pct")
        front_skew_val = s.get("front_skew")
        ts = data.get("term_structure") or {}
        front_iv, back_iv = ts.get("front_atm_iv"), ts.get("back_atm_iv")
        term_spread_val = (front_iv - back_iv) if (front_iv is not None and back_iv is not None) else None

        skew_series = (hist.dropna(subset=["front_skew"])["front_skew"].tolist()
                       if (not hist.empty and "front_skew" in hist.columns) else [])
        vrp_disp = f"{vrp_val:+.1f}pp" if vrp_val is not None else "—"
        if vrp_pct is not None:
            vrp_disp += f" ({_ordinal(vrp_pct)} %ile)"
        skew_disp = f"{front_skew_val:+.1f}pp" if front_skew_val is not None else "—"
        if len(skew_series) >= 5 and front_skew_val is not None:
            skew_disp += f" ({_ordinal(percentileofscore(skew_series, front_skew_val))} %ile)"
        term_disp = f"{term_spread_val:+.1f}pp" if term_spread_val is not None else "—"

        h1, h2, h3 = st.columns(3)
        h1.metric("VRP", vrp_disp)
        h2.metric("Front Skew (25Δ)", skew_disp)
        h3.metric("Term Spread", term_disp)

    # The surface video: one frame per stored session, fixed color scale.
    movie = _movie_payload_cached(evo_tkr, evo_mode)
    if movie is not None:
        st.caption(
            f"{len(movie['frames'])} sessions · "
            f"{movie['frames'][0]['date']} → {movie['frames'][-1]['date']}"
        )
        components.html(render_movie_html(movie), height=620, scrolling=False)
    else:
        st.info(f"{evo_tkr}: need ≥2 stored sessions to animate.")


def _render_explore_tab(shared_rate: float, shared_vvix: float | None) -> None:
    """Ad-hoc, ephemeral single-day snapshot for ANY US-listed optionable ticker.

    Routes through the same no-save compute path as the tracked indexes
    (compute_ticker never persists) — nothing is written to out/. History-based
    metrics (VRP percentile, evolution/compare, 5-day shifts) stay blank because
    an untracked ticker has no accrued snapshots or CBOE vol-index sibling.
    """
    st.caption(
        "Type any US-listed optionable ticker for a one-day CBOE snapshot — "
        "surface, skew, open interest. Snapshot only: nothing is saved or tracked, "
        "so history-based metrics (VRP percentile, evolution, 5-day shifts) are blank."
    )
    raw = st.text_input(
        "Explore ticker",
        value="",
        max_chars=6,
        key="explore_ticker",
        placeholder="e.g. AAPL, NVDA, TSLA",
        label_visibility="collapsed",
    ).strip().upper()

    if not raw:
        st.info("Enter a US ticker above to load its current-day snapshot.")
        return

    with st.spinner(f"Loading {raw} from CBOE…"):
        try:
            data = fetch_ticker(raw, shared_rate, shared_vvix)
        except Exception as exc:
            st.error(
                f"Couldn't load '{raw}'. It may not be a US-listed optionable ticker "
                "on CBOE (only US options are available), or CBOE has no chain for it. "
                "Check the symbol and try another."
            )
            st.caption(f"Detail: {exc}")
            return

    explore_data = {raw: data}
    s = data.get("summary") or {}
    spot = data.get("spot")
    day = s.get("price_change_pct")

    day_str = f" · {day:+.2f}%" if day is not None else ""
    spot_str = f"{spot:,.2f}" if spot else "—"
    st.markdown(
        f"#### {raw} · {spot_str}{day_str}  "
        "<span style='font-size:0.8rem;color:#8b949e;'>snapshot only — not tracked</span>",
        unsafe_allow_html=True,
    )

    def _pct(level):
        if level is None or spot is None or spot <= 0:
            return "—"
        return f"{(level - spot) / spot * 100:+.1f}%"

    # ── Vol metrics (single-name lens leads with what's defensible here) ─────
    st.markdown('<div class="sec">Vol Metrics</div>', unsafe_allow_html=True)
    iv30 = s.get("iv30")
    rv20 = s.get("rv20")
    skew = s.get("front_skew")
    em_pct = s.get("expected_move_pct")
    m = st.columns(4)
    m[0].metric("IV30", f"{iv30:.1f}%" if iv30 else "—")
    m[1].metric("RV20", f"{rv20 * 100:.1f}%" if rv20 else "—")
    m[2].metric("25Δ skew", f"{skew:+.1f}pp" if skew is not None else "—")
    m[3].metric("Expected move", f"±{em_pct:.1f}%" if em_pct is not None else "—")
    st.caption(
        "25Δ skew (put IV − call IV) is the OTM-put premium — at the single-name "
        "level it's the best-studied options tilt (Xing, Zhang & Zhao 2010, JFQA). "
        "VRP percentile, term-structure and surface evolution stay index-only "
        "(SPY/QQQ/IWM) — they need the CBOE vol-index series and accrued daily "
        "snapshots an explore ticker doesn't have."
    )

    # ── Surface (reuses the tracked path's renderer) ────────────────────────
    st.markdown('<div class="sec">Surface</div>', unsafe_allow_html=True)
    _surface_today_section(raw, explore_data)

    # ── Open interest (raw — no dealer-gamma model for single names) ─────────
    st.markdown('<div class="sec">Open Interest</div>', unsafe_allow_html=True)
    st.caption(
        "Raw OI only — no γ-flip / net-GEX / dealer walls here. The dealer-net-short "
        "convention those rest on is empirically supported for index options "
        "(Gârleanu, Pedersen & Poteshman 2009) but not for single names, where market "
        "makers are often net long (Muravyev 2016) and most don't continuously "
        "delta-hedge (Hu et al. 2023). OI is prior-session (T-1), current day only."
    )
    oi_cw = s.get("oi_call_wall")
    oi_pw = s.get("oi_put_wall")
    w1, w2 = st.columns(2)
    w1.metric(
        "OI call wall (raw)",
        f"{oi_cw:,.0f}" if oi_cw is not None else "—",
        _pct(oi_cw) if oi_cw is not None else None,
    )
    w2.metric(
        "OI put wall (raw)",
        f"{oi_pw:,.0f}" if oi_pw is not None else "—",
        _pct(oi_pw) if oi_pw is not None else None,
    )

    expiry_oi_df = data.get("expiry_oi_df")
    if expiry_oi_df is None or expiry_oi_df.empty:
        st.caption(f"{raw}: OI by expiry data unavailable.")
    else:
        df = expiry_oi_df[["expiry", "dte", "oi", "pct_of_total", "put_call_ratio"]].copy()
        df["Expiry"] = pd.to_datetime(df["expiry"]).dt.strftime("%b %d")
        df["DTE"] = df["dte"].round(0).astype(int)
        df["OI"] = df["oi"].apply(lambda x: f"{x / 1e3:.0f}K" if x >= 1000 else f"{x:.0f}")
        df["OI Share"] = df["pct_of_total"].apply(lambda x: f"{x:.1f}%")
        df["P/C Ratio"] = df["put_call_ratio"].apply(lambda x: f"{x:.2f}")
        df["Impact"] = df.apply(
            lambda r: format_oi_impact(r.get("pct_of_total"), r.get("put_call_ratio")),
            axis=1,
        )
        st.dataframe(
            df[["Expiry", "DTE", "OI", "OI Share", "P/C Ratio", "Impact"]],
            use_container_width=True, hide_index=True,
        )


if sel_index:
    # on_change="rerun" makes tab bodies lazy — without it Streamlit computes and
    # ships EVERY tab on every run, which put the Evolution tab's surface video
    # (dozens of RBF solves) on the cold-start path of a tab nobody had clicked.
    tab_regime, tab_surfaces, tab_positioning, tab_explore = st.tabs(
        ["Regime", "Surfaces", "Option conditions", "Explore"],
        on_change="rerun",
    )

    with tab_regime:
        if tab_regime.open:
            _render_regime_cards(selected_all, all_data)

    # ── Surfaces (Today / Compare / Evolution) ───────────────────────────────
    with tab_surfaces:
        surf_tkr = st.segmented_control(
            "Surface ticker", selected_all,
            default=selected_all[0], required=True,
            key="surf_main_tkr", label_visibility="collapsed",
        )
        # ── Momentum strip — trend headline before any surface detail ────────
        _render_surface_momentum([surf_tkr], all_data)

        # ── Vanna/Volga metrics — second-order Greeks ────────────────────────
        st.divider()
        _render_vanna_volga_metrics([surf_tkr], all_data)

        sub_today, sub_compare, sub_evolution = st.tabs(
            ["Today", "Compare", "Evolution"], on_change="rerun"
        )

        with sub_today:
            if sub_today.open:
                _surface_today_section(surf_tkr, all_data)

        with sub_compare:
            if sub_compare.open:
                _surface_compare_section(surf_tkr, all_data)

        with sub_evolution:
            if sub_evolution.open:
                _evolution_section(surf_tkr, all_data)

    # ── Option conditions ───────────────────────────────────────────────────────
    with tab_positioning:
        st.caption(
            "What the option market structure implies for a position — a move-size "
            "regime for sizing, the expected-move cone for strike placement, and open "
            "interest for assignment / pin risk. Applies whether you are writing, "
            "buying, or rolling. No price targets, no direction call."
        )

        pos_tkr = st.segmented_control(
            "Option-conditions ticker", selected_all,
            default=selected_all[0], required=True,
            key="positioning_tkr", label_visibility="collapsed",
        )

        for ticker in [pos_tkr]:
            if ticker not in all_data:
                continue
            data = all_data[ticker]
            s = data["summary"]
            spot = data.get("spot")

            st.markdown(f"**{ticker}**")

            ng = s.get("net_gex")
            if ng is None:
                regime_txt, regime_note, regime_color = "—", "Move-size regime unavailable.", "#64748b"
            elif ng >= 0:
                regime_txt = "Contained"
                regime_note = ("Dealer gamma net-long → moves tend smaller. A short-premium "
                               "posture sits easier; sizing can lean in.")
                regime_color = "#4ade80"
            else:
                regime_txt = "Elevated"
                regime_note = ("Dealer gamma net-short → moves tend larger either way. Size "
                               "down, widen strikes, mind the tails.")
                regime_color = "#f87171"

            em_pct = s.get("expected_move_pct")
            em_expiry = s.get("em_expiry")
            em_dte = s.get("em_dte")
            if em_pct is not None and em_expiry is not None and em_dte is not None:
                try:
                    em_str = (f"±{em_pct:.1f}% by {pd.to_datetime(em_expiry).strftime('%b %d')} "
                              f"({int(round(float(em_dte)))}d)")
                except (TypeError, ValueError):
                    em_str = f"±{em_pct:.1f}%"
            elif em_pct is not None:
                em_str = f"±{em_pct:.1f}%"
            else:
                em_str = "—"

            c1, c2 = st.columns(2)
            with c1:
                st.markdown(
                    f"<span style='font-size:0.78rem;color:#8b949e;'>Move-size regime "
                    f"<span style='opacity:0.7;'>(sizing input, not a target)</span></span><br>"
                    f"<span style='font-size:1.25rem;font-weight:700;color:{regime_color};'>"
                    f"{regime_txt}</span>",
                    unsafe_allow_html=True,
                )
                st.caption(regime_note)
            with c2:
                st.markdown(
                    f"<span style='font-size:0.78rem;color:#8b949e;'>Expected-move cone "
                    f"<span style='opacity:0.7;'>(1σ, for strike placement)</span></span><br>"
                    f"<span style='font-size:1.25rem;font-weight:700;'>{em_str}</span>",
                    unsafe_allow_html=True,
                )
                st.caption("Set short strikes outside the band you'll accept assignment within.")

            st.markdown(
                "<div class='sec'>Open interest — assignment &amp; pin risk</div>",
                unsafe_allow_html=True,
            )
            expiry_oi_df = data.get("expiry_oi_df")
            if expiry_oi_df is None or expiry_oi_df.empty:
                st.caption(f"{ticker}: OI by expiry data unavailable.")
            else:
                st.caption(
                    f"Where OI concentrates relative to your short strikes → breach / pin risk. "
                    f"Filtered set (OI ≥ 100, DTE ≤ {config.GEX_MAX_DTE}, IV ≤ 300%, 0DTE excluded); "
                    "OI is T-1, and 5d share context is shown when history exists."
                )
                prior = _prior_oi_cached(ticker, date.today())
                prior_oi_map = {}
                if not prior.empty and "expiry" in prior.columns and "oi" in prior.columns:
                    for _, row in prior.iterrows():
                        prior_oi_map[str(row["expiry"])] = row["oi"]

                display_df = expiry_oi_df[["expiry", "dte", "oi", "pct_of_total", "put_call_ratio"]].copy()
                oi_hist = _oi_history_cached(ticker, days=5)
                avg_share_map: dict[str, float] = {}
                if not oi_hist.empty and {"expiry", "pct_of_total"}.issubset(set(oi_hist.columns)):
                    avg_share = oi_hist.groupby("expiry", dropna=True)["pct_of_total"].mean()
                    avg_share_map = {str(k): float(v) for k, v in avg_share.items()}

                def _fmt_oi(x):
                    return f"{x/1e3:.0f}K" if x >= 1000 else f"{x:.0f}"

                def _fmt_delta_oi(current_oi, expiry_key):
                    prior_val = prior_oi_map.get(str(expiry_key))
                    if prior_val is None:
                        return "–"
                    d = current_oi - prior_val
                    if abs(d) >= 1000:
                        return f"+{d/1e3:.0f}K" if d >= 0 else f"{d/1e3:.0f}K"
                    return f"+{d:.0f}" if d >= 0 else f"{d:.0f}"

                display_df["Expiry"] = pd.to_datetime(display_df["expiry"]).dt.strftime("%b %d")
                display_df["DTE"] = display_df["dte"].round(0).astype(int)
                display_df["OI"] = display_df["oi"].apply(_fmt_oi)
                display_df["Δ OI"] = [
                    _fmt_delta_oi(row["oi"], row["expiry"])
                    for _, row in expiry_oi_df.iterrows()
                ]
                display_df["OI Share"] = display_df["pct_of_total"].apply(lambda x: f"{x:.1f}%")
                display_df["P/C Ratio"] = display_df["put_call_ratio"].apply(lambda x: f"{x:.2f}")
                display_df["5d Avg Share"] = [
                    (f"{avg_share_map[str(row['expiry'])]:.1f}%" if str(row["expiry"]) in avg_share_map else "—")
                    for _, row in expiry_oi_df.iterrows()
                ]
                display_df["vs 5d Avg"] = [
                    (
                        f"{(row['pct_of_total'] - avg_share_map[str(row['expiry'])]):+.1f}pp"
                        if str(row["expiry"]) in avg_share_map else "—"
                    )
                    for _, row in expiry_oi_df.iterrows()
                ]
                display_df["Impact"] = display_df.apply(
                    lambda r: format_oi_impact(r.get("pct_of_total"), r.get("put_call_ratio")),
                    axis=1,
                )

                display_df = display_df[
                    ["Expiry", "DTE", "OI", "Δ OI", "OI Share", "5d Avg Share", "vs 5d Avg", "P/C Ratio", "Impact"]
                ]
                st.dataframe(display_df, use_container_width=True, hide_index=True)

            if ticker == "IWM":
                st.caption(
                    "IWM: lean on the OI read here — small-cap dealer gamma is thin, so the "
                    "move-size regime is a weaker input than it is for SPY / QQQ."
                )

    # ── Explore (ad-hoc, ephemeral single-ticker snapshot) ─────────────────────
    with tab_explore:
        _render_explore_tab(shared_rate, shared_vvix)

