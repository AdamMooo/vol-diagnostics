# Roadmap: GEX Interactive Dashboard (v3.0)

## Overview

Four phases build the GEX Interactive Dashboard in strict dependency order. Phase 1 extends the Black-Scholes engine with second-order Greeks. Phase 2 threads those Greeks into the exposure layer and adds PM flow analytics. Phase 3 surfaces everything in a Streamlit dashboard. Phase 4 adds historical context via a dedicated tab.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3, 4): Planned milestone work
- Decimal phases (e.g., 2.1): Urgent insertions if needed

- [x] **Phase 1: Greeks Engine** - Add Vanna and Charm to the Black-Scholes engine with 0DTE safety guard (complete 2026-05-05)
- [ ] **Phase 2: Exposure + PM Flow** - Aggregate VEX/CHEX by strike; add delta-hedge flow and vs-yesterday metrics to email pipeline
- [ ] **Phase 3: Streamlit Dashboard** - Launch interactive dashboard with regime cards, cross-asset chart, and per-ticker expanders
- [ ] **Phase 4: Historical Tab** - Extend dashboard with ZGL trend chart, regime persistence table, streak counter, and event study

## Phase Details

### Phase 1: Greeks Engine
**Goal**: The Black-Scholes engine computes Vanna and Charm per contract with correct numerical guards
**Depends on**: Nothing (first phase)
**Requirements**: GRKS-01, GRKS-02, GRKS-03, GRKS-04
**Success Criteria** (what must be TRUE):
  1. `add_greeks()` returns a DataFrame with `vanna` and `charm` columns alongside the existing `gamma` column
  2. A 0DTE row (T = 0.0001) returns `charm = 0.0` — no divide-by-zero or inf
  3. Vanna values have the correct sign: calls produce positive vanna, puts produce negative vanna for standard moneyness
  4. Running `python -m pytest gex/` passes with tests covering bs_vanna and bs_charm
**Plans**: 2 plans

Plans:
- [ ] 01-01-PLAN.md — Add bs_vanna(), bs_charm(), T_MIN to greeks_engine.py; extend add_greeks()
- [ ] 01-02-PLAN.md — Create gex/tests/ pytest suite covering vanna, charm, 0DTE guard, and add_greeks()

### Phase 2: Exposure + PM Flow
**Goal**: Exposure aggregates include VEX and CHEX by strike; delta-hedge flow and vs-yesterday labels appear in the email summary table
**Depends on**: Phase 1
**Requirements**: EXP-01, EXP-02, EXP-03, EXP-04, FLOW-01, FLOW-02, FLOW-03, FLOW-04
**Success Criteria** (what must be TRUE):
  1. `summarise()` output dict contains `net_vex`, `net_chex`, and `delta_hedge_flow` keys with non-null float values
  2. Running `python -m gex.run_daily` completes without error and the saved parquet row contains a `vanna_exposure` column (old rows tolerate NaN without error)
  3. The email summary table includes a delta-flow column and a vs-yesterday label (UNCHANGED / FLIPPED / INTENSIFIED / EASED) for each ticker
  4. Loading the parquet snapshot for a prior session via `load_yesterday(ticker)` returns the previous trading session row — not calendar day minus one
**Plans**: 4 plans

Plans:
- [ ] 02-01-PLAN.md — Add compute_vex, compute_chex, strike_vex, strike_chex to exposure_engine.py; extend summarise() with optional flow kwargs
- [ ] 02-02-PLAN.md — Extend save_snapshot() with vanna_exposure; add load_yesterday() and _classify_vs_yesterday() to validation.py
- [ ] 02-03-PLAN.md — Wire VEX/CHEX/flow/vs-yesterday into process_ticker() in run_daily.py; update email table columns in report.py
- [ ] 02-04-PLAN.md — pytest suite for all Phase 2 new functions (parallel with 02-03)

### Phase 3: Streamlit Dashboard
**Goal**: A developer can launch the Streamlit app and interact with regime cards, charts, and per-ticker expanders for all 3 tickers (SPY, QQQ, IWM)
**Depends on**: Phase 2
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, DASH-06
**Success Criteria** (what must be TRUE):
  1. `streamlit run streamlit_app.py` starts without import errors from project root
  2. Selecting a subset of tickers in the sidebar and clicking refresh re-fetches only those tickers (cache cleared)
  3. Each regime card displays regime color, net GEX, VEX, delta-flow, and vs-yesterday label
  4. The cross-asset overview bar chart renders (reusing `analytics.plot_overview()`) and each selected ticker has an expandable section with strike GEX chart, gamma profile, and summary table
  5. `import streamlit_app` does not transitively import `gex.emailer` or `gex.run_daily` (verifiable via `python -c "import streamlit_app"` in a env without win32com)
**Plans**: 2 plans

Plans:
- [ ] 03-01-PLAN.md — Install streamlit; create full streamlit_app.py with sidebar, fetch layer, regime cards, overview chart, per-ticker expanders
- [ ] 03-02-PLAN.md — Create gex/tests/test_streamlit_app.py: import smoke, cache clear, plot_overview smoke tests

### Phase 4: Historical Tab
**Goal**: The dashboard Historical tab shows ZGL trend, regime persistence, streak counters, and event study output drawn from the parquet snapshot store
**Depends on**: Phase 3
**Requirements**: HIST-01, HIST-02, HIST-03, HIST-04
**Success Criteria** (what must be TRUE):
  1. The Historical tab renders a ZGL trend chart for any selected ticker showing 30 days of zero-gamma level with spot price overlaid on the same axes
  2. The regime persistence table shows % positive / negative / neutral over the last 20 trading sessions per selected ticker
  3. Each regime card displays a "Days in current regime" streak counter sourced from the parquet history
  4. Selecting a ticker with fewer than 20 sessions of history in the event study section shows an informational message rather than an error or empty chart
**Plans**: 2 plans

Plans:
- [ ] 04-01-PLAN.md — Add load_history() to gex/validation.py; pytest suite in gex/tests/test_validation_history.py
- [ ] 04-02-PLAN.md — Wrap streamlit_app.py in st.tabs; add streak counter; build Historical tab content

## Progress

**Execution Order:** 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Greeks Engine | 2/2 | Complete | 2026-05-05 |
| 2. Exposure + PM Flow | 0/4 | Not started | - |
| 3. Streamlit Dashboard | 0/2 | Not started | - |
| 4. Historical Tab | 0/2 | Not started | - |
