"""
Daily GEX orchestrator — run all tickers, send email report, save snapshots.

Usage:
    python -m gex.run_daily            # all tickers
    python -m gex.run_daily --dry-run  # compute + print, no email

Scheduled via: runners/gex_daily.ps1 (Task Scheduler, 4:30 PM ET on trading days)
"""
from __future__ import annotations

import argparse
import datetime
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas_market_calendars as mcal
import pytz

from gex.compute import compute_ticker
from gex.analytics import plot_gamma_profile, plot_overview, fig_to_b64
from gex.validation import save_snapshot
from gex import report as rpt
from gex import emailer

INDEX_TICKERS   = ["SPY", "QQQ", "IWM", "XLF", "GLD", "TLT"]
PURPOSE_TICKERS = ["NVDA", "TSLA", "AAPL", "AMD", "META", "AMZN",
                   "GOOGL", "MSFT", "AVGO", "COIN", "COST", "NFLX", "PLTR", "UNH"]
ALL_TICKERS = INDEX_TICKERS + PURPOSE_TICKERS

OUT_DIR = pathlib.Path(__file__).resolve().parents[1] / "out"
ET = pytz.timezone("America/New_York")


def is_trading_day(date: datetime.date | None = None) -> bool:
    nyse = mcal.get_calendar("NYSE")
    d = date or datetime.datetime.now(ET).date()
    schedule = nyse.schedule(start_date=d.strftime("%Y-%m-%d"), end_date=d.strftime("%Y-%m-%d"))
    return not schedule.empty


def process_ticker(ticker: str) -> dict:
    """Never raises — errors go in result."""
    try:
        return compute_ticker(ticker)
    except Exception as exc:
        print(f"  [WARN] {ticker}: {exc}")
        return {"summary": {"ticker": ticker, "error": str(exc)}}


def run(dry_run: bool = False) -> None:
    today = datetime.datetime.now(ET).date()

    if not is_trading_day(today):
        print(f"[gex-daily] {today} is not a NYSE trading day — skipping.")
        return

    print(f"[gex-daily] {today}  tickers: {', '.join(ALL_TICKERS)}")
    OUT_DIR.mkdir(exist_ok=True)

    all_data: list[dict] = []
    for ticker in ALL_TICKERS:
        print(f"  {ticker}...", end=" ", flush=True)
        data = process_ticker(ticker)
        all_data.append(data)
        s = data["summary"]
        if not s.get("error"):
            save_snapshot(s, ticker)
            iv30_str = f"  iv30={s['iv30']:.1f}%" if s.get("iv30") else ""
            print(f"spot={s['spot']:.2f}  gex=${s['net_gex']/1e9:.2f}B  regime={s['gamma_regime']}{iv30_str}")
        else:
            print(f"ERROR: {s['error']}")

    index_results   = [d["summary"] for d in all_data if d["summary"]["ticker"] in INDEX_TICKERS]
    purpose_results = [d["summary"] for d in all_data if d["summary"]["ticker"] in PURPOSE_TICKERS]
    all_results     = [d["summary"] for d in all_data]
    good            = [d for d in all_data if not d["summary"].get("error")]

    overview_fig = plot_overview(all_results)
    overview_b64 = fig_to_b64(overview_fig)
    plt.close(overview_fig)

    charts_b64: dict[str, str] = {}
    for d in good:
        ticker = d["summary"]["ticker"]
        fig = plot_gamma_profile(d["p_df"], d["spot"], ticker, d["summary"], figsize=(6, 2.8))
        charts_b64[ticker] = fig_to_b64(fig)
        plt.close(fig)

    subject = f"GEX Report — {today.strftime('%b %d, %Y').replace(' 0', ' ')}"
    html = rpt.build_email(
        index_results=index_results,
        purpose_results=purpose_results,
        date=today,
        charts_b64=charts_b64,
    )

    if dry_run:
        out_path = OUT_DIR / f"gex_{today.strftime('%Y%m%d')}.html"
        out_path.write_text(html, encoding="utf-8")
        print(f"[gex-daily] Report saved: {out_path}")
        return

    try:
        emailer.send(subject=subject, html_body=html)
        print("[gex-daily] Email sent.")
    except Exception as exc:
        print(f"[gex-daily] Email failed: {exc}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
