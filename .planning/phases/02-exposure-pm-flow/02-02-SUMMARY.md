---
phase: 02-exposure-pm-flow
plan: "02"
subsystem: gex
tags: [validation, snapshot, load-yesterday, classify-vs-yesterday, tdd]
dependency_graph:
  requires: [02-01]
  provides: [vanna_exposure-in-parquet, load_yesterday, _classify_vs_yesterday]
  affects: [gex/run_daily.py]
tech_stack:
  added: []
  patterns: [never-raise-contract, dt.date-normalization]
key_files:
  modified:
    - gex/validation.py
decisions:
  - "pandas_market_calendars imported locally inside load_yesterday — keeps validation.py import-light"
  - "dt.date normalization (pd.to_datetime().dt.date) guards against datetime64 vs date.date parquet mismatch"
metrics:
  duration: "~5 minutes"
  completed: "2026-05-05"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 1
---

# Phase 02 Plan 02: Validation Extensions Summary

One-liner: `save_snapshot()` gains `vanna_exposure`, `load_yesterday()` looks up prior NYSE session from parquet, `_classify_vs_yesterday()` labels regime change as FLIPPED/INTENSIFIED/EASED/UNCHANGED.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | vanna_exposure + load_yesterday | 9442adb | gex/validation.py |
| 2 | _classify_vs_yesterday | 9442adb | gex/validation.py |

## What Was Built

**`save_snapshot()` extended:**
- Row dict gains `"vanna_exposure": summary.get("net_vex")` — old parquet rows read back as NaN (no migration needed)

**`load_yesterday(ticker, today=None) -> pd.Series | None`:**
- Uses `pandas_market_calendars` NYSE schedule to find prior trading session (not calendar day minus one)
- Normalises parquet date dtype via `pd.to_datetime().dt.date` before filter
- Never raises — all exceptions return None silently

**`_classify_vs_yesterday(net_gex_today, regime_today, prior) -> str`:**
- FLIPPED: regime sign changed
- INTENSIFIED: same regime, magnitude >5% larger
- EASED: same regime, magnitude >5% smaller
- UNCHANGED: within ±5% band or prior net_gex == 0

## Deviations from Plan

None.

## Self-Check

### Assertions pass:
- `vanna_exposure` in `save_snapshot` source
- `load_yesterday('NOTICKER_FAKE')` returns None without raising
- All 5 `_classify_vs_yesterday` cases (FLIPPED, INTENSIFIED, EASED, UNCHANGED, zero-guard)

### Tests:
- 51 passed (no regressions)

## Self-Check: PASSED

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/02-exposure-pm-flow/02-01-PLAN|02-01-PLAN]]
- [[_planning/gamma-omm/phases/02-exposure-pm-flow/02-01-SUMMARY|02-01-SUMMARY]]
- [[_planning/gamma-omm/phases/02-exposure-pm-flow/02-02-PLAN|02-02-PLAN]]
- [[_planning/gamma-omm/phases/02-exposure-pm-flow/02-03-PLAN|02-03-PLAN]]
- [[_planning/gamma-omm/phases/02-exposure-pm-flow/02-03-SUMMARY|02-03-SUMMARY]]
- [[_planning/gamma-omm/phases/02-exposure-pm-flow/02-04-PLAN|02-04-PLAN]]
- [[_planning/gamma-omm/phases/02-exposure-pm-flow/02-04-SUMMARY|02-04-SUMMARY]]
- [[_planning/gamma-omm/phases/02-exposure-pm-flow/02-CONTEXT|02-CONTEXT]]
- [[_planning/gamma-omm/phases/02-exposure-pm-flow/02-DISCUSSION-LOG|02-DISCUSSION-LOG]]
- [[_planning/gamma-omm/phases/02-exposure-pm-flow/02-PATTERNS|02-PATTERNS]]
- [[_planning/gamma-omm/phases/02-exposure-pm-flow/02-RESEARCH|02-RESEARCH]]

<!-- LINKS:END -->
