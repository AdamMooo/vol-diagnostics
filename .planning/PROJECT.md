# Options Quant — GEX Analysis Platform

*Last updated: 2026-05-21 — v3.2 milestone started; PM-actionable positioning pivot*

## Current Milestone: v3.2 — Actionable Positioning Context

**Goal:** Transform GEX dashboard from mathematical showcase to PM-actionable positioning monitor — cut outputs that don't inform decisions, add context that does.

**PM use case:** "Should I pay up for protection right now, and what's the dealer-driven vol environment telling me about whether I need to?"

**Target features:**
- Positioning narrative — always-visible mechanical explanation of GEX sign (dampening vs amplifying)
- GEX percentile rank — today's net GEX vs trailing 30–90d history
- VRP (IV30 − RV20) — hedging cost context ("options rich/cheap")
- OI tilt — dollar-weighted put vs call OI, directional pressure
- Front skew gauge — percentile rank on card (term structure chart stays)
- Output cuts — remove non-decision-informing metrics, demote vol surface

## What This Is

A dealer gamma exposure (GEX) analysis platform. Computes dealer positioning across SPY/QQQ/IWM from live options chains (CBOE delayed quotes JSON — no API key), identifies gamma regime (positive/negative/neutral), locates structural levels (zero-gamma, call wall, put wall), and delivers daily context via both a scheduled HTML email and an interactive Streamlit dashboard.

## Core Value

Given today's dealer positioning across SPY/QQQ/IWM — should a PM pay up for protection right now, and is the dealer-driven vol environment suppressing or amplifying moves? Actionable positioning context, not mathematical showcase.

## Runtime & Stack

- **Runtime:** local Python venv. `python -m gex.run_daily --send` → email (scheduled via Task Scheduler). `streamlit run streamlit_app.py` → dashboard (interactive).
- **Data:** CBOE delayed quotes JSON (`cdn.cboe.com` — free, no auth). Snapshots: `out/gex_snapshots.parquet`.
- **Stack:** pandas, numpy, scipy, matplotlib, requests, pyarrow, streamlit, plotly, pandas_market_calendars.
- **Tests:** pytest, 24 tests green (down from 77 post-v3.0 due to feature cuts per 2026-05-11 refactor).

## Key Files

| File | Purpose | Last Updated |
|------|---------|---|
| `gex/greeks_engine.py` | BS gamma, vanna, charm — vectorised with 0DTE guard | 2026-05-06 |
| `gex/exposure_engine.py` | GEX/VEX by strike; delta-hedge flow | 2026-05-11 (refactor: kept GEX only) |
| `gex/analytics.py` | Summary dict, defensible chart outputs | 2026-05-11 (refactor: removed CHEX, regime labels) |
| `gex/validation.py` | Parquet snapshot store, load_yesterday, load_history | 2026-05-06 |
| `gex/report.py` | HTML email body builder — defensible outputs only | 2026-05-11 (refactor: removed VEX, ZGL flow, regime label) |
| `gex/run_daily.py` | Daily orchestrator — 3 tickers, save + send | 2026-05-06 |
| `streamlit_app.py` | Interactive dashboard — Live + Historical tabs; defensible display only | 2026-05-11 (refactor: removed VEX/CHEX, regime label, badges) |
| `out/gex_snapshots.parquet` | Historical GEX snapshot store (30+ days) | Growing daily |

## Requirements

### Validated / Implemented (v3.0–v3.1)

**Core Defensible Outputs** (all surfaces):
- ✓ Spot, Day %, IV30, 1-day σ (from IV30)
- ✓ Net GEX (sign + magnitude)
- ✓ Zero-gamma level and vs-ZGL %
- ✓ Single max-GEX call/put walls + distance from spot
- ✓ Δ-flow = |Net GEX| / (spot × 0.01)
- ✓ 30-session ZGL-vs-spot history chart (dashboard only)
- ✓ Accent bar (driven by net GEX sign; no categorical label)

**Greeks & Flow Engine:**
- ✓ GRKS-01/02/03/04 — Vanna + Charm in BS engine, `add_greeks()` enriches chain DF, 0DTE guard — v3.0
- ✓ EXP-01/02/03 — GEX by strike, net scalar in `summarise()`, parquet store — v3.1 (VEX removed)
- ✓ FLOW-01/02/03 — Delta-hedge $/1%, email table columns — v3.0

**Dashboard & Email:**
- ✓ DASH-01/02/03/04/05 — Streamlit app: regime cards (sign-driven color only), cross-asset chart, expanders, COM isolation — v3.0/v3.1
- ✓ HIST-01/02/03/04 — Historical tab: ZGL trend, regime persistence, streak counter, event study — v3.0 (streak removed v3.1)
- ✓ EMAIL-01/02/03 — HTML email: per-ticker cards, defensible fields, theme-adaptive styling — v3.0/v3.1

**UAT Sign-Off:**
- ✓ UAT-01/02/03/04 — All 4 Streamlit scenarios pass; dashboard launches without error — v3.1

### Removed / Not Defensible

| Output | Reason | Cut When |
|--------|--------|----------|
| VEX display | Vanna is BS-European; 5–15% error on American options | 2026-05-11 |
| CHEX display | Charm is second-order vol; less PM-readable; statistically thin | 2026-05-11 |
| Regime categorical label | $200M neutral floor is hand-tuned; non-stationary | 2026-05-11 |
| vs-yesterday badge | Daily OI roll dominates 5% threshold | 2026-05-11 |
| Regime streak counter | Depends on removed label | 2026-05-11 |
| VEX/GEX ratio | Depends on VEX | 2026-05-11 |
| Early-exercise flag | Fragile signal; not actionable for SPY/QQQ/IWM | 2026-05-11 |
| ZGL flow row | ~20% numerical differentiation error | 2026-05-11 |
| GEX-weighted wall cluster | Arbitrary band parameters | 2026-05-11 |

### Active (v3.2)

- [ ] NARR-01 — Positioning narrative (always-visible mechanical explanation of GEX sign)
- [ ] NARR-02 — GEX percentile rank vs trailing history
- [ ] CTX-01 — VRP display (IV30 − RV20) with hedging cost interpretation
- [ ] CTX-02 — OI tilt (dollar-weighted put vs call OI)
- [ ] CTX-03 — Front skew gauge with percentile rank
- [ ] CUT-01 — Remove Hedge Sh/$1, % vs ZGL, strike slope, term slope from cards
- [ ] CUT-02 — Demote vol surface to collapsed/optional section

### Out of Scope

| Feature | Reason |
|---------|--------|
| Bloomberg data swap | One-class change in data_loader.py — deferred to v4.x |
| Vomma / second-order vol Greeks | Less PM-readable than vanna |
| New GEX signals / predictive scoring | Holm-Bonferroni bar is high |
| Sleeve allocation framework (v2.x) | Separate track |
| Automated Task Scheduler / Streamlit autostart | After PM desk validates dashboard |
| Live intraday refresh | CBOE CDN is delayed — real-time needs paid feed |
| Dispersion / implied-correlation | Out of scope |
| Live execution / order routing | Research tool only |

## Strategic Decisions

| Date | Decision | Why |
|------|----------|-----|
| 2026-05-21 | Pivot to PM-actionable positioning; cut non-decision metrics | Outputs audited against "does this change a PM decision?"; mathematical elegance deprioritized |
| 2026-05-21 | Add VRP (IV30 − RV20) as hedging cost context | Carr & Wu (2009) VRP; descriptive metric even without causal backing |
| 2026-05-21 | Kill strike slope, term slope, hedge sh/$1, % vs ZGL | None inform a PM decision; model constructs without predictive value |
| 2026-05-11 | Cut VEX/CHEX/regime labels per methodology audit | BS-European Greeks on American options add 5–15% error; categorical regime label depends on hand-tuned non-stationary floor; focus on defensible outputs only |
| 2026-05-06 | GSD sign convention: calls +, puts − | SpotGamma/retail standard. Positive net GEX = dealers net long gamma = stabilising |
| 2026-05-05 | Vanna over Vomma | Vanna (∂delta/∂vol) translates to dealer rehedging flow — PM-readable. Vomma is not. |
| 2026-05-05 | Streamlit additive — email pipeline preserved | Email is scheduled and working; dashboard adds interactivity without breaking existing workflow |
| 2026-05-06 | Replaced yfinance with CBOE delayed quotes JSON | Free, no auth, CBOE-native Greeks (American-style). data_loader.py rewritten. |
| 2026-05-05 | New milestone v3.0 — GEX Interactive Dashboard | GEX POC is production-grade; direction is depth (Greeks, flow, dashboard) not more signals |
| 2026-05-11 | Expected-1d-sigma display (from IV30) | Answers "how much might this move today?" without eyeballing gamma charts |
| 2026-05-11 | Single max-strike walls (not GEX-weighted cluster) | Empirically observable; no arbitrary band parameters |

## Known Open Items

| Item | Description | Status | Next Action |
|------|-------------|--------|---|
| Phase 6 (Charm by DTE) | Pending — ready to plan/execute | Blocked on Phase 5 complete ✅ + refactor sign-off | Plan Phase 6 |
| Phase 7 (Test coverage) | Pending — 24 current tests; target ~35–40 | Blocked on Phase 6 complete | Plan Phase 7 |
| Phase 8 (Pre-Dist Hardening) | Partial out-of-phase (2026-05-11); ~2 requirements remain (timestamp, filter-drop) | In progress | Integrate out-of-phase work; complete DIST-01 + DIST-04 |
| American-style BS for IWM | IWM uses European model — acknowledged with expected early exercise risk signal | Acceptable for POC | Revisit in v4.x if PM feedback warrants |
| NDX skew identity | NDX/SPX share same CBOE SKEW signal in sleeve framework | v2.x track — not blocking | Defer to v2.x roadmap |

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

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
