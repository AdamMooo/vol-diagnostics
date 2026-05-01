---
phase: 02-regime-model
plan: 03
subsystem: regime-model
tags: [hmm, posterior-probability, predict-proba, regime-posteriors, p-risk-on, forward-backward, visualization]

requires:
  - phase: 02-01
    provides: model (GaussianHMM), X (np.ndarray), label_0, bench_aligned, regime_labels, COLOR_BENCH
  - phase: 02-02
    provides: spells_df, seed stability confirmation
provides:
  - regime_posteriors (pd.Series, DatetimeIndex, float64 [0,1], name='p_risk_on')
  - P(Risk-On) chart: single line with dashed 0.5 decision boundary in COLOR_BENCH
  - Phase 2 output summary cell with 4 integrity assertions
affects:
  - Phase 5 (visualization — regime_posteriors is the canonical posterior input)
  - Phase 3 (fund behavior by regime — output contract confirmed in cell 15)
  - Phase 4 (regime stability and transitions — output contract confirmed in cell 15)

tech-stack:
  added: []
  patterns:
    - "predict_proba vs predict: forward-backward posteriors (smooth) vs Viterbi (hard assignment)"
    - "risk_on_state_idx: 0 if label_0 == 'Risk-On' else 1 — state-index lookup pattern"
    - "Output summary cell with assert statements as cross-phase contract documentation"

key-files:
  created: []
  modified:
    - hmm.ipynb

key-decisions:
  - "D-03: Single P(Risk-On) line chart using COLOR_BENCH, figsize=(12,4), dashed gray axhline at 0.5 — not stacked area, not two lines"

patterns-established:
  - "Output contract cell: print metadata + assert integrity before declaring phase complete — reuse for Phase 3, 4"
  - "Posterior extraction: model.predict_proba(X)[:, risk_on_state_idx] with bench_aligned.index — reuse for any 2-state HMM"

requirements-completed: [REGM-03]

duration: ~5min
completed: 2026-04-22
---

# Phase 2 Plan 3: Posterior Probability Extraction and Phase 2 Output Summary

**Posterior probabilities extracted via forward-backward (predict_proba), P(Risk-On) plotted as single orange line with 0.5 decision boundary, Phase 2 output contract declared and asserted in cell 15.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-22
- **Completed:** 2026-04-22
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Cell 13: `model.predict_proba(X)` extracts smooth posterior probabilities; `risk_on_state_idx` determined from `label_0`; `regime_posteriors` created as pd.Series with bench_aligned.index and name='p_risk_on'
- Cell 14: P(Risk-On) chart using `plt.subplots(figsize=(12, 4))`, single line in `COLOR_BENCH`, dashed gray `axhline` at y=0.5, y-axis [0,1] formatted as percentages (Decision D-03)
- Cell 15: Phase 2 output summary prints metadata for both `regime_labels` and `regime_posteriors`, runs 4 assert statements validating label values, NaN absence, [0,1] bounds, and shared index — declares both variables ready for downstream phases

## Task Commits

No git repository — cells written directly to hmm.ipynb.

## Files Created/Modified

- `hmm.ipynb` — Added cells 13 (posterior extraction), 14 (P(Risk-On) chart), 15 (Phase 2 output summary); notebook now has 15 cells total

## Decisions Made

- D-03: P(Risk-On) chart uses single line (not stacked area, not two lines) with COLOR_BENCH orange, figsize=(12,4), dashed 0.5 boundary — matches plan spec locked before execution

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- REGM-03 satisfied: `regime_posteriors` produced via `model.predict_proba(X)`, P(Risk-On) chart with 0.5 boundary complete
- All 8 Phase 2 cells inserted (cells 8-15); Phase 2 is complete
- `regime_labels` and `regime_posteriors` both validated with assertions in cell 15 — ready for Phase 3 and Phase 4
- Phase 3 (Fund Analysis) and Phase 4 (Regime Stability & Transitions) can proceed

## Self-Check

- [x] hmm.ipynb has exactly 15 cells
- [x] Cell 13 contains "model.predict_proba(X)"
- [x] Cell 13 contains "risk_on_state_idx = 0 if label_0 == 'Risk-On' else 1"
- [x] Cell 13 contains "pd.Series(posteriors[:, risk_on_state_idx], index=bench_aligned.index)"
- [x] Cell 13 contains "regime_posteriors.name = 'p_risk_on'"
- [x] Cell 14 contains "plt.subplots(figsize=(12, 4))"
- [x] Cell 14 contains "ax.plot(regime_posteriors.index, regime_posteriors.values"
- [x] Cell 14 contains "color=COLOR_BENCH"
- [x] Cell 14 contains "ax.axhline(y=0.5"
- [x] Cell 14 contains "linestyle='--'"
- [x] Cell 14 contains "ax.set_ylim(0, 1)"
- [x] Cell 15 contains "=== PHASE 2 OUTPUTS ==="
- [x] Cell 15 contains "assert set(regime_labels.unique()) == {'Risk-On', 'Risk-Off'}"
- [x] Cell 15 contains "assert regime_posteriors.isnull().sum() == 0"
- [x] Cell 15 contains "assert (regime_posteriors >= 0).all() and (regime_posteriors <= 1).all()"
- [x] Cell 15 contains "assert regime_labels.index.equals(regime_posteriors.index)"
- [x] Cell 15 contains "Phase 2 complete"

## Self-Check: PASSED

---
*Phase: 02-regime-model*
*Completed: 2026-04-22*
