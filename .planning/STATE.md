---
gsd_state_version: 1.0
milestone: v6.0
milestone_name: Risk-Environment / Regime Read
status: parked
last_updated: "2026-08-06T00:00:00.000Z"
last_activity: 2026-08-06
progress:
  total_phases: 5
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-27)

**Core value:** How expensive is protection, where on the surface is that expensiveness concentrated, how is the surface moving over time, and what does it imply for portfolio overlays or option-writing sleeves?
**Current focus:** none — project closed out at a stable point 2026-08-06 for a dev-machine transition. v6.0 is **planned but PARKED at 0%**: charter + roadmap + requirements are written and committed, no code written.

## Current Position

Phase: 28 of 32 (Barometer Axes Engine) — PARKED, not started
Plan: — (roadmap created, never planned)
Status: Parked — project intentionally closed out; resume when Adam chooses
Last activity: 2026-08-06 — close-out: 4 stale `test_app.py` contract tests fixed (481 green), stale CLAUDE.md claims corrected, v6.0 parked, transition runbook written

Progress: [░░░░░░░░░░] 0%

## ▶ START HERE

**One-line:** the project is CLOSED OUT and stable — nothing is half-built, nothing is uncommitted, 481 tests green, the live site and daily email run without this laptop. v6.0 is fully *planned* and deliberately *parked*.

**If resuming v6.0:** next action is `/gsd:plan-phase 28` (Barometer Axes Engine). The charter is `research/risk-environment-conditioning.md` — do not re-derive the theory, it is already written. Plan-phase forks left open on purpose: binning vs k-NN for conditioning cells; whether the absorption meta-read is Tier-1 or standalone.

**Why parked (2026-08-06):** Adam wanted the project done and to move to his main computer. v6.0 is 5 phases / 14 requirements — multi-session work. Parking a fully-specified, zero-code milestone was chosen over shipping a rushed partial barometer right before a machine move. This was a deliberate stop, not an abandonment.

**Machine transition:** see `CLAUDE.md` → "Moving to a New Dev Machine" (verified + expanded 2026-08-06).

**The milestone in one breath:** a non-directional second-moment barometer (level · vol-of-vol · term slope · gamma fragility · rarity/persistence · coupling) shown as *components, never a verdict*, in the Regime tab + daily email. A separate GATED validation track builds a conditional forward-risk base rate that ships to no surface until an explicit go/no-go (VAL-05).

**Hard boundaries carried from the charter into the phases:**
- No categorical CALM/STRESSED label (twice-killed regime-label scar). Barometer, not switch.
- No hidden scoring/weighting; non-compensatory Tier-1 (deep base rate) vs Tier-2 (gamma, descriptive-only) — no offsetting.
- The descriptive barometer (28–30) is shippable BEFORE and independently of the validation track (31–32). Do not collapse them.
- Reuse, don't rebuild: `engine/monitor/` already computes percentile/rarity/drift/persistence for 17 metric-pairs daily; reuse `card_model.build_card_read` gating. BAR-06's cross-ticker return panel is the only build-from-scratch axis.

**Still-open non-milestone item:** none blocking — OCI restore drill (BACKUP-02) already PASSED 2026-07-29 (see Session Continuity below).

**Do NOT** re-open the covered-call tilt-timing model without materially new evidence — it was killed deliberately (v6.0 slot reclaimed for this barometer work), not forgotten.

**Constraint:** gsd-sdk state handlers CORRUPT STATE.md — hand-edit STATE/PROJECT/MILESTONES/ROADMAP/REQUIREMENTS; never run state.milestone-switch / milestone.complete.

## Accumulated Context

### Roadmap Evolution

- 2026-08-05: v6.0 roadmap created — Phases 28–32. Two-track split honored: **barometer** (28 axes engine, 29 coupling/absorption, 30 surfaces) ships descriptively to Regime tab + email; **gated validation** (31 conditional forward-risk base rate, 32 EVT tail + ship-gate) is research-only, no surface until VAL-05. 14/14 requirements mapped (BAR-01–09, VAL-01–05). Charter: `research/risk-environment-conditioning.md`.
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

## Session Continuity (2026-08-06 — PROJECT CLOSE-OUT)

Last session: 2026-08-06 — deliberate close-out ahead of a dev-machine transition.
What happened: (1) Found and fixed **4 failing tests** in `engine/tests/test_app.py` — all stale contract assertions left behind by the 2026-08-04 de-directionalization, not app bugs: the two-layer quick/deep methods panel became a sidebar popover + expander, the "Positioning" tab became "Writing conditions", and γ-flip/call-wall/put-wall labels were deleted from the UI. Rather than delete the guards, they were rewritten against the *current* contract, including a new inverse guard (`test_directional_model_levels_are_not_surfaced`) that fails if the directional model levels are ever reintroduced. **481 green.** (2) Corrected stale `CLAUDE.md` claims: test count 449 → 481, and the "local Windows Task Scheduler job also still active" line — no such task exists on this machine (verified), so the daily pipeline is fully machine-independent on GitHub Actions. (3) **Parked v6.0** at 0% with charter/roadmap/requirements committed. (4) Verified and expanded the dev-machine move runbook in `CLAUDE.md` → "Moving to a New Dev Machine".
Resume queue: nothing outstanding. Resuming v6.0 means `/gsd:plan-phase 28`.
**Later the same session — `a1-flex-retry.yml` DELETED.** It was first called out here as harmless; it wasn't. Scheduled every 15 min (96 runs/day) on a *private* repo where Actions minutes are metered, it consumed the account's allowance: only ~9 of 96 daily runs actually executed, those failed with `The job was not acquired by Runner of type hosted`, and it starved `daily-report.yml` — which slipped from its 20:35 UTC cron to **00:56 UTC, 4h21m late**, on 2026-08-06 (and 1h14m late on 08-05). Deleted; rationale + resurrection terms (≤ `0 */6 * * *`, check the minutes budget first) in `ORACLE-CLOUD-SETUP.md` Step 5b. A1 capacity is now a manual console check. Supersedes the 2026-07-29 resume-queue item (3) below.

## Session Continuity (2026-07-29 update)

Last session: 2026-07-29 (ad-hoc, no active milestone — infra hardening, session #2 of the interview-readiness push)
Stopped at: BACKUP-02 restore drill passed and Phase 23 fully closed; A1.Flex capacity retry moved off a laptop-bound script onto GitHub Actions (`.github/workflows/a1-flex-retry.yml`, runs every 15 min, verified authenticating and reaching Oracle's real API across 3 test runs); all 18 project env vars consolidated into `.env` with find-it instructions and pushed to GitHub Actions secrets, verified live via a full manual `daily-report.yml` run (every step green — SMTP email actually sent, OCI backup ran, health check passed); fixed a real bug in `scripts/deploy.sh` (assumed Oracle Linux, actual instances are Ubuntu); retired `scripts/oracle-retry.ps1`. New standing intent, not yet started: git-crypt across all AdammoOO projects (memory: `git-crypt-all-projects-decision`).
Resume queue: (1) **Prep sheet** still the one item blocking project close (per Adam, deferred not skipped). (2) **UI/emoji/methodology-length sweep** — Adam explicitly flagged this as the real interview-readiness blocker, then this session went down the OCI/Oracle infra path instead; next session should start here unless redirected. (3) If A1.Flex ever lands (GitHub issue will fire) — run the migration checklist in `ORACLE-CLOUD-SETUP.md` → "Migrating to a New Instance". (4) git-crypt pilot on this repo, whenever Adam wants it.

## Session Continuity (previous — 2026-07-27)

Last session: 2026-07-27T22:40:00.000Z (ad-hoc, no active milestone — interview/portfolio readiness pass)
Stopped at: Regime tab rebuilt same session. Phase 27's monitor UI (raw percentile board + evidence panel, ~450 lines) was executed earlier, then **deleted outright** today after Adam judged it unjustifiable clutter ("not needed unless you have some proof of why we should share") — replaced with plain-English evidence-tiered cards reusing `build_card_fields`/`build_card_read`. A fact-check of `research/methodology-deep-review.md` against primary sources found citation errors + two inflated confidence tiers + two omitted counter-papers — corrected in place. Card "lean" text stopped stating an unvalidated trading recommendation; added `gex_mechanism_note()` (magnitude-not-direction caption on the dealer regime label); email Alerts banner suppressed pending the same rework; ordinal-suffix bug ("82th") fixed in 3 places; added an in-app "ℹ️ Methodology & assumptions" popover. 490 tests green. Committed `5b2db25`, merged an unrelated remote README-badge commit, pushed `91b8753`. Adam redeployed Oracle himself.
Resume queue: (1) **Prep sheet required before this project is considered closed** — Adam explicitly deferred writing it this session, not skipping it; do not treat the project as done without it (see auto-memory `interview-portfolio-goal`). (2) No active milestone otherwise.

**2026-07-29 update: OCI restore drill (BACKUP-02) PASSED.** Adam generated a second Customer Secret Key (`local-restore`) scoped for manual testing (separate from the `github-actions-backup` key CI uses), ran `python -m engine.restore_from_oci --dry-run` (listed all 67 backed-up objects correctly) then a real restore to `out_restore_test/` — all 67 files downloaded, parquet integrity checks passed, spot-checked `gex_snapshots.parquet` and confirmed real recent data (through 2026-07-28). Scratch dir deleted after. Phase 23 / BACKUP-02 is now fully closed — backup AND restore both proven, not just backup. Only remaining open item is the prep sheet above.

## Operator Next Steps

- **Prep sheet (blocking project close, not blocking further work)** — a study doc for Adam: architecture, key decisions, defensible talking points, likely interviewer questions on the options-flow literature. Write once he asks; do not consider vol-diagnostics "finalized" without it existing and being committed.
- ~~**Phase 23 close-out (blocked on Adam)**~~ — DONE 2026-07-29. Restore drill (BACKUP-02) passed: 67/67 objects restored, integrity verified. Phase 23 fully closed.
- Known accepted behavior in the monitor: an active alert holds indefinitely across a persistent data outage (self-heals on data return) — by design, not a bug. (Monitor backend is unused by the UI as of 2026-07-27 — see above — but this behavior still governs `engine/monitor/` itself.)

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
---
---
---
---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[vol-diagnostics/vol-diagnostics|Hub]]
<!-- LINKS:END -->
