---
phase: 13-1-day-iv-email-pngs
reviewed: 2026-06-01T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - gex/run_daily.py
  - gex/tests/test_run_daily_pngs.py
  - gex/tests/test_streamlit_app.py
findings:
  critical: 1
  warning: 2
  info: 1
  total: 4
status: issues_found
---

# Phase 13: Code Review Report

**Reviewed:** 2026-06-01
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Three files reviewed: the daily orchestrator with the new PNG-attachment block, its behavioral test suite, and the Streamlit app test suite. The core orchestration logic is clean — error isolation is consistent, the non-blocking pattern is applied correctly, and the email guard (`--send` / `GEX_SEND`) works. The test coverage for the PNG block is thorough with good edge-case coverage.

Two defects surfaced: one is a structural coupling in production code that creates a silent data-corruption path; the other is a fragile test that breaks based on process working directory.

---

## Critical Issues

### CR-01: `_build_png_attachments` indexes `all_data` by position, not by ticker — silent wrong-data risk

**File:** `gex/run_daily.py:60-68`

**Issue:** `_build_png_attachments` iterates `INDEX_TICKERS` with `enumerate` and uses `ticker_idx` as a positional index into `all_data` (which is built by iterating `ALL_TICKERS` in `run()`). Today `ALL_TICKERS = INDEX_TICKERS` (the same list object), so the indices align. But the coupling is implicit and fragile:

1. Any future insertion of a non-INDEX ticker at the front of `ALL_TICKERS` (e.g., `ALL_TICKERS = ["ES=F"] + INDEX_TICKERS`) silently maps `ticker_idx=0` (SPY) to `all_data[0]` which now holds "ES=F" data. `plot_iv_change_surface` would be called with the wrong `today_surface_df` and `today_spot`, producing a corrupted ΔIV chart with no error.

2. Even today, if `process_ticker` is ever called in a different order than `INDEX_TICKERS`, the same silent mismatch occurs.

The inner `try/except` at line 83 catches `IndexError` (out-of-bounds) and logs a warning, but an in-bounds wrong-index lookup produces no exception — just silently wrong chart data in the email.

**Fix:** Look up data by ticker key, not positional index. Either build `all_data` as a dict keyed by ticker:

```python
# In run(): change all_data to a dict
all_data: dict[str, dict] = {}
for ticker in ALL_TICKERS:
    data = process_ticker(ticker)
    all_data[ticker] = data
    ...

# In _build_png_attachments: change signature and lookup
def _build_png_attachments(
    all_data: dict[str, dict],   # keyed by ticker
    today: datetime.date,
    out_dir: pathlib.Path,
) -> list:
    ...
    for ticker in INDEX_TICKERS:
        data = all_data.get(ticker)
        if data is None:
            continue
        ...
```

Or, at minimum, add a guard inside `_build_png_attachments`:

```python
data = all_data[ticker_idx]
if data["summary"].get("ticker") != ticker:
    print(f"  [WARN] index mismatch: expected {ticker}, got {data['summary'].get('ticker')}")
    continue
```

---

## Warnings

### WR-01: `test_evolution_store_untouched` uses a hardcoded relative path — fails outside repo root

**File:** `gex/tests/test_run_daily_pngs.py:185`

**Issue:** `pathlib.Path("gex/run_daily.py").read_text(encoding="utf-8")` resolves against the process working directory. Pytest run from the repo root works; pytest run from any other directory (e.g., `cd gex/tests && pytest`, a CI runner that changes dirs, or a subprocess invocation) raises `FileNotFoundError` with no useful message. The test errors rather than failing, which masks what it was testing.

**Fix:** Use `__file__` to anchor the path:

```python
src = (pathlib.Path(__file__).resolve().parents[2] / "run_daily.py").read_text(encoding="utf-8")
```

`__file__` is `gex/tests/test_run_daily_pngs.py`, so `.parents[2]` is the repo root, and `/ "run_daily.py"` would be wrong — correct is `.parents[1] / "run_daily.py"`:

```python
src = (pathlib.Path(__file__).resolve().parent.parent / "run_daily.py").read_text(encoding="utf-8")
# i.e. gex/tests/ -> parent = gex/ -> parent = repo-root/ -> run_daily.py
# Actually: __file__ = gex/tests/test_run_daily_pngs.py
#           .parent   = gex/tests/
#           .parent   = gex/
#           / "run_daily.py" -> gex/run_daily.py  ✓
src = (pathlib.Path(__file__).resolve().parent.parent / "run_daily.py").read_text(encoding="utf-8")
```

### WR-02: `png_note` condition does not distinguish kaleido failure from all-tickers-errored state

**File:** `gex/run_daily.py:140-141`

**Issue:** The note is set when `not attachments and any(d.get("surface_df") is not None for d in all_data)`. This correctly fires when at least one ticker had a surface but produced no PNG. However, `all_data` contains the raw dicts including error-path dicts (which have no `surface_df` key, so `.get()` returns `None`). The condition works correctly today.

The latent issue is subtler: if one ticker succeeds (has `surface_df`) but its PNG fails due to kaleido, and another ticker fails at compute time (no `surface_df`), the note still fires — which is the correct behavior. But the message says "kaleido not installed or PNG export failed" even when the cause might be `plot_iv_change_surface` itself throwing (caught silently in the inner try). The note is accurate enough, but if kaleido is installed and the failure is in `plot_iv_change_surface`, the message misleads.

**Fix:** Track failure reason in `_build_png_attachments` by returning a named tuple or a dict with `attachments` and `failure_reason`. This is low-priority — the current message is acceptable for a monitoring email. Flag for future improvement if debugging is needed.

---

## Info

### IN-01: Deferred `import os` inside `__main__` block is non-standard

**File:** `gex/run_daily.py:192`

**Issue:** `import os as _os` appears inside the `if __name__ == "__main__":` block rather than at the top of the file with other imports. The `_os` alias suggests it was intentionally scoped to avoid polluting the module namespace, but `os` is a stdlib module with no side effects and the alias adds visual noise.

**Fix:** Move `import os` to the top of the file with other stdlib imports and reference `os.getenv(...)` directly:

```python
# at top of file
import os
...
# in __main__ block
authorized = args.send or os.getenv("GEX_SEND") == "1"
```

---

_Reviewed: 2026-06-01_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/13-1-day-iv-email-pngs/13-01-PLAN|13-01-PLAN]]
- [[_planning/gamma-omm/phases/13-1-day-iv-email-pngs/13-01-SUMMARY|13-01-SUMMARY]]

<!-- LINKS:END -->
