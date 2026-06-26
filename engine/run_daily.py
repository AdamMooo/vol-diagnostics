"""
Daily GEX orchestrator — run all tickers, send email report, save snapshots.

Usage:
    python -m engine.run_daily            # all tickers
    python -m engine.run_daily --dry-run  # compute + print, no email
    python -m engine.run_daily --force    # bypass idempotency guard

Idempotent: safe to double-fire. If today's snapshots already exist for all
tickers, the run is a no-op (use --force to override).

Scheduled via container cron (supercronic) or Task Scheduler on Windows.
"""
from __future__ import annotations

import argparse
import datetime
import pathlib

import pandas_market_calendars as mcal
import pytz

from engine.compute import compute_ticker
from engine.data.validation import save_snapshot
from engine.data.surface_history import save_surface_snapshot, nth_trading_day_back, load_surface_snapshot
from engine.data.oi_history import save_oi_snapshot
from engine.report import report as rpt
from engine.report import emailer
from engine.report import observation
from engine.report.png_export import export_png
from engine.gex.analytics import plot_iv_change_heatmap, plot_price_with_levels
from engine.surface.surface_evolution import load_evolution
from engine.vol.vol_metrics import evolution_5d_summary
from engine.data.vol_index import refresh_vol_indices

INDEX_TICKERS = ["SPY", "QQQ", "IWM"]
ALL_TICKERS = INDEX_TICKERS

OUT_DIR = pathlib.Path(__file__).resolve().parents[1] / "out" / "gex"
ET = pytz.timezone("America/New_York")

SNAPSHOT_STORE = pathlib.Path(__file__).resolve().parents[1] / "out" / "gex_snapshots.parquet"


def _already_collected_today(today: datetime.date) -> bool:
    """True if snapshots exist for all tickers on the given date."""
    if not SNAPSHOT_STORE.exists():
        return False
    try:
        import pandas as pd
        df = pd.read_parquet(SNAPSHOT_STORE)
        df["date"] = pd.to_datetime(df["date"]).dt.date
        today_rows = df[df["date"] == today]
        collected = set(today_rows["ticker"].unique())
        return all(t in collected for t in ALL_TICKERS)
    except Exception:
        return False


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


def _build_png_attachments(
    all_data: list[dict],
    today: datetime.date,
    out_dir: pathlib.Path,
) -> list:
    attachments: list = []
    data_by_ticker = {d["summary"]["ticker"]: d for d in all_data}
    try:
        for ticker in INDEX_TICKERS:
            try:
                prior_date = nth_trading_day_back(ticker, today, 1)
                if prior_date is None:
                    continue
                prior_surface_df, prior_spot = load_surface_snapshot(ticker, prior_date)
                if prior_surface_df.empty:
                    continue
                data = data_by_ticker.get(ticker, {})
                today_surface_df = data.get("surface_df")
                today_spot = data["summary"].get("spot")
                if today_surface_df is None or today_spot is None:
                    continue
                prior_spot = prior_spot if prior_spot is not None else today_spot
                label_prior = prior_date.strftime("%b %d")
                label_today = today.strftime("%b %d")
                fig = plot_iv_change_heatmap(
                    today_surface_df, prior_surface_df,
                    ticker, today_spot, prior_spot,
                    label_prior=label_prior,
                    label_today=label_today,
                )
                path = export_png(fig, ticker, "div_surface", today, out_dir)
                if path is not None:
                    attachments.append(path)
            except Exception as exc:
                print(f"  [WARN] PNG for {ticker} failed (non-blocking): {exc}")
    except Exception as exc:
        print(f"[WARN] PNG generation failed (non-blocking): {exc}")
        return []
    return attachments


def _fetch_price_history_yf(ticker: str, period: str = "3mo"):
    """Dated recent closes for the price-level chart. None on any failure."""
    try:
        import yfinance as yf
        import pandas as pd
        hist = yf.Ticker(ticker.replace(".", "-")).history(period=period)
        if hist.empty or "Close" not in hist.columns:
            return None
        df = hist.reset_index()[["Date", "Close"]].rename(
            columns={"Date": "date", "Close": "close"}
        )
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
        return df.dropna()
    except Exception as exc:
        print(f"  [WARN] price history for {ticker} failed (non-blocking): {exc}")
        return None


def _build_price_level_attachments(
    all_data: list[dict],
    today: datetime.date,
    out_dir: pathlib.Path,
) -> list:
    """Per-ticker price-vs-levels PNG (dealer γ-flip/walls + OI walls). Non-blocking."""
    attachments: list = []
    data_by_ticker = {d["summary"]["ticker"]: d for d in all_data}
    for ticker in INDEX_TICKERS:
        try:
            data = data_by_ticker.get(ticker, {})
            summary = data.get("summary", {})
            spot = summary.get("spot")
            if summary.get("error") or spot is None:
                continue
            price_df = _fetch_price_history_yf(ticker)
            fig = plot_price_with_levels(price_df, ticker, summary, spot)
            path = export_png(fig, ticker, "price_levels", today, out_dir)
            if path is not None:
                attachments.append(path)
        except Exception as exc:
            print(f"  [WARN] price-level PNG for {ticker} failed (non-blocking): {exc}")
    return attachments


def run(dry_run: bool = False, force: bool = False) -> None:
    today = datetime.datetime.now(ET).date()

    if not is_trading_day(today):
        print(f"[gex-daily] {today} is not a NYSE trading day — skipping.")
        return

    if not force and _already_collected_today(today):
        print(f"[gex-daily] {today} already collected for all tickers — skipping (use --force to override).")
        return

    print(f"[gex-daily] {today}  tickers: {', '.join(ALL_TICKERS)}")
    OUT_DIR.mkdir(exist_ok=True)

    print("[run_daily] Refreshing vol-index snapshots...")
    try:
        refresh_vol_indices()
    except Exception as exc:
        print(f"  [WARN] vol-index refresh failed (non-blocking): {exc}")

    all_data: list[dict] = []
    for ticker in ALL_TICKERS:
        print(f"  {ticker}...", end=" ", flush=True)
        data = process_ticker(ticker)
        all_data.append(data)
        s = data["summary"]
        if not s.get("error"):
            save_snapshot(s, ticker, skew_df=data.get("skew_df"), date=today)
            save_surface_snapshot(data.get("surface_df"), ticker, spot=s["spot"], date=today)
            try:
                expiry_oi_df = data.get("expiry_oi_df")
                if expiry_oi_df is not None and not expiry_oi_df.empty:
                    save_oi_snapshot(expiry_oi_df, ticker, today)
            except Exception as exc:
                print(f"  [WARN] OI snapshot for {ticker} failed (non-blocking): {exc}")
            iv30_str = f"  iv30={s['iv30']:.1f}%" if s.get("iv30") else ""
            print(f"spot={s['spot']:.2f}  gex=${s['net_gex']/1e9:.2f}B{iv30_str}")
        else:
            print(f"ERROR: {s['error']}")

    print("\n[run_daily] Computing surface evolution...")
    from engine.surface.surface_evolution import update_evolution
    for ticker in INDEX_TICKERS:
        try:
            rows = update_evolution(ticker, today)
            print(f"  {ticker}: {rows} evolution row(s) written")
        except Exception as exc:
            print(f"  [WARN] {ticker} evolution failed (non-blocking): {exc}")

    # Gather evolution scalars for email section (non-blocking per-ticker)
    evolution_data: dict = {}
    for ticker in INDEX_TICKERS:
        try:
            evol_df = load_evolution(ticker, horizon=5, days=30)
            evolution_data[ticker] = evolution_5d_summary(evol_df)
        except Exception as exc:
            print(f"  [WARN] {ticker} evolution gather failed (non-blocking): {exc}")
            evolution_data[ticker] = {
                "level": None, "rms": None,
                "skew_change": None, "term_change": None, "as_of": None,
            }

    # Generate PNG attachments (non-blocking — kaleido failure sends email without PNGs)
    png_note: str | None = None
    attachments = _build_png_attachments(all_data, today, OUT_DIR)
    attachments += _build_price_level_attachments(all_data, today, OUT_DIR)
    if not attachments and any(d.get("surface_df") is not None for d in all_data):
        png_note = "Surface charts unavailable — kaleido not installed or PNG export failed."

    print(f"[run_daily] {len(attachments)} PNG attachment(s) ready.")

    index_results = [d["summary"] for d in all_data if d["summary"]["ticker"] in INDEX_TICKERS]
    good = [d for d in all_data if not d["summary"].get("error")]
    if not good:
        errors = {d["summary"]["ticker"]: d["summary"].get("error") for d in all_data}
        print(f"[run_daily] All tickers failed — skipping email. Errors: {errors}")
        raise SystemExit(1)

    subject = f"Index Volatility Report — {today.strftime('%B')} {today.day}, {today.year}"
    oi_data = {
        d["summary"]["ticker"]: d["expiry_oi_df"]
        for d in all_data
        if not d["summary"].get("error") and d.get("expiry_oi_df") is not None
    }
    html = rpt.build_email(
        index_results=index_results,
        date=today,
        evolution_data=evolution_data,
        png_note=png_note,
        oi_data=oi_data if oi_data else None,
    )

    if dry_run:
        out_path = OUT_DIR / f"index-vol-report-{today.strftime('%Y-%m-%d')}.html"
        out_path.write_text(html, encoding="utf-8")
        print(f"[gex-daily] Report saved: {out_path}")
        return

    try:
        emailer.send(subject=subject, html_body=html, attachments=attachments)
        print("[gex-daily] Email sent.")
    except Exception as exc:
        print(f"[gex-daily] Email failed: {exc}")

    # Auto-prefill observation block in today's daily note (60-day observation log)
    try:
        note_path = observation.append_to_daily_note(index_results, today)
        if note_path:
            print(f"[gex-daily] Observation block appended: {note_path}")
    except Exception as exc:
        print(f"[gex-daily] Observation log failed (non-blocking): {exc}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Write HTML preview to out/, do not send email.")
    parser.add_argument("--send", action="store_true",
                        help="Required to actually send the email. Without this flag, "
                             "the script behaves as --dry-run. Set by the scheduled task.")
    parser.add_argument("--force", action="store_true",
                        help="Bypass idempotency guard (re-collect even if today's data exists).")
    args = parser.parse_args()

    # Safety guard: require an explicit --send (or GEX_SEND=1) to send mail.
    # Prevents accidental fires from terminal up-arrow recall.
    import os as _os
    authorized = args.send or _os.getenv("GEX_SEND") == "1"
    if not authorized and not args.dry_run:
        print("[gex-daily] No --send flag (and GEX_SEND != 1). Falling back to --dry-run.")
        print("[gex-daily] The scheduled task is the only authorized sender.")
        args.dry_run = True

    run(dry_run=args.dry_run, force=args.force)
