---
phase: 01-poc-delivery
fixed_at: 2026-05-04T00:00:00Z
review_path: .planning/phases/01-poc-delivery/01-REVIEW.md
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 01: Code Review Fix Report

**Fixed at:** 2026-05-04
**Source review:** .planning/phases/01-poc-delivery/01-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 2 (WR-01, WR-02; CR-* none; IN-* excluded by fix_scope)
- Fixed: 2
- Skipped: 0

## Fixed Issues

### WR-01: Section D forward-realized signals always return NaN

**Files modified:** `dashboard.py`
**Commit:** 8ab2047
**Applied fix:** Added `u: str` parameter to `_forward_realized_environment`. Replaced `pd.concat(sigs.pct, axis=1)` (which produced MultiIndex columns `(signal, underlying)`) with `pd.concat({sig: panel[u] for sig, panel in sigs.pct.items()}, axis=1)`, so columns are plain signal name strings. Updated the single call site in `section_d_analog` (line 284) to pass `u` — already available from the enclosing `for u in bt.rolls:` loop.

### WR-02: `_add_regime_shading` crashes or shades incorrectly with multi-column DataFrame

**Files modified:** `build_report.py`
**Commit:** 49037c8
**Applied fix:** After the `None` guard, added `if isinstance(fragility_ts, pd.DataFrame): fragility_ts = fragility_ts.mean(axis=1)` to collapse the per-underlying DataFrame to a single Series. Also corrected line 93: changed `fragility_ts[transitions].index` to `high_frag[transitions].index` (boolean index over the boolean Series, not the raw float Series) to correctly extract transition timestamps.

---

_Fixed: 2026-05-04_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
