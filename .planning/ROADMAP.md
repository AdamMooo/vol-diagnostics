# Roadmap: Options Quant — GEX Analysis Platform

*Last updated: 2026-06-22 · v3.3 SHIPPED · v3.4 SHIPPED · v3.5 active (Phases 15–19; 15–16 done) · v4.0 planned*

## Milestones

- ✅ **v3.0 GEX Interactive Dashboard** — Phases 1–4 (shipped 2026-05-06)
- ✅ **v3.1 Hardening & Cleanup** — Phase 5 + out-of-phase refactor (shipped 2026-05-06 + 2026-05-11)
- ✅ **v3.2 Vol Surface Reframe** — Phases 6–7 (computation engine + institutional dashboard rendering)
- ✅ **v3.3 Surface Evolution & Daily Intelligence** — Phases 8–11 (shipped 2026-06-01)
- ✅ **v3.4 Email-First Daily Report Polish** — Phases 12–14 (shipped 2026-06-02)
- 🚧 **v3.5 Index Vol-Context Rebuild** — Phases 15–19 (active; 15–16 done)
- **v4.0 Cloud Hosting** — VPS deploy + git workflow + data migration (planned)
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

### v3.4 Email-First Daily Report Polish (Superseded by v3.5 — Phase 14 unexecuted)

**Milestone Goal:** Curate the daily email into a tight single-snapshot diagnostic, unify the email and dashboard around one canonical card, replace the static surface PNGs with 1-day ΔIV surfaces, and gate accumulation-dependent UI until enough sessions exist. Every scope item is single-snapshot or near-it.

- [x] **Phase 12: Canonical Card** — Single source-of-truth card shared by email + dashboard; VRP, scalar deltas, wall labels (completed 2026-06-01)
- [x] **Phase 13: 1-Day ΔIV Email PNGs** — Replace static surface + 5d ΔIV PNGs with one 1d ΔIV surface PNG per ticker (completed 2026-06-02)
- [~] **Phase 14: Accumulation Gating** — SUPERSEDED by v3.5 Phase 18. Gating intent (GATE-01/02) carried forward verbatim into Phase 18; not executed standalone.

---

### v3.5 Index Vol-Context Rebuild (Planned)

**Milestone Goal:** Re-aim the dashboard at the index income-sleeve PM — lead with VRP percentile and VIX term-structure regime, reorganize surfaces and GEX beneath them.

- [x] **Phase 15: Vol-Index Data Layer** — Fetch + cache CBOE vol-index daily CSVs (VIX/VXN/RVX + siblings); Bloomberg-swappable isolated module (completed 2026-06-05)
- [x] **Phase 16: VRP Percentile** — VRP (vol-index − RV20) ranked as a percentile against its own history; internally consistent series, lookback labeled
- [x] **Phase 16.5: OI Depth Expansion** — Richer open-interest analytics: expiry concentration, day-over-day strike-level OI change, put/call split per expiry, parameter-free large-block flagging; Positioning tab + email summary
 (completed 2026-06-22)
- [ ] **Phase 17: Term-Structure Regime** — SPY VIX9D/VIX/VIX3M raw ratio; QQQ/IWM graceful degradation; no hidden scoring
- [x] **Phase 17.1: Convexity & Expected Move** (INSERTED) — front-expiry ATM-straddle expected move + 25Δ butterfly on the page-1 card; descriptive only
 (completed 2026-06-23)
- [ ] **Phase 18.1: Dashboard Trust and Clarity Hardening** (INSERTED) — compact trust-tagged scorecard, table-first OI context, 14-DTE primary dealer-impact framing, methods quick/deep trim, and evolution plain-English summary
- [ ] **Phase 18: 3-Page Reorg + Email Parity + Gating** — Dashboard reorganized to 3 pages (VRP+term+snapshot / surfaces / GEX); page-1 snapshot tied to canonical card; accumulation-dependent elements gated
- [ ] **Phase 19: Data Health & Continuity** — Health-check CLI for all parquet stores, Task Scheduler re-verify, monthly SOP documented in CLAUDE.md

---

### v4.0 Cloud Hosting (Planned)

**Milestone Goal:** Move the dashboard off the local Windows machine onto a VPS or cloud VM — runs 24/7, accessible from any computer. Code deploys via git pull from personal GitHub; historical parquet data migrated via volume mount; cron replaces Windows Task Scheduler. No code changes required to the app itself.

- [ ] **Phase 20: VPS Setup + Code Deploy Workflow** — Provision server, configure git remote, automated deploy script
- [ ] **Phase 21: Data Migration + Cron Scheduler** — Migrate `out/` parquet history, wire cron job for daily run
- [ ] **Phase 22: Multi-Machine Access + Hardening** — Auth layer (password guard already in app.py), HTTPS, stable URL

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

- [x] 13-01-PLAN.md — Swap PNG block: 1-day ΔIV per ticker, delete static surface + 5d ΔIV PNGs, add tests

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

### Phase 15: Vol-Index Data Layer

**Goal**: The system can fetch, parse, and cache CBOE vol-index daily history for all index-relevant symbols (VIX/VXN/RVX plus the VIX9D/VIX3M term siblings that CBOE actually publishes) in one isolated module — so VRP and term-structure computations downstream never touch a data source directly.
**Depends on**: None (foundation phase; Phase 14 superseded, not a dependency)
**Requirements**: VIDX-01, VIDX-02
**Success Criteria** (what must be TRUE):

  1. Running the data-layer module fetches and caches VIX, VXN, RVX, VIX9D, and VIX3M history from the free CBOE CDN CSVs; a second run uses the cache and makes no network call.
  2. The module exposes a single `load_vol_index(symbol)` function (or equivalent); no downstream metric code imports from `requests` or touches a CSV path directly.
  3. Swapping the data source to Bloomberg requires changes only inside this module — no downstream edits needed (verified by inspection, not runtime).
  4. A smoke test confirms the returned DataFrame has a date index and a closing-price column for each symbol, with no silent all-NaN result on a successful fetch.

**Plans**: 2 plans

Plans:
**Wave 1**

- [x] 15-01-PLAN.md — gex/vol_index.py: fetch, parse, persist, load accessor + DEFAULT_VOL_INDICES in config.py

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 15-02-PLAN.md — run_daily.py integration + test_vol_index.py (VIDX-01/VIDX-02 coverage)

---

### Phase 16: VRP Percentile

**Goal**: The PM can see today's VRP (vol-index implied vol minus RV20 realized vol) for each index together with its percentile rank against its own history, computed from one internally-consistent series and labeled with the lookback window.
**Depends on**: Phase 15
**Requirements**: VRP-01, VRP-02, VRP-03
**Success Criteria** (what must be TRUE):

  1. The dashboard and email display today's VRP scalar for SPY, QQQ, and IWM (vol-index minus RV20).
  2. Each VRP value is accompanied by its percentile rank (e.g. "74th percentile, 252-day lookback") with the lookback window explicitly labeled.
  3. The percentile is computed using only the vol-index series for both the current reading and its history — snapshot IV30 is never mixed into the VRP history (verifiable by reading the computation path).
  4. When fewer sessions exist than the lookback window, the percentile is either omitted or labeled with the actual available count — never silently computed on a thin sample without disclosure.

**Plans**: 2/2 complete (16-01-PLAN.md, 16-02-PLAN.md)

---

### Phase 16.5: OI Depth Expansion

**Goal**: The Positioning tab and daily email surface richer open-interest analytics — concentration by expiry, day-over-day strike-level OI change, put/call OI split per expiry, and parameter-free large-block identification — all raw labeled numbers with no scoring or categorical calls.
**Depends on**: Phase 16
**Requirements**: OI-01, OI-02, OI-03, OI-04
**Success Criteria** (what must be TRUE):

  1. The Positioning tab shows OI concentration by expiry: top expirations ranked by total OI (calls + puts), auto-scaled to the chain, no hand-tuned absolute cutoff.
  2. Day-over-day OI change by strike is displayed — net change from prior chain snapshot; when no prior snapshot exists, the column shows "–" rather than NaN or an error.
  3. Put/call OI ratio is shown per expiry (not just overall), labeling which expirations skew protective vs speculative.
  4. Large OI blocks are flagged parameter-free — strikes in the top decile of total OI within 90 DTE — threshold auto-scales to the chain without a hand-tuned absolute cutoff.
  5. The daily email includes a text summary of the top-expiry OI concentration per ticker (top 3 expirations by OI, with put/call split).

**Plans**: 3 plans

**Wave 1**

- [x] 16.5-01-PLAN.md — Engine layer: oi_history.py store, expiry_oi() aggregation, is_top_decile on s_df

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 16.5-02-PLAN.md — Dashboard display: OI by Expiry expander + large-block annotation on OI chart
- [x] 16.5-03-PLAN.md — Email OI table, run_daily store write, tests

---

### Phase 17: Term-Structure Regime

**Goal**: The PM can see the SPY VIX term structure (VIX9D/VIX/VIX3M) as raw ratios indicating contango or backwardation, and QQQ/IWM show whatever CBOE actually publishes for them without fabricating a term structure.
**Depends on**: Phase 15
**Requirements**: TERM-01, TERM-02
**Success Criteria** (what must be TRUE):

  1. The SPY display shows two raw ratios — VIX9D/VIX and VIX/VIX3M — with no categorical label or hidden scoring; the PM reads the number and judges.
  2. For QQQ and IWM, the display shows whichever term-structure siblings CBOE publishes; if only the 30-day level (VXN/RVX) is available, the term-structure row is omitted or marked "N/A — single point only" rather than fabricated.
  3. A one-time verification step during the phase confirms which CBOE sibling symbols actually exist for VXN/RVX (e.g. VXN9D, VXST) and documents the finding in CLAUDE.md.

**Plans**: TBD

---

### Phase 17.1: Convexity & Expected Move (INSERTED)

**Goal**: The PM sees two additional descriptive options-math reads on the page-1 card for SPY/QQQ/IWM — (1) the front-expiry implied expected move as a ±% range (ATM straddle implied), and (2) the 25Δ butterfly (smile convexity = ½(25Δput_iv + 25Δcall_iv) − ATM_iv) beside the existing 25Δ risk reversal — completing the smile shape (direction + tail demand). Raw labeled numbers only; no scoring, no categorical labels, no trade prescription.
**Depends on**: Phase 16
**Requirements**: EM-01, SHAPE-01
**Success Criteria** (what must be TRUE):

  1. The dashboard and email card display the front-expiry implied expected move for SPY/QQQ/IWM as a ±% (and/or ± price) range, with the expiry/DTE explicitly labeled.
  2. The card displays the front-month 25Δ butterfly alongside the existing 25Δ risk reversal, labeled, computed as ½(25Δput_iv + 25Δcall_iv) − ATM_iv from the values compute_skew_25d / compute_term_structure already produce.
  3. The butterfly carries percentile context vs its own history where enough sessions exist, reusing the Phase 16 percentile + cold-start gating pattern; below the lookback it is omitted or labeled with the actual count — never a silent thin sample.
  4. No realized-vol cone, risk-neutral density, put/call ratio, or VVIX is added — scope is exactly the two reads above.

**Plans**: 2 plans

Plans:

- [x] 17.1-01-PLAN.md — Engine + persistence wiring for model-free EM and 25Δ fly percentile history
- [x] 17.1-02-PLAN.md — Canonical card rendering for IV30/EM + 25Δ Fly and 17.1-MATH reference

### Phase 18: 3-Page Reorg + Email Parity + Gating

**Goal**: The dashboard is reorganized into three pages (page 1: VRP + term structure + snapshot; page 2: surfaces; page 3: GEX) with nothing deleted; the page-1 snapshot renders numbers identical to the daily email via the shared canonical card; and all history-dependent UI elements on page 1 are gated behind session-count guards.
**Depends on**: Phase 16, Phase 17, Phase 17.1
**Requirements**: VIEW-06, VIEW-07, CUT-02, PAR-01, GATE-01, GATE-02
**Success Criteria** (what must be TRUE):

  1. The dashboard opens to page 1 showing VRP percentile, term-structure ratios, and the snapshot card; pages 2 and 3 contain the vol surface and GEX panels respectively — nothing is deleted, only reorganized.
  2. The page-1 snapshot card renders the same field values as the daily email for the same session; a single canonical card definition drives both surfaces.
  3. The 3D vol surface does not appear on page 1; it lives on page 2 alongside other surface content.
  4. Page-1 elements that require accumulated history (VRP percentile, term-structure percentile) display a clear "needs ≥N sessions" caption rather than NaN or an empty widget when insufficient history exists.
  5. The email omits history-dependent content rather than rendering empty/NaN rows when required history is absent, and the send never errors on cold-start.

**Plans**: TBD
**UI hint**: yes

---

### Phase 18.1: Dashboard Trust and Clarity Hardening (INSERTED)

**Goal**: Harden dashboard/email trust framing and clarity (compact trust-tagged scorecard, OI table-first context, 14-DTE primary dealer-impact framing, quick/deep methods, and plain-English evolution summary) without adding new signal domains.
**Requirements**: D-01, D-02, D-03, D-04, D-05, D-06, D-07, D-08, D-09, D-10, D-11, D-12
**Depends on**: Phase 17.1
**Plans**: 3 plans

Plans:
- [x] 18.1-01-PLAN.md
- [x] 18.1-02-PLAN.md
- [ ] 18.1-03-PLAN.md

### Phase 19: Data Health & Continuity

**Goal**: A single CLI command audits all parquet stores for freshness, row count, date gaps, and schema consistency; the result is clean on a healthy setup. Task Scheduler is re-verified and a monthly SOP is documented in CLAUDE.md so the accumulation engine keeps running reliably.
**Depends on**: Phase 18
**Requirements**: HEALTH-01, HEALTH-02
**Success Criteria** (what must be TRUE):

  1. `python -m gex.health_check` prints a table: store name, row count, first/last date, gap count vs NYSE calendar, and a PASS/WARN flag per store.
  2. Running it on the current setup produces no WARN flags.
  3. Task Scheduler re-verified: battery flags off, RestartCount=2, last-result=0 confirmed; any fix committed and documented.
  4. CLAUDE.md documents the monthly-check SOP: run health_check, verify Task Scheduler last-result, confirm latest parquet date is within 2 trading days.

**Plans**: TBD

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
| 13. 1-Day ΔIV Email PNGs | v3.4 | 1/1 | Complete    | 2026-06-02 |
| 14. Accumulation Gating | v3.4 | — | Superseded → Phase 18 | - |
| 15. Vol-Index Data Layer | v3.5 | 2/2 | Complete    | 2026-06-05 |
| 16. VRP Percentile | v3.5 | 2/2 | Complete | 2026-06-16 |
| 16.5. OI Depth Expansion | v3.5 | 3/3 | Complete    | 2026-06-22 |
| 17. Term-Structure Regime | v3.5 | 0/TBD | Not started | - |
| 18. 3-Page Reorg + Email Parity + Gating | v3.5 | 0/TBD | Not started | - |
| 19. Data Health & Continuity | v3.5 | 0/TBD | Not started | - |

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
