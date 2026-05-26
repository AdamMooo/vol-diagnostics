# Roadmap: Options Quant — Institutional Vol Diagnostics Platform

*Last updated: 2026-05-26 · v3.2 in progress — reframed as institutional vol diagnostics*

## Milestones

- ✅ **v3.0 GEX Interactive Dashboard** — Phases 1–4 (shipped 2026-05-06)
- ✅ **v3.1 Hardening & Cleanup** — Phase 5 + out-of-phase refactor (shipped 2026-05-06 + 2026-05-11)
- 🚧 **v3.2 Institutional Vol Diagnostics** — Phases 6–7 (in progress)
- **Backlog (999.x)** — Charm, test coverage, pre-distribution; awaiting research

## Product Philosophy

Dashboard anchors on observable option prices and derived quantities (IV surface, skew, term structure, VRP). GEX is a secondary contextual layer — useful for short-horizon flow context, not the organizing principle.

PM-facing questions this product answers:
- **Protection timing**: is downside insurance expensive or cheap right now?
- **Vol-writing/overwrite timing**: are we being paid enough to be short vol?
- **Risk regime monitoring**: is the surface behaving normally, stressed, or dislocated?

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

### 🚧 v3.2 Institutional Vol Diagnostics

- [ ] **Phase 6: Whole-Chain Computation Engine** — 25Δ skew, ATM term structure, VRP/carry engine, clean surface data; noise cuts
- [ ] **Phase 7: Institutional Dashboard Rendering** — 5-module tab structure: Surface, Skew, Term Structure, Carry, Flow Context (GEX demoted)

## Phase Details

### Phase 6: Whole-Chain Computation Engine
**Goal**: Pipeline computes all institutional vol metrics from the chain — 25Δ skew per expiry, ATM term structure, RV20/VRP carry — and surface is stripped of GEX overlays. Computation exists before display.
**Depends on**: Phase 5
**Product modules delivered**: Surface (data), Skew (computation), Term Structure (computation), Carry (computation)
**Success Criteria** (what must be TRUE):
  1. `gex/vol_metrics.py` exists with pure functions: `compute_skew_25d()`, `compute_term_structure()`, `compute_rv20()`, `compute_vrp()` — each returns correct values given test inputs
  2. `vol_surface_data()` in `exposure_engine.py` returns clean OTM IV scatter; `plot_vol_surface()` in `analytics.py` accepts no GEX overlay parameters — no spot plane, no meridian traces
  3. `compute_ticker()` in `compute.py` returns dict containing `skew`, `term_structure`, `rv20`, `vrp` keys (values may be None on cold-start)
  4. Parquet snapshots include `rv20` and `vrp` columns; old snapshots load without error (NaN for new columns)
  5. `compute_surface_slopes()` is no longer called anywhere (dead code removed)
  6. Noise cuts: dashboard no longer shows "Hedge Sh" row or "% vs ZGL" line
**Plans**: 4 plans
Plans:
- [x] 06-01-PLAN.md — create gex/vol_metrics.py with 4 pure functions + 11 unit tests (TDD)
- [x] 06-02-PLAN.md — strip GEX overlays from plot_vol_surface(), Viridis colorscale, 3 noise cuts in streamlit_app.py
- [x] 06-03-PLAN.md — wire new metrics into compute_ticker() return dict; extend parquet schema (rv20, vrp)
- [x] 06-04-PLAN.md — gap closure: VRP unit fix (CR-01 BLOCKER), mock namespace (WR-01), stale text (WR-02), dead var (IN-01)

### Phase 7: Institutional Dashboard Rendering
**Goal**: Dashboard presents as a whole-chain vol diagnostics tool with 5 clear modules. PM can answer cost-of-protection and vol-carry questions directly from the dashboard.
**Depends on**: Phase 6
**Product modules delivered**: all 5 rendered
**Success Criteria** (what must be TRUE):
  1. **Surface tab**: clean 3D IV surface (log-moneyness × DTE × IV%), no GEX overlays, viridis colorscale, matches institutional reference aesthetic
  2. **Skew tab**: front-month and second-month 25Δ put-call skew displayed with rolling 30-day history chart; labeled precisely ("25Δ put-call skew")
  3. **Term Structure tab**: ATM IV by expiry plotted as line chart; curve classified as normal / flat / humped / inverted with restrained label
  4. **Carry tab**: IV30 vs RV20 side-by-side + VRP spread (IV30 − RV20) with rolling history; labeled as "vol carry / VRP"
  5. **Flow Context tab**: GEX, net gamma, zero-gamma level displayed here only, with explicit header "Microstructure / Execution Context — model-based, not market prices"
  6. No deterministic language anywhere on dashboard; all panels use precise metric labels
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
| 6. Whole-Chain Computation Engine | v3.2 | 4/4 | Complete | 2026-05-26 |
| 7. Institutional Dashboard Rendering | v3.2 | 0/TBD | Not started | - |

---
---
---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
