# Requirements: TQ HMM

**Defined:** 2026-04-22
**Core Value:** Given fund NAV and benchmark return data, answer: "what regime are we in, how stable is it, and how does our fund actually behave in each regime?"

## v1 Requirements

### Data

- [ ] **DATA-01**: Internal DB connection established and documented in notebook Setup cell
- [ ] **DATA-02**: Fund return series (or NAV) loaded, cleaned, and validated (no gaps, correct frequency)
- [ ] **DATA-03**: Benchmark return series loaded at same frequency as fund
- [ ] **DATA-04**: Returns aligned on a common date index with missing data handled explicitly
- [ ] **DATA-05**: EDA outputs: summary statistics table, cumulative return chart, rolling 21-day vol chart, drawdown chart

### Regime Model

- [ ] **REGM-01**: 2-state Gaussian HMM fit on benchmark returns using hmmlearn
- [ ] **REGM-02**: Regime state sequence decoded and stored as a date-indexed labeled series
- [ ] **REGM-03**: Regime posterior probability series computed and plotted over time
- [ ] **REGM-04**: Regime stability validated: average duration is weeks-to-months (not days); document finding
- [ ] **REGM-05**: Model seed stability checked: re-fit with 10 seeds, confirm regimes are consistent
- [ ] **REGM-06**: Regimes labeled with economic intuition (e.g. Risk-On / Risk-Off) after reviewing regime-conditional statistics

### Fund Analysis

- [ ] **FUND-01**: Regime-conditional statistics computed: mean return, vol, Sharpe ratio, max drawdown per state
- [ ] **FUND-02**: Alpha and beta by regime via OLS (split sample by regime assignment)
- [ ] **FUND-03**: Sample size (n) and date range documented for each regime-split statistic
- [ ] **FUND-04**: Summary statistics table formatted for finance audience (the core deliverable)

### Regime Stability

- [ ] **STAB-01**: Transition probability matrix computed and displayed as labeled heatmap
- [ ] **STAB-02**: Expected regime duration computed from transition matrix diagonal
- [ ] **STAB-03**: Current regime: posterior probability as of latest date, days in current regime

### Visualization

- [ ] **VIZ-01**: Cumulative return chart with regime shading (background band by state)
- [ ] **VIZ-02**: Return distribution histogram split by regime (overlapping, labeled)
- [ ] **VIZ-03**: Consistent regime color palette applied across all time-series charts
- [ ] **VIZ-04**: All charts are presentation-quality: clean axes, titles, labels, no chart junk

### Summary & Output

- [ ] **SUMM-01**: Summary section with 3–5 plain-English bullet findings
- [ ] **SUMM-02**: Caveats section: in-sample labels, no forecasting, sample size warnings where relevant
- [ ] **SUMM-03**: Notebook runs top-to-bottom without errors on a fresh kernel

## v2 Requirements

### Attribution (contingent on holdings data)

- **ATTR-01**: Portfolio weights by sector loaded and aligned to regime time series
- **ATTR-02**: Sector weight comparison table by regime (active vs benchmark)
- **ATTR-03**: Attribution waterfall by regime: sector contribution to return
- **ATTR-04**: Active exposure drift chart: does fund systematically shift sector weights in certain regimes?

### Extensions

- **EXT-01**: 3-state HMM variant explored (Risk-On / Transition / Risk-Off) if 2-state validation is strong
- **EXT-02**: Information ratio by regime (if benchmark tracking is a stated mandate objective)
- **EXT-03**: Rolling regime probability chart with regime duration annotations

## Out of Scope

| Feature | Reason |
|---------|--------|
| External market data (VIX, rates, Bloomberg) | Adds external dependency; benchmark-only model is sufficient and cleaner |
| >3 HMM states | Kills interpretability; 2-state is design target, 3-state is max extension |
| Predictive / forecasting output | Model is descriptive — no forecasting claims |
| CLI entry points or deployment | Research notebook only, not a production system |
| Real-time data feeds | Internal DB snapshots are sufficient for research purposes |
| Regime-switching regression | More powerful but harder to present; HMM is chosen for explainability |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 | Pending |
| DATA-02 | Phase 1 | Pending |
| DATA-03 | Phase 1 | Pending |
| DATA-04 | Phase 1 | Pending |
| DATA-05 | Phase 1 | Pending |
| REGM-01 | Phase 2 | Pending |
| REGM-02 | Phase 2 | Pending |
| REGM-03 | Phase 2 | Pending |
| REGM-04 | Phase 2 | Pending |
| REGM-05 | Phase 2 | Pending |
| REGM-06 | Phase 2 | Pending |
| FUND-01 | Phase 3 | Pending |
| FUND-02 | Phase 3 | Pending |
| FUND-03 | Phase 3 | Pending |
| FUND-04 | Phase 3 | Pending |
| STAB-01 | Phase 4 | Pending |
| STAB-02 | Phase 4 | Pending |
| STAB-03 | Phase 4 | Pending |
| VIZ-01 | Phase 5 | Pending |
| VIZ-02 | Phase 5 | Pending |
| VIZ-03 | Phase 5 | Pending |
| VIZ-04 | Phase 5 | Pending |
| SUMM-01 | Phase 6 | Pending |
| SUMM-02 | Phase 6 | Pending |
| SUMM-03 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 25 total
- Mapped to phases: 25
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-22*
*Last updated: 2026-04-22 after initial definition*
