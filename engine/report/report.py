"""
Build the HTML email body from GEX summaries.

Design principles:
    - No body/card backgrounds — inherit the client's light/dark theme.
    - Regime cue = left accent bar (4px) + solid badge (works in both modes).
    - Text colors stay vivid (green/red) so signs read in dark mode.
    - Labels use a mid-gray that reads acceptably on both white and near-black.
    - Numbers use a monospace family so columns line up; everything else sans.
"""
from __future__ import annotations

import datetime

import pandas as pd

from engine import config
from engine.report.card_model import (
    build_card_read, _pct_from_spot, _fmt_pct as _fmt_signed_pct,
    _fmt_pct as _fmt_unsigned_pct, format_oi_impact,
    _fmt_vrp, _fmt_skew, _fmt_expected_move, _fmt_term_ratios,
)

# Sign-of-net-gex visual cue for the accent bar — muted, report-grade tones
# (kept email-local; the dashboard keeps config.PALETTE untouched).
POS_GREEN   = "#0f7b57"   # muted forest green — directional "up/rich/stabilizing"
NEG_RED     = "#b23b34"   # muted brick red   — directional "down/cheap/amplifying"
REGIME_COLOR = {
    "positive": POS_GREEN,
    "negative": NEG_RED,
    "zero":     "#64748b",
}

# Badge backgrounds (solid color with white text — survive theme inversion).
TICKER_LABEL = {
    "SPY": "SPY  S&P 500",
    "QQQ": "QQQ  Nasdaq 100",
    "IWM": "IWM  Russell 2000",
}

# ── Report palette (professional, restrained) ──────────────────────────
INK         = "#1f2a37"   # primary text — near-black navy
LABEL_GRAY  = "#64748b"   # secondary text & labels — slate (legible on white)
RULE_COLOR  = "#e5e9f0"   # hairline dividers
PANEL_BG    = "#f8fafc"   # subtle card panel fill
PAGE_BG     = "#eef2f6"   # page backdrop behind the white report sheet
MAST_BG     = "#0f2036"   # masthead deep navy
MAST_SUB    = "#aebdcf"   # masthead subtitle text
ACCENT      = "#c19a3e"   # refined gold accent — the single brand color

_SANS = "font-family:Arial,Helvetica,sans-serif;"
_MONO = "font-family:Consolas,'SF Mono',Menlo,monospace;"


# ── Badges ────────────────────────────────────────────────────────────

# ── Key/value rows ────────────────────────────────────────────────────

def _kv_cell(label: str, value: str, value_color: str | None = None,
             mono: bool = True) -> str:
    """One label/value row. value_color overrides the default ink color when a
    caller wants directional emphasis; otherwise values render in INK on the
    white report sheet for a clean, high-contrast read."""
    value_family = _MONO if mono else _SANS
    color = value_color or INK
    return (
        f'<tr>'
        f'<td style="{_SANS}padding:6px 12px 6px 0;font-size:11px;color:{LABEL_GRAY};'
        f'letter-spacing:0.4px;text-transform:uppercase;white-space:nowrap;'
        f'border-bottom:1px solid {RULE_COLOR};">{label}</td>'
        f'<td align="right" style="{value_family}padding:6px 0;font-size:14px;'
        f'font-weight:600;color:{color};white-space:nowrap;'
        f'border-bottom:1px solid {RULE_COLOR};">{value}</td>'
        f'</tr>'
    )


def _kv_table(rows_html: str) -> str:
    return (
        f'<table cellpadding="0" cellspacing="0" border="0" '
        f'style="border-collapse:collapse;width:100%;">{rows_html}</table>'
    )


# ── Read line (the "so what") ─────────────────────────────────────────

def _read_block(r: dict) -> str:
    """The plain-English read on top of the card — same chips + soft lean as the
    dashboard, sourced from the canonical build_card_read. Gated inputs ride on the
    summary (read_skew_pct / read_move_5d) from compute_ticker, so email = dashboard."""
    read = build_card_read(
        r, skew_pct=r.get("read_skew_pct"), move_5d=r.get("read_move_5d"),
    )
    if not read.chips and not read.lean:
        return ""
    amber = config.PALETTE["accent"]
    tone_color = {"positive": amber, "negative": amber, "neutral": LABEL_GRAY}
    chips = "".join(
        f'<span style="{_SANS}display:inline-block;padding:2px 9px;margin:0 6px 6px 0;'
        f'border-radius:10px;font-size:12px;color:{tone_color.get(t, LABEL_GRAY)};'
        f'border:1px solid {tone_color.get(t, LABEL_GRAY)};">{txt}</span>'
        for txt, t in read.chips
    )
    lean = (
        f'<div style="{_SANS}font-size:13px;font-weight:600;margin-top:4px;'
        f'line-height:1.4;">{read.lean}</div>' if read.lean else ""
    )
    return f'<div style="margin:6px 0 10px;">{chips}{lean}</div>'


# ── Vol snapshot — surfaces the VRP / IV / skew / term work in the email ──

def _vol_snapshot_block(r: dict) -> str:
    """Compact vol-premium snapshot: VRP as the hero line, then IV30/EM, skew,
    and (SPY-only) VIX term structure. This is the payload of the Phase 23-26
    data work — it lived only in the read chips before, never as real numbers.

    Reads precomputed summary fields (no I/O). VRP colouring keys off its deep
    percentile: rich (>=67th) green, cheap (<=33rd) red, else neutral gray."""
    vrp = r.get("vrp")
    vrp_pct = r.get("vrp_pct")
    vrp_pct_n = r.get("vrp_pct_n")
    iv30 = r.get("iv30")
    em_pct = r.get("expected_move_pct")
    em_expiry = r.get("em_expiry")
    em_dte = r.get("em_dte")
    front_skew = r.get("front_skew")
    term_9d_30d = r.get("term_ratio_9d_30d")
    term_30d_3m = r.get("term_ratio_30d_3m")

    # VRP hero — its own emphasized line above the KV rows.
    hero = ""
    if vrp is not None:
        if vrp_pct is not None and vrp_pct >= 67:
            vrp_color, tag = POS_GREEN, "rich"
        elif vrp_pct is not None and vrp_pct <= 33:
            vrp_color, tag = NEG_RED, "cheap"
        else:
            vrp_color, tag = LABEL_GRAY, "fair"
        tag_bit = (
            f' <span style="{_SANS}font-size:11px;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:0.5px;color:{vrp_color};">'
            f'{tag}</span>' if vrp_pct is not None else ""
        )
        hero = (
            f'<div style="background:{PANEL_BG};border-left:3px solid {vrp_color};'
            f'border-radius:0 4px 4px 0;padding:8px 12px;margin:2px 0 8px;">'
            f'<span style="{_SANS}font-size:10px;color:{LABEL_GRAY};'
            f'letter-spacing:0.6px;text-transform:uppercase;">Vol risk premium</span>'
            f'{tag_bit}<br>'
            f'<span style="{_MONO}font-size:16px;font-weight:700;color:{vrp_color};">'
            f'{_fmt_vrp(vrp, vrp_pct, vrp_pct_n)}</span>'
            f'</div>'
        )

    rows: list[tuple[str, str]] = []
    if iv30:
        em_str = _fmt_expected_move(em_pct, em_expiry, em_dte)
        iv_val = f"{iv30:.1f}%" + (f" · {em_str}" if em_str != "—" else "")
        rows.append(("IV30 / EM", iv_val))
    if front_skew is not None:
        rows.append(("Skew (25Δ)", _fmt_skew(front_skew)))
    term_str = _fmt_term_ratios(term_9d_30d, term_30d_3m)
    if term_str:
        rows.append(("VIX term", term_str))

    if not hero and not rows:
        return ""
    rows_html = "".join(_kv_cell(label, value) for label, value in rows)
    table = _kv_table(rows_html) if rows_html else ""
    return f'<div style="margin:8px 0 6px;">{hero}{table}</div>'


# ── Key Levels — single-column, mirrors the dashboard Regime tab ───────

def _key_levels_block(r: dict) -> str:
    spot = r.get("spot")
    zgl = r.get("zero_gamma_level")
    cw = r.get("call_wall")
    pw = r.get("put_wall")
    em_pct = r.get("expected_move_pct")

    def _shift(key: str) -> str:
        v = r.get(key)
        return f" ({v:+.1f}% 5d)" if v is not None else ""

    rows: list[tuple[str, str]] = []
    if zgl is not None:
        rows.append(("γ-flip", f"{zgl:,.0f}  {_fmt_signed_pct(_pct_from_spot(spot, zgl))}{_shift('zgl_5d_shift')}"))
    if cw is not None:
        rows.append(("Call wall", f"{cw:,.0f}  {_fmt_signed_pct(_pct_from_spot(spot, cw))}{_shift('call_wall_5d_shift')}"))
    if pw is not None:
        rows.append(("Put wall", f"{pw:,.0f}  {_fmt_signed_pct(_pct_from_spot(spot, pw))}{_shift('put_wall_5d_shift')}"))
    if em_pct is not None:
        rows.append(("Expected move", f"±{em_pct:.1f}%"))

    if not rows:
        return ""
    rows_html = "".join(_kv_cell(label, value) for label, value in rows)
    return _kv_table(rows_html)


# ── Per-ticker card ───────────────────────────────────────────────────

INDEX_NAME = {
    "SPY": "S&P 500",
    "QQQ": "Nasdaq 100",
    "IWM": "Russell 2000",
}


def _ticker_card(r: dict) -> str:
    ticker = r["ticker"]
    index_name = INDEX_NAME.get(ticker, "")
    spot = r.get("spot")

    if r.get("error"):
        return (
            f'<table width="100%" cellpadding="0" cellspacing="0" '
            f'style="border-collapse:collapse;margin-bottom:16px;'
            f'border:1px solid {RULE_COLOR};border-radius:8px;background:{PANEL_BG};">'
            f'<tr><td style="padding:14px 16px;">'
            f'<span style="{_SANS}display:inline-block;background:{LABEL_GRAY};color:#fff;'
            f'font-size:12px;font-weight:700;padding:2px 8px;border-radius:4px;">{ticker}</span>'
            f'<div style="{_SANS}color:{NEG_RED};font-size:12px;margin-top:8px;">'
            f'Load failed: {r.get("error", "unknown")}</div>'
            f'</td></tr></table>'
        )

    net_gex = r.get("net_gex") or 0
    if net_gex > 0:
        accent, regime_txt, regime_color = REGIME_COLOR["positive"], "Dealers stabilizing", POS_GREEN
    elif net_gex < 0:
        accent, regime_txt, regime_color = REGIME_COLOR["negative"], "Dealers amplifying", NEG_RED
    else:
        accent, regime_txt, regime_color = "#64748b", "Dealers neutral", LABEL_GRAY

    day_pct = r.get("price_change_pct")
    day_bit = ""
    if day_pct is not None:
        dcol = POS_GREEN if day_pct >= 0 else NEG_RED
        day_bit = (
            f'<span style="{_MONO}font-size:12px;font-weight:600;color:{dcol};">'
            f'{_fmt_signed_pct(day_pct)}</span>'
        )
    spot_cell = (
        f'<div style="{_MONO}font-size:20px;font-weight:700;color:{INK};line-height:1;">'
        f'{spot:,.0f}</div>{day_bit}' if spot else "&nbsp;"
    )

    # Card header — ticker badge + index name on the left, spot + day% on the right.
    header = (
        f'<table width="100%" cellpadding="0" cellspacing="0" border="0" '
        f'style="border-collapse:collapse;">'
        f'<tr>'
        f'<td style="vertical-align:middle;">'
        f'<span style="{_SANS}display:inline-block;background:{MAST_BG};color:#fff;'
        f'font-size:14px;font-weight:700;letter-spacing:0.5px;padding:3px 9px;'
        f'border-radius:4px;">{ticker}</span>'
        f'<span style="{_SANS}font-size:12px;color:{LABEL_GRAY};margin-left:8px;">{index_name}</span>'
        f'</td>'
        f'<td align="right" style="vertical-align:middle;">{spot_cell}</td>'
        f'</tr></table>'
        f'<div style="{_SANS}font-size:11px;font-weight:700;color:{regime_color};'
        f'letter-spacing:0.5px;text-transform:uppercase;margin-top:8px;">'
        f'&#9679; {regime_txt}</div>'
    )

    read_html = _read_block(r)
    vol_html = _vol_snapshot_block(r)
    levels_html = _key_levels_block(r)

    # Clean panel: hairline border, subtle fill, rounded corners, left accent bar
    # keyed to the net-GEX sign. Single-column, stacked — renders identically on
    # mobile mail clients.
    return (
        f'<table width="100%" cellpadding="0" cellspacing="0" '
        f'style="border-collapse:separate;margin-bottom:16px;'
        f'border:1px solid {RULE_COLOR};border-radius:8px;overflow:hidden;'
        f'background:#ffffff;">'
        f'<tr>'
        f'<td width="4" style="background:{accent};width:4px;"></td>'
        f'<td style="padding:14px 16px 16px;">{header}{read_html}{vol_html}{levels_html}</td>'
        f'</tr></table>'
    )



# ── OI by expiry table ────────────────────────────────────────────────

def _oi_summary_table(expiry_oi_df: "pd.DataFrame | None") -> "str | None":
    """Compact top-3 expiry OI table for email insertion after _ticker_card().

    Returns None when expiry_oi_df is None or empty (caller omits silently).
    T-16.5-08: guard against malformed df via None/empty check + safe head(3).

    Deliberately fewer columns than the dashboard's OI Impact tab (which also
    shows raw OI count and 5d-avg-share context) — a mobile-width email table
    can't fit 8 columns without forcing horizontal scroll/overlap, so this
    keeps only Expiry/DTE/OI Share/P:C Ratio/Impact. Impact text is allowed to
    wrap (no nowrap) since it's a phrase, not a number.
    """
    if expiry_oi_df is None:
        return None
    try:
        if expiry_oi_df.empty:
            return None
    except AttributeError:
        return None

    top3 = expiry_oi_df.head(3)

    th_style = (
        f'style="{_SANS}padding:4px 10px 4px 0;font-size:11px;'
        f'color:{LABEL_GRAY};letter-spacing:0.5px;text-transform:uppercase;'
        f'text-align:left;"'
    )
    td_style = (
        f'style="{_MONO}padding:4px 10px 4px 0;font-size:12px;'
        f'white-space:nowrap;"'
    )
    td_impact_style = (
        f'style="{_SANS}padding:4px 0 4px 0;font-size:12px;"'
    )

    header_row = (
        f'<tr>'
        f'<th {th_style}>Expiry</th>'
        f'<th {th_style}>DTE</th>'
        f'<th {th_style}>OI Share</th>'
        f'<th {th_style}>P:C Ratio</th>'
        f'<th {th_style}>Impact</th>'
        f'</tr>'
    )

    def _fmt_pct(v) -> str:
        try:
            fv = float(v)
            return f"{fv:.1f}%"
        except Exception:
            return "—"

    def _fmt_ratio(v) -> str:
        try:
            fv = float(v)
            return f"{fv:.2f}" if fv == fv else "—"  # fv == fv is False for NaN
        except Exception:
            return "—"

    data_rows = ""
    for _, row in top3.iterrows():
        try:
            import datetime as _dt
            expiry_raw = row.get("expiry", "")
            expiry_str = (
                _dt.datetime.strptime(str(expiry_raw), "%Y-%m-%d").strftime("%b %d")
                if expiry_raw else str(expiry_raw)
            )
        except (ValueError, TypeError):
            expiry_str = str(row.get("expiry", ""))
        dte = int(round(float(row.get("dte", 0)))) if row.get("dte") is not None else 0
        impact = format_oi_impact(row.get("pct_of_total"), row.get("put_call_ratio"))
        data_rows += (
            f'<tr>'
            f'<td {td_style}>{expiry_str}</td>'
            f'<td {td_style}>{dte}</td>'
            f'<td {td_style}>{_fmt_pct(row.get("pct_of_total"))}</td>'
            f'<td {td_style}>{_fmt_ratio(row.get("put_call_ratio"))}</td>'
            f'<td {td_impact_style}>{impact}</td>'
            f'</tr>'
        )

    table = (
        f'<table cellpadding="0" cellspacing="0" border="0" '
        f'style="border-collapse:collapse;width:100%;">'
        f'{header_row}{data_rows}'
        f'</table>'
    )

    label = (
        f'<div style="{_SANS}font-size:11px;color:{LABEL_GRAY};'
        f'letter-spacing:0.5px;text-transform:uppercase;margin-bottom:6px;">'
        f'OI IMPACT BY EXPIRY · 14 DTE primary (≤{config.GEX_MAX_DTE} DTE context)</div>'
    )

    return (
        f'<div style="margin-top:12px;margin-bottom:12px;padding-top:12px;'
        f'border-top:1px solid {RULE_COLOR};">'
        f'{label}{table}'
        f'</div>'
    )

# ── Header block: snapshot timestamp + methodology caveat banner ──────

def _snapshot_timestamp_line(r: dict) -> str:
    """Plain, small, gray fact line — real fetch time + the two fixed freshness
    facts (OI T-1, Greeks 15-min delayed). Omitted entirely when fetched_at is
    unavailable (cold-start-safe) — never rendered as a placeholder."""
    fetched_at = r.get("fetched_at")
    if fetched_at is None:
        return ""
    ts = fetched_at.strftime("%Y-%m-%d %H:%M")
    return (
        f'<div style="{_SANS}font-size:12px;color:{LABEL_GRAY};margin:0 0 10px;">'
        f'Snapshot {ts} ET &middot; OI T-1 &middot; Greeks 15-min delayed</div>'
    )


# ── Section header ────────────────────────────────────────────────────

def _section_header(label: str) -> str:
    return (
        f'<div style="{_SANS}font-size:12px;font-weight:700;letter-spacing:1.4px;'
        f'text-transform:uppercase;color:{INK};margin:22px 0 12px;'
        f'padding-bottom:6px;border-bottom:2px solid {ACCENT};">{label}</div>'
    )


# ── Masthead & footer ─────────────────────────────────────────────────

def _masthead(date: datetime.date) -> str:
    """Branded report header — deep-navy bar with title, tagline, and date.
    Sets the 'professional research desk' tone before any content."""
    date_str = f"{date.strftime('%A, %B')} {date.day}, {date.year}"
    return (
        f'<table width="100%" cellpadding="0" cellspacing="0" border="0" '
        f'style="border-collapse:collapse;">'
        f'<tr><td style="background:{MAST_BG};padding:20px 22px;'
        f'border-radius:8px 8px 0 0;">'
        f'<div style="{_SANS}color:#ffffff;font-size:20px;font-weight:700;'
        f'letter-spacing:0.4px;">Index Vol Diagnostics</div>'
        f'<div style="{_SANS}color:{MAST_SUB};font-size:12px;margin-top:4px;'
        f'letter-spacing:0.3px;">Dealer gamma &amp; implied-vol brief &middot; SPY / QQQ / IWM</div>'
        f'<div style="height:3px;width:44px;background:{ACCENT};margin:12px 0 0;"></div>'
        f'<div style="{_SANS}color:{MAST_SUB};font-size:11px;margin-top:10px;'
        f'text-transform:uppercase;letter-spacing:0.8px;">{date_str}</div>'
        f'</td></tr></table>'
    )


def _footer() -> str:
    """Fine print — descriptive-only disclaimer, restrained and small."""
    return (
        f'<div style="border-top:1px solid {RULE_COLOR};margin-top:22px;padding-top:14px;">'
        f'<div style="{_SANS}font-size:10px;color:{LABEL_GRAY};line-height:1.6;">'
        f'Descriptive diagnostics only — no predictive or prescriptive claims. '
        f'VRP percentiles ranked vs a ~10-year vol-index window; chain-derived '
        f'metrics accrue from daily snapshots. Not investment advice.'
        f'</div></div>'
    )


def _methodology_caveat_banner() -> str:
    """Static (never gated) framed note — light tint + gold left accent bar,
    matching the report's brand vocabulary."""
    return (
        f'<div style="{_SANS}font-size:12px;color:{INK};'
        f'background:#f1f5f9;border-left:3px solid {ACCENT};'
        f'padding:10px 14px;margin:16px 0;line-height:1.5;border-radius:0 4px 4px 0;">'
        f'<b style="color:{INK};">Methodology note:</b> '
        f'<span style="color:{LABEL_GRAY};">Trust GEX direction first; '
        f'absolute GEX level varies by source.</span>'
        f'</div>'
    )


# ── VRP at-a-glance strip — cross-ticker premium headline ─────────────

def _vrp_strip(index_results: list[dict]) -> str:
    """A compact cross-ticker VRP headline placed at the very top of the email.

    One cell per ticker: percentile (hero number, rich/cheap coloured) + the
    signed VRP in vol points beneath. This is the single most-actionable summary
    of the vol work — it lets the PM see rich/cheap across SPY/QQQ/IWM at a glance
    before scrolling into the per-ticker detail. Omitted when no ticker has a
    credible VRP percentile yet (cold start)."""
    cells: list[str] = []
    for r in index_results:
        if r.get("error"):
            continue
        vrp = r.get("vrp")
        vrp_pct = r.get("vrp_pct")
        if vrp is None or vrp_pct is None:
            continue
        if vrp_pct >= 67:
            color, tag = POS_GREEN, "rich"
        elif vrp_pct <= 33:
            color, tag = NEG_RED, "cheap"
        else:
            color, tag = "#64748b", "fair"
        cells.append(
            f'<td align="center" style="padding:10px 4px;vertical-align:top;'
            f'border-left:1px solid {RULE_COLOR};">'
            f'<div style="{_SANS}font-size:12px;font-weight:700;color:{INK};'
            f'letter-spacing:0.5px;">{r.get("ticker","")}</div>'
            f'<div style="{_MONO}font-size:24px;font-weight:700;color:{color};'
            f'line-height:1.2;margin:3px 0 0;">{vrp_pct}<span style="font-size:11px;">th</span></div>'
            f'<div style="{_SANS}font-size:10px;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:0.5px;color:{color};">{tag}</div>'
            f'<div style="{_MONO}font-size:12px;color:{LABEL_GRAY};margin-top:2px;">'
            f'{vrp:+.1f}pp</div>'
            f'</td>'
        )
    if not cells:
        return ""
    # First cell shouldn't have a left divider — strip it.
    cells[0] = cells[0].replace(f'border-left:1px solid {RULE_COLOR};', '', 1)
    return (
        f'<div style="border:1px solid {RULE_COLOR};border-radius:8px;'
        f'background:{PANEL_BG};margin:16px 0;overflow:hidden;">'
        f'<div style="{_SANS}font-size:11px;font-weight:700;letter-spacing:0.8px;'
        f'text-transform:uppercase;color:{LABEL_GRAY};padding:10px 14px 0;">'
        f'Vol risk premium &middot; percentile vs ~10yr</div>'
        f'<table width="100%" cellpadding="0" cellspacing="0" border="0" '
        f'style="border-collapse:collapse;"><tr>{"".join(cells)}</tr></table>'
        f'</div>'
    )


# ── Evolution section ─────────────────────────────────────────────────

def _evolution_largest_move_line(ticker: str, metrics: dict) -> str:
    import math
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
        return f"{ticker}: insufficient history yet."

    _, key, value = max(ranked, key=lambda x: x[0])
    label, up_word, down_word = defs[key]
    direction = up_word if value >= 0 else down_word
    return f"{ticker}: {label} {direction} ({value:+.2f}pp)."


def _evolution_horizon_summary_line(evolution_data: dict) -> str:
    def _fmt_level(v: float | None) -> str:
        import math
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return "—"
        return f"{v:+.2f}pp"

    horizons = ("5d", "10d", "30d")
    parts: list[str] = []
    for horizon in horizons:
        vals = []
        for ticker in ("SPY", "QQQ", "IWM"):
            level = (
                evolution_data.get(ticker, {})
                .get("horizons", {})
                .get(horizon, {})
                .get("level")
            )
            vals.append(_fmt_level(level))
        parts.append(f"{horizon} [{vals[0]}/{vals[1]}/{vals[2]}]")
    return " | ".join(parts)


def evolution_section_html(evolution_data: dict) -> str | None:
    """Build the Surface Evolution cross-ticker table for the email top section.

    evolution_data: {'SPY': {level, rms, skew_change, term_change, as_of}, 'QQQ': ..., 'IWM': ...}

    Returns None (omit entirely) on cold start — when all scalars across all tickers are None.
    Returns an HTML string otherwise.
    """
    _SCALAR_KEYS = ("level", "rms", "skew_change", "term_change")

    all_none = all(
        all(ticker_data.get(k) is None for k in _SCALAR_KEYS)
        for ticker_data in evolution_data.values()
    )
    if all_none:
        return None

    # Lead sentence based on SPY level (D-12 Claude's discretion)
    spy_data = evolution_data.get("SPY", {})
    spy_level = spy_data.get("level")
    as_of = spy_data.get("as_of")

    if spy_level is None:
        lead = "Five-day rolling mean — cross-ticker."
    elif spy_level > 0.5:
        lead = "Surfaces moved higher over the 5-day rolling mean."
    elif spy_level < -0.5:
        lead = "Surfaces moved lower over the 5-day rolling mean."
    else:
        lead = "Surfaces largely unchanged over the 5-day rolling mean."

    if as_of is not None:
        as_of_str = as_of.strftime("%b %d, %Y") if hasattr(as_of, "strftime") else str(as_of)
        lead += f" As of {as_of_str}."

    # Table header
    th_style = (
        f'style="{_SANS}padding:5px 10px 5px 0;font-size:11px;'
        f'color:{LABEL_GRAY};letter-spacing:0.5px;text-transform:uppercase;'
        f'border-bottom:1px solid {RULE_COLOR};text-align:left;"'
    )
    td_style = (
        f'style="{_MONO}padding:5px 10px 5px 0;font-size:13px;font-weight:600;'
        f'white-space:nowrap;"'
    )
    td_ticker_style = (
        f'style="{_SANS}padding:5px 10px 5px 0;font-size:13px;font-weight:700;'
        f'white-space:nowrap;"'
    )

    header_row = (
        f'<tr>'
        f'<th {th_style}>Ticker</th>'
        f'<th {th_style}>Level</th>'
        f'<th {th_style}>RMS</th>'
        f'<th {th_style}>Skew Chg</th>'
        f'<th {th_style}>Term Chg</th>'
        f'</tr>'
    )

    def _pp(v: float | None) -> str:
        import math
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return "—"
        return f"{v:+.2f}pp"

    ticker_rows = ""
    for ticker in ("SPY", "QQQ", "IWM"):
        d = evolution_data.get(ticker, {})
        ticker_rows += (
            f'<tr>'
            f'<td {td_ticker_style}>{ticker}</td>'
            f'<td {td_style}>{_pp(d.get("level"))}</td>'
            f'<td {td_style}>{_pp(d.get("rms"))}</td>'
            f'<td {td_style}>{_pp(d.get("skew_change"))}</td>'
            f'<td {td_style}>{_pp(d.get("term_change"))}</td>'
            f'</tr>'
        )

    table = (
        f'<table cellpadding="0" cellspacing="0" border="0" '
        f'style="border-collapse:collapse;width:100%;margin-top:10px;">'
        f'{header_row}{ticker_rows}'
        f'</table>'
    )

    lead_html = (
        f'<p style="{_SANS}font-size:13px;margin:10px 0 6px;color:{LABEL_GRAY};">{lead}</p>'
    )

    move_lines = " ".join(
        _evolution_largest_move_line(ticker, evolution_data.get(ticker, {}))
        for ticker in ("SPY", "QQQ", "IWM")
    )
    summary_html = (
        f'<p style="{_SANS}font-size:13px;margin:2px 0 8px;color:{LABEL_GRAY};">'
        f'<b>What changed most today:</b> {move_lines}</p>'
    )
    horizon_summary_html = (
        f'<p style="{_SANS}font-size:12px;margin:2px 0 10px;color:{LABEL_GRAY};">'
        f'<b>Level by horizon (SPY/QQQ/IWM):</b> '
        f'{_evolution_horizon_summary_line(evolution_data)}</p>'
    )

    return _section_header("Surface Evolution — 5-day") + lead_html + summary_html + horizon_summary_html + table


# ── Main ──────────────────────────────────────────────────────────────

def build_email(
    index_results: list[dict],
    date: datetime.date | None = None,
    evolution_data: dict | None = None,
    png_note: str | None = None,
    oi_data: "dict | None" = None,
) -> str:
    date = date or datetime.date.today()

    if oi_data is not None:
        blocks = []
        for r in index_results:
            card_html = _ticker_card(r)
            oi_table = _oi_summary_table(oi_data.get(r["ticker"]))
            blocks.append(card_html + (oi_table or ""))
        cards = "\n".join(blocks)
    else:
        cards = "\n".join(_ticker_card(r) for r in index_results)

    failed = [r["ticker"] for r in index_results if r.get("error")]
    failed_note = (
        f'<p style="{_SANS}color:{NEG_RED};font-size:12px;margin-top:8px;">'
        f'Failed to load: {", ".join(failed)}</p>' if failed else ""
    )

    # Header block: snapshot-freshness timestamp + methodology caveat banner
    # (D-01, D-02) — inserted directly below the section header, above Evolution.
    primary = next((r for r in index_results if not r.get("error")), None)
    ts_line = _snapshot_timestamp_line(primary) if primary else ""
    caveat_banner = _methodology_caveat_banner()
    vrp_strip = _vrp_strip(index_results)
    masthead = _masthead(date)
    footer = _footer()

    # Evolution section — omitted entirely on cold start (D-10, D-11)
    evol_html = ""
    if evolution_data is not None:
        evol_section = evolution_section_html(evolution_data)
        if evol_section:
            evol_html = evol_section

    # PNG fallback note — rendered below ticker cards (D-05)
    png_note_html = ""
    if png_note:
        png_note_html = (
            f'<p style="{_SANS}font-size:12px;color:{LABEL_GRAY};margin-top:8px;">{png_note}</p>'
        )

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="{_SANS}margin:0;padding:0;background:#ffffff;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:{PAGE_BG};">
  <tr><td align="center" style="padding:24px 16px;background:{PAGE_BG};">
    <table width="100%" cellpadding="0" cellspacing="0" style="max-width:390px;{_SANS}
      background:#ffffff;border:1px solid {RULE_COLOR};border-radius:8px;overflow:hidden;">
      <tr><td>{masthead}</td></tr>
      <tr><td style="padding:6px 20px 20px;">

  {ts_line}
  {caveat_banner}
  {vrp_strip}
  {evol_html}
  {_section_header("Ticker Detail")}
  {cards}
  {failed_note}
  {png_note_html}
  {footer}

      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>
"""



