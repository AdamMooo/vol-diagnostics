# Roadmap: Options Quant — Institutional Vol Diagnostics Platform

*Last updated: 2026-05-29 · v3.3 roadmapped — Surface Evolution & Daily Intelligence (Phases 8–11)*

## Milestones

- ✅ **v3.0 GEX Interactive Dashboard** — Phases 1–4 (shipped 2026-05-06)
- ✅ **v3.1 Hardening & Cleanup** — Phase 5 + out-of-phase refactor (shipped 2026-05-06 + 2026-05-11)
- ✅ **v3.2 Institutional Vol Diagnostics** — Phases 6–7 (closed; P7 5-tab layout superseded by v3.3 restructure)
- 🚧 **v3.3 Surface Evolution & Daily Intelligence** — Phases 8–11 (roadmapped 2026-05-29)
- **Backlog (999.x)** — Charm, test coverage, pre-distribution; awaiting research

## Product Philosophy

Dashboard anchors on observable option prices and derived quantities (IV surface, skew, term structure, VRP). GEX is a secondary contextual layer — useful for short-horizon flow context, not the organizing principle.

PM-facing questions this product answers:
- **Protection timing**: is downside insurance expensive or cheap right now?
- **Vol-writing/overwrite timing**: are we being paid enough to be short vol?
- **Risk regime monitoring**: is the surface behaving normally, stressed, or dislocated?
- **Surface evolution (v3.3)**: how is the surface *moving* over time, and where is that movement real vs interpolation artifact?

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

<details>
<summary>✅ v3.2 Institutional Vol Diagnostics (Phases 6–7) — CLOSED</summary>

- [x] **Phase 6: Whole-Chain Computation Engine** — 25Δ skew, ATM term structure, VRP/carry engine, clean surface data; noise cuts (2026-05-26)
- [x] **Phase 7: Institutional Dashboard Rendering** — 5-module tab structure: Surface, Skew, Term Structure, Carry, Flow Context (GEX demoted). *Note: the 5-tab layout is superseded by the v3.3 Phase 10 5→4 restructure.*

</details>

### 🚧 v3.3 Surface Evolution & Daily Intelligence (Phases 8–11)

Foundation-first, gated. Phase 8 produces a coverage mask + fit-honesty layer that is the **single source of truth for "where the surface is real."** Phases 9/10/11 may not compute, display, or email a value in an uncovered grid cell. Hard dependency chain: 9 reuses 8's mask and reads `surface_history`; 10 reads 9's parquet store; 11 surfaces both. **Cut, not deferred:** PCA, SVI/SABR calibration — verify the surface, don't re-calibrate it.

- [ ] **Phase 8: Surface Validation (the gate)** — coverage mask, fit residuals, documented smoothing, no-arb checks (report-only), shared `rbf_grid` helper, dashboard readout
- [ ] **Phase 9: Surface Evolution Engine** — ΔIV decomposition (level/rms/skew/term) over 1/5/20 trading-day horizons, idempotent parquet, non-blocking daily pass, cross-ticker, backfill
- [ ] **Phase 10: Dashboard Restructure (local-only)** — 5→4 tabs, merge Skew+Term, remove carry/RR-history/bar charts, stored-vs-stored compare, evolution time-series, restrained palette, 3D retained
- [ ] **Phase 11: Richer Daily Report** — kaleido spike → 3D surface + ΔIV PNG attachments (pinned camera), content priority surfaces>walls>OI>gamma, clean formal aesthetic, narrative leads with 5-day horizon

## Phase Details

<details>
<summary>✅ Phase 6 & 7 details (v3.2 — closed)</summary>

### Phase 6: Whole-Chain Computation Engine
**Goal**: Pipeline computes all institutional vol metrics from the chain — 25Δ skew per expiry, ATM term structure, RV20/VRP carry — and surface is stripped of GEX overlays. Computation exists before display.
**Depends on**: Phase 5
**Success Criteria** (what must be TRUE):
  1. `gex/vol_metrics.py` exists with pure functions: `compute_skew_25d()`, `compute_term_structure()`, `compute_rv20()`, `compute_vrp()`
  2. `vol_surface_data()` returns clean OTM IV scatter; `plot_vol_surface()` accepts no GEX overlay parameters
  3. `compute_ticker()` returns dict containing `skew`, `term_structure`, `rv20`, `vrp` keys
  4. Parquet snapshots include `rv20` and `vrp` columns; old snapshots load without error
  5. `compute_surface_slopes()` no longer called anywhere (dead code removed)
  6. Dashboard no longer shows "Hedge Sh" row or "% vs ZGL" line
**Plans**: 4/4 complete

### Phase 7: Institutional Dashboard Rendering
**Goal**: Dashboard presents as a whole-chain vol diagnostics tool with clear modules. PM can answer cost-of-protection and vol-carry questions directly.
**Depends on**: Phase 6
**Success Criteria** (what must be TRUE):
  1. Surface tab: clean 3D IV surface, no GEX overlays, viridis colorscale
  2. Skew tab: front/second-month 25Δ put-call skew + rolling 30-day history
  3. Term Structure tab: ATM IV by expiry line chart with restrained classification
  4. Carry tab: IV30 vs RV20 + VRP spread with rolling history
  5. Flow Context tab: GEX/net gamma/ZGL with explicit microstructure header
  6. No deterministic language anywhere on dashboard
**Plans**: 2/2 complete
**UI hint**: yes

</details>

### Phase 8: Surface Validation (the gate)
**Goal**: Prove the interpolated vol surface isn't overfit. Produce a coverage mask + fit-honesty layer that becomes the single source of truth for "where the surface is real" — and that every downstream phase imports. Where there's no quote support, the surface shows an honest NaN hole, not fabricated IV.
**Depends on**: Phase 7 (v3.2 surface render)
**Requirements**: VALID-01, VALID-02, VALID-03, VALID-04, VALID-05, VALID-06
**Success Criteria** (what must be TRUE):
  1. The RBF interpolation exists as one shared `analytics.rbf_grid` helper consumed by the surface render, the diagnostics, and (later) the evolution engine — the two duplicated copies are gone, and the surface renders identically to before (regression-checked).
  2. A coverage mask (convex-hull / kNN over real quote locations) flags every grid cell with no nearby quote; unsupported cells render as honest NaN holes, and the mask is exported as the single artifact downstream phases consume.
  3. Per-ticker fit quality — RMSE and max residual (pp) of the RBF against input quotes — is computed headless in `compute_ticker` and persisted daily to the snapshot store.
  4. The `smoothing` parameter lives in `config.py` with a documented sensitivity sweep justifying the chosen value (no unexplained magic number).
  5. No-arbitrage checks (calendar-spread total-variance monotonicity + butterfly convexity) report PASS/FAIL and violation locations — and never auto-repair the surface.
  6. Surface coverage % and fit RMS are visible in the Streamlit dashboard, so the user can see at a glance whether today's surface is trustworthy.
**Plans**: 4 plans
- [ ] 08-01-PLAN.md - shared rbf_grid helper + coverage_mask + config constants (regression-checked foundation)
- [ ] 08-02-PLAN.md - apply coverage_mask to surface render (honest NaN holes) + clip instrumentation
- [ ] 08-03-PLAN.md - headless fit diagnostics + surface-coherence checks + snapshot persistence + VALID-04 reword
- [ ] 08-04-PLAN.md - surface_sweep.py (smoothing + k) + config docstrings + Streamlit raw-number trust readout
**UI hint**: yes

### Phase 9: Surface Evolution Engine
**Goal**: Build the "calculus of the surface" — how it moves over time, decomposed into interpretable scalars and accumulating daily. Every delta is computed only where both days have real quote support, reusing Phase 8's mask, so movement is never manufactured in an interpolated corner.
**Depends on**: Phase 8 (reuses the coverage mask + `rbf_grid`; reads `surface_history`)
**Requirements**: EVOL-01, EVOL-02, EVOL-03, EVOL-04, EVOL-05, EVOL-06
**Success Criteria** (what must be TRUE):
  1. A `surface_evolution` module decomposes today-vs-prior ΔIV into four scalars on the intersected mask of both days: level (mean ΔIV), rms (total movement), skew-change (put-wing vs call-wing), term-change (front vs back).
  2. The comparison runs at 1, 5, and 20 trading-day horizons, each resolved against actually-stored sessions via `surface_history.nth_trading_day_back` (not calendar arithmetic) and labelled with the real prior date.
  3. Evolution metrics persist to `out/surface_evolution.parquet`, idempotent on (date, ticker, horizon), accumulating forward.
  4. Evolution runs automatically as a non-blocking second pass in `run_daily` after the snapshot is saved — a failure there never blocks the email.
  5. Surface-change is comparable across SPY/QQQ/IWM so divergence (e.g. IWM moving alone) is visible, and a backfill routine retro-computes evolution from existing `surface_history` so the dashboard isn't empty on first use.
**Plans**: TBD

### Phase 10: Dashboard Restructure (local-only)
**Goal**: Restructure the LOCAL-only Streamlit dashboard around the surface calculus — fewer, clearer tabs; remove the noise; make the dashboard useful on accumulated history without a live fetch; show coverage holes honestly.
**Depends on**: Phase 9 (reads `out/surface_evolution.parquet` via `load_evolution`)
**Requirements**: VIEW-01, VIEW-02, VIEW-03, VIEW-04, VIEW-05
**Success Criteria** (what must be TRUE):
  1. Tabs collapse from 5 to 4 — Skew and Term Structure merge into one tab reframed around the surface calculus.
  2. The carry/VRP block (which lives *inside* the Term tab — there is no standalone Carry tab), the 25Δ risk-reversal history chart, and the strike-GEX bar charts are removed (data over bar charts).
  3. The surface comparison view can difference two *stored* dates (not only today-live vs stored), so it works on accumulated history without a live fetch.
  4. A surface-evolution view charts level / rms / skew-change / term-change over time, selectable by horizon (1/5/20).
  5. The dashboard uses a restrained, professional palette; coverage holes are shown honestly; the interactive 3D surface is retained here.
**Plans**: TBD
**UI hint**: yes

### Phase 11: Richer Daily Report
**Goal**: Deliver the surface and its evolution in a clean, formal daily email. Open with a kaleido smoke-test spike to de-risk PNG embedding; surface the highest-value content (surfaces, then walls, then OI, then gamma); lead the narrative with the 5-day horizon.
**Depends on**: Phase 9 (evolution scalars) + Phase 8 (diagnostics). Phase 10 informs the consistent palette/camera.
**Requirements**: RPT-01, RPT-02, RPT-03, RPT-04, RPT-05
**Success Criteria** (what must be TRUE):
  1. A kaleido smoke-test spike (`kaleido>=1.0,<2.0` + one-time `get_chrome`) confirms PNG export works on the target Windows machine *before* embedding is committed; if it fails, HTML-artifact attachment is the documented, working fallback.
  2. The daily email attaches the surface and ΔIV-surface images as 3D renders consistent with the Streamlit views, using a pinned camera angle so the static frame is readable.
  3. Report content is prioritised surfaces > put/call walls > OI > gamma, with open interest surfaced as data (currently absent from the email).
  4. The report reads as a clean, formal business document — restrained palette consistent with the dashboard, no garish colours, no decorative noise.
  5. Evolution scalars appear in the report and the narrative leads with the 5-day horizon (1-day ΔIV is mostly expiry-roll + quote noise — the hazard that retired the v3.1 vs-yesterday badge).
**Plans**: TBD

---

## Backlog (999.x) — Deferred Pending Research & Validation

### 999.1: Charm by DTE Chart (Research Required)
**Status:** ⏸️ **PARKED** — Charm calculation on American options lacks mathematical rigor.

### 999.2: Critical-Path Test Coverage (Deferred)
**Status:** ⏸️ **BACKLOG** — Deferred pending 999.1 outcome.

### 999.3: Pre-Distribution Hardening (Partial)
**Status:** 🟡 **PARTIAL** — 50% complete via 2026-05-11 out-of-phase work.

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
| 7. Institutional Dashboard Rendering | v3.2 | 2/2 | Complete | 2026-05-29 |
| 8. Surface Validation (the gate) | v3.3 | 0/? | Not started | - |
| 9. Surface Evolution Engine | v3.3 | 0/? | Not started | - |
| 10. Dashboard Restructure | v3.3 | 0/? | Not started | - |
| 11. Richer Daily Report | v3.3 | 0/? | Not started | - |

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
