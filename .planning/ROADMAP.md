# Roadmap: Options Quant — v2.1 POC Delivery & Validation

> **Active milestone v2.1 (started 2026-05-04).** v2.0 engine build is closed and archived under `.planning/phases-archive/v2.0-engine/`. v1.0 HMM is closed and archived under `.planning/phases-archive/v1.0-hmm/`. Phase numbering restarts at 1.

## Overview

v2.1 takes the v2.0 engine (signals, sleeve backtest, decision dashboard, statistical rigor) and prepares it for evaluation by the quant team. Deliverable is a self-contained HTML report (`build_report.py`) on free CBOE+FRED data. Phase 1 is complete; future phases are driven by team feedback.

## Phases

- [x] **Phase 1: POC Delivery & Calibration** — HTML report, WALKTHROUGH.md, cleanup of forecasting drift. **COMPLETE.**
- [x] **Post-phase: Bayesian Reframe** — Conditional summary leads report; equity chart removed; Section E unconditional caveat. **COMPLETE.**
- [ ] **Phase 2: Short-Vol Environment Historical Distributions** — `section_short_vol_environment()` in `dashboard.py`: percentile distributions (10/25/50/75/90) of three market-level metrics by signal quartile. No sleeve labels, no strategy ranking. PM reads raw environmental outcomes and draws their own conclusion about book risk.
- [ ] **Phase 3+:** Open — data quality fixes (NDX skew identity), Tier 2 features (GEX/OI), or productionizing based on team feedback.

---

## Phase Details

### Phase 1: POC Delivery & Calibration — COMPLETE
**Goal:** Deliver a quant-readable POC to the quant team for async review followed by a meeting.

**Shipped:**
- `build_report.py` — HTML report generator producing `out/sleeve_report_YYYYMMDD.html`; sections A–H; charts as base64 data URIs
- Section D reframed — forward-realized environment (signals) after analog match; K-NN logic untouched
- `validate.py` deleted (forecasting drift)
- `WALKTHROUGH.md` — per-section quant guide; Holm framing; two team questions
- Chart styling — CHART_STYLE dict, regime shading, consistent palette

**Note on scope:** Deliverable is the HTML report, not a Jupyter notebook. Bloomberg calibration deferred; free-data POC ships as-is.

**Plans:** 01-02, 01-03, 01-04, 01-05, 01-06 (01-01 BloombergCon dropped as not needed for free-data delivery)

### Post-phase: Bayesian Reframe — COMPLETE (2026-05-04)
**Goal:** Remove the misleading unconditional narrative; add explicit conditional bridge from today's signals to historical sleeve returns.

**Shipped:**
- `section_today_conditional()` in `dashboard.py` — for each bucketed signal, today's quartile + mean monthly return per sleeve in that quartile; no new math (same bucket computation as Section C)
- `_equity_chart()` deleted from `build_report.py` — growth-of-$1 chart was loudest unconditional strategy-ranking signal
- Section order: conditional summary → A → signal chart → B → C → D → E → G → H
- Section E: "Unconditional reference class over 2010–2026 (a sustained equity bull market)" caveat
- `build_dashboard()` updated — `run.py` parity
- WALKTHROUGH.md updated — conditional summary section entry, updated sections table, Section E description

---

## Progress

| Phase | Plans | Status | Completed |
|-------|-------|--------|-----------|
| 1. POC Delivery & Calibration | 5 plans (01-01 dropped) | COMPLETE | 2026-05-04 |
| Post-phase: Bayesian Reframe | inline (no GSD phase) | COMPLETE | 2026-05-04 |
| 2. Short-Vol Environment Historical Distributions | 2 plans | OPEN | — |
| 3+. Post-feedback | TBD | OPEN | — |

### Phase 2: Short-Vol Environment Historical Distributions — OPEN
**Goal:** Add a signal-conditioned historical distribution section that shows what the short-vol environment actually did when each signal was in each quartile. PM uses this to calibrate whether current conditions are permissive or hostile to their existing short-convexity book — not to pick a strategy.

**Deliverables:**
- `dashboard.py` — `section_short_vol_environment(sigs, panels)`: percentile table (10/25/50/75/90 + n) for three metrics × four signals × four quartiles
- `build_report.py` — new section in HTML output; `section_market_outcomes` removed

**Three metrics (market-level, no strategy labels):**
1. Realized vol / implied vol at period open — did the vol-selling premise hold?
2. Absolute monthly SPX return — how violent were the moves? (gamma exposure proxy)
3. IV change over the period — did vol spike further? (vega risk proxy)

**Constraints:** Single-signal quartile slices only. Always show n. No "best sleeve" language. No Holm discussion. Frame as "historical calibration only, not a forecast."

**Depends on:** Phase 1 (complete)

**Plans:**
- [ ] 02-01-PLAN.md — implement section_short_vol_environment in dashboard.py
- [ ] 02-02-PLAN.md — wire into build_report.py; remove section_market_outcomes from HTML

---

## Known Open Items (pre-Phase 2)

| Item | Description | Priority |
|------|-------------|----------|
| NDX skew identity | NDX/SPX share the same CBOE SKEW signal — readings always identical | Fix before team meeting |
| NDX iv90_atm synthesis | Uses SPX term-structure ratio — same data accuracy category | Fix before team meeting |
| Bloomberg calibration | Replace synthesized 90mny IV with `30DAY_IMPVOL_90.0%MNY_DF` | Pending team greenlight |
| UAT | Open `out/sleeve_report_YYYYMMDD.html` in browser; verify conditional summary | Now |

---

## Closed milestones

### v2.0 — Sleeve Allocation Framework: Engine Build
Closed 2026-05-04. Engine functionally complete on free CBOE+FRED data with statistical rigor (Holm correction, block bootstrap, 74 tests). Phases archived under `.planning/phases-archive/v2.0-engine/`.

### v1.0 — Regime-Aware Fund Intelligence Notebook (HMM)
Closed 2026-04-30 without ship. Pivoted to v2.0. `hmm.ipynb` preserved as legacy single-fund diagnostic. Phases archived under `.planning/phases-archive/v1.0-hmm/`.
