# Options Quant — GEX Interactive Dashboard

*Last updated: 2026-05-05 — v3.0 milestone started*

## What This Is

A dealer gamma exposure (GEX) analysis platform. The GEX module computes dealer positioning across 10 liquid ETFs from live options chains (yfinance), identifies gamma regime (positive/negative/neutral), locates structural levels (zero-gamma, call wall, put wall), and delivers daily context for the PM desk.

**v3.0 direction:** Extend the GEX module from a daily HTML email into a live Streamlit dashboard with second-order Greeks (Vanna, Charm) and PM-facing flow analytics (delta-hedge $/1%, vs-yesterday regime comparison).

## Core Value

Given today's dealer positioning across SPY/QQQ/IWM — what regime are we in, how much dealer hedging flow will a 1% move generate, and where are the structural levels that matter? One-sentence answer per ticker, full analytics on demand.

## Current Milestone: v3.0 — GEX Interactive Dashboard

**Goal:** Add second-order Greeks and PM flow metrics to the GEX engine, then surface them in an interactive Streamlit dashboard with historical context.

**Target features:**
- Vanna + Charm via existing Black-Scholes engine; VEX (Vanna Exposure) aggregated like GEX
- PM flow metrics: delta-hedge $/1% move + vs-yesterday regime comparison
- Streamlit app: colored regime cards, cross-asset chart, per-ticker expanders
- Historical tab: zero-gamma level trend, regime persistence table, event study output

**Key constraints:**
- Email pipeline (run_daily.py → Outlook COM) stays intact — Streamlit is additive
- No new data sources — yfinance + existing parquet snapshots only
- Phase 1→2→3→4 strict ordering (each builds on prior)

## Runtime & Stack

- **Runtime:** local Python venv. `python -m gex.run_daily` → email. `streamlit run streamlit_app.py` → dashboard.
- **Data:** yfinance options chains (live). Snapshots: `out/gex_snapshots.parquet`.
- **Stack:** pandas, numpy, scipy, matplotlib, yfinance, pyarrow, streamlit (Phase 3).
- **Tests:** pytest (gex unit tests, math correctness).

## Key Files

| File | Purpose |
|------|---------|
| `gex/greeks_engine.py` | BS gamma (+ vanna/charm in v3.0) |
| `gex/exposure_engine.py` | GEX computation and aggregation (+ VEX in v3.0) |
| `gex/analytics.py` | Summary dict, matplotlib charts |
| `gex/validation.py` | Parquet snapshot store, event study |
| `gex/report.py` | HTML email body builder |
| `gex/run_daily.py` | Daily orchestrator — 10 tickers, save + send |
| `streamlit_app.py` | Interactive dashboard (Phase 3 — new) |
| `out/gex_snapshots.parquet` | Historical GEX/VEX snapshot store |

## Strategic Decisions

| Date | Decision | Why |
|------|----------|-----|
| 2026-05-05 | New milestone v3.0 — GEX Interactive Dashboard | GEX POC is production-grade; direction is now depth (Greeks, flow analytics, dashboard) not more signals |
| 2026-05-05 | Streamlit additive — email pipeline preserved | Email is already scheduled and working; dashboard adds interactivity without breaking the existing workflow |
| 2026-05-05 | Vanna over Vomma as second-order Greek | Vanna (∂delta/∂vol) directly translates to dealer rehedging flow when vol spikes — PM-readable. Vomma is harder to explain. |
| 2026-05-05 | No new data sources in v3.0 | All four phases use only yfinance + parquet history. Bloomberg swap is a one-class change deferred to v4.x. |
| 2026-05-04 | GEX sign convention: calls +, puts − | SpotGamma/retail standard. Positive net GEX = dealers net long gamma = stabilising. |
| 2026-05-04 | Parquet store keyed on (date, ticker), idempotent | Prevents duplicate rows on reruns |

## Out of Scope (v3.0)

| Feature | Reason |
|---------|--------|
| Bloomberg data swap | One-class change deferred to v4.x — yfinance works for the POC |
| Vomma / second-order vol Greeks | Harder to explain to PMs than vanna; vanna story is cleaner |
| New GEX signals or predictive scoring | Holm-Bonferroni bar is high; flow-mechanics angle is more defensible |
| Sleeve allocation framework (v2.x) | Separate track; HTML report in `out/sleeve_report_*.html` preserved |
| Automated Task Scheduler activation | Manual run for POC; revisit after PM desk validates dashboard |
| Dispersion / implied-correlation | Out of scope for this project |
| Live execution / order routing | Research / decision-support only |

## Known Open Items

| Item | Description | Status |
|------|-------------|--------|
| NDX skew identity | NDX/SPX share same CBOE SKEW signal in sleeve framework | v2.x track — not blocking v3.0 |
| Bloomberg 90mny IV calibration | Sleeve framework only | v2.x track — not blocking v3.0 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---

## Previous Milestones

### v2.1 — POC Delivery & Validation (closed 2026-05-05)
Delivered sleeve allocation HTML report (`build_report.py`) to quant team. Bayesian reframe: conditional summary leads, equity chart removed, Section E caveat added. GEX POC shipped as parallel track (commit 972dc99).

### v2.0 — Sleeve Allocation Framework: Engine Build (closed 2026-05-04)
Seven modules, 74 tests, Holm-Bonferroni rigor. 0 of 30 bucket-mean tests survived correction — honest finding, not failure.

### v1.0 — Regime-Aware Fund Intelligence Notebook (pivoted 2026-04-30)
HMM GMM diagnostic on SPX. Pivoted because it never touched options-pricing data.
