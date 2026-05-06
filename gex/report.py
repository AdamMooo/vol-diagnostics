"""
Build the HTML email body from GEX summaries and embedded charts.
"""
from __future__ import annotations

import datetime

REGIME_COLOR = {
    "positive": "#1a7a4a",
    "negative": "#c0392b",
    "neutral":  "#7f8c8d",
}
REGIME_BG = {
    "positive": "#d5f5e3",
    "negative": "#fadbd8",
    "neutral":  "#ecf0f1",
}
GEX_CELL_BG = {
    "positive": "#eafaf1",
    "negative": "#fdf2f0",
    "neutral":  "#f8f9fa",
}

GROUPS: dict[str, list[str]] = {
    "US Equity":      ["SPY", "QQQ", "IWM", "XLF"],
    "International":  ["EEM", "EFA", "EWJ"],
    "Rates / Credit": ["TLT", "HYG"],
    "Commodities":    ["GLD"],
}

TICKER_LABEL = {
    "SPY": "SPY  S&P 500",
    "QQQ": "QQQ  Nasdaq 100",
    "IWM": "IWM  Russell 2000",
    "XLF": "XLF  Financials",
    "EEM": "EEM  MSCI EM",
    "EFA": "EFA  MSCI EAFE",
    "EWJ": "EWJ  Japan",
    "TLT": "TLT  20yr Treasury",
    "HYG": "HYG  High Yield",
    "GLD": "GLD  Gold",
}


# ── Formatting ────────────────────────────────────────────────────────

def _fmt_gex(val: float) -> str:
    b = val / 1e9
    return f"{'+'if b>=0 else ''}{b:.2f}B"


def _fmt_price(val: float | None) -> str:
    return f"{val:.2f}" if val is not None else "—"


def _fmt_distance(spot: float, zero_gamma: float | None) -> tuple[str, str]:
    """Returns (text, css_color)."""
    if zero_gamma is None:
        return "—", "#aaa"
    pct = (spot - zero_gamma) / spot * 100
    color = "#1a7a4a" if pct >= 0 else "#c0392b"
    return f"{'+'if pct>=0 else ''}{pct:.1f}%", color


def _fmt_delta_flow(val: float | None) -> str:
    if val is None:
        return "—"
    b = abs(val) / 1e9
    return f"${b:.1f}B/1%"


_VS_YESTERDAY_COLOR = {
    "FLIPPED":     "#c0392b",
    "INTENSIFIED": "#e67e22",
    "EASED":       "#27ae60",
    "UNCHANGED":   "#7f8c8d",
}


def _vs_yesterday_color(label: str | None) -> str:
    return _VS_YESTERDAY_COLOR.get(label or "", "#aaa")


def _badge(regime: str) -> str:
    c  = REGIME_COLOR.get(regime, "#999")
    bg = REGIME_BG.get(regime, "#eee")
    return (
        f'<span style="background:{bg};color:{c};padding:3px 9px;'
        f'border-radius:4px;font-weight:bold;font-size:11px;white-space:nowrap;">'
        f'{regime.upper()}</span>'
    )


# ── Scorecard strip ───────────────────────────────────────────────────

def _scorecard(results: list[dict]) -> str:
    """One-line regime summary: coloured ticker pills."""
    valid = [r for r in results if not r.get("error")]
    n_pos = sum(1 for r in valid if r["gamma_regime"] == "positive")
    n_neg = sum(1 for r in valid if r["gamma_regime"] == "negative")

    pills = ""
    for r in valid:
        c  = REGIME_COLOR.get(r["gamma_regime"], "#999")
        bg = REGIME_BG.get(r["gamma_regime"], "#eee")
        pills += (
            f'<span style="background:{bg};color:{c};padding:3px 10px;'
            f'border-radius:12px;font-size:12px;font-weight:bold;'
            f'margin-right:4px;display:inline-block;">'
            f'{r["ticker"]}</span>'
        )

    summary_text = f"{n_pos}/{len(valid)} positive gamma"
    if n_neg == 0:
        summary_text += " — broad stabilisation"
    elif n_pos > n_neg:
        summary_text += " — risk-on tilt, some pockets of stress"
    else:
        summary_text += " — negative gamma dominant, moves amplified"

    return f"""
<div style="background:#fff;border-radius:6px;padding:12px 16px;
            margin-bottom:14px;box-shadow:0 1px 4px rgba(0,0,0,.06);">
  <div style="margin-bottom:8px;">{pills}</div>
  <div style="font-size:12px;color:#555;">{summary_text}</div>
</div>"""


# ── Narrative ─────────────────────────────────────────────────────────

def _narrative(results: list[dict]) -> str:
    """Rule-based cross-asset observations — regenerated fresh from each day's data."""
    r = {x["ticker"]: x for x in results if not x.get("error")}

    lines = []

    # US Equity cap stack
    us = {t: r[t]["gamma_regime"] for t in ["SPY", "QQQ", "IWM"] if t in r}
    pos_count = sum(1 for v in us.values() if v == "positive")
    if len(us) == 3:
        if pos_count == 3:
            lines.append(
                "<b>US equity:</b> positive gamma across the full cap stack — "
                "dealers absorbing moves in large, growth, and small cap simultaneously."
            )
        elif pos_count == 2 and us.get("IWM") != "positive":
            lines.append(
                "<b>US equity:</b> large-cap and growth pinned (SPY/QQQ) but small-cap IWM "
                "in negative gamma — positioning concentrated in mega-cap; breadth risk if selling starts."
            )
        elif pos_count == 0:
            lines.append(
                "<b>US equity:</b> negative gamma across the cap stack — "
                "dealer hedging amplifies moves; intraday ranges likely elevated."
            )

    # Financials vs broad equity
    xlf_reg = r.get("XLF", {}).get("gamma_regime")
    spy_reg = r.get("SPY", {}).get("gamma_regime")
    if xlf_reg == "negative" and spy_reg == "positive":
        lines.append(
            "<b>Financials stress:</b> XLF in negative gamma while SPY stabilises — "
            "bank/credit sector positioning diverging from broad market; watch spreads and bank vol."
        )
    elif xlf_reg == "positive" and spy_reg == "negative":
        lines.append(
            "<b>Financials firm:</b> XLF stable while SPY negative — "
            "equity stress is not originating from the financial sector."
        )

    # Credit vs equity
    hyg_reg = r.get("HYG", {}).get("gamma_regime")
    if spy_reg == "positive" and hyg_reg == "negative":
        lines.append(
            "<b>Credit divergence:</b> HYG negative gamma while SPY stabilises — "
            "credit market pricing more stress than equity implies; potential leading indicator."
        )

    # Rates
    tlt_reg = r.get("TLT", {}).get("gamma_regime")
    if tlt_reg == "negative":
        lines.append(
            "<b>Rates:</b> TLT negative gamma — rate moves self-reinforcing; "
            "watch duration-sensitive equity and mortgage spreads."
        )

    # Japan / carry
    ewj_reg = r.get("EWJ", {}).get("gamma_regime")
    if ewj_reg == "negative" and spy_reg == "positive":
        lines.append(
            "<b>Yen carry watch:</b> EWJ in negative gamma while US positive — "
            "Japan dealer stress may signal carry unwind risk; monitor USD/JPY."
        )

    # International consensus
    intl = {t: r[t]["gamma_regime"] for t in ["EEM", "EFA", "EWJ"] if t in r}
    if all(v == "negative" for v in intl.values()) and len(intl) >= 2:
        lines.append(
            "<b>Global risk-off:</b> EM, developed ex-US, and Japan all in negative gamma — "
            "broad international dealer stress, USD strength likely."
        )

    if not lines:
        return ""
    items = "".join(f"<li style='margin-bottom:6px;'>{l}</li>" for l in lines)
    return f"""
<div style="background:#fff;border-radius:6px;padding:12px 16px;
            margin-bottom:14px;box-shadow:0 1px 4px rgba(0,0,0,.06);">
  <ul style="margin:0;padding-left:16px;font-size:13px;color:#2c3e50;line-height:1.6;">
    {items}
  </ul>
</div>"""


# ── Table ─────────────────────────────────────────────────────────────

def _result_row(r: dict, idx: int = 0) -> str:
    if r.get("error"):
        return (
            f'<tr><td style="padding:8px 10px;font-weight:bold;color:#aaa;">'
            f'{TICKER_LABEL.get(r["ticker"], r["ticker"])}</td>'
            f'<td colspan="6" style="color:#e74c3c;padding:8px 10px;font-size:12px;">'
            f'Load failed</td></tr>'
        )
    bg   = "#fff" if idx % 2 == 0 else "#fafafa"
    regime = r.get("gamma_regime", "neutral")
    gex_bg = GEX_CELL_BG.get(regime, "#f8f9fa")
    dist, dist_color = _fmt_distance(r.get("spot", 0), r.get("zero_gamma_level"))

    return (
        f'<tr style="background:{bg};">'
        f'<td style="padding:9px 10px;font-weight:600;font-size:13px;">'
        f'{TICKER_LABEL.get(r["ticker"], r["ticker"])}</td>'
        f'<td align="right" style="padding:9px 10px;font-size:13px;">'
        f'{_fmt_price(r.get("spot"))}</td>'
        f'<td align="right" style="padding:9px 10px;font-family:monospace;'
        f'font-size:13px;background:{gex_bg};font-weight:bold;">'
        f'{_fmt_gex(r.get("net_gex", 0))}</td>'
        f'<td align="center" style="padding:9px 10px;">'
        f'{_badge(regime)}</td>'
        f'<td align="right" style="padding:9px 10px;font-size:13px;'
        f'color:{dist_color};font-weight:600;">{dist}</td>'
        f'<td align="right" style="padding:9px 10px;font-size:13px;color:#555;">'
        f'{_fmt_delta_flow(r.get("delta_hedge_flow"))}</td>'
        f'<td align="center" style="padding:9px 10px;font-size:13px;'
        f'color:{_vs_yesterday_color(r.get("vs_yesterday"))};">'
        f'{r.get("vs_yesterday") or "—"}</td>'
        f'</tr>'
    )


def _build_table(results: list[dict]) -> str:
    ticker_to_group = {t: g for g, tickers in GROUPS.items() for t in tickers}
    rows_by_group: dict[str, list[dict]] = {g: [] for g in GROUPS}
    ungrouped: list[dict] = []

    for r in results:
        g = ticker_to_group.get(r["ticker"])
        (rows_by_group[g] if g else ungrouped).append(r)

    html = ""
    idx = 0
    for group, group_results in rows_by_group.items():
        if not group_results:
            continue
        html += (
            f'<tr><td colspan="7" style="background:#2c3e50;color:#ecf0f1;'
            f'padding:5px 10px;font-size:10px;font-weight:bold;letter-spacing:1.5px;">'
            f'{group.upper()}</td></tr>'
        )
        for r in group_results:
            html += _result_row(r, idx)
            idx += 1
    for r in ungrouped:
        html += _result_row(r, idx)
        idx += 1
    return html


# ── Chart grid ────────────────────────────────────────────────────────

def _chart_grid(charts_b64: dict[str, str]) -> str:
    if not charts_b64:
        return ""
    cells = ""
    tickers = list(charts_b64.keys())
    for i in range(0, len(tickers), 2):
        pair = tickers[i:i+2]
        cells += "<tr>"
        for t in pair:
            cells += (
                f'<td style="padding:5px;width:50%;vertical-align:top;">'
                f'<p style="margin:0 0 3px;font-size:11px;font-weight:bold;color:#34495e;">'
                f'{TICKER_LABEL.get(t, t)}</p>'
                f'<img src="data:image/png;base64,{charts_b64[t]}" '
                f'style="width:100%;border:1px solid #eee;border-radius:3px;"></td>'
            )
        if len(pair) == 1:
            cells += '<td style="width:50%;"></td>'
        cells += "</tr>"

    return f"""
<h3 style="color:#2c3e50;margin:20px 0 8px;font-size:14px;">Gamma Profiles</h3>
<table width="100%" cellpadding="0" cellspacing="0">{cells}</table>"""


# ── Main ──────────────────────────────────────────────────────────────

def build_email(results: list[dict],
                date: datetime.date | None = None,
                overview_b64: str | None = None,
                charts_b64: dict[str, str] | None = None) -> str:
    date = date or datetime.date.today()
    valid = [r for r in results if not r.get("error")]

    narrative  = _narrative(valid)
    table_rows = _build_table(results)
    chart_sec  = _chart_grid(charts_b64) if charts_b64 else ""

    failed = [r["ticker"] for r in results if r.get("error")]
    failed_note = (
        f'<p style="color:#e74c3c;font-size:12px;margin-top:8px;">'
        f'Failed to load: {", ".join(failed)}</p>' if failed else ""
    )

    return f"""
<html><body style="font-family:Arial,sans-serif;background:#f0f2f5;padding:20px;margin:0;">
<div style="max-width:780px;margin:0 auto;">

  <h2 style="color:#2c3e50;margin-bottom:2px;font-size:20px;">GEX Daily Report</h2>
  <p style="color:#95a5a6;margin-top:0;margin-bottom:16px;font-size:12px;">
    {date.strftime("%A, %B %d, %Y").replace(" 0", " ")}
    &nbsp;&middot;&nbsp; yfinance chains &nbsp;&middot;&nbsp; Dealer gamma exposure proxy
  </p>

  {narrative}

  <table width="100%" cellpadding="0" cellspacing="0"
         style="border-collapse:collapse;background:#fff;border-radius:8px;
                box-shadow:0 1px 6px rgba(0,0,0,.08);font-size:13px;margin-bottom:6px;
                overflow:hidden;">
    <thead>
      <tr style="background:#34495e;color:#ecf0f1;font-size:12px;">
        <th align="left"   style="padding:11px 10px;font-weight:600;">Instrument</th>
        <th align="right"  style="padding:11px 8px;font-weight:600;">Spot</th>
        <th align="right"  style="padding:11px 8px;font-weight:600;">Net GEX</th>
        <th align="center" style="padding:11px 8px;font-weight:600;">Regime</th>
        <th align="right"  style="padding:11px 8px;font-weight:600;">ZGL</th>
        <th align="right"  style="padding:11px 8px;font-weight:600;">&#916;-flow</th>
        <th align="center" style="padding:11px 8px;font-weight:600;">vs-Yesterday</th>
      </tr>
    </thead>
    <tbody>{table_rows}</tbody>
  </table>

  {failed_note}
  {chart_sec}

</div>
</body></html>
"""
