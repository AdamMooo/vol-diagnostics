---
phase: 11-richer-daily-report
reviewed: 2026-06-01T00:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - gex/compute.py
  - gex/config.py
  - gex/png_export.py
  - gex/report.py
  - gex/run_daily.py
  - gex/tests/test_compute_wiring.py
  - gex/tests/test_png_export.py
  - gex/tests/test_report.py
  - requirements.txt
findings:
  critical: 1
  warning: 4
  info: 3
  total: 8
status: issues_found
---

# Phase 11: Code Review Report

**Reviewed:** 2026-06-01
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Phase 11 adds PNG export, surface evolution, OI walls, VRP/RV20 metrics, and a richer HTML email. The core logic is generally sound. One critical bug: `surface_diagnostics` and `compute_skew_25d`/`compute_term_structure` are not mocked in the test fixtures, yet the fake surface DataFrame lacks required columns (`dte`, `iv_pct`), causing NaN propagation through every `summary["coverage_pct"]` / `"fit_rmse"` assertion path in the test suite — the tests pass accidentally because no assertion covers those keys. Four warnings cover a silent data-loss path (flat-day price change shown as "—"), a type inconsistency in the `as_of` pipeline, a missing `pytz` pin in `requirements.txt`, and an unmocked live I/O call in tests. Three info items cover a stale column name in test fixtures, dead function not yet removed, and the VRP unit inconsistency that is latent for now.

---

## Critical Issues

### CR-01: `surface_diagnostics` not mocked — NaN values silently injected into `summary` dict

**File:** `gex/tests/test_compute_wiring.py:80-85` (fixture), `gex/compute.py:62-92` (production)

**Issue:** `compute_ticker` calls `surface_diagnostics(surface_df, snapshot.spot)` at line 62, then assigns six keys from its result into `summary` (lines 86-92: `coverage_pct`, `fit_rmse`, `max_resid`, `cv_rmse`, `coherence_calendar`, `coherence_butterfly`, `coherence_violations`). In every `mock_result` fixture in `test_compute_wiring.py`, `vol_surface_data` is patched to return `fake_surface_df`, but `surface_diagnostics` is **not mocked**. It runs with the real implementation against `fake_surface_df`.

`surface_diagnostics` requires columns `{"strike", "dte", "iv_pct"}` (checked at `exposure_engine.py:224`). The fixture DataFrame has `{"strike", "expiry", "T_years", "iv"}` — it is missing `"dte"` and `"iv_pct"`. The column-set guard triggers immediately and returns `nan_result` (`coverage_pct=nan`, `fit_rmse=nan`, etc.).

This means every fixture invocation silently injects `float("nan")` into `summary["coverage_pct"]`, `summary["fit_rmse"]`, and so on. The tests pass only because no assertion checks those keys. Any downstream code that writes these NaN values to parquet (`save_snapshot`) will produce NaN rows silently.

Additionally, `compute_skew_25d` and `compute_term_structure` (from `vol_metrics`) are also not mocked and run with the real `fake_df`. If either raises on the minimal fixture, the entire fixture fails — this is fragile even if it currently passes.

**Fix — two required changes:**

1. Add `surface_diagnostics` to the mock patch block in every fixture:

```python
from gex.exposure_engine import surface_diagnostics as _sd
fake_diag = {
    "coverage_pct": 80.0, "fit_rmse": 0.4, "max_resid": 1.2,
    "cv_rmse": 0.6, "coherence_calendar": True,
    "coherence_butterfly": True, "coherence_violations": 0,
}
with mock.patch.object(compute_mod, "surface_diagnostics", return_value=fake_diag), \
     # ... rest of patches
```

2. Also mock `compute_skew_25d` and `compute_term_structure` to avoid real I/O-adjacent computation:

```python
with mock.patch.object(compute_mod, "compute_skew_25d", return_value={"front_month": None, "second_month": None}), \
     mock.patch.object(compute_mod, "compute_term_structure", return_value={"points": [], "classification": "normal", "front_atm_iv": None, "back_atm_iv": None}), \
     # ...
```

---

## Warnings

### WR-01: Flat-day price change (0.0%) silently renders as "—" in email

**File:** `gex/report.py:182, 210-211`

**Issue:** Line 182: `pct_chg = r.get("price_change_pct") or 0.0`. Then line 210: `_fmt_pct(pct_chg) if pct_chg else "—"`. When the market closes exactly flat (a valid and observable event), `price_change_pct` is `0.0`, so `r.get("price_change_pct") or 0.0` yields `0.0`, and `if pct_chg` is `False`, so the Day % row shows "—" instead of "+0.0%". A reader receiving the email on a flat day would see missing data rather than the correct value.

**Fix:**

```python
pct_chg = r.get("price_change_pct")
# ...
_kv_cell("Day %",
    _fmt_pct(pct_chg) if pct_chg is not None else "—",
    value_color=_signed_color(pct_chg) if pct_chg is not None else None)
```

The `or 0.0` on line 182 can be dropped entirely since `_fmt_pct` is already None-safe.

### WR-02: `as_of` type inconsistency between `evolution_5d_summary` and `evolution_section_html` contract

**File:** `gex/vol_metrics.py:264`, `gex/report.py:311`

**Issue:** `evolution_5d_summary` always converts `as_of` to a plain string via `str(date_val)` (line 264). However, `evolution_section_html` in `report.py` at line 311 checks `hasattr(as_of, "strftime")` to decide whether to call `.strftime("%b %d, %Y")` or fall back to `str(as_of)`. In the real pipeline, `as_of` is always a string (from `evolution_5d_summary`) so the `strftime` branch is dead. In the test at `test_report.py:106`, `as_of` is passed as `datetime.date(2026, 5, 27)` — a date object — so the test exercises the `strftime` branch that production never hits.

The consequence: if someone changes `evolution_5d_summary` to return a date object (the natural type), the fallback `str()` branch in `report.py` would format the date as `"2026-05-27"` instead of `"May 27, 2026"`, which is an inconsistent display.

**Fix:** Make `evolution_5d_summary` return the date object (or `None`) rather than stringifying it. Let `evolution_section_html` own the formatting:

```python
# vol_metrics.py:263-264
date_val = row.get("date") if hasattr(row, "get") else (row["date"] if "date" in evol_df.columns else None)
as_of = date_val if date_val is not None else None  # keep as date object
```

Then the `hasattr(as_of, "strftime")` guard in `report.py` becomes meaningful and both paths are exercisable.

### WR-03: `pytz` used in `run_daily.py` but absent from `requirements.txt`

**File:** `gex/run_daily.py:17`, `requirements.txt` (missing)

**Issue:** `run_daily.py` imports `pytz` at line 17 and uses it at lines 34 and 39/54. `pytz` is not listed in `requirements.txt`. The package is installed transitively (via `pandas_market_calendars` or another dependency), but transitive dependencies are not guaranteed across upgrades. A clean `pip install -r requirements.txt` may not include `pytz`, causing `run_daily.py` to fail at import time — specifically when the scheduled task fires.

Python 3.9+ stdlib provides `zoneinfo` as an alternative, but since pytz is already used, the simplest fix is pinning it.

**Fix:**

```
# requirements.txt — add:
pytz>=2024.1
```

Or migrate to `zoneinfo` (stdlib, no dependency):

```python
# run_daily.py
from zoneinfo import ZoneInfo
ET = ZoneInfo("America/New_York")
# datetime.datetime.now(ET).date() still works
```

### WR-04: `_get_risk_free_rate` uses `fast_info.get("lastPrice")` which is not a stable yfinance API

**File:** `gex/compute.py:26`

**Issue:** `yf.Ticker("^IRX").fast_info.get("lastPrice")` — `FastInfo` is a dict-like that has changed field names across yfinance versions. In some versions the key is `"last_price"` (snake_case), in others `"lastPrice"` (camelCase), and the `.get()` method returning `None` on a missing key would silently cause `if rate and rate > 0` to be `False`, falling back to `RISK_FREE_FALLBACK` with no warning printed. The `except` block (line 29) correctly prints a fallback message, but a silent `None` from a key rename would not trigger the `except` — it would silently use 5% without any indication.

**Fix:**

```python
try:
    import yfinance as yf
    ticker_obj = yf.Ticker("^IRX")
    fi = ticker_obj.fast_info
    # Try both naming conventions across yfinance versions
    rate = fi.get("lastPrice") or fi.get("last_price")
    if rate and rate > 0:
        return float(rate) / 100
    print(f"[compute] ^IRX rate fetch returned None; using fallback {config.RISK_FREE_FALLBACK}")
except Exception as exc:
    print(f"[compute] rate fetch failed ({exc}); using fallback {config.RISK_FREE_FALLBACK}")
return config.RISK_FREE_FALLBACK
```

---

## Info

### IN-01: Test fixture uses stale column name `"call_50d_iv"` — real schema is `"call_25d_iv"`

**File:** `gex/tests/test_compute_wiring.py:67, 151, 206`

**Issue:** All three `fake_skew_df` fixtures use column `"call_50d_iv"` but `exposure_engine.compute_skew()` returns column `"call_25d_iv"` (see `exposure_engine.py:151`). The production code only reads `skew_df["skew_pp"].iloc[0]` so this wrong column name doesn't cause a test failure — but the fixture is inaccurate and would mislead anyone adding assertions on skew columns later.

**Fix:** Rename the column in all three fixture DataFrames:

```python
fake_skew_df = pd.DataFrame([
    {"expiry": "2024-06-21", "dte": 37.0, "put_25d_iv": 22.0,
     "call_25d_iv": 18.0, "skew_pp": 4.0},   # was "call_50d_iv"
])
```

### IN-02: `compute_surface_slopes` is dead code — referenced in comments but not deleted

**File:** `gex/exposure_engine.py:158` (not in review scope, but referenced by tests in scope)

**Issue:** `test_compute_wiring.py:TestDeadCodeRemoved` correctly asserts `"compute_surface_slopes"` is absent from `compute.py` — and it is. However, the function still exists in `exposure_engine.py` (line 158) with no callers. The test only guards against it being imported in `compute.py`; it does not assert the function itself is removed. This leaves dead code in the codebase that will confuse future readers.

**Fix:** Delete `compute_surface_slopes` from `gex/exposure_engine.py` entirely, or add an assertion in `TestDeadCodeRemoved`:

```python
EXPOSURE_SRC = pathlib.Path(__file__).resolve().parents[2] / "gex" / "exposure_engine.py"

def test_compute_surface_slopes_removed_from_engine(self):
    src = EXPOSURE_SRC.read_text(encoding="utf-8")
    assert "def compute_surface_slopes" not in src, (
        "compute_surface_slopes dead function must be deleted from exposure_engine.py"
    )
```

### IN-03: VRP stored in `summary` in decimal units; future email rendering will produce wrong values without a unit comment

**File:** `gex/compute.py:117-119`

**Issue:** `vrp = compute_vrp(iv30_decimal, rv20)` stores VRP as a decimal fraction (e.g., `0.027` for 2.7 vol points), while `summary["iv30"]` is in percentage points (e.g., `18.5`). The docstring in `compute_vrp` states "result is in decimal fraction units." The `vrp_headline()` function in `vol_metrics.py` expects `vrp_pp` as percentage points. When `vrp_headline()` is eventually wired to the email (it is not currently used), passing `summary["vrp"]` directly would produce wrong output (e.g., `0.027pp` instead of `2.7pp`).

No active rendering bug today, but the unit mismatch will surface on first use.

**Fix:** Either store `vrp` in percentage points at the summary level to match `iv30`:

```python
# compute.py:117
vrp_decimal = compute_vrp(iv30_decimal, rv20)
vrp = vrp_decimal * 100 if vrp_decimal is not None else None  # → percentage points
```

Or add an explicit comment on the `summary["vrp"]` line noting the decimal unit, so the future caller knows to multiply by 100 before passing to `vrp_headline()`.

---

_Reviewed: 2026-06-01_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/11-richer-daily-report/11-01-PLAN|11-01-PLAN]]
- [[_planning/gamma-omm/phases/11-richer-daily-report/11-01-SUMMARY|11-01-SUMMARY]]
- [[_planning/gamma-omm/phases/11-richer-daily-report/11-02-PLAN|11-02-PLAN]]
- [[_planning/gamma-omm/phases/11-richer-daily-report/11-02-SUMMARY|11-02-SUMMARY]]
- [[_planning/gamma-omm/phases/11-richer-daily-report/11-03-PLAN|11-03-PLAN]]
- [[_planning/gamma-omm/phases/11-richer-daily-report/11-03-SUMMARY|11-03-SUMMARY]]
- [[_planning/gamma-omm/phases/11-richer-daily-report/11-04-PLAN|11-04-PLAN]]
- [[_planning/gamma-omm/phases/11-richer-daily-report/11-04-SUMMARY|11-04-SUMMARY]]
- [[_planning/gamma-omm/phases/11-richer-daily-report/11-CONTEXT|11-CONTEXT]]
- [[_planning/gamma-omm/phases/11-richer-daily-report/11-DISCUSSION-LOG|11-DISCUSSION-LOG]]
- [[_planning/gamma-omm/phases/11-richer-daily-report/11-PATTERNS|11-PATTERNS]]
- [[_planning/gamma-omm/phases/11-richer-daily-report/11-RESEARCH|11-RESEARCH]]

<!-- LINKS:END -->
