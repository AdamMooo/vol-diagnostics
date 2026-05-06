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

TICKER_LABEL = {
    "SPY":   "SPY  S&P 500",
    "QQQ":   "QQQ  Nasdaq 100",
    "IWM":   "IWM  Russell 2000",
    "XLF":   "XLF  Financials",
    "GLD":   "GLD  Gold",
    "TLT":   "TLT  20yr Treasury",
    "NVDA":  "NVDA  Nvidia",
    "TSLA":  "TSLA  Tesla",
    "AAPL":  "AAPL  Apple",
    "AMD":   "AMD  AMD",
    "META":  "META  Meta",
    "AMZN":  "AMZN  Amazon",
    "GOOGL": "GOOGL  Alphabet",
    "MSFT":  "MSFT  Microsoft",
    "AVGO":  "AVGO  Broadcom",
    "COIN":  "COIN  Coinbase",
    "COST":  "COST  Costco",
    "NFLX":  "NFLX  Netflix",
    "PLTR":  "PLTR  Palantir",
    "UNH":   "UNH  UnitedHealth",
    "EEM":   "EEM  MSCI EM",
    "EFA":   "EFA  MSCI EAFE",
    "HYG":   "HYG  High Yield",
}


# ── Formatting ────────────────────────────────────────────────────────

def _fmt_gex(val: float) -> str:
    b = val / 1e9
    return f"{'+'if b>=0 else ''}{b:.2f}B"


def _fmt_price(val: float | None) -> str:
    return f"{val:.2f}" if val is not None else "—"


def _fmt_distance(spot: float, zero_gamma: float | None) -> tuple[str, str]:
    if zero_gamma is None:
        return "—", "#aaa"
    pct = (spot - zero_gamma) / spot * 100
    color = "#1a7a4a" if pct >= 0 else "#c0392b"
    return f"{'+'if pct>=0 else ''}{pct:.1f}%", color


def _fmt_delta_flow(val: float | None) -> str:
    if val is None:
        return "—"
    return f"${abs(val)/1e9:.1f}B/1%"


_VS_YESTERDAY_COLOR = {
    "FLIPPED":     "#c0392b",
    "INTENSIFIED": "#e67e22",
    "EASED":       "#27ae60",
    "UNCHANGED":   "#7f8c8d",
}


def _vs_color(label: str | None) -> str:
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

def _scorecard(results: list[dict], label: str) -> str:
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
            f'margin-right:4px;margin-bottom:4px;display:inline-block;">'
            f'{r["ticker"]}</span>'
        )

    if n_neg == 0 and n_pos > 0:
        summary_line = f"{n_pos}/{len(valid)} positive — broad positive gamma"
    elif n_pos == 0 and n_neg > 0:
        summary_line = f"{n_neg}/{len(valid)} negative — broad negative gamma, moves amplified"
    elif n_pos > n_neg:
        summary_line = f"{n_pos}/{len(valid)} positive — positive majority with some stress pockets"
    elif n_neg > n_pos:
        summary_line = f"{n_neg}/{len(valid)} negative — negative majority"
    else:
        summary_line = f"{n_pos} positive / {n_neg} negative — mixed"

    return f"""
<div style="margin-bottom:6px;">
  <div style="font-size:10px;font-weight:700;letter-spacing:1.4px;text-transform:uppercase;
              color:#64748b;margin-bottom:6px;">{label}</div>
  <div style="margin-bottom:6px;line-height:1.8;">{pills}</div>
  <div style="font-size:12px;color:#555;">{summary_line}</div>
</div>"""


# ── Observations (data-derived, no hardcoded opinions) ────────────────

def _observations(index_results: list[dict]) -> str:
    r = {x["ticker"]: x for x in index_results if not x.get("error")}
    lines = []

    spy = r.get("SPY", {})
    qqq = r.get("QQQ", {})
    iwm = r.get("IWM", {})

    us_regimes = {t: r[t]["gamma_regime"] for t in ["SPY", "QQQ", "IWM"] if t in r}
    n_pos = sum(1 for v in us_regimes.values() if v == "positive")

    if len(us_regimes) == 3:
        if n_pos == 3:
            lines.append(
                "<b>US equity:</b> positive gamma across the full cap stack — "
                "dealer hedging is stabilising across large, growth, and small cap."
            )
        elif n_pos == 0:
            lines.append(
                "<b>US equity:</b> negative gamma across the cap stack — "
                "dealer hedging amplifies moves; intraday ranges likely elevated."
            )
        elif us_regimes.get("IWM") != "positive" and n_pos == 2:
            lines.append(
                "<b>US equity:</b> large and growth cap pinned (SPY/QQQ), "
                "small cap (IWM) in negative gamma — breadth divergence."
            )

    xlf = r.get("XLF", {})
    if xlf.get("gamma_regime") == "negative" and spy.get("gamma_regime") == "positive":
        lines.append(
            "<b>Financials:</b> XLF in negative gamma while SPY stabilises — "
            "sector positioning diverging from broad market."
        )

    tlt = r.get("TLT", {})
    if tlt.get("gamma_regime") == "negative":
        lines.append(
            "<b>Rates:</b> TLT negative gamma — rate moves self-reinforcing; "
            "duration-sensitive equity and credit worth monitoring."
        )

    gld = r.get("GLD", {})
    if gld.get("gamma_regime") == "positive" and spy.get("gamma_regime") == "negative":
        lines.append(
            "<b>Gold:</b> GLD positive gamma while equities are negative — "
            "safe-haven positioning elevated relative to risk assets."
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


# ── Index table ───────────────────────────────────────────────────────

def _index_row(r: dict, idx: int = 0) -> str:
    if r.get("error"):
        return (
            f'<tr><td style="padding:8px 10px;font-weight:bold;color:#aaa;">'
            f'{TICKER_LABEL.get(r["ticker"], r["ticker"])}</td>'
            f'<td colspan="6" style="color:#e74c3c;padding:8px 10px;font-size:12px;">Load failed</td></tr>'
        )
    bg = "#fff" if idx % 2 == 0 else "#fafafa"
    regime = r.get("gamma_regime", "neutral")
    gex_bg = GEX_CELL_BG.get(regime, "#f8f9fa")
    dist, dist_color = _fmt_distance(r.get("spot", 0), r.get("zero_gamma_level"))

    return (
        f'<tr style="background:{bg};">'
        f'<td style="padding:9px 10px;font-weight:600;font-size:13px;">{TICKER_LABEL.get(r["ticker"], r["ticker"])}</td>'
        f'<td align="right" style="padding:9px 10px;font-size:13px;">{_fmt_price(r.get("spot"))}</td>'
        f'<td align="right" style="padding:9px 10px;font-family:monospace;font-size:13px;background:{gex_bg};font-weight:bold;">{_fmt_gex(r.get("net_gex", 0))}</td>'
        f'<td align="center" style="padding:9px 10px;">{_badge(regime)}</td>'
        f'<td align="right" style="padding:9px 10px;font-size:13px;color:{dist_color};font-weight:600;">{dist}</td>'
        f'<td align="right" style="padding:9px 10px;font-size:13px;color:#555;">{_fmt_delta_flow(r.get("delta_hedge_flow"))}</td>'
        f'<td align="center" style="padding:9px 10px;font-size:13px;color:{_vs_color(r.get("vs_yesterday"))};">{r.get("vs_yesterday") or "—"}</td>'
        f'</tr>'
    )


def _index_table(results: list[dict]) -> str:
    rows = "".join(_index_row(r, i) for i, r in enumerate(results))
    return f"""
<table width="100%" cellpadding="0" cellspacing="0"
       style="border-collapse:collapse;background:#fff;border-radius:8px;
              box-shadow:0 1px 6px rgba(0,0,0,.08);font-size:13px;margin-bottom:6px;overflow:hidden;">
  <thead>
    <tr style="background:#34495e;color:#ecf0f1;font-size:12px;">
      <th align="left"   style="padding:11px 10px;font-weight:600;">Instrument</th>
      <th align="right"  style="padding:11px 8px;font-weight:600;">Spot</th>
      <th align="right"  style="padding:11px 8px;font-weight:600;">Net GEX</th>
      <th align="center" style="padding:11px 8px;font-weight:600;">Regime</th>
      <th align="right"  style="padding:11px 8px;font-weight:600;">vs ZGL</th>
      <th align="right"  style="padding:11px 8px;font-weight:600;">&#916;-flow</th>
      <th align="center" style="padding:11px 8px;font-weight:600;">vs Yesterday</th>
    </tr>
  </thead>
  <tbody>{rows}</tbody>
</table>"""


# ── Purpose table ─────────────────────────────────────────────────────

def _purpose_row(r: dict, idx: int = 0) -> str:
    if r.get("error"):
        return (
            f'<tr><td style="padding:8px 10px;font-weight:bold;color:#aaa;">'
            f'{TICKER_LABEL.get(r["ticker"], r["ticker"])}</td>'
            f'<td colspan="7" style="color:#e74c3c;padding:8px 10px;font-size:12px;">Load failed</td></tr>'
        )
    bg = "#fff" if idx % 2 == 0 else "#fafafa"
    regime = r.get("gamma_regime", "neutral")
    gex_bg = GEX_CELL_BG.get(regime, "#f8f9fa")
    dist, dist_color = _fmt_distance(r.get("spot", 0), r.get("zero_gamma_level"))
    iv30 = r.get("iv30", 0.0)
    iv30_str = f"{iv30:.1f}%" if iv30 else "—"
    ee_s = r.get("early_exercise_strikes", 0)
    ee_str = f"{ee_s} strikes" if ee_s > 0 else "—"
    ee_color = "#c0392b" if ee_s > 20 else ("#e67e22" if ee_s > 5 else "#27ae60")
    pct_chg = r.get("price_change_pct", 0.0)
    pct_str = f"{'+'if pct_chg>=0 else ''}{pct_chg:.2f}%" if pct_chg else "—"
    pct_color = "#1a7a4a" if pct_chg >= 0 else "#c0392b"

    return (
        f'<tr style="background:{bg};">'
        f'<td style="padding:8px 10px;font-weight:600;font-size:12px;">{TICKER_LABEL.get(r["ticker"], r["ticker"])}</td>'
        f'<td align="right" style="padding:8px 8px;font-size:12px;">{_fmt_price(r.get("spot"))}</td>'
        f'<td align="right" style="padding:8px 8px;font-size:12px;color:{pct_color};font-weight:600;">{pct_str}</td>'
        f'<td align="right" style="padding:8px 8px;font-family:monospace;font-size:12px;background:{gex_bg};font-weight:bold;">{_fmt_gex(r.get("net_gex", 0))}</td>'
        f'<td align="center" style="padding:8px 8px;">{_badge(regime)}</td>'
        f'<td align="right" style="padding:8px 8px;font-size:12px;color:#555;">{iv30_str}</td>'
        f'<td align="right" style="padding:8px 8px;font-size:12px;color:{dist_color};font-weight:600;">{dist}</td>'
        f'<td align="center" style="padding:8px 8px;font-size:12px;color:{ee_color};font-weight:600;">{ee_str}</td>'
        f'<td align="center" style="padding:8px 8px;font-size:12px;color:{_vs_color(r.get("vs_yesterday"))};">{r.get("vs_yesterday") or "—"}</td>'
        f'</tr>'
    )


def _purpose_table(results: list[dict]) -> str:
    rows = "".join(_purpose_row(r, i) for i, r in enumerate(results))
    return f"""
<table width="100%" cellpadding="0" cellspacing="0"
       style="border-collapse:collapse;background:#fff;border-radius:8px;
              box-shadow:0 1px 6px rgba(0,0,0,.08);font-size:12px;margin-bottom:6px;overflow:hidden;">
  <thead>
    <tr style="background:#2c3e50;color:#ecf0f1;font-size:11px;">
      <th align="left"   style="padding:10px 10px;font-weight:600;">Name</th>
      <th align="right"  style="padding:10px 8px;font-weight:600;">Spot</th>
      <th align="right"  style="padding:10px 8px;font-weight:600;">Day %</th>
      <th align="right"  style="padding:10px 8px;font-weight:600;">Net GEX</th>
      <th align="center" style="padding:10px 8px;font-weight:600;">Regime</th>
      <th align="right"  style="padding:10px 8px;font-weight:600;">IV30</th>
      <th align="right"  style="padding:10px 8px;font-weight:600;">vs ZGL</th>
      <th align="center" style="padding:10px 8px;font-weight:600;">Early Exercise</th>
      <th align="center" style="padding:10px 8px;font-weight:600;">vs Yesterday</th>
    </tr>
  </thead>
  <tbody>{rows}</tbody>
</table>"""


# ── Chart grid ────────────────────────────────────────────────────────

def _chart_grid(charts_b64: dict[str, str], section_tickers: list[str], title: str) -> str:
    tickers = [t for t in section_tickers if t in charts_b64]
    if not tickers:
        return ""
    rows = ""
    for t in tickers:
        rows += (
            f'<div style="margin-bottom:18px;">'
            f'<img src="data:image/png;base64,{charts_b64[t]}" '
            f'style="width:100%;border:1px solid #e2e8f0;border-radius:6px;display:block;">'
            f'</div>'
        )
    return f"""
<div style="font-size:10px;font-weight:700;letter-spacing:1.6px;text-transform:uppercase;
            color:#64748b;border-bottom:1px solid #e2e8f0;padding-bottom:5px;
            margin:24px 0 14px;">{title} — Charts</div>
{rows}"""


# ── Section header ────────────────────────────────────────────────────

def _section_header(label: str) -> str:
    return (
        f'<div style="font-size:10px;font-weight:700;letter-spacing:1.6px;'
        f'text-transform:uppercase;color:#64748b;border-bottom:1px solid #e2e8f0;'
        f'padding-bottom:5px;margin:20px 0 10px;">{label}</div>'
    )


# ── Main ──────────────────────────────────────────────────────────────

def build_email(
    index_results: list[dict],
    purpose_results: list[dict],
    date: datetime.date | None = None,
    charts_b64: dict[str, str] | None = None,
) -> str:
    date = date or datetime.date.today()
    charts_b64 = charts_b64 or {}

    index_tickers   = [r["ticker"] for r in index_results]
    purpose_tickers = [r["ticker"] for r in purpose_results]

    obs_html = _observations(index_results)

    failed = [r["ticker"] for r in (index_results + purpose_results) if r.get("error")]
    failed_note = (
        f'<p style="color:#e74c3c;font-size:12px;margin-top:8px;">'
        f'Failed to load: {", ".join(failed)}</p>' if failed else ""
    )

    return f"""
<html><body style="font-family:Arial,sans-serif;background:#f0f2f5;padding:20px;margin:0;">
<div style="max-width:820px;margin:0 auto;">

  <h2 style="color:#2c3e50;margin-bottom:2px;font-size:20px;">GEX Daily Report</h2>
  <p style="color:#95a5a6;margin-top:0;margin-bottom:16px;font-size:12px;">
    {date.strftime("%A, %B %d, %Y").replace(" 0", " ")}
    &nbsp;&middot;&nbsp; CBOE delayed chains &nbsp;&middot;&nbsp; American-style options
    &nbsp;&middot;&nbsp; Dealer gamma exposure
  </p>

  {_section_header("Index")}
  {_scorecard(index_results, "Index")}
  {obs_html}
  {_index_table(index_results)}

  {_section_header("Purpose Yield Shares")}
  <p style="font-size:11px;color:#94a3b8;margin:0 0 8px;">
    Underlyings for weekly options writing &middot; American options &middot;
    Early Exercise = deep ITM calls (delta &gt;0.85, extrinsic &lt;2%)
  </p>
  {_scorecard(purpose_results, "Purpose Yield Shares")}
  {_purpose_table(purpose_results)}

  {failed_note}

  {_chart_grid(charts_b64, index_tickers, "Index")}
  {_chart_grid(charts_b64, purpose_tickers, "Purpose Yield Shares")}

</div>
</body></html>
"""
