---
gsd_state_version: "1.0"
milestone: "v3.2 — Institutional Vol Diagnostics"
status: active
last_updated: 2026-05-26
context_gathered: true
plans_ready: true
phase_7_planned: true
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-21)

**Core value:** How expensive is protection, where on the surface is that expensiveness concentrated, and what does it imply for portfolio overlays or option-writing sleeves?
**Current focus:** v3.2 — Institutional Vol Diagnostics

## Current Position

Phase: 7 of 7 (Institutional Dashboard Rendering)
Plan: 2/2 — 07-02 Task 1 complete, awaiting UAT checkpoint
Status: In progress — blocked at human-verify checkpoint
Last activity: 2026-05-26 — 07-02 Task 1: streamlit_app.py restructured to 5-tab layout (fe44011)

Progress: [██████░░░░] 60% (v3.2)

## Performance Metrics

**Velocity:**
- Total plans completed: 8 (v3.1 Phase 5 × 3 + v3.2 Phase 6 × 4 + v3.2 Phase 7 × 1)
- Average duration: ~7 min per plan
- Current test count: 66

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 5. UAT Sign-Off & Cleanup | 3 | ~21 min | ~7 min |
| 6. Whole-Chain Computation Engine | 4 | ~35 min | ~9 min |
| 7. Institutional Dashboard Rendering | 1 | ~2 min | ~2 min |

**Recent Trend:** 07-01 complete — 3 Plotly chart primitives (plot_skew_25d_current, plot_term_structure, plot_carry_vrp) added to analytics.py with 6 smoke tests; 66 total passing.

## Accumulated Context

### Decisions

- 2026-05-26: Full strategic reframe — observable prices first, GEX secondary; build institutional vol diagnostics not a GEX monitor
- 2026-05-26: 5-module structure — Surface, Skew (25Δ), Term Structure, Carry (VRP), Flow Context (GEX demoted)
- 2026-05-26: plot_vol_surface() stripped of all GEX overlays; Viridis colorscale
- 2026-05-22: VRP (IV30 − RV20) as hedging cost context; RV20 from parquet history (not yfinance)
- 2026-05-22: Two-phase v3.2 structure — computation before rendering; cuts before additions

### Pending Todos

None.

### Blockers/Concerns

None.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| v3.2 → v3.3+ | TILT-01 OI tilt | Scoped for future | 2026-05-21 |
| v3.2 → v3.3+ | SKEW-01 Front skew gauge | Scoped for future | 2026-05-21 |
| v3.2 → v3.3+ | SURF-01 Vol surface demotion | Scoped for future | 2026-05-21 |
| v3.1 → backlog | 999.1 Charm by DTE | Parked; awaiting research | 2026-05-12 |
| v4.x | Bloomberg data swap | One-class change | 2026-05-05 |

## Session Continuity

Last session: 2026-05-26
Stopped at: 07-02 Task 1 complete — awaiting human UAT (Task 2 checkpoint). Run `streamlit run streamlit_app.py` and verify all 9 checks.
Resume file: None

**Next action:** Provide "approved" or issue description after UAT, then run `/gsd-execute-phase 7` to complete 07-02.

---
---
---
---
---
---
---
---
---
---
---
---
---
---
---
---
---
---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
