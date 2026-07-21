---
phase: 23-data-completeness-backup-model-readiness
plan: "01"
subsystem: infra
tags: [pandas-market-calendars, parquet, health-check, gap-detection, pytest]

# Dependency graph
requires: []
provides:
  - "full_history_report() — full-history (not just tail) gap scanner across gex_snapshots/surface_history/vol_index/oi_history x SPY/QQQ/IWM"
  - "list_snapshot_dates() — full-history date listing for gex_snapshots.parquet (validation.py), mirroring surface_history/oi_history patterns"
  - "engine.health_check main()'s combined --strict/--json output (tail-check + full-history)"
affects: [23-02, 23-03, 23-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-ticker dates_by_series computed once per ticker (not once per series comparison) to avoid redundant parquet reads"
    - "vol_index gap semantics: a missing session is only a gap if at least one other series (gex_snapshots/surface_history/oi_history) collected data that date; otherwise treated as expected CBOE/NYSE non-publish"

key-files:
  created: []
  modified:
    - engine/data/validation.py
    - engine/health_check.py
    - engine/tests/test_data_health.py

key-decisions:
  - "Extended engine/health_check.py in place (D-02) rather than a second gap-audit script — reuses existing NYSE-calendar plumbing and the existing --strict CI gate"
  - "Full-history scan wired into every --strict/--json invocation (not a separate flag) — runtime for a ~2-week test window and current empty out/ tree is negligible; Pitfall 4 mitigated by computing dates_by_series once per ticker"

patterns-established:
  - "_series_dates(ticker, series) dispatcher — single seam for adding a 5th data series later without touching _full_history_scan"

requirements-completed: [DATA-01, DATA-02]

duration: 25min
completed: 2026-07-21
---

# Phase 23 Plan 01: Full-History Gap Scanner Summary

**Extended `engine/health_check.py` from a 2-series tail-freshness checker into a full-history, 4-series (gex_snapshots/surface_history/vol_index/oi_history) gap scanner across SPY/QQQ/IWM, wired into the existing `--strict`/`--json` CLI surface.**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-07-21T20:00:41Z
- **Tasks:** 1
- **Files modified:** 3

## Accomplishments
- `engine/data/validation.py` gains `list_snapshot_dates(ticker)` — full-history date listing for `gex_snapshots.parquet`, needed because `load_history()` is tail-limited (`days=N`)
- `engine/health_check.py` gains `get_nyse_sessions()`, `_series_dates()`, `_full_history_scan()`, `full_history_report()` — a full-history scanner that walks the NYSE session calendar per ticker/series and flags any session with no stored row, catching mid-history gaps a tail-only check would miss
- vol_index CBOE-holiday semantics (D-05) correctly distinguished from real gaps: a missing vol_index session is only flagged when another series (gex_snapshots/surface_history/oi_history) DID collect data that date
- `main()` now combines the existing tail-freshness `check_health()` result with `full_history_report()` into one `--strict` exit code and one `--json` payload (`{"tail_check": ..., "full_history": ...}`)
- `check_health()` and its 3 existing tests are byte-for-byte unchanged

## Task Commits

1. **Task 1: Add list_snapshot_dates() + full-history gap scanner + tests** - `26a19a3` (feat)

## Files Created/Modified
- `engine/data/validation.py` - added `list_snapshot_dates(ticker)` after `load_history()`
- `engine/health_check.py` - added `SERIES_NAMES`, `get_nyse_sessions()`, `_series_dates()`, `_full_history_scan()`, `full_history_report()`; `main()` now combines tail-check + full-history for `--strict`/`--json`
- `engine/tests/test_data_health.py` - added `TestFullHistoryGapScan` (5 tests) and `TestHealthCheckStrict` (2 tests)

## Decisions Made
- Extend `engine/health_check.py` in place per D-02 (avoids a second parallel gap-audit tool duplicating NYSE-calendar plumbing)
- Full-history scan runs on every `--strict`/`--json` call rather than behind a separate flag — measured runtime is negligible (full suite still completes in ~19s; scan itself reads at most 4 small parquet files x 3 tickers)
- vol_index gap reason string includes "other series collected" so it's grep-able in CI logs when a real CBOE-fetch failure needs distinguishing from a holiday

## Deviations from Plan

None - plan executed exactly as written. The fresh worktree's `out/` directory was missing subdirectories (`out/gex`, `out/surface_history`, `out/vol_index`, `out/oi_history`) needed by one pre-existing, unrelated test (`TestRunIdempotencyGuard::test_force_overrides_guard`); these are git-ignored runtime directories, not part of this plan's scope, and were created locally only to unblock the full-suite verification run (not committed — they're empty and gitignored).

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 23-04 (model-readiness depth audit) can reuse `_series_dates()`/`get_nyse_sessions()` directly for session counting, as planned
- No blockers for Plans 23-02/23-03 (backup/restore, independent of this scanner)

---
*Phase: 23-data-completeness-backup-model-readiness*
*Completed: 2026-07-21*

## Self-Check: PASSED

- FOUND: engine/data/validation.py
- FOUND: engine/health_check.py
- FOUND: engine/tests/test_data_health.py
- FOUND: .planning/phases/23-data-completeness-backup-model-readiness/23-01-SUMMARY.md
- FOUND: 26a19a3 (task commit)
