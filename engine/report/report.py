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

# Sign-of-net-gex visual cue — muted, report-grade tones (email-local;
# the dashboard keeps config.PALETTE untouched).
POS_GREEN   = "#2e7355"   # muted forest green — "good" (rich / stabilizing / up)
NEG_RED     = "#a8483f"   # muted brick red   — "bad"  (cheap / amplifying / down)
REGIME_COLOR = {
    "positive": POS_GREEN,
    "negative": NEG_RED,
    "zero":     "#6b6880",
}

# Badge backgrounds (solid color with white text — survive theme inversion).
TICKER_LABEL = {
    "SPY": "SPY  S&P 500",
    "QQQ": "QQQ  Nasdaq 100",
    "IWM": "IWM  Russell 2000",
}

# ── Report palette — dark-purple fintech, restrained ───────────────────
INK         = "#211b2e"   # primary text — dark purple-charcoal
LABEL_GRAY  = "#6b6880"   # secondary text & labels — muted purple-slate
RULE_COLOR  = "#e6e3ee"   # hairline dividers
PANEL_BG    = "#f7f5fb"   # subtle card / panel fill (faint lavender)
PAGE_BG     = "#edeaf3"   # page backdrop behind the white report sheet
MAST_BG     = "#2b2140"   # masthead deep purple (the single brand color)
MAST_SUB    = "#b7aecb"   # masthead subtitle text
ACCENT      = "#6a5a95"   # structural accent — muted purple (rules, bars)
BAR_TRACK   = "#e6e3ee"   # percentile-bar track

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


# ── Read line (the "so what") — one concise sentence, no chip clutter ──

def _read_block(r: dict) -> str:
    """A single plain-English 'so what' line — the soft lean from the canonical
    build_card_read. The chip pills were dropped: they duplicated the VRP tag and
    the dealer-regime label already shown in the card header, adding color noise
    without new information. Gated inputs ride on the summary (read_skew_pct /
    read_move_5d) so the email read matches the dashboard."""
    read = build_card_read(
        r, skew_pct=r.get("read_skew_pct"), move_5d=r.get("read_move_5d"),
    )
    if not read.lean:
        return ""
    return (
        f'<div style="{_SANS}font-size:13px;font-weight:600;color:{INK};'
        f'line-height:1.45;margin:10px 0 12px;">{read.lean}</div>'
    )


# ── Percentile bar — the one lightweight visual (pure CSS, client-safe) ─

def _pct_bar(pct: int | None, color: str) -> str:
    """A thin 0-100 percentile track with a filled portion — renders in every
    mail client (nested tables, no images). Gives the VRP a real visual anchor
    without external chart attachments."""
    if pct is None:
        return ""
    pct = max(0, min(100, int(pct)))
    return (
        f'<table width="100%" cellpadding="0" cellspacing="0" border="0" '
        f'style="border-collapse:collapse;margin-top:5px;"><tr>'
        f'<td style="background:{color};height:4px;width:{pct}%;font-size:0;line-height:0;'
        f'border-radius:2px;">&nbsp;</td>'
        f'<td style="background:{BAR_TRACK};height:4px;font-size:0;line-height:0;">&nbsp;</td>'
        f'</tr></table>'
    )


# ── Metrics table — one clean table per card (vol + key levels merged) ──

def _metrics_table(r: dict) -> str:
    """A single, tightly-scoped metrics table per ticker. Merges the vol snapshot
    (VRP / IV30 / skew / VIX term) with the key levels (γ-flip / walls / expected
    move) into ONE clean table instead of two — less visual chrome, one scan path.

    Strategic field set (only what an income-sleeve PM acts on):
      VRP (coloured), IV30, Skew, VIX term (SPY only), γ-flip, Call/Put wall,
      Expected move. Reads precomputed summary fields only (no I/O)."""
    spot = r.get("spot")
    vrp = r.get("vrp")
    vrp_pct = r.get("vrp_pct")
    vrp_pct_n = r.get("vrp_pct_n")
    iv30 = r.get("iv30")
    em_pct = r.get("expected_move_pct")
    front_skew = r.get("front_skew")
    term_9d_30d = r.get("term_ratio_9d_30d")
    term_30d_3m = r.get("term_ratio_30d_3m")
    zgl = r.get("zero_gamma_level")
    cw = r.get("call_wall")
    pw = r.get("put_wall")

    def _shift(key: str) -> str:
        v = r.get(key)
        return f" ({v:+.1f}% 5d)" if v is not None else ""

    # (label, value, value_color) — color None means default INK.
    rows: list[tuple[str, str, str | None]] = []

    # VRP first — the hero metric, coloured by rich/cheap.
    if vrp is not None:
        if vrp_pct is not None and vrp_pct >= 67:
            vrp_color = POS_GREEN
        elif vrp_pct is not None and vrp_pct <= 33:
            vrp_color = NEG_RED
        else:
            vrp_color = INK
        rows.append(("VRP", _fmt_vrp(vrp, vrp_pct, vrp_pct_n), vrp_color))
    if iv30:
        rows.append(("IV30", f"{iv30:.1f}%", None))
    if front_skew is not None:
        rows.append(("Skew 25Δ", _fmt_skew(front_skew), None))
    term_str = _fmt_term_ratios(term_9d_30d, term_30d_3m)
    if term_str:
        rows.append(("VIX term", term_str, None))
    if zgl is not None:
        rows.append(("γ-flip", f"{zgl:,.0f}  {_fmt_signed_pct(_pct_from_spot(spot, zgl))}{_shift('zgl_5d_shift')}", None))
    if cw is not None:
        rows.append(("Call wall", f"{cw:,.0f}  {_fmt_signed_pct(_pct_from_spot(spot, cw))}{_shift('call_wall_5d_shift')}", None))
    if pw is not None:
        rows.append(("Put wall", f"{pw:,.0f}  {_fmt_signed_pct(_pct_from_spot(spot, pw))}{_shift('put_wall_5d_shift')}", None))
    if em_pct is not None:
        rows.append(("Expected move", f"±{em_pct:.1f}%", None))

    if not rows:
        return ""
    rows_html = "".join(_kv_cell(label, value, value_color=color) for label, value, color in rows)
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
        accent, regime_txt, regime_color = REGIME_COLOR["zero"], "Dealers neutral", LABEL_GRAY

    # Day % stays neutral gray — direction isn't a "good/bad" signal here, so
    # colouring it just adds noise. Green/red are reserved for VRP + regime.
    day_pct = r.get("price_change_pct")
    day_bit = (
        f'<div style="{_MONO}font-size:12px;font-weight:600;color:{LABEL_GRAY};'
        f'margin-top:2px;">{_fmt_signed_pct(day_pct)}</div>'
        if day_pct is not None else ""
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
    metrics_html = _metrics_table(r)

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
        f'<td style="padding:14px 16px 16px;">{header}{read_html}{metrics_html}</td>'
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
    """Branded report header — deep-purple bar with title, tagline, and date.
    Sets the fintech research-desk tone before any content."""
    date_str = f"{date.strftime('%A, %B')} {date.day}, {date.year}"
    return (
        f'<table width="100%" cellpadding="0" cellspacing="0" border="0" '
        f'style="border-collapse:collapse;">'
        f'<tr><td style="background:{MAST_BG};padding:20px 22px;'
        f'border-radius:8px 8px 0 0;">'
        f'<div style="{_SANS}color:#ffffff;font-size:19px;font-weight:700;'
        f'letter-spacing:0.4px;">Index Vol Diagnostics</div>'
        f'<div style="{_SANS}color:{MAST_SUB};font-size:12px;margin-top:4px;'
        f'letter-spacing:0.3px;">Dealer gamma &amp; implied-vol brief &middot; SPY / QQQ / IWM</div>'
        f'<div style="height:3px;width:44px;background:{ACCENT};margin:12px 0 0;"></div>'
        f'<div style="{_SANS}color:{MAST_SUB};font-size:11px;margin-top:10px;'
        f'text-transform:uppercase;letter-spacing:0.8px;">{date_str}</div>'
        f'</td></tr></table>'
    )


def _footer() -> str:
    """Fine print — one restrained disclaimer line. All the wordy static
    methodology copy was removed; this is the only fixed prose in the report."""
    return (
        f'<div style="border-top:1px solid {RULE_COLOR};margin-top:20px;padding-top:12px;">'
        f'<div style="{_SANS}font-size:10px;color:{LABEL_GRAY};line-height:1.5;">'
        f'Descriptive only, not advice &middot; VRP ranked vs ~10yr &middot; '
        f'OI T-1, greeks 15-min delayed &middot; trust GEX direction, not level.'
        f'</div></div>'
    )


# ── VRP at-a-glance strip — cross-ticker premium headline ─────────────

def _vrp_strip(index_results: list[dict]) -> str:
    """A compact cross-ticker VRP headline placed at the very top of the email.

    One cell per ticker: percentile (hero number, rich/cheap coloured) + a thin
    percentile bar + the signed VRP in vol points. The single most-actionable
    summary of the vol work — rich/cheap across SPY/QQQ/IWM at a glance. Omitted
    when no ticker has a credible VRP percentile yet (cold start)."""
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
            color, tag = LABEL_GRAY, "fair"
        cells.append(
            f'<td align="center" style="padding:12px 10px;vertical-align:top;'
            f'border-left:1px solid {RULE_COLOR};">'
            f'<div style="{_SANS}font-size:12px;font-weight:700;color:{INK};'
            f'letter-spacing:0.5px;">{r.get("ticker","")}</div>'
            f'<div style="{_MONO}font-size:23px;font-weight:700;color:{color};'
            f'line-height:1.2;margin:3px 0 0;">{vrp_pct}<span style="font-size:11px;">th</span></div>'
            f'<div style="{_SANS}font-size:10px;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:0.5px;color:{color};margin-bottom:2px;">{tag}</div>'
            f'{_pct_bar(vrp_pct, color)}'
            f'<div style="{_MONO}font-size:12px;color:{LABEL_GRAY};margin-top:4px;">'
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

    # Table header
    th_style = (
        f'style="{_SANS}padding:5px 10px 5px 0;font-size:11px;'
        f'color:{LABEL_GRAY};letter-spacing:0.5px;text-transform:uppercase;'
        f'border-bottom:1px solid {RULE_COLOR};text-align:left;"'
    )
    td_style = (
        f'style="{_MONO}padding:5px 10px 5px 0;font-size:13px;font-weight:600;'
        f'color:{INK};white-space:nowrap;"'
    )
    td_ticker_style = (
        f'style="{_SANS}padding:5px 10px 5px 0;font-size:13px;font-weight:700;'
        f'color:{INK};white-space:nowrap;"'
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

    move_lines = " ".join(
        _evolution_largest_move_line(ticker, evolution_data.get(ticker, {}))
        for ticker in ("SPY", "QQQ", "IWM")
    )
    summary_html = (
        f'<p style="{_SANS}font-size:12px;margin:0 0 8px;color:{INK};line-height:1.5;">'
        f'<b>What changed most today:</b> '
        f'<span style="color:{LABEL_GRAY};">{move_lines}</span></p>'
    )
    horizon_summary_html = (
        f'<p style="{_SANS}font-size:11px;margin:10px 0 0;color:{LABEL_GRAY};line-height:1.5;">'
        f'<b>Level by horizon (SPY/QQQ/IWM):</b> '
        f'{_evolution_horizon_summary_line(evolution_data)}</p>'
    )

    return _section_header("Surface Evolution — 5-day") + summary_html + table + horizon_summary_html


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

    # Snapshot-freshness timestamp (real fetch time) — small gray fact line.
    primary = next((r for r in index_results if not r.get("error")), None)
    ts_line = _snapshot_timestamp_line(primary) if primary else ""
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



