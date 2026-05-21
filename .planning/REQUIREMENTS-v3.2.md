# Requirements — v3.2 Actionable Positioning Context

*Defined: 2026-05-21*
*Core Value: Should a PM pay up for protection right now, and is the dealer-driven vol environment suppressing or amplifying moves?*

---

## v3.2 Requirements

### Positioning Context

- [ ] **NARR-01**: Dashboard and email always show a mechanical positioning narrative explaining what GEX sign means (positive = dealers long gamma = sell rallies/buy dips = vol suppression; negative = short gamma = chase moves = vol amplification). Frozen template text, no dynamic generation.
- [ ] **NARR-02**: Dashboard card shows GEX percentile rank vs trailing 60-day history ("82nd percentile") with graceful degradation below 30 observations ("building context, N sessions").

### Volatility Context

- [ ] **CTX-01**: Dashboard and email show VRP (IV30 − RV20) with interpretation label ("options rich" / "options cheap" relative to realized vol).
- [ ] **CTX-02**: RV20 computed from close-to-close log-return std × √252, sourced from parquet spot history with yfinance backfill as fallback. Graceful degradation if fewer than 20 sessions available.

### Output Cleanup

- [ ] **CUT-01**: Remove from regime cards: Hedge Sh/$1 row, % vs ZGL observation line.
- [ ] **CUT-02**: Remove from Vol tab: strike slope metric widget, term slope metric widget.
- [ ] **CUT-03**: Remove `compute_surface_slopes()` call from `compute.py` pipeline (dead code after CUT-02).

### Infrastructure

- [ ] **INFRA-01**: New `gex/positioning.py` module with pure functions: `compute_rv20()`, `compute_vrp()`, `gex_percentile()`, `positioning_narrative()`.
- [ ] **INFRA-02**: Parquet snapshot schema extended with `rv20`, `vrp` fields (NaN for cold-start sessions; forward-compatible with existing load_history pattern).

## Future Requirements (v3.3+)

### Deferred from v3.2

- **TILT-01**: OI tilt — dollar-weighted put vs call OI with moneyness filter and covered-call caveat
- **SKEW-01**: Front skew gauge with percentile rank on card
- **SURF-01**: Vol surface demotion to collapsed/optional section
- **RV-01**: Yang-Zhang RV estimator upgrade (close-to-close sufficient for v3.2)

### Backlog (from v3.1)

- **CHARM-01/02**: Charm by DTE chart — requires validated charm methodology (999.1)
- **COV-01–05**: Critical-path test coverage expansion (999.2)
- **DIST-01/04**: Pre-distribution hardening remainder (999.3)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Composite scoring / traffic lights | Each metric stands alone — compound signals repeat the regime label mistake (v3.0 lesson) |
| Dynamic narrative generation | Frozen templates only — avoid implying prediction or over-claiming |
| Predictive signals from VRP/GEX | Descriptive metrics only — no "expect X" language |
| OI tilt directional labels | "Bullish/bearish" labeling not defensible — covered-call programs distort put/call ratio |
| Real-time VRP updates | RV20 is a daily metric; intraday updates meaningless |
| Bloomberg data swap | Deferred to v4.x — one-class swap in data_loader.py |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| NARR-01 | TBD | Pending |
| NARR-02 | TBD | Pending |
| CTX-01 | TBD | Pending |
| CTX-02 | TBD | Pending |
| CUT-01 | TBD | Pending |
| CUT-02 | TBD | Pending |
| CUT-03 | TBD | Pending |
| INFRA-01 | TBD | Pending |
| INFRA-02 | TBD | Pending |

**Coverage:**
- v3.2 requirements: 9 total
- Mapped to phases: 0 (pending roadmap)
- Unmapped: 9

---
*Requirements defined: 2026-05-21*
*Last updated: 2026-05-21 after milestone initialization*
