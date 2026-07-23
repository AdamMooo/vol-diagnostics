---
phase: 26-severity-stats-alert-engine
plan: 01
subsystem: monitor/severity-ranking
tags: [ecdf, percentile, vrp, skew, surface-evolution, term-ratio]
requires: []
provides:
  - engine/monitor/schema.py (MonitorRow, AlertEvent, METRIC_INVENTORY)
  - engine/monitor/ranker.py (compute_level_ranks, compute_change_rank)
  - engine/monitor/metrics.py (load_metric_series)
  - engine/vol/vrp_history.py:vrp_history_series
affects:
  - Plan 02 (persistence + hysteresis + run_daily wiring)
  - Plan 03 (calibration CLI)
tech-stack:
  added: []
  patterns:
    - "ECDF severity rank via scipy.stats.percentileofscore(kind='rank'), mirroring vrp_history.py's existing convention"
    - "Never-raise contract on all new I/O functions (none-dict / None return on any failure)"
key-files:
  created:
    - engine/monitor/__init__.py
    - engine/monitor/schema.py
    - engine/monitor/ranker.py
    - engine/monitor/metrics.py
    - engine/tests/test_monitor/__init__.py
    - engine/tests/test_monitor/test_ranker.py
    - engine/tests/test_monitor/test_metrics.py
  modified:
    - engine/config.py
    - engine/vol/vrp_history.py
decisions:
  - "vrp_history.vrp_percentile() refactored to delegate to new vrp_history_series() — single source of truth for both the scalar/percentile path and the new monitor metric loader"
metrics:
  duration: "~40 min"
  completed: "2026-07-22"
---

# Phase 26 Plan 01: Severity-Ranking Foundation Summary

Built the ECDF severity-ranking foundation (dual-lookback level rank + two-sided k=5 change rank) and per-metric history loaders for all 17 metric×ticker pairs, with a generalized `vrp_history_series()` extracted from the existing VRP percentile engine as the shared source of truth.

## What Was Built

**Task 1 — Config + schema contracts:**
- `engine/config.py`: added `MONITOR_ONEYR_LOOKBACK_SESSIONS=252`, `MONITOR_CHANGE_K_SESSIONS=5`, `MONITOR_CREDIBILITY_FLOOR_SESSIONS=252`, each with a D-XX rationale comment.
- `engine/monitor/__init__.py`: minimal package docstring, no re-exports (mirrors `engine/gex/__init__.py`).
- `engine/monitor/schema.py`: `MonitorRow` and `AlertEvent` dataclasses; `METRIC_INVENTORY` — 17 (metric, ticker) pairs (5 per-ticker metrics × SPY/QQQ/IWM + 2 SPY-only term ratios). `net_gex` explicitly excluded (D-10).

**Task 2 — ECDF ranker (TDD: RED commit `b05be45`, GREEN commit `8737d21`):**
- `engine/monitor/ranker.py`: `compute_level_ranks(history, today_value, deep_lookback=None, oneyr_lookback=252)` — two fully independent lookback windows (deep + 1yr), each ranked separately via `percentileofscore(kind="rank")`. `compute_change_rank(history, today_value=None, k=5, lookback=None)` — two-sided `|Δk|` rank, magnitude only.
- Both functions never raise; `.dropna()` applied before any numpy conversion; ranks are always computed and labeled with `n` regardless of the credibility floor (gating deferred to Plan 02's hysteresis layer).
- 12 tests, all passing, including a synthetic regime-shift case (long flat history + recent step-up) confirming deep and 1yr ranks can be computed on genuinely different windows, and a two-sided symmetry check (equal-magnitude up-move and down-move rank identically).

**Task 3 — Metric loaders + VRP generalization (TDD: RED commit `6ed1606`, GREEN commit `508d04e`):**
- `engine/vol/vrp_history.py`: extracted `vrp_history_series(ticker) -> pd.Series | None` — the full vi−RV20 vol-points series, date-indexed ascending. `vrp_percentile()` rewritten as a thin wrapper calling `vrp_history_series()` then applying the existing lookback/percentile logic — no behavior change (all 9 existing `test_vrp_history.py` tests still pass unmodified).
- `engine/monitor/metrics.py`: `load_metric_series(ticker, metric_name)` dispatches across 7 branches — `vrp` (delegates to `vrp_history_series`), `skew_25d`/`fly_25d` (gex_snapshots.parquet `front_skew`/`butterfly`), `surface_level`/`surface_rms` (surface_evolution.parquet, `horizon==5`), `term_9d_30`/`term_30_3m` (built from `load_vol_index`, inner-joined by date, reusing `vol_metrics._TERM_SYMBOLS` — not redefined). QQQ/IWM term ratios return `None` (no CBOE siblings). Unknown metric name or any I/O failure returns `None`.

## Deviations from Plan

None — plan executed exactly as written. One frontmatter discrepancy noted below (not a deviation from behavior, just an unused planned artifact):

- `engine/tests/conftest.py` was listed in the plan's `files_modified` frontmatter but no task action referenced creating it, and no test in this plan required shared fixtures beyond what's already local to each test file. Not created — nothing depended on it.

## Verification

```
pytest engine/tests/test_monitor/ -v      # 23 passed (12 ranker + 11 metrics)
pytest engine/tests/test_vrp_history.py -v # 9 passed, no regression
pytest engine/tests -q (excluding 4 pre-existing collection errors
  from a missing `pandas_market_calendars` dependency unrelated to this
  plan, and 11 pre-existing test_app.py failures unrelated to any file
  touched by this plan) # 361 passed
```

All acceptance criteria from the plan's tasks verified directly:
- `METRIC_INVENTORY` has exactly 17 pairs; `net_gex` absent; QQQ/IWM `term_9d_30` absent.
- `config.MONITOR_ONEYR_LOOKBACK_SESSIONS, MONITOR_CHANGE_K_SESSIONS, MONITOR_CREDIBILITY_FLOOR_SESSIONS` = `252 5 252`.
- `load_metric_series("QQQ", "term_9d_30")` returns `None` (verified by test).

## Self-Check: PASSED

- FOUND: engine/monitor/__init__.py
- FOUND: engine/monitor/schema.py
- FOUND: engine/monitor/ranker.py
- FOUND: engine/monitor/metrics.py
- FOUND: engine/tests/test_monitor/test_ranker.py
- FOUND: engine/tests/test_monitor/test_metrics.py
- FOUND commit bb3138c (task 1)
- FOUND commit b05be45 (task 2 RED)
- FOUND commit 8737d21 (task 2 GREEN)
- FOUND commit 6ed1606 (task 3 RED)
- FOUND commit 508d04e (task 3 GREEN)
