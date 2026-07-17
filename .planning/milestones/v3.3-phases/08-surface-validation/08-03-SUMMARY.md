---
phase: 08-surface-validation
plan: "03"
subsystem: gex/exposure_engine
tags: [surface-diagnostics, rmse, cross-validation, coherence, snapshot-schema, tdd]
dependency_graph:
  requires:
    - phase: 08-01
      provides: [coverage_mask, config.SURFACE_SMOOTHING]
  provides: [surface_diagnostics, snapshot-diagnostic-columns, "compute_ticker.surface_diag"]
  affects: [08-04, "Phase 9 surface_evolution", "Phase 10 dashboard"]
tech_stack:
  added: []
  patterns: [pure-diagnostic-function, leave-one-expiry-out-cv, additive-snapshot-schema, report-only-coherence]
key_files:
  created: [gex/tests/test_surface_diagnostics.py]
  modified: [gex/exposure_engine.py, gex/compute.py, gex/validation.py, gex/tests/test_validation_schema.py, .planning/REQUIREMENTS.md]
decisions:
  - "Coherence computed on RAW quotes (calendar via ~5% moneyness buckets, butterfly via per-expiry strike 2nd-difference) — deterministic + testable, and matches the D-11 watch-condition which is about the quotes, not the smoothed fit"
  - "surface_diagnostics degrades to NaN on <2 distinct expiries — a single expiry is a smile not a surface, and the TPS-RBF monomial matrix is singular on collinear points (verified)"
  - "Added a column-presence guard ({strike,dte,iv_pct}) so a malformed/mock surface_df degrades instead of KeyError — keeps the existing compute-wiring mock green without churning its fixture"
  - "ROADMAP.md SC#5 reword (plan Task 3) is N/A: .planning/ROADMAP.md is the stale v3.1 doc with no v3.3 Phase 8 section; v3.3 phase definitions live in REQUIREMENTS.md"
patterns_established:
  - "Diagnostics flow compute_ticker -> summary -> save_snapshot as additive float columns; coherence booleans persist as bool"
requirements_completed: [VALID-02, VALID-04]
metrics:
  duration: "~20m (inline)"
  completed: 2026-05-30
---

# Phase 8 Plan 03: Surface Fit-Honesty + Coherence Diagnostics Summary

**One-liner:** Headless `surface_diagnostics()` computes RBF fit RMSE/max-resid, leave-one-expiry-out CV, coverage %, and report-only calendar+butterfly coherence; wired into `compute_ticker` and persisted as additive snapshot columns; VALID-04 reworded to surface coherence.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | surface_diagnostics() + tests | 65e8661 (feat) | gex/exposure_engine.py, gex/tests/test_surface_diagnostics.py |
| 2 | wire into compute_ticker + additive snapshot cols | b450eac (feat) | gex/compute.py, gex/validation.py, gex/tests/test_validation_schema.py |
| 3 | reword VALID-04 → surface coherence | 8c31c89 (docs) | .planning/REQUIREMENTS.md |

## What Was Built

- **`surface_diagnostics(surface_df, spot) -> dict`** in `exposure_engine.py` (beside `compute_surface_slopes`). Keys: `coverage_pct, fit_rmse, max_resid, cv_rmse, coherence_calendar, coherence_butterfly, coherence_violations`. Leave-one-EXPIRY-out CV (refits RBFInterpolator per held-out expiry; skips folds leaving <2 training expiries). Coherence is flag/count/print-only, never repairs. Deferred imports of `rbf_grid`/`coverage_mask` (no circular import). No sklearn.
- **`compute_ticker`** computes `surface_diag`, logs a `[diag] {ticker}` line, merges the 7 scalars into `summary`, and returns `surface_diag` (for Streamlit/08-04 without recompute).
- **`validation.save_snapshot`** persists the 5 floats (`coverage_pct/fit_rmse/max_resid/cv_rmse/coherence_violations`) + 2 coherence bools as additive columns; `_FLOAT_COLS` extended; docstring Columns list updated. Old snapshots still load.
- **VALID-04 reworded** "No-arbitrage sanity checks" → "Surface-coherence checks" (fit-QA, never a trade signal, never auto-repair, no Phase 8 UI).

## Test Results

- `test_surface_diagnostics.py` (7): key set; smooth surface coherent w/ small finite residuals + finite CV; injected calendar inversion → calendar FAIL; injected butterfly bump → butterfly FAIL; sparse → NaN-degraded; single-expiry → cv_rmse NaN; empty → degraded.
- `test_validation_schema.py` (+3): diagnostics in `_FLOAT_COLS`; diagnostics persisted; pre-diagnostics snapshot loads.
- Full suite: **87 passed** (77 + 10 new), 0 regressions. `surface_diagnostics` imports with no circular dep; no sklearn.

## Deviations from Plan

1. **Coherence on raw quotes, not the fitted grid** — the plan offered either; raw-quote checks (5% moneyness buckets for calendar, per-expiry 2nd-difference for butterfly) are deterministic/testable and align with the D-11 watch-condition (about delayed/crossed quotes). No RBF-smoothing in the coherence path.
2. **Single-expiry → NaN-degraded** — not explicitly in the plan, but required: the TPS-RBF monomial matrix is singular on one collinear expiry (verified with a probe). Matches `plot_vol_surface`'s own single-expiry guard.
3. **Column-presence guard added** — `surface_diagnostics` returns NaN if `{strike,dte,iv_pct}` are absent, so the existing `test_compute_wiring` mock (whose `fake_surface_df` lacks `dte`/`iv_pct`) stays green without editing its fixture. Defensive, never-raise.
4. **ROADMAP.md Task-3 reword N/A** — `.planning/ROADMAP.md` is the stale v3.1 roadmap (no v3.3 Phase 8 / SC#5). The v3.3 phase lives in REQUIREMENTS.md (reworded). Flagged as planning-doc drift for the phase-completion report; verify adjusted to assert REQUIREMENTS reworded + ROADMAP carries no stale no-arb wording.

## Threat Flags

None — local-only analytics, pure functions, additive parquet schema.

## Self-Check: PASSED

- `exposure_engine.surface_diagnostics(` with exact 7-key dict: FOUND
- leave-one-expiry-out (`np.unique` + RBFInterpolator inside loop): FOUND
- no sklearn/scikit import: VERIFIED
- compute.py merges scalars + returns `surface_diag`: FOUND
- validation `_FLOAT_COLS` has the 5 floats; old snapshots load: VERIFIED
- VALID-04 reworded: VERIFIED
- 87 tests pass: VERIFIED

## Next Phase Readiness

`compute_ticker(...)['surface_diag']` is live — 08-04's Streamlit trust readout reads it directly. Diagnostics now persist daily for Phase 9/10 history.

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
- [[_planning/gamma-omm/phases/08-surface-validation/08-02-SUMMARY|08-02-SUMMARY]]
- [[_planning/gamma-omm/phases/08-surface-validation/08-03-PLAN|08-03-PLAN]]
- [[_planning/gamma-omm/phases/08-surface-validation/08-04-PLAN|08-04-PLAN]]
- [[_planning/gamma-omm/phases/08-surface-validation/08-CONTEXT|08-CONTEXT]]
- [[_planning/gamma-omm/phases/08-surface-validation/08-DISCUSSION-LOG|08-DISCUSSION-LOG]]

<!-- LINKS:END -->
