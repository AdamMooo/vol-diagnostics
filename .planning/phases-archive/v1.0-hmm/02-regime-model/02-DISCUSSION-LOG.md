# Phase 2: Regime Model - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-22
**Phase:** 02-regime-model
**Areas discussed:** Regime labeling, Posterior prob chart, Seed stability output, Stability doc format

---

## Regime Labeling

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-label by mean return | Lower mean = Risk-Off, higher = Risk-On. Fully automatic. | |
| User assigns after reviewing stats | Code shows stats table, user fills REGIME_LABELS dict manually. | |
| Auto-label by volatility | Lower vol = Risk-On, higher = Risk-Off. | |
| Composite rank (Other) | Score each state on mean return, vol, and Sharpe — majority vote across 3 signals. | ✓ |

**User's choice:** Composite rank — ensemble of return, vol, and Sharpe (majority vote). Applied automatically in code.
**Notes:** User felt single-signal labeling was insufficient: "regimes are not all based on return or vol." Composite signal better captures the risk/reward character of each state.

---

## Posterior Probability Chart

| Option | Description | Selected |
|--------|-------------|----------|
| Single line — P(Risk-On) only | One line, 0.5 threshold dashed. Clean. | ✓ |
| Stacked area — both states | Two bands summing to 1.0 at all times. | |
| Two separate lines | P(Risk-On) and P(Risk-Off) as separate lines. Redundant for 2 states. | |

**User's choice:** Single line — P(Risk-On) with 0.5 threshold.
**Notes:** None.

---

## Seed Stability Output

| Option | Description | Selected |
|--------|-------------|----------|
| Agreement fraction — printed | 10 seeds, compare each to baseline, print agreement fraction. | ✓ |
| Adjusted Rand Index | More rigorous, less interpretable to non-quants. | |
| Visual overlay — 10 sequences | Plot all 10 decoded sequences on one chart. | |

**User's choice:** Agreement fraction, printed output.
**Notes:** None.

---

## Stability Doc Format

| Option | Description | Selected |
|--------|-------------|----------|
| Printed table in code cell output | Mean/median duration per state in days and weeks. | ✓ |
| Markdown cell with hardcoded stats | Manual copy step after running computation. | |
| Duration distribution chart | Histogram of spell lengths per state. | |

**User's choice:** Printed table in code cell output.
**Notes:** None.

---

## Claude's Discretion

- n_iter and tol convergence settings for GaussianHMM
- covariance_type (diag appropriate for 1D input)
- Color for posterior probability line
- Whether posterior chart is its own cell or combined with regime state visualization

## Deferred Ideas

None.
