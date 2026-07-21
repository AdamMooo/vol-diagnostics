---
phase: 23-data-completeness-backup-model-readiness
plan: "04"
subsystem: infra
tags: [health-check, model-readiness, data-depth-audit, garch, pytest]

# Dependency graph
requires:
  - phase: 23-data-completeness-backup-model-readiness (Plan 23-01)
    provides: "_series_dates(ticker, series), SERIES_NAMES, INDEX_TICKERS — reused directly, not re-implemented"
provides:
  - "MODEL-READY-DATA-SPEC.md — grounded per-series minimum-depth targets + required schema, the bar the next modeling milestone checks data against"
  - "depth_audit() + MODEL_READY_TARGETS in engine/health_check.py — current depth vs. target per series/ticker, via --depth-audit CLI flag"
affects: [25-model-ready-data-definition-depth-audit]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "depth_audit() is a standalone informational branch in main() — returns before the --strict exit-code path so a data-foundation phase's series being below target never fails daily CI"
    - "MODEL_READY_TARGETS numbers are hand-kept in sync with MODEL-READY-DATA-SPEC.md's table; test_vol_index_target_matches_config_constant locks the one target that's also referenced elsewhere in the codebase"

key-files:
  created:
    - .planning/notes/MODEL-READY-DATA-SPEC.md
  modified:
    - engine/health_check.py
    - engine/tests/test_data_health.py
    - .planning/PROJECT.md

key-decisions:
  - "STATE.md link deferred to the orchestrator's centralized post-wave write (worktree execution contract) rather than committed in this plan's worktree — the decision text is recorded here for the orchestrator to fold in: '2026-07-21: Model-ready depth/schema spec now exists at .planning/notes/MODEL-READY-DATA-SPEC.md (Phase 23 Plan 04, SCHEMA-01/02) — the bar the next modeling milestone checks its data against before building anything; per-series targets grounded in GARCH/RV20/percentile literature, audited via python -m engine.health_check --depth-audit.'"
  - "gex_snapshots target set to 750 sessions (GARCH(1,1) literature midpoint, Ng & Lam 2006, 500-1000 range) — this store's scalar columns (net_gex, vrp, rv20) are the natural GARCH-style time-series input if that's the eventual model family"
  - "surface_history and oi_history both target 251 sessions (RV20 ~1yr 'one seasonal cycle' convention, not a GARCH minimum) — these are per-day cross-sectional stores, not return series, so importing a return-series estimator's sample-size rule would be the wrong anchor"
  - "vol_index target reuses config.VRP_DEEP_LOOKBACK_SESSIONS (2500) verbatim rather than a new number — CBOE-published history already exceeds any plausible modeling requirement; restated only for spec/code traceability"

patterns-established:
  - "Per-series depth targets live in exactly two places (MODEL-READY-DATA-SPEC.md table + MODEL_READY_TARGETS dict) and must be kept byte-identical — flagged as this plan's main correctness hazard (T-23-10) rather than a security boundary"

requirements-completed: [SCHEMA-01, SCHEMA-02]

duration: 25min
completed: 2026-07-21
---

# Phase 23 Plan 04: Model-Readiness Depth Audit Summary

**Wrote a grounded model-ready data spec (per-series minimum session-depth targets with named-estimator rationale) and `depth_audit()` in `engine/health_check.py` — a standalone `--depth-audit` CLI report of actual depth vs. those targets, reusing Plan 23-01's `_series_dates()` rather than re-implementing session counting.**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-07-21T16:11:00-04:00
- **Tasks:** 2
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments
- `.planning/notes/MODEL-READY-DATA-SPEC.md` — new spec with a summary table + one `###` subsection per series (`gex_snapshots`, `surface_history`, `vol_index`, `oi_history`), each with full reasoning (not just a number): GARCH(1,1) literature (Ng & Lam 2006) for `gex_snapshots`, RV20 ~1yr convention for `surface_history`/`oi_history`, "already deep enough" traceability to `config.VRP_DEEP_LOOKBACK_SESSIONS` for `vol_index`
- `engine/health_check.py` gains `MODEL_READY_TARGETS` (4-key dict matching the spec exactly) and `depth_audit(verbose=True) -> dict`, reusing Plan 23-01's `_series_dates()` per ticker/series
- `--depth-audit` CLI flag added to `main()` as a standalone informational branch that returns before the `--strict` exit-code path — never gates the daily CI build
- `.planning/PROJECT.md` links the spec from its Key Files section (discoverable per D-09, not buried in `.planning/notes/`)
- Full TDD cycle followed: RED (5 failing tests, ImportError) → GREEN (implementation, all pass) for the `tdd="true"` task

## Task Commits

1. **Task 1: Write MODEL-READY-DATA-SPEC.md and link it from PROJECT.md/STATE.md** - `16e727a` (docs) — preceded by `3f1221c` (chore: copy in this plan's untracked planning inputs so the worktree could execute)
2. **Task 2: Add depth_audit() + --depth-audit CLI flag + tests** - RED `b8123cc` (test) → GREEN `202055f` (feat)

## Files Created/Modified
- `.planning/notes/MODEL-READY-DATA-SPEC.md` - new spec: per-series depth targets, rationale, schema, audit instructions
- `engine/health_check.py` - added `MODEL_READY_TARGETS`, `depth_audit()`, `--depth-audit` CLI flag
- `engine/tests/test_data_health.py` - added `TestModelReadinessAudit` (5 tests), alongside Plan 23-01's existing classes (untouched)
- `.planning/PROJECT.md` - added a line near "Key Files" linking the new spec

## Decisions Made
- STATE.md's link was written locally during Task 1 per the plan, then reverted before committing — worktree execution contract reserves STATE.md/ROADMAP.md writes for the orchestrator's centralized post-wave pass. The exact decision line the orchestrator should fold in is captured verbatim in this SUMMARY's frontmatter `key-decisions` (first bullet) and body above.
- Depth targets grounded per D-10: 750/251/2500/251 sessions for gex_snapshots/surface_history/vol_index/oi_history respectively — see frontmatter `key-decisions` for full rationale per series.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Copied this plan's untracked planning inputs into the worktree**
- **Found during:** Setup, before Task 1
- **Issue:** `23-04-PLAN.md`, `23-CONTEXT.md`, `23-RESEARCH.md` existed only in the main repo's untracked working tree (not yet committed anywhere reachable from this worktree's branch history) — the worktree had no way to read them otherwise.
- **Fix:** Copied the three files from the main repo into the worktree and committed them (`3f1221c`) before starting Task 1.
- **Files modified:** `.planning/phases/23-data-completeness-backup-model-readiness/23-04-PLAN.md`, `23-CONTEXT.md`, `23-RESEARCH.md`
- **Verification:** Files present and readable in the worktree; plan execution proceeded normally.
- **Committed in:** `3f1221c`

---

**Total deviations:** 1 auto-fixed (blocking — worktree setup, not a code/logic issue)
**Impact on plan:** No scope creep; purely a worktree-isolation artifact of running this plan in parallel with sibling plans that already merged (23-01, 23-02).

## Issues Encountered
- Worktree HEAD was initially on a stale base (`484b180`, missing Plan 23-01/23-02 merges); corrected via the mandatory `<worktree_branch_check>` reset to `edbc1e89` before any work began. No data was lost — this happened before any file edits.
- The worktree has no local `.venv`; tests were run against the main repo's venv at `C:\dev\vol-diagnostics\.venv\Scripts\python.exe` (same interpreter, different cwd — imports resolve correctly against the worktree's `engine/` since pytest uses rootdir-relative imports).
- `out/gex`, `out/surface_history`, `out/vol_index`, `out/oi_history` were missing (gitignored, not part of this plan) and needed by one pre-existing unrelated test (`TestRunIdempotencyGuard::test_force_overrides_guard`, same gap Plan 23-01 documented); created locally only to unblock the full-suite verification run, not committed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 25 (Model-Ready Data Definition & Depth Audit, per STATE.md's v5.0 phase order) can build directly on `MODEL_READY_TARGETS` and `depth_audit()` rather than re-deriving targets
- `python -m engine.health_check --depth-audit` is available today; current live depth is far short of every target (cold-start, ~2 months of collection since 2026-05-06) — expected, not a defect; the audit exists precisely to track progress toward these targets over time
- No blockers. Full test suite green (390 passed) after this plan's changes.

---
*Phase: 23-data-completeness-backup-model-readiness*
*Completed: 2026-07-21*

## Self-Check: PASSED

- FOUND: .planning/notes/MODEL-READY-DATA-SPEC.md
- FOUND: engine/health_check.py
- FOUND: engine/tests/test_data_health.py
- FOUND: .planning/PROJECT.md
- FOUND: .planning/phases/23-data-completeness-backup-model-readiness/23-04-SUMMARY.md
- FOUND: 3f1221c, 16e727a, b8123cc, 202055f, a1f5673 (all task commits)
