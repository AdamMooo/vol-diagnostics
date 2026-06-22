---
gsd_state_version: 1.0
milestone: v3.5
milestone_name: Index Vol-Context Rebuild
status: planning
stopped_at: Phase 16.5 context gathered
last_updated: "2026-06-22T20:07:52.427Z"
last_activity: 2026-06-21
progress:
  total_phases: 10
  completed_phases: 4
  total_plans: 8
  completed_plans: 8
  percent: 40
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-04)

**Core value:** How expensive is protection, where on the surface is that expensiveness concentrated, how is the surface moving over time, and what does it imply for portfolio overlays or option-writing sleeves?
**Current focus:** Phase 16.5 — OI Depth Expansion (next)

## Current Position

Phase: 16.5
Plan: Not started (next up)
Status: Planning
Last activity: 2026-06-21

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

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260621-v8g | UI pass-2 polish: unify axis K/S labels, fix radio labels, trim redundant card rows, @st.fragment de-lag | 2026-06-22 | c92ddaf | [260621-v8g-ui-pass-2-polish-unify-axis-k-s-labels-f](./quick/260621-v8g-ui-pass-2-polish-unify-axis-k-s-labels-f/) |

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| v4.x | Inline `cid:` email images (vs attachments) | Requires Outlook COM PropertyAccessor plumbing | 2026-05-29 |
| v4.x | Bloomberg data swap | One-class change in data_loader.py | 2026-05-05 |
| v3.x | Large OI blocks expiring soon | Needs parameter-free design (no hand-tuned cutoff) | 2026-06-01 |
| backlog | 999.1 Charm by DTE | Parked; awaiting research | 2026-05-12 |

## Session Continuity

Last session: 2026-06-22T20:07:52.415Z
Stopped at: Phase 16.5 context gathered
Post-rename hotfixes (2026-06-22): (a) **Store-path regression fixed** — after `gex/→engine/` rename, subpackage modules (`engine/data/*`, `engine/surface/*`, `engine/report/*`) used `Path(__file__).parents[1]` which now resolved to `engine/` not project root → daily run wrote parquet to `engine/out/`. Re-anchored 6 files to `parents[2]` (validation, surface_history, vol_index, surface_evolution, png_export, emailer `.env`). `run_daily`/`run_gex` at engine root keep `parents[1]` (correct). Full path audit done — all 9 anchors verified resolving under `out/`. Deleted stray `engine/out/`; real `out/` history intact. (b) **Scheduler re-pointed** — Task Scheduler "GEX Daily Report" action was still `-m gex.run_daily`; updated in place to `-m engine.run_daily --send` (battery flags/RestartCount preserved via Set-ScheduledTask -Action). 246 tests green.
Resume queue (updated 2026-06-22): (1) Phase 16.5 OI Depth Expansion is next up the roadmap (no CONTEXT.md yet → discuss-phase first). (2) Roadmap "where": Phase 17 (term) → 17.1 (expected-move cone). Hosting eventual (app.py has _check_password). st.iframe deferred (not a drop-in). See memory [[project_email_vs_hosting]]. Note: skew/motion read chips still gated off (sample <60 sessions, HISTORY_DAYS=30 caps the skew series — latent: with floor=60 the skew chip can never light until HISTORY_DAYS is raised; revisit if skew chip wanted sooner).

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
