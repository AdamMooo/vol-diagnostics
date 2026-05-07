---
gsd_state_version: "1.0"
milestone: "v3.1 — Hardening & Charm"
status: active
last_updated: 2026-05-06 (v3.1 milestone started)
context_gathered: true
plans_ready: false
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-06)

**Core value:** Given today's dealer positioning across SPY/QQQ/IWM — what regime are we in, how much dealer hedging flow will a 1% move generate, and where are the structural levels that matter?
**Current focus:** v3.1 — Hardening & Charm

## Current Position

Phase: Not started (defining roadmap)
Plan: —
Status: Defining requirements
Last activity: 2026-05-06 — Milestone v3.1 started

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:** -

## Accumulated Context

### Decisions

- 2026-05-05: Vanna over Vomma — delta shift per vol point is PM-readable; Vomma is not
- 2026-05-05: Streamlit additive — email pipeline (run_daily.py → Outlook COM) stays intact unchanged
- 2026-05-05: Phase order strictly 1→2→3→4 — each phase is a hard dependency on the prior
- 2026-05-05: No new data sources — yfinance + existing parquet only through v3.0

### Pending Todos

None.

### Blockers/Concerns

- Phase 2: ~~Verify `zero_gamma_level` exists in parquet schema~~ — confirmed present in live parquet, no action needed
- Phase 3: yfinance 429 on cold load — use per-ticker `@st.cache_data(ttl=300)` + serial fetch with sleep(0.3)
- Phase 4: Event study requires 60+ sessions meaningful signal; HIST-04 gates UI at 20 sessions minimum

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| v4.x | Bloomberg data swap | One-class change in data_loader.py | 2026-05-05 |
| v3.1 | Charm by DTE bucket chart | Differentiator, not MVP | 2026-05-05 |
| v3.1 | Live intraday refresh | yfinance rate limits risky at launch | 2026-05-05 |
| Post-v3.0 | Task Scheduler / Streamlit autostart | After PM desk validates dashboard | 2026-05-05 |
| v2.x | NDX skew identity bug | Sleeve framework track | 2026-05-04 |

Items acknowledged and deferred at milestone close on 2026-05-06:

| Category | Item | Status |
|----------|------|--------|
| uat | Phase 03: 03-HUMAN-UAT.md | partial — 4 pending scenarios |
| verification | Phase 03: 03-VERIFICATION.md | human_needed |

## Session Continuity

Last session: 2026-05-06
Stopped at: Phase 4 context gathered — ready to plan
Resume file: .planning/phases/04-historical-tab/04-CONTEXT.md
