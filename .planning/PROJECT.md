# Options Quant — Sleeve Allocation Framework

*Last updated: 2026-05-04 — v2.1 Bayesian reframe shipped*

## What This Is

A decision dashboard that describes the current options environment (VRP, skew, term structure, trend, drawdown, fragility) and shows the historical base rates for each sleeve (covered call, cash-covered put, collar, short strangle) conditional on today's signal quartiles. Ships as a self-contained HTML report on free CBOE+FRED data.

**Market-general** — no fund specialization. Phase β (PDIV) dropped 2026-05-04.

## Core Value

Given today's vol/skew/trend/drawdown readings, what have options sleeves historically returned in similar environments — and what is the honest statistical confidence in that pattern (0 of 30 tests survive Holm correction)?

The conditional summary is the primary output. Section C is the analytical core. Section E (unconditional full-period stats) is context, not evidence of sleeve superiority.

## Current Milestone: v2.1 — POC Delivery & Validation

**Phase 1 COMPLETE.** Post-phase Bayesian reframe COMPLETE. Report ready to send.

**Deliverable:** `out/sleeve_report_YYYYMMDD.html` — run `python build_report.py`.

**Audience:** Quant team first. Async handoff (HTML + WALKTHROUGH.md) followed by meeting.

**Hard scope cap (locked):** No PDIV / fund specialization. No Markov-switching/HMM. No new signals beyond the six + fragility composite already in v2.0.

## Runtime & Stack

- **Runtime:** local Python venv. `python build_report.py` → HTML. No Jupyter required.
- **Data:** CBOE CDN + FRED (free, no auth). Bloomberg is a one-class swap in `local_data.py` pending team greenlight.
- **Stack:** pandas, numpy, scipy, statsmodels, matplotlib. `requirements.txt` is authoritative.
- **Tests:** 74 (math correctness + pipeline invariants + property-based). Run with `pytest`.

## Key Files

| File | Purpose |
|------|---------|
| `run.py` | Text dashboard to stdout |
| `build_report.py` | HTML report generator |
| `local_data.py` | `FreeCon` — CBOE+FRED data dispatch |
| `data_layer.py` | `build_panels()` → `Panels` |
| `signals.py` | `build_signals()` → `Signals` |
| `backtest.py` | `run_backtest()` → `BacktestResults` |
| `dashboard.py` | All section functions including `section_today_conditional` |
| `stats_rigor.py` | Holm-Bonferroni, block bootstrap |
| `sensitivity.py` | TC sensitivity, tail risk |
| `WALKTHROUGH.md` | Per-section quant team guide |
| `hmm.ipynb` | v1.0 legacy — DO NOT MODIFY |

## Constraints

- No predictive claims — descriptive and historical only
- No new signals — six + fragility locked until team validates
- No PDIV, no HMM
- Windows paths (pathlib / os.path.join)
- Strategy menu: CC, CSP, Collar, Short Strangle. Dispersion out of scope.

## Strategic Decisions

| Date | Decision | Why |
|------|----------|-----|
| 2026-05-04 | Bayesian reframe — conditional summary leads; equity chart removed; Section E has unconditional caveat | Equity curve chart was a strategy-ranking signal (16yr bull market), not decision support. Conditional base rates are the point. |
| 2026-05-04 | Deliverable is HTML report (`build_report.py`), not Jupyter notebook | Simpler; no Jupyter dependency; same analytical content |
| 2026-05-04 | Bloomberg calibration deferred — ship on free data | POC value is the framing and conditional analysis; Bloomberg is a one-class swap when team greenlights |
| 2026-05-04 | Drop Phase β (PDIV specialization) | Market-general scorecard more useful to quant team than fund-tuned overlay rule |
| 2026-05-04 | Local POC dev track (CBOE + FRED) | Free official sources; identifier set matches Bloomberg so math is portable |
| 2026-05-04 | yfinance rejected — all-official sources only | yfinance is unofficial Yahoo scraper; CBOE/FRED are clean provenance |
| 2026-05-04 | Universe = SPX + NDX index level | Matches what VIX/VXN measure (index options) |
| 2026-04-30 | Pivot v1.0 HMM → v2.0 Sleeve Framework | HMM alone cannot inform sleeve allocation without options-pricing data |
| 2026-04-30 | Scorecard primary, HMM optional fragility flag | PM-auditable, governance-friendly, robust to data limits |
| 2026-04-30 | Strategy menu = CC + CSP + Collar + ShortStrangle; drop dispersion | Dispersion is dealer/HF turf, capacity-limited, governance-unfriendly for retail AM |
| 2026-04-30 | Use `statsmodels.MarkovRegression` if Markov-switching ever needed | `hmmlearn` unavailable; statsmodels gives proper sticky Markov-switching |

## Out of Scope

| Feature | Reason |
|---------|--------|
| Dispersion / implied-correlation sleeve | Dealer/HF turf, capacity-limited, governance-unfriendly |
| PDIV fund specialization | Phase β dropped — market-general scope only |
| New signals beyond current six + fragility | Locked until team validates current set |
| HMM / Markov-switching as spine | Demoted to optional fragility flag extension |
| Automated weekly schedule | Manual run for POC; revisit if team adopts |
| Live execution / order routing | Research / decision-support only |
| Jupyter notebook deliverable | Replaced by HTML report |
| Cron2 production run | Deferred; Bloomberg swap is a one-class change |

## Known Open Items

| Item | Description | Status |
|------|-------------|--------|
| NDX skew identity | NDX/SPX share same CBOE SKEW signal — readings always identical | Fix before team meeting |
| NDX iv90_atm synthesis | Uses SPX term-structure ratio | Fix in same pass as skew |
| Bloomberg 90mny IV | Synthesized with slope=0.2; absolute level uncalibrated | Pending team greenlight |
| UAT | Browser check of `out/sleeve_report_YYYYMMDD.html` | Now |
