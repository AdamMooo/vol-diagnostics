---
phase: 01-poc-delivery
reviewed: 2026-05-04T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - run.py
  - dashboard.py
  - build_report.py
  - WALKTHROUGH.md
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-05-04
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Four files reviewed: the two entry points (`run.py`, `build_report.py`), the dashboard module (`dashboard.py`), and the handoff document (`WALKTHROUGH.md`). The orchestration and statistical logic are sound. Two bugs found — both silent (no crash, wrong output):

1. Section D forward-realized signals always display `nan` due to a MultiIndex key mismatch.
2. `_add_regime_shading` in `build_report.py` will either raise `ValueError: The truth value of a Series is ambiguous` at the `high_frag.iloc[-1]` check, or silently shade incorrect periods, depending on whether the code path reaches the trailing-period branch.

The WALKTHROUGH.md is clean — accurate, well-scoped, no factual inconsistencies with the code.

---

## Warnings

### WR-01: Section D forward-realized signals always return NaN

**File:** `dashboard.py:224`

**Issue:** `pd.concat(sigs.pct, axis=1)` where `sigs.pct` is a `dict[str, DataFrame]` produces a MultiIndex column DataFrame with levels `(signal_name, underlying)`. Calling `.to_dict()` on a row of this DataFrame yields keys that are tuples, e.g. `('vrp', 'SPX')`. The downstream lookup `sig_dict.get('vrp', np.nan)` never matches a tuple key, so it always returns `np.nan`. Every forward-realized environment row in Section D will read `vrp=nan, skew=nan, term=nan, dd=nan` regardless of actual values.

**Fix:** Either flatten to a single underlying per call, or use a column-level lookup:

```python
# Option A — if single underlying context is available, pass u explicitly
# and slice before concat:
all_sigs = pd.concat(
    {sig: panel[u] for sig, panel in sigs.pct.items()}, axis=1
)
# Now columns are signal names (str), .to_dict() yields {'vrp': 0.62, ...}

# Option B — keep MultiIndex but extract by level when printing:
# sig_dict.get(('vrp', u), np.nan)
```

Option A is cleaner. The function would need `u` passed as a parameter, or the concat done per-underlying inside the caller loop in `section_d_analog`.

---

### WR-02: `_add_regime_shading` crashes or shades incorrectly with multi-column DataFrame

**File:** `build_report.py:87-101`

**Issue:** `sigs.pct["fragility"]` is a DataFrame (one column per underlying, e.g. `['SPX', 'NDX']`). The function treats it as a Series throughout:

- Line 87: `high_frag = fragility_ts >= fragility_threshold` — returns a boolean DataFrame, not a Series.
- Line 89: `transitions = high_frag != high_frag.shift()` — DataFrame comparison, result is a DataFrame.
- Line 90: `frag_periods = fragility_ts[transitions].index` — boolean DataFrame indexing on a DataFrame produces element-wise NaN where False, not a filtered index. This likely returns the full index or raises depending on pandas version.
- Line 98: `high_frag.iloc[-1]` — returns a Series (last row across all columns). The `if` check raises `ValueError: The truth value of a Series is ambiguous` when more than one underlying exists.

**Fix:** Collapse to a single Series before processing. The most natural choice is to use the mean across underlyings (or the first column if there is only one):

```python
fragility_ts = sigs.pct.get("fragility")
if fragility_ts is None:
    return
# Collapse DataFrame → Series (mean across underlyings)
if isinstance(fragility_ts, pd.DataFrame):
    fragility_ts = fragility_ts.mean(axis=1)

high_frag = fragility_ts >= fragility_threshold
transitions = high_frag != high_frag.shift()
frag_periods = high_frag[transitions].index  # also: use high_frag not fragility_ts here
# ... rest of function unchanged
```

Note also line 90 uses `fragility_ts[transitions]` but should use `high_frag[transitions]` — the intent is to get index positions where state changes, not raw fragility values.

---

## Info

### IN-01: Mutable default argument in `_forward_realized_environment`

**File:** `dashboard.py:211`

**Issue:** `horizons: list[int] = [21, 63, 126]` uses a mutable list as a default argument. The list is never mutated inside the function so there is no actual bug, but it is a Python anti-pattern that can cause subtle defects if the function is ever modified to append/extend.

**Fix:**
```python
def _forward_realized_environment(close_dt, sigs, horizons=(21, 63, 126)):
```
Use a tuple for immutable default, or `None` with internal assignment.

---

### IN-02: WALKTHROUGH.md references Section F implicitly missing

**File:** `WALKTHROUGH.md` (table at line 17) and `build_report.py:181-192`

**Issue:** The section table in WALKTHROUGH.md lists A, B, C, D, E, G, H — Section F is absent with no explanation. The HTML report follows the same A/B/C/D/E then G/H ordering (Section E ends at line 179, Section G begins at 186). A reader will notice the gap. Either a section was removed without updating the table, or F was deliberately skipped and this should be noted explicitly (e.g. "Section F reserved / not in POC").

**Fix:** Add a row to the table:

```markdown
| F — (reserved) | Not included in POC scope |
```

Or add a parenthetical in the intro: "Sections A–E, G–H (F not in scope for this POC)."

---

_Reviewed: 2026-05-04_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
