# Requirements: TQ — Sleeve Allocation Framework

**Defined:** 2026-04-30 (milestone v2.0)
**Core Value:** PM-readable scorecard of options-overlay sleeve attractiveness across SPX/QQQ (and optionally XIU/XSP), backed by sleeve P&L backtests, conditioned on a transparent signal panel, with optional Markov-switching fragility flag.

---

## v2.0 Requirements (Active)

### Data Layer (extended for sleeve work)

- [ ] **DATA-06**: SPX, QQQ price + 30d ATM IV + 30d 90%-moneyness IV pulled via `con.bdh` over the full available history with documented field names
- [ ] **DATA-07**: Probe and document availability of XIU and XSP equivalents; if available, included; if not, documented as deferred
- [ ] **DATA-08**: VIX (and optional VVIX) pulled via `con.bdh` for fragility composite
- [ ] **DATA-09**: All series aligned on a common trading-day index (`pandas_market_calendars` for NYSE; TSX calendar if Canadian underlyings included), explicit handling of cross-calendar holidays
- [ ] **DATA-10**: Risk-free rate proxy (3M T-bill or equivalent) loaded for option pricing
- [ ] **DATA-11**: Data freshness check — last-bar dates printed; staleness > 5 trading days = warning
- [ ] **DATA-12**: Data layer cells run cleanly on a fresh kernel and produce a `prices_panel`, `iv_panel`, `skew_panel` set of canonical DataFrames

### Signal Engineering

- [ ] **SIG-01**: 21-day realized vol (close-to-close, annualized) computed per underlying
- [ ] **SIG-02**: Variance Risk Premium signal: `IV_30d_ATM - RV_21d`, per underlying
- [ ] **SIG-03**: Skew signal: `IV_30d_90moneyness - IV_30d_ATM`, per underlying
- [ ] **SIG-04**: Trend signal: 12-month total return, per underlying
- [ ] **SIG-05**: Drawdown-state signal: percent below 1-year high, per underlying
- [ ] **SIG-06**: Cross-asset fragility composite: weighted combination of VIX-level, IV term-shape proxy (where available), and skew level — single time-series
- [ ] **SIG-07**: All signals percentile-ranked on a 252-day **expanding** window (causal — no future leak); ranked outputs in [0, 1]
- [ ] **SIG-08**: Signal QA cell: missingness %, rolling stationarity-of-rank check, sanity-bounds asserted

### Sleeve Backtest Engine

- [ ] **SLV-01**: Black-Scholes pricing helper (call/put, given spot, K, T, sigma, r) — vectorized on pandas
- [ ] **SLV-02**: Synthetic monthly-roll Covered Call P&L: long underlying + short 30d ATM call, rolled monthly, per underlying — net of an explicit slippage assumption
- [ ] **SLV-03**: Synthetic monthly-roll Cash-Covered Put P&L: short 30d ATM put + cash earning risk-free, rolled monthly, per underlying
- [ ] **SLV-04**: Synthetic monthly-roll 95/110 Collar P&L: long underlying + short 110% call + long 95% put, rolled monthly, per underlying — uses 90% moneyness IV for put leg
- [ ] **SLV-05**: Synthetic monthly-roll Short Straddle P&L: short 30d ATM call + short 30d ATM put + cash earning risk-free, rolled monthly, per underlying — sized at the dollar-delta of the underlying
- [ ] **SLV-06**: All sleeves return a sleeve-vs-underlying comparison table: total return, ann. return, vol, Sharpe, max DD, worst-month, hit rate
- [ ] **SLV-07**: Sleeve P&L backtests reproducibility — `random_state=42`, snapshot to parquet per refresh date

### Sleeve Scorecard

- [ ] **SCR-01**: Per-sleeve scoring rule expressed as a transparent linear combination of signal panel ranks, weights printed in the cell (no hidden coefficients)
- [ ] **SCR-02**: Sleeve scores output in [-1, +1], one row per (sleeve × underlying), at the latest date
- [ ] **SCR-03**: Sleeve weights normalized within a configurable overlay budget (default 25% of NAV) — long-only on overlay sleeves, with a sleeve-cap override
- [ ] **SCR-04**: Top-2 driver signals identified per (sleeve × underlying) — for the auto-commentary

### PM-Grade Output

- [ ] **OUT-01**: Single dashboard table: sleeve × underlying × score × recommended weight × top-2 drivers × current-vs-history percentile of key signals
- [ ] **OUT-02**: Auto-generated commentary block (3-5 sentences) summarizing the dashboard in plain English, generated from the data, not hard-coded
- [ ] **OUT-03**: Sleeve scores chart over time (small multiples, one panel per sleeve)
- [ ] **OUT-04**: Sleeve cumulative P&L chart per underlying with regime/fragility shading where applicable
- [ ] **OUT-05**: Output table also written to disk as parquet/csv per refresh date for downstream consumption

### Validation Gates

- [ ] **VAL-01**: Causality test: deliberate label-shift confirms no time-t signal uses data > t
- [ ] **VAL-02**: Walk-forward sleeve sign accuracy: for each sleeve, test that score > 0.5 windows have higher mean sleeve return than score < 0 windows, p < 0.10 by bootstrap
- [ ] **VAL-03**: Turnover sanity: combined overlay turnover < 200%/yr after rules and assumed costs
- [ ] **VAL-04**: Tail-risk reporting: 1-day 99% VaR + conditional VaR per sleeve and combined; documented as descriptive, not forecast
- [ ] **VAL-05**: Robustness probe: replace one signal at a time with random-rank noise — does the dashboard recommendation flip?
- [ ] **VAL-06**: Trust scorecard: PASS/WARN/FAIL one-line verdict aggregating VAL-01 through VAL-05 — printed prominently in the notebook

### Phase β — PDIV Specialization

- [ ] **PDIV-01**: PDIV's current overlay rule documented (read-once, captured in notebook config cell)
- [ ] **PDIV-02**: Engine pointed at PDIV's actual benchmark and current overlay rule
- [ ] **PDIV-03**: Output: per-week recommendation on heavier/lighter overlay vs current rule, with optional collar / put-buy add given current skew
- [ ] **PDIV-04**: Variance vs benchmark passive-overlay return computed historically — quantifies the overlay alpha

### Phase γ — Optional Fragility Flag (HMM Appendix)

- [ ] **FRG-01**: 2-state `statsmodels.tsa.regime_switching.MarkovRegression` fit on the cross-asset fragility composite (SIG-06), with switching variance, `random_state=42`
- [ ] **FRG-02**: Hysteresis filter (5-day minimum hold) applied to fragility flag; OOS K and dwell-time validation as a release gate
- [ ] **FRG-03**: Override rule documented: when fragility flag = ON, cap short-vol sleeves (CSP, Short Strangle) and increase weight on Collar / put-buy

---

## Validated (carried from v1.0)

These v1.0 reqs are functionally validated by the existing `hmm.ipynb` and are not re-built in v2.0:

- DATA-01..05 (Data Layer for fund/benchmark) — covered in `hmm.ipynb` Section 0/1
- REGM-01..06 (Regime Model on benchmark) — covered in `hmm.ipynb` Section 2 (caveat: GMM not HMM)
- FUND-01..04 (Fund-by-regime stats) — `hmm.ipynb` Section 3 cells written, pending server run
- STAB-01..03 (Transition matrix, expected duration, current regime) — `hmm.ipynb` Section 4 cells written

These are diagnostic artifacts on a single fund (RTA) and are out of scope for the v2.0 sleeve framework.

---

## Out of Scope (v2.0)

| Feature | Reason |
|---------|--------|
| Dispersion / implied-correlation sleeve | Dealer/HF turf, capacity-limited, governance-unfriendly for retail AM |
| Single-name option overlays | Capacity, complexity, dispersion-adjacent |
| Real-time / intraday signal refresh | Weekly cadence sufficient for the use case |
| External data beyond `emds_client` | Locked environment, license risk |
| Live execution / order routing | Research notebook only |
| Modification of `hmm.ipynb` | v1.0 artifact preserved untouched |
| Predictive / forecasting language | Framework is descriptive + historical analog only |
| Multi-account portfolio optimization | Out of scope; single-overlay focus |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-06..12 | Phase 1 — Extended Data Layer | Pending |
| SIG-01..08 | Phase 2 — Signal Engineering | Pending |
| SLV-01..07 | Phase 3 — Sleeve Backtest Engine | Pending |
| SCR-01..04 | Phase 4 — Scorecard | Pending |
| OUT-01..05 | Phase 5 — PM-Grade Output | Pending |
| VAL-01..06 | Phase 6 — Validation Gates | Pending |
| PDIV-01..04 | Phase 7 — PDIV Specialization (β) | Pending |
| FRG-01..03 | Phase 8 — Optional Fragility Flag (γ) | Pending |

**Coverage:** 38 active v2.0 requirements, all mapped to phases.

---
*Defined: 2026-04-30*
*Last updated: 2026-04-30 — milestone v2.0 requirements defined*
