---
gsd_state_version: "1.0"
milestone: "v2.0 — Sleeve Allocation Framework (α only, market-general)"
status: active
last_updated: 2026-05-04
context_gathered: Phase 1
plans_ready: Phase 1
authored_local: Phase 1
cron2_pending: Phase 1
local_poc_active: true
progress: 17
---

# Project State

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-04-30)
See: `.planning/MILESTONES.md` (v1.0 pivot rationale)

**Core value:** PM-readable scorecard of options-overlay sleeve attractiveness across SPX/QQQ (and optionally XIU/XSP), backed by sleeve P&L backtests, conditioned on a transparent signal panel.

**Current focus:** Phase 2 — Signal Engineering, **on the local POC track** (`sleeve_alpha_dev.ipynb`). v1.0 (HMM) closed/archived. Phase β (PDIV specialization) dropped 2026-05-04 — scope is α only, market-general.

## Current Position

Phase: **1 of 6** (Extended Data Layer) — DONE on both tracks
- Cron2/Bloomberg track: `sleeve_alpha.ipynb` authored locally; Cron2 run pending (deferred — local POC takes priority)
- Local POC track: `sleeve_alpha_dev.ipynb` runs end-to-end with CBOE+FRED data, panels match Cron2 identifier contract verbatim

Next: `/gsd-plan-phase 2` — Signal Engineering (RV, VRP, term, skew, trend, drawdown, fragility composite) on the local track.
Status: 4 plans authored Cron2-side, 16-cell dev notebook executes clean locally. SPX (CBOE) + NDX (FRED) panels both populated, 4107 obs from 2010-01-04. VVIX deferred (no free historical), XIU/XSP deferred (Canadian, revisit on Bloomberg).
Last activity: 2026-05-04 — local POC scaffold + α-only scope pivot

Progress: [██░░░░░░░░] 17% (1/6 phases done on POC track)

## Performance Metrics

**Velocity:**
- Total plans completed (locally authored): 4 (this milestone — Phase 1: 01-01..01-04)
- Plans Cron2-confirmed: 0 (pending operator run on first phase)
- Total execution time: ~30 min local (Phase 1, 4 plans, 8 atomic feat commits + 4 doc commits)

## Accumulated Context

### Decisions (carried forward — see PROJECT.md Strategic Decisions for full list)

- 2026-05-04: **Drop Phase β (PDIV specialization)** — scope simplified to market-general scorecard only; quant team uses for broader trading view
- 2026-05-04: Local POC dev path adopted — `sleeve_alpha_dev.ipynb` + `local_data.py` against CBOE+FRED official sources; math ports back to Cron2/Bloomberg verbatim
- 2026-05-04: yfinance rejected in favour of CBOE direct CSV + FRED — all-official data publishers, zero scrapers
- 2026-05-04: Universe trimmed to SPX + NDX index level (matches what VIX/VXN measure); QQQ ETF/Canadian add back on Bloomberg
- 2026-04-30: Pivot from v1.0 HMM to v2.0 Sleeve Framework (audit-driven)
- 2026-04-30: Scorecard primary, HMM optional — PM-auditable, governance-friendly
- 2026-04-30: Strategy menu = CC + CSP + Collar + ShortStrangle. Drop dispersion
- 2026-04-30: `30DAY_IMPVOL_100.0%MNY_DF` and `30DAY_IMPVOL_90.0%MNY_DF` confirmed working via `con.bdh` (emds_client)
- 2026-04-30: Phase numbering reset to 1 for v2.0 (v1.0 phases archived to `.planning/phases-archive/v1.0-hmm/`)

### Pending Todos

- **Cron2 run gate for Phase 1** — deprioritized while local POC is the active track. Open `sleeve_alpha.ipynb` on Cron2, Run All, confirm panels land — only after POC produces math worth porting.
- ~~Capture PDIV's current overlay rule (gate for Phase 7/β)~~ — N/A; Phase β dropped 2026-05-04
- ~~Probe XIU and XSP IV field availability during Phase 1~~ — folded into Phase 1 Plan 02 (`[landed]/[deferred]` log); Canadian deferred to Bloomberg
- ~~Probe `90DAY_IMPVOL_100.0%MNY_DF` for term structure during Phase 1~~ — folded into Phase 1 Plan 01 `IV_FIELDS["iv90_atm"]`

### Blockers/Concerns

- None active. PDIV overlay rule capture is a Phase β prerequisite, not a Phase α blocker.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| v1.0 | All v1.0 phases (1-6 HMM diagnostic) | Closed without ship — `.planning/phases-archive/v1.0-hmm/` | 2026-04-30 |
| v2.0 | Dispersion / implied-correlation sleeve | Out of scope (dealer/HF turf) | Init |
| v2.0 | Phase β (PDIV specialization) | **Dropped** — market-general scope only | 2026-05-04 |
| v2.0 | XIU / XSP (Canadian) | Deferred — no free official source; revisit on Bloomberg | 2026-05-04 |
| v2.0 | VVIX | Deferred — no free historical; revisit on Bloomberg | 2026-05-04 |
| v2.0 | Phase γ (Markov-switching fragility flag) | Optional — only after Phase α green | Init |

## Session Continuity

Last session: 2026-05-04
Stopped at: Local POC scaffolded — `local_data.py` (CBOE+FRED), `sleeve_alpha_dev.ipynb` runs end-to-end, panels match Cron2 contract. Scope pivoted to α-only/market-general. Ready for Phase 2 math.
Resume: `/gsd-plan-phase 2` for Signal Engineering on the POC track.
