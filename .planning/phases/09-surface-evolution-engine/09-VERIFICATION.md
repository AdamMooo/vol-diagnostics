---
phase: 09-surface-evolution-engine
verified: 2026-05-31T23:59:59Z
status: passed
score: 6/6 success criteria verified
overrides_applied: 0
re_verification: false
---

# Phase 09: Surface Evolution Engine — Verification Report

**Phase Goal:** Build the `surface_evolution` module — decompose ΔIV into level / rms / skew-change / term-change scalars on the masked grid against an N-day rolling-mean baseline, at 5/10/20 trading-day horizons, persisted daily and accumulating, computed as a non-blocking pass in `run_daily`, comparable cross-ticker, with a backfill from existing surface history.

**Verified:** 2026-05-31
**Status:** PASSED — All 6 success criteria achieved; 111 tests green (18 new surface-evolution tests, 93 baseline)

## Success Criteria Verification

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Four scalars (level/rms/skew/term) computed vs N-day rolling baseline on masked grid; mask = today ∩ all N baseline-day masks | ✓ VERIFIED | `gex/surface_evolution.py:83-138` compute_evolution_scalars implements all four scalars with proper mask intersection applied in `update_evolution` steps 7-8 (lines 301-310); test coverage: `test_scalars_level_is_nanmean_diff`, `test_scalars_rms_ignores_nan`, `test_skew_change_wing_split`, `test_term_change_front_back` all pass |
| 2 | Horizons 5/10/20 resolved against stored trading sessions; labelled with real prior date; 1-day excluded | ✓ VERIFIED | `gex/surface_evolution.py:55` HORIZONS = (5, 10, 20); `gex/surface_history.py:103-121` nth_trading_day_back uses index-based list lookup (no calendar arithmetic); `update_evolution` lines 267 & 315 label each horizon with `prior_date_label = nth_trading_day_back(ticker, date, horizon)` (the furthest day in window); test coverage: `test_nth_back_resolves_to_correct_index`, `test_nth_back_cold_start_returns_none`, `test_nth_back_off_by_one` all pass |
| 3 | Metrics persist to out/surface_evolution.parquet, idempotent on (date, ticker, horizon), accumulating | ✓ VERIFIED | `gex/surface_evolution.py:51` STORE path; `save_evolution_row` lines 145-199 implements read-filter-concat-write idempotency with 3-key dedup mask (lines 180-185); test coverage: `test_evolution_idempotent_on_rerun` passes; cold-start test confirms 0 rows written when insufficient history (spec-correct); backfill test confirms honest row counting |
| 4 | Evolution runs as non-blocking pass inside run_daily after snapshot save; failure never blocks email | ✓ VERIFIED | `gex/run_daily.py:73-80` evolution pass inserted between snapshot loop end (line 67) and index_results construction (line 82); per-ticker try/except at lines 76-80 catches all exceptions and prints WARN; email path at lines 86-101 is strictly downstream and unconditional on evolution success; test coverage: `test_run_daily_evolution_failure_does_not_propagate` passes |
| 5 | Surface change comparable across SPY/QQQ/IWM (cross-ticker schema consistency) | ✓ VERIFIED | `save_evolution_row` lines 162-172 writes identical schema (date, ticker, horizon, prior_date, level, rms, skew_change, term_change, coverage) for all tickers; test coverage: `test_cross_ticker_schema_consistency` writes rows for all three tickers and asserts identical columns and horizon subset ⊆ {5,10,20} |
| 6 | Backfill routine retro-computes evolution from existing surface_history | ✓ VERIFIED | `gex/surface_evolution.py:327-363` backfill loops over dates, calls update_evolution per date (own horizon iteration), reports honest persisted-row counts; CLI entry-point at lines 370-388 accepts --backfill, ticker, --start args; test coverage: `test_backfill_consistency` and `test_backfill_reports_honest_row_count` both pass; CLI reachable via `python -m gex.surface_evolution --help` |

## Implementation Detail Verification

### Requirement ID Traceability (from REQUIREMENTS.md)

| REQ-ID | Phase 9 Plan | Criterion | Implementation | Status |
|--------|--------------|-----------|-----------------|--------|
| EVOL-01 | 09-02 | Four scalars on masked grid | `compute_evolution_scalars()` pure function; `update_evolution()` steps 1-8 | ✓ VERIFIED |
| EVOL-02 | 09-01 + 09-02 | 5/10/20 horizons via nth_trading_day_back | `HORIZONS=(5,10,20)` constant; index-based date resolution | ✓ VERIFIED |
| EVOL-03 | 09-02 | Idempotent parquet persistence | `save_evolution_row()` read-filter-concat-write; 3-key dedup | ✓ VERIFIED |
| EVOL-04 | 09-03 | Non-blocking run_daily integration | Evolution pass at lines 73-80 in `run_daily.py`; per-ticker try/except | ✓ VERIFIED |
| EVOL-05 | 09-02 + 09-03 | Cross-ticker comparability | Identical schema; all tickers write same columns | ✓ VERIFIED |
| EVOL-06 | 09-03 | Backfill CLI | `backfill()` function; `__main__` argparse block | ✓ VERIFIED |

### Artifacts Verification (Three Levels)

#### Level 1: Existence

| Artifact | Path | Exists | Substantive | Wired |
|----------|------|--------|-------------|-------|
| Config constants | `gex/config.py:96-124` | ✓ | ✓ docstrings | ✓ imported in `surface_evolution.py:39` |
| nth_trading_day_back | `gex/surface_history.py:103-121` | ✓ | ✓ pure function, index-based | ✓ imported in `surface_evolution.py:43` |
| compute_evolution_scalars | `gex/surface_evolution.py:83-138` | ✓ | ✓ pure function, 4 scalars | ✓ called in `update_evolution:310` |
| update_evolution | `gex/surface_evolution.py:230-320` | ✓ | ✓ 8-step algorithm, 230 lines | ✓ called in `run_daily.py:77` and `backfill:349` |
| save_evolution_row | `gex/surface_evolution.py:145-199` | ✓ | ✓ idempotent parquet write | ✓ called in `update_evolution:311-317` |
| load_evolution | `gex/surface_evolution.py:202-223` | ✓ | ✓ read filter return | ✓ importable for Phase 10 |
| backfill | `gex/surface_evolution.py:327-363` | ✓ | ✓ date iteration, honest counts | ✓ wired to __main__:386 |
| __main__ CLI | `gex/surface_evolution.py:370-388` | ✓ | ✓ argparse, full help | ✓ runnable via `python -m gex.surface_evolution` |
| surface_evolution.parquet | `out/surface_evolution.parquet` | ✗ | N/A | N/A |

**Note on parquet:** Not created (cold-start; only 2 trading days of surface_history exist). Horizons 5/10/20 each require N+1 prior sessions. This is spec-correct; test suite confirms zero rows written. File will be created once ~6 trading days of history accumulate.

#### Level 2: Substantiveness Check

- `compute_evolution_scalars`: Pure function; receives IV_diff_masked + grids; returns 4 scalars; no I/O, no masking. Correct.
- `_construct_grid_axes`: Called once per `update_evolution` from today's surface (lines 254). Grid axes loop-invariant across all horizons and all prior-date calls (used in lines 257-261 for today, lines 285-289 for each prior date). Correct.
- `update_evolution`: Implements canonical 8-step algorithm: step 1 load today (lines 249-251), step 2 construct axes once (line 254), step 3 compute today's grid+mask (lines 257-262), steps 4-8 per horizon: resolve dates (lines 267-275), load grids+masks on same axes (lines 281-292), stack baseline (lines 297-299), mask intersection (lines 302-304), diff+mask+scalars (lines 307-318). Correct.
- `save_evolution_row`: Idempotent write with 3-key dedup (date, ticker, horizon) at lines 180-185; returns bool indicating persistence success. Correct.
- `backfill`: Iterates dates oldest-first (line 347), calls update_evolution per date (line 349; no inner horizon loop), returns total rows written (not date count). Honest reporting. Correct.

#### Level 3: Wiring Verification

**Key wiring pattern: evolution pass in run_daily**

```python
# gex/run_daily.py:73-80
print("\n[run_daily] Computing surface evolution...")
from gex.surface_evolution import update_evolution
for ticker in INDEX_TICKERS:
    try:
        rows = update_evolution(ticker, today)
        print(f"  {ticker}: {rows} evolution row(s) written")
    except Exception as exc:
        print(f"  [WARN] {ticker} evolution failed (non-blocking): {exc}")
```

✓ WIRED: Import is inline (inside `run()` function), per-ticker loop, try/except isolation, prints row count, exception does not propagate to email path (lines 86-101 are unconditional).

**Key wiring pattern: compute_evolution_scalars call in update_evolution**

```python
# gex/surface_evolution.py:310-318
scalars = compute_evolution_scalars(IV_diff_masked, otm_grid, dte_grid)
if save_evolution_row(
    date=date,
    ticker=ticker,
    horizon=horizon,
    prior_date=prior_date_label,
    **scalars,
):
    rows_written += 1
```

✓ WIRED: Scalars dict unpacked into save_evolution_row; return bool tracked; row count accumulated.

### Data-Flow Trace (Level 4)

**Artifact: compute_evolution_scalars**

Data source verification:
- Input: `IV_diff_masked` (already-masked ΔIV array constructed in `update_evolution` step 8, lines 307-308)
- Processing: nanmean of masked array (no NaN replacement); np.sqrt, np.nanmean on subarray views
- Output: dict of 4 float scalars; coverage = count of non-NaN / total cells

✓ VERIFIED: Data flows from compute_evolution_scalars into save_evolution_row (lines 311-317).

**Artifact: update_evolution**

Data source verification:
- Loads today's surface and spot (line 249) via `load_surface_snapshot()`
- Loads each prior date's surface and spot (line 282) via same helper
- Constructs grid axes from today's surface only (line 254)
- Computes RBF grids for today and all prior dates on shared axes (lines 257-258, 285-286)
- Applies coverage masks to both (lines 260-261, 288-289)
- Stacks prior grids and computes nanmean baseline (lines 297-299)
- Mask intersection applied before diff (lines 302-304, 308)
- Diff computed and masked (line 308)
- Scalars computed from masked diff (line 310)
- Persisted via save_evolution_row (lines 311-317)

✓ VERIFIED: Data flows through all 8 steps correctly. No hardcoded static values; all IV/mask values sourced from real snapshots and interpolation.

**Artifact: backfill**

Data source verification:
- Lists available dates (line 338) via `list_available_dates()`
- Filters to dates >= start_date (line 339)
- Iterates dates oldest-first (line 347)
- Calls update_evolution per date (line 349)
- Accumulates actual rows written (line 351)

✓ VERIFIED: Data flows from surface_history into update_evolution into save_evolution_row.

### Test Suite Verification

**Test run output:**

```
111 passed, 1 warning in 13.56s
```

**Surface-evolution-specific tests (18 new):**

1. `test_nth_back_resolves_to_correct_index` — ✓ PASS
2. `test_nth_back_cold_start_returns_none` — ✓ PASS
3. `test_nth_back_anchor_not_in_store_returns_none` — ✓ PASS
4. `test_nth_back_off_by_one` — ✓ PASS (off-by-one guard)
5. `test_scalars_level_is_nanmean_diff` — ✓ PASS
6. `test_scalars_rms_ignores_nan` — ✓ PASS
7. `test_scalars_coverage_in_unit_interval` — ✓ PASS
8. `test_skew_change_wing_split` — ✓ PASS
9. `test_term_change_front_back` — ✓ PASS
10. `test_grid_axis_identity_across_horizons` — ✓ PASS (loop-invariance)
11. `test_mask_intersection_excludes_extrapolated_cells` — ✓ PASS
12. `test_evolution_idempotent_on_rerun` — ✓ PASS
13. `test_cold_start_no_row_written` — ✓ PASS
14. `test_evolution_does_not_raise_on_empty_store` — ✓ PASS
15. `test_run_daily_evolution_failure_does_not_propagate` — ✓ PASS (non-blocking)
16. `test_cross_ticker_schema_consistency` — ✓ PASS (SPY/QQQ/IWM)
17. `test_backfill_consistency` — ✓ PASS
18. `test_backfill_reports_honest_row_count` — ✓ PASS

**Config & helper imports:**

- ✓ `from gex.config import SURFACE_EVOLUTION_*` — 5 constants present with docstrings
- ✓ `from gex.surface_history import nth_trading_day_back` — pure function, index-based
- ✓ `from gex.surface_evolution import {compute_evolution_scalars, update_evolution, save_evolution_row, load_evolution, backfill}` — all importable

**Baseline regression:**

- Before Phase 9: 93 tests (Phase 8 baseline)
- After Phase 9 Plans 01-03: 111 tests
- Delta: +18 new tests
- Status: No regressions; all baseline tests still pass

### Anti-Pattern Scan

**Debt markers:** None found in modified files (`gex/config.py`, `gex/surface_history.py`, `gex/surface_evolution.py`, `gex/run_daily.py`)

**Stubs in production code:** None. (Test stubs in Plan 01 were replaced with real implementations in Plan 02.)

**Empty implementations:** None. All public functions have substantive implementations.

**Hardcoded static values that should be config:**
- ✓ All region thresholds (PUT_WING_CLIP, CALL_WING_CLIP, DTE_FRONT_MAX, DTE_BACK_MIN, ATM_CLIP) are config constants
- ✓ Horizons (5, 10, 20) are a module constant
- ✓ Grid dimensions (30, 40) reference config constants

### CLI Verification

**Backfill CLI reachable:**

```
python -m gex.surface_evolution --help
```

Output shows:
- positional argument: ticker (SPY/QQQ/IWM)
- --backfill flag
- --start flag (optional, defaults to 90 days ago)

**Behavior (on current 2-date cold-start):**

```
python -m gex.surface_evolution --backfill SPY
[surface_evolution] backfill: ... (2 dates processed, 0 row(s) written)
```

✓ Honest reporting; zero rows because insufficient history for any horizon.

### Cold-Start Data Status

**Current surface_history:** Only 2 trading days (2026-05-28, 2026-05-29)

**Horizon requirements:**
- Horizon 5: needs 6 sessions (1 today + 5 back) — NOT MET
- Horizon 10: needs 11 sessions — NOT MET
- Horizon 20: needs 21 sessions — NOT MET

**Expected behavior:** `update_evolution()` returns 0 for all horizons; `out/surface_evolution.parquet` is not created. Test `test_cold_start_no_row_written` confirms this is correct.

**Accumulation timeline:** As surface_history grows:
- After ~6 trading days: horizon=5 starts writing rows
- After ~11 trading days: horizon=10 starts writing rows
- After ~21 trading days: horizon=20 starts writing rows

All handled automatically by `update_evolution()` check at line 268: `if prior_date_label is None: continue`.

## Summary

**Phase goal achievement:** ✓ COMPLETE

All six success criteria are satisfied:
1. Four scalars computed on masked grid against rolling baseline
2. Horizons 5/10/20 resolved via stored sessions (index-based, not calendar)
3. Idempotent persistence with 3-key dedup
4. Non-blocking run_daily integration with per-ticker error handling
5. Cross-ticker schema consistency (SPY/QQQ/IWM)
6. Backfill CLI for cold-start population

**Test coverage:** 18 new tests, all passing; 111 total suite green; no regressions.

**Code quality:** No debt markers, no stubs in production code, all region thresholds config-driven.

**Operational readiness:** Evolution pass runs automatically in run_daily; backfill CLI ready for historical population; cold-start behavior correct (zero rows written until sufficient history accumulates).

---

_Verified: 2026-05-31_
_Verifier: Claude (gsd-verifier)_

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/09-surface-evolution-engine/.continue-here|.continue-here]]
- [[_planning/gamma-omm/phases/09-surface-evolution-engine/09-01-PLAN|09-01-PLAN]]
- [[_planning/gamma-omm/phases/09-surface-evolution-engine/09-01-SUMMARY|09-01-SUMMARY]]
- [[_planning/gamma-omm/phases/09-surface-evolution-engine/09-02-PLAN|09-02-PLAN]]
- [[_planning/gamma-omm/phases/09-surface-evolution-engine/09-02-SUMMARY|09-02-SUMMARY]]
- [[_planning/gamma-omm/phases/09-surface-evolution-engine/09-03-PLAN|09-03-PLAN]]
- [[_planning/gamma-omm/phases/09-surface-evolution-engine/09-03-SUMMARY|09-03-SUMMARY]]
- [[_planning/gamma-omm/phases/09-surface-evolution-engine/09-PATTERNS|09-PATTERNS]]
- [[_planning/gamma-omm/phases/09-surface-evolution-engine/09-RESEARCH|09-RESEARCH]]
- [[_planning/gamma-omm/phases/09-surface-evolution-engine/09-REVIEW|09-REVIEW]]

<!-- LINKS:END -->
