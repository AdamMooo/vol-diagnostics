---
phase: 09-surface-evolution-engine
plan: "03"
subsystem: surface-evolution-daily-integration
tags: [surface-evolution, run-daily, backfill, integration, non-blocking, cli]
dependency_graph:
  requires:
    - gex/surface_evolution.py::update_evolution
    - gex/surface_evolution.py::backfill
    - gex/surface_history.py::list_available_dates
    - gex/run_daily.py::run
  provides:
    - gex/run_daily.py (non-blocking evolution second pass)
    - gex/surface_evolution.py::backfill (refined; honest row count)
    - gex/surface_evolution.py (__main__ CLI: --backfill, ticker, --start)
  affects:
    - out/surface_evolution.parquet (populated daily once history is sufficient)
    - streamlit_app.py (Phase 10 will read load_evolution)
tech_stack:
  added: []
  patterns:
    - non-blocking-try-except-second-pass
    - inline-import-for-failure-isolation
    - honest-persisted-row-count
    - argparse-cli-entrypoint
decisions:
  - "Evolution pass inserted between the snapshot save loop and index_results build; per-ticker try/except so an evolution failure prints WARN and never reaches the email send path"
  - "update_evolution import is inline inside run() (not module-top) so an import-time failure stays contained in the non-blocking pass"
  - "DEVIATION (user-directed): backfill/update_evolution/save_evolution_row now report rows ACTUALLY persisted, not dates touched — overrides the plan spec's `n = count of dates processed without exception`. save_evolution_row returns bool, update_evolution returns int, backfill sums the real total. Cold-start prints '0 rows (insufficient history)' instead of the misleading '(N rows)'"
  - "run_daily logs per-ticker evolution row counts each trading day so accumulation is visible as history builds"
  - "Edit-in-place honored: backfill + __main__ + test_backfill_consistency + test_cold_start_no_row_written already existed from Plan 02 — refined in place, no duplicate defs (blocking anti-pattern from .continue-here avoided)"
key_files:
  created: []
  modified:
    - gex/run_daily.py
    - gex/surface_evolution.py
    - gex/tests/test_surface_evolution.py
metrics:
  duration_minutes: 6
  completed_date: "2026-05-31"
  tasks_completed: 3
  tasks_total: 3
  files_changed: 3
---

# Phase 9 Plan 03: Daily Integration + Backfill CLI Summary

Wires the evolution engine into the daily orchestrator as a non-blocking second pass, refines the backfill CLI to report honest persisted-row counts, and proves both the populated and cold-start paths with integration tests. The engine now runs automatically every trading day and will begin accumulating rows the moment enough surface history exists.

## What Was Built

**Task 1 — `gex/run_daily.py` + `gex/surface_evolution.py`:**

- `run_daily.run()` gained a non-blocking evolution pass between the snapshot save loop and `index_results` construction. Inline `from gex.surface_evolution import update_evolution`, per-ticker `try/except` that prints `[WARN] {ticker} evolution failed (non-blocking): {exc}` and continues — an evolution failure can never block the email send path. Each ticker also logs `{ticker}: {rows} evolution row(s) written` for daily accumulation visibility.
- `surface_evolution.backfill()` refined in place (NOT appended — it already existed from Plan 02): per-date `try/except`, oldest-first iteration, and honest row accounting (see Deviations). The `__main__` argparse block already matched spec and was left unchanged.

**Task 2 — `gex/tests/test_surface_evolution.py`:** Added 3 new integration tests; existing `test_backfill_consistency` / `test_cold_start_no_row_written` left untouched (no re-add). A 4th test was added during checkpoint resolution (see Deviations).

| Test | What It Verifies |
|------|-----------------|
| test_evolution_does_not_raise_on_empty_store | empty snapshot → no exception, no parquet written |
| test_run_daily_evolution_failure_does_not_propagate | non-blocking loop collects all 3 failures, propagates none |
| test_cross_ticker_schema_consistency | SPY/QQQ/IWM rows share identical columns; horizons ⊆ {5,10,20} |
| test_backfill_reports_honest_row_count | backfill returns rows persisted (not dates touched); cold-start returns 0 and writes no file |

**Task 3 — Human-verify checkpoint (blocking):** Resolved. Full suite green, backfill CLI exercised against live surface_history, parquet inspected, cold-start behavior confirmed correct and now honestly reported.

## Commits

| Task | Commit | Files |
|------|--------|-------|
| 1 — wire run_daily + refine backfill | 1b9c28a | gex/run_daily.py, gex/surface_evolution.py |
| 2 — integration tests | 33c3bb1 | gex/tests/test_surface_evolution.py |
| Checkpoint fix — honest row count | f8a002e | gex/run_daily.py, gex/surface_evolution.py, gex/tests/test_surface_evolution.py |

## Deviations from Plan

1. **Honest persisted-row count (user-directed).** The plan spec defined backfill's `n` as "count of dates processed without exception" and printed `-> rows written` / `({n} rows)`. In cold-start this claimed "(2 rows)" when zero rows were actually written — misleading. Per user direction at the checkpoint, the count was reworked to report rows *actually persisted*: `save_evolution_row` returns `bool`, `update_evolution` returns the persisted-row `int`, and `backfill` sums the real total. Cold-start now prints `0 rows (insufficient history)` and `N date(s) processed, M row(s) written`. `run_daily` logs the per-ticker count each day. Backed by `test_backfill_reports_honest_row_count`.

2. **Edit-in-place, not append.** Plan wording said "append the backfill function and __main__ block" / "replace the test_backfill_consistency stub", but Plan 02 had already written all four symbols. A grep gate confirmed each exists once; they were refined in place with no duplicate `def backfill`, no second `__main__`, and no re-added tests (avoided the `blocking` anti-pattern recorded in `.continue-here.md`).

## Known Stubs

None.

## Data-Collection Status (cold-start)

Only 2 trading days of `surface_history` exist (2026-05-28, 05-29). Horizons 5/10/20 each need N+1 prior sessions, so `update_evolution` correctly writes **0 rows** today and `out/surface_evolution.parquet` is not yet created. This is spec-correct cold-start, proven by `test_cold_start_no_row_written`. Rows begin landing automatically once history accumulates: horizon=5 at ~6 trading days, horizon=10 at ~11, horizon=20 at ~21. The daily `run_daily` pass and `--backfill` both report the climbing count honestly.

## Threat Flags

None — no new network endpoints, no new auth, no new trust boundaries. `--ticker`/`--start` CLI args are parsed via argparse (`datetime.date.fromisoformat`), feed only `list_available_dates`/`_store_path` (constructed from `__file__`, no traversal), no shell expansion, no eval.

## Self-Check: PASSED

- [x] `run_daily.py` has the non-blocking evolution pass (per-ticker try/except, never raises) between snapshot loop and `index_results` — verified via source assertion
- [x] `surface_evolution.py` exports `backfill(ticker, start_date)` and a `__main__` CLI (`--backfill`, ticker, `--start`) — verified via `--help`
- [x] backfill loops over dates only; `update_evolution` owns horizon iteration — no inner horizon loop in backfill
- [x] No duplicate symbols introduced — grep gate confirms `def backfill`, `__main__`, both existing tests each appear exactly once
- [x] Honest count verified at runtime — backfill SPY/QQQ prints `0 rows (insufficient history)` + `N date(s) processed, 0 row(s) written`; store correctly absent
- [x] Full suite 111 passed, 0 failed, 1 warning (expected cosmetic "Mean of empty slice") — no regressions
- [x] commits 1b9c28a, 33c3bb1, f8a002e exist — verified via git log

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/09-surface-evolution-engine/.continue-here|.continue-here]]
- [[_planning/gamma-omm/phases/09-surface-evolution-engine/09-01-PLAN|09-01-PLAN]]
- [[_planning/gamma-omm/phases/09-surface-evolution-engine/09-01-SUMMARY|09-01-SUMMARY]]
- [[_planning/gamma-omm/phases/09-surface-evolution-engine/09-02-PLAN|09-02-PLAN]]
- [[_planning/gamma-omm/phases/09-surface-evolution-engine/09-02-SUMMARY|09-02-SUMMARY]]
- [[_planning/gamma-omm/phases/09-surface-evolution-engine/09-03-PLAN|09-03-PLAN]]
- [[_planning/gamma-omm/phases/09-surface-evolution-engine/09-PATTERNS|09-PATTERNS]]
- [[_planning/gamma-omm/phases/09-surface-evolution-engine/09-RESEARCH|09-RESEARCH]]

<!-- LINKS:END -->
