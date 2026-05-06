---
phase: 04-historical-tab
reviewed: 2026-05-06T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - gex/validation.py
  - gex/tests/test_validation_history.py
  - streamlit_app.py
findings:
  critical: 1
  warning: 2
  info: 2
  total: 5
status: issues_found
---

# Phase 4: Code Review Report

**Reviewed:** 2026-05-06
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Three files reviewed: `load_history` in `gex/validation.py`, its 7-test suite, and the updated `streamlit_app.py`. The new `load_history` function is clean and the tests cover all happy paths. Two issues surface in `streamlit_app.py`: a password bypass when the `PASSWORD` secret is not configured, and a reversed x-axis on the ZGL trend chart. The bare-except in `load_history` silently discards all errors, which will make parquet corruption or permission failures invisible.

---

## Critical Issues

### CR-01: Empty-string password bypass

**File:** `streamlit_app.py:51`

**Issue:** `st.secrets.get("PASSWORD", "")` defaults to `""` when the secret is absent. If `PASSWORD` is not set in `.streamlit/secrets.toml` (e.g., a fresh deployment or local dev run), then `pwd == ""` evaluates `True` immediately — any user who clicks Submit with an empty field is authenticated.

**Fix:** Reject empty-string passwords before the equality check, and fail closed rather than open when the secret is missing:

```python
def _check_password() -> bool:
    if st.session_state.get("authenticated"):
        return True
    st.markdown("## GEX Dashboard")
    pwd = st.text_input("Password", type="password", placeholder="Enter password")
    expected = st.secrets.get("PASSWORD", "")
    if not expected:
        st.error("PASSWORD secret not configured.")
        return False
    if pwd and pwd == expected:
        st.session_state.authenticated = True
        st.rerun()
    elif pwd:
        st.error("Incorrect password")
    return False
```

---

## Warnings

### WR-01: ZGL trend chart x-axis is reversed (newest-to-oldest)

**File:** `streamlit_app.py:292-295`

**Issue:** `hist30` is returned by `load_history` sorted descending (index 0 = most recent). Plotting `hist30["date"]` directly on the x-axis puts the newest date on the left and the oldest on the right — the line appears to run backwards in time.

**Fix:** Sort ascending for display only:

```python
chart_df = hist30.sort_values("date")
ax.plot(chart_df["date"], chart_df["zero_gamma_level"], label="Zero-γ", linewidth=1.5)
ax.plot(chart_df["date"], chart_df["spot"], label="Spot", linewidth=1.2, linestyle="--")
```

### WR-02: `load_history` bare except swallows all errors silently

**File:** `gex/validation.py:77-83`

**Issue:** `except Exception: return pd.DataFrame()` discards parquet corruption, permission errors, and schema mismatches without any diagnostic output. Callers (including the Streamlit app) receive an empty DataFrame and display "No history available" — the actual failure is invisible.

**Fix:** At minimum, log before returning:

```python
except Exception as exc:
    print(f"[gex] load_history({ticker!r}) failed: {exc}")
    return pd.DataFrame()
```

Or re-raise if the caller can handle it. The `load_yesterday` function has the same pattern at line 70 — same fix applies there if desired.

---

## Info

### IN-01: Two separate cache entries for the same ticker's history

**File:** `streamlit_app.py:282-283`

**Issue:** The Historical tab calls `_load_history_cached(ticker, days=30)` and `_load_history_cached(ticker, days=20)` in a loop. These are separate cache keys, so each reads the parquet file independently. Since `days=30` is a superset, the 20-row view could be derived from the 30-row result without a second cache entry or parquet read.

**Fix:** Call once and slice:

```python
hist30 = _load_history_cached(ticker, days=30)
hist20 = hist30.head(20) if len(hist30) >= 20 else hist30
```

### IN-02: No test for corrupted parquet or `days=0`

**File:** `gex/tests/test_validation_history.py`

**Issue:** The bare-except path in `load_history` (WR-02 above) is never exercised by the test suite. A test confirming graceful degradation on a bad file would close that gap. Additionally, `days=0` is legal Python but returns an empty DataFrame — not obviously intentional.

**Fix (optional):** Add a test that writes a non-parquet file at the store path and confirms `load_history` returns an empty DataFrame. Add a test for `days=0` if the intent is to guard against caller mistakes.

---

_Reviewed: 2026-05-06_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
