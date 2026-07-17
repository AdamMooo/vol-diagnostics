---
phase: 09-surface-evolution-engine
reviewed: 2026-05-31T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - gex/config.py
  - gex/run_daily.py
  - gex/surface_evolution.py
  - gex/surface_history.py
  - gex/tests/test_surface_evolution.py
findings:
  critical: 0
  warning: 3
  info: 4
  total: 7
status: issues_found
---

# Phase 9: Code Review Report

**Reviewed:** 2026-05-31
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Reviewed the surface ΔIV evolution engine (`surface_evolution.py`), the `nth_trading_day_back`
helper added to `surface_history.py`, the four new evolution config constants, the
`run_daily` integration wiring, and the test suite. I verified the load-bearing contracts
empirically rather than by inspection:

- **Parquet idempotency holds.** Tested multi-horizon writes + repeated overwrites of the same
  `(date, ticker, horizon)` key: store stays at the correct row count, `horizon` keeps `int64`
  dtype, and the dedup mask matches because a `datetime.date` column round-trips through
  pyarrow as `object`-dtype holding `datetime.date` (so `hist["date"] == row["date"]` is True).
- **Non-blocking evolution contract holds.** The only change to `run_daily.run()` is the
  evolution loop (lines 73–80), which is wrapped per-ticker in `try/except` — an evolution
  failure logs `[WARN] ... (non-blocking)` and the email path proceeds.
- **NaN handling is spec-correct.** `np.nanmean`/`np.sqrt(np.nanmean(...))` propagate NaN
  rather than coercing to 0; the all-NaN-region `RuntimeWarning: Mean of empty slice` is the
  known, intended behavior and is NOT flagged.
- **Honest row-count semantics hold.** `backfill` returns rows actually persisted (cold-start
  dates contribute 0), confirmed by `test_backfill_reports_honest_row_count`.
- All 18 tests pass.

No BLOCKER-class defects found. The engine's core algorithm and persistence are sound. The
findings below are a latent timezone/date-source inconsistency that is masked by the current
deployment host, plus a handful of robustness and dead-code items.

## Structural Findings (fallow)

No `<structural_findings>` block was provided with this review. None to report.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: Two different definitions of "today" — write-side uses local clock, read-side uses ET

**File:** `gex/surface_history.py:37` and `gex/run_daily.py:50,77`
**Issue:** `save_surface_snapshot` keys the day's rows with `datetime.date.today()` (the host's
**local** system date, line 37). But `run_daily.run()` derives `today = datetime.datetime.now(ET).date()`
(line 50) and passes that ET date into `update_evolution(ticker, today)` (line 77). The
evolution engine then looks up that ET date in the store via `load_surface_snapshot(ticker, date)`
and `nth_trading_day_back(ticker, date, ...)`, both of which match against the *local*-dated rows.

When the host's local date and the ET date diverge (host in a non-ET timezone, or a run that
straddles local midnight), `update_evolution`'s Step-1 lookup misses today's freshly-written
snapshot, hits the `surface_today.empty or spot_today is None` early-return (line 250–251), and
**silently writes 0 evolution rows** — no error, no warning, just a `0 evolution row(s) written`
line. The scheduled task triggers at `16:30` *local* time (`runners/gex_daily.ps1`), so on the
ET deployment box the two dates coincide and the bug is masked; it surfaces only off that host.
The system is internally inconsistent — the date the snapshot is filed under and the date the
engine asks for are produced by two different clocks.
**Fix:** Single-source the date. Either pass the ET date into `save_surface_snapshot` from the
caller, or have the snapshot helper accept an explicit `date` argument instead of calling
`datetime.date.today()`:
```python
# gex/surface_history.py
def save_surface_snapshot(surface_df, ticker, spot, date: datetime.date | None = None):
    today = date or datetime.date.today()
    ...
# gex/run_daily.py:67 — pass the same ET `today` used by update_evolution
save_surface_snapshot(data.get("surface_df"), ticker, spot=s["spot"], date=today)
```

### WR-02: `save_surface_snapshot` is unguarded inside the main ticker loop — can abort the email path

**File:** `gex/run_daily.py:66-67`
**Issue:** The spec for this phase is that an evolution failure must never block the email send
path. The evolution loop (lines 73–80) honors that. But `save_surface_snapshot(...)` at line 67
runs earlier, inside the main per-ticker loop, and is **not** wrapped in `try/except`. The
evolution engine depends on the surface snapshot, so a malformed `surface_df` (e.g. a missing
expected column in `surface_df[["dte","strike","moneyness","log_moneyness","iv_pct"]]`,
`surface_history.py:38`) would raise a `KeyError` here, unwind `run()`, and skip the entire
email build/send. Note: the `save_surface_snapshot` call was introduced in phase 08, not this
phase, but it is now the upstream dependency that feeds the phase-09 engine, and the
non-blocking guarantee should extend to the data the engine reads.
**Fix:** Wrap the snapshot save the same way `process_ticker` and the evolution loop are
guarded, so one bad ticker degrades to a warning rather than killing the report:
```python
if not s.get("error"):
    save_snapshot(s, ticker, skew_df=data.get("skew_df"))
    try:
        save_surface_snapshot(data.get("surface_df"), ticker, spot=s["spot"])
    except Exception as exc:
        print(f"  [WARN] {ticker} surface snapshot failed (non-blocking): {exc}")
```

### WR-03: `nth_trading_day_back` is called O(horizon) times per horizon, re-reading the parquet each call

**File:** `gex/surface_evolution.py:267-275`
**Issue:** For each horizon, `update_evolution` calls `nth_trading_day_back` once for the guard
(line 267) and then again for every `k in range(1, horizon+1)` (lines 271–274). Each call invokes
`list_available_dates(ticker)` (`surface_history.py:107`), which does a fresh
`pd.read_parquet(path, columns=["date"])`. For horizon=20 that is 21 parquet reads to resolve a
date list that is identical across all calls within the invocation — and the same list is
re-read again for horizons 5 and 10. This is not in the v1 performance scope, but it is also a
**correctness fragility**: the list is re-derived mid-loop, so if the store changed between reads
(concurrent run) the resolved prior dates could be inconsistent with the guard. Resolve the
prior-date list once and slice it.
**Fix:** Compute the descending date list once and index into it:
```python
available = list_available_dates(ticker)  # once, before the horizon loop
...
if date not in available:
    return 0
anchor = available.index(date)
for horizon in HORIZONS:
    if anchor + horizon >= len(available):
        continue
    prior_dates = available[anchor + 1 : anchor + horizon + 1]
    prior_date_label = available[anchor + horizon]
```

## Info

### IN-01: `good` is computed but never used (dead code)

**File:** `gex/run_daily.py:83`
**Issue:** `good = [d for d in all_data if not d["summary"].get("error")]` is assigned and never
read anywhere in `run()`. Dead binding. (Pre-existing — outside the phase-09 diff — but adjacent
to the edited region.)
**Fix:** Delete line 83.

### IN-02: CLI silently no-ops on a bare positional ticker without `--backfill`

**File:** `gex/surface_evolution.py:384-388`
**Issue:** `python -m gex.surface_evolution SPY` (forgetting `--backfill`) falls through to
`parser.print_help()` with no diagnostic explaining that `--backfill` is required. Likewise
`--backfill` with no ticker just prints help. A user running the backfill by memory gets a help
dump instead of a targeted message.
**Fix:** Emit an explicit message before help, e.g.
`print("Nothing to do: pass a ticker with --backfill, e.g. `--backfill SPY`.")` in the else branch.

### IN-03: `compute_evolution_scalars` can divide-by-zero / empty-slice on a degenerate `otm_grid`

**File:** `gex/surface_evolution.py:114-119,130`
**Issue:** As a documented *pure public function*, `compute_evolution_scalars` accepts arbitrary
grid axes. If a caller passes an `otm_grid` whose values never cross ±5 (the wing clips) or whose
size is 0, `put_wing_idx`/`call_wing_idx` select zero rows and `np.nanmean` of an empty slice
returns NaN with a RuntimeWarning; `IV_diff_masked.size == 0` makes `coverage` a `0/0` NaN. The
internal caller (`update_evolution`) always supplies the standard ±15% / 30-point grid so this
never triggers in production, and NaN propagation is the intended contract — hence Info, not
Warning. Worth a one-line note in the docstring that the wing/ATM scalars assume the grid spans
the configured clip bands.
**Fix:** Add to the docstring: "Assumes `otm_grid` spans at least the put/call wing clips and is
non-empty; degenerate axes yield NaN scalars by design." Optionally guard `coverage` against an
empty array.

### IN-04: `from gex.surface_evolution import update_evolution` imported inside `run()`

**File:** `gex/run_daily.py:74`
**Issue:** The evolution import is done lazily inside `run()` rather than at module top with the
other `gex.*` imports (lines 19–24). If this is a deliberate guard against an import-time failure
in the evolution module breaking the whole orchestrator, it works — but it is inconsistent with
the surrounding import style and the import error would surface only at runtime, after the ticker
loop has already done work. If the intent is isolation, prefer wrapping the import in the existing
non-blocking pattern; if not, hoist it to the top.
**Fix:** Move `from gex.surface_evolution import update_evolution` to the top-level import block,
or document the lazy import with a one-line comment explaining the isolation intent.

---

_Reviewed: 2026-05-31_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

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

<!-- LINKS:END -->
