---
phase: 02-regime-model
plan: 01
subsystem: regime-model
tags: [hmm, gaussian-hmm, viterbi, regime-decoded, regime-labels, risk-on, risk-off, composite-labeling]
dependency-graph:
  requires:
    - bench_aligned (Phase 1, cell 4)
    - compute_summary_stats (Phase 1, cell 6)
  provides:
    - model (fitted GaussianHMM)
    - regime_decoded (pd.Series, integer states, DatetimeIndex)
    - regime_labels (pd.Series, 'Risk-On'/'Risk-Off', DatetimeIndex)
  affects:
    - Phase 3 (fund behavior by regime)
    - Phase 4 (regime stability and transitions)
tech-stack:
  added:
    - hmmlearn.hmm.GaussianHMM
  patterns:
    - Viterbi decode via model.predict(X)
    - Majority-vote composite labeling (3 signals)
key-files:
  created: []
  modified:
    - hmm.ipynb
decisions:
  - "D-01: Composite majority vote (score_0 >= 2 of 3 signals) determines Risk-On/Risk-Off assignment — avoids arbitrary single-signal labeling"
  - "D-02: Stats table printed per state with signal winners identified for audit trail"
metrics:
  tasks_completed: 2
  tasks_total: 2
  completed_date: 2026-04-22
---

# Phase 2 Plan 1: HMM Fit and Regime Labeling Summary

## What Was Built

2-state GaussianHMM fit on benchmark returns with Viterbi decode and composite majority-vote regime labeling. Three cells added to hmm.ipynb (cells 8, 9, 10).

**Cell 8 — Section 2 markdown header:** Introduces the regime model section with a description of the HMM approach and Viterbi decoding.

**Cell 9 — HMM Fit and Viterbi Decode (Section 2.1):**
- Input validation: assert no NaN in bench_aligned, assert len > 100
- Reshapes bench_aligned to (n, 1) for hmmlearn
- Fits `GaussianHMM(n_components=2, covariance_type='diag', n_iter=100, tol=1e-4, random_state=0)`
- Prints convergence status and log-likelihood; warns if EM did not converge
- Prints transition matrix, per-state means, per-state volatility
- Viterbi decodes via `model.predict(X)`
- Produces `regime_decoded`: pd.Series with DatetimeIndex, values 0/1, name='regime_state'

**Cell 10 — Regime Statistics and Labeling (Section 2.2):**
- Splits bench_aligned by state, reuses `compute_summary_stats()` from Phase 1
- `label_states_by_composite()`: majority vote across annual return, annual vol, Sharpe ratio — state winning >= 2 of 3 signals = Risk-On
- Prints formatted stats table per state with signal winner identification
- Produces `regime_labels`: pd.Series with DatetimeIndex, values 'Risk-On'/'Risk-Off', name='regime_label'

## Variables Produced

| Variable | Type | Description |
|----------|------|-------------|
| model | GaussianHMM | Fitted 2-state HMM |
| X | np.ndarray | bench_aligned reshaped to (n, 1) |
| state_sequence | np.ndarray | Integer state per observation from Viterbi |
| regime_decoded | pd.Series | DatetimeIndex, int states 0/1, name='regime_state' |
| stats_0, stats_1 | dict | Annualized stats per state from compute_summary_stats |
| label_0, label_1 | str | 'Risk-On' or 'Risk-Off' per state |
| score_0 | int | Composite score 0-3 for state 0 |
| regime_labels | pd.Series | DatetimeIndex, 'Risk-On'/'Risk-Off', name='regime_label' |

## Commits

No git repository — cells written directly to hmm.ipynb.

## Deviations

None — executed exactly per plan spec.

## Self-Check: PASSED

- [x] Notebook has exactly 10 cells
- [x] Cell 8 is markdown, contains "## 2. Regime Model"
- [x] Cell 9 contains GaussianHMM(n_components=2, covariance_type='diag', n_iter=100, tol=1e-4, random_state=0)
- [x] Cell 9 contains X = bench_aligned.values.reshape(-1, 1)
- [x] Cell 9 contains model.predict(X)
- [x] Cell 9 contains regime_decoded = pd.Series(state_sequence, index=bench_aligned.index)
- [x] Cell 9 contains regime_decoded.name = 'regime_state'
- [x] Cell 9 contains model.monitor_.converged
- [x] Cell 9 contains assert statements for NaN and length
- [x] Cell 10 contains compute_summary_stats(state_0_returns, risk_free_rate=0.02)
- [x] Cell 10 contains compute_summary_stats(state_1_returns, risk_free_rate=0.02)
- [x] Cell 10 contains label_states_by_composite
- [x] Cell 10 contains score_0 >= 2
- [x] Cell 10 contains label_0 = 'Risk-On' if score_0 >= 2 else 'Risk-Off'
- [x] Cell 10 contains label_1 = 'Risk-Off' if score_0 >= 2 else 'Risk-On'
- [x] Cell 10 contains regime_labels = regime_decoded.map({0: label_0, 1: label_1})
- [x] Cell 10 contains regime_labels.name = 'regime_label'
- [x] Cell 10 contains "=== REGIME STATISTICS ===" in a print statement

## PLAN COMPLETE
