---
phase: 04-historical-tab
plan: "01"
status: complete
completed: 2026-05-06
commit: e3b6623
---

# Plan 04-01 Summary — load_history() + pytest suite

## What Was Built

Added `load_history(ticker, days=30)` to `gex/validation.py` immediately after `load_yesterday()`. Function reads the parquet store, filters by ticker, sorts descending by date, and returns the N most-recent rows. Returns `pd.DataFrame()` (never None, never raises) on missing store, missing ticker, or any exception. Implementation follows the `load_yesterday` pattern exactly as specified.

Created `gex/tests/test_validation_history.py` with 7 hermetic pytest tests using `tmp_path` + `monkeypatch.setattr` to redirect `STORE`. All 7 pass.

## Key Files

- `gex/validation.py` — `load_history` added after line 71, before `_classify_vs_yesterday`
- `gex/tests/test_validation_history.py` — 7 tests, all green

## Test Results

```
7 passed in 1.01s (gex/tests/test_validation_history.py)
75 passed, 2 failed (full suite — 2 failures are pre-existing secrets.toml issue, no regression)
```

## Deviations

One test (`test_load_history_default_days_is_30`) used `datetime.date(2025, 1, i+1)` for 35 rows — invalid since January has 31 days. Fixed to use `base + timedelta(days=i)` so dates span Jan–Feb 2025. Logic of the test is unchanged.

## Self-Check: PASSED

- [x] `load_history` present in `gex/validation.py` after `load_yesterday`, before `_classify_vs_yesterday`
- [x] Returns `pd.DataFrame()` always, never raises
- [x] `sort_values("date", ascending=False)` then `head(days)` then `reset_index(drop=True)`
- [x] 7 tests in `test_validation_history.py`, all pass
- [x] No existing functions modified
- [x] `python -m pytest gex/tests/ -q` — 75 passed (2 pre-existing failures unrelated to this plan)
