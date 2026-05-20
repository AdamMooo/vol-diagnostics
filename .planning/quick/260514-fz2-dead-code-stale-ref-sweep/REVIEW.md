---
phase: recent-changes
reviewed: 2025-05-26T00:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - gex/analytics.py
  - gex/compute.py
  - gex/config.py
  - gex/data_loader.py
  - gex/exposure_engine.py
  - gex/run_gex.py
  - gex/validation.py
  - streamlit_app.py
  - gex/report.py
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Code Review — Dead Code & Stale Reference Sweep

**Reviewed:** 2025-05-26  
**Depth:** standard  
**Files Reviewed:** 9  
**Status:** issues_found

> **Note on test files:** The five test files listed in the review scope (`gex/tests/__init__.py`, `test_analytics_summarise.py`, `test_exposure_engine.py`, `test_exposure_flow.py`, `test_greeks_engine.py`, `test_streamlit_app.py`) do not exist at `gex/tests/`. They are physically located at `gex/__pycache__/tests/` — see WR-02 below.

## Summary

Nine source files reviewed at standard depth. No critical security vulnerabilities found. The most impactful finding is a silent zero-spot propagation in `data_loader.py` that causes a `ZeroDivisionError` in `compute.py` if CBOE ever returns a null `current_price`. A structural issue with test files landing in `__pycache__/tests/` rather than `gex/tests/` means the test suite is not discoverable by pytest. Three minor code-quality items complete the findings.

---

## Warnings

### WR-01: Silent zero spot propagates to ZeroDivisionError

**File:** `gex/data_loader.py:75` + `gex/compute.py:60`

**Issue:** `load_chain()` coerces a missing or null `current_price` to `0.0` with no guard:

```python
spot = float(data.get("current_price") or 0.0)
```

This zero is carried into `ChainSnapshot.spot` and used without validation downstream. In `compute.py:60`:

```python
delta_hedge_flow = net_gex_scalar / (snapshot.spot ** 2 * 0.01)
```

When `spot == 0.0`, this raises `ZeroDivisionError`. Secondary effects: `gamma_profile()` sweeps a grid of zeros, and `vol_surface_data()` produces an empty DataFrame since `lo = hi = 0`. The Streamlit caller wraps `fetch_ticker` in a `try/except`, so the error surfaces as a user-visible error banner — but `run_gex.py` has no such guard and would crash with a traceback.

**Fix:**

In `data_loader.py`, raise immediately rather than silently defaulting:

```python
spot = float(data.get("current_price") or 0.0)
if spot <= 0:
    raise ValueError(
        f"CBOE returned invalid spot price for {ticker}: {data.get('current_price')!r}"
    )
```

Alternatively, guard in `compute.py` before the division:

```python
if snapshot.spot <= 0:
    raise ValueError(f"Invalid spot price {snapshot.spot} for {ticker}")
delta_hedge_flow = net_gex_scalar / (snapshot.spot ** 2 * 0.01)
```

---

### WR-02: Test files are in `gex/__pycache__/tests/` — not pytest-discoverable

**File:** `gex/__pycache__/tests/` (all five test modules)

**Issue:** All test files reside inside `__pycache__`, which Python reserves for compiled bytecode (`.pyc` files). A standard pytest invocation — `pytest`, `pytest gex/tests/`, or `pytest --rootdir=.` — will not find them because:

1. `gex/tests/` as a directory does not exist at the project root.
2. pytest skips `__pycache__` by default (`norecursedirs` includes `__pycache__`).

The tests can only run if explicitly pointed at the wrong path (`pytest gex/__pycache__/tests/`). Any CI pipeline using a normal invocation runs zero tests while reporting success.

**Fix:** Move the test files to the canonical location:

```
gex/tests/__init__.py
gex/tests/test_analytics_summarise.py
gex/tests/test_exposure_engine.py
gex/tests/test_exposure_flow.py
gex/tests/test_greeks_engine.py
gex/tests/test_streamlit_app.py
```

```powershell
New-Item -ItemType Directory gex\tests
Move-Item gex\__pycache__\tests\*.py gex\tests\
```

Verify with `pytest gex/tests/ -v` afterward.

---

### WR-03: `if pct_chg:` silently drops observation on unchanged days

**File:** `streamlit_app.py:103`

**Issue:** The observation block uses a truthiness check:

```python
pct_chg = summary.get("price_change_pct")
if pct_chg:
    obs.append(f"{pct_chg:+.2f}% today")
```

`price_change_pct` is always set as a `float` (defaulting to `0.0` in `data_loader.py:77`). When the underlying closes unchanged — `pct_chg == 0.0` — the check `if 0.0:` is `False`, so the observation is silently omitted rather than showing `+0.00% today`. The same pattern appears in `_derive_observations()` for `zgl` (line 93) and `cw`/`pw` (line 99), though those are less likely to be exactly zero in practice.

**Fix:**

```python
# Before
if pct_chg:
    obs.append(f"{pct_chg:+.2f}% today")

# After
if pct_chg is not None:
    obs.append(f"{pct_chg:+.2f}% today")
```

---

## Info

### IN-01: `expiry_gex()` is dead code — never imported or called

**File:** `gex/exposure_engine.py:47–55`

**Issue:** `expiry_gex()` is defined in `exposure_engine.py` but is not imported by any module in the project (`compute.py`, `run_gex.py`, `validation.py`, `streamlit_app.py` — none import it). It is not tested. It produces a GEX aggregation by expiry that was presumably useful during earlier development but has no current caller.

**Fix:** Remove the function, or if it is planned for future use, add a `# noqa: F401` comment and document the planned caller so it doesn't confuse future readers.

```python
# Remove lines 47-55 in exposure_engine.py:
def expiry_gex(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate GEX by expiry."""
    ...
```

---

### IN-02: `run_gex.py` assembles the pipeline manually, bypasses live risk-free rate

**File:** `gex/run_gex.py:36–41`

**Issue:** `run_gex.py` directly chains `add_greeks → compute_gex → strike_gex → gamma_profile` rather than delegating to `compute_ticker()` from `gex.compute`. As a result:

- `gamma_profile()` is called without fetching a live risk-free rate via `_get_risk_free_rate()` — it always uses `config.RISK_FREE_FALLBACK = 0.05`.
- The vol surface, skew, and surface slope metrics are not computed, meaning the printed summary may diverge from what the dashboard shows for the same session.

Since `compute.py` is documented as "single source of truth for both run_daily and streamlit_app," `run_gex.py` is the only caller that drifts. If `compute_ticker()` gains further logic, the CLI output will silently lag.

**Fix:** Either refactor `run_gex.run()` to call `compute_ticker()` and format its output, or add a comment acknowledging the deliberate divergence:

```python
# NOTE: run_gex.py is a lightweight POC/CLI entry point. It intentionally
# bypasses compute_ticker() (which fetches live ^IRX and computes vol surface).
# γ-flip sweep uses config.RISK_FREE_FALLBACK.
```

---

### IN-03: `REGIME_COLOR` missing `"zero"` key — fallback is load-bearing but implicit

**File:** `streamlit_app.py:131` + `gex/report.py:16–19`

**Issue:** `streamlit_app.py` imports `REGIME_COLOR` from `gex.report` and calls:

```python
color = REGIME_COLOR.get(sign, "#999")
```

where `sign` can be `"positive"`, `"negative"`, or `"zero"`. `REGIME_COLOR` only defines two keys:

```python
REGIME_COLOR = {
    "positive": "#16a34a",
    "negative": "#dc2626",
}
```

The `"zero"` sign relies entirely on the `.get()` fallback returning `"#999"`. This is not a crash but the `"zero"` visual state is implicitly defined by the absence of a dict entry. If the fallback is ever removed or the code path is copied without the default argument, the accent bar colour silently becomes `None`.

**Fix:** Add the zero state explicitly to `REGIME_COLOR` in `report.py`:

```python
REGIME_COLOR = {
    "positive": "#16a34a",
    "negative": "#dc2626",
    "zero":     "#64748b",   # slate-500, consistent with analytics._sign_color()
}
```

Then in `streamlit_app.py` change to a direct lookup:

```python
color = REGIME_COLOR[sign]
```

---

_Reviewed: 2025-05-26_  
_Reviewer: Claude (gsd-code-reviewer)_  
_Depth: standard_
