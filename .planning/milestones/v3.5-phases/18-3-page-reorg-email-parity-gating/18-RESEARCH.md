# Phase 18: 3-Page Reorg + Email Parity + Gating - Research

**Researched:** 2026-06-24  
**Confidence:** High

## Goal Fit

Phase 18 is a presentation-layer reorganization with strict cross-surface parity:
1. Page 1 becomes the PM-facing regime snapshot.
2. Page 2 contains surface workflows (Today/Compare/Evolution).
3. Page 3 contains full positioning/GEX/OI mechanics.
4. Shared card numbers/ordering/formatting must stay canonical across dashboard and email.

No engine math changes are required to deliver the phase objective.

## Locked Inputs from Context

- Top-level tabs are the primary page switch.
- Evolution belongs under the Surfaces page.
- Page 1 defaults to all three ticker cards.
- Page 1 compact hierarchy is regime-first.
- Trust tags remain visible by default.
- History-dependent states are explicit per metric ("building to N", "needs >=N sessions").
- Email parity is strict for shared fields, with warning-grade drift checks.

## Existing Implementation Seams to Reuse

### Canonical card contract
- `engine/report/card_model.py` `build_card_fields()` is already the shared field source.
- `split_compact_fields()` already supports compact-vs-detail layout.
- Trust-tag resolution is already centralized.

### Dashboard composition
- `app.py` already has top-level tabs (`Surface`, `Evolution`, `Positioning`) and ticker toggles for heavy sections.
- Regime cards are already rendered via canonical card fields.

### Email composition
- `engine/report/report.py` `_ticker_card()` already consumes `build_card_fields()`.
- Cold-start omission behavior already exists for history-heavy sections.

### Data/compute layer
- `engine/compute.py` already emits summary fields required for page-1 regime reads and gating labels.
- No new store schema is needed for this phase.

## Key Risks

1. **Parity drift risk** if dashboard page-1 selects/reorders fields differently than email.
2. **Inconsistent gating copy** if page-1 widgets use ad-hoc captions instead of centralized thresholds/state strings.
3. **Scope bleed** into new analytics or compute changes (out of phase scope).

## Recommended Planning Shape

### Plan A — Page architecture refactor
- Recompose current tabs into explicit 3-page structure in `app.py`.
- Route existing surface/evolution blocks into page 2.
- Route full positioning/OI/GEX blocks into page 3.

### Plan B — Canonical parity + hierarchy
- Define explicit page-1 compact field selection/order from canonical field list.
- Use same canonical values/formatting for email and page-1 shared fields.
- Keep unavailable-by-design rows omitted in both surfaces.

### Plan C — Gating standardization + warning checks
- Normalize metric-specific "building/needs >=N sessions" behavior on page 1.
- Ensure email uses matching cold-start behavior for card-level vs section-level content.
- Add warning-grade parity drift checks in tests (not hard-fail gate for this phase).

## Files Most Relevant for Planning

- `.planning/phases/18-3-page-reorg-email-parity-gating/18-CONTEXT.md`
- `.planning/REQUIREMENTS.md`
- `.planning/ROADMAP.md`
- `app.py`
- `engine/report/card_model.py`
- `engine/report/report.py`
- `engine/compute.py`
- `engine/tests/test_app.py`
- `engine/tests/test_report.py`
- `engine/tests/test_card_model.py`

## Out-of-Scope Guardrails

- No predictive scoring or new signals.
- No changes to core vol/GEX formulas.
- No new data sources or schema migrations.
- No extension beyond SPY/QQQ/IWM parity rules already locked in prior phases.

## Research Conclusion

Phase 18 is ready for planning immediately. The strongest plan sequence is:
1. **Recompose UI pages** (layout only, no metric semantics changes),
2. **Harden canonical parity path** (shared field contract and ordering),
3. **Standardize gating UX + warning-grade parity checks**.

## RESEARCH COMPLETE
