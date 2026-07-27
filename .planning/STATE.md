---
gsd_state_version: 1.0
milestone: v6.0
milestone_name: SPY Covered-Call Sleeve Timing
status: in_progress
stopped_at: "v6.0 OPENED 2026-07-27. PROJECT/STATE/ROADMAP/REQUIREMENTS written by hand (gsd-sdk state handlers CORRUPT STATE.md — never run state.milestone-switch / milestone.complete). v5.0 shipped 2026-07-27 (OCI backup live since 2026-07-23; restore drill pending). Design locked via discussion 2026-07-27 — see START HERE + memory v6-covered-call-model-decision. NEXT: plan Phase 28 (proxy data layer) via /gsd-plan-phase 28, or run the restore drill. Learning Mode OFF."
last_updated: "2026-07-27T20:00:00.000Z"
last_activity: 2026-07-27 -- v6.0 milestone opened; roadmap (Phases 28-31) + requirements written; ready to plan Phase 28
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-27)

**Core value:** How expensive is protection, where on the surface is that expensiveness concentrated, how is the surface moving over time, and what does it imply for portfolio overlays or option-writing sleeves?
**Current focus:** v6.0 Phase 28 — proxy data layer (BXM/BXMD + USCC ingest); v5.0 shipped 2026-07-27

## Current Position

Milestone: v6.0 — SPY Covered-Call Sleeve Timing (opened 2026-07-27)
Phase: 28 — proxy data layer (not started)

v5.0 SHIPPED 2026-07-27 (Phases 23–27; OCI backup live since 2026-07-23, restore drill pending). Full record in `.planning/MILESTONES.md`.

**v6.0 roadmap** (4 phases + 1 quick task; critical path 28→29→30→31):
- (quick) **Restore drill** — verify `restore_from_oci` recovers `out/` (closes v5.0 BACKUP-02)
- **Phase 28 — proxy data layer**: ingest BXM/BXMD + USCC history (backtest depth to 1986)
- **Phase 29 — persistence engine**: hysteresis regime + half-life + conditional base-rates on deep VRP
- **Phase 30 — validated backtest**: USCC↔VFV tilt vs BXM/S&P TR, OOS + MT-corrected — **THE GATE**
- **Phase 31 — weekly Sat-AM PDF review**: built around validated numbers only

Status: v6.0 opened — ROADMAP + REQUIREMENTS written; ready to plan Phase 28
Last activity: 2026-07-27 -- v6.0 milestone opened (PROJECT/STATE/ROADMAP/REQUIREMENTS written by hand)

---

## ▶ START HERE

**One-line:** v6.0 is open. Next = `/gsd-plan-phase 28` (proxy data layer), or run the restore drill.

**Locked design (2026-07-27 discussion; full detail in PROJECT.md + memory `v6-covered-call-model-decision`):**
- **Decision = USCC↔VFV tilt** (Global X S&P 500 Covered Call ETF ↔ plain S&P 500 / VFV), **conviction dial** the user sizes, **environment + base-rates framing** — supporting input, never a trigger. Beta + unhedged USD/CAD FX net out between the legs, so the VRP premium-richness signal is the right input.
- **Backtest on REAL BXM** (ATM/monthly/100%-cover S&P buy-write, to 1986) vs S&P total-return — NOT synthetic Black-Scholes (drops the American-option error + the 30% haircut fudge). Cross-check vs USCC.TO live. **OOS + multiple-testing gate before anything ships to the report.**
- **Deliverable = weekly Sat-AM PDF review** (weasyprint in CI, iPhone-native, portable — generation stays in the cloud, local = HTML preview only). Trajectory-first, consistent template. Skeleton: regime header → cross-index location → SPY CC block → surface/evolution → what-would-change → methodology link. Palette via dataviz skill (samples at build). Daily email + dashboard retained.
- **Learning Mode OFF** (autonomous incl. core estimators) — reconfirmed 2026-07-27.
- **Future seam (OUT of v6.0):** the separate `regime-detection` system's bull/bear gate sits *above* the tilt (bear → neither USCC nor VFV).

**Constraints:** gsd-sdk state handlers CORRUPT STATE.md — hand-edit STATE/PROJECT/MILESTONES/ROADMAP/REQUIREMENTS; never run state.milestone-switch / milestone.complete. Portability is a hard rule (production 100% cloud; PDF generated in CI, local = HTML preview only).

**Also pending (not blocking):**
- Restore drill (DUR-01 / v5.0 BACKUP-02).
- Two root-level synthetic previews (`out_preview_*.html`) — safe to delete.
- `scripts/update.sh` has an uncommitted rebrand echo (`Gamma OMM` → `Vol Update`) — Adam's, left unstaged.
- Spike priors are reconstructed/unverified in `research/covered-call-spike-findings.md` — reproduce in Phase 30.

## Accumulated Context

### Roadmap Evolution

- 2026-07-23: Phases 26 (Severity Statistics & Alert Engine) and 27 (Microstructure Monitor UI) added to v5.0 — product reframed from descriptive daily report to market-microstructure exception monitor. Design decisions in `.planning/notes/microstructure-monitor-design.md` (ECDF severity ranks, transition-with-hysteresis alerts, false-alarm-budgeted bands, distribution-board UI, event-shaped email). Tier-2 conditional base rates stay deferred behind the v5.0 validation work.

### Decisions (carried forward, still load-bearing)

- 2026-07-21: Merged old Phases 23 (Data Completeness & Gap Monitoring), 24 (Backup & Restore), and 25 (Model-Ready Data Definition & Depth Audit) into a single Phase 23 ("Data Completeness, Backup & Model-Readiness Audit") — all three sat on the same "make the data trustworthy before modeling" arc and the old 25 already depended on 23's logic, so planning/executing them as one phase avoids an artificial seam. Old Phase 26 renumbered to 24, old Phase 27 renumbered to 25 (still depends on the new 24, unchanged relationship). v5.0 is now a 3-phase milestone (23–25) instead of 5.
- 2026-07-17: v5.0 roadmap extended with what were then Phase 26 (Codebase Organization & Dead Code Removal) and Phase 27 (Existing Computation Rigor Hardening; now 24/25 per the 2026-07-21 merge above), covering CLEAN-01/02 and RIGOR-01/02 respectively. The dependency (rigor audit reads more cleanly post-cleanup) is unchanged. RIGOR-01/02 harden the EXISTING VRP/RV20/surface-fit/skew-term computations only — explicitly not a new predictive model (MODEL-01/02 stay deferred).
- 2026-07-26: VRP kept as the vol-point spread (`vol_index − RV20×100`) with the "VRP" label — documented as an intentional methodology deviation (a practitioner IV−RV proxy, NOT the Carr-Wu variance-swap VRP `IV²−RV²`) at first use in `vrp_history.py` docstring + email glossary, rather than renamed or switched to variance units (25-03). Full per-computation certification in `25-METHODOLOGY-AUDIT.md`.
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
- `out/` parquet stores live only on the Oracle server, no backup anywhere — now part of Phase 23 of v5.0 (no longer just a flagged risk).

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
| quick_task | 260514-fz2-dead-code-stale-ref-sweep | resolved — completed 2026-05-14 (commit 22ec33a), confirmed during Phase 24 |
| quick_task | 260621-v8g-ui-pass-2-polish-unify-axis-k-s-labels-f | missing |
| todo | 2026-05-11-salvaged-from-legacy-task-board.md | pending |
| todo | 2026-05-11-v3-2-pre-distribution-hardening.md | resolved 2026-07-26 (Phase 24 / backlog 999.3) — items a/b/d shipped out-of-phase, item c (regime sharpness) deferred; moved to todos/done/ |
| seed | SEED-001-short-end-gamma-concentration | dormant |

## Session Continuity

Last session: 2026-07-26T23:32:16.223Z
Stopped at: Paused 2026-07-26 for review after shipping Phases 24 + 25 and fully planning Phase 27. Phase 27 is plan-only per Adam — do NOT execute until he gives the go.
Resume queue: (1) On Adam's go → `/gsd:execute-phase 27` (plans committed, checker-passed, 4 plans/3 waves; app.py-touching plans 27-02 & 27-03 must NOT run same-wave; runs sequentially on main). (2) Phase 23 close-out is blocked on Adam's OCI step. (3) After v5.0 closes → v6.0 covered-call persistence model (seed: `.planning/seeds/v6-covered-call-persistence-model.md`).

## Operator Next Steps

- **Phase 27 (Microstructure Monitor UI)** — ✅ PLANNED + committed (8465f24), checker-passed (0 blockers), NOT executed. On Adam's go: `/gsd:execute-phase 27` (or resume the current orchestration). 4 plans: 27-01 monitor_reader adapter + vrp_components, 27-02 distribution board (app.py), 27-03 evidence panels (app.py), 27-04 event-shaped email + boilerplate cut. Waves: 1=[27-01], 2=[27-02,27-04 parallel], 3=[27-03]. Watch: 27-02 & 27-03 both touch app.py — never same wave; on Windows, run sequentially on main (skip worktrees). Adam must set `config.DASHBOARD_METHODOLOGY_URL`. Cold-start: board/email near-empty for weeks (zero alerts fired yet) — test sparse case, don't mistake for a bug. Refs: `27-CONTEXT.md` (7 derived success criteria — phase has no REQUIREMENTS.md IDs), `27-RESEARCH.md`, `.planning/notes/microstructure-monitor-design.md`.
- **Phase 23 close-out (blocked on you)** — OCI console + GitHub secrets setup (`.planning/notes/ORACLE-CLOUD-SETUP.md` → "Object Storage Backup Setup (Phase 23)"), reply "approved", and I'll write 23-03-SUMMARY + verify. Still the only open item in Phase 23.
- Known accepted behavior in the monitor: an active alert holds indefinitely across a persistent data outage (self-heals on data return) — by design, not a bug.

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
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[vol-diagnostics/vol-diagnostics|Hub]]
<!-- LINKS:END -->
