---
gsd_state_version: "1.0"
milestone: "v2.0 — Sleeve Allocation Framework"
status: active
last_updated: 2026-04-30
context_gathered: Phase 1
progress: 0
---

# Project State

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-04-30)
See: `.planning/MILESTONES.md` (v1.0 pivot rationale)

**Core value:** PM-readable scorecard of options-overlay sleeve attractiveness across SPX/QQQ (and optionally XIU/XSP), backed by sleeve P&L backtests, conditioned on a transparent signal panel.

**Current focus:** Phase 1 — Extended Data Layer (start of Phase α — engine). v1.0 (HMM) is closed and archived; do not work on it.

## Current Position

Phase: **1 of 8** (Extended Data Layer) — NOT STARTED
Next: `/gsd-discuss-phase 1` then `/gsd-plan-phase 1`
Status: Milestone v2.0 freshly defined; phases renumbered 1-8 to make focus unambiguous; v1.0 phases archived
Last activity: 2026-04-30 — milestone v2.0 created after sleeve-pivot audit; phase numbering reset to 1

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
- 2026-04-30: Phase numbering reset to 1 for v2.0 (v1.0 phases archived to `.planning/phases-archive/v1.0-hmm/`)

### Pending Todos

- Capture PDIV's current overlay rule (gate for Phase 7/β)
- Probe XIU and XSP IV field availability during Phase 1
- Probe `90DAY_IMPVOL_100.0%MNY_DF` for term structure during Phase 1

### Blockers/Concerns

- None active. PDIV overlay rule capture is a Phase β prerequisite, not a Phase α blocker.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| v1.0 | All v1.0 phases (1-6 HMM diagnostic) | Closed without ship — `.planning/phases-archive/v1.0-hmm/` | 2026-04-30 |
| v2.0 | Dispersion / implied-correlation sleeve | Out of scope (dealer/HF turf) | Init |
| v2.0 | Phase γ (Markov-switching fragility flag) | Optional — only after Phase α/β green | Init |

## Session Continuity

Last session: 2026-04-30
Stopped at: Milestone v2.0 initialization complete (PROJECT, REQUIREMENTS, ROADMAP, MILESTONES, STATE written; phases renumbered 1-8; v1.0 archived)
Resume: `/gsd-discuss-phase 1` to gather context for Extended Data Layer, or `/gsd-plan-phase 1` to skip discussion and plan directly
