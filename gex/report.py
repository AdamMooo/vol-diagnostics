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

# Sign-of-net-gex visual cue for the accent bar.
REGIME_COLOR = {
    "positive": "#16a34a",  # green-600
    "negative": "#dc2626",  # red-600
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
POS_GREEN   = "#16a34a"
NEG_RED     = "#dc2626"

_SANS = "font-family:Arial,Helvetica,sans-serif;"
_MONO = "font-family:Consolas,'SF Mono',Menlo,monospace;"


# ── Formatting helpers ────────────────────────────────────────────────

def _fmt_b(val: float | None) -> str:
    if val is None:
        return "—"
    b = val / 1e9
    return f"{'+' if b >= 0 else ''}{b:.2f}B"


def _fmt_price(val: float | None, dp: int = 2) -> str:
    return f"{val:,.{dp}f}" if val is not None else "—"


def _fmt_pct(val: float | None, signed: bool = True, dp: int = 1) -> str:
    if val is None:
        return "—"
    sign = "+" if signed and val >= 0 else ""
    return f"{sign}{val:.{dp}f}%"


def _fmt_skew(val: float | None) -> str:
    if val is None:
        return "—"
    return f"{val:+.1f}pp"


def _fmt_hedge_shares(val: float | None) -> str:
    if val is None:
        return "—"
    v = abs(val)
    if v >= 1e6:
        return f"{v / 1e6:.1f}M sh/$1"
    elif v >= 1e3:
        return f"{v / 1e3:.0f}K sh/$1"
    return f"{v:.0f} sh/$1"


def _pct_from_spot(spot: float | None, level: float | None) -> float | None:
    if not spot or level is None:
        return None
    return (level - spot) / spot * 100


def _signed_color(val: float | None) -> str:
    if val is None or val == 0:
        return LABEL_GRAY
    return POS_GREEN if val >= 0 else NEG_RED


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


# ── Wall insight ──────────────────────────────────────────────────────

def _wall_value(level: float | None, pct_from_spot: float | None) -> str:
    """Format a wall as: '740  +0.3%' (anchor strike, distance from spot).

    Concentration % was removed intentionally — it changes daily with OI rotation
    and measures noise, not structural support. The strike itself is the signal.
    """
    if level is None:
        return "—"
    parts = [f"{level:,.0f}"]
    if pct_from_spot is not None:
        parts.append(
            f'<span style="font-weight:600;margin-left:10px;font-size:13px;">'
            f'{_fmt_pct(pct_from_spot)}</span>'
        )
    return "".join(parts)


def _expected_1d_range_pct(iv30: float | None) -> float | None:
    """1-sigma 1-day expected move in % of spot, from IV30 (annualized vol in %)."""
    if not iv30:
        return None
    return iv30 / (252 ** 0.5)


def _pin_location(spot: float | None, pw: float | None, cw: float | None) -> str:
    """How close is spot to call wall vs put wall, as a percentage of the range."""
    if spot is None or pw is None or cw is None or cw <= pw:
        return "—"
    pct = (spot - pw) / (cw - pw) * 100
    pct = max(0.0, min(100.0, pct))
    direction = "→ CW" if pct >= 50 else "← PW"
    return f"{pct:.0f}% {direction}"


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

    # Accent bar color is driven purely by the *sign* of net gex — no hand-tuned
    # neutral-floor label, since the value below already shows sign and magnitude.
    net_gex_for_color = r.get("net_gex") or 0
    if net_gex_for_color > 0:
        accent = REGIME_COLOR["positive"]
    elif net_gex_for_color < 0:
        accent = REGIME_COLOR["negative"]
    else:
        accent = "#64748b"

    spot = r.get("spot")
    pct_chg = r.get("price_change_pct") or 0.0
    net_gex = r.get("net_gex")

    iv30 = r.get("iv30") or 0.0
    iv30_str = f"{iv30:.1f}%" if iv30 else "—"

    zgl = r.get("zero_gamma_level")
    vs_zgl = _pct_from_spot(spot, zgl)
    # vs_zgl is (zgl - spot)/spot; we want spot-vs-ZGL i.e. (spot-zgl)/spot.
    vs_zgl_spot = (-vs_zgl) if vs_zgl is not None else None

    # Walls — single max one-sided GEX strike. Empirically observable, no smoothing.
    # We deliberately do NOT show the GEX-weighted cluster center: the ±2% / top-3
    # band parameters are arbitrary and add estimation noise the reader cannot audit.
    cw = r.get("call_wall")
    pw = r.get("put_wall")
    cw_pct = _pct_from_spot(spot, cw)
    pw_pct = _pct_from_spot(spot, pw)
    range_width_pct = (
        (cw - pw) / spot * 100 if (cw is not None and pw is not None and spot) else None
    )

    expected_1d = _expected_1d_range_pct(iv30)
    expected_str = f"±{expected_1d:.2f}%" if expected_1d else "—"

    # Left column: spot/price-action + structural levels (the "where am I" lens)
    left_rows = (
        _kv_cell("Spot",   _fmt_price(spot))
        + _kv_cell("Day %", _fmt_pct(pct_chg) if pct_chg else "—",
                   value_color=_signed_color(pct_chg) if pct_chg else None)
        + _kv_cell("IV30 / 1d σ", f"{iv30_str} &middot; {expected_str}", mono=False)
        + _kv_cell("γ-flip", _fmt_price(zgl, dp=1) if zgl is not None else "—")
        + _kv_cell("vs γ-flip",
                   _fmt_pct(vs_zgl_spot) if vs_zgl_spot is not None else "—",
                   value_color=_signed_color(vs_zgl_spot))
    )

    # Right column: dealer positioning + wall context (the "what's holding it" lens)
    right_rows = (
        _kv_cell("Net GEX", _fmt_b(net_gex), value_color=_signed_color(net_gex))
        + _kv_cell("Hedge Shares/$1", _fmt_hedge_shares(r.get("delta_hedge_flow")))
        + _kv_cell("Skew (25Δ)", _fmt_skew(r.get("front_skew")))
        + _kv_cell("Call Wall", _wall_value(cw, cw_pct))
        + _kv_cell("Put Wall",  _wall_value(pw, pw_pct))
        + _kv_cell("Range",
                   f"{range_width_pct:.1f}% &middot; {_pin_location(spot, pw, cw)}"
                   if range_width_pct is not None else "—")
    )

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


# ── Main ──────────────────────────────────────────────────────────────

def build_email(
    index_results: list[dict],
    purpose_results: list[dict] | None = None,
    date: datetime.date | None = None,
) -> str:
    """purpose_results retained for signature compat; ignored (3-ticker focus)."""
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
        '<b>Skew (25Δ)</b>: IV(25Δ put) − IV(50Δ call) for the nearest expiry ≥7 DTE, '
        'in percentage points. Relative cost of downside protection vs upside exposure. '
        'Xing, Zhang & Zhao (2010, JFQA) found steeper skew predicts subsequent '
        'underperformance (10.9% annual alpha). Higher = puts more expensive = elevated fear.<br>'
        '<b>Call Wall / Put Wall</b>: the single strike with the largest one-sided GEX, with '
        'distance from spot. Use the <i>strike</i> as a hard level; one-sided magnitude is '
        'methodology-dependent and not shown.<br>'
        '<b>Range</b>: width between walls as % of spot &middot; pin location of spot inside the range.'
        '<br><br>'
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

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
</head>
<body style="{_SANS}margin:0;padding:0;">
<table width="100%" cellpadding="0" cellspacing="0">
  <tr><td align="center" style="padding:20px;">
    <table width="720" cellpadding="0" cellspacing="0" style="width:720px;max-width:720px;{_SANS}">
      <tr><td>

  {_section_header("Equity Index Dealer Flow &middot; " + date.strftime("%b %d, %Y").replace(" 0", " "))}
  {cards}
  {failed_note}
  {methodology_footer}

      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>
"""
