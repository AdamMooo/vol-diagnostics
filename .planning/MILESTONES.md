# Milestones — Options Quant

## v3.0 — GEX Interactive Dashboard

**Shipped:** 2026-05-06
**Phases:** 1–4 | **Plans:** 10

### Delivered

Extended GEX from a daily email into a live Streamlit dashboard with second-order Greeks (Vanna, Charm), PM flow analytics (delta-hedge $/1%, vs-yesterday regime labels), and a historical context tab (ZGL trend, regime persistence, streak counters, event study).

### Key Accomplishments

1. Added Vanna + Charm to Black-Scholes engine with 0DTE guard; extended `add_greeks()` and 31 tests
2. VEX/CHEX by strike; `delta_hedge_flow` = net_gex / (spot × 0.01); vs-yesterday classification in email table
3. Streamlit app: regime cards, cross-asset chart, per-ticker expanders; COM isolation (no emailer import)
4. Historical tab: 30-day ZGL trend, regime persistence table, streak counter, event study (20-session gate)
5. 77 tests green across the full gex module

### Stats

- Timeline: 2026-05-05 → 2026-05-06 (2 days)
- Files changed: 73 | Lines changed: +6263 / −4566
- Total Python LOC: ~7,275

### Known Deferred Items at Close (2 — see STATE.md)

- Phase 3 UAT: 4 pending human test scenarios
- Phase 3 verification: human_needed items

### Archive

- Roadmap: `.planning/milestones/v3.0-ROADMAP.md`
- Requirements: `.planning/milestones/v3.0-REQUIREMENTS.md`

---

## v2.1 — POC Delivery & Validation

**Shipped:** 2026-05-05

Delivered sleeve allocation HTML report (`build_report.py`) to quant team. Bayesian reframe: conditional summary leads, equity chart removed, Section E caveat added. GEX POC shipped as parallel track (commit 972dc99).

---

## v2.0 — Sleeve Allocation Framework: Engine Build

**Shipped:** 2026-05-04

Seven modules, 74 tests, Holm-Bonferroni rigor. 0 of 30 bucket-mean tests survived correction — honest finding, not failure.

---

## v1.0 — Regime-Aware Fund Intelligence Notebook

**Shipped / Pivoted:** 2026-04-30

HMM GMM diagnostic on SPX. Pivoted because it never touched options-pricing data.

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
