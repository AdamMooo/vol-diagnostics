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

from engine.config import TICKER_VOL_INDEX, VRP_DEEP_LOOKBACK_SESSIONS
from engine.data.oi_history import list_oi_dates
from engine.data.surface_history import list_available_dates
from engine.data.validation import list_snapshot_dates, load_history
from engine.data.vol_index import load_vol_index

INDEX_TICKERS = ["SPY", "QQQ", "IWM"]
SERIES_NAMES = ["gex_snapshots", "surface_history", "vol_index", "oi_history"]

# Model-ready minimum session-depth targets per series. Numbers must match
# .planning/notes/MODEL-READY-DATA-SPEC.md exactly (Plan 23-04, SCHEMA-01/02) --
# gex_snapshots: GARCH(1,1) sample-size convention (Ng & Lam 2006, 500-1000
# observations, 750 = literature midpoint). surface_history/oi_history: RV20
# 251-trading-day (~1yr) "one seasonal cycle" convention -- these are per-day
# cross-sectional stores, not return series, so a GARCH minimum doesn't apply.
# vol_index: reuses VRP_DEEP_LOOKBACK_SESSIONS -- CBOE-published external
# history already exceeds any plausible modeling requirement, restated here
# only for traceability with the spec doc.
MODEL_READY_TARGETS = {
    "gex_snapshots": 750,
    "surface_history": 251,
    "vol_index": VRP_DEEP_LOOKBACK_SESSIONS,
    "oi_history": 251,
}


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


def get_nyse_sessions(start_date: date, end_date: date) -> set[date]:
    """All NYSE trading days between start_date and end_date (inclusive)."""
    nyse = mcal.get_calendar("NYSE")
    sched = nyse.schedule(
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
    )
    return set(d.date() for d in sched.index)


def _series_dates(ticker: str, series: str) -> set[date]:
    """Dispatch to the appropriate store reader and return its dates as a set."""
    if series == "gex_snapshots":
        return set(list_snapshot_dates(ticker))
    elif series == "surface_history":
        return set(list_available_dates(ticker))
    elif series == "vol_index":
        symbol = TICKER_VOL_INDEX.get(ticker)
        if not symbol:
            return set()
        hist = load_vol_index(symbol)
        if hist.empty:
            return set()
        return set(hist["date"])
    elif series == "oi_history":
        return set(list_oi_dates(ticker))
    else:
        raise ValueError(f"Unknown series: {series}")


def _full_history_scan(dates: set[date], dates_by_series: dict[str, set[date]], series: str) -> dict:
    """Walk the NYSE session calendar across a series' full stored date range,
    reporting any session with no corresponding row (per D-04: catches gaps
    that a tail-only check would miss).

    For vol_index (D-05), a missing session is only flagged when at least one
    of the other 3 series DID collect data that date — otherwise it's treated
    as an expected CBOE/NYSE non-publish day, not a gap.
    """
    if not dates:
        return {"earliest": None, "latest": None, "total_sessions": 0, "gaps": [], "gap_count": 0}

    earliest, latest = min(dates), max(dates)
    sessions = get_nyse_sessions(earliest, latest)
    missing = sorted(sessions - dates)

    gaps = []
    for d in missing:
        if series == "vol_index":
            other_collected = any(
                d in dates_by_series[s] for s in ("gex_snapshots", "surface_history", "oi_history")
            )
            if not other_collected:
                continue
            gaps.append((d, "data missing (other series collected this date; CBOE gap unexpected)"))
        else:
            gaps.append((d, "data missing"))

    return {
        "earliest": str(earliest),
        "latest": str(latest),
        "total_sessions": len(sessions),
        "gaps": [{"date": str(d), "reason": r} for d, r in gaps],
        "gap_count": len(gaps),
    }


def full_history_report(verbose: bool = True) -> dict:
    """Full-history gap scan across all 4 series x 3 tickers.

    Returns {"clean": bool, "series": {ticker: {series: scan_dict}}}.
    """
    all_clean = True
    series_result: dict[str, dict[str, dict]] = {}

    for ticker in INDEX_TICKERS:
        # Compute once per ticker (not once per series-pair comparison) to avoid
        # redundant parquet reads — see Pitfall 4 in 23-RESEARCH.md.
        dates_by_series = {series: _series_dates(ticker, series) for series in SERIES_NAMES}
        ticker_result = {}

        for series in SERIES_NAMES:
            scan = _full_history_scan(dates_by_series[series], dates_by_series, series)
            ticker_result[series] = scan
            if scan["gap_count"] > 0:
                all_clean = False

            if verbose:
                print(f"[{series}] {ticker}")
                print(f"  Earliest: {scan['earliest']}, Latest: {scan['latest']}, "
                      f"Sessions: {scan['total_sessions']}, Gaps: {scan['gap_count']}")
                for gap in scan["gaps"]:
                    print(f"    - {gap['date']} ({gap['reason']})")

        series_result[ticker] = ticker_result

    return {"clean": all_clean, "series": series_result}


def depth_audit(verbose: bool = True) -> dict:
    """Report current data depth vs. model-ready targets, per ticker/series.

    Informational only (SCHEMA-02) -- never feeds the --strict exit code;
    a data-foundation phase's series will legitimately be below target for
    a long time and that must never fail the daily CI gate.

    Returns {"all_ready": bool, "series": {ticker: {series: {depth, target, meets_target}}}}.
    """
    all_ready = True
    series_result: dict[str, dict[str, dict]] = {}

    for ticker in INDEX_TICKERS:
        ticker_result = {}
        for series in SERIES_NAMES:
            depth = len(_series_dates(ticker, series))
            target = MODEL_READY_TARGETS[series]
            meets = depth >= target
            if not meets:
                all_ready = False
            ticker_result[series] = {"depth": depth, "target": target, "meets_target": meets}

            if verbose:
                label = "MEETS" if meets else "SHORT"
                print(f"[{series}] {ticker}: {depth}/{target} -- {label}")

        series_result[ticker] = ticker_result

    return {"all_ready": all_ready, "series": series_result}


def main():
    parser = argparse.ArgumentParser(description="Gamma OMM health check")
    parser.add_argument("--strict", action="store_true",
                        help="Exit 1 if any ticker is stale/missing")
    parser.add_argument("--json", action="store_true",
                        help="Output JSON instead of human-readable")
    parser.add_argument("--depth-audit", action="store_true",
                        help="Report current data depth vs. model-ready targets "
                             "(informational only -- does not affect --strict exit code)")
    args = parser.parse_args()

    if args.depth_audit:
        depth_result = depth_audit(verbose=not args.json)
        if args.json:
            import json
            print(json.dumps(depth_result, indent=2))
        return

    result = check_health(verbose=not args.json)
    fh_result = full_history_report(verbose=not args.json)

    if args.json:
        import json
        print(json.dumps({"tail_check": result, "full_history": fh_result}, indent=2))

    # --strict is the operational freshness gate used by the daily workflow.
    # Historical gap scans are still reported, but known backfill holes must not
    # flip today's collection job red after the current session saved cleanly.
    if args.strict and not result["healthy"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
