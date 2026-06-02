---
phase: 13-1-day-iv-email-pngs
plan: "01"
subsystem: gex/run_daily
tags: [email, png, iv-surface, tdd]
dependency_graph:
  requires: [surface_history.nth_trading_day_back, analytics.plot_iv_change_surface, png_export.export_png]
  provides: [run_daily._build_png_attachments]
  affects: [gex/run_daily.py, gex/tests/test_run_daily_pngs.py, gex/tests/test_streamlit_app.py]
tech_stack:
  added: []
  patterns: [extracted-function, per-ticker-loop, graceful-skip, inner-try-except]
key_files:
  created:
    - gex/tests/test_run_daily_pngs.py
  modified:
    - gex/run_daily.py
    - gex/tests/test_streamlit_app.py
decisions:
  - "Extracted _build_png_attachments() from inline block — makes per-ticker logic directly testable without mocking the entire run() function"
  - "Module-level import of gex.run_daily avoided in test_run_daily_pngs.py — prevents gex.emailer bleed into sys.modules"
  - "Fixed test_import_no_emailer_bleed to purge stale sys.modules before assertion — makes it robust to test ordering"
metrics:
  duration: "~12 min"
  completed: "2026-06-01"
  tasks_completed: 2
  files_changed: 3
---

# Phase 13 Plan 01: 1-Day ΔIV Email PNGs Summary

**One-liner:** Per-ticker 1-day ΔIV surface PNG loop via `_build_png_attachments()`, replacing the old static surface + SPY-only 5-day ΔIV block, with 7 behavioral tests covering skip logic, label format, and evolution isolation.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for 1-day ΔIV PNG attachment | 3ccade1 | gex/tests/test_run_daily_pngs.py |
| 2 (GREEN) | Swap PNG block + fix bleed test | 26f3a9f | gex/run_daily.py, gex/tests/test_run_daily_pngs.py, gex/tests/test_streamlit_app.py |

## What Changed

**gex/run_daily.py:**
- Removed `plot_vol_surface` from imports (unused after block removal)
- Extracted new `_build_png_attachments(all_data, today, out_dir) -> list` function
- Removed old PNG block: the 3-ticker static surface loop + SPY-only 5-day ΔIV block
- New block: per-ticker loop over `INDEX_TICKERS`; calls `nth_trading_day_back(ticker, today, 1)`, skips when `None`; loads prior snapshot, skips when empty; calls `plot_iv_change_surface` with `label_prior=prior_date.strftime("%b %d")`; exports with `surface_type="div_surface"`; inner try/except per ticker so one failure doesn't abort others

**gex/tests/test_run_daily_pngs.py** (new file):
- `TestOneDayDeltaIVPngs` with 7 tests: three_tickers_attach, missing_prior_snapshot_skips_ticker, empty_prior_df_skips_ticker, export_png_failure_non_blocking, label_prior_format, surface_type_is_div_surface, evolution_store_untouched (source-text assertion)

**gex/tests/test_streamlit_app.py:**
- `test_import_no_emailer_bleed`: added `sys.modules` purge of `gex.emailer`, `gex.run_daily`, and `streamlit_app` before the fresh import — makes the test robust to ordering when other test files legitimately import `gex.run_daily`

## Verification

```
python -m pytest gex/tests/ -q
181 passed in 11.5s
```

Structural checks:
- `grep plot_vol_surface gex/run_daily.py` → no matches
- `grep -c "nth_trading_day_back(ticker, today, 1)" gex/run_daily.py` → 1
- `grep "HORIZONS = (5, 10, 20)" gex/surface_evolution.py` → line 56 (unchanged)
- `update_evolution` not in PNG block → confirmed by test 7

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_import_no_emailer_bleed fragility**
- **Found during:** Task 2 (GREEN phase full-suite run)
- **Issue:** `test_import_no_emailer_bleed` asserts `gex.emailer` not in `sys.modules`, but after the new `test_run_daily_pngs.py` tests ran (which import `gex.run_daily` inside test methods), `gex.emailer` was already in `sys.modules` — causing the bleed test to fail due to test ordering, not an actual bleed from `streamlit_app`
- **Fix:** Purge `gex.emailer`, `gex.run_daily`, and `streamlit_app` from `sys.modules` inside `test_import_no_emailer_bleed` before the fresh import + assertion — preserves the test's actual intent (streamlit_app doesn't import run_daily/emailer when loaded clean) while being robust to session state
- **Files modified:** gex/tests/test_streamlit_app.py
- **Commit:** 26f3a9f

**2. [Rule 1 - Bug] Removed module-level gex.run_daily import from test file**
- **Found during:** Task 2 initial test run
- **Issue:** `from gex.run_daily import INDEX_TICKERS` at module level in `test_run_daily_pngs.py` would have bleeded `gex.emailer` at collection time
- **Fix:** Defined `INDEX_TICKERS = ["SPY", "QQQ", "IWM"]` locally in the test file with a comment explaining why; all `_build_png_attachments` imports moved inside test methods
- **Files modified:** gex/tests/test_run_daily_pngs.py
- **Commit:** 26f3a9f

## TDD Gate Compliance

- RED gate: commit `3ccade1` — `test(13-01): add failing tests for 1-day ΔIV PNG attachment logic`
- GREEN gate: commit `26f3a9f` — `feat(13-01): swap PNG block to per-ticker 1-day ΔIV surfaces`
- REFACTOR gate: not needed — code is clean after extraction

## Known Stubs

None.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes. The PNG block reads from the existing `surface_history` parquet store (same trust boundary as before, T-13-01 accepted). No new threat surface introduced.

## Self-Check: PASSED

- gex/tests/test_run_daily_pngs.py: EXISTS
- gex/run_daily.py: EXISTS, contains `_build_png_attachments`
- Commits 3ccade1 and 26f3a9f: FOUND in git log
- 181 tests pass, 0 failures

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/agent-a8cb05d96a3dd9b0b/ROADMAP|ROADMAP]] · [[_planning/agent-a8cb05d96a3dd9b0b/STATE|STATE]]
**Phase siblings:**
- [[_planning/agent-a8cb05d96a3dd9b0b/phases/13-1-day-iv-email-pngs/13-01-PLAN|13-01-PLAN]]

<!-- LINKS:END -->
