#!/usr/bin/env python3
"""
Health check for Gamma OMM data collection pipeline.

Verifies that daily snapshots are current for all tickers. Designed to run
as a cron job or Docker healthcheck — exits 0 (healthy) or 1 (stale/missing).

Usage:
    python -m engine.health_check              # print status
    python -m engine.health_check --strict     # exit 1 if any ticker is stale
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta

import pandas_market_calendars as mcal

from engine.data.surface_history import list_available_dates
from engine.data.validation import load_history

INDEX_TICKERS = ["SPY", "QQQ", "IWM"]


def _last_expected_session(today: date | None = None) -> date:
    """Most recent NYSE trading day that should have a snapshot by now."""
    today = today or date.today()
    nyse = mcal.get_calendar("NYSE")
    sched = nyse.schedule(
        start_date=(today - timedelta(days=14)).strftime("%Y-%m-%d"),
        end_date=today.strftime("%Y-%m-%d"),
    )
    sessions = [d.date() for d in sched.index]
    if not sessions:
        return today
    # Today's session only counts if market is closed (after 4:35pm ET)
    from datetime import datetime
    import pytz
    now_et = datetime.now(pytz.timezone("America/New_York"))
    if sessions[-1] == today and now_et.hour < 17:
        return sessions[-2] if len(sessions) >= 2 else today
    return sessions[-1]


def check_health(verbose: bool = True) -> dict:
    """Check all tickers for stale or missing data.

    Returns {"healthy": bool, "tickers": {ticker: {status, latest, expected, gap}}}
    """
    expected = _last_expected_session()
    results = {}
    all_healthy = True

    for ticker in INDEX_TICKERS:
        # Check surface snapshots (daily chain storage)
        available = list(list_available_dates(ticker))
        # Check GEX snapshot store
        hist = load_history(ticker, days=10)

        latest_surface = max(available) if available else None
        latest_snapshot = None
        if not hist.empty and "date" in hist.columns:
            latest_snapshot = hist["date"].max()
            if hasattr(latest_snapshot, "date"):
                latest_snapshot = latest_snapshot.date()

        latest = latest_surface or latest_snapshot
        if latest is None:
            status = "MISSING"
            gap = None
            all_healthy = False
        elif latest < expected:
            nyse = mcal.get_calendar("NYSE")
            sched = nyse.schedule(
                start_date=latest.strftime("%Y-%m-%d"),
                end_date=expected.strftime("%Y-%m-%d"),
            )
            gap = sum(1 for d in sched.index if d.date() > latest)
            status = f"STALE ({gap} session{'s' if gap != 1 else ''} behind)"
            all_healthy = False
        else:
            status = "OK"
            gap = 0

        results[ticker] = {
            "status": status,
            "latest": str(latest) if latest else "none",
            "expected": str(expected),
            "gap": gap,
        }

        if verbose:
            icon = "[OK]" if gap == 0 else "[MISSING]" if gap is None else f"[STALE +{gap}d]"
            print(f"  {ticker}: {icon} latest={latest or 'none'} expected={expected}")

    if verbose:
        print(f"\nOverall: {'HEALTHY' if all_healthy else 'UNHEALTHY'}")

    return {"healthy": all_healthy, "expected": str(expected), "tickers": results}


def main():
    parser = argparse.ArgumentParser(description="Gamma OMM health check")
    parser.add_argument("--strict", action="store_true",
                        help="Exit 1 if any ticker is stale/missing")
    parser.add_argument("--json", action="store_true",
                        help="Output JSON instead of human-readable")
    args = parser.parse_args()

    result = check_health(verbose=not args.json)

    if args.json:
        import json
        print(json.dumps(result, indent=2))

    if args.strict and not result["healthy"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
