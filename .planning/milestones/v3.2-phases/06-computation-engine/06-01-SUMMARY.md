---
phase: "06-computation-engine"
plan: "01"
subsystem: "gex/vol_metrics"
tags: ["vol-metrics", "skew", "term-structure", "rv20", "vrp", "tdd"]
dependency_graph:
  requires: []
  provides: ["gex/vol_metrics.py: compute_skew_25d, compute_term_structure, compute_rv20, compute_vrp"]
  affects: ["gex/compute.py (Plan 03 wiring target)"]
tech_stack:
  added: []
  patterns: ["pure functions — no I/O, no side effects", "TDD RED/GREEN cycle", "groupby expiry (not T_years)"]
key_files:
  created:
    - gex/vol_metrics.py
    - gex/tests/test_vol_metrics.py
  modified: []
decisions:
  - "25d call uses literal 0.25 (not config.SKEW_CALL_DELTA which is 0.50 — different metric)"
  - "Bucket assignment: dte <= 45 → front_month, 46-90 → second_month, else skip"
  - "len < 2 puts or calls per bucket → bucket value is None (not error)"
  - "Flat classification checked first before slope-based classifications"
  - "humped uses third-split average comparison (works for 3+ points)"
metrics:
  duration: "~2 min"
  completed: "2026-05-26"
  tasks_completed: 2
  files_created: 2
  tests_added: 12
  tests_total: 35
requirements_satisfied:
  - INFRA-01
  - CTX-02
---

# Phase 6 Plan 01: Vol Metrics Computation Functions Summary

**One-liner:** Four pure vol computation functions — 25d skew bucketing, term structure classification, 20-day RV, and VRP — built TDD with 12 tests, 35 total passing.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Write failing tests for all four vol_metrics functions | 3f4138e | gex/tests/test_vol_metrics.py |
| 2 (GREEN) | Implement gex/vol_metrics.py until all 12 tests pass | f3a26cc | gex/vol_metrics.py |

## What Was Built

`gex/vol_metrics.py` — four pure computation functions:

- **`compute_skew_25d(df, spot)`** — selects the 25Δ put and 25Δ call per expiry, buckets into `front_month` (≤45 DTE) and `second_month` (46–90 DTE), returns `None` per bucket when < 2 puts or calls qualify. Groups by `"expiry"` string (not `T_years`).

- **`compute_term_structure(df, spot)`** — extracts ATM IV per expiry (OTM call preferred, put fallback), classifies curve as `flat / humped / inverted / normal`. Flat check first (< 1 vol point per 30 DTE); humped uses third-split average comparison; inverted is negative total slope; normal is default.

- **`compute_rv20(spot_history)`** — 20-day annualized realized vol using `ddof=1` log returns from `iloc[-21:]`. Returns `None` when fewer than 21 prices available.

- **`compute_vrp(iv30, rv20)`** — `iv30 - rv20` with `None` propagation on either input.

`gex/tests/test_vol_metrics.py` — 12 unit tests across 4 classes covering all classification paths, None propagation, and manual calculation verification.

## Test Results

```
35 passed in 6.11s  (23 existing + 12 new)
```

## TDD Gate Compliance

- RED gate: `test(06-01): add failing tests for vol_metrics` (3f4138e) — ImportError confirmed before implementation
- GREEN gate: `feat(06-01): implement vol_metrics — skew_25d, term_structure, rv20, vrp` (f3a26cc) — all 35 tests pass

## Deviations from Plan

**1. [Rule 0 - Minor] 12 tests collected, not 11**
- The plan estimated 11 tests. The actual count is 12 — `test_vrp_none_propagation` tests both `None` propagation cases in separate assertions but is one test method. The additional count came from correctly implementing `test_term_structure_keys` as its own test. All plan-specified behaviors are covered.
- No plan fix needed; 12 > 11 is more coverage.

## Known Stubs

None — functions are fully implemented and self-contained pure computations.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced. Functions are pure; inputs validated via guard clauses as specified in T-06-01.

## Self-Check: PASSED

- FOUND: gex/vol_metrics.py
- FOUND: gex/tests/test_vol_metrics.py
- FOUND: 3f4138e (test commit)
- FOUND: f3a26cc (feat commit)
- 35 tests pass, 0 failures

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/agent-a789fc7b4484fac12/ROADMAP|ROADMAP]] · [[_planning/agent-a789fc7b4484fac12/STATE|STATE]]
**Phase siblings:**
- [[_planning/agent-a789fc7b4484fac12/phases/06-computation-engine/06-01-PLAN|06-01-PLAN]]
- [[_planning/agent-a789fc7b4484fac12/phases/06-computation-engine/06-02-PLAN|06-02-PLAN]]
- [[_planning/agent-a789fc7b4484fac12/phases/06-computation-engine/06-03-PLAN|06-03-PLAN]]

<!-- LINKS:END -->
