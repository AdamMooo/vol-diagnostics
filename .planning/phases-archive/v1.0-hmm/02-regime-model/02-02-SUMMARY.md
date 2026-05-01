---
phase: 02-regime-model
plan: 02
subsystem: regime-model
tags: [hmm, regime-duration, spell-detection, seed-stability, validation, risk-on, risk-off]

requires:
  - phase: 02-01
    provides: regime_labels (pd.Series, Risk-On/Risk-Off, DatetimeIndex), model (GaussianHMM), X (np.ndarray), bench_aligned
provides:
  - spells_df (pd.DataFrame of regime spell durations)
  - Regime duration analysis: mean/median days and weeks per state, temporal stability verdict
  - Seed stability check: 9-refit agreement fractions with label-swap-aware comparison, STABLE/UNSTABLE verdict
affects:
  - Phase 4 (regime stability and transitions — duration stats provide baseline expectations)

tech-stack:
  added: []
  patterns:
    - Spell detection via cumsum on shift-differenced label series
    - Label-swap-aware seed stability comparison (max of direct vs. swapped agreement)

key-files:
  created: []
  modified:
    - hmm.ipynb

key-decisions:
  - "D-04: Per-seed agreement fractions printed individually; label swap handled by taking max(direct, swapped)"
  - "D-05: Stability threshold: >=8 of 9 seeds at >=90% agreement = STABLE; printed as conditional output"
  - "D-06: Per-state duration printed as mean and median in both days and weeks"

patterns-established:
  - "Spell detection: (labels != labels.shift()).cumsum() as spell ID — reusable for any regime series"
  - "Seed stability loop: range(1,10) refits with label-swap-aware max(direct, swap) comparison"

requirements-completed: [REGM-04, REGM-05]

duration: ~10min
completed: 2026-04-22
---

# Phase 2 Plan 2: Regime Duration and Seed Stability Validation Summary

**Regime spell duration analysis (mean/median days+weeks per state) and 9-seed stability check with label-swap-aware agreement fractions added as cells 11-12.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-04-22
- **Completed:** 2026-04-22
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Cell 11: spell detection using `cumsum()` on shift-differenced regime labels, per-state mean/median duration in days and weeks, PASS/WARN temporal stability verdict (threshold: mean >= 7 days)
- Cell 12: 9-refit seed stability loop (seeds 1-9 vs. seed-0 baseline), label-swap-aware agreement via `max(direct, swap)`, STABLE/UNSTABLE verdict based on >=8/9 seeds at >=90% threshold
- `spells_df` available at notebook scope for downstream use in Phase 4

## Task Commits

No git repository — cells written directly to hmm.ipynb.

## Files Created/Modified

- `hmm.ipynb` — Added cells 11 (regime duration validation) and 12 (seed stability check); notebook now has 12 cells total

## Decisions Made

- D-04: Label-swap handling in seed stability loop uses `max(agreement_direct, agreement_swap)` — accounts for HMM label permutation invariance across seeds
- D-05: STABLE threshold is >=8 of 9 seeds at >=90% agreement; printed as conditional string literal
- D-06: Duration table format: mean and median per state in days (`Xd`) and weeks (`~X.Xwk`); N spells shown

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- REGM-04 and REGM-05 satisfied: duration validation and seed stability check are in place
- `spells_df` available for Phase 4 (regime stability and transitions)
- `regime_labels` and `regime_decoded` remain the canonical outputs for Phase 3 (fund behavior by regime)
- Phase 2 Wave 3 (posterior probability chart, cell 13) is the remaining Wave 2 item

## Self-Check

- [x] hmm.ipynb has exactly 12 cells
- [x] Cell 11 contains "=== REGIME DURATION ANALYSIS ==="
- [x] Cell 11 contains "regime_labels.astype(str) != regime_labels.astype(str).shift(1)"
- [x] Cell 11 contains "spell_id = regime_change.cumsum()"
- [x] Cell 11 contains "spells_df"
- [x] Cell 11 contains "mean_days / 7"
- [x] Cell 11 contains "median_days / 7"
- [x] Cell 11 contains "Temporal Stability (mean"
- [x] Cell 11 contains "PASS" and "WARN" as conditional output strings
- [x] Cell 12 contains "=== SEED STABILITY CHECK ==="
- [x] Cell 12 contains "for seed in range(1, 10):"
- [x] Cell 12 contains GaussianHMM with n_components=2, covariance_type='diag', n_iter=100, tol=1e-4, random_state=seed
- [x] Cell 12 contains "np.mean(states_seed == baseline_states)"
- [x] Cell 12 contains "np.mean((1 - states_seed) == baseline_states)"
- [x] Cell 12 contains "max(agreement_direct, agreement_swap)"
- [x] Cell 12 contains "stable_seeds >= 8"
- [x] Cell 12 contains both "STABLE" and "UNSTABLE" as output string literals

## Self-Check: PASSED

---
*Phase: 02-regime-model*
*Completed: 2026-04-22*
