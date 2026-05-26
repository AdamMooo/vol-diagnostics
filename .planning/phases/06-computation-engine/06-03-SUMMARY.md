---
phase: "06-computation-engine"
plan: "03"
subsystem: "gex/compute + gex/validation"
tags: ["compute-wiring", "dead-code-removal", "parquet-schema", "rv20", "vrp", "tdd"]
dependency_graph:
  requires:
    - "06-01: gex/vol_metrics.py — compute_skew_25d, compute_term_structure, compute_rv20, compute_vrp"
  provides:
    - "gex/compute.py: compute_ticker() returns skew, term_structure, rv20, vrp keys"
    - "gex/validation.py: save_snapshot() persists rv20 and vrp to parquet"
  affects:
    - "Phase 7 rendering — consumes new keys from compute_ticker() return dict"
    - "streamlit_app.py — fetch_ticker() already wraps compute_ticker()"
tech_stack:
  added: []
  patterns:
    - "TDD RED/GREEN cycle"
    - "cold-start guard (empty history → rv20, vrp = None)"
    - "parquet forward-compat schema extension (append only, never reorder)"
key_files:
  created:
    - gex/tests/test_compute_wiring.py
    - gex/tests/test_validation_schema.py
  modified:
    - gex/compute.py
    - gex/validation.py
decisions:
  - "compute_surface_slopes fully removed (import + call site + summary injections)"
  - "Cold-start guard: hist.empty or 'spot' not in hist.columns → rv20, vrp = None"
  - "load_history() returns descending date order — reversed with .iloc[::-1] before passing to compute_rv20"
  - "rv20/vrp also written to summary dict (not just return dict) so save_snapshot() can persist them"
  - "Parquet schema extended by append only — _FLOAT_COLS order preserved, no renames"
metrics:
  duration: "~8 min"
  completed: "2026-05-26"
  tasks_completed: 2
  files_created: 2
  files_modified: 2
  tests_added: 18
  tests_total: 59
requirements_satisfied:
  - INFRA-01
  - INFRA-02
  - CTX-02
---

# Phase 6 Plan 03: Compute Wiring and Parquet Schema Extension Summary

**One-liner:** compute_ticker() wired to all four vol_metrics functions with cold-start guard; parquet schema extended with rv20 and vrp; compute_surface_slopes dead code removed; 59 tests pass.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Write failing tests for compute_ticker() wiring and dead-code removal | da603c6 | gex/tests/test_compute_wiring.py |
| 1 (GREEN) | Wire vol_metrics into compute_ticker, remove compute_surface_slopes | 65370e4 | gex/compute.py |
| 2 (RED) | Write failing tests for validation.py rv20 and vrp schema extension | 3bfd8e8 | gex/tests/test_validation_schema.py |
| 2 (GREEN) | Extend parquet schema in validation.py | b6c0f4c | gex/validation.py |

## What Was Built

**`gex/compute.py`** — compute_ticker() extended:

- `compute_surface_slopes` removed from exposure_engine import and call site; `summary["strike_slope"]` and `summary["term_slope"]` assignments removed.
- New imports: `from gex.vol_metrics import compute_skew_25d, compute_term_structure, compute_rv20, compute_vrp` and `from gex.validation import load_history`.
- Cold-start guard: `if hist.empty or "spot" not in hist.columns: rv20, vrp = None, None`; otherwise reverses load_history()'s descending-date series before passing to compute_rv20.
- Return dict gains four new keys: `skew`, `term_structure`, `rv20`, `vrp`.
- Summary dict gains `rv20` and `vrp` (needed for save_snapshot() persistence).

**`gex/validation.py`** — parquet schema extended:

- `_FLOAT_COLS` tuple appended with `"rv20"` and `"vrp"` (order preserved, no renames).
- `save_snapshot()` row dict appended with `rv20: summary.get("rv20")` and `vrp: summary.get("vrp")`.
- Module docstring Columns list updated.
- Forward-compat: existing `for col in _FLOAT_COLS: if col in hist.columns` read loop handles new columns — old parquet files load without error, new columns come back as NaN.

**Tests added — 18 new tests across 2 files:**

`gex/tests/test_compute_wiring.py` (12 tests):
- `TestDeadCodeRemoved` — 3 static source text assertions confirming compute_surface_slopes, strike_slope, term_slope are gone.
- `TestNewImports` — 2 static assertions confirming vol_metrics and load_history imports exist.
- `TestComputeTickerReturnKeys` — 7 tests via mocked pipeline: return dict has all four new keys; summary dict has rv20/vrp; cold-start sets both to None.

`gex/tests/test_validation_schema.py` (6 tests):
- `TestFloatColsSchema` — rv20 and vrp in _FLOAT_COLS.
- `TestSaveSnapshotRowDict` — rv20 persisted, vrp persisted, None written as null.
- `TestOldSnapshotCompat` — old parquet without rv20/vrp loads without crash.

## Test Results

```
59 passed in 7.55s  (41 existing + 18 new)
```

## TDD Gate Compliance

**Task 1:**
- RED gate: `test(06-03): add failing tests for compute_ticker wiring and dead-code removal` (da603c6) — 5 failures + 7 errors confirmed before implementation
- GREEN gate: `feat(06-03): wire vol_metrics into compute_ticker, remove compute_surface_slopes dead code` (65370e4) — 53 tests pass

**Task 2:**
- RED gate: `test(06-03): add failing tests for validation.py rv20 and vrp schema extension` (3bfd8e8) — 5 failures confirmed before implementation
- GREEN gate: `feat(06-03): extend validation.py parquet schema with rv20 and vrp columns` (b6c0f4c) — 59 tests pass

## Deviations from Plan

**1. [Rule 0 - Count] 18 tests added, not plan-estimated count**

The plan's success criteria cited "34 tests pass (23 existing + 11 from Plan 01)" as a baseline, but the actual baseline entering Plan 03 was 41 tests (Wave 1 added 12 not 11, and existing tests were 29 not 23). Final count is 59, not 34. This is more coverage — no correctness issue.

None — plan executed exactly as written in terms of behavior.

## Known Stubs

None — all four vol_metrics functions are fully wired; parquet schema extension is complete. No data sources are mocked in production code.

## Threat Flags

None — no new network endpoints, auth paths, or trust boundary crossings introduced. The cold-start guard for T-06-03-01 is implemented exactly as specified.

## Self-Check: PASSED

- FOUND: gex/compute.py
- FOUND: gex/validation.py
- FOUND: gex/tests/test_compute_wiring.py
- FOUND: gex/tests/test_validation_schema.py
- FOUND: da603c6 (test RED compute)
- FOUND: 65370e4 (feat GREEN compute)
- FOUND: 3bfd8e8 (test RED validation)
- FOUND: b6c0f4c (feat GREEN validation)
- 59 tests pass, 0 failures

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/06-computation-engine/06-01-PLAN|06-01-PLAN]]
- [[_planning/gamma-omm/phases/06-computation-engine/06-01-SUMMARY|06-01-SUMMARY]]
- [[_planning/gamma-omm/phases/06-computation-engine/06-02-PLAN|06-02-PLAN]]
- [[_planning/gamma-omm/phases/06-computation-engine/06-02-SUMMARY|06-02-SUMMARY]]
- [[_planning/gamma-omm/phases/06-computation-engine/06-03-PLAN|06-03-PLAN]]
- [[_planning/gamma-omm/phases/06-computation-engine/06-CONTEXT|06-CONTEXT]]
- [[_planning/gamma-omm/phases/06-computation-engine/06-PATTERNS|06-PATTERNS]]
- [[_planning/gamma-omm/phases/06-computation-engine/06-RESEARCH|06-RESEARCH]]

<!-- LINKS:END -->
