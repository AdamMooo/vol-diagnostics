"""Calibration CLI: replay the ECDF ranker + hysteresis state machine over all
stored metric history, reporting alert episodes/week for a grid of candidate
bands and hysteresis widths (D-05, D-06).

Permanent, re-runnable deliverable -- not a one-off analysis. Re-run via
`python -m engine.monitor.calibration` as chain-metric history deepens
(D-08's ~2027-05 credibility-floor milestone).

Never auto-writes config.py (T-26-05) -- always prints a config-ready
snippet for human/executor review and manual copy-in.
"""
from __future__ import annotations

import argparse

import pandas as pd

from engine import config
from engine.monitor import metrics
from engine.monitor.hysteresis import check_alert_transition
from engine.monitor.ranker import compute_level_ranks
from engine.monitor.schema import METRIC_INVENTORY

FLICKER_WINDOW_SESSIONS = 3


def replay_metric(
    history: "pd.Series",
    entry: int,
    escalate: int,
    exit_: int,
    credibility_floor: int = config.MONITOR_CREDIBILITY_FLOOR_SESSIONS,
) -> list[dict]:
    """Walk history day-by-day (expanding window, no look-ahead), replaying
    the level_rank_deep + hysteresis pipeline. Returns every fired alert
    event as {"date":, "alert_type":, "rank":}. Never raises."""
    events: list[dict] = []
    try:
        clean = history.dropna()
        if clean.empty:
            return events

        state = "out"
        start = min(credibility_floor, len(clean) - 1) if len(clean) > 1 else 0

        for i in range(start, len(clean)):
            history_so_far = clean.iloc[:i + 1]
            today_value = clean.iloc[i]
            today_date = clean.index[i]

            ranks = compute_level_ranks(history_so_far, today_value, deep_lookback=None)
            today_rank = ranks["level_rank_deep"]
            n = ranks["n_deep"]

            alert_type, state = check_alert_transition(
                today_rank=today_rank,
                n=n,
                yesterday_state=state,
                entry=entry,
                escalate=escalate,
                exit_=exit_,
                credibility_floor=credibility_floor,
            )
            if alert_type is not None:
                events.append({"date": today_date, "alert_type": alert_type, "rank": today_rank})

        return events
    except Exception as exc:
        print(f"[calibration] replay_metric failed: {exc}")
        return events


def count_episodes_per_week(events: list[dict], total_sessions: int) -> float:
    """len(events) / (total_sessions / 5) -- 5 trading sessions/week."""
    if total_sessions <= 0:
        return 0.0
    return len(events) / (total_sessions / 5)


def flicker_ratio(events: list[dict]) -> float:
    """Fraction of "entry" events that re-fire within FLICKER_WINDOW_SESSIONS
    sessions of a prior entry/escalation for the SAME metric -- the
    bouncing-near-the-band signature (RESEARCH.md Pitfall 3). Events must
    already be scoped to one metric when calling this."""
    entries = [e for e in events if e["alert_type"] == "entry"]
    if len(entries) < 2:
        return 0.0

    flickers = 0
    for prev, curr in zip(entries, entries[1:]):
        gap_days = abs((curr["date"] - prev["date"]).days)
        if gap_days <= FLICKER_WINDOW_SESSIONS:
            flickers += 1

    return flickers / len(entries)


def calibrate(
    candidate_bands: list[int] | None = None,
    hysteresis_gaps: list[int] | None = None,
) -> dict:
    """Run replay_metric across ALL METRIC_INVENTORY pairs for every
    (entry, gap) combination (escalate = midpoint between entry and 99).
    Aggregates episodes/week and flicker_ratio ACROSS all metrics per band
    combination (D-05's budget is monitor-wide, not per-metric). Never
    raises -- metrics with no/short history are skipped."""
    if candidate_bands is None:
        candidate_bands = [90, 95, 97, 98, 99]
    if hysteresis_gaps is None:
        hysteresis_gaps = [5, 10, 15]

    series_cache: dict[tuple[str, str], "pd.Series | None"] = {}
    for metric_name, ticker in METRIC_INVENTORY:
        try:
            series_cache[(metric_name, ticker)] = metrics.load_metric_series(ticker, metric_name)
        except Exception as exc:
            print(f"[calibration] load_metric_series({ticker}, {metric_name}) failed: {exc}")
            series_cache[(metric_name, ticker)] = None

    results = []
    for band_entry in candidate_bands:
        for gap in hysteresis_gaps:
            band_exit = band_entry - gap
            band_escalate = band_entry + (99 - band_entry) // 2

            all_events: list[dict] = []
            all_flicker_ratios: list[float] = []
            total_sessions = 0

            for (metric_name, ticker), history in series_cache.items():
                if history is None or history.dropna().empty:
                    continue
                clean = history.dropna()
                if len(clean) <= config.MONITOR_CREDIBILITY_FLOOR_SESSIONS:
                    continue

                events = replay_metric(
                    clean, entry=band_entry, escalate=band_escalate, exit_=band_exit,
                    credibility_floor=config.MONITOR_CREDIBILITY_FLOOR_SESSIONS,
                )
                all_events.extend(events)
                all_flicker_ratios.append(flicker_ratio(events))
                total_sessions += len(clean)

            episodes_per_week = count_episodes_per_week(all_events, total_sessions) if total_sessions else 0.0
            avg_flicker = (
                sum(all_flicker_ratios) / len(all_flicker_ratios) if all_flicker_ratios else 0.0
            )

            results.append({
                "band_entry": band_entry,
                "band_escalate": band_escalate,
                "band_exit": band_exit,
                "episodes_per_week": episodes_per_week,
                "flicker_ratio": avg_flicker,
            })

    results.sort(key=lambda r: abs(r["episodes_per_week"] - 1.0))
    return {"results": results}


def _print_report(result: dict) -> None:
    results = result["results"]
    print(f"\n{'='*78}")
    print("  CALIBRATION REPLAY -- alert band grid (sorted by closeness to ~1 eps/week)")
    print(f"{'='*78}")
    print(f"{'entry':>6}{'escalate':>10}{'exit':>6}{'gap':>6}{'eps/week':>12}{'flicker':>10}")
    for r in results:
        gap = r["band_entry"] - r["band_exit"]
        print(
            f"{r['band_entry']:>6}{r['band_escalate']:>10}{r['band_exit']:>6}{gap:>6}"
            f"{r['episodes_per_week']:>12.3f}{r['flicker_ratio']:>10.3f}"
        )
    print(f"{'='*78}")

    if results:
        top = results[0]
        gap = top["band_entry"] - top["band_exit"]
        print("\nTop recommendation (closest to D-05's ~1 episode/week target):")
        print(
            f"  entry={top['band_entry']}  escalate={top['band_escalate']}  "
            f"exit={top['band_exit']}  gap={gap}  eps/week={top['episodes_per_week']:.3f}  "
            f"flicker={top['flicker_ratio']:.3f}"
        )
        print("\nConfig-ready snippet (never auto-written -- copy in manually per T-26-05):")
        print(f"MONITOR_ALERT_BAND_ENTRY: int = {top['band_entry']}")
        print(f"MONITOR_ALERT_BAND_ESCALATE: int = {top['band_escalate']}")
        print(f"MONITOR_ALERT_BAND_EXIT: int = {top['band_exit']}")
        print(f"MONITOR_ALERT_HYSTERESIS_GAP: int = {gap}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-bands", default="90,95,97,98,99")
    parser.add_argument("--hysteresis-gaps", default="5,10,15")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    bands = [int(x) for x in args.candidate_bands.split(",")]
    gaps = [int(x) for x in args.hysteresis_gaps.split(",")]

    report = calibrate(candidate_bands=bands, hysteresis_gaps=gaps)
    _print_report(report)
