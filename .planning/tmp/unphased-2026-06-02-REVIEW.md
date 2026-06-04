---
phase: unphased-2026-06-02
reviewed: 2026-06-02T00:00:00Z
depth: standard
files_reviewed: 17
files_reviewed_list:
  - gex/analytics.py
  - gex/config.py
  - gex/exposure_engine.py
  - gex/report.py
  - gex/run_daily.py
  - gex/run_daily_yield.py
  - gex/surface_evolution.py
  - gex/surface_sweep.py
  - gex/tests/test_coverage_mask.py
  - gex/tests/test_rbf_grid.py
  - gex/tests/test_surface_evolution.py
  - gex/tests/test_surface_holes.py
  - runners/run_index_app.ps1
  - runners/run_yield_app.ps1
  - runners/yield_daily.ps1
  - streamlit_app.py
  - yield_vol_app.py
findings:
  critical: 3
  warning: 5
  info: 3
  total: 11
status: issues_found
---

# Code Review — unphased 2026-06-02

**Reviewed:** 2026-06-02
**Depth:** standard
**Files Reviewed:** 17
**Status:** issues_found

## Summary

17 files reviewed across the GEX/vol-surface pipeline, both daily runners, the Streamlit dashboards, and the test suite. The core interpolation machinery (rbf_grid, coverage_mask, surface_evolution scalars) is solid. Three blockers surface: a KeyError crash in the Positioning tab triggered by tickers that failed to load, a falsy-zero bug in two IV formatters that suppresses a legitimate 0.0% reading, and a NaN-propagation gap in `compute_evolution_scalars` when all cells in the intersection mask are NaN (all-NaN nanmean returns NaN, which becomes `float("nan")` stored as a float column — technically safe but not caught by any test). Five warnings follow: an off-by-one risk in the `plot_iv_change_surface` coverage mask (it is absent from the ΔIV surface), a password comparison timing attack, a silent hard-coded task path, and two minor correctness concerns.

---

## Critical Issues

### CR-01: KeyError crash in Positioning tab when a ticker has no `s_df`

**File:** `streamlit_app.py:490`
**Issue:** The Positioning tab calls `data["s_df"]` and `data["p_df"]` with bare dict-key access, not `.get()`. `process_ticker()` (via `compute_ticker`) raises on failure and the result dict returned from the except-branch in `run_daily.process_ticker` only contains `{"summary": {"ticker": ..., "error": ...}}` — no `s_df` or `p_df` key. The Positioning tab already skips errored tickers in the surface/evolution tabs (`not all_data[t]["summary"].get("error")`), but the Positioning tab iterates `selected_all` without that guard and reads `data["s_df"]` directly.

The streamlit `fetch_ticker()` wraps `compute_ticker` with no try/except of its own (line 134), so a mid-session network error or CBOE outage that wasn't cached produces an exception that bypasses the `all_data` dict population entirely — but a stale cache returning a partial dict is the more likely path to the bare key access crash.

**Fix:**
```python
# streamlit_app.py ~488
with c1:
    s_df = data.get("s_df")
    if s_df is not None:
        st.plotly_chart(
            plot_oi_by_strike(s_df, spot, ticker, s),
            width='stretch',
        )
    else:
        st.caption(f"{ticker}: OI data unavailable.")
```
And similarly for `data["p_df"]` at line 563:
```python
p_df = data.get("p_df")
if p_df is not None:
    st.plotly_chart(plot_gamma_profile(p_df, spot, ticker, s), ...)
```

---

### CR-02: Falsy-zero bug — IV of exactly 0.0% renders as "—"

**File:** `yield_vol_app.py:78`, `gex/run_daily_yield.py:84`

**Issue:** Both formatters use `if v` as the truthiness gate:

```python
# yield_vol_app.py:78
def _fmt_iv(v) -> str:
    return f"{v:.1f}%" if v else "—"

# run_daily_yield.py:84
def _fmt(v, suffix="", prec=1, prefix="") -> str:
    if v is None:
        return "—"
    return f"{prefix}{v:.{prec}f}{suffix}"
```

`_fmt_iv` treats `v = 0.0` as falsy and shows "—". This is unlikely for IV30 in practice but `rv20` (line 132 of `run_daily_yield.py`) uses `rv20 * 100 if rv20 else None` — if `rv20` is exactly `0.0` it passes `None` to `_fmt`, suppressing the value. The same pattern appears in `yield_vol_app.py:133`.

**Fix:**
```python
def _fmt_iv(v) -> str:
    if v is None:
        return "—"
    return f"{v:.1f}%"
```
And for the rv20 scaling:
```python
rv20_display = rv20 * 100 if rv20 is not None else None
```

---

### CR-03: `compute_evolution_scalars` produces `float("nan")` for `level` and `rms` when all masked cells are NaN, stored without a guard

**File:** `gex/surface_evolution.py:109-112`

**Issue:** When the intersection mask is all-False (two surfaces with zero overlapping hull — possible during market dislocations or ticker restarts with sparse chains), `IV_diff_masked` is all-NaN. `np.nanmean` of an all-NaN array returns `nan` with a RuntimeWarning. `float(nan)` succeeds in Python, so `level` and `rms` are stored as IEEE NaN in the parquet. The `warnings.catch_warnings` block only covers `skew_change` / `term_change` (lines 116-135), not `level`/`rms`. The result is silently stored with all-NaN scalars, which downstream consumers (`evolution_5d_summary`, email formatter `_pp`) do not explicitly handle — `_pp` in `report.py:214` passes `None`-gated check (`if v is not None`), and a stored NaN float is not `None`, so it would render as `nan` in the email table.

**Fix:**
```python
# surface_evolution.py — after computing scalars, guard before persist:
if not np.isfinite(level) and not np.isfinite(rms):
    continue  # all-NaN mask — no meaningful signal, skip this horizon

# Or inside compute_evolution_scalars, wrap level/rms with nan-guard:
with warnings.catch_warnings():
    warnings.simplefilter("ignore", RuntimeWarning)
    level = float(np.nanmean(IV_diff_masked))
    rms = float(np.sqrt(np.nanmean(IV_diff_masked ** 2)))
```
And in `report.py:214` extend `_pp` to handle NaN:
```python
def _pp(v: float | None) -> str:
    import math
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    return f"{v:+.2f}pp"
```

---

## Warnings

### WR-01: `plot_iv_change_surface` has no coverage mask — fabricated extrapolation rendered without warning

**File:** `gex/analytics.py:322-437`

**Issue:** `plot_vol_surface` applies `coverage_mask` and NaN-holes cells outside the convex hull of real quotes (lines 231-233). `plot_iv_change_surface` does not. The ΔIV surface is the difference of two separately-extrapolated grids, so extrapolated regions are doubly fabricated. The Compare tab and the PNG email attachment both display these cells as valid surface — there is no honesty-hole. This is inconsistent with the explicit design principle stated in the codebase (VALID-01).

**Fix:** Apply the intersection mask from `coverage_mask` on both grids before differencing:
```python
mask_today = coverage_mask(df_today, spot_today, dte_grid, otm_grid, dte_floor=_DTE_FLOOR, clip=clip)
mask_prior = coverage_mask(df_prior, spot_prior, dte_grid, otm_grid, dte_floor=_DTE_FLOOR, clip=clip)
mask = mask_today & mask_prior
IV_diff = np.where(mask, IV_today - IV_prior, np.nan)
```

---

### WR-02: Password comparison is timing-attack vulnerable

**File:** `streamlit_app.py:47`

**Issue:** `pwd == expected` is a plain string equality check. For a deployed Streamlit app reachable over the network, this leaks timing information (Python's `==` short-circuits on first differing byte). This is low-severity for an internal tool but the code comment says "no password configured — open access" at line 44, implying it is intended for external deployment.

**Fix:**
```python
import hmac
if hmac.compare_digest(pwd, expected):
```

---

### WR-03: `yield_daily.ps1` has no RunLevel — runs without elevation but doesn't say so; more importantly, it hardcodes `C:\dev\gamma-omm`

**File:** `runners/yield_daily.ps1:9`

**Issue:** `$ProjectDir = "C:\dev\gamma-omm"` is hardcoded. If this repo is cloned anywhere else (CI, colleague machine, relocated vault) the scheduled task silently points at the wrong path and fails with a misleading "file not found" from Task Scheduler rather than an obvious misconfiguration error. Compare `run_index_app.ps1` and `run_yield_app.ps1` which correctly use `$PSScriptRoot\..` for relative resolution.

**Fix:**
```powershell
$ProjectDir = (Resolve-Path "$PSScriptRoot\..").Path
```

---

### WR-04: `surface_sweep.py` — `_load_surface` falls back to live `compute_ticker()` silently; live fetch in a sweep tool can produce misleading timing results

**File:** `gex/surface_sweep.py:98-110`

**Issue:** When the surface history store is empty, `_load_surface` automatically calls `compute_ticker()` (live CBOE fetch). A sweep run immediately after market open will use a fresh noisy chain, while a run after market close uses a different chain. The source label printed ("live compute_ticker()") is correct, but the fallback is silent and non-interactive — a user running the sweep to validate smoothing could unknowingly compare stored historical data against today's live chain if one call uses stored and another uses live.

More concretely: `list_available_dates` returns newest-first (line 102 assumption `dates[0]` is most recent), but the `_load_surface` guard at line 103 checks `if df is not None and not df.empty and spot:` — `spot` is a falsy-zero guard again. If `spot == 0.0` (a degenerate CBOE payload) the fallback fires silently.

**Fix:**
```python
# Guard spot with explicit None check, not truthiness:
if df is not None and not df.empty and spot is not None:
    return df, spot, f"stored snapshot {dates[0]}"
```

---

### WR-05: `surface_evolution.py` — `prior_dates` list can be shorter than `horizon` without any warning, producing a mean baseline over fewer than N days

**File:** `gex/surface_evolution.py:279-283`

**Issue:**
```python
prior_dates = [nth_trading_day_back(ticker, date, k) for k in range(1, horizon + 1)]
prior_dates = [d for d in prior_dates if d is not None]
```
If some intermediate dates are missing from the surface history store (e.g. a day was skipped due to a failed run), the baseline mean is silently computed over fewer than `horizon` days. For a 5-day horizon where day 3 is missing, the baseline is a 4-day mean. This is not flagged anywhere — the stored row says `horizon=5` but reflects a 4-day mean. The parquet has no `n_actual` column.

**Fix:** Add an `n_actual` column to the evolution store and print a warning:
```python
n_actual = len(IV_grids)
if n_actual < horizon:
    print(f"[surface_evolution] {ticker} horizon={horizon}: only {n_actual} prior days available")
# Store n_actual in save_evolution_row (requires schema addition)
```

---

## Info

### IN-01: `surface_evolution.py` — variable shadowing `pd` from outer scope

**File:** `gex/surface_evolution.py:289`

**Issue:** The loop variable `pd_date` is named to avoid shadowing `pd` (pandas), which is correct — but the comment at line 287-289 uses `for pd_date in prior_dates` which is fine. No actual bug, but line 289's variable was likely named `pd_date` specifically because someone noticed the shadow risk. If a future refactor shortens it to `pd`, the import is clobbered silently.

No action required unless the loop variable is renamed.

---

### IN-02: Duplicate `is_trading_day` function definition

**File:** `gex/run_daily.py:37-41`, `gex/run_daily_yield.py:61-65`

**Issue:** Both daily runners define identical `is_trading_day(date)` functions. No bug — just duplication. If the NYSE calendar library changes its API, both copies must be updated.

**Fix:** Extract to a shared utility (e.g. `gex/calendar_utils.py`) and import from both runners.

---

### IN-03: `streamlit_app.py` — `width='stretch'` is not a valid Streamlit `plotly_chart` argument

**File:** `streamlit_app.py:259`, and multiple other `st.plotly_chart` calls throughout the file; same in `yield_vol_app.py:159`.

**Issue:** `st.plotly_chart(..., width='stretch')` passes an unrecognized keyword argument. Streamlit silently ignores unknown kwargs in older versions; in newer versions this may warn or error. The correct parameter is `use_container_width=True`.

**Fix:**
```python
st.plotly_chart(fig, use_container_width=True)
```

---

_Reviewed: 2026-06-02_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
