---
gsd_state_version: 1.0
milestone: v4.0
milestone_name: Cloud Hosting
status: executing
stopped_at: Phase 20 complete; ready for Phase 21 Oracle Cloud deploy
last_updated: "2026-06-25T09:15:00.000Z"
last_activity: 2026-06-25 -- Phase 20 Data Health + Collection Hardening committed
progress:
  total_phases: 4
  completed_phases: 2
  total_plans: 2
  completed_plans: 2
  percent: 50
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-04)

**Core value:** How expensive is protection, where on the surface is that expensiveness concentrated, how is the surface moving over time, and what does it imply for portfolio overlays or option-writing sleeves?
**Current focus:** v4.0 Cloud Hosting — Docker on Oracle Cloud Free Tier

## Current Position

Milestone: v4.0
Phase: 21
Plan: 01
Status: Not started
Last activity: 2026-06-25 -- Phase 20 committed

Progress: [█████░░░░░] 50%

## v3.5 Milestone Summary (SHIPPED 2026-06-24)

All phases complete:
- Phase 15: Vol-Index Data Layer ✅
- Phase 16: VRP Percentile ✅
- Phase 16.5: OI Depth Expansion ✅
- Phase 17: Term-Structure Regime ✅
- Phase 17.1: Convexity & Expected Move ✅
- Phase 18.1: Dashboard Trust & Clarity Hardening ✅
- Phase 18: 3-Page Reorg + Email Parity + Gating ✅

## v4.0 Phases Remaining

| Phase | Status | Notes |
|-------|--------|-------|
| 19. Dockerize | ✅ Complete | Dockerfile, compose, Caddy, SMTP emailer |
| 20. Data Health + Collection Hardening | ✅ Complete | Idempotent run_daily, supercronic, health-check |
| 21. Oracle Cloud Provision + Deploy | Not started | ARM instance, Docker, git clone, migrate parquet |
| 22. HTTPS + Remote Access | Not started | Caddy + Let's Encrypt, firewall |

## Performance Metrics

**Velocity:**

- Total plans completed: 35 (v3.1 ×3, v3.2 ×6, v3.3 ×12, phases 8–11) + 4 (v3.4 phases 12–13) + 13 (v3.5 phases 15–18) + 1 (v4.0 phase 19)
- Average duration: ~7 min per plan
- Current test count: 344

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
| 16.5 | 3 | - | - |
| Phase 17.1-convexity-expected-move P01 | 6 | 2 tasks | 7 files |
| Phase 17.1 P02 | 38min | 2 tasks | 6 files |
| Phase 18.1 P01 | 1380 | 2 tasks | 6 files |
| Phase 18.1 P02 | 26min | 2 tasks | 8 files |
| Phase 17 P01 | 12min | 5 tasks | 5 files |

## Accumulated Context

### Roadmap Evolution

- Phase 18.1 inserted after Phase 18: Dashboard Trust and Clarity Hardening (URGENT)

### Decisions

- 2026-06-24: Phase 18-01 — Top-level dashboard routing is locked to Regime / Surfaces / Positioning; Evolution is nested under Surfaces.
- 2026-06-24: Phase 18-01 — Page-1 hierarchy is cross-index briefing + short OI teaser above default three-card snapshot.
- 2026-06-24: Phase 18-01 — Full OI/GEX mechanics remain on Positioning and heavy pages use single-ticker radios.
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
- [Phase ?]: 17.1-01: Model-free expected move uses CBOE variance with invalid-mid and >=3-strike guard.
- [Phase ?]: 17.1-01: Butterfly computed from same-expiry front skew put/call/atm inputs.
- [Phase ?]: 17.1-01: Butterfly percentile uses rank method and is suppressed below 10 sessions while exposing n.
- [Phase ?]: 17.1-02: OI impact language unified across dashboard/email using pct_of_total and put_call_ratio.
- [Phase 17.1]: IV30 / EM now renders precomputed expected_move_pct with by-date DTE context.
- [Phase 17.1]: 25Δ Fly added after skew with percentile/count-aware cold-start labeling.
- [Phase 17.1]: OI impact language unified across dashboard/email using pct_of_total and put_call_ratio only.
- [Phase 18.1]: CardField trust_tag and split_compact_fields are the canonical renderer contract for compact scorecards.
- [Phase 18.1]: VRP trust framing is explicit and sample-aware: building before lookback, history at lookback.
- [Phase 18.1]: Primary dealer-impact framing centralized as GEX_PRIMARY_DTE=14 and emitted via compute summary keys.
- [Phase 18.1]: OI interpretation remains table-first with 5d share context shown in dashboard/email when history exists.
- [Phase 17]: VIX term ratios (VIX9D/VIX, VIX/VIX3M) SPY-only; CBOE does not publish 9D/3M for VXN or RVX. Field conditionally emitted — omitted entirely for QQQ/IWM.

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

Last session: 2026-06-25T09:15:00.000Z
Stopped at: Phase 20 complete; ready for Phase 21 Oracle Cloud deploy
Resume queue: (1) **Phase 21: Oracle Cloud Provision + Deploy** — create Always Free ARM instance, install Docker, clone repo, compose up, migrate parquet via scp. (2) **Phase 22: HTTPS + Remote Access** — Caddy + Let's Encrypt, firewall rules.

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

