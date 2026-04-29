# Phase 2: Regime Model - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Fit a 2-state Gaussian HMM on the benchmark log return series (`bench_aligned`) from Phase 1, decode the regime state sequence, validate that regimes are temporally stable (weeks-to-months average duration, not days), confirm seed stability across 10 random initializations, and assign human-readable labels (Risk-On / Risk-Off) using a composite signal. Output is a date-indexed labeled regime series and a posterior probability series, both ready for Phase 3 (fund analysis) and Phase 4 (stability/transitions).

</domain>

<decisions>
## Implementation Decisions

### Regime labeling
- **D-01:** Auto-label by composite rank: code scores each state on three signals — mean return (higher = Risk-On), annualized vol (lower = Risk-On), and Sharpe ratio (higher = Risk-On). The state that wins on the majority of the three signals (2 or 3 out of 3) is labeled Risk-On; the other is labeled Risk-Off. Labels are applied programmatically in the fit cell — no manual user step.
- **D-02:** A composite stats display (mean return, vol, Sharpe per state, with the winning signal highlighted) is produced alongside the labeling logic so the user can audit the assignment.

### Posterior probability chart
- **D-03:** Single line showing P(Risk-On state) over the full date range. A dashed horizontal line at 0.5 marks the decision boundary. Color: use the Risk-On regime color from the Phase 1 palette. This is one chart — not stacked area, not two lines.

### Seed stability check
- **D-04:** Refit with 10 random seeds (random_state 0–9). For each seed, compute the agreement fraction between its decoded state sequence and the baseline (seed 0) — accounting for label swaps (compare both alignments, take the better of the two). Print a summary: e.g. "Seed stability: 9/10 seeds ≥90% agreement with baseline. Model is stable." No visual chart — printed output only.
- **D-05:** Stability threshold: ≥90% agreement on ≥8 of 10 seeds = stable; otherwise flag a warning.

### Stability duration documentation
- **D-06:** After computing individual regime spells from the decoded sequence, print a table: mean and median duration per state in calendar days and approximate weeks. E.g. "Risk-On: mean 47d (~7wk), median 31d. Risk-Off: mean 28d (~4wk), median 18d." This documents REGM-04 directly in code cell output — no markdown hardcoding required.

### Claude's Discretion
- n_iter and tol convergence settings for GaussianHMM
- covariance_type (diag is appropriate for 1D input)
- Specific color to use for the posterior probability line (Phase 1 palette constants are defined in Setup cell)
- Whether the posterior probability chart is its own cell or combined with the regime state sequence visualization

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 1 output variables
- `.planning/phases/01-data-layer/01-CONTEXT.md` — Defines `bench_aligned` (date-indexed daily log return Series, inner join aligned) as the HMM input. D-06 through D-08 establish return computation and alignment decisions.
- `.planning/phases/01-data-layer/01-RESEARCH.md` — hmmlearn version, stack, and code patterns. Confirms GaussianHMM from hmmlearn.hmm.

### Project constraints
- `CLAUDE.md` (project root) — Notebook-only constraint, max 3 HMM states, no forecasting claims, Windows paths
- `.planning/REQUIREMENTS.md` — REGM-01 through REGM-06 are the acceptance criteria for this phase

No external ADRs or design specs — requirements fully captured in decisions above and REQUIREMENTS.md.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `hmm.ipynb` Setup cell: defines `COLOR_FUND`, `COLOR_BENCH`, `COLOR_DD` palette constants — the posterior probability chart should draw from these rather than hardcoding colors.
- `hmm.ipynb` Phase 1 cells: `bench_aligned` is the output variable name — Plan 02-01 should reference it directly.

### Established Patterns
- Cell structure from Phase 1: short focused cells with a markdown header cell (e.g. `## 2. Regime Model`) before each section.
- Server-side execution: all cells run in shell_plus context — no local file I/O, no explicit connection setup.
- `figsize=(12, 4)` established as the standard figure size in Phase 1.

### Integration Points
- Phase 2 outputs two variables consumed by downstream phases:
  - `regime_labels` — date-indexed pandas Series with string labels ('Risk-On' / 'Risk-Off') — consumed by Phase 3 and Phase 4
  - `regime_posteriors` — date-indexed DataFrame with columns per state (or a single P(Risk-On) Series) — consumed by Phase 5 visualization

</code_context>

<specifics>
## Specific Ideas

- Composite labeling signal: mean return + vol + Sharpe (majority vote across 3). This was preferred over single-signal labeling because regimes are not purely return-driven or vol-driven — the composite better captures the risk/reward character of each state.
- Seed stability check is printed output only — no chart. The printout format: "Seed stability: X/10 seeds ≥90% agreement with baseline. Model is stable/UNSTABLE."

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-regime-model*
*Context gathered: 2026-04-22*
