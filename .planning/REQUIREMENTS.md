# Requirements — v3.1 Hardening & Charm

*Last updated: 2026-05-06*

## Milestone Goal

Sign off deferred UAT, add Charm chart, and fill critical test coverage gaps before handing the platform to PMs.

---

## Requirements

### UAT Sign-Off

- [ ] **UAT-01** — User can launch `streamlit run streamlit_app.py` without ImportError, COM error, or matplotlib backend error, and the browser page loads showing the app title
- [ ] **UAT-02** — Three regime cards render for SPY, QQQ, IWM with correct background colour, regime label, net GEX (B), VEX (B), delta-flow ($X.XB/1%), and vs-yesterday label
- [ ] **UAT-03** — Clicking a ticker expander reveals two charts (strike GEX, gamma profile) and a summary table with columns: Net GEX, VEX, CHEX, Zero-Gamma, Call Wall, Put Wall
- [ ] **UAT-04** — Clicking Refresh in the sidebar clears the per-ticker cache and triggers a re-fetch (spinners visible); new data loads successfully

### Charm Chart

- [ ] **CHARM-01** — `analytics.py` exposes a `charm_by_dte_chart()` function that renders net charm exposure bucketed by DTE (e.g. 0–7, 8–30, 31–60, 60+) as a bar chart
- [ ] **CHARM-02** — The Streamlit Live tab surfaces the Charm by DTE chart inside the per-ticker expander alongside the existing strike GEX and gamma profile charts

### Test Coverage

- [ ] **COV-01** — `tests/test_data_loader.py` covers: happy-path CBOE JSON parse → valid ChainSnapshot; min_oi / min_dte / max_iv filters each drop the right rows; malformed symbol is skipped without crash
- [ ] **COV-02** — `tests/test_report.py` covers: `build_email()` (or equivalent entry point) returns a non-empty HTML string containing expected ticker headers and regime class; color maps produce correct hex for each regime
- [ ] **COV-03** — `tests/test_emailer.py` covers: `send()` raises ValueError when no recipients configured; Outlook COM dispatch is mocked so the test runs without Outlook installed
- [ ] **COV-04** — `tests/test_run_daily.py` covers: full orchestration happy path (all 3 tickers) with data_loader and emailer mocked; parquet snapshot is written and contains expected columns
- [ ] **COV-05** — `tests/test_analytics_charts.py` covers: chart functions return a matplotlib Figure without error for a known-good summarise() output; zero-exposure edge case does not crash

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
