---
phase: 06-computation-engine
reviewed: 2026-05-26T15:49:53Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - gex/vol_metrics.py
  - gex/analytics.py
  - gex/compute.py
  - gex/validation.py
  - streamlit_app.py
  - gex/tests/test_vol_metrics.py
  - gex/tests/test_vol_surface_strip.py
  - gex/tests/test_compute_wiring.py
  - gex/tests/test_validation_schema.py
findings:
  critical: 1
  warning: 2
  info: 2
  total: 5
status: issues_found
---

# Phase 6: Code Review Report

**Reviewed:** 2026-05-26T15:49:53Z
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Phase 6 delivers `gex/vol_metrics.py` (4 new pure functions), pipeline wiring in `compute.py`, parquet schema extension in `validation.py`, GEX overlay strip from `plot_vol_surface`, and a 36-test suite — all 36 tests pass. The implementation is clean and well-structured. One critical unit mismatch in VRP computation will produce garbage values in production. Two warnings: an ineffective mock that silently passes without actually isolating I/O, and a stale methodology text. Two info items.

---

## Critical Issues

### CR-01: VRP unit mismatch — iv30 is percentage, rv20 is decimal

**File:** `gex/compute.py:88`

**Issue:** `snapshot.iv30` is stored as a percentage (e.g., `18.0` = 18% vol) — confirmed by `report.py:136` docstring ("annualized vol in %") and the `.1f%` display format in `streamlit_app.py:147`. `compute_rv20` returns a decimal fraction (e.g., `0.158` for 16% vol) — the formula `sqrt(252) * std(log_returns)` on raw price ratios produces values in [0, 0.5] range. `compute_vrp(iv30, rv20)` subtracts them directly: `18.0 - 0.158 ≈ 17.8`, which is approximately `iv30` every time and economically meaningless. Actual VRP for SPY is typically 1–5 vol points.

The unit inconsistency also affects `validation.py` — the `vrp` column written to parquet will contain these inflated values, corrupting historical data from the first snapshot forward.

**Fix:** Normalize `iv30` to decimal before computing VRP, or multiply `rv20` by 100 before passing it. The cleanest fix is in `compute.py` where both values are in scope:

```python
# gex/compute.py — after rv20 is computed
rv20 = compute_rv20(spot_series)
iv30_decimal = (snapshot.iv30 / 100.0) if snapshot.iv30 else None
vrp = compute_vrp(iv30_decimal, rv20)
```

Or equivalently, convert `rv20` to percentage before passing:

```python
rv20_pct = rv20 * 100 if rv20 is not None else None
vrp = compute_vrp(snapshot.iv30, rv20_pct)
```

Pick one convention and document it on `compute_vrp`. The VRP test at `test_vol_metrics.py:137` (`compute_vrp(25.0, 20.0)`) should also be updated to reflect whichever convention is chosen, using realistic units (e.g., `compute_vrp(18.0, 15.8)` if both are percentages).

---

## Warnings

### WR-01: Ineffective mock for load_history in test_compute_wiring.py

**File:** `gex/tests/test_compute_wiring.py:101`

**Issue:** `mock.patch("gex.validation.load_history", ...)` patches the function in the `gex.validation` module namespace, but `compute.py` uses `from gex.validation import load_history` — importing the name directly into the `compute` module namespace. The patch does not intercept the call inside `compute_ticker`. The test passes only because `load_history` returns a real empty DataFrame when the parquet store doesn't exist on the test machine. If a parquet store exists (e.g., on a dev machine with history), the test would exercise live data rather than the mock, making `test_cold_start_rv20_and_vrp_are_none` potentially wrong.

**Fix:**

```python
# Replace:
mock.patch("gex.validation.load_history", return_value=pd.DataFrame())
# With:
mock.patch.object(compute_mod, "load_history", return_value=pd.DataFrame())
```

### WR-02: Stale methodology text claims IV surface has GEX overlay meridians

**File:** `streamlit_app.py:344-346`

**Issue:** The methodology expander still reads: "Annotated with **γ-flip, call wall, and put wall meridians** so the smile shape can be read against the dealer positioning state." Phase 6 stripped these overlays from `plot_vol_surface()` as part of the strategic reframe. The claim is now false — the surface renders clean with no GEX annotations. A user reading this text would expect annotations that don't exist.

**Fix:** Update the IV Surface bullet in the methodology expander:

```python
# Replace the existing IV Surface description sentence:
# "Annotated with **γ-flip, call wall, and put wall meridians** so the smile
#  shape can be read against the dealer positioning state — the cross-product
#  between vol structure and GEX."
# With:
# "Clean surface — GEX overlays (γ-flip, call wall, put wall meridians) removed
#  per v3.2 reframe; GEX context available in the Strikes tab."
```

---

## Info

### IN-01: Dead variable in test_rv20_manual

**File:** `gex/tests/test_vol_metrics.py:121`

**Issue:** `log_returns = np.log(arr[1:] / arr[:-1])` is computed but never used. The expected value is built from `last_21` on lines 123-124. The dead assignment adds confusion — it looks like it feeds the expected calculation but doesn't.

**Fix:** Remove lines 120-121 (`arr = np.array(prices)` and `log_returns = ...`) from the test body. They're scaffolding that survived a refactor.

### IN-02: compute_surface_slopes remains in exposure_engine.py (dead code not fully cut)

**File:** `gex/exposure_engine.py:135-175`

**Issue:** `compute_surface_slopes()` is still present in `exposure_engine.py` and is still imported in `compute.py` line 15 (`from gex.exposure_engine import compute_gex, strike_gex, gamma_profile, vol_surface_data, compute_skew`). Wait — re-checking: it is NOT in the import list on line 15. The function exists in `exposure_engine.py` but is no longer called from anywhere in the reviewed files. The phase 6 success criterion says to remove calls, not the function itself. However the function is dead code that survived the cleanup and may confuse future readers. No test asserts its removal from `exposure_engine.py` (only from `compute.py`, which is correct).

**Fix:** Remove `compute_surface_slopes()` from `gex/exposure_engine.py` in a follow-up cleanup, or note it as deferred. Not blocking.

---

_Reviewed: 2026-05-26T15:49:53Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/06-computation-engine/06-01-PLAN|06-01-PLAN]]
- [[_planning/gamma-omm/phases/06-computation-engine/06-01-SUMMARY|06-01-SUMMARY]]
- [[_planning/gamma-omm/phases/06-computation-engine/06-02-PLAN|06-02-PLAN]]
- [[_planning/gamma-omm/phases/06-computation-engine/06-02-SUMMARY|06-02-SUMMARY]]
- [[_planning/gamma-omm/phases/06-computation-engine/06-03-PLAN|06-03-PLAN]]
- [[_planning/gamma-omm/phases/06-computation-engine/06-03-SUMMARY|06-03-SUMMARY]]
- [[_planning/gamma-omm/phases/06-computation-engine/06-CONTEXT|06-CONTEXT]]
- [[_planning/gamma-omm/phases/06-computation-engine/06-PATTERNS|06-PATTERNS]]
- [[_planning/gamma-omm/phases/06-computation-engine/06-RESEARCH|06-RESEARCH]]

<!-- LINKS:END -->
