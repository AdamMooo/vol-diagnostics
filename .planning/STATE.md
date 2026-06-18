---
gsd_state_version: 1.0
milestone: v3.5
milestone_name: Index Vol-Context Rebuild
status: executing
stopped_at: Completed 16-02-PLAN.md (VRP percentile wiring)
last_updated: "2026-06-16T20:04:21.558Z"
last_activity: 2026-06-16
progress:
  total_phases: 8
  completed_phases: 4
  total_plans: 8
  completed_plans: 8
  percent: 50
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-04)

**Core value:** How expensive is protection, where on the surface is that expensiveness concentrated, how is the surface moving over time, and what does it imply for portfolio overlays or option-writing sleeves?
**Current focus:** Phase 16 — vrp percentile

## Current Position

Phase: 16
Plan: 16-02 complete (Phase 16 done)
Status: Executing
Last activity: 2026-06-16

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**

- Total plans completed: 32 (v3.1 ×3, v3.2 ×6, v3.3 ×12, phases 8–11) + 4 (v3.4 phases 12–13)
- Average duration: ~7 min per plan
- Current test count: 66

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 5. UAT Sign-Off & Cleanup | 3 | ~21 min | ~7 min |
| 6. Whole-Chain Computation Engine | 4 | ~35 min | ~9 min |
| 7. Institutional Dashboard Rendering | 2 | ~4 min | ~2 min |
| 9. Surface Evolution Engine | 3 | - | - |
| 10. Dashboard Restructure | 2 | - | - |
| 11. Richer Daily Report | 4 | - | - |
| Phase 12-canonical-card P01 | 15 min | 2 tasks | 4 files |
| Phase 12-canonical-card P02 | 10 min | 2 tasks | 2 files |
| Phase 12-canonical-card P03 | 10 min | 2 tasks | 2 files |
| 13 | 1 | - | - |
| 15 | 2 | - | - |
| 16-vrp-percentile P01 | ~2 min | 2 tasks | 3 files |
| 16-vrp-percentile P02 | ~12 min | 2 tasks | 4 files |

## Accumulated Context

### Decisions

- 2026-06-16: Phase 16-02 — Displayed VRP scalar switched from snapshot.iv30 − RV20 to vol_index − RV20 (LOCKED CONTEXT); scalar + percentile share one series and cannot drift. vrp_pct/vrp_pct_n precomputed in compute_ticker; build_card_fields stays I/O-free. One VRP CardField (index 8, after Skew) reaches both email and dashboard via the PAR-01 seam. _fetch_spot_history_yf widened 35d→400d.
- 2026-06-16: Phase 16-01 — VRP percentile built from one vol-index-based series (`vol_index − RV20×100`, vol points); snapshot-IV30 `vrp` column never enters the history (VRP-03). `percentileofscore(kind="rank")` for uniformity with the skew percentile. Cold-start returns actual count n; failure paths return None-dict, never raise. Engine isolated in `gex/vrp_history.py` so 16-02 only wires it.
- 2026-06-04: v3.5 roadmap — 4 phases (15–18). VIDX data layer first (foundation); VRP percentile and term-structure regime are separate phases (distinct deliverables, both depend on VIDX); 3-page reorg + email parity + gating last (presentation layer, depends on both metrics). GATE-01/02 folded into Phase 18 (display-layer safety net for the same page-1 reorg).
- 2026-06-01: v3.4 1d-change framing — the 1-day ΔIV surface in the email is a DESCRIPTIVE daily glance, NOT a signal in the evolution engine. Does not reverse the 2026-05-30 "no 1d in evolution horizons" decision. Resolved via `nth_trading_day_back(ticker, today, 1)`.
- 2026-06-01: Scheduler IS firing — Task Scheduler "GEX Daily Report" runs weekdays 4:30pm ET. SETUP FLAW: `DisallowStartIfOnBatteries=True` caused silent skips on battery. Fix: elevated PowerShell set both battery flags false + RestartCount=2/PT5M. RESOLVED 2026-06-01 (Adam ran it).
- 2026-05-30: ΔIV horizons locked {5,10,20}; 1-day excluded from evolution engine.
- 2026-05-30: Coverage mask = convex hull (not kNN) — parameter-free, 92%+ coverage.
- [Phase ?]: CardField + build_card_fields() is single source of truth for card fields; both renderers iterate the list
- [Phase ?]: iv30 already in _FLOAT_COLS/save_snapshot — no schema change; load_prior_snapshot was the missing piece
- [Phase ?]: _wall_value in card_model.py is renderer-agnostic plain text; report.py adds HTML span in plan 02
- [Phase ?]: _ticker_card() delegates field construction to build_card_fields(); no local field logic remains in report.py
- [Phase ?]: render_regime_card delegates field construction to build_card_fields(); no local field logic remains in streamlit_app
- [Phase ?]: patch target for load_prior_snapshot in dashboard tests is streamlit_app.load_prior_snapshot — from-import creates a direct reference

### Pending Todos

- None. (Phase 14 was superseded by Phase 18 per the 2026-06-04 roadmap — GATE-01/02 carried forward; it is NOT incomplete work and does not block Phase 15.)

### Blockers/Concerns

None.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| v4.x | Inline `cid:` email images (vs attachments) | Requires Outlook COM PropertyAccessor plumbing | 2026-05-29 |
| v4.x | Bloomberg data swap | One-class change in data_loader.py | 2026-05-05 |
| v3.x | Large OI blocks expiring soon | Needs parameter-free design (no hand-tuned cutoff) | 2026-06-01 |
| backlog | 999.1 Charm by DTE | Parked; awaiting research | 2026-05-12 |

## Session Continuity

Last session: 2026-06-18
Stopped at: Surface spike (branch spike/vol-surface-beast) — interactive surface/compare/video shipped into app.py, card "read" layer + credibility gating, GEX capped ≤90 DTE. Paused before launching the UI audit.
Resume file: spike/SPIKE.md (NEXT section) — start with gsd-ui-auditor, then @st.fragment de-lag, then merge + Phase 17.

---
---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
