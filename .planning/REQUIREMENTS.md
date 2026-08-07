# Requirements — v6.0 Risk-Environment / Regime Read

*Last updated: 2026-08-05*

**Milestone goal:** A non-directional, second-moment barometer answering "is there too much risk in the market right now to justify putting on exposure" — surfaced in the Regime tab and daily email as components (never a verdict), with the forward-looking conditional base rate gated behind statistical validation.

**Design charter:** `research/risk-environment-conditioning.md` — do not re-derive theory. Key non-negotiables carried into requirements: barometer-not-switch (no categorical label), interpretability-first (no hidden scoring/weighting), non-compensatory Tier-1/Tier-2 maturity split, effective-N accounting, mechanism-gated axis selection, no unvalidated signal on a surface.

---

## v6.0 Requirements

### Barometer — Engine (BAR)

- [ ] **BAR-01**: A **vol-level percentile** axis is computed per ticker — the raw vol-index level ranked against deep history (distinct from the existing VRP percentile), so "how elevated is priced vol" is a first-class read.
- [ ] **BAR-02**: A **vol-of-vol / derivative** axis is computed — short-window rate-of-change and/or z-score of the vol index (and VVIX percentile) — expressing "vol rising vs falling," the axis that separates *too-much-risk* from *calming-down*.
- [ ] **BAR-03**: A **term-slope** axis surfaces the VIX9D/VIX3M ratio as a contango/backwardation read (SPY; QQQ/IWM degrade gracefully per CBOE constraint).
- [ ] **BAR-04**: A **fragility** axis surfaces dealer-gamma sign (stabilizing/amplifying) as **Tier-2, shown-not-scored** — descriptive of the present, with no historical base-rate claim (respects the ~months-only gamma history).
- [ ] **BAR-05**: **Rarity + persistence** for the barometer axes are surfaced by lighting up the dormant `engine/monitor/` engine (percentile / drift / rarity / persistence already computed daily, currently surfaced nowhere) rather than rebuilding.
- [ ] **BAR-06**: A **coupling / absorption meta-read** is computed cross-ticker (shared SPY/QQQ/IWM return panel + absorption-ratio / correlation-collapse measure), distinguishing "several independent axes agree" (confirmation) from "axes fused into one factor" (the stress-is-real state). Descriptive/coincident only — no leading-indicator claim.

### Barometer — Surfaces (BAR)

- [ ] **BAR-07**: A whole-market **barometer block renders in the Regime tab** (top of `_render_regime_cards`, above the per-ticker columns) — component panel, credibility-gated, reusing the `card_model.build_card_read` gating pattern; no categorical CALM/STRESSED label.
- [ ] **BAR-08**: A **barometer block renders in the daily email** (slot between the snapshot timestamp and the VRP strip), mobile-safe, showing the same components as the dashboard.
- [ ] **BAR-09**: **Credibility gating + non-compensatory maturity tiering** governs every chip — omit-if-below-floor (never shown with a caveat), Tier-1 (deep base rate) vs Tier-2 (gamma, descriptive-only) kept separate with no offsetting, no hidden weighting, no verdict.

### Validation Track — GATED (VAL)

*Does NOT touch the Regime tab or email until VAL-05 passes. This is research/validation, not a surface.*

- [ ] **VAL-01**: **Effective-N accounting** for any conditional base rate — Stambaugh/Hodrick overlapping-observation correction; conditional-distribution point estimate from the full sample but confidence intervals sized by a block/stationary bootstrap matched to persistence; effective-N and CI width are what the credibility gate would display.
- [ ] **VAL-02**: **Mechanism-gated axis selection + confound-check** — each conditioning axis has a written structural reason it survives being known (no backtest-first selection, D-10); slope (and every axis) confound-checked by conditioning within level buckets before its cell is trusted.
- [ ] **VAL-03**: A **conditional forward-risk distribution** engine ("days like today → forward-20d realized-vol distribution") exists as a research artifact — computed and inspectable, **not surfaced**.
- [ ] **VAL-04**: **Tail estimation** uses EVT / peaks-over-threshold (Generalized Pareto on exceedances, not k-of-N counting) plus cross-market pooling (VXN/RVX and, where possible, other markets), with out-of-sample confirmation — the tail is treated as the weakest, most decision-relevant estimate.
- [ ] **VAL-05**: An explicit **ship-gate go/no-go** decision is recorded — the forward-risk read graduates onto the Regime tab / email only if VAL-01–04 clear the bar; a clean null is an acceptable, documented outcome (as with the covered-call investigation).

---

## Future Requirements (deferred)

- **SEED-001** — short-end 0DTE / front-expiry gamma concentration as a richer fragility sub-read (parked 2026-08-05; pull into a later phase once the barometer skeleton exists).
- Leading-indicator use of the absorption/coupling read (currently descriptive-coincident only) — would require the full VAL gauntlet on its own.

## Out of Scope

| Excluded | Reason |
|----------|--------|
| Any buy/sell/direction claim | First-moment forecasting; the entire milestone is deliberately second-moment only |
| Categorical CALM/STRESSED regime label | Repo has twice killed hand-tuned/non-stationary categorical regime labels; barometer-not-switch is a hard boundary |
| Hidden scoring / weighted composite of axes | Interpretability-first; conditional base rates + components primary |
| Shipping the forward-risk base rate before VAL-05 | No unvalidated signal on a surface — self-imposed discipline |
| Intraday / real-time barometer | CBOE CDN is delayed; unchanged from project-wide constraint |

## Traceability

Each REQ maps to exactly one phase. 14/14 mapped.

| REQ-ID | Phase | Track |
|--------|-------|-------|
| BAR-01 | Phase 28 | Barometer (ships to surfaces) |
| BAR-02 | Phase 28 | Barometer (ships to surfaces) |
| BAR-03 | Phase 28 | Barometer (ships to surfaces) |
| BAR-04 | Phase 28 | Barometer (ships to surfaces) |
| BAR-05 | Phase 28 | Barometer (ships to surfaces) |
| BAR-06 | Phase 29 | Barometer (ships to surfaces) |
| BAR-07 | Phase 30 | Barometer (ships to surfaces) |
| BAR-08 | Phase 30 | Barometer (ships to surfaces) |
| BAR-09 | Phase 30 | Barometer (ships to surfaces) |
| VAL-01 | Phase 31 | Gated validation (no surface until VAL-05) |
| VAL-02 | Phase 31 | Gated validation (no surface until VAL-05) |
| VAL-03 | Phase 31 | Gated validation (no surface until VAL-05) |
| VAL-04 | Phase 32 | Gated validation (no surface until VAL-05) |
| VAL-05 | Phase 32 | Gated validation (ship-gate go/no-go) |

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
<!-- LINKS:END -->
