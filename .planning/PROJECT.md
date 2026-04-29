# TQ HMM — Regime-Aware Fund Intelligence Notebook

## What This Is

A Jupyter research notebook that fits a Hidden Markov Model on benchmark returns to identify latent market regimes, then characterizes how a fund's risk, return, drawdown, and behavior shift across those regimes. Output is structured investment research — presentable to a PM or investment committee without a quant lecture. Built entirely on internal company data.

## Core Value

Given fund NAV and benchmark return data, answer: "what regime are we in, how stable is it, and how does our fund actually behave in each regime?"

## Requirements

### Validated

(None yet — ship to validate)

### Active

**Data Layer**
- [ ] Internal DB connection established and documented in notebook Setup cell
- [ ] Fund return series loaded, cleaned, and aligned with benchmark
- [ ] Benchmark return series loaded at same frequency
- [ ] EDA section with summary stats, cumulative return chart, rolling vol, drawdown chart

**Regime Model**
- [ ] 2-state Gaussian HMM fit on benchmark returns (hmmlearn)
- [ ] Regime state sequence decoded and stored as a labeled series
- [ ] Regime posterior probability series plotted over time
- [ ] Regime stability validated: average duration weeks-to-months, not days
- [ ] Regimes labeled with economic intuition (e.g. Risk-On / Risk-Off) after reviewing statistics

**Fund Analysis**
- [ ] Regime-conditional statistics: return, vol, Sharpe, max drawdown per state
- [ ] Alpha and beta by regime (OLS split by regime assignment)
- [ ] Summary statistics table — the core deliverable

**Regime Stability & Transitions**
- [ ] Transition probability matrix computed and displayed as heatmap
- [ ] Expected regime duration computed from transition matrix
- [ ] Current regime posterior probability as of latest date

**Visualization**
- [ ] Cumulative return chart with regime shading (background color by state)
- [ ] Return distribution histogram split by regime
- [ ] All time-series charts use consistent regime color palette
- [ ] Charts are presentation-quality (clean axes, labeled, no chart junk)

**Summary**
- [ ] Summary section with 3–5 bullet plain-English findings
- [ ] Regime-conditional stats table formatted for finance audience
- [ ] Caveats section: in-sample labels, no forecasting, sample sizes noted

### Out of Scope

- External market data (VIX, rates, Bloomberg) — adds dependency without clear upside over benchmark-only model
- More than 3 HMM states — kills interpretability; 2-state is the design target
- Predictive/forecasting claims — model is descriptive, not predictive
- CLI entry points or deployment — this is a research notebook, not a production system
- Phase 4 Attribution (sector/factor) — conditional on holdings data availability; deferred to v2 unless data confirmed

## Context

Internal company database is the primary data source — fund NAV/prices and benchmark returns are available. Holdings/weights data may or may not be available; Phase 4 (attribution) is explicitly optional and gated on data availability. The audience includes PMs and investment committee members who are finance-literate but not quant-literate — all outputs must have plain-English labels and explanations alongside the math. The existing `hmm.ipynb` is a blank slate.

## Constraints

- **Format**: Jupyter Notebook only — all analysis in `hmm.ipynb`
- **Interpretability**: Max 3 HMM states; model must be explainable to a non-quant
- **Model fitting**: Regime model fit on benchmark returns only (not fund returns — avoids circularity)
- **Data source**: Internal DB preferred; no external data dependencies unless they add clear, demonstrated value
- **Claims**: Descriptive/diagnostic only — no forecasting or predictive language
- **No git**: Local-only project, no version control
- **Platform**: Windows; use pathlib or os.path.join for any file paths

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 2-state Gaussian HMM on benchmark returns | Interpretable, explainable, aligns with finance intuition; easy to label | — Pending |
| Fit regime on benchmark, not fund | Avoids circularity — regime reflects market conditions, fund behavior analyzed conditionally | — Pending |
| Internal data only at MVP | Avoids external dependencies; Bloomberg/macro adds complexity without clear upside at this scope | — Pending |
| Attribution phase deferred (v2) | Contingent on holdings data being available and clean; don't gate core analysis on uncertain data | — Pending |
| hmmlearn as HMM library | Well-maintained, sklearn-compatible API, Gaussian HMM in ~15 lines, not a black box | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition:**
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone:**
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-22 after initialization*
