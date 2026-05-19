# Retrospective — Options Quant

---

## Milestone: v3.0 — GEX Interactive Dashboard

**Shipped:** 2026-05-06
**Phases:** 4 | **Plans:** 10

### What Was Built

- Vanna + Charm in BS engine with 0DTE guard; 31 tests
- VEX/CHEX by strike; delta-hedge $/1%, vs-yesterday email labels; 16 tests
- Streamlit dashboard: regime cards, cross-asset chart, per-ticker expanders; COM isolation
- Historical tab: ZGL trend (30-day), regime persistence table, streak counter, event study with 20-session gate; 7 tests

### What Worked

- Strict phase dependency order (1→2→3→4) meant each phase had a clean API contract to build on — no integration surprises
- `add_greeks()` pattern from Phase 1 carried cleanly into Phase 2's VEX/CHEX computation
- `streamlit_app.py` never importing emailer/run_daily was enforced from day one — made the Historical tab refactor easy
- Parquet-first snapshot store with idempotent keying meant no migration issues when schema extended

### What Was Inefficient

- Phase 3 UAT was left in `partial` state — 4 scenarios untested at milestone close; should have been cleared before closing
- Coverage gaps on data_loader, report, emailer, run_daily carried in as unaddressed debt
- Some American-style options (IWM) risk was acknowledged late rather than designed around from the start

### Patterns Established

- Email pipeline and Streamlit as parallel, fully decoupled outputs — validate one without touching the other
- `_classify_vs_yesterday()` label pattern (UNCHANGED / FLIPPED / INTENSIFIED / EASED) — reusable for other metrics
- Per-ticker `@st.cache_data(ttl=300)` + serial fetch + sleep(0.3) as yfinance 429 mitigation

### Key Lessons

- Test fixtures that don't match real data (the `gamma` column gap) silently pass and then fail in integration — fixture should mirror what the live pipeline produces
- Human UAT items should be resolved within the phase, not deferred to milestone close

---

## Cross-Milestone Trends

| Milestone | Phases | Plans | Timeline | Tests |
|-----------|--------|-------|----------|-------|
| v3.0 | 4 | 10 | 2 days | 77 |
| v2.1 | — | — | — | — |
| v2.0 | — | — | — | 74 |

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
