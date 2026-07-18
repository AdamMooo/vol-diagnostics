# Roadmap: Options Quant — GEX Analysis Platform

*Last updated: 2026-07-17 · v5.0 Data Foundation roadmap extended (Phases 26–27 added)*

## Milestones

- ✅ **v3.0 GEX Interactive Dashboard** — Phases 1–4 (shipped 2026-05-06)
- ✅ **v3.1 Hardening & Cleanup** — Phase 5 + out-of-phase refactor (shipped 2026-05-06 + 2026-05-11)
- ✅ **v3.2 Vol Surface Reframe** — Phases 6–7 (computation engine + institutional dashboard rendering)
- ✅ **v3.3 Surface Evolution & Daily Intelligence** — Phases 8–11 (shipped 2026-06-01)
- ✅ **v3.4 Email-First Daily Report Polish** — Phases 12–14 (shipped 2026-06-02)
- ✅ **v3.5 Index Vol-Context Rebuild** — Phases 15–18 (shipped 2026-06-24)
- ✅ **v4.0 Cloud Hosting** — Phases 19–22, 20.5 (shipped 2026-07-17) — see [[.planning/milestones/v4.0-ROADMAP|archive]]
- **v5.0 Data Foundation** — Phases 23–27 (in progress) — data completeness/gap monitoring, `out/` backup+restore, model-ready data definition + depth audit, codebase cleanup, existing-computation rigor hardening
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

- [ ] **Phase 23: Data Completeness & Gap Monitoring** - Detect and surface missing-session gaps per series/ticker
- [ ] **Phase 24: Backup & Restore** - Get `out/` off the single Oracle VM with a documented restore path
- [ ] **Phase 25: Model-Ready Data Definition & Depth Audit** - Write the depth/schema bar for future modeling, measure current data against it
- [ ] **Phase 26: Codebase Organization & Dead Code Removal** - Sweep `engine/` for dead code/stale references, review module organization, sync CLAUDE.md
- [ ] **Phase 27: Existing Computation Rigor Hardening** - Verify VRP/RV20/surface-fit/skew-term computations against methodology, harden edge cases

## Phase Details

### Phase 23: Data Completeness & Gap Monitoring
**Goal**: An operator can see, for each ticker × series, whether data is complete or has gaps — without manually inspecting parquet files.
**Depends on**: Nothing (first phase of v5.0)
**Requirements**: DATA-01, DATA-02
**Success Criteria** (what must be TRUE):
  1. Running a single command/script reports missing-session gaps per series (`gex_snapshots`, `surface_history`, `vol_index`, `oi_history`) per ticker (SPY/QQQ/IWM)
  2. Gap findings appear somewhere visible (health-check output or a dashboard panel) — not just sitting silently in parquet
  3. A known historical gap (e.g. a day the scheduler didn't fire) is correctly flagged by the tool
  4. Running the check against a complete history produces a clean "no gaps" result with no false positives
**Plans**: TBD
**UI hint**: yes

### Phase 24: Backup & Restore
**Goal**: `out/` data survives loss of the Oracle VM.
**Depends on**: Nothing (independent of Phase 23)
**Requirements**: BACKUP-01, BACKUP-02
**Success Criteria** (what must be TRUE):
  1. `out/` parquet stores are copied to a location other than the Oracle VM on an automated cadence
  2. A written/runnable restore procedure exists that rebuilds `out/` without depending on the Oracle instance still existing
  3. A test restore (dry run) successfully reconstructs a working `out/` tree from the backup location
  4. Backup runs automatically (e.g. as part of the existing GitHub Actions workflow) with no manual step required
**Plans**: TBD

### Phase 25: Model-Ready Data Definition & Depth Audit
**Goal**: A future modeling milestone has a concrete, written bar for what "model-ready" data means, and current data is measured against it.
**Depends on**: Phase 23 (reuses gap-detection/session-counting logic to measure actual depth)
**Requirements**: SCHEMA-01, SCHEMA-02
**Success Criteria** (what must be TRUE):
  1. A written spec exists stating, per data series, the minimum session depth and schema (columns/types) required before a predictive/prescriptive model could be built on it
  2. Current actual depth per series is measured and reported per ticker (SPY/QQQ/IWM) against those targets
  3. The measurement clearly shows which series/tickers already meet the bar and which fall short
  4. The spec and depth audit are discoverable from PROJECT.md/STATE.md so the next modeling milestone can reference them directly
**Plans**: TBD

### Phase 26: Codebase Organization & Dead Code Removal
**Goal**: The `engine/` codebase carries no dead code, unused imports, or stale references, and its module organization plus CLAUDE.md orientation docs are consistent with what's actually on disk.
**Depends on**: Nothing (independent cleanup pass; no hard technical dependency on Phases 23–25, though it folds in the stale `260514-fz2-dead-code-stale-ref-sweep` quick-task and backlog item 999.3 Pre-Distribution)
**Requirements**: CLEAN-01, CLEAN-02
**Success Criteria** (what must be TRUE):
  1. A static-analysis sweep of `engine/` and `app.py` (e.g. vulture/pyflakes-style dead-code scan) turns up zero unresolved findings — each hit is either removed or explicitly triaged as intentional
  2. The stale `260514-fz2-dead-code-stale-ref-sweep` quick-task and backlog item 999.3 Pre-Distribution are resolved and closed out, not just re-flagged
  3. Every module listed in CLAUDE.md's `engine/` package table still exists and matches its documented purpose; no orphaned files sit outside that table
  4. `pytest engine/tests` still passes 100% after all removals (no live code accidentally deleted)
  5. CLAUDE.md's `engine/` package tree section is edited in the same pass to reflect the actual on-disk structure
**Plans**: TBD

### Phase 27: Existing Computation Rigor Hardening
**Goal**: The existing VRP, RV20, vol-surface-fit, and skew/term-structure computations are verified correct against their documented methodology and behave predictably (not silently wrong) on edge-case inputs. This is hardening of existing descriptive computations only — no new predictive/prescriptive model logic.
**Depends on**: Phase 26 (auditing correctness reads more cleanly against a codebase with dead code and stale references already removed)
**Requirements**: RIGOR-01, RIGOR-02
**Success Criteria** (what must be TRUE):
  1. Each of VRP, RV20, vol surface fit, and skew/term-structure has its implementation checked against its documented formula/methodology (e.g. Carr & Wu VRP, Black-Scholes surface fit), with any discrepancy either fixed or explicitly logged as an intentional deviation
  2. Edge cases — thin/cold-start data, missing strikes, single-quote days, degenerate surfaces — are exercised by new tests, and each produces a defined result (graceful NaN/skip) or fails loudly, never a silently-wrong number
  3. `pytest engine/tests` shows new tests specifically covering these edge cases (test count increases from the current 364), and 100% still pass
  4. No new predictive/prescriptive model logic is introduced — changes are limited to correctness/hardening of the existing four computations, consistent with MODEL-01/02 staying deferred
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|-----------------|--------|-----------|
| 23. Data Completeness & Gap Monitoring | 0/TBD | Not started | - |
| 24. Backup & Restore | 0/TBD | Not started | - |
| 25. Model-Ready Data Definition & Depth Audit | 0/TBD | Not started | - |
| 26. Codebase Organization & Dead Code Removal | 0/TBD | Not started | - |
| 27. Existing Computation Rigor Hardening | 0/TBD | Not started | - |

All phases through v4.0 (22 phases, 24 tracked plans + several ad-hoc) are complete. See `.planning/milestones/v4.0-ROADMAP.md` for full phase-level detail on the prior milestone; earlier milestones are archived similarly under `.planning/milestones/`.

---

## Backlog (999.x)

| Phase | Status | Notes |
|-------|--------|-------|
| 999.1 Charm Research | Parked | Awaiting validated methodology |
| 999.2 Test Coverage | Backlog | Depends on 999.1 |
| 999.3 Pre-Distribution | Partial | 50% out-of-phase; 50% deferred — folded into Phase 26 |

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
<!-- LINKS:END -->
