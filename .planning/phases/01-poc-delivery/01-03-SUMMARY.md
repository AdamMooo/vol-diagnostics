---
phase: 01-poc-delivery
plan: "03"
subsystem: dashboard
tags: [section-d, reframe, knn, signals, history]
dependency_graph:
  requires: ["01-02"]
  provides: ["section-d-reframed"]
  affects: ["dashboard.py", "build_report.py (indirectly via section_d_analog)"]
tech_stack:
  added: []
  patterns: ["forward-horizon signal lookup", "snap-to-nearest index pattern"]
key_files:
  created: []
  modified:
    - C:\dev\options-quant\dashboard.py
decisions:
  - "section_d_analog() reframed from realized sleeve P&L to forward-realized environment signals"
  - "_forward_realized_environment() snaps to nearest valid date rather than interpolating, returning None when no forward data exists"
metrics:
  duration: "~10 minutes"
  completed: "2026-05-04"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 1
---

# Phase 1 Plan 03: Section D Reframe — Past Periods That Looked Like Now — Summary

One-liner: Section D reframed from realized sleeve P&L table to forward-realized environment signals (vrp, skew, term, dd) at 1m/3m/6m horizons after each K-NN match.

## What Was Done

**Task 1 — Add _forward_realized_environment helper (commit 99515e7)**

Added `_forward_realized_environment(close_dt, sigs, horizons=[21, 63, 126])` before `section_d_analog()` in `dashboard.py`. The helper:
- Concatenates all `sigs.pct` panels into a single DataFrame via `pd.concat(sigs.pct, axis=1)`
- For each horizon (21/63/126 trading days ~ 1m/3m/6m), snaps `close_dt + Timedelta(days=h)` to the nearest valid index date >= that date
- Returns `None` for horizons where no forward data exists (matches are from recent history)

**Task 2 — Reframe section_d_analog() (commit 99515e7, same commit)**

- Header changed: `## Section D — Closest Regime Analogs` → `## Section D — Past Periods That Looked Like Now`
- Description changed: "Mean and dispersion of realized sleeve returns" → "For each matched period, the realized environment (signals) that followed."
- Replaced `nn_rolls = rolls.loc[nn.index, ["open"] + SLEEVE_COLS]` and the sleeve P&L aggregation block with a per-match loop calling `_forward_realized_environment()`
- Output per match: `{h}d forward: vrp=X.XX, skew=X.XX, term=X.XX, dd=X.XX`
- K-NN matching logic (feat DataFrame, `nsmallest(k, "_d")`) unchanged

## Deviations from Plan

None — plan executed exactly as written. Both tasks committed together as one logical unit (they are tightly coupled: the helper is only called by section_d_analog).

## Known Stubs

None. The forward signal values come from live `sigs.pct` data — no hardcoded placeholders.

## Threat Surface Scan

No new network endpoints, auth paths, or trust boundaries introduced. `_forward_realized_environment` operates on in-memory `Signals` data already loaded by the caller. T-01-06 and T-01-07 mitigations are implemented: snap-to-nearest prevents runaway future-date lookups; missing data returns `None` with "(no data)" output.

## Self-Check: PASSED

- `dashboard.py` exists and modified: confirmed
- `_forward_realized_environment` at line 210: confirmed
- `Past Periods That Looked Like Now` in output: confirmed
- `realized environment` language: confirmed
- Module imports cleanly: confirmed (`imported successfully`)
- Commit 99515e7 exists: confirmed
