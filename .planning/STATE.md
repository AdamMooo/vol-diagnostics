---
gsd_state_version: 1.0
milestone: v5.0
milestone_name: Data Foundation
status: planning
last_updated: "2026-07-17T00:00:00.000Z"
last_activity: 2026-07-17
progress:
  total_phases: 5
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-17)

**Core value:** How expensive is protection, where on the surface is that expensiveness concentrated, how is the surface moving over time, and what does it imply for portfolio overlays or option-writing sleeves?
**Current focus:** v5.0 Data Foundation — roadmap drafted (Phases 23–27), awaiting user approval before phase planning starts

## Current Position

Phase: Not started (roadmap drafted, Phase 23 up first)
Plan: —
Status: Roadmap created, awaiting approval
Last activity: 2026-07-17 — Roadmap extended for v5.0 (Phases 23–27; added 26 Codebase Organization & Dead Code Removal, 27 Existing Computation Rigor Hardening)

## Accumulated Context

### Decisions (carried forward, still load-bearing)

- 2026-07-17: v5.0 roadmap extended with Phase 26 (Codebase Organization & Dead Code Removal) and Phase 27 (Existing Computation Rigor Hardening), covering CLEAN-01/02 and RIGOR-01/02 respectively. Phase 26 has no hard technical dependency on Phases 23–25 (independent cleanup pass); Phase 27 depends on Phase 26 so the rigor audit reads against an already-cleaned codebase. RIGOR-01/02 harden the EXISTING VRP/RV20/surface-fit/skew-term computations only — explicitly not a new predictive model (MODEL-01/02 stay deferred).
- 2026-07-17: v5.0 phase order set as Phase 23 (Data Completeness & Gap Monitoring) → Phase 24 (Backup & Restore) → Phase 25 (Model-Ready Data Definition & Depth Audit) → Phase 26 → Phase 27. Phase 25 depends on Phase 23's gap-detection/session-counting logic to measure actual depth against the written schema targets. Phase 24 is independent of the other two.
- 2026-07-16: VRP percentile ranks against ~10yr (`config.VRP_DEEP_LOOKBACK_SESSIONS`, 2500 sessions) instead of a rolling 252-session (~1yr) window — a short window can only say "cheap vs. a possibly-already-elevated recent regime"; CBOE vol-index actually holds decades of history.
- 2026-07-16: Skew (25Δ) card field states direction explicitly ("puts pricier"/"calls pricier"/"flat") instead of a bare signed number.
- 2026-07-16: CLAUDE.md's "locked until team validates" language dropped (no external team left, sole-owner + public) — self-imposed statistical-validation discipline kept.
- 2026-07-14: Daily scheduler moved from an Oracle-hosted container to GitHub Actions after the Oracle Micro instance's first live cron fire hung mid-PNG-export (1 vCPU/1GB couldn't run headless Chromium reliably). Oracle now only runs `dashboard` + `caddy`; GitHub Actions rsyncs `out/` down/up around each run.
- 2026-07-14: Deployed to Oracle E2.1.Micro (AMD64) rather than A1.Flex ARM — Toronto capacity stayed constrained; A1 retry loop left running in background in case it frees up.
- 2026-05-16: v5.0 milestone scoped as "Data Foundation" (hardening collection/retention) rather than jumping straight to the options-writing/pricing model — user's own sequencing.

Full decision history (v3.0–v4.0): `.planning/PROJECT.md` Strategic Decisions table + `.planning/milestones/v4.0-ROADMAP.md`.

### Pending Todos

- None new. 2 stale pre-v4.0 todos acknowledged and deferred at milestone close (see Deferred Items below).

### Blockers/Concerns

None blocking. Carried-forward known debt (see Deferred Items):

- `engine/report/png_export.py` still swallows any export failure into a `print()` warning and returns None — the same silent-failure shape that hid the plotly/kaleido version mismatch for months. (Partial-failure visibility was fixed one layer up in `run_daily.py`'s PNG attachment builders.)
- `runners/gex_daily.ps1`'s "GEX Daily" naming is stale (script retired, kept for reference only).
- `out/` parquet stores live only on the Oracle server, no backup anywhere — now Phase 24 of v5.0 (no longer just a flagged risk).

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

Acknowledged and deferred at v4.0 milestone close on 2026-07-17 (all pre-date v4.0; none blocked the close):

| Category | Item | Status |
|----------|------|--------|
| uat_gap | Phase 16.5 (16.5-HUMAN-UAT.md) | partial — 3 pending scenarios |
| verification_gap | Phase 11 (11-VERIFICATION.md) | human_needed |
| verification_gap | Phase 16.5 (16.5-VERIFICATION.md) | human_needed |
| quick_task | 260514-fz2-dead-code-stale-ref-sweep | missing — now folded into v5.0 Phase 26 (CLEAN-01) |
| quick_task | 260621-v8g-ui-pass-2-polish-unify-axis-k-s-labels-f | missing |
| todo | 2026-05-11-salvaged-from-legacy-task-board.md | pending |
| todo | 2026-05-11-v3-2-pre-distribution-hardening.md | pending — now folded into v5.0 Phase 26 (CLEAN-01) |
| seed | SEED-001-short-end-gamma-concentration | dormant |

## Session Continuity

Last session: 2026-07-17T00:00:00.000Z
Stopped at: v5.0 roadmap extended (Phases 23–27) — ROADMAP.md, STATE.md written, REQUIREMENTS.md traceability updated (10/10 mapped). Awaiting user approval of the full roadmap draft.
Resume queue: On approval, run `/gsd:plan-phase 23` to start Data Completeness & Gap Monitoring.

## Operator Next Steps

- Review the v5.0 roadmap draft (Phases 23–27) and approve or request changes.
- On approval: `/gsd:plan-phase 23`.

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[vol-diagnostics/vol-diagnostics|Hub]]
<!-- LINKS:END -->
