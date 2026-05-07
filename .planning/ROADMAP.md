# Roadmap: Options Quant — GEX Analysis Platform

## Milestones

- ✅ **v3.0 GEX Interactive Dashboard** — Phases 1–4 (shipped 2026-05-06)
- 🚧 **v3.1 Hardening & Charm** — Phases 5–7 (in progress)

## Phases

<details>
<summary>✅ v3.0 GEX Interactive Dashboard (Phases 1–4) — SHIPPED 2026-05-06</summary>

- [x] Phase 1: Greeks Engine (2/2 plans) — completed 2026-05-05
- [x] Phase 2: Exposure + PM Flow (4/4 plans) — completed 2026-05-06
- [x] Phase 3: Streamlit Dashboard (2/2 plans) — completed 2026-05-06
- [x] Phase 4: Historical Tab (2/2 plans) — completed 2026-05-06

Full details: `.planning/milestones/v3.0-ROADMAP.md`

</details>

### 🚧 v3.1 Hardening & Charm (In Progress)

**Milestone Goal:** Sign off deferred UAT, add Charm chart, and fill critical test coverage gaps before handing the platform to PMs.

#### Phase Summary

- [ ] **Phase 5: UAT Sign-Off & Cleanup** — Complete 4 deferred Streamlit UAT scenarios, commit outstanding code changes, and update stale docs
- [ ] **Phase 6: Charm by DTE Chart** — Add Charm-by-DTE-bucket bar chart to analytics and surface it in the Streamlit Live tab expander
- [ ] **Phase 7: Critical-Path Test Coverage** — Add critical-path tests for the 5 previously uncovered modules

## Phase Details

### Phase 5: UAT Sign-Off & Cleanup
**Goal**: Complete the 4 deferred Streamlit UAT scenarios, commit outstanding code changes, and update stale docs/notes
**Depends on**: Phase 4
**Requirements**: UAT-01, UAT-02, UAT-03, UAT-04
**Success Criteria** (what must be TRUE):
  1. User can launch `streamlit run streamlit_app.py` without any import, COM, or matplotlib backend error
  2. Three regime cards (SPY, QQQ, IWM) render with correct colors, regime label, net GEX, VEX, delta-flow, and vs-yesterday label
  3. Clicking a ticker expander reveals two charts and a summary table with all 6 expected columns
  4. Clicking Refresh in the sidebar triggers a visible re-fetch and loads new data successfully
  5. Outstanding changes in emailer.py, report.py, and validation.py are committed; CLAUDE.md no longer references yfinance
**Plans**: 3 plans
Plans:
- [x] 05-P1-PLAN.md — Commit 3 outstanding code fixes (emailer, report, validation)
- [ ] 05-P2-PLAN.md — Live UAT walkthrough — 4 Streamlit scenarios (human interactive)
- [ ] 05-P3-PLAN.md — Post-UAT docs sweep and sign-off commit
**UI hint**: yes

### Phase 6: Charm by DTE Chart
**Goal**: Add a Charm-by-DTE-bucket bar chart to analytics and surface it in the Streamlit Live tab expander
**Depends on**: Phase 5
**Requirements**: CHARM-01, CHARM-02
**Success Criteria** (what must be TRUE):
  1. `analytics.py` exposes `charm_by_dte_chart()` that renders a bar chart of net charm bucketed by DTE (0–7, 8–30, 31–60, 60+)
  2. The chart appears inside the per-ticker expander in the Streamlit Live tab alongside the existing strike GEX and gamma profile charts
  3. The chart function does not raise an error when charm exposure is zero for a given bucket
**Plans**: TBD
**UI hint**: yes

### Phase 7: Critical-Path Test Coverage
**Goal**: Add critical-path tests for the 5 previously uncovered modules (data_loader, report, emailer, run_daily, analytics charts)
**Depends on**: Phase 6
**Requirements**: COV-01, COV-02, COV-03, COV-04, COV-05
**Success Criteria** (what must be TRUE):
  1. `tests/test_data_loader.py` passes: happy-path CBOE JSON parse, three filter variants, and malformed-symbol skip
  2. `tests/test_report.py` passes: `build_email()` returns non-empty HTML with ticker headers, correct regime class, and correct hex from color map
  3. `tests/test_emailer.py` passes: ValueError raised when no recipients configured; Outlook COM is mocked so the test runs without Outlook installed
  4. `tests/test_run_daily.py` passes: full 3-ticker orchestration with mocked data_loader and emailer; parquet snapshot written with expected columns
  5. `tests/test_analytics_charts.py` passes: chart functions return a matplotlib Figure for known-good input; zero-exposure edge case does not crash
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Greeks Engine | v3.0 | 2/2 | Complete | 2026-05-05 |
| 2. Exposure + PM Flow | v3.0 | 4/4 | Complete | 2026-05-06 |
| 3. Streamlit Dashboard | v3.0 | 2/2 | Complete | 2026-05-06 |
| 4. Historical Tab | v3.0 | 2/2 | Complete | 2026-05-06 |
| 5. UAT Sign-Off & Cleanup | v3.1 | 1/3 | In Progress | - |
| 6. Charm by DTE Chart | v3.1 | 0/TBD | Not started | - |
| 7. Critical-Path Test Coverage | v3.1 | 0/TBD | Not started | - |
