# Roadmap: Options Quant — GEX Analysis Platform

*Last updated: 2026-06-01 · v3.3 SHIPPED · v3.4 active (Phases 12–14 planned)*

## Milestones

- ✅ **v3.0 GEX Interactive Dashboard** — Phases 1–4 (shipped 2026-05-06)
- ✅ **v3.1 Hardening & Cleanup** — Phase 5 + out-of-phase refactor (shipped 2026-05-06 + 2026-05-11)
- ✅ **v3.2 Vol Surface Reframe** — Phases 6–7 (computation engine + institutional dashboard rendering)
- ✅ **v3.3 Surface Evolution & Daily Intelligence** — Phases 8–11 (shipped 2026-06-01)
- 🚧 **v3.4 Email-First Daily Report Polish** — Phases 12–14 (in progress)
- **Backlog (999.x)** — Charm, test coverage, pre-distribution; awaiting research

## Phases

<details>
<summary>✅ v3.0–v3.3 (Phases 1–11) — SHIPPED</summary>

- [x] **Phase 1: Greeks Engine** — Vanna + Charm BS engine, 0DTE guard, `add_greeks()`
- [x] **Phase 2: Exposure + PM Flow** — GEX/VEX by strike, delta-hedge flow, vs-yesterday labels
- [x] **Phase 3: Streamlit Dashboard** — Regime cards, cross-asset chart, per-ticker expanders
- [x] **Phase 4: Historical Tab** — ZGL trend, regime persistence, streak counter, event study
- [x] **Phase 5: UAT Sign-Off & Cleanup** — All 4 Streamlit scenarios pass, docs updated
- [x] **Phase 6: Whole-Chain Computation Engine** — Vol surface, skew/term, VRP, parquet schema
- [x] **Phase 7: Institutional Dashboard Rendering** — Clean surface, 25Δ skew, term structure, VRP display
- [x] **Phase 8: Surface Validation** — Convex-hull coverage mask, fit residuals, QA gate
- [x] **Phase 9: Surface Evolution Engine** — ΔIV decomposed level/rms/skew/term at 5/10/20 horizons
- [x] **Phase 10: Dashboard Restructure** — 5→4 tabs, stored-vs-stored compare, evolution view, OI-led Positioning
- [x] **Phase 11: Richer Daily Report** — Surface + ΔIV PNG attachments, OI walls, evolution scalars in email

</details>

---

### 🚧 v3.4 Email-First Daily Report Polish (In Progress)

**Milestone Goal:** Curate the daily email into a tight single-snapshot diagnostic, unify the email and dashboard around one canonical card, replace the static surface PNGs with 1-day ΔIV surfaces, and gate accumulation-dependent UI until enough sessions exist. Every scope item is single-snapshot or near-it.

- [x] **Phase 12: Canonical Card** — Single source-of-truth card shared by email + dashboard; VRP, scalar deltas, wall labels (completed 2026-06-01)
- [ ] **Phase 13: 1-Day ΔIV Email PNGs** — Replace static surface + 5d ΔIV PNGs with one 1d ΔIV surface PNG per ticker
- [ ] **Phase 14: Accumulation Gating** — Gate history-dependent UI elements behind session-count guards; cold-start safe email

---

## Phase Details

### Phase 12: Canonical Card

**Goal**: A single canonical per-ticker card definition drives both the email and the Streamlit dashboard — VRP, signed 1-session scalar deltas on iv30/skew/net GEX, and "(model)" vs "(raw OI)" wall labels — so the two surfaces cannot drift apart.
**Depends on**: Phase 11
**Requirements**: CARD-01, CARD-02, CARD-03, CARD-04
**Success Criteria** (what must be TRUE):
  1. The email card and the dashboard regime card render the same fields from the same source; changing the card definition in one place updates both.
  2. VRP (IV30 − RV20) appears as a scalar on the card in both the email and the dashboard.
  3. IV30, front skew (25Δ), and net GEX each show a signed 1-session delta (e.g. `18.5% (+0.8)`); when no prior snapshot exists the delta suffix is absent, not NaN or an error.
  4. GEX walls are labelled "(model)" and OI walls "(raw OI)" consistently in both surfaces, with a one-line inline distinction so the two types are never confused.
**Plans**: 3 plans
**UI hint**: yes

Plans:
- [x] 12-01-PLAN.md — Shared card-model layer: CardField + build_card_fields(), iv30 schema, load_prior_snapshot
- [x] 12-02-PLAN.md — Email renderer integration: _ticker_card() consumes build_card_fields()
- [x] 12-03-PLAN.md — Dashboard renderer integration: render_regime_card() consumes build_card_fields()

---

### Phase 13: 1-Day ΔIV Email PNGs

**Goal**: The daily email attaches exactly one PNG type — a 1-day ΔIV surface render per index (SPY, QQQ, IWM) labelled with the real prior date — replacing the 3 static surface PNGs and the old SPY-only 5-day ΔIV PNG 1:1. The evolution engine's {5,10,20} horizons are untouched.
**Depends on**: Phase 12
**Requirements**: RPT-06, RPT-07
**Success Criteria** (what must be TRUE):
  1. The email attaches up to 3 PNGs (one per ticker); no static surface PNGs or 5-day ΔIV PNGs are attached.
  2. Each PNG shows the 1-day ΔIV surface labelled with the real prior-session date, resolved via `nth_trading_day_back(ticker, today, 1)` (gap-safe).
  3. When no prior snapshot exists for a ticker, that ticker's PNG is omitted and the email still sends successfully.
  4. The evolution engine's `surface_evolution.parquet` and its {5,10,20} horizon computations are unchanged.
**Plans**: 1 plan

Plans:
- [ ] 13-01-PLAN.md — Swap PNG block: 1-day ΔIV per ticker, delete static surface + 5d ΔIV PNGs, add tests

---

### Phase 14: Accumulation Gating

**Goal**: History-dependent UI elements in the dashboard are hidden behind explicit "needs ≥N sessions" guards until enough stored sessions exist; the email never fails or renders empty/NaN content when required history is absent.
**Depends on**: Phase 12
**Requirements**: GATE-01, GATE-02
**Success Criteria** (what must be TRUE):
  1. Evolution-tab small-multiples, VRP/skew percentiles, the VRP sparkline, and the 42-session spot-vs-levels chart each display a clear "needs ≥N sessions" caption when insufficient history exists, rather than an empty chart or NaN values.
  2. The underlying engines and parquet stores are untouched — only display is gated.
  3. The email cold-starts cleanly: history-dependent sections (evolution block, ΔIV PNGs) are omitted rather than rendered empty when required history does not exist, and the send completes without error.
**Plans**: 3 plans
**UI hint**: yes

Plans:
- [x] 12-01-PLAN.md — Shared card-model layer: CardField + build_card_fields(), iv30 schema, load_prior_snapshot
- [x] 12-02-PLAN.md — Email renderer integration: _ticker_card() consumes build_card_fields()
- [ ] 12-03-PLAN.md — Dashboard renderer integration: render_regime_card() consumes build_card_fields()

---

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Greeks Engine | v3.0 | 2/2 | Complete | 2026-05-05 |
| 2. Exposure + PM Flow | v3.0 | 4/4 | Complete | 2026-05-06 |
| 3. Streamlit Dashboard | v3.0 | 2/2 | Complete | 2026-05-06 |
| 4. Historical Tab | v3.0 | 2/2 | Complete | 2026-05-06 |
| 5. UAT Sign-Off & Cleanup | v3.1 | 3/3 | Complete | 2026-05-06 |
| 6. Whole-Chain Computation Engine | v3.2 | 4/4 | Complete | 2026-05-26 |
| 7. Institutional Dashboard Rendering | v3.2 | 2/2 | Complete | 2026-05-26 |
| 8. Surface Validation | v3.3 | 3/3 | Complete | 2026-05-30 |
| 9. Surface Evolution Engine | v3.3 | 3/3 | Complete | 2026-05-30 |
| 10. Dashboard Restructure | v3.3 | 2/2 | Complete | 2026-06-01 |
| 11. Richer Daily Report | v3.3 | 4/4 | Complete | 2026-06-01 |
| 12. Canonical Card | v3.4 | 3/3 | Complete   | 2026-06-01 |
| 13. 1-Day ΔIV Email PNGs | v3.4 | 0/TBD | Not started | - |
| 14. Accumulation Gating | v3.4 | 0/TBD | Not started | - |

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
