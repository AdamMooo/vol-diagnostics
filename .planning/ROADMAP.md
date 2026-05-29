# Roadmap: Options Quant — GEX Analysis Platform

*Last updated: 2026-05-12 · v3.1 SHIPPED · Backlog pending research*

## Milestones

- ✅ **v3.0 GEX Interactive Dashboard** — Phases 1–4 (shipped 2026-05-06)
- ✅ **v3.1 Hardening & Cleanup** — Phase 5 + out-of-phase refactor (shipped 2026-05-06 + 2026-05-11)
- 🔍 **Research Phase (TBD)** — Validate charm/Greeks methodology before next milestone
- **Backlog (999.x)** — Charm, test coverage, pre-distribution; awaiting research

## Phases
### 🚧 v3.1 Hardening & Cleanup (In Progress → Complete)

**Milestone Goal:** Complete UAT sign-off, remove non-defensible outputs per methodology audit, and stabilize the GEX POC.

**Completed:**
- [x] Phase 5: UAT Sign-Off & Cleanup (all 4 scenarios pass, docs updated)
- [x] Out-of-Phase Refactor (2026-05-11): VEX/CHEX/regime labels removed; expected-1d-sigma added; methodology footer rewritten
- Status: ✅ SHIPPED (2026-05-06 + 2026-05-11)

**Deferred to Backlog / Future Milestones:**
- Phase 6: Charm by DTE Chart — Requires validated charm calculation methodology (deferred to 999.1)
- Phase 7: Critical-Path Test Coverage — Deferred pending Phase 6 outcome (deferred to 999.2)
- Phase 8: Pre-Distribution Hardening — Partial out-of-phase work done; remainder deferred (deferred to 999.3)

---

## Backlog (999.x) — Deferred Pending Research & Validation

### 999.1: Charm by DTE Chart (Research Required)
**Status:** ⏸️ **PARKED** — Charm calculation on American options lacks mathematical rigor. Requires validated methodology before implementation.
**Decision:** Cannot implement until research establishes defensible charm metric for dealer flow analysis.
**Depends on:** Research phase (validated charm implementation proposal)

### 999.2: Critical-Path Test Coverage (Deferred)
**Status:** ⏸️ **BACKLOG** — Deferred pending Phase 999.1 outcome and overall direction validation.
**Target:** ~15 new tests (data_loader, report, emailer, run_daily, analytics)
**Depends on:** Phase 999.1 complete (know what we're testing)

### 999.3: Pre-Distribution Hardening (Partial)
**Status:** 🟡 **PARTIAL** — 50% complete via 2026-05-11 out-of-phase work (DIST-02, DIST-03 done)
**Remaining:** DIST-01 (timestamp threading), DIST-04 (filter-drop transparency)
**Decision:** Defer both until Phase 6 research resolves direction.
**Depends on:** Phase 999.1 & 999.2 complete

---

## Phase Details

### Phase 5: UAT Sign-Off & Cleanup
**Goal**: Complete the 4 deferred Streamlit UAT scenarios, commit outstanding code changes, and update stale docs/notes
**Depends on**: Phase 4
**Requirements**: UAT-01, UAT-02, UAT-03, UAT-04
**Success Criteria** (what must be TRUE):
  1. User can launch `streamlit run streamlit_app.py` without any import, COM, or matplotlib backend error ✅
  2. Regime cards (SPY, QQQ, IWM) render with correct colors, net GEX, delta-flow, and vs-ZGL label ✅
  3. Clicking a ticker expander reveals two charts and a summary table with all expected columns ✅
  4. Clicking Refresh in the sidebar triggers a visible re-fetch and loads new data successfully ✅
  5. Outstanding changes in emailer.py, report.py, and validation.py are committed ✅
**Plans**: 3 plans
Plans:
- [x] 05-P1-PLAN.md — Commit 3 outstanding code fixes (emailer, report, validation) ✅
- [x] 05-P2-PLAN.md — Live UAT walkthrough — 4 Streamlit scenarios (human interactive) ✅
- [x] 05-P3-PLAN.md — Post-UAT docs sweep and sign-off commit ✅
**UI hint**: yes
**Status**: ✅ COMPLETE (2026-05-06)

---

### Out-of-Phase Refactoring (2026-05-11)
**Trigger**: [[_audits/methodology-review-2026-05-11|Methodology audit 2026-05-11]] revealed statistically indefensible outputs
**Work completed**:
- EMAIL (gex/report.py): Removed regime badge, ZGL flow row, GEX-weighted wall cluster (replaced with single max strike)
- DASHBOARD (streamlit_app.py): Removed VEX/CHEX, regime label text, vs-yesterday badge, streak counter, regime % frequency table
- Rewrote methodology footer in both surfaces with "defensible outputs only" framing
**Impact on Phase 6**: Charm chart phase can now proceed — CHEX removal clarifies that Charm will be new, not a display-only fix
**Impact on Phase 8**: ~70% of Phase 8 scope completed as part of this refactor (removed non-defensible outputs; added expected-1d-sigma display; clarified wall/ZGL/DF as load-bearing signals)
**Test count**: Down to 24 (from 77 post-v3.0); removed tests for deleted features; core analytics tests intact
**Status**: ✅ COMPLETE (2026-05-11; merged main)







## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Greeks Engine | v3.0 | 2/2 | Complete | 2026-05-05 |
| 2. Exposure + PM Flow | v3.0 | 4/4 | Complete | 2026-05-06 |
| 3. Streamlit Dashboard | v3.0 | 2/2 | Complete | 2026-05-06 |
| 4. Historical Tab | v3.0 | 2/2 | Complete | 2026-05-06 |
| 5. UAT Sign-Off & Cleanup | v3.1 | 3/3 | Complete | 2026-05-06 |
| Out-of-Phase Refactor | v3.1 | (ad hoc) | Complete | 2026-05-11 |

**Milestone Status:** ✅ **v3.1 SHIPPED** (2026-05-06 + 2026-05-11)

---

## Backlog (999.x)

| Phase | Status | Notes |
|-------|--------|-------|
| 999.1 Charm Research | Parked | Awaiting validated methodology |
| 999.2 Test Coverage | Backlog | Depends on 999.1 |
| 999.3 Pre-Distribution | Partial | 50% out-of-phase; 50% deferred |

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
