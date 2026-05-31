---
phase: 09-surface-evolution-engine
plan: "02"
subsystem: surface-evolution-engine-core
tags: [surface-evolution, scalars, parquet, tdd, backfill]
dependency_graph:
  requires:
    - gex/config.py::SURFACE_EVOLUTION_PUT_WING_CLIP
    - gex/config.py::SURFACE_EVOLUTION_CALL_WING_CLIP
    - gex/config.py::SURFACE_EVOLUTION_DTE_FRONT_MAX
    - gex/config.py::SURFACE_EVOLUTION_DTE_BACK_MIN
    - gex/config.py::SURFACE_EVOLUTION_ATM_CLIP
    - gex/surface_history.py::nth_trading_day_back
    - gex/surface_history.py::load_surface_snapshot
    - gex/analytics.py::rbf_grid
    - gex/analytics.py::coverage_mask
  provides:
    - gex/surface_evolution.py::compute_evolution_scalars
    - gex/surface_evolution.py::update_evolution
    - gex/surface_evolution.py::save_evolution_row
    - gex/surface_evolution.py::load_evolution
    - gex/surface_evolution.py::backfill
    - out/surface_evolution.parquet
  affects:
    - gex/run_daily.py (Plan 03 wires update_evolution into the daily pass)
    - streamlit_app.py (Plan 10 will read load_evolution)
tech_stack:
  added: []
  patterns:
    - pure-function-scalar-computation
    - 8-step-rolling-mean-baseline
    - read-filter-concat-write-idempotency
    - shared-grid-axis-loop-invariant
    - mask-intersection-before-scalar
decisions:
  - "compute_evolution_scalars is a pure function: no I/O, no masking — receives already-masked IV_diff_masked + shared grid axes"
  - "_construct_grid_axes called exactly once per update_evolution from today's surface; dte_grid/otm_grid are loop-invariant across all horizons"
  - "save_evolution_row mirrors validation.py read-filter-concat-write with 3-key dedup (date, ticker, horizon)"
  - "np.ix_ used for 2D subarray indexing in term_change to avoid shape broadcasting issues"
  - "backfill iterates dates oldest-first (reversed) for progress clarity; delegates to update_evolution per date"
key_files:
  created:
    - gex/surface_evolution.py
  modified:
    - gex/tests/test_surface_evolution.py
metrics:
  duration_minutes: 5
  completed_date: "2026-05-31"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 2
---

# Phase 9 Plan 02: Surface Evolution Engine Core Summary

Rolling-mean ΔIV engine with four interpretable scalars (level, rms, skew_change, term_change), idempotent parquet persistence, and a backfill CLI — all backed by 14 passing tests.

## What Was Built

**Task 1 — `gex/surface_evolution.py`:** New module with five public functions:

- `_construct_grid_axes(surface_df)` — builds (dte_grid, otm_grid) from today's surface once per `update_evolution` call; the returned axes are loop-invariant and passed to every `rbf_grid` and `coverage_mask` call for today and all prior dates.
- `compute_evolution_scalars(IV_diff_masked, otm_grid, dte_grid)` — pure function; receives an already-masked ΔIV array and shared grid axes; computes level (nanmean), rms (sqrt nanmean squared), skew_change (put-wing minus call-wing nanmean using config clips), term_change (front-ATM minus back-ATM nanmean using config DTE bands and ATM clip); uses `np.ix_` for 2D subarray indexing; NaN never replaced with 0.
- `update_evolution(ticker, date)` — implements the 8-step rolling-mean algorithm: load today (step 1), construct axes once (step 2), compute IV_today + mask_today (step 3), per-horizon: resolve N prior dates (step 4), load each prior's grid + mask on shared axes (step 5), stack → nanmean baseline (step 6), AND-intersect all masks (step 7), diff → mask → compute_evolution_scalars → save (step 8). Skips horizon on cold-start (nth_trading_day_back returns None).
- `save_evolution_row(...)` — idempotent read-filter-concat-write with 3-key mask (date, ticker, horizon); mirrors `gex/validation.py:40-88`; wrapped in try/except for Windows parquet locking resilience.
- `load_evolution(ticker, horizon=None, days=30)` — mirrors `validation.py:92-102` with optional horizon filter; returns empty DataFrame on missing store or exception.
- `backfill(ticker, start_date)` — retro-computes all dates >= start_date by calling `update_evolution` per date (oldest-first); idempotent.

**Task 2 — `gex/tests/test_surface_evolution.py`:** All 8 stubs replaced with real assertions; 3 new tests added (off-by-one, coverage interval, grid-axis identity). 14 tests total, all passing:

| Test | What It Verifies |
|------|-----------------|
| test_nth_back_resolves_to_correct_index | n=2 from 5-date list returns dates[2] |
| test_nth_back_cold_start_returns_none | n=5 from 3-date list returns None |
| test_nth_back_anchor_not_in_store_returns_none | absent anchor returns None |
| test_nth_back_off_by_one | n=1 returns dates[1], not dates[0] (off-by-one guard) |
| test_scalars_level_is_nanmean_diff | level ≈ -2.0 when prior = today + 2.0pp |
| test_scalars_rms_ignores_nan | rms == sqrt(nanmean(diff²)); differs from zero-padded version |
| test_scalars_coverage_in_unit_interval | 0.0 <= coverage <= 1.0 |
| test_skew_change_wing_split | put-wing +4.0 / call-wing +1.0 → skew_change ≈ +3.0 |
| test_term_change_front_back | front-ATM +3.0 / back-ATM +1.0 → term_change ≈ +2.0 |
| test_grid_axis_identity_across_horizons | prior DTE=110 on today-DTE=160 axes → shape (30,40) |
| test_mask_intersection_excludes_extrapolated_cells | AND mask → NaN at unsupported cells |
| test_evolution_idempotent_on_rerun | second write overwrites level, not appends |
| test_cold_start_no_row_written | no parquet when nth_trading_day_back returns None |
| test_backfill_consistency | backfill level matches daily update_evolution level |

## Commits

| Task | Commit | Files |
|------|--------|-------|
| 1 — surface_evolution.py | 2e1c78c | gex/surface_evolution.py |
| 2 — test stubs filled | d38295a | gex/tests/test_surface_evolution.py |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all stubs from Plan 01 are now real passing tests.

## Threat Flags

None — no new network endpoints, no new auth paths, no new trust boundaries beyond the hardcoded `out/surface_evolution.parquet` write path (constructed via `pathlib.Path(__file__).resolve().parents[1]`; cannot traverse above project root).

## Self-Check: PASSED

- [x] `gex/surface_evolution.py` exists and imports cleanly — verified by `python -c "from gex.surface_evolution import ..."` → "imports OK"
- [x] All five public functions present: compute_evolution_scalars, update_evolution, save_evolution_row, load_evolution, backfill
- [x] `compute_evolution_scalars` is pure: no I/O, no masking in the function body
- [x] `_construct_grid_axes` called exactly once per `update_evolution` (before the horizon loop)
- [x] NaN never replaced with 0 anywhere in the module
- [x] 14 passing tests in test_surface_evolution.py — verified by pytest run
- [x] Full suite 107 passed, 0 failed, 1 warning — no regressions
- [x] commit 2e1c78c exists — verified via git log
- [x] commit d38295a exists — verified via git log

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/09-surface-evolution-engine/09-01-PLAN|09-01-PLAN]]
- [[_planning/gamma-omm/phases/09-surface-evolution-engine/09-01-SUMMARY|09-01-SUMMARY]]
- [[_planning/gamma-omm/phases/09-surface-evolution-engine/09-02-PLAN|09-02-PLAN]]
- [[_planning/gamma-omm/phases/09-surface-evolution-engine/09-03-PLAN|09-03-PLAN]]
- [[_planning/gamma-omm/phases/09-surface-evolution-engine/09-PATTERNS|09-PATTERNS]]
- [[_planning/gamma-omm/phases/09-surface-evolution-engine/09-RESEARCH|09-RESEARCH]]

<!-- LINKS:END -->
