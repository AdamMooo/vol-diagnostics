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

from engine.compute import compute_ticker
from engine.data.validation import save_snapshot
from engine.data.surface_history import (
    save_surface_snapshot, nth_trading_day_back, load_surface_snapshot, list_available_dates,
)
from engine.data.oi_history import save_oi_snapshot, list_oi_dates
from engine.report import report as rpt
from engine.report import emailer
from engine.report import observation
from engine.report.png_export import export_png
from engine.gex.analytics import plot_iv_change_heatmap
from engine.surface.surface_evolution import load_evolution
from engine.vol.vol_metrics import evolution_summary
from engine.data.vol_index import refresh_vol_indices
from engine.session import ET, is_trading_day, latest_session, MARKET_OPEN_HOUR, MARKET_OPEN_MIN
from engine.monitor import monitor_store
from engine import config

INDEX_TICKERS = ["SPY", "QQQ", "IWM"]
ALL_TICKERS = INDEX_TICKERS

OUT_DIR = pathlib.Path(__file__).resolve().parents[1] / "out" / "gex"
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
    except Exception as exc:
        print(f"[CORRUPT] run_daily: {SNAPSHOT_STORE.name} unreadable ({exc}) — re-collecting today.")
        return False


def process_ticker(
    ticker: str,
    today: datetime.date | None = None,
    risk_free_rate: float | None = None,
    vvix: float | None = None,
) -> dict:
    """Never raises — errors go in result."""
    try:
        return compute_ticker(ticker, today=today, risk_free_rate=risk_free_rate, vvix=vvix)
    except Exception as exc:
        print(f"  [WARN] {ticker}: {exc}")
        return {"summary": {"ticker": ticker, "error": str(exc)}}


def _build_png_attachments(
    all_data: list[dict],
    today: datetime.date,
    out_dir: pathlib.Path,
) -> tuple[list, list[str]]:
    """Returns (attachments, failed_tickers). failed_tickers only counts tickers where
    export was actually attempted and failed — not benign skips (no prior day, etc.) —
    so a partial failure (e.g. 1-of-3) can be surfaced instead of only a total one."""
    attachments: list = []
    failed: list[str] = []
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
                attachments.append(path)
            except Exception as exc:
                print(f"  [WARN] PNG for {ticker} failed (non-blocking): {exc}")
                failed.append(ticker)
    except Exception as exc:
        print(f"[WARN] PNG generation failed (non-blocking): {exc}")
        return [], list(INDEX_TICKERS)
    return attachments, failed


def _verify_stores_written(all_data: list[dict], today: datetime.date) -> None:
    """Post-write cross-store consistency check.

    Atomic writes (engine.data.store) close the in-file corruption window, but a
    process killed *between* the per-ticker scalar/surface/OI saves still leaves
    the stores desynced for that ticker — silently degrading the compare tab and
    evolution baseline downstream. Verify each store we attempted to write
    actually has today's rows and shout if not, rather than letting it pass.
    """
    import pandas as pd

    scalar_tickers: set[str] = set()
    if SNAPSHOT_STORE.exists():
        try:
            df = pd.read_parquet(SNAPSHOT_STORE)
            df["date"] = pd.to_datetime(df["date"]).dt.date
            scalar_tickers = set(df[df["date"] == today]["ticker"].unique())
        except Exception as exc:
            print(f"[CORRUPT] run_daily: store verify could not read {SNAPSHOT_STORE.name} ({exc})")

    problems: list[str] = []
    for data in all_data:
        s = data["summary"]
        if s.get("error"):
            continue
        ticker = s["ticker"]
        if ticker not in scalar_tickers:
            problems.append(f"{ticker}: scalar snapshot missing")
        sdf = data.get("surface_df")
        if sdf is not None and not sdf.empty and today not in set(list_available_dates(ticker)):
            problems.append(f"{ticker}: surface snapshot missing")
        odf = data.get("expiry_oi_df")
        if odf is not None and not odf.empty and today not in set(list_oi_dates(ticker)):
            problems.append(f"{ticker}: OI snapshot missing")

    if problems:
        print(f"[ERROR] cross-store consistency check FAILED for {today}: " + "; ".join(problems))
    else:
        print("[run_daily] Cross-store consistency check passed.")


def run(dry_run: bool = False, force: bool = False) -> None:
    # Calendar-derived session date (not the raw wall-clock date): a delayed or
    # after-midnight catch-up run files under the session it actually collected.
    today = latest_session(datetime.datetime.now(ET), MARKET_OPEN_HOUR, MARKET_OPEN_MIN)

    if not is_trading_day(today):
        print(f"[gex-daily] {today} is not a NYSE trading day — skipping.")
        return

    if not force and _already_collected_today(today):
        print(f"[gex-daily] {today} already collected for all tickers — skipping (use --force to override).")
        return

    print(f"[gex-daily] {today}  tickers: {', '.join(ALL_TICKERS)}")
    OUT_DIR.mkdir(exist_ok=True)

    print("[run_daily] Refreshing vol-index snapshots...")
    refreshed: list[str] = []
    try:
        refreshed = refresh_vol_indices()
    except Exception as exc:
        print(f"  [WARN] vol-index refresh failed (non-blocking): {exc}")
    vol_feed_note = None
    if "VIX" not in refreshed:
        vol_feed_note = ("Vol-index feed unavailable this run — VRP, term structure and "
                         "VVIX may be stale (last good values shown).")
        print("  [WARN] vol-index feed did not refresh VIX — VRP/term/VVIX may be stale.")

    # risk_free_rate and vvix are identical across SPY/QQQ/IWM — fetch each once
    # (risk_free_rate is a ~4-5s yfinance call) instead of once per ticker.
    from engine.compute import _get_risk_free_rate
    from engine.vol.vol_metrics import compute_vvix_level
    shared_rate = _get_risk_free_rate()
    shared_vvix = compute_vvix_level()

    all_data: list[dict] = []
    for ticker in ALL_TICKERS:
        print(f"  {ticker}...", end=" ", flush=True)
        data = process_ticker(ticker, today, risk_free_rate=shared_rate, vvix=shared_vvix)
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

    _verify_stores_written(all_data, today)

    print("\n[run_daily] Computing surface evolution...")
    from engine.surface.surface_evolution import update_evolution
    for ticker in INDEX_TICKERS:
        try:
            rows = update_evolution(ticker, today)
            print(f"  {ticker}: {rows} evolution row(s) written")
        except Exception as exc:
            print(f"  [WARN] {ticker} evolution failed (non-blocking): {exc}")

    print("\n[run_daily] Computing severity monitor rows...")
    all_data_by_ticker = {d["summary"]["ticker"]: d for d in all_data}
    for ticker in ALL_TICKERS:
        try:
            n = monitor_store.compute_and_save_monitor_rows(
                ticker, all_data_by_ticker[ticker]["summary"], today,
                band_entry=config.MONITOR_ALERT_BAND_ENTRY,
                band_escalate=config.MONITOR_ALERT_BAND_ESCALATE,
                band_exit=config.MONITOR_ALERT_BAND_EXIT,
            )
            print(f"  {ticker}: {n} monitor row(s) written")
        except Exception as exc:
            print(f"  [WARN] {ticker} monitor failed (non-blocking): {exc}")

    # Gather evolution scalars for email section (non-blocking per-ticker)
    evolution_data: dict = {}
    for ticker in INDEX_TICKERS:
        try:
            evol_5 = evolution_summary(load_evolution(ticker, horizon=5, days=30))
            evol_10 = evolution_summary(load_evolution(ticker, horizon=10, days=30))
            evol_30 = evolution_summary(load_evolution(ticker, horizon=30, days=30))
            evolution_data[ticker] = {
                **evol_5,
                "horizons": {
                    "5d": evol_5,
                    "10d": evol_10,
                    "30d": evol_30,
                },
            }
        except Exception as exc:
            print(f"  [WARN] {ticker} evolution gather failed (non-blocking): {exc}")
            evolution_data[ticker] = {
                "level": None, "rms": None,
                "skew_change": None, "term_change": None, "as_of": None,
                "horizons": {
                    "5d": {"level": None, "rms": None, "skew_change": None, "term_change": None, "as_of": None},
                    "10d": {"level": None, "rms": None, "skew_change": None, "term_change": None, "as_of": None},
                    "30d": {"level": None, "rms": None, "skew_change": None, "term_change": None, "as_of": None},
                },
            }

    # Generate PNG attachments (non-blocking — kaleido failure sends email without PNGs).
    # failed_pngs surfaces PARTIAL failures too, not just a total wipeout — a silent
    # print()-only partial failure is exactly the shape of bug that hid the
    # plotly/kaleido version mismatch for months before it was caught (2026-07-13).
    png_note: str | None = None
    attachments, failed_pngs = _build_png_attachments(all_data, today, OUT_DIR)
    if not attachments and any(d.get("surface_df") is not None for d in all_data):
        png_note = "Surface charts unavailable — kaleido not installed or PNG export failed."
    elif failed_pngs:
        png_note = f"PNG export failed for {', '.join(failed_pngs)} — other charts unaffected."

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
    notes = [n for n in (vol_feed_note, png_note) if n]

    # Event-shaped alerts banner input — band entries/escalations fired today plus
    # each alerting pair's prior rank (for the Delta-vs-yesterday fragment). Cold-start
    # safe: load_recent_alert_events returns an empty frame until an alert ever fires,
    # so the banner renders as "" and the email is unchanged (non-blocking).
    from engine.monitor import monitor_reader
    alert_events = None
    prior_rank_lookup: dict = {}
    try:
        alert_events = monitor_reader.load_recent_alert_events(days=1)
        for _, ev in alert_events.iterrows():
            tkr, mtr, kind = ev.get("ticker"), ev.get("metric"), ev.get("rank_kind")
            col = rpt._ALERT_RANK_KIND_COLUMN.get(kind)
            if col is None:
                continue
            trail = monitor_reader.load_rank_trail(tkr, mtr, n=2)
            if len(trail) >= 2 and col in trail.columns:
                prior_rank_lookup[(tkr, mtr, kind)] = trail.iloc[-2][col]
    except Exception as exc:
        print(f"  [WARN] alert-events gather failed (non-blocking): {exc}")
        alert_events = None

    html = rpt.build_email(
        index_results=index_results,
        date=today,
        evolution_data=evolution_data,
        png_note=" · ".join(notes) if notes else None,
        oi_data=oi_data if oi_data else None,
        alert_events=alert_events,
        prior_rank_lookup=prior_rank_lookup,
    )

    if dry_run:
        out_path = OUT_DIR / f"index-vol-report-{today.strftime('%Y-%m-%d')}.html"
        out_path.write_text(html, encoding="utf-8")
        print(f"[gex-daily] Report saved: {out_path}")
        return

    email_ok = False
    try:
        emailer.send(subject=subject, html_body=html, attachments=attachments)
        email_ok = True
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

    # Snapshots are saved and the observation is logged; a dead email channel must
    # surface as a non-zero exit so Task Scheduler reports failure instead of a
    # silent "success" with no email. Re-run (--force) to resend from the saved chain.
    if not email_ok:
        raise SystemExit(2)


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
