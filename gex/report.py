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

from gex import config
from gex.card_model import (
    CardField, build_card_fields,
    _fmt_b, _fmt_price, _fmt_pct, _fmt_skew,
    _fmt_hedge_shares, _pct_from_spot, _wall_value,
    _expected_1d_range_pct, _pin_location, _signed_color,
)
from gex.validation import load_prior_snapshot

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

    left_fields = fields[:5]
    right_fields = fields[5:]

    left_rows = "".join(_kv_cell(f.label, f.value) for f in left_fields)
    right_rows = "".join(_kv_cell(f.label, f.value) for f in right_fields)

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

    # No card background — accent bar on the left is the only visual cue.
    return (
        f'<table width="100%" cellpadding="0" cellspacing="0" '
        f'style="border-collapse:collapse;margin-bottom:14px;'
        f'border-bottom:1px solid {RULE_COLOR};">'
        f'<tr>'
        f'<td width="4" style="background:{accent};width:4px;"></td>'
        f'<td style="padding:8px 0 18px 16px;">{header}{body}</td>'
        f'</tr></table>'
    )


# ── Section header ────────────────────────────────────────────────────

def _section_header(label: str) -> str:
    return (
        f'<div style="{_SANS}font-size:13px;font-weight:700;letter-spacing:1.6px;'
        f'text-transform:uppercase;color:{LABEL_GRAY};border-bottom:1px solid {RULE_COLOR};'
        f'padding-bottom:7px;margin:8px 0 18px;">{label}</div>'
    )


# ── Evolution section ─────────────────────────────────────────────────

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

    return _section_header("Surface Evolution — 5-day") + lead_html + table


# ── Main ──────────────────────────────────────────────────────────────

def build_email(
    index_results: list[dict],
    date: datetime.date | None = None,
    evolution_data: dict | None = None,
    png_note: str | None = None,
) -> str:
    date = date or datetime.date.today()

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
        '<b>Spot</b>: current underlying price (CBOE, ~15-min delayed).<br>'
        '<b>Day %</b>: change vs prior session close.<br>'
        '<b>IV30 / 1d σ</b>: 30-day implied vol, then 1-sigma 1-day move under a lognormal '
        'assumption (≈ IV30 / √252). Textbook stdev — not a forecast.<br>'
        '<b>γ-flip</b> (formerly "Zero-γ Level" / ZGL): spot level at which cumulative '
        'net GEX crosses zero. Linear interpolation of the profile sign change. '
        'Model construct — no peer-reviewed validation as a price level; interpret as '
        'the threshold where the gamma-hedging environment flips sign, not a price target.<br>'
        '<b>vs γ-flip</b>: % distance from spot to γ-flip. Positive = spot above the flip '
        '(stabilising dealer regime); negative = spot below (destabilising regime).<br>'
        '<b>Net GEX</b>: sum of strike-level gamma exposure. Calls +, puts −. '
        'Positive = dealers long gamma. Negative = dealers short gamma. '
        'The accent bar on the left of each card reflects the sign of this number; '
        'no categorical "positive/negative/neutral" regime label is shown because the '
        '$200M neutral cutoff would be hand-tuned and non-stationary.<br>'
        '<b>Hedge Shares/$1</b>: shares dealers must trade per $1 spot move to stay delta-neutral '
        '(= Net GEX ÷ (spot² × 0.01) = Γ_net × OI × 100). Positive = buy demand on up-moves; '
        'negative = sell pressure on up-moves. Prior label "Δ-flow" used an incorrect formula.<br>'
        '<b>Skew (25Δ)</b>: IV(25Δ put) − IV(25Δ call) for the nearest expiry ≥7 DTE, '
        'in percentage points. Relative cost of downside protection vs upside exposure. '
        'Xing, Zhang & Zhao (2010, JFQA) found steeper skew predicts subsequent '
        'underperformance (10.9% annual alpha). Higher = puts more expensive = elevated fear.<br>'
        '<b>Call Wall / Put Wall</b>: the single strike with the largest one-sided GEX, with '
        'distance from spot. Use the <i>strike</i> as a hard level; one-sided magnitude is '
        'methodology-dependent and not shown.<br>'
        '<b>Range</b>: width between walls as % of spot &middot; pin location of spot inside the range.<br>'
        '<b>OI Call Wall / OI Put Wall</b>: strike with the largest call or put open interest '
        '(assumption-free — no dealer model). Contrast with Call Wall / Put Wall above, which '
        'are GEX-weighted (dealer positioning model).<br>'
        '<br>'
        '<b>Data limitations — read before trading off this</b><br>'
        '&bull; <b>OI is T-1.</b> Open interest reflects the prior session close. γ-flip and walls '
        'describe <i>yesterday\'s</i> positioning. Intraday OI drift is not captured.<br>'
        '&bull; <b>Quotes are ~15-min delayed.</b> Spot, IV, and chain mids are not live.<br>'
        '&bull; <b>Full-chain ≥ 1 DTE.</b> 0DTE is excluded for math consistency. Absolute GEX '
        'magnitude is methodology-dependent (other commercial sources publish very different '
        'numbers on the same chain). Treat the <i>sign</i> and <i>order of magnitude</i> as '
        'load-bearing; treat absolute levels as conventions.<br>'
        '&bull; <b>No realized-vol attribution.</b> This is a positioning monitor, not a forecaster. '
        'No event study, base rate, or backtest is shown — the sample is too short for inference.<br>'
        '&bull; <b>Dealer positioning assumption.</b> GEX assumes dealers are net short all options '
        '(retail buys, dealers sell). Holds empirically in aggregate for SPY/QQQ/IWM; can be wrong '
        'at individual strikes with covered-call, vol-selling, or institutional flow dominant.<br>'
        '&bull; <b>What is genuinely defensible:</b> Net GEX (Gatheral/Bergomi-derivable; '
        'dealer positioning per Garleanu-Pedersen-Poteshman 2009, RFS), Hedge Shares/$1 '
        '(Egebjerg & Kokholm 2024 mechanism), <b>Skew (25Δ)</b> (Xing-Zhang-Zhao 2010, JFQA — '
        'only metric here with direct peer-reviewed predictive validity), IV30. '
        'γ-flip and wall strikes are model constructs (zero peer-reviewed papers as price '
        'levels) — read as descriptive positioning context, not predictions.<br>'
        '<b>Universe</b>: SPY / QQQ / IWM only — the standard dealer positioning convention '
        '(long calls, short puts) is empirically defensible for these names.'
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

  {_section_header("Equity Index Dealer Flow &middot; " + f"{date.strftime('%B')} {date.day}, {date.year}")}
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
