---
gsd_state_version: "1.0"
milestone: "v2.0 — Sleeve Allocation Framework"
status: active
last_updated: 2026-04-30
context_gathered: Phase 1
plans_ready: Phase 1
authored_local: Phase 1
cron2_pending: Phase 1
progress: 12
---

# Project State

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-04-30)
See: `.planning/MILESTONES.md` (v1.0 pivot rationale)

**Core value:** PM-readable scorecard of options-overlay sleeve attractiveness across SPX/QQQ (and optionally XIU/XSP), backed by sleeve P&L backtests, conditioned on a transparent signal panel.

**Current focus:** Phase 1 — Extended Data Layer (start of Phase α — engine). v1.0 (HMM) is closed and archived; do not work on it.

## Current Position

Phase: **1 of 8** (Extended Data Layer) — AUTHORED LOCAL · CRON2 RUN PENDING
Next: Open `sleeve_alpha.ipynb` on Cron2, Run All, confirm fresh-kernel pass + freshness/QA tables. Then `/gsd-plan-phase 2`.
Status: All 4 plans executed locally. `sleeve_alpha.ipynb` has 20 cells (valid nbformat v4); 11 atomic commits. gsd-verifier source-level: PASSED (62/62 identifier greps, 8/8 plan acceptance checks, all D-01..D-13 honored, `hmm.ipynb` byte-identical). Cron2-run gate (5 items) is the operator's confirmation step.
Last activity: 2026-04-30 — Phase 1 execution complete (local); Cron2 run pending

Progress: [█░░░░░░░░░] 12% (1/8 phases authored; 0/8 phases Cron2-confirmed)

## Performance Metrics

**Velocity:**
- Total plans completed (locally authored): 4 (this milestone — Phase 1: 01-01..01-04)
- Plans Cron2-confirmed: 0 (pending operator run on first phase)
- Total execution time: ~30 min local (Phase 1, 4 plans, 8 atomic feat commits + 4 doc commits)

## Accumulated Context

### Decisions (carried forward — see PROJECT.md Strategic Decisions for full list)

- 2026-04-30: Pivot from v1.0 HMM to v2.0 Sleeve Framework (audit-driven)
- 2026-04-30: Scorecard primary, HMM optional — PM-auditable, governance-friendly
- 2026-04-30: Strategy menu = CC + CSP + Collar + ShortStrangle. Drop dispersion
- 2026-04-30: `30DAY_IMPVOL_100.0%MNY_DF` and `30DAY_IMPVOL_90.0%MNY_DF` confirmed working via `con.bdh` (emds_client)
- 2026-04-30: Engine first (α), then specialize (β); HMM (γ) is appendix-only
- 2026-04-30: Phase numbering reset to 1 for v2.0 (v1.0 phases archived to `.planning/phases-archive/v1.0-hmm/`)

### Pending Todos

- **Cron2 run gate for Phase 1** — open `sleeve_alpha.ipynb` on Cron2, Run All on a fresh kernel, confirm: (1) no exception; (2) SPX/QQQ price + iv30_atm + iv30_90mny all land; (3) XIU/XSP landed-or-deferred verdict captured; (4) VIX lands; rf_rate verdict captured; (5) `freshness_table` and `qa_table` print as expected. Update verifier status from `human_needed` → `passed` after.
- Capture PDIV's current overlay rule (gate for Phase 7/β)
- ~~Probe XIU and XSP IV field availability during Phase 1~~ — folded into Phase 1 Plan 02 (`[landed]/[deferred]` log)
- ~~Probe `90DAY_IMPVOL_100.0%MNY_DF` for term structure during Phase 1~~ — folded into Phase 1 Plan 01 `IV_FIELDS["iv90_atm"]`

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
Stopped at: Phase 1 authored locally; awaiting operator Cron2 run (5-item gate). VERIFICATION.md at `.planning/phases/01-extended-data-layer/01-VERIFICATION.md`.
Resume: After Cron2 confirms green → `/gsd-plan-phase 2` (Signal Engineering). If Cron2 surfaces a defect → `/gsd-debug` or `/gsd-plan-phase 1 --gaps`.
