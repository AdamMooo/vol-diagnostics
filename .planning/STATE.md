---
gsd_state_version: "1.0"
milestone: "v2.0 — Sleeve Allocation Framework"
status: active
last_updated: 2026-04-30
context_gathered: Phase 7
progress: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-30)
See: .planning/MILESTONES.md (v1.0 pivot rationale)

**Core value:** PM-readable scorecard of options-overlay sleeve attractiveness across SPX/QQQ (and optionally XIU/XSP), backed by sleeve P&L backtests, conditioned on a transparent signal panel.
**Current focus:** Phase 7 — Extended Data Layer (start of Phase α — engine)

## Current Position

Phase: 7 of 14 (Extended Data Layer) — NOT STARTED
Next: `/gsd-discuss-phase 7` then `/gsd-plan-phase 7`
Status: Milestone v2.0 freshly defined; data probes confirmed `con.bdh` IV fields work
Last activity: 2026-04-30 — milestone v2.0 created after sleeve-pivot audit; PROJECT.md, REQUIREMENTS.md, ROADMAP.md, MILESTONES.md written

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0 (this milestone)
- Average duration: —
- Total execution time: —

## Accumulated Context

### Decisions (carried forward — see PROJECT.md Strategic Decisions for full list)

- 2026-04-30: Pivot from v1.0 HMM to v2.0 Sleeve Framework (audit-driven)
- 2026-04-30: Scorecard primary, HMM optional — PM-auditable, governance-friendly
- 2026-04-30: Strategy menu = CC + CSP + Collar + ShortStrangle. Drop dispersion
- 2026-04-30: `30DAY_IMPVOL_100.0%MNY_DF` and `30DAY_IMPVOL_90.0%MNY_DF` confirmed working via `con.bdh` (emds_client)
- 2026-04-30: Engine first (α), then specialize (β); HMM (γ) is appendix-only

### Pending Todos

- Capture PDIV's current overlay rule (gate for Phase 13/β)
- Probe XIU and XSP IV field availability during Phase 7

### Blockers/Concerns

- None active. PDIV overlay rule capture is a Phase β prerequisite, not a Phase α blocker.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| v1.0 | Phase 3-6 server run + completion (HMM diagnostic) | Pivoted — not in v2.0 scope | 2026-04-30 |
| v2.0 | Dispersion / implied-correlation sleeve | Out of scope (dealer/HF turf) | Init |
| v2.0 | Phase γ (Markov-switching fragility flag) | Optional — only after Phase α/β green | Init |

## Session Continuity

Last session: 2026-04-30
Stopped at: Milestone v2.0 initialization complete (PROJECT, REQUIREMENTS, ROADMAP, MILESTONES, STATE written)
Resume: `/gsd-discuss-phase 7` to gather context for Extended Data Layer, or `/gsd-plan-phase 7` to skip discussion and plan directly
