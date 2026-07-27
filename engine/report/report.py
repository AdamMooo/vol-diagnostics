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
)

# Sign-of-net-gex visual cue for the accent bar — reads from shared palette.
REGIME_COLOR = {
    "positive": config.PALETTE["positive"],
    "negative": config.PALETTE["negative"],
    "zero":     config.PALETTE["neutral"],
}

# Badge backgrounds (solid color with white text — survive theme inversion).
TICKER_LABEL = {
    "SPY": "SPY  S&P 500",
    "QQQ": "QQQ  Nasdaq 100",
    "IWM": "IWM  Russell 2000",
}

# Muted gray for labels & secondary text — reads on both #ffffff and #1f2937 backgrounds.
LABEL_GRAY  = "#94a3b8"
RULE_COLOR  = "#cbd5e1"  # thin divider rule — barely visible in dark mode (fine)
POS_GREEN   = config.PALETTE["positive"]
NEG_RED     = config.PALETTE["negative"]

_SANS = "font-family:Arial,Helvetica,sans-serif;"
_MONO = "font-family:Consolas,'SF Mono',Menlo,monospace;"


# ── Badges ────────────────────────────────────────────────────────────

# ── Key/value rows ────────────────────────────────────────────────────

def _kv_cell(label: str, value: str, value_color: str | None = None,
             mono: bool = True) -> str:
    """One label/value row. value_color arg retained for signature compat but
    intentionally ignored — values inherit the client theme color so light/dark
    modes both stay legible. Sign is already obvious from the +/- prefix."""
    value_family = _MONO if mono else _SANS
    return (
        f'<tr>'
        f'<td style="{_SANS}padding:7px 12px 7px 0;font-size:12px;color:{LABEL_GRAY};'
        f'letter-spacing:0.5px;text-transform:uppercase;white-space:nowrap;">'
        f'{label}</td>'
        f'<td align="right" style="{value_family}padding:7px 0;font-size:15px;'
        f'font-weight:600;white-space:nowrap;">{value}</td>'
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

def _ticker_card(r: dict) -> str:
    label = TICKER_LABEL.get(r["ticker"], r["ticker"])
    spot = r.get("spot")

    if r.get("error"):
        return (
            f'<table width="100%" cellpadding="0" cellspacing="0" '
            f'style="border-collapse:collapse;margin-bottom:18px;'
            f'border-bottom:1px solid {RULE_COLOR};">'
            f'<tr><td style="padding:12px 0 18px;">'
            f'<div style="{_SANS}font-size:14px;font-weight:700;color:{LABEL_GRAY};">{label}</div>'
            f'<div style="{_SANS}color:{NEG_RED};font-size:12px;margin-top:4px;">'
            f'Load failed: {r.get("error", "unknown")}</div>'
            f'</td></tr></table>'
        )

    net_gex_for_color = r.get("net_gex") or 0
    if net_gex_for_color > 0:
        accent = REGIME_COLOR["positive"]
    elif net_gex_for_color < 0:
        accent = REGIME_COLOR["negative"]
    else:
        accent = "#64748b"

    spot_bit = (
        f' <span style="{_MONO}font-size:13px;font-weight:400;color:{LABEL_GRAY};">'
        f'&middot; spot {spot:,.0f}</span>' if spot else ""
    )
    header = (
        f'<table width="100%" cellpadding="0" cellspacing="0" border="0" '
        f'style="border-collapse:collapse;">'
        f'<tr>'
        f'<td style="{_SANS}font-size:18px;font-weight:700;'
        f'letter-spacing:0.3px;padding-bottom:2px;">{label}{spot_bit}</td>'
        f'</tr></table>'
    )

    read_html = _read_block(r)
    levels_html = _key_levels_block(r)

    # No card background — accent bar on the left is the only visual cue.
    # Single-column, stacked — no side-by-side split, so it renders identically
    # on mobile mail clients (the old 50/50 two-column grid broke on phones).
    return (
        f'<table width="100%" cellpadding="0" cellspacing="0" '
        f'style="border-collapse:collapse;margin-bottom:14px;'
        f'border-bottom:1px solid {RULE_COLOR};">'
        f'<tr>'
        f'<td width="4" style="background:{accent};width:4px;"></td>'
        f'<td style="padding:8px 0 18px 16px;">{header}{read_html}{levels_html}</td>'
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


def _methodology_caveat_banner() -> str:
    """Static (never gated) framed block — visually distinct from the plain
    timestamp line via a light tint + left accent bar, reusing the file's other
    'framed block' vocabulary (the ticker-card accent bar)."""
    amber = config.PALETTE["accent"]
    return (
        f'<div style="{_SANS}font-size:12px;color:{LABEL_GRAY};'
        f'background:#f1f5f9;border-left:3px solid {amber};'
        f'padding:8px 12px;margin:0 0 16px;line-height:1.5;">'
        f'<b>Methodology note:</b> Trust GEX direction first; absolute GEX level varies by source.'
        f'</div>'
    )


# ── Section header ────────────────────────────────────────────────────

def _section_header(label: str) -> str:
    return (
        f'<div style="{_SANS}font-size:13px;font-weight:700;letter-spacing:1.6px;'
        f'text-transform:uppercase;color:{LABEL_GRAY};border-bottom:1px solid {RULE_COLOR};'
        f'padding-bottom:7px;margin:8px 0 18px;">{label}</div>'
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
<table width="100%" cellpadding="0" cellspacing="0">
  <tr><td align="center" style="padding:20px 16px;">
    <table width="100%" cellpadding="0" cellspacing="0" style="max-width:390px;{_SANS}">
      <tr><td>

  {_section_header("Index Vol Diagnostics &middot; " + f"{date.strftime('%B')} {date.day}, {date.year}")}
  {ts_line}
  {caveat_banner}
  {evol_html}
  {cards}
  {failed_note}
  {png_note_html}

      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>
"""



