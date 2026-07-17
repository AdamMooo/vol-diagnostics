---
phase: 17-term-structure-regime
plan: 01
subsystem: vol-metrics
tags: [term-structure, vix, vol-index, card-model]
requires:
  - phase: 15
    provides: Vol-index data layer with VIX/VIX9D/VIX3M parquet store
provides:
  - compute_term_ratios(ticker) in vol_metrics.py — SPY gets VIX9D/VIX and VIX/VIX3M ratios from vol-index store
  - CardField "VIX Term" on SPY card with contango/backwardation labels
  - QQQ/IWM gracefully omit the field (no CBOE siblings)
  - CBOE sibling availability documented in CLAUDE.md
affects: [engine-compute, card-model, dashboard-card, email-card]
tech-stack:
  added: []
  patterns: [conditional-field-emission, deferred-import-for-testability]
key-files:
  created: [engine/tests/test_term_ratios.py]
  modified: [engine/vol/vol_metrics.py, engine/compute.py, engine/report/card_model.py, CLAUDE.md]
key-decisions:
  - "VIX term ratios use latest close from vol-index store — same session alignment as VRP."
  - "Field conditionally emitted only when ratios are non-None (SPY only)."
  - "Contango/backwardation word shown inline but no categorical regime label or score."
  - "CBOE does not publish VXN9D/VXN3M or RVX9D/RVX3M — confirmed 2026-06-23."
patterns-established:
  - "Conditional CardField emission: build list, then append if data exists, then extend with remaining."
requirements-completed: [TERM-01, TERM-02]
duration: 12min
completed: 2026-06-23
---

# Phase 17 Plan 01 — Summary

## What Was Done

1. **`engine/vol/vol_metrics.py`** — Added `compute_term_ratios(ticker)` that maps
   SPY → (VIX9D, VIX, VIX3M) and returns `{term_ratio_9d_30d, term_ratio_30d_3m}`.
   QQQ/IWM return None/None (no CBOE siblings).

2. **`engine/compute.py`** — Wired `compute_term_ratios(ticker)` into `compute_ticker()`;
   summary now carries `term_ratio_9d_30d` and `term_ratio_30d_3m`.

3. **`engine/report/card_model.py`** — Added `_fmt_term_ratios()` formatter and conditional
   "VIX Term" CardField after VRP. Field omitted entirely for QQQ/IWM. Trust tag: "market".

4. **`CLAUDE.md`** — Documented CBOE sibling availability finding per SC-3.

5. **`engine/tests/test_term_ratios.py`** — 10 tests covering compute, formatting, and
   card integration.

## Test Results

324 passed, 16 skipped (up from 314 — 10 new tests added).
