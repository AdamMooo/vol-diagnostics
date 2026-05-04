---
gsd_state_version: "1.0"
milestone: "v2.1 — POC Delivery & Validation"
status: active
last_updated: 2026-05-04
context_gathered: Phase 1
plans_ready: true
authored_local: false
cron2_pending: false
local_poc_active: true
progress: 5
---

# Project State

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-05-04 for v2.1)
See: `.planning/MILESTONES.md` (v2.0 closure recorded 2026-05-04)
See: `.planning/ROADMAP.md` (v2.1 roadmap, Phase 1 active)

**Core value:** Calibrated, quant-readable description of options-overlay environment + exposure mechanics + historical context for the quant team's weekly review. State + history, never prescriptive.

**Current focus:** v2.1 Phase 1 — POC Delivery & Calibration. 6 plans ready, 3 waves.

## Current Position

Milestone: **v2.1 — POC Delivery & Validation**
Phase: **1 of 1+** (POC Delivery & Calibration) — PLANS READY · READY TO EXECUTE
Next: `/gsd-execute-phase 1` to run all 6 plans across 3 waves.
Status: 16 decisions captured across 4 areas (audience, output, pruning, done bar). v2.0 engine is the dependency — closed and archived. Three deliverables: Bloomberg calibration, notebook artifact, walkthrough doc. Hard scope cap: no PDIV, no HMM, no new signals.
Last activity: 2026-05-04 — Phase 1 re-scoped: local-first (drop Cron2 constraint), Bloomberg deferred, Plan 01-01 dropped. 5 plans remain.

Progress: [███░░░░░░░] 20% (01-02 complete; 01-03 through 01-06 remain)

## Performance Metrics

**v2.0 final velocity (closed):**
- Engine modules shipped: 7 (`local_data`, `data_layer`, `signals`, `backtest`, `dashboard`, `stats_rigor`, `sensitivity`)
- Tests: 74 passing
- Statistical rigor: Holm-Bonferroni, stationary block bootstrap
- Honest finding: 0 of 30 bucket-mean tests survive Holm correction at FWE α=0.05

**v2.1 velocity (active):**
- Plans completed: 1 (01-02 validate.py cleanup)
- Plans pending: 4 (01-03, 01-04, 01-05, 01-06)

## Accumulated Context

### Decisions (carried forward)

**v2.0 closure (2026-05-04):**
- Engine build complete on free CBOE+FRED data; mode shift to deliver/learn warranted milestone boundary
- Phases 1-5 archived under `.planning/phases-archive/v2.0-engine/`
- Original Phase 6 "Validation Gates" re-scoped and lifted to v2.1 Phase 1

**v2.1 Phase 1 locked decisions (16, see `01-CONTEXT.md`):**
- Audience: quant team first; weekly Monday review; async handoff then meeting
- Output: Jupyter notebook (.ipynb), manual run, top-of-page current-state, charts critical
- Pruning: delete `validate.py`; reframe Section D; keep Section C + Holm
- Calibration: Bloomberg swap BEFORE delivery (synthetic 90mny IV pushback expected)
- Scope cap: no PDIV, no HMM, no new signals — locked

**Earlier (carried from v2.0):**
- Strategy menu = CC + CSP + Collar + Short Strangle (drop dispersion)
- Universe = SPX + NDX index level (POC)
- Insight framing = state + exposure + history; never prescriptive

### Pending Todos

- **Execute v2.1 Phase 1** — `/gsd-execute-phase 1` to run 6 plans across 3 waves. Wave 1: BloombergCon + validate cleanup. Wave 2: Section D reframe + notebook builder. Wave 3: chart styling + WALKTHROUGH.md.
- ~~Cron2 run gate for v2.0 Phase 1~~ — moot; v2.0 closed without Cron2 production. Bloomberg run happens as part of v2.1 Phase 1.
- **Capture for the team meeting:** Does the team already have a vol/regime/sleeve-context dashboard we shouldn't duplicate? Surface in walkthrough doc.

### Blockers/Concerns

- **Bloomberg/emds_client access required for v2.1 Phase 1** — the calibration step needs Cron2 to run. Plan needs to identify whether Bloomberg fields are pulled locally (via auth'd client) or whether Cron2 is the only path.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| v1.0 | All v1.0 phases (HMM diagnostic) | Closed without ship | 2026-04-30 |
| v2.0 | Phase 6 (original Validation Gates) | Re-scoped → v2.1 Phase 1 | 2026-05-04 |
| v2.0 | Cron2 production run | Subsumed into v2.1 Bloomberg calibration | 2026-05-04 |
| v2.0 | Phase 7 (PDIV / fund specialization) | Dropped 2026-05-04, market-general scope only | 2026-05-04 |
| v2.0 | Phase 8 (Markov-switching fragility flag) | Optional appendix, deferred indefinitely | 2026-05-04 |
| v2.1 | New signals beyond six + fragility composite | Locked OUT — only after team validates current set | 2026-05-04 |
| v2.1 | Automated weekly schedule | Manual run for POC; revisit if team uses weekly | 2026-05-04 |
| v2.1 | HTML/PDF/Slack export formats | POC ships as .ipynb; revisit if asked | 2026-05-04 |
| v2.1 | Transaction cost calibration to broker desk | Generic 0/5/10/20bp grid in current dashboard | 2026-05-04 |

## Session Continuity

Last session: 2026-05-04
Stopped at: 01-02 complete (validate.py deleted, run.py cleaned). Wave 1 done (01-01 was dropped; 01-02 is the only wave-1 plan).
Resume: Execute 01-03 (Section D reframe) — Wave 2.
