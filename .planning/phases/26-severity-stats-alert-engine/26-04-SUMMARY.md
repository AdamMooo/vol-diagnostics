---
phase: 26-severity-stats-alert-engine
plan: 04
subsystem: monitor
tags: [pandas, scipy, hysteresis, ecdf, correctness-fix]

# Dependency graph
requires:
  - phase: 26-severity-stats-alert-engine (plans 01-03)
    provides: ranker.py, hysteresis.py, monitor_store.py, metrics.py, calibration.py -- the monitor package these fixes patch
provides:
  - Date-guarded stale-value fallback in monitor_store.py (CR-01)
  - Hysteresis state held across a transient None-rank I/O blip (WR-04)
  - Explicit today_in_history contract on compute_change_rank (WR-05)
  - Decoupled MONITOR_SURFACE_EVOLUTION_HORIZON constant (WR-06)
affects: [27-dashboard-email-consumption]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "credibility-floor check runs unconditionally first in check_alert_transition; state-hold logic is a separate, later branch"
    - "keyword-only today_in_history flag lets a pure function support two calling contracts (production vs. future replay) without call-site changes"

key-files:
  created: []
  modified:
    - engine/monitor/monitor_store.py
    - engine/monitor/hysteresis.py
    - engine/monitor/ranker.py
    - engine/monitor/metrics.py
    - engine/config.py
    - engine/tests/test_monitor/test_store.py
    - engine/tests/test_monitor/test_hysteresis.py
    - engine/tests/test_monitor/test_ranker.py
    - engine/tests/test_monitor/test_metrics.py

key-decisions:
  - "Credibility-floor gate (n < floor) is checked first and unconditionally in check_alert_transition, so it always wins over the new None-rank state-hold branch"
  - "today_in_history defaults to True (matches production, no call-site changes needed) with today_in_history=False available for a future replay/calibration caller"
  - "MONITOR_SURFACE_EVOLUTION_HORIZON introduced as its own constant (=5, same value as MONITOR_CHANGE_K_SESSIONS today) rather than reusing the change-rank constant, purely to remove the coupling"

patterns-established: []

requirements-completed: [CR-01, WR-04, WR-05, WR-06]

# Metrics
duration: ~25min
completed: 2026-07-24
---

# Phase 26 Plan 04: Gap Closure (CR-01, WR-04, WR-05, WR-06) Summary

**Fixed four shipped-code correctness bugs from 26-REVIEW.md: stale-value fallback writing yesterday's data under today's date, hysteresis state collapsing on a one-day I/O blip, an off-by-one in the change-rank comparator, and a silent coupling between the surface-evolution horizon and the change-rank window constant.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 3 completed
- **Files modified:** 9 (5 source, 4 test)

## Accomplishments
- `monitor_store.py`'s `history.iloc[-1]` fallback now requires `history.index[-1] == today`; stale history logs a warning and leaves the row's `value`/ranks `None` instead of silently persisting a today-dated observation from an earlier day
- `hysteresis.check_alert_transition` holds `yesterday_state` (`in_entry`/`in_escalate`) across a `today_rank=None` blip instead of resetting to `"out"`; the credibility-floor reset stays unconditional and takes priority
- `ranker.compute_change_rank` gained an explicit `today_in_history: bool = True` keyword documenting and correctly implementing both today-in-history contracts (`clean.iloc[-1-k]` vs `clean.iloc[-k]`); removed the dead `len(clean) > k` ternary
- `metrics.py`'s `surface_level`/`surface_rms` loaders now filter on a new, independent `config.MONITOR_SURFACE_EVOLUTION_HORIZON` constant instead of `MONITOR_CHANGE_K_SESSIONS`

## Task Commits

Each task was committed atomically:

1. **Task 1: CR-01 — date-guard the stale-value fallback in monitor_store.py** - `9bd1614` (fix)
2. **Task 2: WR-04 — hold hysteresis state on a transient None rank** - `4f4d2d3` (fix)
3. **Task 3: WR-05 — fix compute_change_rank's today-in-history contract; WR-06 — decouple surface-evolution horizon** - `9a1088f` (fix)

**Plan metadata:** (this commit)

## Files Created/Modified
- `engine/monitor/monitor_store.py` - date-guards the `history.iloc[-1]` stale-value fallback
- `engine/monitor/hysteresis.py` - splits the credibility-floor check from the None-rank state-hold logic
- `engine/monitor/ranker.py` - `compute_change_rank` gains `today_in_history` kwarg, drops dead guard
- `engine/monitor/metrics.py` - `surface_level`/`surface_rms` key off `MONITOR_SURFACE_EVOLUTION_HORIZON`
- `engine/config.py` - new `MONITOR_SURFACE_EVOLUTION_HORIZON` constant
- `engine/tests/test_monitor/test_store.py` - new stale-history test (value=None, warning logged, written count unaffected)
- `engine/tests/test_monitor/test_hysteresis.py` - replaced the old "resets to out" expectation with state-hold assertions for in_entry/in_escalate/out, plus a floor-still-resets test
- `engine/tests/test_monitor/test_ranker.py` - new tests proving both `today_in_history` modes select the correct comparator
- `engine/tests/test_monitor/test_metrics.py` - new decoupling test (changing `MONITOR_CHANGE_K_SESSIONS` doesn't affect `surface_level` loading)

## Decisions Made
- Kept the credibility-floor check as an unconditional, absolute reset (per D-08: sample size cannot regress in practice), checked before the new None-rank state-hold branch — matches the plan's specified priority order exactly.
- `today_in_history` defaults to `True` so no existing call site (monitor_store.py) needs to change; the parameter exists purely to make the function's contract correct and explicit for any future caller (e.g. a replay/calibration path) that passes `today_value` before it's in the history store.
- Left IN-02 (dead monkeypatch line in test_store.py, noted in 26-REVIEW.md) and WR-01/02/03/07/08 untouched — out of this plan's scope (`requirements: [CR-01, WR-04, WR-05, WR-06]`); those belong to the calibration-methodology rework tracked separately.

## Deviations from Plan

None - plan executed exactly as written. All four fixes match the review's proposed diffs; tests were added per the plan's specified behaviors (in one case reordering test-then-fix vs fix-then-test for Task 1, since the fix and test were written in the same pass rather than strictly test-first — the resulting test still fails without the fix and passes with it, verified by inspection of the guard logic).

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Monitor package's four CR/WR-tagged correctness defects are closed; `out/monitor/ranks.parquet` and `alert_events.parquet` will no longer receive stale-dated values or spurious duplicate entry alerts from transient I/O blips going forward.
- WR-01/WR-02/WR-03 (calibration methodology: eps/week denominator, flicker_ratio, replay window) and WR-07/WR-08 (test hermeticity, dead CLI flag) remain open per 26-REVIEW.md — out of this plan's scope, tracked for a future calibration-rework plan before the shipped 90/94/85 bands can be considered fully trustworthy.
- Full suite green: 441 passed (up from the pre-existing 434, +7 new tests across the four fixes).

---
*Phase: 26-severity-stats-alert-engine*
*Completed: 2026-07-24*

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
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-05-PLAN|26-05-PLAN]]
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-CONTEXT|26-CONTEXT]]
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-DISCUSSION-LOG|26-DISCUSSION-LOG]]
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-PATTERNS|26-PATTERNS]]
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-RESEARCH|26-RESEARCH]]
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-REVIEW|26-REVIEW]]
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-VERIFICATION|26-VERIFICATION]]

<!-- LINKS:END -->
