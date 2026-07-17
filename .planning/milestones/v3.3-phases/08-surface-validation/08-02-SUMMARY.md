---
phase: 08-surface-validation
plan: "02"
subsystem: gex/analytics
tags: [vol-surface, coverage-mask, nan-holes, plotly, tdd]
dependency_graph:
  requires:
    - phase: 08-01
      provides: [rbf_grid, coverage_mask]
  provides: [masked-surface-render, coverage-instrumentation]
  affects: [08-04, "Phase 10 dashboard"]
tech_stack:
  added: []
  patterns: [nan-safe-colorbar, coverage-logging]
key_files:
  created: [gex/tests/test_surface_holes.py]
  modified: [gex/analytics.py]
decisions:
  - "Clip instrumentation kept lightweight (count of supported cells pinned to 0) rather than changing rbf_grid's signature to expose raw negatives — coverage % is the primary diagnostic"
  - "Gap test uses two DTE clusters with an internal gap (not just a short-end cluster) because plot_vol_surface caps dte_max at the data's own max — a single short cluster yields no in-grid gap"
patterns_established:
  - "Mask applied via np.where(mask, IV, np.nan) immediately after rbf_grid; all downstream z-stats use np.nan* variants"
requirements_completed: [VALID-01]
metrics:
  duration: "~6m (inline)"
  completed: 2026-05-30
---

# Phase 8 Plan 02: Honest NaN Holes Summary

**One-liner:** `plot_vol_surface` now NaN-masks every grid cell with no nearby real quote (Plotly draws gaps, not extrapolation), with a NaN-safe colorbar and a `[surface] coverage NN%` stdout line.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | apply coverage_mask → NaN holes + clip/coverage instrumentation + NaN-safe z-range | 3743aa6 (feat) | gex/analytics.py, gex/tests/test_surface_holes.py |

## What Was Built

After the `rbf_grid` call in `plot_vol_surface`:
- `mask = coverage_mask(...)`; `IV = np.where(mask, IV, np.nan)` — unsupported cells become holes.
- All-NaN guard → `_empty("no supported cells")`.
- `coverage_pct = 100 * mask.mean()`; `n_clipped` = supported cells the `>=0` clip pinned to 0; logged as `[surface] {ticker}: coverage NN%  zero-clipped cells M`.
- `iv_floor`/`iv_cap` switched to `np.nanmin` / `np.nanpercentile` so holes don't break the colorbar.
- `go.Surface` trace unchanged — Plotly renders NaN z natively as holes.

## Test Results

- `test_surface_holes.py` (3): dense chain <5% NaN; internal DTE-gap chain has NaN at the ~45-DTE gap while near-cluster columns keep real values; empty df still returns a valid Figure.
- Full suite: **77 passed** (74 + 3 new), 0 regressions. Existing `test_vol_surface_strip` (colorscale/trace) still green under masking.

## Deviations from Plan

Minor: the plan's gap-test premise ("quotes only at DTE 7/14/21, grid to 90") doesn't hold because `plot_vol_surface` caps `dte_max` at the data max — a short-only cluster gives a 5–21 grid with no gap. Adjusted the fixture to two DTE clusters with an internal gap, which exercises the same VALID-01 behavior correctly.

## Threat Flags

None — local-only analytics, no new surface.

## Self-Check: PASSED

- `plot_vol_surface` calls `coverage_mask(` and `np.where(mask, IV, np.nan)`: FOUND
- `np.nanmin` + `np.nanpercentile` for iv_floor/iv_cap: FOUND
- `[surface] ... coverage` print: FOUND
- 77 tests pass: VERIFIED

## Next Phase Readiness

Render path now honest. 08-04's trust readout will surface coverage % as a raw number above this masked surface.

---
*Phase: 08-surface-validation*
*Completed: 2026-05-30*

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/08-surface-validation/08-01-PLAN|08-01-PLAN]]
- [[_planning/gamma-omm/phases/08-surface-validation/08-01-SUMMARY|08-01-SUMMARY]]
- [[_planning/gamma-omm/phases/08-surface-validation/08-02-PLAN|08-02-PLAN]]
- [[_planning/gamma-omm/phases/08-surface-validation/08-03-PLAN|08-03-PLAN]]
- [[_planning/gamma-omm/phases/08-surface-validation/08-04-PLAN|08-04-PLAN]]
- [[_planning/gamma-omm/phases/08-surface-validation/08-CONTEXT|08-CONTEXT]]
- [[_planning/gamma-omm/phases/08-surface-validation/08-DISCUSSION-LOG|08-DISCUSSION-LOG]]

<!-- LINKS:END -->
