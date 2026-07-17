---
phase: 09-surface-evolution-engine
plan: "01"
subsystem: gex-config-and-surface-history
tags: [config, surface-evolution, test-scaffold, tdd]
dependency_graph:
  requires: []
  provides:
    - gex/config.py::SURFACE_EVOLUTION_PUT_WING_CLIP
    - gex/config.py::SURFACE_EVOLUTION_CALL_WING_CLIP
    - gex/config.py::SURFACE_EVOLUTION_DTE_FRONT_MAX
    - gex/config.py::SURFACE_EVOLUTION_DTE_BACK_MIN
    - gex/config.py::SURFACE_EVOLUTION_ATM_CLIP
    - gex/surface_history.py::nth_trading_day_back
    - gex/tests/test_surface_evolution.py
  affects: []
tech_stack:
  added: []
  patterns:
    - config-constants-with-docstring-rationale
    - index-based-trading-day-resolution
    - pytest-monkeypatch-list-injection
key_files:
  created:
    - gex/tests/test_surface_evolution.py
  modified:
    - gex/config.py
    - gex/surface_history.py
decisions:
  - "Wing clips set at ±5% OTM (symmetric) to balance put-call representation; documented in config docstring"
  - "Front DTE max = 30, back DTE min = 90 — 30-90 gap avoids mixing the volatile monthly roll zone"
  - "ATM band = ±2% — narrow enough for isolation, wide enough for several grid cells at 30-point moneyness resolution"
  - "nth_trading_day_back uses index into descending list_available_dates; no timedelta or calendar arithmetic"
metrics:
  duration_minutes: 8
  completed_date: "2026-05-31"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 3
---

# Phase 9 Plan 01: Interface-First Constants and Horizon Helper Summary

Five locked region constants in config.py and the `nth_trading_day_back` index helper in surface_history.py, providing the stable contract that Plans 02 and 03 build against.

## What Was Built

**Task 1 — `gex/config.py`:** Added a new "Surface evolution scalar region definitions" section after the coverage-mask comment block (after line 94). Five constants with triple-quoted docstrings explaining rationale:
- `SURFACE_EVOLUTION_PUT_WING_CLIP = -5.0` — put-wing %OTM threshold for skew_change
- `SURFACE_EVOLUTION_CALL_WING_CLIP = 5.0` — call-wing %OTM threshold (symmetric)
- `SURFACE_EVOLUTION_DTE_FRONT_MAX = 30` — front-month DTE ceiling for term_change
- `SURFACE_EVOLUTION_DTE_BACK_MIN = 90` — back-month DTE floor for term_change
- `SURFACE_EVOLUTION_ATM_CLIP = 2.0` — ATM band half-width for term_change

**Task 2 — `gex/surface_history.py`:** Appended `nth_trading_day_back(ticker, anchor_date, n)` after `list_available_dates`. Pure list indexing on the descending date list — no timedelta, no calendar calls. Returns `None` on cold-start (idx + n >= len) or missing anchor.

**Task 2 — `gex/tests/test_surface_evolution.py`:** New test file with 3 passing tests for `nth_trading_day_back` and 8 `pytest.skip` stubs for Plan 02/03 scalar and persistence behaviors. Full suite: 96 passed, 8 skipped.

## Commits

| Task | Commit | Files |
|------|--------|-------|
| 1 — config constants | 6e04a91 | gex/config.py |
| 2 — helper + tests | 712bf86 | gex/surface_history.py, gex/tests/test_surface_evolution.py |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

The following test functions in `gex/tests/test_surface_evolution.py` are intentional stubs (`pytest.skip`), not broken tests. They scaffold the test contract for Plans 02 and 03:

| Stub | File | Reason |
|------|------|--------|
| test_scalars_level_is_nanmean_diff | test_surface_evolution.py | Plan 02 implements scalar logic |
| test_scalars_rms_ignores_nan | test_surface_evolution.py | Plan 02 |
| test_skew_change_wing_split | test_surface_evolution.py | Plan 02 |
| test_term_change_front_back | test_surface_evolution.py | Plan 02 |
| test_mask_intersection_excludes_extrapolated_cells | test_surface_evolution.py | Plan 02 |
| test_evolution_idempotent_on_rerun | test_surface_evolution.py | Plan 03 implements persistence |
| test_backfill_consistency | test_surface_evolution.py | Plan 03 |
| test_cold_start_no_row_written | test_surface_evolution.py | Plan 03 |

These stubs are intentional — they do not block the plan goal (interface-first constants and horizon helper).

## Threat Flags

None — config file additions and a pure-Python helper. No network endpoints, no new I/O paths, no schema changes.

## Self-Check: PASSED

- [x] `gex/config.py` contains all five SURFACE_EVOLUTION_ constants — verified by import assertion
- [x] `gex/surface_history.py` exports `nth_trading_day_back` — verified by 3 passing tests
- [x] `gex/tests/test_surface_evolution.py` exists — verified by pytest collection (11 items: 3 pass, 8 skip)
- [x] commit 6e04a91 exists — `git log --oneline` confirms
- [x] commit 712bf86 exists — `git log --oneline` confirms
- [x] full suite 96 passed, 8 skipped — no regressions

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/09-surface-evolution-engine/09-01-PLAN|09-01-PLAN]]
- [[_planning/gamma-omm/phases/09-surface-evolution-engine/09-02-PLAN|09-02-PLAN]]
- [[_planning/gamma-omm/phases/09-surface-evolution-engine/09-03-PLAN|09-03-PLAN]]
- [[_planning/gamma-omm/phases/09-surface-evolution-engine/09-PATTERNS|09-PATTERNS]]
- [[_planning/gamma-omm/phases/09-surface-evolution-engine/09-RESEARCH|09-RESEARCH]]

<!-- LINKS:END -->
