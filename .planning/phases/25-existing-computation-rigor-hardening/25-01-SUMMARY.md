---
phase: 25-existing-computation-rigor-hardening
plan: 01
subsystem: vol-metrics
tags: [edge-case-hardening, dead-code-removal, tdd, nan-guard]
requires: []
provides:
  - "insufficient_data term-structure sentinel"
  - "NaN-close guards for compute_term_ratios + compute_vvix_level"
  - "compute_vrp removed"
affects:
  - engine/vol/vol_metrics.py
tech-stack:
  added: []
  patterns:
    - "pd.isna missing-value guard at store->compute boundary"
    - "distinct sentinel string over substantive default claim"
key-files:
  created: []
  modified:
    - engine/vol/vol_metrics.py
    - engine/tests/test_vol_metrics.py
    - engine/tests/test_term_ratios.py
    - CLAUDE.md
decisions:
  - "_classify_term_structure returns 'insufficient_data' (not 'normal') for <2 points — no display consumer reads classification, so no display-layer edit needed"
  - "compute_vrp deleted cleanly (no shim) — zero non-test callers, superseded by vrp_history.vrp_percentile"
  - "0.0 last-row close already returned None via the truthy guard; pd.isna adds the NaN case without changing zero behavior"
metrics:
  duration: ~25m
  completed: 2026-07-26
  tasks: 3
  files_changed: 4
  tests_before: 449
  tests_after: 459
---

# Phase 25 Plan 01: Existing Computation Rigor Hardening Summary

Hardened three defensive gaps in `engine/vol/vol_metrics.py` — a term-structure sentinel, dual NaN-close guards, and dead-code removal — each backed by red-then-green edge-case tests, with no change to any RV20/skew/term formula.

## What Was Built

**Task 1 — term-structure insufficient-data sentinel.** `_classify_term_structure` now returns `"insufficient_data"` for `<2` term points instead of falsely claiming `"normal"` (a substantive curve-shape claim on data that cannot support one). Docstring updated to document the sentinel. Verified no display consumer reads `classification` (app.py/report.py use `front_atm_iv`/`back_atm_iv` only; compute_wiring/oi_wiring only mock it), so no display-layer edit was required. Closes T-25-02.

**Task 2 — NaN-close guards for two identical latent bugs.** Both `compute_term_ratios._latest_close` and `compute_vvix_level` used `float(df.iloc[-1]["close"])`, which returns a truthy NaN float on a partial/corrupt vol-index fetch, silently bypassing downstream `is None` checks. Added a `pd.isna` guard (the codebase's existing missing-value idiom) before the float return in both. Closes T-25-01 at the store→compute trust boundary.

**Task 3 — dead compute_vrp removal + RV20 coverage.** Deleted `compute_vrp()` (grep-confirmed zero non-test callers, superseded by `vrp_history.vrp_percentile`), its `TestComputeVrp` class, the import, and its CLAUDE.md engine-table mention — clean deletion, no shim. Added RV20 edge tests exercising the pre-existing (untested) guards: NaN price → None, non-positive price → None, 21 identical prices → exactly 0.0.

## Task-by-Task

| Task | Name | Commits | Files |
| ---- | ---- | ------- | ----- |
| 1 | Term-structure sentinel + degenerate-input tests | a47dea8 (test), 9807f5d (feat) | vol_metrics.py, test_vol_metrics.py |
| 2 | NaN-close guard for term_ratios + vvix_level | d0ed6d1 (test), 4e28887 (fix) | vol_metrics.py, test_term_ratios.py, test_vol_metrics.py |
| 3 | Remove dead compute_vrp + sync CLAUDE.md + RV20 tests | 0f72887 (refactor) | vol_metrics.py, test_vol_metrics.py, CLAUDE.md |

## Verification

- `pytest engine/tests/test_vol_metrics.py engine/tests/test_term_ratios.py` — 100% green
- Full suite `pytest engine/tests` — **459 passed** (449 baseline − 3 removed compute_vrp tests + 13 new edge tests = net +10 collected)
- `grep -rn compute_vrp engine/ app.py` — no matches (function, tests, import all gone)
- CLAUDE.md engine-table row now lists `compute_rv20, skew/term helpers` only

## TDD Gate Compliance

Tasks 1 and 2 (`tdd="true"`) each have a RED `test(...)` commit followed by a GREEN `feat(...)`/`fix(...)` commit. RED phases were confirmed failing before implementation (Task 1: 4 failing sentinel assertions; Task 2: 2 failing NaN-close assertions). No unexpected passes during RED.

## Deviations from Plan

None — plan executed exactly as written. The 0.0-last-row-close case (E14) was already returning None via the pre-existing truthy `(close_9d and close_30d)` guard; the `pd.isna` fix targets the NaN case specifically, and the E14 test is retained as a regression guard, as the plan intended.

## Self-Check: PASSED

- engine/vol/vol_metrics.py — FOUND (compute_vrp removed, sentinel + guards present)
- engine/tests/test_vol_metrics.py — FOUND (TestComputeVrp removed, edge tests added)
- engine/tests/test_term_ratios.py — FOUND (NaN/zero-close tests added)
- CLAUDE.md — FOUND (row synced)
- Commits a47dea8, 9807f5d, d0ed6d1, 4e28887, 0f72887 — all present in git log

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
**Phase siblings:**
- [[_planning/vol-diagnostics/phases/25-existing-computation-rigor-hardening/25-01-PLAN|25-01-PLAN]]
- [[_planning/vol-diagnostics/phases/25-existing-computation-rigor-hardening/25-02-PLAN|25-02-PLAN]]
- [[_planning/vol-diagnostics/phases/25-existing-computation-rigor-hardening/25-03-PLAN|25-03-PLAN]]
- [[_planning/vol-diagnostics/phases/25-existing-computation-rigor-hardening/25-CONTEXT|25-CONTEXT]]
- [[_planning/vol-diagnostics/phases/25-existing-computation-rigor-hardening/25-RESEARCH|25-RESEARCH]]

<!-- LINKS:END -->
