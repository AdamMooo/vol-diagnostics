---
phase: 26-severity-stats-alert-engine
plan: 02
subsystem: monitor/persistence-alerting
tags: [hysteresis, alert-state-machine, parquet-store, credibility-gate, run_daily-wiring]
requires:
  - engine/monitor/schema.py (MonitorRow, AlertEvent, METRIC_INVENTORY)
  - engine/monitor/ranker.py (compute_level_ranks, compute_change_rank)
  - engine/monitor/metrics.py (load_metric_series)
provides:
  - engine/monitor/hysteresis.py (check_alert_transition)
  - engine/monitor/monitor_store.py (save_monitor_row, save_alert_event, load_prior_monitor_row, compute_and_save_monitor_rows)
  - out/monitor/ranks.parquet (accrues on every scheduled run_daily.py execution)
  - out/monitor/alert_events.parquet (accrues on every alert transition)
affects:
  - Plan 03 (calibration CLI — will overwrite MONITOR_ALERT_BAND_* with replay-derived values)
  - Phase 27 (dashboard/email consumption of ranks.parquet + alert_events.parquet)
tech-stack:
  added: []
  patterns:
    - "Idempotent read-mask-concat-atomic pattern (mirrors engine/data/validation.py:save_snapshot) applied to ranks.parquet"
    - "Append-only pattern (no dedup key) applied to alert_events.parquet — every transition is a distinct fact"
    - "Non-blocking per-ticker try/except wiring into run_daily.py, matching PNG export / observation-log pattern"
key-files:
  created:
    - engine/monitor/hysteresis.py
    - engine/monitor/monitor_store.py
    - engine/tests/test_monitor/test_hysteresis.py
    - engine/tests/test_monitor/test_store.py
  modified:
    - engine/config.py
    - engine/run_daily.py
decisions:
  - "MONITOR_ALERT_BAND_ENTRY/ESCALATE/EXIT added to config.py as provisional placeholders (97/99/87) per plan's explicit instruction, each labeled PROVISIONAL pending Plan 03's calibration CLI"
metrics:
  duration: "~35 min"
  completed: "2026-07-22"
---

# Phase 26 Plan 02: Persistence + Hysteresis + Daily Wiring Summary

Built the transition-with-hysteresis alert state machine gated by the 252-session credibility floor, the two monitor parquet stores (ranks.parquet idempotent-append, alert_events.parquet append-only), and wired both into run_daily.py's orchestration loop so the monitor now accrues automatically on every scheduled run.

## What Was Built

**Task 1 — Hysteresis state machine (TDD: test commit `82872df`, feat commit `6c84a0a`):**
- `engine/monitor/hysteresis.py`: `check_alert_transition(today_rank, n, yesterday_state, entry, escalate, exit_, credibility_floor=config.MONITOR_CREDIBILITY_FLOOR_SESSIONS) -> (alert_type|None, new_state)`. Pure function, no shared state — three independent rank_kinds (level_deep, level_1yr, change) can be in different band_states simultaneously with zero cross-talk, verified directly in the test suite.
- States: "out" → "in_entry" (fires "entry") → "in_escalate" (fires "escalation", re-fire only on escalation per D-04); any in_* state drops to "out" on rank < exit_ (no fire — hysteresis exit). `today_rank is None` or `n < credibility_floor` always forces `(None, "out")` regardless of prior state, per D-08.
- 8 tests, all passing.

**Task 2 — Monitor parquet stores (TDD: test commit `78ddc7d`, feat commit `f13815c`):**
- `engine/monitor/monitor_store.py`: `save_monitor_row` (idempotent on date+ticker+metric, mirrors `validation.py:save_snapshot`'s mask-then-concat), `save_alert_event` (append-only, no dedup key), `load_prior_monitor_row` (mirrors `validation.py:load_prior_snapshot`), `compute_and_save_monitor_rows(ticker, summary, today, band_entry, band_escalate, band_exit) -> int` — orchestrates per-metric: loads history via `metrics.load_metric_series`, computes level+change ranks via `ranker.py`, reads yesterday's three band_states via `load_prior_monitor_row`, runs `check_alert_transition` three times independently, saves the `MonitorRow` and any fired `AlertEvent`s. Never raises per-metric — wrapped in try/except/continue so one metric's failure (e.g. missing history) does not block the others.
- 6 tests, all passing, including an explicit "never raises when metric history missing" test and a "writes 7 rows for SPY" count check (5 per-ticker metrics + 2 SPY-only term ratios).

**Task 3 — Wire into run_daily.py:**
- Added `MONITOR_ALERT_BAND_ENTRY=97`, `MONITOR_ALERT_BAND_ESCALATE=99`, `MONITOR_ALERT_BAND_EXIT=87` to `engine/config.py`, each labeled PROVISIONAL pending Plan 03's calibration CLI (per the plan's explicit instruction — these are not final band choices).
- `run_daily.py`'s `run()` now calls `monitor_store.compute_and_save_monitor_rows(ticker, ...)` per ticker in a new loop placed after the existing snapshot saves and after the surface-evolution `update_evolution` loop (since surface_level/surface_rms metrics need today's evolution row persisted first), wrapped in try/except with a printed WARN — non-blocking, matching the existing PNG-export/observation-log pattern (T-26-03 mitigation).

## Deviations from Plan

None — plan executed exactly as written. One environment note, not a deviation:

- `python -m engine.run_daily --dry-run` could not be executed end-to-end in this environment because `pandas_market_calendars` (a pre-existing `requirements.txt` dependency, not introduced by this plan) is not installed locally — the same gap Plan 01's summary documented as causing 4 pre-existing test-collection errors (`test_compute_oi_wiring.py`, `test_data_health.py`, `test_data_loader.py`, `test_session.py`). This blocks any live exercise of `run_daily.py`'s `run()` function, including the new monitor-wiring code path, in this session. The wiring itself was verified by: (1) AST-parsing `run_daily.py` for syntax correctness, (2) full unit-test coverage of `hysteresis.py` and `monitor_store.py` in isolation (all 14 new tests + all 37 tests under `engine/tests/test_monitor/` pass), and (3) manual review of the call site against the plan's exact specification. Recommend running `pip install pandas_market_calendars` and re-verifying `--dry-run` output includes "monitor row(s) written" lines and that `out/monitor/ranks.parquet` exists, before this plan is considered fully live-verified.

## Verification

```
pytest engine/tests/test_monitor/ -v   # 37 passed (8 hysteresis + 6 store + 12 ranker + 11 metrics)
pytest engine/tests -q (excluding the 4 pre-existing pandas_market_calendars
  collection errors and 11 pre-existing test_app.py failures, both unrelated
  to any file touched by this plan)   # 375 passed
```

Acceptance criteria verified directly:
- `check_alert_transition` never raises on `today_rank=None` (explicit test).
- A rank at/above entry with n below the floor never returns "entry" (explicit test).
- Re-saving the same (date, ticker, metric) via `save_monitor_row` produces exactly one row (explicit test).
- `compute_and_save_monitor_rows` never raises when one metric's `load_metric_series` returns None (explicit test).
- `grep -n "compute_and_save_monitor_rows" engine/run_daily.py` finds the new call site.

The `--dry-run` live-run acceptance criterion (monitor stdout lines + `out/monitor/*.parquet` existing) is deferred per the environment note above — could not run end-to-end due to the missing pre-existing dependency, not something introduced by this plan.

## Self-Check: PASSED

- FOUND: engine/monitor/hysteresis.py
- FOUND: engine/monitor/monitor_store.py
- FOUND: engine/tests/test_monitor/test_hysteresis.py
- FOUND: engine/tests/test_monitor/test_store.py
- FOUND commit 82872df (task 1 RED)
- FOUND commit 6c84a0a (task 1 GREEN)
- FOUND commit 78ddc7d (task 2 RED)
- FOUND commit f13815c (task 2 GREEN)
- FOUND commit 787ee14 (task 3)
