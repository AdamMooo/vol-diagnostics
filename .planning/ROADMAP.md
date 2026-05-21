# Roadmap: Options Quant — GEX Analysis Platform

*Last updated: 2026-05-22 · v3.2 in progress*

## Milestones

- ✅ **v3.0 GEX Interactive Dashboard** — Phases 1–4 (shipped 2026-05-06)
- ✅ **v3.1 Hardening & Cleanup** — Phase 5 + out-of-phase refactor (shipped 2026-05-06 + 2026-05-11)
- 🚧 **v3.2 Actionable Positioning Context** — Phases 6–7 (in progress)
- **Backlog (999.x)** — Charm, test coverage, pre-distribution; awaiting research

## Phases

<details>
<summary>✅ v3.0 GEX Interactive Dashboard (Phases 1–4) — SHIPPED 2026-05-06</summary>

- [x] **Phase 1: Greeks Engine** — Vanna + Charm in BS engine, 0DTE guard
- [x] **Phase 2: Exposure + PM Flow** — GEX/VEX by strike, delta-hedge flow, parquet store
- [x] **Phase 3: Streamlit Dashboard** — Regime cards, cross-asset chart, per-ticker expanders
- [x] **Phase 4: Historical Tab** — ZGL trend, regime persistence, streak counter, event study

</details>

<details>
<summary>✅ v3.1 Hardening & Cleanup (Phase 5) — SHIPPED 2026-05-11</summary>

- [x] **Phase 5: UAT Sign-Off & Cleanup** — 4 Streamlit scenarios pass, docs updated
- [x] **Out-of-Phase Refactor** — VEX/CHEX/regime labels removed; expected-1d-sigma added

</details>

### 🚧 v3.2 Actionable Positioning Context

- [ ] **Phase 6: Computation Engine + Output Cuts** — New positioning module, parquet schema, RV20 computation, remove noise metrics
- [ ] **Phase 7: Actionable Card Rendering** — VRP/percentile/narrative on dashboard + email with graceful degradation

## Phase Details

### Phase 6: Computation Engine + Output Cuts
**Goal**: Pipeline produces all new positioning metrics (RV20, VRP, percentile rank, narrative) and noise metrics are removed — computation exists before display
**Depends on**: Phase 5
**Requirements**: INFRA-01, INFRA-02, CTX-02, CUT-01, CUT-02, CUT-03
**Success Criteria** (what must be TRUE):
  1. `gex/positioning.py` exists with pure functions (`compute_rv20()`, `compute_vrp()`, `gex_percentile()`, `positioning_narrative()`) that return correct values given test inputs
  2. Running `python -m gex.run_daily` produces a summary dict containing `rv20`, `vrp`, `gex_percentile`, and `narrative` keys (values may be None during cold-start)
  3. Parquet snapshots written after this phase include `rv20` and `vrp` columns; old snapshots load without error (NaN for new columns)
  4. Dashboard regime cards no longer show "Hedge Sh/$1" row or "% vs ZGL" line; Vol tab no longer shows strike slope or term slope widgets
  5. `compute_surface_slopes()` is no longer called in the compute pipeline (dead code removed)
**Plans**: TBD

### Phase 7: Actionable Card Rendering
**Goal**: PM sees actionable positioning context on every card — VRP with hedging cost interpretation, GEX percentile rank, and mechanical positioning narrative — on both dashboard and email
**Depends on**: Phase 6
**Requirements**: NARR-01, NARR-02, CTX-01
**Success Criteria** (what must be TRUE):
  1. Dashboard and email cards show VRP (IV30 − RV20) with "options rich" / "options cheap" label; displays "—" gracefully when fewer than 20 sessions of spot history exist
  2. Dashboard cards show GEX percentile rank ("82nd percentile" style) when 30+ days of history exist; shows "Accumulating context (N/30 sessions)" below threshold
  3. Dashboard and email cards show a mechanical positioning narrative explaining GEX sign (positive = dampening, negative = amplifying) — frozen template text, no dynamic generation, no forward-looking language
**Plans**: TBD
**UI hint**: yes

---

## Backlog (999.x) — Deferred Pending Research & Validation

### 999.1: Charm by DTE Chart (Research Required)
**Status:** ⏸️ **PARKED** — Charm calculation on American options lacks mathematical rigor.
**Depends on:** Research phase (validated charm implementation proposal)

### 999.2: Critical-Path Test Coverage (Deferred)
**Status:** ⏸️ **BACKLOG** — Deferred pending 999.1 outcome.
**Depends on:** Phase 999.1 complete

### 999.3: Pre-Distribution Hardening (Partial)
**Status:** 🟡 **PARTIAL** — 50% complete via 2026-05-11 out-of-phase work.
**Depends on:** Phase 999.1 & 999.2 complete

---

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Greeks Engine | v3.0 | 2/2 | Complete | 2026-05-05 |
| 2. Exposure + PM Flow | v3.0 | 4/4 | Complete | 2026-05-06 |
| 3. Streamlit Dashboard | v3.0 | 2/2 | Complete | 2026-05-06 |
| 4. Historical Tab | v3.0 | 2/2 | Complete | 2026-05-06 |
| 5. UAT Sign-Off & Cleanup | v3.1 | 3/3 | Complete | 2026-05-06 |
| Out-of-Phase Refactor | v3.1 | (ad hoc) | Complete | 2026-05-11 |
| 6. Computation Engine + Output Cuts | v3.2 | 0/TBD | Not started | - |
| 7. Actionable Card Rendering | v3.2 | 0/TBD | Not started | - |

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
