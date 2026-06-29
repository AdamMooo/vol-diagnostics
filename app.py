from __future__ import annotations

import time
from datetime import datetime, date, timedelta

import pandas as pd
import plotly.graph_objects as go
import pandas_market_calendars as mcal
import pytz
import streamlit as st
import streamlit.components.v1 as components

from engine import config
from engine.surface.surface_interactive import (
    build_surface_payload, render_surface_html,
    build_diff_payload, render_diff_html,
    build_movie_payload, render_movie_html,
)
from engine.report.card_model import (CardField, build_card_fields, build_card_read, split_compact_fields, LABEL_GRAY, format_oi_impact)
from engine.data.validation import load_prior_snapshot
from engine.data.oi_history import prior_oi_snapshot, load_oi_history
from engine.compute import compute_ticker
from engine.gex.analytics import (
    plot_gamma_profile,
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
    page_title="Option Diagnostics",
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
    st.markdown("## Option Diagnostics")
    pwd = st.text_input("Password", type="password", placeholder="Enter password")
    if pwd == expected:
        st.session_state.authenticated = True
        st.rerun()
    elif pwd:
        st.error("Incorrect password")
    return False

if not _check_password():
    st.stop()

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
.rc-ticker { font-size: 1.05rem; font-weight: 700; letter-spacing: 0.03em; margin-bottom: 8px; }
/* Grid demoted to supporting detail beneath the read-line: smaller, dimmer, hairline-separated. */
.rc-grid {
    display: grid; grid-template-columns: auto 1fr; gap: 3px 16px; font-size: 0.72rem;
    opacity: 0.78; border-top: 1px solid rgba(148,163,184,0.14); padding-top: 8px;
}
.rc-k { opacity: 0.55; }
.rc-v { font-weight: 600; font-variant-numeric: tabular-nums; text-align: right; }
.rc-tag {
    font-size: 0.62rem; padding: 1px 6px; border-radius: 8px; margin-left: 6px;
    border: 1px solid rgba(148,163,184,0.35); color: #94a3b8; opacity: 0.9;
}
.rc-obs { font-size: 0.72rem; opacity: 0.70; margin-top: 10px; line-height: 1.6; }

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
.fresh-ok  { background: rgba(22,163,74,0.10);  border-color: #16a34a; color: #16a34a; }
.fresh-bad { background: rgba(234,88,12,0.12);   border-color: #ea580c; color: #ea580c; }

.risk-bar {
    display: flex; align-items: center; gap: 16px;
    padding: 14px 22px; border-radius: 8px; margin-bottom: 20px;
}
.risk-elevated { background: rgba(248,113,113,0.10); border: 1px solid rgba(248,113,113,0.3); }
.risk-stable   { background: rgba(74,222,128,0.10);  border: 1px solid rgba(74,222,128,0.3); }
.risk-mixed    { background: rgba(251,191,36,0.10);  border: 1px solid rgba(251,191,36,0.3); }
.risk-label {
    font-size: 0.92rem; font-weight: 700; letter-spacing: 0.04em;
}
.risk-elevated .risk-label { color: #f87171; }
.risk-stable .risk-label   { color: #4ade80; }
.risk-mixed .risk-label    { color: #fbbf24; }
.risk-detail { font-size: 0.78rem; color: #94a3b8; }
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
    from engine.data.validation import load_history
    return load_history(ticker, days)


@st.cache_data(ttl=config.CACHE_TTL_HISTORY, show_spinner="Building surface video…")
def _movie_payload_cached(ticker: str, mode: str = "level") -> dict | None:
    snaps = []
    for d in sorted(_available_dates_cached(ticker)):
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


@st.cache_data(ttl=config.CACHE_TTL_HISTORY, show_spinner=False)
def _load_evolution_cached(ticker: str, horizon: int, days: int = 400) -> pd.DataFrame:
    return load_evolution(ticker, horizon=horizon, days=days)


@st.cache_data(ttl=config.CACHE_TTL_HISTORY, show_spinner=False)
def _prior_snapshot_cached(ticker: str, before_date: date) -> "pd.Series | None":
    return load_prior_snapshot(ticker=ticker, before_date=before_date)


@st.cache_data(ttl=config.CACHE_TTL_HISTORY, show_spinner=False)
def _prior_oi_cached(ticker: str, before_date: date) -> pd.DataFrame:
    return prior_oi_snapshot(ticker, before_date)


@st.cache_data(ttl=config.CACHE_TTL_HISTORY, show_spinner=False)
def _oi_history_cached(ticker: str, days: int) -> pd.DataFrame:
    return load_oi_history(ticker, days=days)


@st.cache_data(ttl=config.CACHE_TTL_HISTORY, show_spinner=False)
def _available_dates_cached(ticker: str) -> list:
    return list(list_available_dates(ticker))
    row = latest.iloc[0]
    out = {k: row[k] if k in latest.columns else None for k in cols}
    return out


def _evolution_largest_move_summary(metrics: dict | None) -> str:
    import math
    if not metrics:
        return "What changed most today: insufficient history yet (need stored sessions)."

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
        return "What changed most today: insufficient history yet (need stored sessions)."

    _, key, value = max(ranked, key=lambda x: x[0])
    label, up_word, down_word = defs[key]
    direction = up_word if value >= 0 else down_word
    return f"What changed most today: {label} {direction} ({value:+.2f}pp)."


def render_regime_card(col, summary: dict, spot: float | None = None) -> None:
    """Restrained card: uniform amber accent; the read-line (chips + lean) is the hero,
    the field grid is demoted detail. No sign-based color (UI-REVIEW color-conflict fix)."""
    ticker = summary["ticker"]
    # Restrained palette (UI-REVIEW color-conflict fix): uniform amber accent + neutral bg.
    # Direction/sign no longer colors the card — the read chips carry meaning in WORDS; the
    # only place a red/blue (up/down) scale survives is the fenced ΔIV chart.
    color = config.PALETTE["accent"]
    bg = "rgba(148,163,184,0.05)"

    prior_row = _prior_snapshot_cached(ticker=ticker, before_date=date.today())
    fields = build_card_fields(today_summary=summary, prior_summary=prior_row)
    fields = [f for f in fields if f.label != "γ-flip"]
    primary_fields, detail_fields = split_compact_fields(fields)

    grid_html = "".join(
        f'<span class="rc-k">{f.label}<span class="rc-tag">{f.trust_tag}</span></span>'
        f'<span class="rc-v">{f.value}</span>'
        for f in primary_fields
    )

    # The "so what" read — skew %ile + 5d drift, each shown ONLY if its sample clears the
    # credibility floor (a thin rank is worse than a blank). VRP is gated inside the builder.
    # The gated inputs are computed once in compute_ticker (the canonical-card seam) so this
    # card and the email card stay identical.
    read = build_card_read(
        summary,
        skew_pct=summary.get("read_skew_pct"),
        move_5d=summary.get("read_move_5d"),
    )
    # Restrained: amber = any signal chip, gray = neutral. Color is emphasis, not direction.
    _amber = config.PALETTE["accent"]
    _tone = {"positive": _amber, "negative": _amber, "neutral": LABEL_GRAY}
    chips_html = "".join(
        f'<span style="display:inline-block;padding:2px 8px;margin:0 5px 5px 0;border-radius:9px;'
        f'font-size:0.74rem;background:rgba(217,119,6,0.10);color:{_tone.get(tone, LABEL_GRAY)};'
        f'border:1px solid {_tone.get(tone, LABEL_GRAY)}40;">{txt}</span>'
        for txt, tone in read.chips
    )
    # Read-line is the hero: larger, brighter, not buried. The field grid is demoted below.
    read_html = (
        f'<div style="margin:2px 0 10px;">{chips_html}'
        f'<div style="font-size:0.98rem;color:#e6edf3;font-weight:500;margin-top:7px;'
        f'line-height:1.4;">{read.lean}</div></div>'
    )

    col.markdown(f"""
<div class="rc" style="background:{bg};border-left-color:{color};">
  <div class="rc-ticker" style="color:{color};">{ticker}</div>
  {read_html}
  <div class="rc-grid">{grid_html}</div>
</div>
""", unsafe_allow_html=True)
    with col.expander("More fields", expanded=False):
        for f in detail_fields:
            st.markdown(f"- **{f.label}** ({f.trust_tag}): {f.value}")


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


def _render_environment_hero(selected_all: list[str], all_data: dict[str, dict]) -> None:
    """Page-1 hero: risk bar + narrative + key levels + vol metrics.
    Replaces the old cross-index briefing + positioning teaser + card grid."""
    rows: list[dict] = []
    for ticker in selected_all:
        data = all_data.get(ticker)
        if not data:
            continue
        s = data.get("summary") or {}
        if s.get("error"):
            continue
        rows.append(s)

    if not rows:
        st.info("No data loaded.")
        return

    n = len(rows)
    stabilizing = sum(1 for s in rows if (s.get("net_gex") is not None and s.get("net_gex") >= 0))
    rich = sum(1 for s in rows if (s.get("vrp") is not None and s.get("vrp") > 0))
    amplifying = n - stabilizing

    # ── Risk Bar ──────────────────────────────────────────────────────────────
    if amplifying >= 2:
        bar_class = "risk-bar risk-elevated"
        bar_label = "AMPLIFYING"
        bar_detail = f"{amplifying}/{n} indices under dealer amplification"
    elif stabilizing == n:
        bar_class = "risk-bar risk-stable"
        bar_label = "STABILIZING"
        bar_detail = f"All {n} indices in positive gamma (dealers dampen moves)"
    else:
        bar_class = "risk-bar risk-mixed"
        bar_label = "MIXED"
        bar_detail = f"{stabilizing}/{n} stabilizing · {amplifying}/{n} amplifying"

    vrp_bit = f" · VRP rich: {rich}/{n}" if rich > 0 else ""
    # Surface trend from first ticker with evolution data
    surf_bit = ""
    for s in rows:
        mv = s.get("read_move_5d")
        if mv is not None:
            direction = "rising" if mv > 0 else "falling" if mv < 0 else "flat"
            surf_bit = f" · Surface {direction} 5d"
            break

    st.markdown(f'''<div class="{bar_class}">
  <span class="risk-label">{bar_label}</span>
  <span class="risk-detail">{bar_detail}{vrp_bit}{surf_bit}</span>
</div>''', unsafe_allow_html=True)

    # ── Narrative ─────────────────────────────────────────────────────────────
    narrative_parts = []
    if amplifying >= 2:
        narrative_parts.append(
            "Dealers are net short gamma — moves in either direction get amplified, not dampened."
        )
    elif stabilizing == n:
        narrative_parts.append(
            "Dealers are long gamma across all indices — moves are dampened. Low-vol, mean-reverting regime."
        )

    if rich >= 2:
        narrative_parts.append(
            f"Premium is rich on {rich}/{n} (VRP above realized) — protection demand is elevated."
        )

    # Skew context (SPY first)
    spy_summary = next((s for s in rows if s.get("ticker") == "SPY"), rows[0])
    skew_pct = spy_summary.get("read_skew_pct")
    if skew_pct is not None and skew_pct >= 75:
        narrative_parts.append(
            f"Front skew at {skew_pct}th percentile — heavy put demand relative to history."
        )

    # VIX term
    term_9d = spy_summary.get("term_ratio_9d_30d")
    if term_9d is not None and term_9d > 1.0:
        narrative_parts.append(
            "VIX term structure in backwardation — near-term stress exceeds forward expectations."
        )

    if amplifying >= 2:
        narrative_parts.append(
            "**Follow the break — don't anticipate.** Magnitude is elevated; direction unknown."
        )

    if narrative_parts:
        st.markdown(" ".join(narrative_parts))

    # ── Key Levels ────────────────────────────────────────────────────────────
    st.markdown('<div class="sec">Key Levels</div>', unsafe_allow_html=True)

    cols = st.columns(n)
    for col, s in zip(cols, rows):
        ticker = s.get("ticker", "?")
        spot = s.get("spot")
        zgl = s.get("zero_gamma_level")
        cw = s.get("call_wall")
        pw = s.get("put_wall")
        em_pct = s.get("expected_move_pct")

        def _pct(level):
            if level is None or spot is None or spot <= 0:
                return "—"
            return f"{(level - spot) / spot * 100:+.1f}%"

        def _shift(key):
            v = s.get(key)
            if v is None:
                return ""
            return f" ({v:+.1f}% 5d)"

        with col:
            st.markdown(f"**{ticker}** · spot {spot:,.0f}" if spot else f"**{ticker}**")
            level_rows = []
            if zgl is not None:
                level_rows.append(f"γ-flip **{zgl:,.0f}** {_pct(zgl)}{_shift('zgl_5d_shift')}")
            if cw is not None:
                level_rows.append(f"Call wall **{cw:,.0f}** {_pct(cw)}{_shift('call_wall_5d_shift')}")
            if pw is not None:
                level_rows.append(f"Put wall **{pw:,.0f}** {_pct(pw)}{_shift('put_wall_5d_shift')}")
            if em_pct is not None:
                level_rows.append(f"Expected move **±{em_pct:.1f}%**")
            for lr in level_rows:
                st.markdown(f"<span style='font-size:0.82rem;'>{lr}</span>", unsafe_allow_html=True)

    # ── Vol Metrics Strip ─────────────────────────────────────────────────────
    st.markdown('<div class="sec">Vol Environment</div>', unsafe_allow_html=True)

    # Gather metrics from SPY (primary) with fallbacks
    vrp_val = spy_summary.get("vrp")
    vrp_pct = spy_summary.get("vrp_pct")
    skew_val = spy_summary.get("front_skew")
    vvix = spy_summary.get("vvix")

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        vrp_str = f"{vrp_val:+.1f}pp" if vrp_val is not None else "—"
        if vrp_pct is not None:
            vrp_str += f" ({vrp_pct}th)"
        st.metric("VRP (SPY)", vrp_str)
    with m2:
        skew_str = f"{skew_val:+.1f}pp" if skew_val is not None else "—"
        if skew_pct is not None:
            skew_str += f" ({skew_pct}th)"
        st.metric("Front Skew (SPY)", skew_str)
    with m3:
        if term_9d is not None:
            term_state = "Backwardation" if term_9d > 1.0 else "Contango"
            st.metric("VIX Term", f"{term_state} ({term_9d:.2f})")
        else:
            st.metric("VIX Term", "—")
    with m4:
        vvix_str = f"{vvix:.0f}" if vvix is not None else "—"
        st.metric("VVIX", vvix_str)


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
            '<div class="fresh fresh-bad">⚠ no stored snapshots found — '
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
            f'<div class="fresh fresh-ok">✓ data current through {latest_str}</div>',
            unsafe_allow_html=True,
        )
    else:
        plural = "s" if missing != 1 else ""
        st.markdown(
            f'<div class="fresh fresh-bad">⚠ last collection {latest_str} · '
            f"{missing} trading day{plural} missing</div>",
            unsafe_allow_html=True,
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
  <span>{_top_date}  ·  CBOE delayed, 15-min lag  ·  OI T-1 (OCC standard)</span>
</div>""",
    unsafe_allow_html=True,
)

_render_freshness_banner()

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


@st.fragment
def _surface_today_section(selected_all: list[str], all_data: dict) -> None:
    surf_today_tkr = st.radio(
        "Surface ticker", selected_all, horizontal=True,
        key="surf_today_tkr", label_visibility="collapsed",
    )
    for ticker in [surf_today_tkr]:  # one heavy surface at a time (perf)
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
def _surface_compare_section(selected_all: list[str], all_data: dict) -> None:
    _horizon_options = {
        "live": 0,
        "1d": 1,
        "5d": 5,
        "10d": 10,
        "20d": 20,
        "30d": 30,
        "60d": 60,
    }
    surf_cmp_tkr = st.radio(
        "Compare ticker", selected_all, horizontal=True,
        key="surf_cmp_tkr", label_visibility="collapsed",
    )
    for ticker in [surf_cmp_tkr]:  # one heavy surface at a time (perf)
        if ticker not in all_data:
            continue
        data = all_data[ticker]
        surface_df_today = data.get("surface_df")
        spot_today = data.get("spot")

        available = _available_dates_cached(ticker)
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
                f"DTE range is bounded by the intersection of {label_a}'s and "
                f"{label_b}'s data — if the surface is narrower than today's, "
                "the prior snapshot's front expiry has rolled off."
            )
        else:
            st.caption(f"{ticker}: insufficient data for comparison.")


@st.fragment
def _evolution_section(selected_all: list[str], all_data: dict) -> None:
    st.caption(
        "How the surface changes day by day — hit ▶ to play it like a video, "
        "or drag the slider to scrub through stored sessions."
    )
    ec1, ec2 = st.columns([2, 2])
    with ec1:
        evo_tkr = st.radio(
            "Evolution ticker", selected_all, horizontal=True,
            key="evo_tkr", label_visibility="collapsed",
        )
    with ec2:
        evo_mode_label = st.radio(
            "Mode", ["Level (IV)", "Change vs ref"], horizontal=True,
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
            vrp_disp += f" ({vrp_pct}th %ile)"
        skew_disp = f"{front_skew_val:+.1f}pp" if front_skew_val is not None else "—"
        if len(skew_series) >= 5 and front_skew_val is not None:
            skew_disp += f" ({int(percentileofscore(skew_series, front_skew_val))}th %ile)"
        term_disp = f"{term_spread_val:+.1f}pp" if term_spread_val is not None else "—"

        h1, h2, h3 = st.columns(3)
        h1.metric("VRP (vol − RV20)", vrp_disp)
        h2.metric("Front skew (25Δ RR)", skew_disp)
        h3.metric("Term spread (front − back)", term_disp)

    # The surface video: one frame per stored session, fixed color scale.
    movie = _movie_payload_cached(evo_tkr, evo_mode)
    if movie is not None:
        st.caption(
            f"{len(movie['frames'])} sessions · "
            f"{movie['frames'][0]['date']} → {movie['frames'][-1]['date']}"
        )
        components.html(render_movie_html(movie), height=620, scrolling=False)
    else:
        st.info(
            f"{evo_tkr}: need ≥2 stored sessions to animate — "
            "accumulates from `run_daily` runs forward."
        )


if sel_index:
    tab_regime, tab_surfaces, tab_positioning = st.tabs(
        ["Regime", "Surfaces", "Positioning"]
    )

    with tab_regime:
        _render_environment_hero(selected_all, all_data)

    # ── Surfaces (Today / Compare / Evolution) ───────────────────────────────
    with tab_surfaces:
        surf_tkr = st.radio(
            "Surface ticker", selected_all, horizontal=True,
            key="surf_main_tkr", label_visibility="collapsed",
        )
        # ── Momentum strip — trend headline before any surface detail ────────
        _render_surface_momentum([surf_tkr], all_data)

        sub_today, sub_compare, sub_evolution = st.tabs(["Today", "Compare", "Evolution"])

        with sub_today:
            _surface_today_section(selected_all, all_data)

        with sub_compare:
            _surface_compare_section(selected_all, all_data)

        with sub_evolution:
            _evolution_section(selected_all, all_data)

    # ── Positioning ───────────────────────────────────────────────────────────
    with tab_positioning:
        st.markdown(
            f"Positioning defaults to a **{config.GEX_PRIMARY_DTE} DTE primary dealer-impact lens**. "
            f"Broader ≤{config.GEX_MAX_DTE} DTE remains secondary context. "
            "OI is assumption-free (no dealer model needed), while GEX-derived levels "
            "(γ-flip, walls) are model constructs under the dealer net-short assumption "
            "(Garleanu et al. 2009).",
            unsafe_allow_html=False,
        )

        pos_tkr = st.radio(
            "Positioning ticker", selected_all, horizontal=True,
            key="positioning_tkr", label_visibility="collapsed",
        )

        for ticker in [pos_tkr]:
            if ticker not in all_data:
                continue
            data = all_data[ticker]
            s = data["summary"]
            spot = data.get("spot")

            st.markdown(f"**{ticker}**")

            # Net GEX + Net Delta side by side
            nd = s.get("net_delta")
            ng = s.get("net_gex")
            d1, d2 = st.columns(2)
            with d1:
                gex_sign = "Stabilizing" if (ng is not None and ng >= 0) else "Amplifying"
                gex_color = "#4ade80" if ng and ng >= 0 else "#f87171"
                gex_str = f"{ng/1e9:.2f}B" if ng is not None else "—"
                st.markdown(
                    f"<span style='font-size:0.78rem;color:#8b949e;'>Net GEX</span><br>"
                    f"<span style='font-size:1.1rem;font-weight:700;color:{gex_color};'>"
                    f"{gex_str}</span> <span style='font-size:0.78rem;color:{gex_color};'>{gex_sign}</span>",
                    unsafe_allow_html=True,
                )
            with d2:
                if nd is not None:
                    nd_dir = "Long" if nd > 0 else "Short"
                    nd_str = f"{abs(nd)/1e6:.1f}M shares {nd_dir.lower()}"
                else:
                    nd_str = "—"
                st.markdown(
                    f"<span style='font-size:0.78rem;color:#8b949e;'>Net Delta (dealer hedge)</span><br>"
                    f"<span style='font-size:1.1rem;font-weight:700;'>{nd_str}</span>",
                    unsafe_allow_html=True,
                )

            with st.container():
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
                p_df = data.get("p_df")
                if p_df is not None:
                    st.plotly_chart(
                        plot_gamma_profile(p_df, spot, ticker, s),
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

            with st.expander("OI Impact by Expiry", expanded=False):
                expiry_oi_df = data.get("expiry_oi_df")
                if expiry_oi_df is None or expiry_oi_df.empty:
                    st.caption(f"{ticker}: OI by expiry data unavailable.")
                else:
                    st.caption(
                        f"Table-first OI context from the filtered positioning set "
                        f"(OI >= 100, DTE <= {config.GEX_MAX_DTE}, IV <= 300%, 0DTE excluded). "
                        f"Primary narrative lens: first {config.GEX_PRIMARY_DTE} DTE; broader tenor remains secondary context. "
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

        st.caption(
            "IWM: OI data is the more reliable signal — "
            "GEX-derived levels may be less reliable due to thinner dealer positioning in small-caps."
        )

# ── Methodology & assumptions (quick/deep) ───────────────────────────────────
def _methods_quick_bullets() -> list[str]:
    return [
        "Quick assumptions (default): descriptive diagnostics only — no forecast or trade signal.",
        "Data latency: quotes are delayed and OI is prior-session (T-1); positioning is not live tape.",
        "Positioning lens: 14 DTE primary dealer-impact framing, with ≤90 DTE as secondary context.",
        "VRP series: CBOE index-vol close minus RV20×100; scalar and percentile use the same history.",
    ]


def _methods_deep_markdown() -> str:
    return """
**Deep methodology details**

**Data source.** Free CBOE delayed quotes JSON (no auth, no OPRA tick feed).
Spot, IV, and chain mids are ~15-min delayed. **OI reflects prior session close**
(OCC settles contracts end-of-day; this is true for all data vendors including
Bloomberg — no intraday OI update exists). Greeks (γ, Δ, vega, θ) come from
**CBOE's American option pricing model** (accounts for early exercise + dividends);
we do not recompute them locally.

**VRP source + formula.** VRP is **not** chain IV30 minus RV20 anymore. It is
**CBOE index-vol close (VIX/VXN/RVX) − RV20×100**, where RV20 is from yfinance
daily closes. That keeps the scalar and percentile on one consistent series.

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


with st.expander("Methodology & Assumptions", expanded=False):
    st.markdown("**Quick assumptions (default)**")
    for bullet in _methods_quick_bullets():
        st.markdown(f"- {bullet}")

    with st.expander("Deep methodology details", expanded=False):
        st.markdown(_methods_deep_markdown())





