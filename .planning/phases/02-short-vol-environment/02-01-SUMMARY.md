---
phase: 02-short-vol-environment
plan: 01
subsystem: dashboard
tags: [short-vol, percentile-distribution, signal-conditioning, new-section]
dependency_graph:
  requires: []
  provides: [section_short_vol_environment]
  affects: [dashboard.py]
tech_stack:
  added: []
  patterns: [monthly-sampling, forward-metric-computation, percentile-table-formatting]
key_files:
  created: []
  modified:
    - path: dashboard.py
      change: "Add section_short_vol_environment + _last_trading_day_per_month + _primary_underlying helpers"
decisions:
  - "Added _last_trading_day_per_month and _primary_underlying helpers to worktree dashboard.py — these exist in the main repo's unstaged working tree but not in the committed HEAD version the worktree is based on"
  - "Placed new function after section_e_subperiod (no section_market_outcomes in this version of dashboard.py)"
  - "Used per-row _forward_rv21 helper rather than vectorized shift approach — clearer semantics and confirmed non-NaN on >150 of ~179 monthly rows"
metrics:
  duration: "4 minutes"
  completed: "2026-05-04"
  tasks_completed: 1
  tasks_total: 1
  files_modified: 1
---

# Phase 02 Plan 01: section_short_vol_environment Summary

One-liner: Signal-conditioned percentile distributions (p10/25/50/75/90) of VRP capture ratio, move magnitude, and IV change over ~179 monthly samples from 2010-present, with today's quartile marked '*'.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Implement section_short_vol_environment | 0c9c546 | dashboard.py |

## What Was Built

`section_short_vol_environment(sigs: Signals, panels: Panels) -> str` added to `dashboard.py`.

Output: one table per BUCKETED_SIGNAL (vrp, term, skew, fragility) showing three short-vol environment metrics across four signal quartile bins.

**Three forward metrics computed at each monthly sample point:**
- VRP capture ratio: forward 21d realized vol / IV at period open (ratio; >1.0 = premise failed)
- Move magnitude: abs(spot_t+21 / spot_t - 1) * 100 (absolute %, direction-agnostic)
- IV change: iv_t+21 - iv_t (vol pts; positive = vol spike)

**Two helpers also added** (required for the function, present in main repo working tree but not in the committed HEAD version):
- `_last_trading_day_per_month(daily_df, before)` — resample to actual last trading day per calendar month
- `_primary_underlying(panels)` — return 'SPX' if present, else first column

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Missing helper functions in worktree's dashboard.py**
- **Found during:** Task 1
- **Issue:** The plan references `_last_trading_day_per_month` and `_primary_underlying` as existing helpers to reuse, but the worktree is based on committed HEAD (`23d58ed`) which predates these helpers. They exist only in the main repo's unstaged working tree.
- **Fix:** Added both helpers to the worktree's dashboard.py before the new function. Implementations match the unstaged version exactly.
- **Files modified:** dashboard.py
- **Commit:** 0c9c546

**2. [Rule 3 - Blocking] Worktree dashboard.py has no section_market_outcomes**
- **Found during:** Task 1
- **Issue:** Plan says to insert after `section_market_outcomes`, but this function doesn't exist in the committed version.
- **Fix:** Placed `section_short_vol_environment` after `section_e_subperiod` and before `build_dashboard`. Position is equivalent -- section is present and callable.
- **Files modified:** dashboard.py
- **Commit:** 0c9c546

## Verification Results

All acceptance criteria met:
- `def section_short_vol_environment` exists (one match)
- Signature: `section_short_vol_environment(sigs: Signals, panels) -> str`
- `_last_trading_day_per_month` called inside the function
- `_bucket_by_pct` called inside the function
- Automated verify command: PASS
- Four signal sub-sections (vrp, term, skew, fragility): PASS
- Three metric rows per sub-section: PASS
- Today's quartile marked '*': PASS (Q3 for vrp today at 0.63)
- Footer "Historical calibration only. ~48 obs per quartile. Not a forecast.": 4 occurrences (one per signal)
- No new top-level imports added

## Known Stubs

None. All three metrics are wired to live panel data.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes. Function reads from existing in-memory `Panels` and `Signals` objects only. T-02-02 (NaN propagation) mitigated: `np.nanpercentile` used throughout; assert guards that >= 150 of ~179 monthly rows have non-NaN forward_rv before table render.

## Self-Check: PASSED

- FOUND: dashboard.py modified in worktree (0c9c546)
- FOUND: 0c9c546 in git log
- FOUND: .planning/phases/02-short-vol-environment/02-01-SUMMARY.md
- All verify assertions passed
