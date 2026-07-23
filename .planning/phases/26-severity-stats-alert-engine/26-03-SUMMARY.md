---
phase: 26-severity-stats-alert-engine
plan: 03
subsystem: monitor/calibration
tags: [calibration, replay, alert-bands, hysteresis, episodes-per-week]
requires:
  - engine/monitor/schema.py (METRIC_INVENTORY)
  - engine/monitor/metrics.py (load_metric_series)
  - engine/monitor/ranker.py (compute_level_ranks)
  - engine/monitor/hysteresis.py (check_alert_transition)
provides:
  - engine/monitor/calibration.py (replay_metric, count_episodes_per_week, flicker_ratio, calibrate, CLI)
  - engine/config.py MONITOR_ALERT_BAND_ENTRY/ESCALATE/EXIT/HYSTERESIS_GAP finalized with replay evidence
affects:
  - Phase 27 (dashboard/email consumption of alert-band-driven monitor output)
tech-stack:
  added: []
  patterns:
    - "Expanding-window replay (no look-ahead) reusing the same ranker + hysteresis functions the live system uses, not a re-derivation"
    - "CLI never auto-writes config.py — always prints a config-ready snippet for human copy-in (T-26-05)"
key-files:
  created:
    - engine/monitor/calibration.py
    - engine/tests/test_monitor/test_calibration.py
  modified:
    - engine/config.py
decisions:
  - "Calibration replay against actual out/ stores (15,699 sessions across 5/17 qualifying metrics) recommends band_entry=90/escalate=94/exit=85/gap=5, closest to D-05's ~1 eps/week target at 0.186 eps/week — the grid's eps/week is monotonically below target everywhere tested, an honest empirical finding (deep vol-index history genuinely produces fewer false alarms than the a priori D-05 budget assumed), not a defect in the calibration"
  - "Only 5 of 17 METRIC_INVENTORY pairs (VRP x3, SPY term ratios x2) clear the 252-session credibility floor as of 2026-07-22; the 12 chain-derived skew/fly/surface metrics (19-41 sessions since ~2026-05 cold-start) were skipped by the replay per D-08, not included via any workaround — documented in config.py as a re-run trigger once they cross the floor (~2027-05)"
metrics:
  duration: "~30 min"
  completed: "2026-07-22"
---

# Phase 26 Plan 03: Calibration CLI + Band Finalization Summary

Built the permanent, re-runnable calibration replay CLI (`engine.monitor.calibration`) that walks stored metric history day-by-day through the exact ranker + hysteresis pipeline the live system uses, counts alert episodes/week and flicker ratio across a grid of candidate bands and hysteresis widths, and used its output against real `out/` stores to replace Plan 02's provisional MONITOR_ALERT_BAND_* placeholders with calibration-derived values.

## What Was Built

**Task 1 — Calibration replay engine (TDD: test commit `4c13400`, feat commit `052f0b8`):**
- `engine/monitor/calibration.py`: `replay_metric(history, entry, escalate, exit_, credibility_floor)` — expanding-window replay (day `i` ranked only against `history.iloc[:i]`, verified by an explicit no-look-ahead test that mutates the tail of a copy and confirms events before the mutation point are byte-identical). Reuses `ranker.compute_level_ranks` and `hysteresis.check_alert_transition` directly rather than re-deriving the logic.
- `count_episodes_per_week(events, total_sessions)` — `len(events) / (total_sessions / 5)`.
- `flicker_ratio(events)` — fraction of "entry" events re-firing within 3 sessions of a prior entry (the bouncing-near-the-band signature from RESEARCH.md Pitfall 3).
- `calibrate(candidate_bands, hysteresis_gaps)` — runs the replay across every `(metric, ticker)` in `METRIC_INVENTORY` for every `(entry, gap)` combination (`escalate = entry + (99-entry)//2`), aggregates episodes/week and flicker_ratio ACROSS all qualifying metrics per band combination (D-05's budget is monitor-wide), skips metrics with no/thin history without crashing, sorts results by closeness to the ~1 eps/week target.
- CLI entry point mirroring `run_gex.py`'s argparse pattern: `--candidate-bands`, `--hysteresis-gaps`, `--dry-run` (never writes config.py — always prints a report table + config-ready snippet, per T-26-05).
- 6 tests, all passing, including the single-spike-produces-one-entry-event hysteresis-in-replay check and the no-look-ahead assertion.

**Task 2 — Ran calibration against real stored history, finalized config.py bands:**
- `python -m engine.monitor.calibration --dry-run` run against the actual current `out/` stores. Of the 17 `METRIC_INVENTORY` pairs, only 5 clear `MONITOR_CREDIBILITY_FLOOR_SESSIONS=252`: VRP (SPY/QQQ/IWM, 2515-2520 sessions each, riding the CBOE vol-index's multi-decade depth) and `term_9d_30`/`term_30_3m` (SPY, 3909/4235 sessions). The 12 chain-derived skew/fly/surface metrics are still cold-starting at 19-41 sessions since ~2026-05 and were correctly skipped by the replay per D-08 — not a bug.
- Total replay: 15,699 aligned sessions across those 5 metrics. Grid result: episodes/week is monotonically below the D-05 ~1/week target across the ENTIRE tested grid (entry in [90,95,97,98,99] x gap in [5,10,15]) — closest is entry=90/escalate=94/exit=85/gap=5 at 0.186 eps/week, flicker_ratio 0.047 (lowest tested gap already minimizes flicker at this band).
- `engine/config.py`: replaced `MONITOR_ALERT_BAND_ENTRY=97`/`ESCALATE=99`/`EXIT=87` (Plan 02's PROVISIONAL placeholders) with `ENTRY=90`/`ESCALATE=94`/`EXIT=85`, added new `MONITOR_ALERT_HYSTERESIS_GAP=5`. Each constant's docstring documents the calibration date (2026-07-22), history depth (15,699 sessions, 5/17 metrics), the observed eps/week, and an explicit re-run trigger once chain metrics cross the 252-session floor (~2027-05, D-08) — since the current recommendation is honest but based on only 5 of 17 metrics.

## Deviations from Plan

None — plan executed exactly as written. One honest finding worth flagging (not a deviation, a result):

- The plan's interfaces section anticipated bands landing "~97th-98th per D-05" as the expected outcome. The actual replay recommends a lower band (90th) because the D-05 ~1 eps/week target is not reachable anywhere in the tested grid — the deep vol-index history (VIX-derived, back to 1990/2009) genuinely produces far fewer than 1 false alarm/week even at the 90th percentile once ranked against its own full depth. This is exactly the kind of evidence-over-theory outcome D-06 calls for (bands from replay, not from the a priori ~97th-98th expectation) — documented in config.py rather than silently forced toward the expected range.

## Verification

```
pytest engine/tests/test_monitor/test_calibration.py -v   # 6 passed
python -m engine.monitor.calibration --dry-run             # ran against real out/ stores, printed report table + recommendation, did not touch config.py
pytest engine/tests -q                                     # 434 passed
```

Acceptance criteria verified directly:
- `grep -v '^#' engine/config.py | grep -c PROVISIONAL` returns 0.
- `grep -n "MONITOR_ALERT_HYSTERESIS_GAP" engine/config.py` finds the new constant.
- All four `MONITOR_ALERT_*` constants' comments mention the 2026-07-22 calibration date, the 15,699-session/5-of-17-metric depth, and the observed eps/week or the cold-start caveat for the 12 skipped metrics.
- `replay_metric`'s no-look-ahead property is directly tested (mutating the tail of a copy leaves earlier events byte-identical).

## Self-Check: PASSED

- FOUND: engine/monitor/calibration.py
- FOUND: engine/tests/test_monitor/test_calibration.py
- FOUND commit 4c13400 (task 1 RED)
- FOUND commit 052f0b8 (task 1 GREEN)
- FOUND commit 9a9aa5e (task 2)

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
**Phase siblings:**
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-01-PLAN|26-01-PLAN]]
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-01-SUMMARY|26-01-SUMMARY]]
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-02-PLAN|26-02-PLAN]]
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-02-SUMMARY|26-02-SUMMARY]]
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-03-PLAN|26-03-PLAN]]
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-CONTEXT|26-CONTEXT]]
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-DISCUSSION-LOG|26-DISCUSSION-LOG]]
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-PATTERNS|26-PATTERNS]]
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-RESEARCH|26-RESEARCH]]

<!-- LINKS:END -->
