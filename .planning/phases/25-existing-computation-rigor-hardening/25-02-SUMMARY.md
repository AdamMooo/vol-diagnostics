---
phase: 25-existing-computation-rigor-hardening
plan: 02
subsystem: testing
tags: [vol-surface, rbf, scipy, edge-case-hardening, pytest]

requires:
  - phase: 25-existing-computation-rigor-hardening
    provides: RESEARCH edge-case catalog (E17/E18/E19), CONTEXT locked decisions
provides:
  - Symmetric try/except around the RBF fit in build_surface_payload and build_diff_payload (near-singular fit degrades to None, not crash)
  - Adversarial-chain + degenerate-input tests documenting E17 (singular fit), E18 (spot<=0), E19 (missing-column loud KeyError)
affects: [surface-render, dashboard, daily-email, phase-27-microstructure-monitor-ui]

tech-stack:
  added: []
  patterns:
    - "All three surface builders (surface/diff/movie) share one near-singular-fit defense: degrade the fit to None/skip, never propagate an uncaught LinAlgError mid-render"
    - "Schema-corruption (missing structural column) fails loudly with a KeyError; only the numerical fit failure degrades — silent-wrong is never a permitted outcome"

key-files:
  created: []
  modified:
    - engine/surface/surface_interactive.py
    - engine/tests/test_surface_interactive.py

key-decisions:
  - "E19 loud-KeyError contract exercised by dropping log_moneyness (accessed before the fit), not iv_pct — iv_pct access now sits inside the try block, so its removal degrades to None; log_moneyness preserves the visible-failure contract the threat model (T-25-04) requires"
  - "Adversarial singular-fit tests pass smoothing=0.0 to make the duplicate-point singularity deterministic (default 0.5 regularises it away)"

patterns-established:
  - "Pattern 1: mesh grid computed before the fit try-block (no dependency on rbf), fit + grid-eval wrapped together, return None on Exception"
  - "Pattern 2: duplicate a row with dte >= fit_floor so it survives the fit-set filter — duplicating a below-floor row is silently discarded and never reaches the RBF"

requirements-completed: [RIGOR-01, RIGOR-02]

duration: 14min
completed: 2026-07-26
---

# Phase 25 Plan 02: Surface-Builder Exception-Handling Symmetry Summary

**build_surface_payload and build_diff_payload now degrade a near-singular RBF fit to None exactly like build_movie_payload, with adversarial-chain tests proving defined results (None or loud KeyError) instead of a crash mid-render.**

## Performance

- **Duration:** 14 min
- **Started:** 2026-07-26
- **Completed:** 2026-07-26
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Back-ported the `try/except Exception → return None` guard around `_fit_rbf` into both single-day builders, closing gap #2 from 25-RESEARCH (exception-handling asymmetry: 2 of 3 near-identical functions defended, 1 didn't).
- All three surface builders (surface / diff / movie) now share one failure semantics for the duplicate-point near-singular fit.
- Added 4 net-new edge-case tests covering E17 (singular fit → None for both builders), E18 (spot<=0 → defined None, no crash), and E19 (missing structural column → loud KeyError).
- Full suite 463 green (was 459 baseline).

## Task Commits

1. **Task 1: Symmetric try/except around the RBF fit** — `d86c615` (fix)
2. **Task 2: Adversarial-chain + degenerate-input tests** — `7ab872e` (test)

## Files Created/Modified
- `engine/surface/surface_interactive.py` — wrapped the `_fit_rbf` + grid-eval in `build_surface_payload` (meshgrid hoisted above the try) and the two fits in `build_diff_payload` with a `return None` guard mirroring `build_movie_payload`. No change to RBF kernel, smoothing, clip, or coverage_mask.
- `engine/tests/test_surface_interactive.py` — added `TestSurfaceEdgeCases` (4 tests).

## Decisions Made
- **E19 tests `log_moneyness`, not `iv_pct`.** The plan's "e.g. drop iv_pct" would now return None (iv_pct is read inside the new try block, so its `KeyError` is swallowed). To honor threat T-25-04's loud-failure contract, the test drops `log_moneyness` — read at the top of the builder, before any try — so a corrupt schema still raises visibly. The broad `except Exception` was kept as the plan specified (mirrors movie exactly); the test-column choice is where the KeyError contract is preserved. This is within the plan's stated discretion on fixtures.
- **smoothing=0.0 in the singular-fit tests.** Default `SURFACE_INTERACTIVE_SMOOTHING=0.5` regularises duplicate points, so the singularity only fires deterministically with the regulariser removed. Passing `smoothing=0.0` is a supported kwarg and makes the red-then-green assertion reliable.

## Deviations from Plan

None - plan executed exactly as written. (The E19 column choice is a fixture decision explicitly left to discretion, not a change to the plan's action.)

## Issues Encountered
- First draft of the duplicate-chain fixture duplicated `df.iloc[0]` (a `dte=1` row), which `fit_floor=5` filters out before the fit — so no singularity and the test failed. Fixed by duplicating a `dte=7` row that survives into the fit set. Caught by the test run, not shipped.

## Self-Check: PASSED
- `engine/surface/surface_interactive.py` — FOUND, contains both new `except` guards
- `engine/tests/test_surface_interactive.py` — FOUND, `TestSurfaceEdgeCases` present
- Commit `d86c615` — FOUND
- Commit `7ab872e` — FOUND
- `pytest engine/tests` — 463 passed (baseline 459, +4)

## Next Phase Readiness
- Plan 25-03 (remaining rigor targets: NaN-vs-None contract, `_classify_term_structure` sentinel, dead `compute_vrp`) unaffected — owns different files, no coupling.
- Surface render path is now uniformly crash-safe against thin/cold-start chains.

---
*Phase: 25-existing-computation-rigor-hardening*
*Completed: 2026-07-26*

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
**Phase siblings:**
- [[_planning/vol-diagnostics/phases/25-existing-computation-rigor-hardening/25-01-PLAN|25-01-PLAN]]
- [[_planning/vol-diagnostics/phases/25-existing-computation-rigor-hardening/25-01-SUMMARY|25-01-SUMMARY]]
- [[_planning/vol-diagnostics/phases/25-existing-computation-rigor-hardening/25-02-PLAN|25-02-PLAN]]
- [[_planning/vol-diagnostics/phases/25-existing-computation-rigor-hardening/25-03-PLAN|25-03-PLAN]]
- [[_planning/vol-diagnostics/phases/25-existing-computation-rigor-hardening/25-CONTEXT|25-CONTEXT]]
- [[_planning/vol-diagnostics/phases/25-existing-computation-rigor-hardening/25-RESEARCH|25-RESEARCH]]

<!-- LINKS:END -->
