# Requirements — v3.1 Hardening & Charm

*Last updated: 2026-05-12 — Phase 5 complete; out-of-phase refactor work documented*

## Milestone Goal

Sign off deferred UAT, add Charm chart, and fill critical test coverage gaps before handing the platform to PMs.

**Note:** Out-of-phase refactoring (2026-05-11) removed non-defensible outputs (VEX, CHEX, regime categorical labels). Core requirements updated to reflect actual feature set.

---

## Requirements

### UAT Sign-Off

**Status: ✅ COMPLETE** — All 4 scenarios passed 2026-05-06. Out-of-phase refactor (2026-05-11) preserves core UAT scenarios.

- [x] **UAT-01** — User can launch `streamlit run streamlit_app.py` without ImportError, COM error, or matplotlib backend error, and the browser page loads showing the app title ✅ PASS (2026-05-06)
- [x] **UAT-02** — Regime cards render for SPY, QQQ, IWM with correct colors (accent bar driven by net GEX sign) showing: Spot, Net GEX, Δ-flow, Zero-Gamma level ✅ PASS (2026-05-06; regime label removed per 2026-05-11 refactor)
- [x] **UAT-03** — Clicking a ticker expander reveals two charts (strike GEX, gamma profile) and a summary table with columns: Spot, Net GEX, Zero-Gamma, Call Wall, Put Wall, IV30, 1-day σ ✅ PASS (2026-05-06; VEX/CHEX removed per 2026-05-11 refactor)
- [x] **UAT-04** — Clicking Refresh in the sidebar clears the per-ticker cache and triggers a re-fetch (spinners visible); new data loads successfully ✅ PASS (2026-05-06)

### Charm Chart

**Status: ⏳ PENDING** — Phase 6 (not yet started). Out-of-phase refactor has cleared the way by removing CHEX display.

- [ ] **CHARM-01** — `analytics.py` exposes a `charm_by_dte_chart()` function that renders net charm exposure bucketed by DTE (e.g. 0–7, 8–30, 31–60, 60+) as a bar chart
- [ ] **CHARM-02** — The Streamlit Live tab surfaces the Charm by DTE chart inside the per-ticker expander alongside the existing strike GEX and gamma profile charts

### Test Coverage

**Status: ⏳ PENDING** — Phase 7 (not yet started). Current: 24 tests green (post-refactor; down from 77 post-v3.0 due to removed features).

- [ ] **COV-01** — `tests/test_data_loader.py` covers: happy-path CBOE JSON parse → valid ChainSnapshot; min_oi / min_dte / max_iv filters each drop the right rows; malformed symbol is skipped without crash
- [ ] **COV-02** — `tests/test_report.py` covers: `build_email()` returns a non-empty HTML string containing expected ticker headers and accent bar colors (driven by net GEX sign)
- [ ] **COV-03** — `tests/test_emailer.py` covers: `send()` raises ValueError when no recipients configured; Outlook COM dispatch is mocked so the test runs without Outlook installed
- [ ] **COV-04** — `tests/test_run_daily.py` covers: full orchestration happy path (all 3 tickers) with data_loader and emailer mocked; parquet snapshot is written and contains expected columns
- [ ] **COV-05** — `tests/test_analytics_charts.py` covers: chart functions return a matplotlib Figure without error for known-good input; zero-exposure edge case does not crash

---

## Removed by Out-of-Phase Refactor (2026-05-11)

Per methodology audit, the following features were removed because they cannot be defended rigorously at PM-level scrutiny:

| Item | Reason |
|------|--------|
| VEX display (both email/dashboard) | Vanna/Charm are BS-European derivations; 5–15% error on American options (CBOE doesn't publish Greeks) |
| CHEX display (both email/dashboard) | Charm is second-order vol derivative; less PM-readable than vanna; statistically thin |
| Regime categorical label ("POSITIVE/NEGATIVE/NEUTRAL") | $200M neutral floor is hand-tuned; non-stationary; label adds editorial noise |
| vs-yesterday badge | Daily OI roll dominates threshold (5%+ noise) |
| Regime streak counter | Depends on calibrated regime label (removed) |
| VEX/GEX ratio | Depends on VEX (removed) |
| Early-exercise flag | Uses delayed mid quotes; fragile signal; not actionable for SPY/QQQ/IWM size |
| "Regime % days" frequency table | Depends on calibrated label (removed) |
| ZGL flow row | Numerical differentiation across 200-point grid = ~20% error; indefensible |
| GEX-weighted wall cluster center | Arbitrary ±2% / top-3 band parameters; replaced with single max one-sided GEX strike |

**What remains** (defensible outputs only):
- Spot, Day %, IV30, 1-day σ (from IV30)
- Net GEX value (sign + magnitude)
- Zero-gamma level and vs-ZGL %
- Single max-GEX call/put wall strikes + distance from spot
- Δ-flow = |Net GEX| / spot / 0.01
- 30-session ZGL-vs-spot history chart (dashboard only)

---

## Future Requirements (deferred)

- Live intraday refresh — CBOE CDN is delayed; real-time needs paid feed
- Automated Task Scheduler / Streamlit autostart — after PM desk validates
- Bloomberg data swap — one-class change in data_loader.py, v4.x
- Vomma — less PM-readable than vanna

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| New GEX signals | Holm-Bonferroni bar is high |
| Sleeve allocation framework | v2.x separate track |
| Dispersion / implied-correlation | Research tool only |
| Live execution / order routing | Research tool only |
| American-style BS for IWM | Acceptable for POC; acknowledged |

---

## Traceability

| REQ-ID | Phase |
|--------|-------|
| UAT-01/02/03/04 | Phase 5 |
| CHARM-01 | Phase 6 |
| CHARM-02 | Phase 6 |
| COV-01/02/03/04/05 | Phase 7 |

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
