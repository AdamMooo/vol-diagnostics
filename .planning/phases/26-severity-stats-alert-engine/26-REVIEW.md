---
phase: 26-severity-stats-alert-engine
reviewed: 2026-07-24T18:30:16Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - engine/config.py
  - engine/monitor/calibration.py
  - engine/monitor/hysteresis.py
  - engine/monitor/metrics.py
  - engine/monitor/monitor_store.py
  - engine/monitor/ranker.py
  - engine/tests/test_monitor/test_calibration.py
  - engine/tests/test_monitor/test_hysteresis.py
  - engine/tests/test_monitor/test_metrics.py
  - engine/tests/test_monitor/test_ranker.py
  - engine/tests/test_monitor/test_store.py
findings:
  critical: 2
  warning: 3
  info: 1
  total: 6
status: issues_found
---

# Phase 26: Code Review Report (gap-closure re-review, plans 26-04/26-05)

**Reviewed:** 2026-07-24
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

This is a post-fix review of 26-04 (CR-01, WR-04, WR-05, WR-06) and 26-05 (WR-01, WR-02, WR-03). The narrow, surgical fixes for WR-05 (today_in_history), WR-06 (decoupled horizon constant), and the WR-01/02/03 calibration-methodology corrections (calendar-week denominator, session-index flicker gaps + escalations, inclusive-of-today ECDF window) are all correct and each is backed by a test that provably fails against the pre-fix code (verified by hand-tracing the old formulas against the new test fixtures).

However, two of the fixes do **not** actually close the hole they were written for, and both were verified empirically (not just by inspection) against the current code in this repo:

1. **WR-04's hysteresis "hold state on transient None" branch is unreachable in production** — the ranker functions that feed `check_alert_transition` always return `n=0` in lockstep with `rank=None`, so the unconditional `n < credibility_floor` check (which must run first, per D-08) always intercepts before the new hold-branch is ever reached. The duplicate-entry-alert-on-recovery bug WR-04 describes is still live. Worse, CR-01's own stale-value guard *increases* how often this fires, because it forces `today_value=None` on every stale day, which forces `n_deep=0`/`n_1yr=0`.
2. **CR-01's stale-value guard doesn't cover `change_rank`** — `compute_change_rank(history, today_value=None)` does not return the "no value" `none_dict`; it computes a change rank from history's own last stored diff, so a stale day can still fire/persist a `band_state_change` alert dated today, built from data that predates today. The new regression test only asserts `row["value"] is None`, not `row["change_rank"] is None`, so this gap ships with green tests.

Both were reproduced directly against the repo's actual functions (session transcript below); these are the two Critical findings. The three Warnings are secondary/interaction issues and a methodology approximation.

## Critical Issues

### CR-02: WR-04's None-rank state-hold is unreachable — hysteresis still resets to "out" on any data gap, and CR-01 makes this worse

**File:** `engine/monitor/hysteresis.py:35-41`, interacting with `engine/monitor/ranker.py:33-34,79-86` and `engine/monitor/monitor_store.py:101-107`
**Issue:** `check_alert_transition` checks `n < credibility_floor` (line 35) *before* the new `today_rank is None` hold-branch (line 38). Every caller derives `(rank, n)` from `ranker.compute_level_ranks` / `ranker.compute_change_rank`, and both functions' `none_dict` couples `rank=None` with `n=0` unconditionally (`compute_level_ranks`: `if history is None or today_value is None: return none_dict` where `none_dict` sets `n_deep=0, n_1yr=0`). So whenever `today_rank` is `None` from a real caller, `n` is always `0`, which means the `n < credibility_floor` branch fires first and returns `(None, "out")` — the hold-branch at line 38 is dead code given every current call site. Verified directly:
```
>>> level_res = ranker.compute_level_ranks(None, None)   # simulates a loader failure
{'level_rank_deep': None, 'n_deep': 0, 'level_rank_1yr': None, 'n_1yr': 0}
>>> hysteresis.check_alert_transition(level_res['level_rank_deep'], level_res['n_deep'], 'in_escalate', 97, 99, 87)
(None, 'out')          # state reset, NOT held — WR-04's fix did not fire
```
Compounding this, CR-01's own fix now forces this exact code path more often than before: on any day `history.index[-1] != today` (e.g. an upstream snapshot/evolution save that ran late or failed for one ticker), `monitor_store.py` deliberately sets `today_value = None` (line 101-107) to avoid persisting a stale value — but that `None` then flows into `compute_level_ranks(history, None)`, which returns `n_deep=0`/`n_1yr=0` regardless of how much real history exists, forcing `check_alert_transition` down the credibility-floor branch and silently clearing any active `in_entry`/`in_escalate` state. The next day, when data recovers with the rank still elevated, a fresh "entry" alert fires — precisely the duplicate-alert scenario WR-04 was written to prevent, now triggered by CR-01's own guard rather than only by a total loader outage. The only tests exercising the hold-branch (`test_none_rank_holds_in_escalate_state`, `test_none_rank_holds_in_entry_state`) hand-pass `n=FLOOR` alongside `today_rank=None` — a combination no real caller produces — so the test suite is green while the fix is inert.
**Fix:** Decouple "no valid today value" from "insufficient sample size" at the source. `compute_level_ranks`/`compute_change_rank` need to report the *actual* history depth (`len(clean)`) even when `today_value` is `None`, e.g.:
```python
def compute_level_ranks(history, today_value, ...):
    if history is None:
        return none_dict
    clean = history.dropna()
    n_deep = len(clean)  # compute depth regardless of today_value
    if today_value is None:
        return {"level_rank_deep": None, "n_deep": n_deep, "level_rank_1yr": None, "n_1yr": min(n_deep, oneyr_lookback)}
    ...
```
Then `check_alert_transition`'s `n < credibility_floor` check will correctly reflect real sample depth, and the `today_rank is None` hold-branch becomes reachable for a metric with sufficient history but a transient gap in today's value — which is the scenario WR-04 actually needs to cover.

### CR-03: CR-01's stale-value guard does not gate `change_rank` — a stale day can still fire a today-dated `band_state_change` alert

**File:** `engine/monitor/monitor_store.py:101-110`, `engine/monitor/ranker.py:79-100`
**Issue:** When `history.index[-1] != today`, `monitor_store.py` correctly leaves `today_value = None` and the printed row's `value` stays `None`. But `change_res = ranker.compute_change_rank(history, today_value)` is called with that same `None`, and `compute_change_rank`'s `today_value is None` branch (lines 96-97) does **not** mean "no data for today" — it means "compute the rank of history's own most recent stored diff" (`todays_change = float(abs_changes.iloc[-1])`), a legitimate mode for a caller with no separate today-value at all. Because `monitor_store.py` conflates "I have no valid value for today" with "call in no-explicit-today-value mode," a stale day still produces a real, non-`None` `change_rank`/`change_n` computed entirely from data that predates today, which is then persisted under today's date and fed to `hysteresis.check_alert_transition` for `band_state_change` — capable of firing/persisting an "entry"/"escalation" alert event dated today, built from stale data. Verified directly against the 300-row stale fixture used in the new `test_stale_history_skips_value_and_warns` test:
```
>>> ranker.compute_change_rank(history, None)   # today_value=None on a stale day
{'change_rank': 50, 'change_n': 295}            # NOT none_dict — fires normally
>>> ranker.compute_level_ranks(history, None)
{'level_rank_deep': None, 'n_deep': 0, ...}      # correctly gated
```
The row this produces has `value=None` and `level_rank_deep=None` (correctly stale-gated) sitting alongside a fully-populated `change_rank=50`/`change_n=295` (not stale-gated) — an internally inconsistent row that can still drive an alert. The new test (`test_stale_history_skips_value_and_warns`) only asserts `row["value"] is None`; it never checks `row["change_rank"]`, so this gap is untested and ships green.
**Fix:** In `monitor_store.py`, only call `compute_change_rank` with the fallback semantics when a genuine today-value exists; when the stale guard fires, skip the change-rank computation the same way the value was skipped, e.g.:
```python
if today_value is None and history is not None and not history.empty:
    last_date = history.index[-1]
    if last_date == today:
        today_value = float(history.iloc[-1])
    else:
        print(f"[monitor] {ticker}/{metric_name}: history stale (last={last_date}); skipping value")

change_res = (
    ranker.compute_change_rank(history, today_value)
    if today_value is not None or summary.get(metric_name) is not None
    else {"change_rank": None, "change_n": 0}
)
```
(or simpler: track a `stale` boolean from the date-guard and short-circuit both `level_res`/`change_res` to their `none_dict`s when `stale` is true).

## Warnings

### WR-09: `calibrate()`'s "union of qualifying metrics' date ranges" is actually a min-start/max-end span, not a true union

**File:** `engine/monitor/calibration.py:141-163`
**Issue:** `min_date`/`max_date` are computed as the minimum post-floor start and maximum post-floor end *across* qualifying metrics (`min_date = min(min_date, post_floor_start)`, `max_date = max(max_date, post_floor_end)`), then `calendar_weeks = (max_date - min_date).days / 7`. This is a convex-hull span, not the union of the individual metrics' post-floor intervals — if any qualifying metric's own post-floor start is materially later than another's (e.g. one metric's usable history begins years after another's), the span still counts the earlier, single-metric-only period at full weight in the denominator, understating `episodes_per_week` for that stretch (fewer metrics could fire, but the denominator doesn't reflect that). The docstring's claim of "union of qualifying metrics' post-credibility-floor date ranges" (config.py comment, calibration.py docstring) overstates what's actually computed. Given the specific 5 qualifying metrics currently in play likely have close/overlapping windows (see prior review's WR-01 discussion), the practical impact on the shipped bands may be small, but the method will silently degrade in accuracy once the 12 currently-cold chain-derived metrics clear the credibility floor at very different times (the config docstring itself flags a planned re-run at that point).
**Fix:** Either compute a true union (sum of non-overlapping interval lengths across metrics' post-floor date ranges) or, more simply, document explicitly that this is a bounding span rather than a union, and consider using `max(starts)`/`min(ends)` (the *intersection*, when metrics overlap) if the intent is "the period during which every qualifying metric could have fired," matching D-05's "monitor-wide" framing more literally.

### WR-10: Hysteresis hold-branch has no bound on how long it can persist, once made reachable

**File:** `engine/monitor/hysteresis.py:38-41`
**Issue:** Independent of CR-02 above: even once the `n`/`rank` decoupling is fixed so the hold-branch is actually reachable, the branch as written holds `yesterday_state` indefinitely across any run of consecutive `today_rank is None` days — there is no cap on how many days a state can be held before either an escape (rank recovers and clears via `exit_`) or a forced reset. A permanently-broken (not transient) metric loader would leave an alert stuck in `in_entry`/`in_escalate` forever with no way to clear other than the credibility-floor case, which — per D-08 — "sample size cannot regress in practice" and so may never trigger for a metric whose *loader* is broken but whose *stored history* is untouched.
**Fix:** Not urgent given CR-02 makes this currently moot, but worth tracking alongside CR-02's fix: consider a max-consecutive-None-days cap (e.g., N sessions) after which the hold degrades to a reset, so a permanently broken loader cannot indefinitely mask a metric's true state.

### WR-11: New calibration grid test (`test_runs_across_grid_and_returns_sorted_results`) still uses non-date-typed synthetic history, understating a possible date-type mismatch in `calibrate()`'s union-span logic

**File:** `engine/tests/test_monitor/test_calibration.py:90-112`
**Issue:** The synthetic loader in this test builds `pd.Series(values, index=_dates(n))` where `_dates` returns `pd.bdate_range(...)` (a `DatetimeIndex` of `pd.Timestamp`), whereas every production loader in `metrics.py` normalizes its index to plain `datetime.date` objects (`.dt.date` throughout). Since this test is the only one exercising `calibrate()`'s new `min_date`/`max_date`/`calendar_weeks` logic end-to-end, it never proves that logic works correctly against the `datetime.date`-typed indices `calibrate()` will actually see in production (mixing `pd.Timestamp` and `datetime.date` in `min()`/`max()` comparisons across metrics would raise, or silently produce a wrong span if one metric's index type ever differs from another's).
**Fix:** Have the synthetic loader normalize its index to `datetime.date` (`.date` on the `bdate_range` result) to match production loaders, so the grid test exercises the same types `calibrate()` will see for real.

## Info

### IN-03: `check_alert_transition`'s module docstring still describes the None-rank branch as effective

**File:** `engine/monitor/hysteresis.py:1-15`
**Issue:** The module docstring and the WR-04 fix's own inline comments describe the hold-on-None behavior as a working mitigation ("a one-day I/O blip cannot manufacture a duplicate entry alert"), which is not true given CR-02 above — this will mislead the next reader into believing the gap is closed.
**Fix:** Once CR-02 is fixed for real, update the docstring to reflect the corrected data flow; until then, consider a `# NOTE:` flagging that this branch is presently unreachable given how `n`/`rank` are supplied by `ranker.py`.

---

_Reviewed: 2026-07-24_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

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
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-05-SUMMARY|26-05-SUMMARY]]
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-CONTEXT|26-CONTEXT]]
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-DISCUSSION-LOG|26-DISCUSSION-LOG]]
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-PATTERNS|26-PATTERNS]]
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-RESEARCH|26-RESEARCH]]
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-VERIFICATION|26-VERIFICATION]]

<!-- LINKS:END -->
