# Roadmap: Options Quant — GEX Analysis Platform

*Last updated: 2026-06-01 · v3.1 SHIPPED · v3.3 active (Phase 11 planned)*

## Milestones

- ✅ **v3.0 GEX Interactive Dashboard** — Phases 1–4 (shipped 2026-05-06)
- ✅ **v3.1 Hardening & Cleanup** — Phase 5 + out-of-phase refactor (shipped 2026-05-06 + 2026-05-11)
- ✅ **v3.2 Vol Surface Reframe** — Phases 6–7 (computation engine + institutional dashboard rendering)
- 🚧 **v3.3 Surface Evolution & Daily Intelligence** — Phases 8–11 (Phase 8 ✅ complete; 9–11 pending)
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

---

## v3.3 Phase Details — Surface Evolution & Daily Intelligence

*Synced into roadmap 2026-05-30. Phases 6–8 were planned/executed while this file tracked only v3.1; the v3.3 milestone lived in REQUIREMENTS.md + STATE.md. Phases 8–11 are recorded here so GSD tooling (`roadmap.get-phase`, init, verify, milestone) resolves them. Source of truth for requirement wording remains `.planning/REQUIREMENTS.md`.*

### Phase 8: Surface Validation (the gate)

**Goal**: Produce a surface coverage mask (honest NaN holes) + fit-honesty layer (RMSE/residuals, no-arb QA, documented smoothing) that becomes the single source of truth gating every downstream metric.
**Depends on**: Phase 7
**Requirements**: VALID-01, VALID-02, VALID-03, VALID-04, VALID-05, VALID-06
**Success Criteria** (what must be TRUE):

  1. Convex-hull coverage mask flags unsupported cells as honest NaN holes; exported as the single source of truth ✅
  2. Per-ticker RMSE + max residual (pp) persisted daily ✅
  3. `smoothing` lives in `config.py` with a documented sensitivity sweep (no magic number) ✅
  4. Calendar total-variance monotonicity + butterfly convexity QA report PASS/FAIL headless; never a signal, never auto-repair ✅
  5. One shared `rbf_grid` helper consumed by render, diagnostics, and evolution ✅
  6. Coverage % + fit RMS visible in the Streamlit dashboard ✅

**Status**: ✅ COMPLETE (verified 2026-05-30, PASSED)

### Phase 9: Surface Evolution Engine

**Goal**: Build the `surface_evolution` module — decompose ΔIV into level / rms / skew-change / term-change scalars on the masked grid against an N-day rolling-mean baseline, at 5/10/20 trading-day horizons, persisted daily and accumulating, computed as a non-blocking pass in `run_daily`, comparable cross-ticker, with a backfill from existing surface history.
**Depends on**: Phase 8
**Requirements**: EVOL-01, EVOL-02, EVOL-03, EVOL-04, EVOL-05, EVOL-06
**Success Criteria** (what must be TRUE):

  1. `surface_evolution` computes 4 scalars (level/rms/skew/term) vs the N-day rolling-mean baseline; comparison mask = today ∩ all N baseline-day masks so no extrapolated cell enters the diff
  2. Horizons 5/10/20 resolved against actually-stored trading sessions (not calendar arithmetic), each labelled with the real prior date; 1-day excluded
  3. Metrics persist to `out/surface_evolution.parquet`, idempotent on (date, ticker, horizon), accumulating forward
  4. Evolution runs as a non-blocking pass inside `run_daily` after the snapshot is saved; a failure here never blocks the email
  5. Surface-change is comparable across SPY / QQQ / IWM (cross-ticker divergence visible)
  6. A backfill routine retro-computes evolution from existing `surface_history`

**Plans**: 3 plans
Plans:
**Wave 1**

- [x] 09-01-PLAN.md — Config constants + nth_trading_day_back helper + test scaffolding

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 09-02-PLAN.md — Core engine: compute_evolution_scalars, update_evolution, save_evolution_row, load_evolution + unit/integration tests

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 09-03-PLAN.md — run_daily non-blocking pass + backfill CLI + integration tests + human checkpoint

**Status**: ○ Pending

### Phase 10: Dashboard Restructure (local only)

**Goal**: Collapse 5→4 tabs (merge Skew + Term around the surface calculus), remove the carry/VRP block + 25Δ RR-history chart + strike-GEX bar charts, add stored-vs-stored comparison and an evolution time-series, on a restrained professional palette with honest coverage holes.
**Depends on**: Phase 9
**Requirements**: VIEW-01, VIEW-02, VIEW-03, VIEW-04, VIEW-05
**Success Criteria** (what must be TRUE):

  1. Tabs reduced 5→4; Skew and Term merged into a single surface-calculus tab
  2. Carry/VRP block, 25Δ risk-reversal history chart, and strike-GEX bar charts removed
  3. Two stored dates can be compared (not only today-live vs a stored date)
  4. An evolution view charts level / rms / skew-change / term-change over time, selectable by horizon
  5. Restrained palette; coverage holes shown honestly; interactive 3D surface retained here

**Plans**: 2 plans
Plans:
**Wave 1**

- [x] 10-01-PLAN.md — Palette tokens + headless analysis functions + analytics.py cleanup (foundation)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 10-02-PLAN.md — streamlit_app.py full tab restructure (Surface / Calculus+VRP / Evolution / Positioning)

**Status**: ✅ COMPLETE (2026-06-01) — verified 5/5; CR-01 OI-vs-GEX gap closed inline (commit 00969c8)

### Phase 11: Richer Daily Report

**Goal**: Deliver a clean, formal daily email — 3D surface + ΔIV-surface PNG attachments (kaleido v1, pinned camera, smoke-test spike first), content prioritised surfaces > walls > OI > gamma, evolution scalars with a 5-day-rolling narrative lead, restrained palette.
**Depends on**: Phase 9
**Requirements**: RPT-01, RPT-02, RPT-03, RPT-04, RPT-05
**Success Criteria** (what must be TRUE):

  1. PNG export works on the target Windows machine via `kaleido>=1.0,<2.0` + one-time Chrome fetch; phase opens with a smoke-test spike; HTML-attachment fallback documented
  2. Email attaches the surface and ΔIV-surface 3D renders with a pinned camera angle
  3. Content prioritised surfaces > put/call walls > OI > gamma; OI surfaced as data
  4. Reads as a clean, formal business document; restrained palette; no decorative noise
  5. Evolution scalars present; narrative leads with the 5-day rolling read; 1-day excluded

**Plans**: 4 plans
Plans:
**Wave 1**

- [x] 11-01-PLAN.md — kaleido smoke-test spike + OI wall computation in compute_ticker()

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 11-02-PLAN.md — gex/png_export.py module (export_png utility, pinned camera, non-blocking)
- [x] 11-03-PLAN.md — report.py enrichment (OI rows, evolution section, #ffffff body, png_note slot)

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 11-04-PLAN.md — run_daily.py wiring + human dry-run checkpoint

**Status**: ○ Pending

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
---
---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
