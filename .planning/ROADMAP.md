# Roadmap: TQ HMM — Regime-Aware Fund Intelligence

## Overview

Six phases build the notebook from raw data to presentation-ready output. Phases 1-2 establish the foundation (data + regime model); Phases 3-4 derive fund behavior and stability analytics; Phase 5 polishes all charts to presentation quality; Phase 6 assembles the deliverable and validates top-to-bottom execution. Phase 4 can begin in parallel with Phase 3 once the regime state series from Phase 2 is complete.

## Phases

- [x] **Phase 1: Data Layer** - Load, clean, and align fund and benchmark returns; produce EDA section
- [x] **Phase 2: Regime Model** - Fit 2-state HMM on benchmark, validate stability, label regimes
- [ ] **Phase 3: Fund Analysis** - Compute regime-conditional statistics and alpha/beta; format core deliverable table
- [ ] **Phase 4: Regime Stability & Transitions** - Transition matrix, expected durations, current regime read-out
- [ ] **Phase 5: Visualization** - Regime-shaded charts, distribution plots, consistent palette, presentation quality
- [ ] **Phase 6: Summary & Polish** - Plain-English findings, caveats, clean top-to-bottom run

## Phase Details

### Phase 1: Data Layer
**Goal**: Fund and benchmark return series are loaded, cleaned, aligned, and characterized — the notebook can run all downstream analysis on validated data
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05
**Success Criteria** (what must be TRUE):
  1. A Setup cell documents the DB connection and data pull without requiring reader intervention
  2. Fund and benchmark returns share a common date index with no unexplained gaps and explicitly handled missing dates
  3. The EDA section shows summary statistics, cumulative return, rolling vol, and drawdown — all readable without further processing
  4. A reader can confirm data quality by inspecting the EDA outputs alone
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md — Setup cell (constants, color palette) + Data Load cell (Django ORM fund NAV, Bloomberg benchmark price, frequency check)
- [x] 01-02-PLAN.md — Log returns (np.log), date alignment (inner join, no forward-fill), fund_aligned + bench_aligned output variables
- [x] 01-03-PLAN.md — EDA section: summary stats table (annualized return/vol/Sharpe/max DD) + 3 charts (cumulative return, rolling 21d vol, drawdown)

### Phase 2: Regime Model
**Goal**: A validated, labeled 2-state HMM is fit on benchmark returns and its regime assignments are ready for downstream use
**Depends on**: Phase 1
**Requirements**: REGM-01, REGM-02, REGM-03, REGM-04, REGM-05, REGM-06
**Success Criteria** (what must be TRUE):
  1. The HMM fits and converges; regime state series is stored as a date-indexed labeled series
  2. Regime posterior probabilities are plotted over the full history
  3. Average regime duration is documented as weeks-to-months (not days), confirming the model isn't noise-following
  4. Re-fitting with 10 random seeds produces consistent regime assignments (stability documented in notebook)
  5. Regimes carry human-readable labels (e.g. Risk-On / Risk-Off) grounded in conditional statistics
**Plans**: 3 plans

Plans:
- [x] 02-01-PLAN.md — Section 2 header + HMM fit (GaussianHMM, Viterbi decode, convergence check) + regime statistics + composite labeling (regime_labels output)
- [x] 02-02-PLAN.md — Regime duration validation (spell detection, mean/median days/weeks per state) + seed stability check (9 refits, label-swap-aware agreement fractions)
- [x] 02-03-PLAN.md — Posterior probability extraction (predict_proba, regime_posteriors) + P(Risk-On) chart + Phase 2 output summary cell with integrity assertions

### Phase 3: Fund Analysis
**Goal**: The core deliverable — regime-conditional statistics, alpha/beta, and a finance-audience summary table — is complete
**Depends on**: Phase 2
**Requirements**: FUND-01, FUND-02, FUND-03, FUND-04
**Success Criteria** (what must be TRUE):
  1. Mean return, vol, Sharpe, and max drawdown are computed separately for each regime state
  2. Alpha and beta are estimated by regime via OLS with sample size and date range documented for each split
  3. A formatted summary statistics table is present and readable without needing to run further code
**Plans**: TBD

Plans:
- [ ] 03-01: Regime-conditional statistics (return, vol, Sharpe, max drawdown per state)
- [ ] 03-02: Alpha/beta by regime (OLS split), sample sizes, date ranges
- [ ] 03-03: Summary statistics table formatted for finance audience

### Phase 4: Regime Stability & Transitions
**Goal**: Transition dynamics and the current regime read-out are fully documented — a reader can assess how sticky regimes are and where we are today
**Depends on**: Phase 2
**Requirements**: STAB-01, STAB-02, STAB-03
**Success Criteria** (what must be TRUE):
  1. A labeled transition probability heatmap shows persistence and switching probabilities between states
  2. Expected duration for each regime is computed from the transition matrix diagonal and stated plainly
  3. The current regime posterior and days-in-current-regime are displayed as of the latest data date
**Plans**: TBD

Plans:
- [ ] 04-01: Transition matrix computation and labeled heatmap
- [ ] 04-02: Expected durations and current regime read-out

### Phase 5: Visualization
**Goal**: All charts are presentation-quality and use a consistent regime color palette — the notebook is visually coherent and presentable to a PM or investment committee
**Depends on**: Phase 3, Phase 4
**Requirements**: VIZ-01, VIZ-02, VIZ-03, VIZ-04
**Success Criteria** (what must be TRUE):
  1. The cumulative return chart has background shading that colors each period by regime state
  2. A return distribution histogram shows fund returns split by regime, overlapping and labeled
  3. Every time-series chart uses the same regime color assignments (no mismatched colors across sections)
  4. All charts have clean axes, titles, and axis labels — no default matplotlib chart junk
**Plans**: TBD
**UI hint**: yes

Plans:
- [ ] 05-01: Regime-shaded cumulative return chart and palette constants
- [ ] 05-02: Return distribution histogram split by regime
- [ ] 05-03: Polish pass — apply consistent palette and presentation standards to all charts

### Phase 6: Summary & Polish
**Goal**: The notebook is a complete, self-contained research deliverable — plain-English findings, honest caveats, and a clean top-to-bottom run on a fresh kernel
**Depends on**: Phase 5
**Requirements**: SUMM-01, SUMM-02, SUMM-03
**Success Criteria** (what must be TRUE):
  1. A summary section contains 3-5 plain-English bullet findings a non-quant PM can read and act on
  2. A caveats section addresses in-sample labeling, no-forecasting scope, and flags any regime splits with small sample sizes
  3. The notebook runs Kernel → Restart & Run All without errors or manual intervention
**Plans**: TBD

Plans:
- [ ] 06-01: Summary section (3-5 plain-English findings)
- [ ] 06-02: Caveats section and sample size warnings
- [ ] 06-03: End-to-end clean run, cell ordering, output validation

## Progress

**Execution Order:**
Phases 1 → 2 → 3 and 4 (parallel after Phase 2) → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Layer | 3/3 | Complete | 2026-04-22 |
| 2. Regime Model | 3/3 | Complete | 2026-04-22 |
| 3. Fund Analysis | 0/3 | Cells written — pending server run | - |
| 4. Regime Stability & Transitions | 0/2 | Not started | - |
| 5. Visualization | 0/3 | Not started | - |
| 6. Summary & Polish | 0/3 | Not started | - |
