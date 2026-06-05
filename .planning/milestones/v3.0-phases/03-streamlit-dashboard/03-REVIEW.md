---
phase: 03-streamlit-dashboard
reviewed: 2026-05-05T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - streamlit_app.py
  - requirements.txt
  - gex/tests/test_streamlit_app.py
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-05-05
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Three files reviewed: the Streamlit dashboard entry point, the requirements manifest, and the dashboard test module. No security vulnerabilities or data-loss bugs found. Three warnings cover a division-by-zero risk in delta-hedge-flow formatting, a silent swallow of all fetch exceptions that hides real errors, and a missing `matplotlib` backend guard in the test file. Three info items cover a stale `seaborn` dependency, a magic-number literal, and a minor test coverage gap.

## Warnings

### WR-01: ZeroDivisionError in `delta_hedge_flow` display when `spot` is 0

**File:** `streamlit_app.py:41`
**Issue:** `delta_hedge_flow = net_gex_scalar / (snapshot.spot * 0.01)` is computed unconditionally in `fetch_ticker`. If `yfinance` returns a spot of `0` or `None` (e.g., a data outage), this raises `ZeroDivisionError` inside the cached function. Because `@st.cache_data` caches exceptions in some Streamlit versions, a single bad fetch can permanently poison the cache for the TTL window.
**Fix:**
```python
delta_hedge_flow = (
    net_gex_scalar / (snapshot.spot * 0.01)
    if snapshot.spot and snapshot.spot != 0
    else None
)
```

### WR-02: Broad `except Exception` silently swallows structural errors

**File:** `streamlit_app.py:110-111`
**Issue:** `except Exception as exc: st.warning(f"{ticker} failed: {exc}")` catches everything, including `ImportError`, `AttributeError`, and `KeyError` from internal bugs in `greeks_engine` or `exposure_engine`. A developer introducing a regression in a downstream module will see only a dashboard warning, not a traceback, making the bug very hard to trace.
**Fix:** Narrow the catch to network/data retrieval errors, or at minimum re-raise non-recoverable types:
```python
except Exception as exc:
    import traceback
    st.warning(f"{ticker} failed: {exc}")
    st.expander("Traceback").code(traceback.format_exc())
```
In production the expander can be hidden behind an env flag, but it should exist during development.

### WR-03: `matplotlib` backend not set before import in test file

**File:** `gex/tests/test_streamlit_app.py:3`
**Issue:** The test file imports `matplotlib.pyplot` at module level without first calling `matplotlib.use("Agg")`. In CI or headless environments this can trigger a `_tkinter` error before any test runs. `streamlit_app.py` itself correctly sets the backend at lines 5-6, but that only applies when `streamlit_app` is imported — not when the test module is loaded standalone or when `test_plot_overview_renders` calls `plot_overview` directly without importing `streamlit_app` first.
**Fix:**
```python
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
```
Add these three lines at the top of `gex/tests/test_streamlit_app.py` replacing the current bare `import matplotlib.pyplot as plt`.

## Info

### IN-01: `seaborn` in `requirements.txt` is unused by the GEX module

**File:** `requirements.txt:6`
**Issue:** `seaborn>=0.13,<1.0` is listed but no file in the `gex/` package imports it. It is a transitive installation cost (~4 MB) with no current call site. If it belongs to the v2.1 sleeve code it should stay; if the GEX module is the only active concern, it can be dropped.
**Fix:** Confirm whether `seaborn` is used anywhere in the active codebase:
```
grep -r "import seaborn" .
```
Remove the line if no matches.

### IN-02: Magic number `1e9` repeated throughout `streamlit_app.py`

**File:** `streamlit_app.py:62-63, 157-159`
**Issue:** `/ 1e9` and `* 1e9` appear six times inline. A module-level constant clarifies intent and simplifies any future unit change.
**Fix:**
```python
_BILLION = 1e9
```
Then `net_gex_b = (summary.get("net_gex") or 0) / _BILLION`.

### IN-03: `test_plot_overview_renders` does not assert figure content

**File:** `gex/tests/test_streamlit_app.py:27-30`
**Issue:** The test asserts only `fig is not None`. An empty figure also satisfies this. Adding a check that axes contain at least one bar (i.e., the chart rendered data, not just a blank canvas) would catch regressions in `plot_overview`.
**Fix:**
```python
assert len(fig.axes) > 0
assert len(fig.axes[0].patches) > 0  # at least one bar rendered
```

---

_Reviewed: 2026-05-05_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/03-streamlit-dashboard/03-01-PLAN|03-01-PLAN]]
- [[_planning/gamma-omm/phases/03-streamlit-dashboard/03-01-SUMMARY|03-01-SUMMARY]]
- [[_planning/gamma-omm/phases/03-streamlit-dashboard/03-02-PLAN|03-02-PLAN]]
- [[_planning/gamma-omm/phases/03-streamlit-dashboard/03-02-SUMMARY|03-02-SUMMARY]]
- [[_planning/gamma-omm/phases/03-streamlit-dashboard/03-HUMAN-UAT|03-HUMAN-UAT]]
- [[_planning/gamma-omm/phases/03-streamlit-dashboard/03-PATTERNS|03-PATTERNS]]
- [[_planning/gamma-omm/phases/03-streamlit-dashboard/03-RESEARCH|03-RESEARCH]]
- [[_planning/gamma-omm/phases/03-streamlit-dashboard/03-VERIFICATION|03-VERIFICATION]]

<!-- LINKS:END -->
