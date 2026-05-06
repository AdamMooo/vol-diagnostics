# Requirements — v3.0: GEX Interactive Dashboard

*Last updated: 2026-05-05*

## Active Requirements

### Greeks Engine

- [ ] **GRKS-01** — Vanna computed per-contract via Black-Scholes: `∂²V/∂S∂σ`
- [ ] **GRKS-02** — Charm computed per-contract via Black-Scholes: `∂²V/∂S∂t`
- [ ] **GRKS-03** — `add_greeks()` enriches chain DataFrame with `vanna` and `charm` columns alongside existing `gamma`
- [ ] **GRKS-04** — T-floor guard (`T_MIN = 1/365`) prevents charm divide-by-zero blowup on 0DTE rows; returns 0.0 for invalid rows

### Exposure Layer

- [ ] **EXP-01** — Vanna Exposure (VEX) aggregated by strike: `sign * vanna * oi * 100 * spot * 0.01`
- [ ] **EXP-02** — Charm Exposure (CHEX) aggregated by strike: `sign * charm * oi * 100 * spot * 0.01`
- [ ] **EXP-03** — Net VEX scalar and net CHEX scalar added to `summarise()` output dict
- [ ] **EXP-04** — `vanna_exposure` stored in parquet snapshot per daily run (backward-compat: old rows get NaN)

### PM Flow Analytics

- [ ] **FLOW-01** — Delta-hedge flow: `net_gex / (spot * 0.01)` — dollar volume dealers trade per 1% spot move
- [ ] **FLOW-02** — vs-yesterday: load prior trading session snapshot from parquet (previous date, not calendar -1)
- [ ] **FLOW-03** — vs-yesterday label: UNCHANGED / FLIPPED / INTENSIFIED / EASED based on GEX delta and regime
- [ ] **FLOW-04** — Daily email summary table gains delta-flow column and vs-yesterday indicator (email pipeline unchanged otherwise)

### Streamlit Dashboard

- [ ] **DASH-01** — Streamlit app launches via `streamlit run streamlit_app.py` from project root
- [ ] **DASH-02** — Ticker multi-select sidebar (all 10 default); refresh button clears `@st.cache_data` and re-fetches
- [ ] **DASH-03** — Colored regime cards: one per selected ticker showing regime + net GEX + VEX + delta-flow + vs-yesterday label
- [ ] **DASH-04** — Cross-asset overview bar chart (reuse `analytics.plot_overview()`)
- [ ] **DASH-05** — Per-ticker expander: strike GEX chart + gamma profile chart + summary table with net GEX, VEX, CHEX, zero-gamma, call wall, put wall
- [ ] **DASH-06** — `streamlit_app.py` never imports `gex.emailer` or `gex.run_daily` (win32com COM thread safety)

### Historical Tab

- [ ] **HIST-01** — Zero-gamma level trend chart: 30-day lookback per selected ticker, spot price overlaid on same axes
- [ ] **HIST-02** — Regime persistence table: % positive / negative / neutral over last 20 trading sessions per ticker
- [ ] **HIST-03** — "Days in current regime" streak counter displayed on each regime card
- [ ] **HIST-04** — Event study display for one selected ticker (gated: requires ≥20 sessions of history; shows info message if insufficient)

---

## Future Requirements (deferred)

- Live intraday refresh (sub-5-minute TTL) — yfinance rate limits make this risky at launch
- Bloomberg data swap (`data_loader.py`) — one-class change, deferred to v4.x
- Automated Task Scheduler activation for Streamlit on server startup
- Vomma (second-order vol Greek) — less PM-readable than vanna; defer
- Charm by DTE bucket chart (0-7 / 8-21 / 22+ days) — differentiator for v3.1

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Predictive signals | Holm-Bonferroni bar is high; flow-mechanics angle is more defensible |
| IV surface visualization | Scope creep; adds complexity without clear PM value |
| Live execution / order routing | Research tool only |
| Multi-user / remote deploy | Local single-user tool; no auth needed |
| Sleeve allocation framework changes | Separate v2.x track |

---

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| GRKS-01 | Phase 1 | Pending |
| GRKS-02 | Phase 1 | Pending |
| GRKS-03 | Phase 1 | Pending |
| GRKS-04 | Phase 1 | Pending |
| EXP-01 | Phase 2 | Pending |
| EXP-02 | Phase 2 | Pending |
| EXP-03 | Phase 2 | Pending |
| EXP-04 | Phase 2 | Pending |
| FLOW-01 | Phase 2 | Pending |
| FLOW-02 | Phase 2 | Pending |
| FLOW-03 | Phase 2 | Pending |
| FLOW-04 | Phase 2 | Pending |
| DASH-01 | Phase 3 | Pending |
| DASH-02 | Phase 3 | Pending |
| DASH-03 | Phase 3 | Pending |
| DASH-04 | Phase 3 | Pending |
| DASH-05 | Phase 3 | Pending |
| DASH-06 | Phase 3 | Pending |
| HIST-01 | Phase 4 | Pending |
| HIST-02 | Phase 4 | Pending |
| HIST-03 | Phase 4 | Pending |
| HIST-04 | Phase 4 | Pending |
