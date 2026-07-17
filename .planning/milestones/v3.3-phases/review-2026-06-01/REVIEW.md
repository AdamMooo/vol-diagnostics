---
phase: review-2026-06-01
reviewed: 2026-06-01T00:00:00Z
depth: deep
files_reviewed: 9
files_reviewed_list:
  - gex/analytics.py
  - gex/compute.py
  - gex/surface_evolution.py
  - gex/surface_history.py
  - gex/vol_metrics.py
  - gex/run_daily.py
  - gex/report.py
  - gex/exposure_engine.py
  - streamlit_app.py
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Code Review — gex/ module (2026-06-01)

**Reviewed:** 2026-06-01
**Depth:** deep (cross-file call chain tracing)
**Files Reviewed:** 9
**Status:** issues_found

## Summary

The codebase is in good shape overall — the prior audit clearly did substantial work. No
critical correctness or security bugs were found. Three warnings and three info items surfaced,
the most impactful being a documentation bug that ships in the daily email (wrong delta cited in
the skew glossary) and a date-consistency gap between the two parquet snapshot stores.

---

## Warnings

### WR-01: Email glossary cites 50Δ call but implementation uses 25Δ call

**File:** `gex/report.py:313`

**Issue:** The methodology footer in every daily email says:

> "IV(25Δ put) − IV(**50Δ** call)"

Both `config.SKEW_CALL_DELTA = 0.25` and `exposure_engine.compute_skew` select the call closest to 0.25 delta (symmetric 25Δ risk reversal). The email ships a factually incorrect description to readers — they'd have no way of knowing the value they see is a 25Δ RR, not an XZ&Z-style 50Δ–25Δ measure. The methodology text in `streamlit_app.py` is correct (no "50Δ" reference there).

**Fix:**
```python
# gex/report.py line 313 — change:
'<b>Skew (25Δ)</b>: IV(25Δ put) − IV(50Δ call) for the nearest expiry ≥7 DTE, '
# to:
'<b>Skew (25Δ)</b>: IV(25Δ put) − IV(25Δ call) (symmetric risk reversal) '
'for the nearest expiry ≥7 DTE, '
```

---

### WR-02: `validation.save_snapshot` uses local clock; `save_surface_snapshot` uses ET — stores can diverge on same run

**File:** `gex/validation.py:52`  /  `gex/run_daily.py:50,66-67`

**Issue:** `run_daily.run()` derives `today` as `datetime.datetime.now(ET).date()` (line 50) and passes it explicitly to `save_surface_snapshot(..., date=today)`. But `save_snapshot` (the scalar snapshot) independently calls `datetime.date.today()` (local system clock, line 52 of validation.py) without accepting a `date` parameter.

On any machine whose local timezone is ahead of US/Eastern — or if the script is run right after midnight ET — the scalar snapshot lands under a different date than the surface snapshot. Since `surface_evolution.update_evolution` looks up the surface by the ET date, and `compute.py` drives history-based RV20/VRP from the scalar snapshot store, the two stores would refer to the same trading session under different keys. The cross-day history chart in the Positioning tab and the `nth_trading_day_back` lookups would then silently misalign.

The machine today is a developer laptop in Eastern time, so the gap is latent but will activate if the codebase is ever deployed in UTC or another timezone.

**Fix:** Add a `date` parameter to `save_snapshot` and pass the ET date from `run_daily`:

```python
# gex/validation.py
def save_snapshot(summary: dict, ticker: str,
                  skew_df: pd.DataFrame | None = None,
                  date: datetime.date | None = None) -> None:
    ...
    row = {
        "date": date or datetime.date.today(),
        ...
    }

# gex/run_daily.py line 66
save_snapshot(s, ticker, skew_df=data.get("skew_df"), date=today)
```

---

### WR-03: Dead variable `good` — computed but never used in `run_daily.run()`

**File:** `gex/run_daily.py:83`

**Issue:** `good = [d for d in all_data if not d["summary"].get("error")]` is assigned but referenced nowhere afterward. This is a dead code path that looks like it was intended to gate the email on having at least one successful ticker, but the email is built unconditionally from `index_results` regardless of errors.

If the intent was to skip the email when all tickers fail, the guard is silently broken. If it was genuinely removed-but-forgotten, it's dead code.

**Fix:** Either delete the line if no guard is needed:
```python
# delete line 83
```
Or enforce the guard if desired:
```python
if not good:
    print("[gex-daily] All tickers failed — skipping email.")
    return
```

---

## Info

### IN-01: Unused `MULTIPLIER` import inside `plot_oi_by_strike` fallback branch

**File:** `gex/analytics.py:539`

**Issue:** In the `else` branch (no `call_oi`/`put_oi`/`oi` columns), `MULTIPLIER` is imported from `gex.exposure_engine` but never referenced — the proxy is computed directly from `chain_df["gex"].abs()`. The import is a dead remnant of an earlier implementation, imported inside the branch at every call through the fallback path.

**Fix:**
```python
# gex/analytics.py — delete line 539
# from gex.exposure_engine import MULTIPLIER   ← remove
proxy = chain_df["gex"].abs()
```

---

### IN-02: `compute_evolution_scalars` can silently emit `RuntimeWarning` and NaN scalars when DTE grid doesn't span front/back regions

**File:** `gex/surface_evolution.py:121-127`

**Issue:** `term_change` is computed as `nanmean(front_atm) - nanmean(back_atm)`. If `_construct_grid_axes` builds a grid whose DTE range falls entirely above `SURFACE_EVOLUTION_DTE_FRONT_MAX` (30) — possible when the snapshot's shortest expiry is > 30 DTE — then `front_atm` has shape `(n_atm, 0)` and `np.nanmean` emits `RuntimeWarning: Mean of empty slice` before returning NaN. The NaN propagates cleanly into the parquet store (the docstring says this is expected), but the log line in `save_evolution_row` then prints `level=nanpp` which is misleading without context.

Similarly, if `back_atm` is empty (no DTE >= 90), `term_change` becomes `finite - NaN = NaN`. Neither case crashes, but the warning noise is unhelpful.

**Fix:** Add a guard before the subtraction, or suppress the warning explicitly:
```python
# gex/surface_evolution.py
front_mean = np.nanmean(front_atm) if front_atm.size > 0 else float("nan")
back_mean  = np.nanmean(back_atm)  if back_atm.size  > 0 else float("nan")
term_change = float(front_mean - back_mean)
```

---

### IN-03: `_find_zero_crossing` misidentifies zero-sign grid points as crossing boundaries

**File:** `gex/analytics.py:51-57`

**Issue:** `np.sign(0.0) == 0`, which is not equal to either +1 or −1. If any `net_gex` value in the gamma profile is exactly 0.0, the condition `signs[i] != signs[i+1]` fires on the pair `(+1, 0)` before it fires on `(0, −1)` — the first detected "crossing" is the grid point preceding the zero, not the sign-change pair. The interpolation in that case returns `x1` (the zero-grid-point's strike), which is exactly correct numerically, but the function returns early and never checks if a cleaner true sign-change exists further along the grid.

In practice, `net_gex` is a continuous sum of GEX terms and will almost never be exactly 0.0 at a 200-point grid node. Risk is minimal but the logic is subtly wrong.

**Fix:**
```python
def _find_zero_crossing(profile_df: pd.DataFrame) -> float | None:
    vals = profile_df["net_gex"].to_numpy()
    for i in range(len(vals) - 1):
        if vals[i] * vals[i + 1] < 0:   # true sign change, ignores exact-zero nodes
            x0, y0 = profile_df["spot_level"].iloc[i], vals[i]
            x1, y1 = profile_df["spot_level"].iloc[i + 1], vals[i + 1]
            return float(x0 - y0 * (x1 - x0) / (y1 - y0))
        if vals[i] == 0.0:               # grid point lands exactly on zero
            return float(profile_df["spot_level"].iloc[i])
    return None
```

---

_Reviewed: 2026-06-01_
_Reviewer: Claude (adversarial code review)_
_Depth: deep_

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
