"""
Daily vol diagnostics for Purpose Yield ETF underlyings.

Usage:
    python -m gex.run_daily_yield            # compute + print, no email (dry-run default)
    python -m gex.run_daily_yield --dry-run  # explicit dry-run — saves HTML to out/
    python -m gex.run_daily_yield --send     # send email (or set GEX_SEND=1)

Scheduled via: runners/yield_daily.ps1 (Task Scheduler, 4:35 PM ET on trading days)

Snapshots accumulate in the same stores as the index pipeline:
    out/gex_snapshots.parquet          — scalar metrics (IV30, skew, RV20, VRP …)
    out/surface_history/surface_*.parquet — raw chain points per ticker

RV20 and VRP require ~20 trading days of spot history before they appear.
"""
from __future__ import annotations

import argparse
import datetime
import pathlib

import pandas_market_calendars as mcal
import pytz

from gex.compute import compute_ticker
from gex.validation import save_snapshot
from gex.surface_history import save_surface_snapshot
from gex import emailer

# CBOE ticker → Purpose ETF display label
YIELD_TICKERS: dict[str, str] = {
    "AMD":   "AMD (AMD) Yield Shares Purpose ETF",
    "META":  "META (META) Yield Shares Purpose ETF",
    "AAPL":  "Apple (AAPL) Yield Shares Purpose ETF",
    "AMZN":  "Amazon (AMZN) Yield Shares Purpose ETF",
    "TSLA":  "Tesla (TSLA) Yield Shares Purpose ETF",
    "BRK":   "Berkshire Hathaway (BRK) Yield Shares Purpose ETF",
    "GOOGL": "Alphabet (GOOGL) Yield Shares Purpose ETF",
    "MSFT":  "Microsoft (MSFT) Yield Shares Purpose ETF",
    "NVDA":  "NVIDIA (NVDA) Yield Shares Purpose ETF",
    "AVGO":  "Broadcom (AVGO) Yield Shares Purpose ETF",
    "COIN":  "Coinbase (COIN) Yield Shares Purpose ETF",
    "COST":  "Costco (COST) Yield Shares Purpose ETF",
    "JPM":   "Yield Shares (JPYS) Purpose ETF",
    "NFLX":  "Netflix (NFLX) Yield Shares Purpose ETF",
    "PLTR":  "Palantir (PLTR) Yield Shares Purpose ETF",
    "UNH":   "UnitedHealth Group (UNH) Yield Shares Purpose ETF",
}

OUT_DIR = pathlib.Path(__file__).resolve().parents[1] / "out"
ET = pytz.timezone("America/New_York")

_SANS = "font-family:Arial,Helvetica,sans-serif;"
_MONO = "font-family:Consolas,'SF Mono',Menlo,monospace;"
_GRAY = "#94a3b8"
_GREEN = "#16a34a"
_RED = "#dc2626"


def is_trading_day(date: datetime.date | None = None) -> bool:
    nyse = mcal.get_calendar("NYSE")
    d = date or datetime.datetime.now(ET).date()
    schedule = nyse.schedule(start_date=d.strftime("%Y-%m-%d"), end_date=d.strftime("%Y-%m-%d"))
    return not schedule.empty


def process_ticker(ticker: str) -> dict:
    try:
        return compute_ticker(ticker)
    except Exception as exc:
        print(f"  [WARN] {ticker}: {exc}")
        return {"summary": {"ticker": ticker, "error": str(exc)}}


# ── Email builder ─────────────────────────────────────────────────────────────

def _pct_color(v: float | None) -> str:
    if v is None:
        return "inherit"
    return _GREEN if v >= 0 else _RED


def _fmt(v, suffix="", prec=1, prefix="") -> str:
    if v is None:
        return "—"
    return f"{prefix}{v:.{prec}f}{suffix}"


def _fmt_rr(v) -> str:
    if v is None or not isinstance(v, (int, float)):
        return "—"
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.1f}pp"


def build_email(results: list[dict], date: datetime.date) -> str:
    date_str = f"{date.strftime('%B')} {date.day}, {date.year}" if hasattr(date, "strftime") else str(date)

    # ── Table rows ────────────────────────────────────────────────────────────
    rows_html = ""
    for data in results:
        s = data["summary"]
        ticker = s["ticker"]
        label = YIELD_TICKERS.get(ticker, ticker)
        skew = data.get("skew")
        front_rr = (skew.get("front_month") or {}).get("skew") if skew else None

        if s.get("error"):
            rows_html += (
                f'<tr><td style="{_SANS}padding:8px 12px;font-size:12px;font-weight:600;">'
                f'{label}</td>'
                f'<td colspan="6" style="{_SANS}padding:8px 12px;font-size:12px;color:{_RED};">'
                f'Error: {s["error"]}</td></tr>'
            )
            continue

        pct = s.get("price_change_pct")
        pct_color = _pct_color(pct)
        pct_str = f"{pct:+.2f}%" if pct is not None else "—"

        rv20 = data.get("rv20")
        cov = s.get("coverage_pct")

        rows_html += f"""
<tr>
  <td style="{_SANS}padding:8px 12px;font-size:12px;font-weight:600;border-bottom:1px solid #e2e8f0;">{label}</td>
  <td style="{_MONO}padding:8px 12px;font-size:12px;border-bottom:1px solid #e2e8f0;">{_fmt(s.get('spot'), prefix='$', prec=2)}</td>
  <td style="{_MONO}padding:8px 12px;font-size:12px;color:{pct_color};border-bottom:1px solid #e2e8f0;">{pct_str}</td>
  <td style="{_MONO}padding:8px 12px;font-size:12px;border-bottom:1px solid #e2e8f0;">{_fmt(s.get('iv30'), suffix='%')}</td>
  <td style="{_MONO}padding:8px 12px;font-size:12px;border-bottom:1px solid #e2e8f0;">{_fmt_rr(front_rr)}</td>
  <td style="{_MONO}padding:8px 12px;font-size:12px;border-bottom:1px solid #e2e8f0;">{_fmt(rv20 * 100 if rv20 is not None else None, suffix='%')}</td>
  <td style="{_MONO}padding:8px 12px;font-size:12px;color:{_GRAY};border-bottom:1px solid #e2e8f0;">{_fmt(cov, suffix='%', prec=0)}</td>
</tr>"""

    header_cell = (
        f'style="{_SANS}padding:6px 12px;font-size:10px;font-weight:700;'
        f'letter-spacing:0.08em;text-transform:uppercase;color:{_GRAY};'
        f'border-bottom:2px solid #cbd5e1;white-space:nowrap;"'
    )

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#ffffff;">
<table width="100%" cellpadding="0" cellspacing="0" style="max-width:900px;margin:0 auto;">
  <tr>
    <td style="{_SANS}padding:28px 12px 6px;font-size:20px;font-weight:700;">
      Purpose Yield ETF — Vol Diagnostics
    </td>
  </tr>
  <tr>
    <td style="{_SANS}padding:0 12px 20px;font-size:12px;color:{_GRAY};">
      {date_str} &nbsp;·&nbsp; CBOE delayed quotes, 15-min lag &nbsp;·&nbsp; OI T-1 (OCC standard)
    </td>
  </tr>
  <tr>
    <td style="padding:0 12px;">
      <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
        <thead>
          <tr>
            <th {header_cell}>ETF / Underlying</th>
            <th {header_cell}>Spot</th>
            <th {header_cell}>Day %</th>
            <th {header_cell}>IV30</th>
            <th {header_cell}>25Δ RR</th>
            <th {header_cell}>RV20</th>
            <th {header_cell}>Surface Cov</th>
          </tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
      </table>
    </td>
  </tr>
  <tr>
    <td style="{_SANS}padding:20px 12px 8px;font-size:10px;color:{_GRAY};line-height:1.6;">
      25Δ RR = 25-delta put IV − 25-delta call IV (front month, ≤45 DTE). Positive = put skew.
      RV20 requires ~20 trading days of history to appear.
      Surface coverage reflects fraction of the ±15% log-moneyness / 5–365 DTE grid with nearby real quotes.
    </td>
  </tr>
</table>
</body>
</html>"""


# ── Main ──────────────────────────────────────────────────────────────────────

def run(dry_run: bool = False) -> None:
    today = datetime.datetime.now(ET).date()

    if not is_trading_day(today):
        print(f"[yield-daily] {today} is not a NYSE trading day — skipping.")
        return

    tickers = list(YIELD_TICKERS.keys())
    print(f"[yield-daily] {today}  tickers: {', '.join(tickers)}")
    OUT_DIR.mkdir(exist_ok=True)

    all_data: list[dict] = []
    for ticker in tickers:
        print(f"  {ticker}...", end=" ", flush=True)
        data = process_ticker(ticker)
        all_data.append(data)
        s = data["summary"]
        if not s.get("error"):
            save_snapshot(s, ticker, skew_df=data.get("skew_df"), date=today)
            save_surface_snapshot(data.get("surface_df"), ticker, spot=s["spot"], date=today)
            iv30_str = f"  iv30={s['iv30']:.1f}%" if s.get("iv30") else ""
            print(f"spot={s['spot']:.2f}{iv30_str}")
        else:
            print(f"ERROR: {s['error']}")

    good = [d for d in all_data if not d["summary"].get("error")]
    if not good:
        print("[yield-daily] All tickers failed — skipping email.")
        return

    subject = f"Purpose Yield Vol — {today.strftime('%b %d, %Y').replace(' 0', ' ')}"
    html = build_email(all_data, today)

    if dry_run:
        out_path = OUT_DIR / f"yield_{today.strftime('%Y%m%d')}.html"
        out_path.write_text(html, encoding="utf-8")
        print(f"[yield-daily] Report saved: {out_path}")
        return

    try:
        emailer.send(subject=subject, html_body=html)
        print("[yield-daily] Email sent.")
    except Exception as exc:
        print(f"[yield-daily] Email failed: {exc}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Write HTML preview to out/, do not send email.")
    parser.add_argument("--send", action="store_true",
                        help="Required to actually send the email.")
    args = parser.parse_args()

    import os as _os
    authorized = args.send or _os.getenv("GEX_SEND") == "1"
    if not authorized and not args.dry_run:
        print("[yield-daily] No --send flag. Falling back to --dry-run.")
        args.dry_run = True

    run(dry_run=args.dry_run)
