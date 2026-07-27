---
phase: 27-microstructure-monitor-ui
plan: 01
subsystem: api
tags: [monitor, parquet, adapter, vrp, pandas, reshape, cold-start]

# Dependency graph
requires:
  - phase: 26-monitor-store
    provides: ranks.parquet / alert_events.parquet stores + MONITOR_ROW/ALERT_EVENT schema + METRIC_INVENTORY
provides:
  - "monitor_reader.load_all_current_ranks: one-row-per-inventory-pair bulk read (latest-per-pair, cold-start safe)"
  - "monitor_reader.load_rank_trail: per-pair ascending history, tail(n) or full (n=None)"
  - "monitor_reader.load_recent_alert_events: last-N-days events, empty DataFrame on cold-start"
  - "vrp_history.vrp_components: exposes vi/rv/vrp legs of the existing VRP series"
affects: [27-02-distribution-board, 27-03-evidence-panels, 27-04-event-email]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "store: pathlib.Path | None = None override mirrored from monitor_store for testability"
    - "[CORRUPT] try/except degrade-to-empty guard (never raises) mirrored from monitor_store"
    - "inventory-spine left-merge guarantees fixed row count regardless of store contents"
    - "single _aligned_vi_rv helper shared by vrp_history_series + vrp_components (one alignment path, VRP-03 clean)"

key-files:
  created:
    - engine/monitor/monitor_reader.py
    - engine/tests/test_monitor/test_monitor_reader.py
  modified:
    - engine/vol/vrp_history.py
    - engine/tests/test_vrp_history.py

key-decisions:
  - "load_all_current_ranks returns exactly len(METRIC_INVENTORY) rows even for absent/sparse/corrupt stores — cold-start is the primary path, not an edge case"
  - "Placeholder pairs carry None ranks/value and n=0 (Int64) so the board renders all tiles without special-casing"
  - "vrp_components reshapes the existing aligned frame via a shared private helper — no second RV/alignment path (avoids the VRP-03 violation)"

patterns-established:
  - "Bulk read/reshape adapter layer over Phase 26 parquet stores; no caching (callers wrap with @st.cache_data)"
  - "Fixed-shape output contract via inventory-spine merge for downstream UI stability"

requirements-completed: [SC-1, SC-5, SC-6]

# Metrics
duration: ~20min
completed: 2026-07-26
---

# Phase 27 Plan 01: Microstructure Monitor Read Foundation Summary

**Thin bulk/trail/event read adapter over the Phase 26 monitor parquet stores plus a vrp_components() exposer of the existing VRP legs — pure reshapes, no new signal or math, with cold-start (sparse/absent stores) as the primary tested path.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-07-26
- **Tasks:** 2 (both TDD)
- **Files created:** 2
- **Files modified:** 2

## Accomplishments
- `monitor_reader.py` bulk-read adapter: `load_all_current_ranks` (17-row inventory guarantee, latest-per-pair), `load_rank_trail` (tail(n)/full), `load_recent_alert_events` (last-N-days) — all cold-start safe, never raise.
- `vrp_components()` added to `vrp_history.py`, exposing vi/rv/vrp legs via a newly extracted shared `_aligned_vi_rv` helper so `vrp_history_series` and `vrp_components` share one alignment definition (no VRP-03 drift).
- Test suite grew from 466 → 482 (+16), 100% green.

## Task Commits

Each task was committed atomically (TDD: test → feat):

1. **Task 1 (RED): monitor_reader cold-start tests** - `40f5408` (test)
2. **Task 1 (GREEN): monitor_reader bulk-read adapter** - `03946cc` (feat, includes fillna→to_numeric refactor to clear FutureWarning)
3. **Task 2 (RED): vrp_components tests** - `b14b879` (test)
4. **Task 2 (GREEN): vrp_components + shared _aligned_vi_rv helper** - `650648a` (feat/refactor)

## Files Created/Modified
- `engine/monitor/monitor_reader.py` - New bulk/trail/event read adapters over ranks.parquet / alert_events.parquet.
- `engine/tests/test_monitor/test_monitor_reader.py` - 12 tests covering sparse/absent/corrupt stores, latest-per-pair, trail n vs n=None, empty-events cold-start.
- `engine/vol/vrp_history.py` - Extracted `_aligned_vi_rv` helper; added public `vrp_components`; `vrp_history_series` now delegates to the helper.
- `engine/tests/test_vrp_history.py` - 4 new tests: vi/rv/vrp columns, vrp==history-series on shared index, None-degradation cases.

## Verification

- `.venv\Scripts\python.exe -m pytest engine/tests/test_monitor/test_monitor_reader.py -x -q` → 12 passed.
- `.venv\Scripts\python.exe -m pytest engine/tests/test_vrp_history.py -x -q` → 15 passed (11 original + 4 new, regression clean).
- `.venv\Scripts\python.exe -m pytest engine/tests -q` → **482 passed** (baseline 466, +16), 100% green.
- Import smoke: `monitor_reader.load_all_current_ranks().shape` → `(17, 13)` against the real sparse store.

## Deviations from Plan

None of substance. One minor in-task cleanup: the initial `fillna(0).astype("Int64")` on placeholder n-columns raised a pandas FutureWarning (object-dtype downcasting) for the absent-store case; switched to `pd.to_numeric(..., errors="coerce").fillna(0).astype("Int64")` to coerce cleanly. Folded into the Task 1 feat commit (`03946cc`). No behavior change.

## Threat Model Compliance

- **T-27-01 (DoS via corrupt/partial parquet):** mitigated — every reader wraps `pd.read_parquet` in try/except with a `[CORRUPT]` print and degrades to placeholder/empty output; tested (`test_corrupt_store_degrades_to_placeholders`, `test_corrupt_store_degrades_to_empty`).
- **T-27-02 (info disclosure):** accepted per plan — no new egress/auth surface introduced; internal vol diagnostics only.

## Known Stubs

None. All returned frames are wired to real store reads; placeholder rows for absent/sparse stores are the intended cold-start contract (documented, consumed by Plans 02–04), not stubs.

## Threat Flags

None — no new network endpoints, auth paths, or trust-boundary surface introduced. Read-only reshape of existing local parquet.

## Self-Check: PASSED
- FOUND: engine/monitor/monitor_reader.py
- FOUND: engine/tests/test_monitor/test_monitor_reader.py
- FOUND (modified): engine/vol/vrp_history.py
- FOUND (modified): engine/tests/test_vrp_history.py
- FOUND commit: 40f5408 (test monitor_reader)
- FOUND commit: 03946cc (feat monitor_reader)
- FOUND commit: b14b879 (test vrp_components)
- FOUND commit: 650648a (feat vrp_components)
