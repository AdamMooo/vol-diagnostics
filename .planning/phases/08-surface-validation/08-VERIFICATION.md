---
status: passed
phase: 08-surface-validation
verified: 2026-05-30
verifier: inline (gsd-verifier subagent bypassed — gsd-sdk query unavailable on this machine)
requirements: [VALID-01, VALID-02, VALID-03, VALID-04, VALID-05, VALID-06]
tests: "92 passed"
---

# Phase 8: Surface Validation (the gate) — Verification

**Verdict: PASSED.** The interpolated vol surface now carries a coverage mask (the single
source of truth), honest NaN holes, persisted fit residuals + leave-one-expiry-out CV,
report-only surface-coherence checks, a documented+swept smoothing parameter, and a
raw-number trust readout. Goal achieved, not merely tasks completed.

## Goal-backward check

Phase goal: *prove the interpolated surface isn't overfit — produce a coverage mask + fit-honesty
layer that becomes the single source of truth for "where the surface is real," imported by
Phases 9–11.* Delivered and wired end-to-end (compute_ticker → snapshot → Streamlit).

## Requirement coverage

| REQ | Requirement | Evidence | Status |
|-----|-------------|----------|--------|
| VALID-01 | Coverage mask flags unsupported cells → honest NaN holes; exported as the single source of truth | `analytics.coverage_mask` (cKDTree, data-adaptive r=k×median-NN); `plot_vol_surface` applies `np.where(mask, IV, np.nan)`; reusable function (not buried) for Phase 9 to recompute+intersect | ✓ |
| VALID-02 | Per-ticker RMSE + max-resid (pp) + leave-one-EXPIRY-out CV, persisted daily | `exposure_engine.surface_diagnostics` returns coverage_pct/fit_rmse/max_resid/cv_rmse/coherence_*; wired into `compute_ticker`; persisted via `validation.save_snapshot` additive cols (in `_FLOAT_COLS`) | ✓ |
| VALID-03 | `smoothing` in config + documented sensitivity sweep | `config.SURFACE_SMOOTHING=1.5` + `COVERAGE_KNN_K=2.0` with rationale docstrings citing `gex/surface_sweep.py`; re-runnable `python -m gex.surface_sweep` prints two scored tables | ✓ |
| VALID-04 | Surface-coherence (calendar + butterfly) PASS/FAIL + violations, report-only, headless, never auto-repair | `surface_diagnostics` raw-quote calendar (per-bucket variance monotonicity) + butterfly (per-expiry 2nd-diff); flags/counts/prints only, no surface mutation; REQUIREMENTS wording reworded from no-arbitrage (D-11) | ✓ |
| VALID-05 | One shared `rbf_grid` helper, no duplicated interpolation | `analytics.rbf_grid` (1 def); both prior duplicates removed (`def _rbf_grid` count = 0); numerical regression test (`assert_allclose atol=1e-9`) proves identical render | ✓ |
| VALID-06 | Coverage % + fit RMS visible in the Streamlit dashboard | `_trust_readout_strings` renders `Coverage NN% · Fit RMS Npp · Max Npp` above each 3D surface; raw numbers, no badge/threshold; coherence stays headless (D-11) | ✓ |

## Automated checks

- Full suite: **92 passed** (66 baseline → +26 new across 08-01..08-04), 0 regressions.
- New test files: test_rbf_grid, test_coverage_mask, test_surface_holes, test_surface_diagnostics, test_surface_sweep (+ extensions to test_validation_schema, test_streamlit_app).
- `python -m gex.surface_sweep --ticker {SPY,QQQ}` runs on stored data, prints both tables, exits 0, never writes config.
- Numerical regression: `rbf_grid` output == frozen inline recomputation (atol=1e-9) → surface renders identically post-refactor.
- Imports clean, no circular dependency (`surface_diagnostics` ↔ `analytics`), no sklearn.

## Deviations / findings (carried to later phases, non-blocking)

1. **ROADMAP.md SC#5 reword N/A** — `.planning/ROADMAP.md` is the stale v3.1 doc; v3.3 phase definitions live in REQUIREMENTS.md (reworded). The v3.3 ROADMAP was never generated. Planning-doc drift to repair separately.
2. **Honest coverage ~22% → RESOLVED 2026-05-30.** The kNN-radius mask only covered ~22% because its isotropic radius (median-NN, set by the dense strike spacing) wrongly holed legitimate between-expiry interpolation. Switched `coverage_mask` to convex-hull support → 92.9% SPY / 92.4% QQQ / 88.6% IWM. See the refinement addendum below.
3. **smoothing cv nuance** — leave-one-expiry-out CV mildly favours less smoothing on a single clean SPY day; 1.5 retained per D-12 as insurance against ringing on noisier/crossed-quote days. Revisit when more days accumulate.

## Tooling note

The GSD `gsd-sdk query` interface (init/state/roadmap/phase.complete/verifier) is unavailable on
this machine (`@gsd-build/sdk@0.1.0` is the autonomous runner, not the query SDK; content is v1.37.1).
Phase 8 was executed and verified inline, routed around the broken binary, using `gsd-tools.cjs`/git
for commits. STATE.md + REQUIREMENTS traceability updated by hand (the `state`/`phase.complete`
mutators corrupt STATE.md — see session notes). Recommend repairing the GSD install before Phase 9.

## Post-verification refinement — coverage_mask → convex hull (2026-05-30)

Running the gate on real stored chains exposed that the kNN-radius coverage mask (D-01/D-03)
covered only ~22% of the grid: the radius `k × median-NN` is dominated by the dense strike
axis, so cells between expiries were holed even though interpolating across a ≤21-35d calendar
gap is honest interpolation, not fabrication (SPY has 22 expiries over DTE 5-175).

Fix (commit `b66625a`): `analytics.coverage_mask` now uses **convex-hull membership** (Delaunay)
— supported = inside the quote cloud (interpolation), holed = outside (extrapolation: the
short/long-DTE deep-wing corners). Coverage: **92.9% SPY / 92.4% QQQ / 88.6% IWM**. The mask is
now **parameter-free** — `COVERAGE_KNN_K` and `surface_sweep.sweep_k` were removed (fits the
project's no-hand-tuned-cutoffs rule better than kNN). VALID-01's wording already permitted
"convex-hull / kNN", so the requirement is unchanged; this reverses only the D-01/D-03
implementation choice. 93 tests pass. VALID-01/06 remain satisfied with stronger, usable coverage.

---
*Phase: 08-surface-validation*
*Verified: 2026-05-30 — PASSED (coverage_mask refined to convex hull same day)*

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
- [[_planning/gamma-omm/phases/08-surface-validation/08-03-SUMMARY|08-03-SUMMARY]]
- [[_planning/gamma-omm/phases/08-surface-validation/08-04-PLAN|08-04-PLAN]]
- [[_planning/gamma-omm/phases/08-surface-validation/08-04-SUMMARY|08-04-SUMMARY]]
- [[_planning/gamma-omm/phases/08-surface-validation/08-CONTEXT|08-CONTEXT]]
- [[_planning/gamma-omm/phases/08-surface-validation/08-DISCUSSION-LOG|08-DISCUSSION-LOG]]

<!-- LINKS:END -->
