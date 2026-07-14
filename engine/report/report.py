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

from engine import config
from engine.report.card_model import (
    CardField, build_card_fields, build_card_read, split_compact_fields,
    _fmt_b, _fmt_price, _fmt_pct, _fmt_skew,
    _fmt_hedge_shares, _pct_from_spot, _wall_value,
    _expected_1d_range_pct, _pin_location, _signed_color, format_oi_impact,
)
from engine.data.validation import load_prior_snapshot
from engine.data.oi_history import load_oi_history

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


# ── Per-ticker card ───────────────────────────────────────────────────

def _ticker_card(r: dict) -> str:
    label = TICKER_LABEL.get(r["ticker"], r["ticker"])

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

    prior_row = load_prior_snapshot(ticker=r["ticker"], before_date=datetime.date.today())
    fields = build_card_fields(today_summary=r, prior_summary=prior_row)

    primary_fields, detail_fields = split_compact_fields(fields)
    ordered_fields = [*primary_fields, *detail_fields]
    left_fields = ordered_fields[:5]
    right_fields = ordered_fields[5:]

    left_rows = "".join(_kv_cell(f"{f.label} [{f.trust_tag}]", f.value) for f in left_fields)
    right_rows = "".join(_kv_cell(f"{f.label} [{f.trust_tag}]", f.value) for f in right_fields)

    header = (
        f'<table width="100%" cellpadding="0" cellspacing="0" border="0" '
        f'style="border-collapse:collapse;">'
        f'<tr>'
        f'<td style="{_SANS}font-size:18px;font-weight:700;'
        f'letter-spacing:0.3px;padding-bottom:2px;">{label}</td>'
        f'</tr></table>'
    )

    body = (
        f'<table width="100%" cellpadding="0" cellspacing="0" border="0" '
        f'style="border-collapse:collapse;margin-top:6px;">'
        f'<tr>'
        f'<td valign="top" width="50%" style="padding-right:18px;">'
        f'{_kv_table(left_rows)}</td>'
        f'<td valign="top" width="50%" style="padding-left:18px;">'
        f'{_kv_table(right_rows)}</td>'
        f'</tr></table>'
    )

    read_html = _read_block(r)

    # No card background — accent bar on the left is the only visual cue.
    return (
        f'<table width="100%" cellpadding="0" cellspacing="0" '
        f'style="border-collapse:collapse;margin-bottom:14px;'
        f'border-bottom:1px solid {RULE_COLOR};">'
        f'<tr>'
        f'<td width="4" style="background:{accent};width:4px;"></td>'
        f'<td style="padding:8px 0 18px 16px;">{header}{read_html}{body}</td>'
        f'</tr></table>'
    )



def _add_oi_history_context(expiry_oi_df: "pd.DataFrame | None", ticker: str) -> "pd.DataFrame | None":
    """Attach 5d OI-share context columns when history is available."""
    if expiry_oi_df is None:
        return None
    try:
        if expiry_oi_df.empty:
            return expiry_oi_df
    except AttributeError:
        return expiry_oi_df

    enriched = expiry_oi_df.copy()
    oi_hist = load_oi_history(ticker, days=5)
    if oi_hist.empty or not {"expiry", "pct_of_total"}.issubset(set(oi_hist.columns)):
        return enriched

    avg_share = oi_hist.groupby("expiry", dropna=True)["pct_of_total"].mean()
    avg_share_map = {str(k): float(v) for k, v in avg_share.items()}

    enriched["avg_pct_of_total_5d"] = [
        avg_share_map.get(str(expiry))
        for expiry in enriched["expiry"].tolist()
    ]
    enriched["vs_avg_pct_of_total_5d"] = [
        (float(pct) - avg_share_map[str(expiry)]) if str(expiry) in avg_share_map else None
        for expiry, pct in zip(enriched["expiry"].tolist(), enriched["pct_of_total"].tolist())
    ]
    return enriched
# ── OI by expiry table ────────────────────────────────────────────────

def _oi_summary_table(expiry_oi_df: "pd.DataFrame | None") -> "str | None":
    """Compact top-3 expiry OI table for email insertion after _ticker_card().

    Returns None when expiry_oi_df is None or empty (caller omits silently).
    T-16.5-08: guard against malformed df via None/empty check + safe head(3).
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
        f'style="{_SANS}padding:4px 12px 4px 0;font-size:11px;'
        f'color:{LABEL_GRAY};letter-spacing:0.5px;text-transform:uppercase;'
        f'text-align:left;"'
    )
    td_style = (
        f'style="{_MONO}padding:4px 12px 4px 0;font-size:12px;'
        f'white-space:nowrap;"'
    )

    header_row = (
        f'<tr>'
        f'<th {th_style}>Expiry</th>'
        f'<th {th_style}>DTE</th>'
        f'<th {th_style}>OI</th>'
        f'<th {th_style}>OI Share</th>'
        f'<th {th_style}>5d Avg Share</th>'
        f'<th {th_style}>vs 5d Avg</th>'
        f'<th {th_style}>P:C Ratio</th>'
        f'<th {th_style}>Impact</th>'
        f'</tr>'
    )

    def _k(v: float) -> str:
        return f"{v/1000:.0f}K"

    def _fmt_pct(v) -> str:
        try:
            fv = float(v)
            return f"{fv:.1f}%"
        except Exception:
            return "—"

    def _fmt_pp(v) -> str:
        try:
            fv = float(v)
            return f"{fv:+.1f}pp"
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
            f'<td {td_style}>{_k(row.get("oi", 0))}</td>'
            f'<td {td_style}>{_fmt_pct(row.get("pct_of_total"))}</td>'
            f'<td {td_style}>{_fmt_pct(row.get("avg_pct_of_total_5d"))}</td>'
            f'<td {td_style}>{_fmt_pp(row.get("vs_avg_pct_of_total_5d"))}</td>'
            f'<td {td_style}>{_fmt_ratio(row.get("put_call_ratio"))}</td>'
            f'<td style="{_SANS}padding:4px 12px 4px 0;font-size:12px;">{impact}</td>'
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

    return _section_header("Surface Evolution — 5-day") + lead_html + summary_html + table


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
            oi_table = _oi_summary_table(_add_oi_history_context(oi_data.get(r["ticker"]), r["ticker"]))
            blocks.append(card_html + (oi_table or ""))
        cards = "\n".join(blocks)
    else:
        cards = "\n".join(_ticker_card(r) for r in index_results)

    failed = [r["ticker"] for r in index_results if r.get("error")]
    failed_note = (
        f'<p style="{_SANS}color:{NEG_RED};font-size:12px;margin-top:8px;">'
        f'Failed to load: {", ".join(failed)}</p>' if failed else ""
    )

    methodology_footer = (
        f'<div style="{_SANS}font-size:12px;color:{LABEL_GRAY};line-height:1.7;'
        f'margin-top:24px;padding-top:14px;border-top:1px solid {RULE_COLOR};">'
        '<b>Glossary</b><br>'
        '<b>Quick assumptions (default)</b><br>'
        '&bull; Descriptive diagnostics only — no forecast or trade signal.<br>'
        '&bull; OI is T-1 and quotes are delayed (~15 min), so positioning is not live tape.<br>'
        '&bull; Positioning framing is 14 DTE primary, with ≤90 DTE secondary context.<br>'
        '&bull; VRP uses CBOE index-vol close minus RV20×100; scalar and percentile share one series.<br>'
        '<br>'
        '<b>Deep methodology details</b><br>'
        '<b>VRP</b>: CBOE index-vol close (VIX/VXN/RVX) minus RV20×100 (vol points), with RV20 '
        'from yfinance daily closes; percentile is computed on this same series. '
        'High = premium rich (selling well paid); low = cheap.<br>'
        '<b>Skew (25Δ)</b>: IV(25Δ put) − IV(25Δ call), nearest expiry ≥7 DTE, in pp. '
        'Higher = downside protection more bid. Only metric here with direct peer-reviewed '
        'predictive validity (Xing-Zhang-Zhao 2010, JFQA).<br>'
        '<b>Net GEX</b>: strike-level gamma exposure summed (calls +, puts −). Sign drives the '
        'card accent: positive = dealers long gamma (stabilising), negative = short (amplifying). '
        'No categorical label — the absolute level is a convention, only the sign is load-bearing.<br>'
        '<b>γ-flip</b>: spot level where cumulative net GEX crosses zero. Threshold where the '
        'hedging environment flips sign — a model construct, not a price target.<br>'
        '<b>Hedge Shares/$1</b>: shares dealers trade per $1 spot move to stay delta-neutral. '
        'Positive = buy demand on up-moves; negative = sell pressure.<br>'
        '<b>Call / Put Wall</b>: strike with the largest one-sided GEX (dealer model). '
        '<b>OI Wall</b>: strike with the largest open interest (assumption-free). Use the '
        '<i>strikes</i> as levels; one-sided magnitudes are methodology-dependent.<br>'
        '&bull; <b>OI views use the filtered positioning set</b> (OI ≥ 100, IV ≤ 300%, DTE ≤ 90, '
        '0DTE excluded).<br>'
        '&bull; <b>Sign &amp; order of magnitude are load-bearing; absolute GEX is not</b> — '
        'other sources publish very different numbers on the same chain.<br>'
        '&bull; <b>Descriptive, not predictive.</b> Positioning + vol context only — no forecast, '
        'event study, or backtest (sample too short).<br>'
        '<b>Universe</b>: SPY / QQQ / IWM — names where the dealer-net-short convention is '
        'empirically defensible.'
        '</div>'
    )

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
</head>
<body style="{_SANS}margin:0;padding:0;background:#ffffff;">
<table width="100%" cellpadding="0" cellspacing="0">
  <tr><td align="center" style="padding:20px;">
    <table width="720" cellpadding="0" cellspacing="0" style="width:720px;max-width:720px;{_SANS}">
      <tr><td>

  {_section_header("Index Vol Diagnostics &middot; " + f"{date.strftime('%B')} {date.day}, {date.year}")}
  {evol_html}
  {cards}
  {failed_note}
  {png_note_html}
  {methodology_footer}

      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>
"""







