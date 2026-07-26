# Roadmap: Options Quant — GEX Analysis Platform

*Last updated: 2026-07-21 · v5.0 Data Foundation restructured — Phases 23–25 merged into one Data Completeness, Backup & Model-Readiness Audit phase; old 26–27 renumbered to 24–25*

## Milestones

- ✅ **v3.0 GEX Interactive Dashboard** — Phases 1–4 (shipped 2026-05-06)
- ✅ **v3.1 Hardening & Cleanup** — Phase 5 + out-of-phase refactor (shipped 2026-05-06 + 2026-05-11)
- ✅ **v3.2 Vol Surface Reframe** — Phases 6–7 (computation engine + institutional dashboard rendering)
- ✅ **v3.3 Surface Evolution & Daily Intelligence** — Phases 8–11 (shipped 2026-06-01)
- ✅ **v3.4 Email-First Daily Report Polish** — Phases 12–14 (shipped 2026-06-02)
- ✅ **v3.5 Index Vol-Context Rebuild** — Phases 15–18 (shipped 2026-06-24)
- ✅ **v4.0 Cloud Hosting** — Phases 19–22, 20.5 (shipped 2026-07-17) — see [[.planning/milestones/v4.0-ROADMAP|archive]]
- **v5.0 Data Foundation** — Phases 23–27 (in progress) — data completeness/gap monitoring + `out/` backup+restore + model-ready data definition/depth audit (merged into Phase 23), codebase cleanup, existing-computation rigor hardening, severity-statistics/alert engine + microstructure monitor UI (Phases 26–27, added 2026-07-23)
- **Backlog (999.x)** — Charm, test coverage, pre-distribution; awaiting research

## Phases

<details>
<summary>✅ v3.0–v4.0 (Phases 1–22) — SHIPPED — see .planning/milestones/ for full detail</summary>

- [x] **Phases 1–11** (v3.0–v3.3) — Greeks/exposure engine, Streamlit dashboard, historical tab, vol surface, surface evolution, dashboard restructure, richer daily report
- [x] **Phases 12–14** (v3.4) — Canonical card, 1-day ΔIV email PNGs, accumulation gating (superseded → Phase 18)
- [x] **Phases 15–18, 16.5, 17.1, 18.1** (v3.5) — Vol-index data layer, VRP percentile, OI depth expansion, term-structure regime, convexity/expected move, dashboard trust hardening, 3-page reorg
- [x] **Phases 19–22, 20.5** (v4.0) — Dockerize, data health hardening, email remodel, Oracle Cloud deploy, HTTPS

</details>

### v5.0 Data Foundation

- [ ] **Phase 23: Data Completeness, Backup & Model-Readiness Audit** - Detect gaps, back up `out/` off the single Oracle VM, and measure current data against a written model-ready bar
- [ ] **Phase 24: Codebase Organization & Dead Code Removal** - Sweep `engine/` for dead code/stale references, review module organization, sync CLAUDE.md
- [ ] **Phase 25: Existing Computation Rigor Hardening** - Verify VRP/RV20/surface-fit/skew-term computations against methodology, harden edge cases
- [x] **Phase 26: Severity Statistics & Alert Engine** - ECDF percentile ranks (levels + k-day changes, dual lookback) over existing metrics; transition-with-hysteresis alerts; bands from a false-alarm budget calibrated on stored history (verification found gaps 2026-07-22; gap closure plans 26-04/05 in progress) (completed 2026-07-24)
- [ ] **Phase 27: Microstructure Monitor UI** - Distribution-board landing + per-row evidence panels on the dashboard; event-shaped email alerts; email boilerplate cut

## Phase Details

### Phase 23: Data Completeness, Backup & Model-Readiness Audit

**Goal**: One integrated data-layer pass — gaps are detected, `out/` is durably backed up off the single Oracle VM, and current data is measured against a written model-ready bar — so the eventual modeling milestone starts from verified, recoverable, sufficient data.
**Depends on**: Nothing (first phase of v5.0)
**Requirements**: DATA-01, DATA-02, BACKUP-01, BACKUP-02, SCHEMA-01, SCHEMA-02
**Success Criteria** (what must be TRUE):

  1. Running a single command/script reports missing-session gaps per series (`gex_snapshots`, `surface_history`, `vol_index`, `oi_history`) per ticker (SPY/QQQ/IWM)
  2. Gap findings appear somewhere visible (health-check output) — not just sitting silently in parquet
  3. A known historical gap (e.g. a day the scheduler didn't fire) is correctly flagged by the tool
  4. Running the check against a complete history produces a clean "no gaps" result with no false positives
  5. `out/` parquet stores are copied to a location other than the Oracle VM on an automated cadence
  6. A written/runnable restore procedure exists that rebuilds `out/` without depending on the Oracle instance still existing
  7. A test restore (dry run) successfully reconstructs a working `out/` tree from the backup location
  8. Backup runs automatically (e.g. as part of the existing GitHub Actions workflow) with no manual step required
  9. A written spec exists stating, per data series, the minimum session depth and schema (columns/types) required before a predictive/prescriptive model could be built on it
  10. Current actual depth per series is measured and reported per ticker (SPY/QQQ/IWM) against those targets
  11. The measurement clearly shows which series/tickers already meet the bar and which fall short
  12. The spec and depth audit are discoverable from PROJECT.md/STATE.md so the next modeling milestone can reference them directly

**Plans**: TBD
**UI hint**: yes (dashboard integration explicitly out — see 23-CONTEXT.md)

### Phase 24: Codebase Organization & Dead Code Removal

**Goal**: The `engine/` codebase carries no dead code, unused imports, or stale references, and its module organization plus CLAUDE.md orientation docs are consistent with what's actually on disk.
**Depends on**: Nothing (independent cleanup pass; no hard technical dependency on Phase 23, though it folds in the stale `260514-fz2-dead-code-stale-ref-sweep` quick-task and backlog item 999.3 Pre-Distribution)
**Requirements**: CLEAN-01, CLEAN-02
**Success Criteria** (what must be TRUE):

  1. A static-analysis sweep of `engine/` and `app.py` (e.g. vulture/pyflakes-style dead-code scan) turns up zero unresolved findings — each hit is either removed or explicitly triaged as intentional
  2. The stale `260514-fz2-dead-code-stale-ref-sweep` quick-task and backlog item 999.3 Pre-Distribution are resolved and closed out, not just re-flagged
  3. Every module listed in CLAUDE.md's `engine/` package table still exists and matches its documented purpose; no orphaned files sit outside that table
  4. `pytest engine/tests` still passes 100% after all removals (no live code accidentally deleted)
  5. CLAUDE.md's `engine/` package tree section is edited in the same pass to reflect the actual on-disk structure

**Plans**: 2 plans

Plans:

**Wave 1**

- [x] 24-01-PLAN.md — Static-analysis dead-code sweep (vulture + pyflakes) over engine/ + app.py, triage every finding, remove genuine dead code, prove suite still 449-green (CLEAN-01, criteria 1 + 4)

**Wave 2** *(blocked on Wave 1 — CLAUDE.md sync must reflect the post-removal file set)*

- [ ] 24-02-PLAN.md — Sync CLAUDE.md engine tree/table to on-disk reality (add monitor/ + Phase-23 modules, fix test count); close out fz2 quick-task + 999.3 Pre-Distribution backlog item (CLEAN-02 + CLEAN-01, criteria 2 + 3 + 5)

### Phase 25: Existing Computation Rigor Hardening

**Goal**: The existing VRP, RV20, vol-surface-fit, and skew/term-structure computations are verified correct against their documented methodology and behave predictably (not silently wrong) on edge-case inputs. This is hardening of existing descriptive computations only — no new predictive/prescriptive model logic.
**Depends on**: Phase 24 (auditing correctness reads more cleanly against a codebase with dead code and stale references already removed)
**Requirements**: RIGOR-01, RIGOR-02
**Success Criteria** (what must be TRUE):

  1. Each of VRP, RV20, vol surface fit, and skew/term-structure has its implementation checked against its documented formula/methodology (e.g. Carr & Wu VRP, Black-Scholes surface fit), with any discrepancy either fixed or explicitly logged as an intentional deviation
  2. Edge cases — thin/cold-start data, missing strikes, single-quote days, degenerate surfaces — are exercised by new tests, and each produces a defined result (graceful NaN/skip) or fails loudly, never a silently-wrong number
  3. `pytest engine/tests` shows new tests specifically covering these edge cases (test count increases from the current 364), and 100% still pass
  4. No new predictive/prescriptive model logic is introduced — changes are limited to correctness/hardening of the existing four computations, consistent with MODEL-01/02 staying deferred

**Plans**: TBD

### Phase 26: Severity Statistics & Alert Engine

**Goal**: Every existing metric carries an honest "how unusual is this" measure — ECDF percentile ranks on levels and k-day changes (dual deep/1yr lookback), a transition-with-hysteresis alert rule, and alert bands derived from a false-alarm budget calibrated by replaying the ranker over stored history. No new signals — a severity transform over already-computed values.
**Requirements**: TBD
**Depends on:** Nothing hard (reads existing `out/` stores; benefits from Phase 23 gap detection but does not require it)
**Canonical refs:** `.planning/notes/microstructure-monitor-design.md`, `.planning/research/questions.md` (alert band calibration)
**Plans:** 5/5 plans complete

Plans:
**Wave 1**

- [x] 26-01-PLAN.md — Severity ranking foundation: config constants, monitor schema, ECDF ranker (dual lookback + k=5 change), per-metric loaders

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 26-02-PLAN.md — Hysteresis alert state machine + out/monitor/ persistence + run_daily wiring

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 26-03-PLAN.md — Calibration CLI (episodes/week replay) + finalize config.py alert bands

**Wave 4 (gap closure)** *(independent correctness fixes -- CR-01, WR-04, WR-05, WR-06)*

- [x] 26-04-PLAN.md — Stale-value fallback date guard, hysteresis state-hold on None rank, change-rank off-by-one fix, surface-evolution horizon decoupling

**Wave 5 (gap closure)** *(blocked on Wave 4 completion -- depends on engine/config.py; re-runs calibration under corrected methodology)*

- [x] 26-05-PLAN.md — Calibration methodology fixes (WR-01/02/03), hermetic test (WR-07), re-run calibration and finalize config.py bands

### Phase 27: Microstructure Monitor UI

**Goal**: The dashboard lands on a distribution board (percentile strip + 10-session trail per metric×ticker, ~15 rows) with per-row evidence panels (metric history with bands + mechanism view: smile / diff surface / implied-vs-realized pair); the daily email becomes event-shaped (band entries + escalations only, near-empty on normal days) with methodology boilerplate cut to a single link. Existing Surfaces/Positioning tabs unchanged as the exploration layer; net-GEX sign shown as a state chip, not a ranked row.
**Requirements**: TBD
**Depends on:** Phase 26 (consumes its severity ranks and alert events)
**Canonical refs:** `.planning/notes/microstructure-monitor-design.md`, `.planning/todos/pending/email-boilerplate-cut.md`
**Plans:** 0 plans

Plans:

- [ ] TBD (run /gsd-plan-phase 27 to break down)

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|-----------------|--------|-----------|
| 23. Data Completeness, Backup & Model-Readiness Audit | 3/4 | In Progress|  |
| 24. Codebase Organization & Dead Code Removal | 1/2 | In Progress|  |
| 25. Existing Computation Rigor Hardening | 0/TBD | Not started | - |

All phases through v4.0 (22 phases, 24 tracked plans + several ad-hoc) are complete. See `.planning/milestones/v4.0-ROADMAP.md` for full phase-level detail on the prior milestone; earlier milestones are archived similarly under `.planning/milestones/`.

---

## Backlog (999.x)

| Phase | Status | Notes |
|-------|--------|-------|
| 999.1 Charm Research | Parked | Awaiting validated methodology |
| 999.2 Test Coverage | Backlog | Depends on 999.1 |
| 999.3 Pre-Distribution | Closed | Closed in Phase 24 (24-02). Shipped out-of-phase: (a) snapshot timestamp header, (b) methodology caveat banner, (d) filter-drop transparency. Deferred: (c) "Regime sharpness" GEX slope field — counter to "no new signals"/GEX-demoted direction. |

---
---
---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
<!-- LINKS:END -->
