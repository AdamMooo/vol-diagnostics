---
phase: 27-microstructure-monitor-ui
plan: 02
subsystem: ui
tags: [streamlit, dashboard, distribution-board, monitor, sparkline, cold-start]

# Dependency graph
requires:
  - phase: 27-microstructure-monitor-ui (plan 01)
    provides: monitor_reader bulk/trail reads + METRIC_INVENTORY-shaped ranks
provides:
  - "Distribution board landing surface (Regime tab) — one row per METRIC_INVENTORY pair from monitor_reader"
  - "Net-GEX sign state chip (not a ranked row) above the board"
  - "Row-selection → selected_monitor_row session-state key for the Plan 03 evidence panel"
  - "Risk bar removed; freshness banner shrunk to a dot unless stale"
affects: [27-03-evidence-panels]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "st.dataframe(on_select='rerun', selection_mode='single-row') for board row selection"
    - "st.column_config.LineChartColumn(y_min=0,y_max=100) for the 10-session deep-rank trail"
    - "selection written to a SEPARATE session_state key, never back into the widget's own key"
    - "@st.fragment on the board section; @st.cache_data on the bulk-rank + trail reads"
    - "inventory-shaped board rows (no tickers×metrics cartesian) — term rows SPY-only degrade cleanly"

key-files:
  created: []
  modified:
    - app.py
    - engine/tests/test_app.py

key-decisions:
  - "Regime tab lands on the distribution board (_distribution_board_section) instead of _render_environment_hero"
  - "Net-GEX = sign chip above the board, not a ranked row (GEX-as-candidate decision 2026-07-22)"
  - "Row selection maps board idx straight back to the raw ranks frame (same order) → (ticker, metric)"
  - "Shallow chain metrics get a 'building to N' depth label; a shown rank is not yet a deep-history rarity claim"
  - "Evidence panel is a Plan-03 stub placeholder here (header + caption only)"

patterns-established:
  - "Distribution-board-as-landing consuming Phase 26 ranks via Plan-01 adapter, cold-start safe"
  - "Widget selection → separate session-state key hand-off between plans"

requirements-completed: [SC-1, SC-3, SC-5, SC-7]

# Metrics
duration: ~25min (incl. interrupted-executor recovery)
completed: 2026-07-26
---

# Phase 27 Plan 02: Microstructure Monitor Distribution Board Summary

**The dashboard Regime tab now lands on a distribution board — one row per METRIC_INVENTORY pair (deep + 1yr level %ile, two-sided change %ile, credibility depth label, 10-session deep-rank trail sparkline) sourced from Plan 01's monitor_reader — with net-GEX as a sign chip, the old AMPLIFYING/MIXED risk bar removed, and the freshness banner shrunk to a dot unless stale.**

## Performance

- **Duration:** ~25 min (executor was interrupted after its first commit; the board work was recovered, verified, and completed inline)
- **Completed:** 2026-07-26
- **Tasks:** 2 (chrome/chip + board)
- **Files modified:** 2

## Accomplishments
- Regime tab lands on `_distribution_board_section(all_data)` (replaces `_render_environment_hero`).
- Board: one row per inventory pair via `_load_current_ranks_cached()` → `monitor_reader.load_all_current_ranks`; columns Deep %ile / 1yr %ile / Δ %ile (NumberColumn), Depth (credibility label), Trail (LineChartColumn, 10-session deep rank).
- Net-GEX rendered as a sign state chip (`_net_gex_chip`) above the board — Stabilizing / Amplifying / em-dash on missing.
- AMPLIFYING/MIXED risk bar and the full-width `fresh-ok` bar removed; freshness is a compact dot unless stale.
- Row selection (`on_select="rerun"`, `selection_mode="single-row"`) writes `(ticker, metric)` to the separate `selected_monitor_row` session-state key; evidence panel header/caption stubbed for Plan 03.
- 4 new tests; suite 482 → 486 green; `app.py` imports cleanly.

## Task Commits

1. **Chrome: remove risk bar, shrink freshness to dot, add net-GEX chip** - `8cda7c2` (feat)
2. **Distribution board landing surface + tests** - `4917f6a` (feat)

## Files Modified
- `app.py` - Added `monitor_reader`/`METRIC_INVENTORY` imports, `_load_current_ranks_cached` + `_load_rank_trail_cached` cached reads, `_METRIC_LABELS`, `_to_int_or_none`, `_distribution_board_section` fragment; removed risk bar + `fresh-ok` style; Regime tab now renders the board.
- `engine/tests/test_app.py` - 4 Phase 27 tests: board wiring contract (SC-1), net-GEX chip sign + degradation (SC-3), `_to_int_or_none` NA handling, cached bulk read is inventory-shaped (SC-1/SC-5).

## Verification

- `.venv\Scripts\python.exe -m pytest engine/tests -q` → **486 passed** (482 → 486, +4), 100% green.
- `app.py` import smoke → "app.py imported OK" (SC-7).
- `ast.parse` on app.py + test_app.py → both parse.

## Deviations from Plan

- **Process:** the spawned executor was interrupted after committing only Task 1 (`8cda7c2`); the Task 2 board work was left uncommitted in the working tree. Recovered inline: verified syntax/import/config-key existence, ran the full suite (486 green), then committed the board as `4917f6a`. No content lost.
- **Pre-existing convention:** the board `st.dataframe` uses `use_container_width=True`, consistent with the other dashboard dataframes (an existing test asserts that pattern). The separate `use_container_width`→`width="stretch"` migration (commit `704f01f`) covered only the deprecated *button* call; migrating all dataframes is out of this plan's scope.

## Cold-Start Note

By design the board is near-empty right now: `out/monitor/ranks.parquet` holds ~2 dates and zero alerts have fired, so most %ile cells are blank/placeholder and trails have <10 points. This is the documented cold-start contract from Plan 01, not a bug — it fills in as `run_daily` accrues sessions.

## Self-Check: PASSED
- FOUND (modified): app.py
- FOUND (modified): engine/tests/test_app.py
- FOUND commit: 8cda7c2 (feat chrome + net-GEX chip)
- FOUND commit: 4917f6a (feat distribution board)
- FOUND: _distribution_board_section in app.py
- FOUND: 486 tests green
