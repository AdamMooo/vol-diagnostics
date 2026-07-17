---
phase: "15"
plan: "01"
subsystem: vol-index-data-layer
tags: [data-layer, cboe, parquet, bloomberg-swappable, tdd]
dependency_graph:
  requires: []
  provides: [gex.vol_index, gex.config.DEFAULT_VOL_INDICES]
  affects: [phase-16-vrp, phase-17-term-structure, phase-18-dashboard]
tech_stack:
  added: []
  patterns: [cboe-csv-fetch, idempotent-parquet-append, fail-soft-403, tdd-red-green]
key_files:
  created:
    - gex/vol_index.py
    - gex/tests/test_vol_index.py
  modified:
    - gex/config.py
decisions:
  - "Top-level import of DEFAULT_VOL_INDICES from gex.config (not lazy) — circular risk is nil since config.py imports nothing from gex/"
  - "Single feat commit covers both vol_index.py and config.py — config is a hard dependency for the import to resolve"
  - "dropna on OPEN/HIGH/LOW/CLOSE only (not DATE) — malformed numeric rows dropped, date parse errors would be upstream CBOE issue"
metrics:
  duration: "12 min"
  completed: "2026-06-05"
  tasks_completed: 2
  files_changed: 3
---

# Phase 15 Plan 01: Vol-Index Data Layer (fetch + store + load) Summary

**One-liner:** Isolated CBOE vol-index CSV fetch + idempotent parquet store via `gex/vol_index.py`, with `DEFAULT_VOL_INDICES = ['VIX', 'VXN', 'RVX', 'VIX9D', 'VIX3M']` in `gex/config.py`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| RED | Failing tests for vol_index | d6207f2 | gex/tests/test_vol_index.py |
| GREEN (T1+T2) | vol_index.py + config.py | c9a2742 | gex/vol_index.py, gex/config.py |

## What Was Built

`gex/vol_index.py` is the sole module that knows how to fetch or read CBOE vol-index CSV data. It exports:

- `_fetch_cboe_vol_index(symbol)` — HTTP GET from `cdn.cboe.com/api/global/us_indices/daily_prices/{SYM}_History.csv`; returns None on 403 or RequestException; `pd.to_numeric(..., errors="coerce")` + `dropna` handles malformed rows per T-15-01
- `save_vol_index_snapshot(df, symbol, date)` — idempotent parquet append under `out/vol_index/{SYM}.parquet`; filters `hist[hist["date"] != today]` before concat
- `load_vol_index(symbol, days)` — returns empty DataFrame (not exception) when parquet absent; sorted ascending; optional days limit returns most-recent N rows
- `refresh_vol_indices(symbols)` — loops over DEFAULT_VOL_INDICES, calls fetch+save, never raises
- `STORE_DIR` — `out/vol_index/` path constant

`gex/config.py` gains `DEFAULT_VOL_INDICES: list[str] = ["VIX", "VXN", "RVX", "VIX9D", "VIX3M"]` in the new "Vol-index data layer" section.

## Test Coverage

12 tests, all passing (TDD RED → GREEN):

- `_fetch_cboe_vol_index`: 200 returns DataFrame with typed columns; 403 returns None; RequestException returns None
- `save_vol_index_snapshot`: creates parquet; idempotency on same date; None/empty df is no-op
- `load_vol_index`: empty DataFrame when no parquet; correct columns + date type after save; ascending sort; days limit returns most-recent N ascending

## Deviations from Plan

None — plan executed exactly as written.

## Threat Surface Scan

No new surface beyond the plan's threat model. T-15-01 (CSV row tampering) mitigated via `pd.to_numeric(..., errors="coerce")` + `dropna`. T-15-02/03/04 accepted per plan disposition.

## Known Stubs

None. The module is a complete data layer with no placeholder values or hardcoded empties that flow to callers.

## TDD Gate Compliance

1. `test(15-01)` commit d6207f2 — RED gate (12 failing tests)
2. `feat(15-01)` commit c9a2742 — GREEN gate (12 passing tests)

## Self-Check: PASSED

- `gex/vol_index.py` exists: FOUND
- `gex/config.py` contains DEFAULT_VOL_INDICES: FOUND
- `gex/tests/test_vol_index.py` exists: FOUND
- Commit d6207f2 (RED): FOUND
- Commit c9a2742 (GREEN): FOUND

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/agent-aa53d427524e51f5f/ROADMAP|ROADMAP]] · [[_planning/agent-aa53d427524e51f5f/STATE|STATE]]
**Phase siblings:**
- [[_planning/agent-aa53d427524e51f5f/phases/15-vol-index-data-layer/15-01-PLAN|15-01-PLAN]]
- [[_planning/agent-aa53d427524e51f5f/phases/15-vol-index-data-layer/15-02-PLAN|15-02-PLAN]]
- [[_planning/agent-aa53d427524e51f5f/phases/15-vol-index-data-layer/15-CONTEXT|15-CONTEXT]]
- [[_planning/agent-aa53d427524e51f5f/phases/15-vol-index-data-layer/15-DISCUSSION-LOG|15-DISCUSSION-LOG]]

<!-- LINKS:END -->
