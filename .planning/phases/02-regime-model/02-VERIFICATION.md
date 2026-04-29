---
phase: 02-regime-model
verified: 2026-04-22T00:00:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run notebook cells 8-15 top-to-bottom in server shell_plus and confirm printed output"
    expected: "Converged: True (or WARNING if not); regime statistics table shows two distinct states; regime_labels distribution shows both 'Risk-On' and 'Risk-Off'; duration analysis shows mean >= 7 days for both states (PASS); seed stability shows >= 8/9 seeds at >= 90% (STABLE); P(Risk-On) chart renders as single orange line with dashed 0.5 boundary; Phase 2 output summary prints without assertion errors"
    why_human: "Notebook runs server-side in Django shell_plus with live DB/Bloomberg connections — no local execution possible. Convergence, actual regime label assignment, duration values, seed agreement fractions, and assertion outcomes depend on real data that cannot be checked statically."
---

# Phase 2: Regime Model Verification Report

**Phase Goal:** A validated, labeled 2-state HMM is fit on benchmark returns and its regime assignments are ready for downstream use
**Verified:** 2026-04-22
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | The HMM fits and converges; regime state series is stored as a date-indexed labeled series | VERIFIED | Cell 9: `GaussianHMM(n_components=2, covariance_type='diag', n_iter=100, tol=1e-4, random_state=0)`, `model.fit(X)`, `model.monitor_.converged` check printed; `regime_decoded = pd.Series(state_sequence, index=bench_aligned.index)` with `name='regime_state'` |
| 2 | Regime posterior probabilities are plotted over the full history | VERIFIED | Cell 13: `model.predict_proba(X)`, `regime_posteriors = pd.Series(posteriors[:, risk_on_state_idx], index=bench_aligned.index)`, `regime_posteriors.name = 'p_risk_on'`; Cell 14: `plt.subplots(figsize=(12, 4))`, single line `ax.plot(regime_posteriors.index, regime_posteriors.values, ..., color=COLOR_BENCH)`, `ax.axhline(y=0.5, ..., linestyle='--')` |
| 3 | Average regime duration is documented as weeks-to-months (not days), confirming the model isn't noise-following | VERIFIED | Cell 11: `=== REGIME DURATION ANALYSIS ===`, spell detection via `regime_change.cumsum()`, mean/median per state in days and weeks (`mean_days / 7`, `median_days / 7`), `Temporal Stability (mean >= 7 days per regime): PASS/WARN` verdict |
| 4 | Re-fitting with 10 random seeds produces consistent regime assignments (stability documented in notebook) | VERIFIED | Cell 12: baseline is seed-0 model (cell 9); `for seed in range(1, 10):` runs 9 comparison refits (seeds 0-9 = 10 total); `max(agreement_direct, agreement_swap)` handles label swaps; `=== SEED STABILITY CHECK ===` printed; `stable_seeds >= 8` verdict as STABLE/UNSTABLE |
| 5 | Regimes carry human-readable labels grounded in conditional statistics | VERIFIED | Cell 10: `compute_summary_stats()` called for both states; `label_states_by_composite()` applies majority vote (return, vol, Sharpe); `regime_labels = regime_decoded.map({0: label_0, 1: label_1})`, `regime_labels.name = 'regime_label'`; values 'Risk-On'/'Risk-Off' |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `hmm.ipynb` (cell 8) | Section 2 markdown header | VERIFIED | Markdown cell: `## 2. Regime Model` with description of HMM/Viterbi approach |
| `hmm.ipynb` (cell 9) | HMM fit + Viterbi decode | VERIFIED | `GaussianHMM(n_components=2, covariance_type='diag', n_iter=100, tol=1e-4, random_state=0)`, input validation asserts, `model.fit(X)`, `model.predict(X)`, `regime_decoded` as named DatetimeIndex Series |
| `hmm.ipynb` (cell 10) | Regime statistics + composite labeling | VERIFIED | `compute_summary_stats()` for state_0 and state_1, `label_states_by_composite()` with majority vote, `=== REGIME STATISTICS ===` table, `regime_labels` defined with `name='regime_label'` |
| `hmm.ipynb` (cell 11) | Regime duration validation | VERIFIED | `spell_id = regime_change.cumsum()`, `spells_df`, mean/median in days and weeks, PASS/WARN temporal stability verdict |
| `hmm.ipynb` (cell 12) | Seed stability check | VERIFIED | 9-refit loop seeds 1-9, label-swap-aware `max(agreement_direct, agreement_swap)`, `stable_seeds >= 8` threshold, STABLE/UNSTABLE output |
| `hmm.ipynb` (cell 13) | Posterior extraction | VERIFIED | `model.predict_proba(X)`, `risk_on_state_idx = 0 if label_0 == 'Risk-On' else 1`, `regime_posteriors` as pd.Series with `name='p_risk_on'` |
| `hmm.ipynb` (cell 14) | P(Risk-On) chart | VERIFIED | `plt.subplots(figsize=(12, 4))`, single line in `COLOR_BENCH`, `ax.axhline(y=0.5, ..., linestyle='--')`, `ax.set_ylim(0, 1)` |
| `hmm.ipynb` (cell 15) | Phase 2 output summary | VERIFIED | `=== PHASE 2 OUTPUTS ===`, metadata for both variables, four assert statements validating label values, NaN absence, [0,1] bounds, shared index |

**Notebook cell count:** 15 cells confirmed (cells 1-7 from Phase 1, cells 8-15 from Phase 2)

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `bench_aligned` (cell 4) | `model.fit(X)` | `X = bench_aligned.values.reshape(-1, 1)` | WIRED | Cell 9 line confirmed in notebook |
| `regime_decoded` | `regime_labels` | `regime_decoded.map({0: label_0, 1: label_1})` | WIRED | Cell 10: mapping confirmed; `regime_labels.name = 'regime_label'` |
| `regime_labels` (cell 10) | spell detection | `(regime_labels.astype(str) != regime_labels.astype(str).shift(1)).cumsum()` | WIRED | Cell 11 confirmed |
| `model` (cell 9) | seed stability loop | `GaussianHMM(..., random_state=seed)` for seed in range(1,10) | WIRED | Cell 12 confirmed |
| `model.predict_proba(X)` | `regime_posteriors` | `posteriors[:, risk_on_state_idx]` as pd.Series with `bench_aligned.index` | WIRED | Cell 13: `risk_on_state_idx = 0 if label_0 == 'Risk-On' else 1` confirmed |
| `label_0` (cell 10) | `risk_on_state_idx` | `0 if label_0 == 'Risk-On' else 1` | WIRED | Cell 13 confirmed |

### Data-Flow Trace (Level 4)

This phase has no external data fetch — all computation flows from `bench_aligned` (Phase 1 output) through the HMM fit to produce `regime_labels` and `regime_posteriors`. Level 4 trace reduces to: does `bench_aligned` flow into `model.fit(X)` and through to `regime_posteriors`? Confirmed yes via the key link chain above. No static/empty data sources found.

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| Cell 9 | `regime_decoded` | `bench_aligned.values.reshape(-1, 1)` fed to `model.predict(X)` | Yes — Viterbi decode of fitted HMM | FLOWING |
| Cell 10 | `regime_labels` | `regime_decoded.map(...)` after composite labeling | Yes — mapped from real decoded states | FLOWING |
| Cell 14 | P(Risk-On) chart | `regime_posteriors` from `model.predict_proba(X)` | Yes — forward-backward posteriors | FLOWING |

### Behavioral Spot-Checks

SKIPPED — notebook runs server-side in Django shell_plus with live DB and Bloomberg connections. No local execution path exists. All behavioral verification routes to human testing.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| REGM-01 | 02-01 | 2-state Gaussian HMM fit on benchmark returns using hmmlearn | SATISFIED | Cell 9: `GaussianHMM(n_components=2, ...)`, `model.fit(X)` |
| REGM-02 | 02-01 | Regime state sequence decoded and stored as date-indexed labeled series | SATISFIED | Cell 9: `regime_decoded` pd.Series with DatetimeIndex; Cell 10: `regime_labels` pd.Series with 'Risk-On'/'Risk-Off' values |
| REGM-03 | 02-03 | Regime posterior probability series computed and plotted over time | SATISFIED | Cell 13: `model.predict_proba(X)`, `regime_posteriors`; Cell 14: single-line chart with 0.5 boundary |
| REGM-04 | 02-02 | Regime stability validated: average duration weeks-to-months; finding documented | SATISFIED | Cell 11: spell detection, mean/median per state in days+weeks, PASS/WARN verdict — actual values are data-dependent (human verification) |
| REGM-05 | 02-02 | Model seed stability checked: re-fit with 10 seeds, regimes consistent | SATISFIED | Cell 12: baseline seed 0 + seeds 1-9 = 10 total seeds; label-swap-aware comparison; STABLE/UNSTABLE verdict — actual agreement fractions are data-dependent (human verification) |
| REGM-06 | 02-01 | Regimes labeled with economic intuition after reviewing regime-conditional statistics | SATISFIED | Cell 10: composite majority vote on return/vol/Sharpe; labels are 'Risk-On'/'Risk-Off'; stats table printed for audit |

**Note on REGM-05 seed count:** REQUIREMENTS.md says "re-fit with 10 seeds"; the plan explicitly resolved this as seed 0 = baseline (the main model) + seeds 1-9 = 9 comparison refits = 10 total seeds used. The verdict line prints "X/9 seeds" (not "X/10") because the baseline is not being compared against itself. This framing matches the plan's explicit decision (D-04, D-05) and satisfies the spirit of REGM-05.

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `hmm.ipynb` cell 15 | `assert set(regime_labels.unique()) == {'Risk-On', 'Risk-Off'}` | Info | This is a correctness guard, not a stub. Will raise AssertionError at runtime if labeling fails — appropriate defensive code. |

No stubs, TODOs, hardcoded empty data, or placeholder patterns found in Phase 2 cells (8-15). All code is substantive and data flows from real computation.

### Human Verification Required

#### 1. End-to-End Notebook Run (Cells 8-15)

**Test:** In server shell_plus (after Phase 1 cells have run), execute cells 8 through 15 in order.

**Expected:**
- Cell 9: Prints "Converged: True" and a log-likelihood value; prints transition matrix, per-state means and volatilities; prints state 0/1 observation counts.
- Cell 10: Prints `=== REGIME STATISTICS ===` table with two distinct states showing materially different return/vol/Sharpe profiles; prints composite signal winners and label assignment; prints regime_labels distribution with both 'Risk-On' and 'Risk-Off' present.
- Cell 11: Prints `=== REGIME DURATION ANALYSIS ===` with mean and median for both states; the temporal stability line ends with `PASS` (confirming mean duration >= 7 days).
- Cell 12: Prints `=== SEED STABILITY CHECK ===` with per-seed agreement fractions; ends with `Status: STABLE` (confirming >= 8/9 seeds at >= 90% agreement).
- Cell 13: Prints `=== POSTERIOR PROBABILITY: P(Risk-On) ===` with non-trivial mean P(Risk-On) (not 0% or 100%); no NaN reported.
- Cell 14: Renders a chart showing a single orange line moving between 0% and 100% with a dashed gray horizontal line at 50%.
- Cell 15: Prints both variable summaries and completes with "Phase 2 complete. Both output variables validated." without any AssertionError.

**Why human:** Server-side execution environment (Django shell_plus + Bloomberg) cannot be replicated locally. Convergence, actual regime label assignment, duration magnitudes, seed agreement fractions, and all assertion outcomes depend on live data.

---

## Gaps Summary

No gaps. All 5 roadmap success criteria are verified at the code level. The single human verification item covers runtime behavior that cannot be confirmed statically — it is an execution check, not a missing implementation.

---

_Verified: 2026-04-22_
_Verifier: Claude (gsd-verifier)_
