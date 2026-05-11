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

# Regime colors — kept vivid enough to read on dark backgrounds.
REGIME_COLOR = {
    "positive": "#16a34a",  # green-600
    "negative": "#dc2626",  # red-600
    "neutral":  "#64748b",  # slate-500
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


def _fmt_delta_flow(val: float | None) -> str:
    if val is None:
        return "—"
    return f"${abs(val) / 1e9:.2f}B/1%"


def _pct_from_spot(spot: float | None, level: float | None) -> float | None:
    if not spot or level is None:
        return None
    return (level - spot) / spot * 100


def _signed_color(val: float | None) -> str:
    if val is None or val == 0:
        return LABEL_GRAY
    return POS_GREEN if val >= 0 else NEG_RED


# ── Badges ────────────────────────────────────────────────────────────

def _badge(regime: str) -> str:
    c = REGIME_COLOR.get(regime, "#64748b")
    return (
        f'<span style="background:{c};color:#ffffff;padding:3px 10px;'
        f'border-radius:4px;font-weight:700;font-size:11px;{_SANS}'
        f'letter-spacing:0.5px;white-space:nowrap;">{regime.upper()}</span>'
    )


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

    regime = r.get("gamma_regime", "neutral")
    accent = REGIME_COLOR.get(regime, "#64748b")

    spot = r.get("spot")
    pct_chg = r.get("price_change_pct") or 0.0
    net_gex = r.get("net_gex")

    iv30 = r.get("iv30") or 0.0
    iv30_str = f"{iv30:.1f}%" if iv30 else "—"

    zgl = r.get("zero_gamma_level")
    vs_zgl = _pct_from_spot(spot, zgl)
    # vs_zgl is (zgl - spot)/spot; we want spot-vs-ZGL i.e. (spot-zgl)/spot.
    vs_zgl_spot = (-vs_zgl) if vs_zgl is not None else None

    # Wall cluster (GEX-weighted center) — fall back to single-strike if cluster missing
    cw = r.get("call_wall_cluster") or r.get("call_wall")
    pw = r.get("put_wall_cluster")  or r.get("put_wall")
    cw_pct = _pct_from_spot(spot, cw)
    pw_pct = _pct_from_spot(spot, pw)
    range_width_pct = (
        (cw - pw) / spot * 100 if (cw is not None and pw is not None and spot) else None
    )

    expected_1d = _expected_1d_range_pct(iv30)
    expected_str = f"±{expected_1d:.2f}%" if expected_1d else "—"

    zgl_flow = r.get("zgl_flow_magnitude")
    zgl_flow_str = f"${zgl_flow / 1e9:.2f}B/1%" if zgl_flow else "—"

    # Left column: spot/price-action + structural levels (the "where am I" lens)
    left_rows = (
        _kv_cell("Spot",   _fmt_price(spot))
        + _kv_cell("Day %", _fmt_pct(pct_chg) if pct_chg else "—",
                   value_color=_signed_color(pct_chg) if pct_chg else None)
        + _kv_cell("IV30 / 1d σ", f"{iv30_str} &middot; {expected_str}", mono=False)
        + _kv_cell("Zero-γ", _fmt_price(zgl, dp=1) if zgl is not None else "—")
        + _kv_cell("vs ZGL",
                   _fmt_pct(vs_zgl_spot) if vs_zgl_spot is not None else "—",
                   value_color=_signed_color(vs_zgl_spot))
        + _kv_cell("ZGL flow", zgl_flow_str)
    )

    # Right column: dealer positioning + wall context (the "what's holding it" lens)
    right_rows = (
        _kv_cell("Net GEX", _fmt_b(net_gex), value_color=_signed_color(net_gex))
        + _kv_cell("Δ-flow",   _fmt_delta_flow(r.get("delta_hedge_flow")))
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
        f'<td align="right" style="white-space:nowrap;">'
        f'{_badge(regime)}'
        f'</td>'
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
        '<b>Glossary</b> (terms used above, in order)<br>'
        '<b>Spot</b>: current underlying price (CBOE, ~15-min delayed).<br>'
        '<b>Day %</b>: change vs prior session close.<br>'
        '<b>IV30 / 1d σ</b>: 30-day implied vol, then 1-sigma 1-day expected move (≈ IV30 / √252).<br>'
        '<b>Zero-γ (ZGL)</b>: spot level at which cumulative net GEX crosses zero. Linear interpolation of the profile sign change.<br>'
        '<b>vs ZGL</b>: % distance from spot to ZGL. Positive = spot above the flip (positive-gamma side, stabilising).<br>'
        '<b>ZGL flow</b>: dealer hedge flow per 1% spot move at ZGL — same units as Δ-flow. '
        'Large vs current Δ-flow → crossing ZGL triggers heavy hedging. Small → cosmetic crossing, thin OI near the level.<br>'
        '<b>Net GEX</b>: sum of strike-level gamma exposure. Sign convention: calls +, puts −. '
        'Positive = dealers long gamma (absorb moves, stabilising). Negative = dealers short gamma (amplify moves).<br>'
        '<b>Δ-flow</b>: dealer hedge flow at current spot per 1% move (= |Net GEX| / spot ÷ 0.01).<br>'
        '<b>Call Wall / Put Wall</b>: anchor strike with the largest one-sided GEX, with distance from spot. '
        'Use the <i>strike</i> as a hard level; magnitude is methodology-dependent.<br>'
        '<b>Range</b>: width between walls as % of spot &middot; pin location of spot inside the range.'
        '<br><br>'
        '<b>Method &middot; Data limitations (read before trading off this)</b><br>'
        '&bull; <b>OI is T-1.</b> Open interest reflects the prior session close — ZGL and walls describe '
        '<i>yesterday\'s</i> positioning. Intraday OI drift is not captured by free CBOE data.<br>'
        '&bull; <b>Quotes are ~15-min delayed.</b> Spot, IV, and chain mids are not live.<br>'
        '&bull; <b>Regime classification is hand-calibrated.</b> The neutral floor (|Net GEX| &lt; $200M) was '
        'tuned May 2026 to the current noise environment; it will drift as vol regime shifts and needs '
        'periodic rebasing. Use the sign, not the label, as the primary signal.<br>'
        '&bull; <b>Full-chain ≥ 1 DTE.</b> 0DTE is excluded for math consistency. Absolute GEX magnitude is '
        'methodology-dependent; treat as order of magnitude only. The robust outputs are <b>Net GEX sign</b>, '
        '<b>ZGL location</b>, and <b>wall strikes</b>.<br>'
        '&bull; <b>No realized-vol attribution.</b> This is a positioning monitor, not a forecaster. '
        'No event study, base rate, or backtest is shown — the sample we have is too short for inference.<br>'
        '<b>Universe</b>: SPY / QQQ / IWM. IWM divergence from SPY/QQQ is the cleanest small-cap stress tell.'
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
