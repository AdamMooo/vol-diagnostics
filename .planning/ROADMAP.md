# Roadmap: Options Quant — Vol Diagnostics

## Milestones

- ✅ **v3.0–v5.0** — Phases 1–27 (shipped; see `.planning/MILESTONES.md`)
- ⏸️ **v6.0 Risk-Environment / Regime Read** — Phases 28–32 (**PLANNED, PARKED at 0%** as of 2026-08-06 — fully specified, no code written; resume with `/gsd:plan-phase 28`)

## Overview

v6.0 builds a **non-directional, second-moment barometer** — "is there too much risk in the market right now to justify putting on exposure" — surfaced in the Regime tab and daily email as *components, never a verdict*. Two bodies of work stay deliberately separate: a **descriptive barometer** that ships to surfaces (needs no forward-looking validation), and a **gated validation track** for a conditional forward-risk base rate that touches no surface until an explicit go/no-go passes. Design charter: `research/risk-environment-conditioning.md` (do not re-derive theory).

## Phases

**Phase Numbering:**
- Integer phases (28, 29, …): Planned milestone work (continues from v5.0's Phase 27)
- Decimal phases (28.1, …): Urgent insertions (marked with INSERTED)

- [ ] **Phase 28: Barometer Axes Engine** - Per-ticker level / vol-of-vol / term-slope / fragility axes + rarity-persistence, reusing existing data and monitor infra
- [ ] **Phase 29: Coupling / Absorption Meta-Read** - Cross-ticker return panel + absorption ratio distinguishing "axes agree" from "axes fused into one factor"
- [ ] **Phase 30: Barometer Surfaces** - Component barometer block in the Regime tab and daily email, credibility-gated, non-compensatory Tier-1/Tier-2, no verdict
- [ ] **Phase 31: Conditional Forward-Risk Base Rate (GATED)** - Conditional forward-risk distribution engine with effective-N error bars and mechanism/confound discipline — research artifact, not surfaced
- [ ] **Phase 32: Tail Estimation & Ship-Gate (GATED)** - EVT tail + cross-market pooling + OOS, and an explicit go/no-go recording whether the forward-risk read may graduate onto surfaces

## Phase Details

### Phase 28: Barometer Axes Engine
**Goal**: Every barometer axis is computed per ticker as an inspectable scalar plus rarity/persistence, reusing the existing deep vol-index, VRP, term-sibling, gamma, and `engine/monitor/` infrastructure — no surface yet.
**Depends on**: Nothing (first phase of milestone; builds on shipped v5.0 infra)
**Requirements**: BAR-01, BAR-02, BAR-03, BAR-04, BAR-05
**Success Criteria** (what must be TRUE):
  1. A vol-level percentile per ticker (raw vol-index level ranked against deep history) is computed and is distinct from the existing VRP percentile — retrievable via a headless call.
  2. A vol-of-vol / derivative axis (short-window rate-of-change and/or z-score of the vol index, plus VVIX percentile) is computed, expressing "vol rising vs falling."
  3. The term-slope axis (VIX9D/VIX3M) is computed for SPY and degrades gracefully — absent, not errored — for QQQ/IWM per the CBOE constraint.
  4. Dealer-gamma fragility is exposed as a Tier-2 descriptive scalar (present sign/magnitude only), carrying no historical base-rate claim.
  5. Rarity + persistence for the axes come from lighting up the existing `engine/monitor/` ranker (percentile/drift/rarity/persistence already persisted daily), not a reimplementation.
**Plans**: TBD

### Phase 29: Coupling / Absorption Meta-Read
**Goal**: A cross-ticker coupling/absorption meta-read exists that distinguishes "several independent axes agree" (confirmation) from "axes fused into one factor" (the stress-is-real state) — descriptive/coincident only.
**Depends on**: Nothing (independent build; parallel-able with Phase 28 — no shared return panel exists today)
**Requirements**: BAR-06
**Success Criteria** (what must be TRUE):
  1. A shared SPY/QQQ/IWM daily-return panel exists (built from scratch — none exists in the codebase today) and is reusable by other engine code.
  2. An absorption-ratio / correlation-collapse measure over that panel is computed and inspectable, quantifying "the tape trading as a single factor."
  3. The meta-read reports the two convergences distinctly — independent axes agreeing vs. axes correlating/fusing — never collapsing them into one number.
  4. The read is explicitly labeled descriptive/coincident, with no leading-indicator claim attached.
**Plans**: TBD

### Phase 30: Barometer Surfaces
**Goal**: The descriptive component barometer renders in both surfaces — Regime tab and daily email — as credibility-gated components with a non-compensatory Tier-1/Tier-2 split and no categorical verdict. This is the shippable barometer; it does not depend on the gated validation track.
**Depends on**: Phase 28, Phase 29
**Requirements**: BAR-07, BAR-08, BAR-09
**Success Criteria** (what must be TRUE):
  1. A whole-market barometer block renders at the top of the Regime tab (above the per-ticker columns) showing the axis components — with no categorical CALM/STRESSED label.
  2. A matching barometer block renders in the daily email between the snapshot timestamp and the VRP strip, mobile-safe, showing the same components as the dashboard.
  3. Every chip is credibility-gated via the existing `card_model.build_card_read` pattern — below-floor chips are omitted entirely, never shown with a caveat.
  4. Tier-1 (deep base rate) and Tier-2 (gamma, descriptive-only) are kept separate with no offsetting and no hidden weighting.
**Plans**: TBD
**UI hint**: yes

### Phase 31: Conditional Forward-Risk Base Rate (GATED)
**Goal**: A conditional forward-risk distribution engine exists as an inspectable research artifact with honest effective-N error bars and mechanism/confound discipline. It is surfaced nowhere and does not feed Phase 30.
**Depends on**: Phase 28 (reuses the axis scalars as conditioning variables)
**Requirements**: VAL-01, VAL-02, VAL-03
**Success Criteria** (what must be TRUE):
  1. A conditional forward-risk distribution ("days like today → forward-20d realized-vol distribution") is computed and inspectable as a research artifact — appearing on no dashboard tab or email.
  2. Confidence intervals are sized by a block/stationary bootstrap matched to vol persistence, and the artifact reports effective-N and CI width rather than raw analog-day count.
  3. Each conditioning axis carries a written structural (mechanism) reason it survives being known — no backtest-first axis selection.
  4. Slope (and each axis) is confound-checked by conditioning within level buckets before its cell is trusted.
**Plans**: TBD

### Phase 32: Tail Estimation & Ship-Gate (GATED)
**Goal**: The decision-critical fat tail is estimated with EVT + cross-market pooling and out-of-sample confirmation, and an explicit go/no-go records whether the forward-risk read may graduate onto the surfaces. A clean null is an acceptable documented outcome.
**Depends on**: Phase 31
**Requirements**: VAL-04, VAL-05
**Success Criteria** (what must be TRUE):
  1. The forward-risk tail is estimated by EVT / peaks-over-threshold (Generalized Pareto on exceedances), not k-of-N counting.
  2. Cross-market pooling (VXN/RVX and, where possible, other markets) raises the tail sample, with out-of-sample confirmation performed and recorded.
  3. A written ship-gate go/no-go decision is recorded; the forward-risk read reaches the Regime tab / email only if VAL-01–04 clear the bar.
  4. A clean null is treated as an acceptable, documented outcome — surfaces stay unchanged if the bar is not met.
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 28 → 29 → 30 → 31 → 32

The descriptive barometer (28 → 29 → 30) is shippable independently of, and before, the gated validation track (31 → 32). Phases 31–32 touch no surface until VAL-05's go/no-go passes.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 28. Barometer Axes Engine | 0/TBD | Not started | - |
| 29. Coupling / Absorption Meta-Read | 0/TBD | Not started | - |
| 30. Barometer Surfaces | 0/TBD | Not started | - |
| 31. Conditional Forward-Risk Base Rate (GATED) | 0/TBD | Not started | - |
| 32. Tail Estimation & Ship-Gate (GATED) | 0/TBD | Not started | - |

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
<!-- LINKS:END -->
