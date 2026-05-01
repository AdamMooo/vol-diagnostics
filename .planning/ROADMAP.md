# Roadmap: TQ — Sleeve Allocation Framework (v2.0)

## Overview

Eight phases (7-14) build a regime-aware options-overlay sleeve scorecard. Phase α (Phases 7-12) is the engine — data, signals, sleeve P&L backtests, scorecard, PM output, validation. Phase β (Phase 13) specializes the engine for PDIV. Phase γ (Phase 14) is an optional Markov-switching fragility flag appendix. All work in a new notebook `sleeve_alpha.ipynb`; `hmm.ipynb` is preserved as legacy v1.0.

Phase numbering continues from v1.0 (which ended at Phase 6) to avoid collision with stale `01-*`, `02-*`, `03-*` phase directories. The α / β / γ labels are the user-facing structure; 7-14 are the GSD phase numbers.

## Phases (Phase α — Engine)

- [ ] **Phase 7: Extended Data Layer** — Multi-underlying price + IV + skew + VIX + risk-free rate, aligned, freshness-checked
- [ ] **Phase 8: Signal Engineering** — RV, VRP, skew, term, trend, drawdown, fragility composite — percentile-ranked
- [ ] **Phase 9: Sleeve Backtest Engine** — BS pricing + synthetic monthly-roll P&L for CC, CSP, Collar, Short Straddle on each underlying
- [ ] **Phase 10: Scorecard** — Per-sleeve linear scoring rules on signal panel, normalized weight allocation
- [ ] **Phase 11: PM-Grade Output** — Dashboard table + auto-commentary + small-multiple charts + parquet snapshot
- [ ] **Phase 12: Validation Gates** — Causality, walk-forward sign accuracy, turnover, tail-risk, robustness, trust scorecard

## Phases (Phase β — PDIV Specialization)

- [ ] **Phase 13: PDIV Specialization** — Engine pointed at PDIV; current-vs-recommended overlay diff; historical overlay alpha quantified

## Phases (Phase γ — Optional Appendix)

- [ ] **Phase 14: Markov-Switching Fragility Flag (optional)** — `statsmodels.MarkovRegression` 2-state on fragility composite, hysteresis, override rule

---

## Phase Details

### Phase 7: Extended Data Layer (α)
**Goal:** Multi-underlying price + ATM IV + 90%-moneyness IV + VIX + risk-free rate are loaded, calendar-aligned, and exposed as canonical panels (`prices_panel`, `iv_panel`, `skew_panel`) ready for downstream signal work.

**Depends on:** Nothing (phase α start; uses confirmed working `con.bdh` fields)

**Requirements:** DATA-06, DATA-07, DATA-08, DATA-09, DATA-10, DATA-11, DATA-12

**Success Criteria:**
1. SPX and QQQ price + ATM IV + 90%-moneyness IV pulled and aligned over full history with documented field names
2. XIU/XSP probed; either included with confirmed fields or explicitly marked deferred with reason
3. VIX and a risk-free proxy loaded
4. All series aligned to a single trading-day index using `pandas_market_calendars`
5. Freshness check warns on stale data; data layer runs clean on fresh kernel

### Phase 8: Signal Engineering (α)
**Goal:** Six core signals + a fragility composite are computed per underlying, percentile-ranked on a causal expanding window, and pass a QA cell.

**Depends on:** Phase 7

**Requirements:** SIG-01, SIG-02, SIG-03, SIG-04, SIG-05, SIG-06, SIG-07, SIG-08

**Success Criteria:**
1. RV, VRP, skew, trend, drawdown signals computed per underlying with no future leakage
2. Cross-asset fragility composite computed
3. All signals percentile-ranked [0, 1] on a 252d expanding window
4. QA cell prints missingness %, sanity bounds, and rolling stationarity diagnostic

### Phase 9: Sleeve Backtest Engine (α)
**Goal:** Synthetic monthly-roll P&L histories for CC, CSP, 95/110 Collar, 1m Short Straddle on each underlying are produced, with Black-Scholes pricing, slippage assumptions, and a sleeve-vs-underlying comparison table.

**Depends on:** Phase 7 (Phase 8 not strictly required — can run in parallel)

**Requirements:** SLV-01, SLV-02, SLV-03, SLV-04, SLV-05, SLV-06, SLV-07

**Success Criteria:**
1. BS pricer covers call/put with vectorized inputs and matches a sanity-check value
2. CC, CSP, Collar, Short Straddle P&L series produced per underlying with explicit slippage
3. Comparison table (return / vol / Sharpe / max DD / hit rate) produced
4. Outputs reproducible (`random_state=42`) and snapshotted to parquet

### Phase 10: Scorecard (α)
**Goal:** Per-sleeve transparent scoring rules combine signal-panel ranks into a [-1, +1] sleeve attractiveness score; sleeve weights normalize within a configurable overlay budget.

**Depends on:** Phase 8 (signals), Phase 9 (sleeve P&L for sanity-check)

**Requirements:** SCR-01, SCR-02, SCR-03, SCR-04

**Success Criteria:**
1. Each sleeve's scoring rule is a printed linear combination of signal ranks (no hidden weights)
2. Latest-date sleeve scores in [-1, +1] for every (sleeve × underlying)
3. Weights normalize to a configurable budget; sleeve caps applied
4. Top-2 driver signals identified per (sleeve × underlying)

### Phase 11: PM-Grade Output (α)
**Goal:** Dashboard table + auto-commentary + small-multiple charts + parquet snapshot. PM can read this without verbal explanation.

**Depends on:** Phase 10

**Requirements:** OUT-01, OUT-02, OUT-03, OUT-04, OUT-05

**Success Criteria:**
1. Dashboard table renders with sleeve × underlying × score × weight × top-2 drivers + signal-percentile context
2. Auto-commentary block (3-5 sentences) generated from data, not hard-coded
3. Sleeve scores small-multiples chart + cumulative P&L chart present
4. Output snapshotted to parquet/csv per refresh date

### Phase 12: Validation Gates (α)
**Goal:** All six validation gates pass, producing a one-line trust verdict at the top of the notebook.

**Depends on:** Phase 11

**Requirements:** VAL-01, VAL-02, VAL-03, VAL-04, VAL-05, VAL-06

**Success Criteria:**
1. Causality, walk-forward sign accuracy, turnover, tail-risk, robustness all tested
2. Trust scorecard prints PASS/WARN/FAIL with per-gate detail
3. Any FAIL is documented with mitigation or scope decision

### Phase 13: PDIV Specialization (β)
**Goal:** Engine specialized to PDIV — produces a per-week sizing recommendation vs PDIV's current overlay rule, plus historical overlay-alpha quantification.

**Depends on:** Phase 11 (engine output) — should not require Phase 12 to be green to start, but must be green to ship to a PM

**Requirements:** PDIV-01, PDIV-02, PDIV-03, PDIV-04

**Success Criteria:**
1. PDIV's current overlay rule captured in a config cell
2. Engine output specialized for PDIV's underlying / sleeve mix
3. Per-week sizing rec vs current rule produced
4. Historical overlay alpha computed and reported

### Phase 14: Markov-Switching Fragility Flag (γ — optional)
**Goal:** `statsmodels.MarkovRegression` 2-state model on the SIG-06 fragility composite produces a sticky fragility flag with hysteresis; flag overrides short-vol sleeve weights when ON.

**Depends on:** Phase 8 (fragility composite) and Phase 10 (scorecard to override)

**Requirements:** FRG-01, FRG-02, FRG-03

**Success Criteria:**
1. 2-state Markov-switching variance model fit, sticky transitions, `random_state=42`
2. 5-day hysteresis filter applied; OOS K and dwell-time documented
3. Override rule wired into Scorecard / Output: short-vol sleeves capped when fragility = ON

---

## Progress

**Execution Order:**
Phase 7 → Phase 8 (and Phase 9 in parallel after 7) → Phase 10 → Phase 11 → Phase 12 → Phase 13 (β) → Phase 14 (γ, optional)

| Phase | Plans | Status | Completed |
|-------|-------|--------|-----------|
| 7. Extended Data Layer | 0 | Not started | - |
| 8. Signal Engineering | 0 | Not started | - |
| 9. Sleeve Backtest Engine | 0 | Not started | - |
| 10. Scorecard | 0 | Not started | - |
| 11. PM-Grade Output | 0 | Not started | - |
| 12. Validation Gates | 0 | Not started | - |
| 13. PDIV Specialization | 0 | Not started | - |
| 14. Fragility Flag (γ — optional) | 0 | Not started | - |

**Phase α (engine, must-ship):** 7-12
**Phase β (PDIV, should-ship):** 13
**Phase γ (HMM appendix, nice-to-have):** 14

---

## v1.0 (HMM) Phases — Archived

Phases 1-6 from v1.0 (HMM-centric fund diagnostic) are not part of v2.0. Their planning artifacts live under `.planning/phases/01-data-layer/`, `02-regime-model/`, `03-fund-analysis/`. The corresponding code is in `hmm.ipynb`, preserved untouched. See `MILESTONES.md` for the v1.0 closure rationale.
