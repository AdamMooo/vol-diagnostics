# Options Quant — GEX Analysis Platform

*Last updated: 2026-05-06 after v3.0 milestone*

## What This Is

A dealer gamma exposure (GEX) analysis platform. Computes dealer positioning across SPY/QQQ/IWM from live options chains (yfinance), identifies gamma regime (positive/negative/neutral), locates structural levels (zero-gamma, call wall, put wall), and delivers daily context via both a scheduled HTML email and an interactive Streamlit dashboard.

## Core Value

Given today's dealer positioning across SPY/QQQ/IWM — what regime are we in, how much dealer hedging flow will a 1% move generate, and where are the structural levels that matter? One-sentence answer per ticker, full analytics on demand.

## Runtime & Stack

- **Runtime:** local Python venv. `python -m gex.run_daily` → email. `streamlit run streamlit_app.py` → dashboard.
- **Data:** yfinance options chains (live). Snapshots: `out/gex_snapshots.parquet`.
- **Stack:** pandas, numpy, scipy, matplotlib, yfinance, pyarrow, streamlit, plotly.
- **Tests:** pytest, 77 tests green.

## Key Files

| File | Purpose |
|------|---------|
| `gex/greeks_engine.py` | BS gamma, vanna, charm — vectorised with 0DTE guard |
| `gex/exposure_engine.py` | GEX/VEX/CHEX by strike; delta-hedge flow |
| `gex/analytics.py` | Summary dict, matplotlib charts |
| `gex/validation.py` | Parquet snapshot store, load_yesterday, load_history |
| `gex/report.py` | HTML email body builder |
| `gex/run_daily.py` | Daily orchestrator — 3 tickers, save + send |
| `streamlit_app.py` | Interactive dashboard — Live + Historical tabs |
| `out/gex_snapshots.parquet` | Historical GEX/VEX snapshot store |

## Requirements

### Validated

- ✓ GRKS-01/02/03/04 — Vanna + Charm in BS engine, `add_greeks()` enriches chain DF, 0DTE guard — v3.0
- ✓ EXP-01/02/03/04 — VEX + CHEX by strike, net scalars in `summarise()`, `vanna_exposure` in parquet — v3.0
- ✓ FLOW-01/02/03/04 — Delta-hedge $/1%, vs-yesterday classification, email table columns — v3.0
- ✓ DASH-01/02/03/04/05/06 — Streamlit app: regime cards, chart, expanders, COM isolation — v3.0
- ✓ HIST-01/02/03/04 — Historical tab: ZGL trend, regime persistence, streak counter, event study — v3.0

### Active

- [ ] Phase 3 UAT sign-off — 4 pending human test scenarios from 03-HUMAN-UAT.md
- [ ] Phase 3 verification human items — 03-VERIFICATION.md human_needed items

### Out of Scope

| Feature | Reason |
|---------|--------|
| Bloomberg data swap | One-class change in data_loader.py — deferred to v4.x |
| Vomma / second-order vol Greeks | Less PM-readable than vanna |
| New GEX signals / predictive scoring | Holm-Bonferroni bar is high |
| Sleeve allocation framework (v2.x) | Separate track |
| Automated Task Scheduler / Streamlit autostart | After PM desk validates dashboard |
| Charm by DTE bucket chart | Differentiator, v3.1 candidate |
| Live intraday refresh | yfinance rate limits risky at launch |
| Dispersion / implied-correlation | Out of scope |
| Live execution / order routing | Research tool only |

## Strategic Decisions

| Date | Decision | Why |
|------|----------|-----|
| 2026-05-06 | GSD sign convention: calls +, puts − | SpotGamma/retail standard. Positive net GEX = dealers net long gamma = stabilising |
| 2026-05-05 | Vanna over Vomma | Vanna (∂delta/∂vol) translates to dealer rehedging flow — PM-readable. Vomma is not. |
| 2026-05-05 | Streamlit additive — email pipeline preserved | Email is scheduled and working; dashboard adds interactivity without breaking existing workflow |
| 2026-05-05 | No new data sources in v3.0 | yfinance + parquet snapshots only. Bloomberg is a one-class swap when team greenlights. |
| 2026-05-05 | New milestone v3.0 — GEX Interactive Dashboard | GEX POC is production-grade; direction is depth (Greeks, flow, dashboard) not more signals |

## Known Open Items

| Item | Description | Status |
|------|-------------|--------|
| Phase 3 UAT | 03-HUMAN-UAT.md: 4 pending scenarios | Deferred to v3.1 |
| Phase 3 verification | 03-VERIFICATION.md: human_needed | Deferred to v3.1 |
| Coverage gaps | data_loader, report, emailer, run_daily, analytics charts — zero test coverage | Tech debt, v3.1 |
| American-style BS | IWM uses European model — acknowledged with early exercise risk signal | Acceptable for POC |
| NDX skew identity | NDX/SPX share same CBOE SKEW signal in sleeve framework | v2.x track — not blocking |

## Evolution

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---

## Previous Milestones

### v3.0 — GEX Interactive Dashboard (shipped 2026-05-06)
Second-order Greeks (Vanna, Charm), VEX/CHEX exposure, delta-hedge flow, vs-yesterday labels, Streamlit dashboard (Live + Historical tabs). 10 plans, 77 tests, 2 days.

### v2.1 — POC Delivery & Validation (closed 2026-05-05)
Delivered sleeve allocation HTML report (`build_report.py`) to quant team. GEX POC shipped as parallel track (commit 972dc99).

### v2.0 — Sleeve Allocation Framework: Engine Build (closed 2026-05-04)
Seven modules, 74 tests, Holm-Bonferroni rigor. 0 of 30 bucket-mean tests survived correction — honest finding, not failure.

### v1.0 — Regime-Aware Fund Intelligence Notebook (pivoted 2026-04-30)
HMM GMM diagnostic on SPX. Pivoted because it never touched options-pricing data.
