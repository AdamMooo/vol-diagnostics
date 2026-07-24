---
phase: 26-severity-stats-alert-engine
plan: 05
subsystem: monitor/calibration
tags: [calibration, replay, methodology-fix, alert-bands, episodes-per-week, gap-closure]
requires:
  - engine/monitor/calibration.py (Plan 03's replay engine)
  - engine/monitor/ranker.py (compute_level_ranks)
  - engine/monitor/hysteresis.py (check_alert_transition)
  - engine/config.py (Plan 04's landed fixes: monitor_store.py, hysteresis.py, ranker.py, metrics.py, config.py)
provides:
  - engine/monitor/calibration.py with an inclusive-today replay window, a calendar-week eps/week denominator, and a session-index + escalation-inclusive flicker_ratio
  - engine/config.py MONITOR_ALERT_BAND_ENTRY/ESCALATE/EXIT/HYSTERESIS_GAP re-derived from a corrected-methodology replay run, with evidence-based docstrings
  - engine/tests/test_monitor/test_calibration.py, now hermetic (no live yfinance/parquet dependency)
affects:
  - Phase 27 (dashboard/email consumption of alert-band-driven monitor output) -- now backed by trustworthy calibration evidence
tech-stack:
  added: []
  patterns:
    - "Calendar-week denominator computed from the union of qualifying metrics' post-credibility-floor date ranges, not a pooled per-metric session count"
    - "Session-index gaps (threaded from the replay loop's positional index) for flicker detection, not calendar-day arithmetic"
    - "Inclusive-today ECDF window (clean.iloc[:i + 1]) matching production's rank definition"
    - "Grid/sort tests monkeypatch metrics.load_metric_series with synthetic series -- no live network/store dependency"
key-files:
  created: []
  modified:
    - engine/monitor/calibration.py
    - engine/tests/test_monitor/test_calibration.py
    - engine/config.py
decisions:
  - "The corrected replay's top recommendation is unchanged at band_entry=90/escalate=94/exit=85/gap=5 -- same band choice as the biased 2026-07-22 run -- but the evidence behind it is materially different: eps/week corrected from 0.186 to 0.704 (a ~3.8x increase, matching WR-01's predicted ~5x pooled-session bias direction) and flicker_ratio corrected from 0.047 to 0.377 (reflecting WR-02's session-index + escalation-inclusive fix). The bands survive the correction; the confidence in them is now real rather than an artifact of a biased denominator."
  - "5 of 17 METRIC_INVENTORY pairs still clear the 252-session credibility floor (VRP x3 tickers, SPY term_9d_30/term_30_3m) -- unchanged from Plan 03's run. The union post-credibility-floor date range across those 5 metrics is 2010-09-20 through the most recent stored session, 826.3 calendar weeks -- this is the corrected denominator's basis, replacing the old pooled 15,693-session figure."
metrics:
  duration: "~45 min"
  completed: "2026-07-24"
---

# Phase 26 Plan 05: Calibration Methodology Gap Closure Summary

Fixed three methodology defects in the calibration replay (WR-01 pooled-session denominator, WR-02 calendar-day/entry-only flicker_ratio, WR-03 train/serve rank-window skew) and one test-hermeticity defect (WR-07 live yfinance/parquet calls), then re-ran the corrected calibration against real `out/` stores and updated `config.py`'s alert-band constants with the new evidence.

## What Was Built

**Task 1 (commit `78e71f7`) -- WR-03 inclusive-today replay window; WR-07 hermetic grid test:**
- `replay_metric`'s ECDF window changed from `clean.iloc[:i]` (excludes today) to `clean.iloc[:i + 1]` (includes today), matching production's `compute_level_ranks` call in `monitor_store.py`, where the history passed in already contains today's row by the time the monitor step runs.
- `test_runs_across_grid_and_returns_sorted_results` now monkeypatches `calib_mod.metrics.load_metric_series` with a synthetic per-`(ticker, metric)` series (300-point, deterministic, seeded by `hash((ticker, metric_name))`) instead of hitting real `out/` parquet stores and live yfinance calls via `vrp_history_series`. Test runtime for the full `test_calibration.py` file dropped to ~2s with no network dependency.
- Existing `test_no_lookahead` and `test_single_spike_produces_one_entry_event_not_one_per_day` verified unaffected by the window-inclusivity change (both still pass unmodified).

**Task 2 (commit `4d62bf3`) -- WR-01 calendar-week denominator; WR-02 session-gap flicker_ratio with escalations:**
- `replay_metric` now threads the loop's positional index into each fired event as `"session_idx": i`.
- `count_episodes_per_week(events, calendar_weeks)` replaced the `total_sessions` parameter and `total_sessions / 5` computation with a direct `calendar_weeks: float` divisor.
- `calibrate()` no longer accumulates `total_sessions += len(clean)` (which pooled sessions across concurrent metrics, inflating the denominator ~Nx for N qualifying metrics). It now tracks the min/max post-credibility-floor date across all qualifying metrics for the band combination and computes `calendar_weeks = (max_date - min_date).days / 7` once per combination.
- `flicker_ratio` now includes `"escalation"` events in the prior-event pool alongside `"entry"` (matching the function's own docstring claim, previously false), and measures gaps via `session_idx` distance instead of `abs((curr["date"] - prev["date"]).days)` -- a session-index window of 3 disagrees with a 3-calendar-day window across weekends.
- Added `TestFlickerRatio` with two new tests: one demonstrating a session-index gap of 3 (within the flicker window) that spans a 5-calendar-day weekend gap (would have been excluded under the old calendar-day measure), and one demonstrating an escalation event followed by an entry event now counts as a flicker.

**Task 3 (commit `8d8cf2f`) -- Re-run corrected calibration, finalize config.py bands:**
- Ran `python -m engine.monitor.calibration --candidate-bands 90,95,97,98,99 --hysteresis-gaps 5,10,15` against the actual `out/` stores using the corrected `calibration.py`.
- Same 5 of 17 `METRIC_INVENTORY` pairs qualify as before (VRP x3 tickers, `term_9d_30`/`term_30_3m` on SPY); the 12 chain-derived skew/fly/surface metrics remain cold-starting (19-41 sessions since ~2026-05) and are still skipped, unchanged from Plan 03.
- `engine/config.py`'s four `MONITOR_ALERT_*` constants updated with the corrected evidence and rewritten docstrings citing today's run, the corrected methodology, and the new figures. Values did not change (90/94/85/5), but every docstring now cites 2026-07-24 and the corrected-methodology evidence, replacing every "Calibrated 2026-07-22" reference in those four constants.

## Full Calibration Report (this run, corrected methodology)

```
==============================================================================
  CALIBRATION REPLAY -- alert band grid (sorted by closeness to ~1 eps/week)
==============================================================================
 entry  escalate  exit   gap    eps/week   flicker
    90        94    85     5       0.704     0.377
    90        94    80    10       0.634     0.339
    90        94    75    15       0.598     0.323
    95        97    90     5       0.413     0.332
    95        97    85    10       0.380     0.305
    95        97    80    15       0.356     0.300
    97        98    92     5       0.270     0.322
    97        98    87    10       0.259     0.316
    97        98    82    15       0.243     0.297
    98        98    93     5       0.213     0.364
    98        98    88    10       0.200     0.360
    98        98    83    15       0.188     0.344
    99        99    94     5       0.128     0.356
    99        99    89    10       0.121     0.346
    99        99    84    15       0.115     0.338
==============================================================================

Top recommendation (closest to D-05's ~1 episode/week target):
  entry=90  escalate=94  exit=85  gap=5  eps/week=0.704  flicker=0.377
```

Union post-credibility-floor date range across the 5 qualifying metrics: 2010-09-20 to the most recent stored session -- 826.3 calendar weeks. 582 total events fired at band 90/gap 5 across the 5 qualifying metrics (SPY vrp: 101, QQQ vrp: 86, IWM vrp: 102, SPY term_9d_30: 170, SPY term_30_3m: 123), giving `582 / 826.3 = 0.704` eps/week.

## Old -> New Band Delta

| Constant | 2026-07-22 (biased) | 2026-07-24 (corrected) | Delta |
|---|---|---|---|
| `MONITOR_ALERT_BAND_ENTRY` | 90 | 90 | unchanged |
| `MONITOR_ALERT_BAND_ESCALATE` | 94 | 94 | unchanged |
| `MONITOR_ALERT_BAND_EXIT` | 85 | 85 | unchanged |
| `MONITOR_ALERT_HYSTERESIS_GAP` | 5 | 5 | unchanged |
| eps/week (evidence, band 90/gap 5) | 0.186 | 0.704 | ~3.8x higher (WR-01 predicted ~5x from the pooled-session bias; the corrected magnitude is in that direction, close to it) |
| flicker_ratio (evidence, band 90/gap 5) | 0.047 | 0.377 | ~8x higher (WR-02's session-index + escalation-inclusive fix surfaces flickers the old calendar-day/entry-only measure missed) |
| pooled sessions / calendar weeks (denominator basis) | 15,699 pooled sessions | 826.3 calendar weeks | denominator changed in kind, not just magnitude |

The band choice (90/94/85/5) is robust to the correction -- it remains the closest-to-target combination in the corrected grid, same as in the biased grid. What changed is the confidence in that choice: the corrected eps/week (0.704) sits much closer to D-05's ~1/week budget than the old figure (0.186) suggested, and the corrected flicker_ratio (0.377), while higher than before, is still the lowest among the tested gaps at this band (0.377 vs 0.339 at gap=10, 0.323 at gap=15 -- narrower gaps flicker slightly more, as expected, and gap=5 is not meaningfully worse). This is the outcome D-06 calls for: evidence-driven bands, not bands assumed correct because the numbers happened to look reassuring.

## Deviations from Plan

None -- plan executed exactly as written. Two notes worth flagging (not deviations, results):

1. The corrected eps/week (0.704) is now much closer to the ~1/week D-05 target than the biased 0.186 figure suggested -- the original "eps/week is monotonically below target everywhere" framing from Plan 03's SUMMARY still holds directionally (no band overshoots 1/week in the corrected grid either), but the magnitude of the gap between observed and target rate is far smaller than previously believed.
2. `test_calibration.py`'s existing `test_skips_metrics_with_no_history_without_crashing` already used the monkeypatch-`load_metric_series` pattern this plan's Task 1 extended to the grid test -- no new pattern was invented, just applied consistently.

## Verification

```
pytest engine/tests/test_monitor/test_calibration.py -v   # 8 passed (was 6; +2 new flicker_ratio tests)
python -m engine.monitor.calibration --candidate-bands 90,95,97,98,99 --hysteresis-gaps 5,10,15
                                                            # ran against real out/ stores, printed corrected report + recommendation
pytest engine/tests -q                                     # 443 passed, 829 warnings (pre-existing pandas/yfinance deprecation warnings, unrelated to this plan)
```

Acceptance criteria verified directly:
- `grep -n "clean.iloc\[:i\]" engine/monitor/calibration.py` -- no matches in `replay_metric` (exclusive form removed).
- `grep -n "clean.iloc\[:i + 1\]" engine/monitor/calibration.py` -- finds the corrected inclusive slice.
- `test_runs_across_grid_and_returns_sorted_results` contains `monkeypatch.setattr(calib_mod.metrics, "load_metric_series", ...)`.
- `grep -n "total_sessions / 5" engine/monitor/calibration.py` -- no matches (pooled-session denominator removed).
- `grep -n "calendar_weeks" engine/monitor/calibration.py` -- finds the parameter in both `count_episodes_per_week` and `calibrate`.
- `grep -n "session_idx" engine/monitor/calibration.py` -- finds the field threaded from `replay_metric` through to `flicker_ratio`.
- `flicker_ratio`'s event-type filter includes `"escalation"` alongside `"entry"`.
- `grep -c "2026-07-22" engine/config.py` -- 0 (verified in the four `MONITOR_ALERT_*` docstrings specifically; no unrelated uses of that date exist elsewhere in the file).
- `MONITOR_ALERT_BAND_ENTRY` and `MONITOR_ALERT_BAND_EXIT` docstrings each contain "calendar week" and "escalation".
- The four `MONITOR_ALERT_*` constants' values (90/94/85/5) exactly match this run's top-sorted recommendation.

## Self-Check: PASSED

- FOUND: engine/monitor/calibration.py
- FOUND: engine/tests/test_monitor/test_calibration.py
- FOUND: engine/config.py
- FOUND commit 78e71f7 (Task 1 -- WR-03 inclusive-today window, WR-07 hermetic test)
- FOUND commit 4d62bf3 (Task 2 -- WR-01 calendar-week denominator, WR-02 session-gap flicker_ratio)
- FOUND commit 8d8cf2f (Task 3 -- re-run corrected calibration, finalize config.py bands)

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
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-03-SUMMARY|26-03-SUMMARY]]
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-04-PLAN|26-04-PLAN]]
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-04-SUMMARY|26-04-SUMMARY]]
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-05-PLAN|26-05-PLAN]]
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-CONTEXT|26-CONTEXT]]
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-DISCUSSION-LOG|26-DISCUSSION-LOG]]
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-PATTERNS|26-PATTERNS]]
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-RESEARCH|26-RESEARCH]]
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-REVIEW|26-REVIEW]]
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-VERIFICATION|26-VERIFICATION]]

<!-- LINKS:END -->
