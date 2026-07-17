---
phase: 15-vol-index-data-layer
reviewed: 2026-06-05T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - gex/vol_index.py
  - gex/config.py
  - gex/run_daily.py
  - gex/tests/test_vol_index.py
findings:
  critical: 1
  warning: 3
  info: 2
  total: 6
status: issues_found
---

# Phase 15: Code Review Report

**Reviewed:** 2026-06-05
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

New `gex/vol_index.py` module adds fetch/parquet-store/load for CBOE vol indices, wired non-blocking into `run_daily.py`. The fetch and load paths are clean. One critical data-corruption bug exists in `save_vol_index_snapshot`: the deduplication logic is scoped only to `today` but the entire CBOE history CSV is concatenated on every call, causing unbounded row duplication for all non-today dates after the second daily run. Three warnings cover a silent empty-list footgun, an unused parameter that misleads callers, and a test gap that doesn't catch the critical bug. Two info items cover a redundant `list()` call and a `config.py` comment that leaks module-internal concerns.

## Critical Issues

### CR-01: `save_vol_index_snapshot` duplicates all historical rows on every call

**File:** `gex/vol_index.py:78-86`

**Issue:** CBOE returns the full daily history CSV (years of data). `_fetch_cboe_vol_index` returns all rows, `df_to_store` contains all of them. The dedup in `save_vol_index_snapshot` only removes `today`'s date from the existing parquet before concatenating `df_to_store`. On the first call the parquet is correct. On the second call (next trading day), `today` is a new date, so yesterday's rows survive in `hist`, and the entire CBOE history is appended again — doubling every historical row. After N daily runs the parquet has N copies of every row except the current day's. `load_vol_index` has no dedup, so downstream consumers silently receive duplicate rows.

The docstring says "idempotent on date" which is only true for the same `date` called twice in one session — not across days.

**Fix:** Either (a) deduplicate the full `df_to_store` against the existing parquet on `date`, or (b) since CBOE provides the complete history, simply overwrite unconditionally — no append logic needed:

```python
def save_vol_index_snapshot(
    df: pd.DataFrame | None,
    symbol: str,
    date: datetime.date | None = None,   # keep for API compat; unused after fix
) -> None:
    if df is None or df.empty:
        return

    df_to_store = df[["DATE", "OPEN", "HIGH", "LOW", "CLOSE"]].copy()
    df_to_store.columns = ["date", "open", "high", "low", "close"]
    df_to_store.insert(0, "symbol", symbol)

    STORE_DIR.mkdir(parents=True, exist_ok=True)
    path = _store_path(symbol)
    df_to_store.to_parquet(path, index=False)
    print(f"[vol_index] {symbol}: {len(df_to_store)} rows written (full replace)")
```

If true incremental-append semantics are ever needed (e.g., Bloomberg intrabar), switch to deduplicating on all dates, not just `today`:

```python
    if path.exists():
        hist = pd.read_parquet(path)
        hist["date"] = pd.to_datetime(hist["date"]).dt.date
        # remove ALL dates present in df_to_store, not just today
        incoming_dates = set(df_to_store["date"])
        hist = hist[~hist["date"].isin(incoming_dates)]
        hist = pd.concat([hist, df_to_store], ignore_index=True)
    else:
        hist = df_to_store
```

## Warnings

### WR-01: `refresh_vol_indices([])` silently falls back to defaults

**File:** `gex/vol_index.py:113`

**Issue:** `symbols = symbols or list(DEFAULT_VOL_INDICES)` treats an empty list `[]` as falsy and substitutes the full default list. A caller passing an explicitly empty list to suppress all fetching (e.g., a test or a dry-run guard) gets the opposite of what it asked for. This is a Python `or`-with-falsy gotcha.

**Fix:**
```python
symbols = DEFAULT_VOL_INDICES if symbols is None else symbols
```

### WR-02: `date` parameter of `save_vol_index_snapshot` is misleading

**File:** `gex/vol_index.py:63,69,81`

**Issue:** The `date` parameter is documented as the snapshot date for the idempotency guard. But after the CR-01 fix (full overwrite), this parameter has no effect on what gets stored — only on which row gets removed from the old parquet. Retaining it post-fix creates a misleading API: callers may assume passing `date=yesterday` re-runs yesterday's snapshot when it does nothing of the sort. Even pre-fix, passing `date=yesterday` only prevents removing yesterday's row; it does not filter `df_to_store` to yesterday's data.

**Fix:** After applying CR-01's full-overwrite fix, drop the `date` parameter entirely (it's only consumed internally). If the parameter must stay for caller compat, document clearly that it has no effect on stored data.

### WR-03: Test `test_idempotent_same_date` does not cover the cross-day duplication case

**File:** `gex/tests/test_vol_index.py:120-134`

**Issue:** The idempotency test saves a single-row DataFrame with `date=today` twice. This catches the same-day double-call case but not the across-days bug (CR-01): it never exercises a second call with a new `today` value and a multi-row `df`. The test passes while the critical bug exists undetected.

**Fix:** Add a test that calls `save_vol_index_snapshot` with a 3-row DataFrame on day 1, then again with the same 3-row DataFrame on day 2 (different `date`), and asserts the parquet has exactly 3 unique rows:

```python
def test_no_duplication_across_days(self, tmp_path):
    df = _make_fetch_df(nrows=3)
    store = tmp_path / "vol_index"
    with patch("gex.vol_index.STORE_DIR", store):
        save_vol_index_snapshot(df, "VIX", date=datetime.date(2026, 1, 6))
        save_vol_index_snapshot(df, "VIX", date=datetime.date(2026, 1, 7))

    stored = pd.read_parquet(store / "VIX.parquet")
    assert stored["date"].nunique() == 3  # fails today, proving CR-01
```

## Info

### IN-01: Redundant `list()` call on already-a-list constant

**File:** `gex/vol_index.py:113`

**Issue:** `DEFAULT_VOL_INDICES` is typed and initialized as `list[str]` in `config.py`. `list(DEFAULT_VOL_INDICES)` creates an unnecessary copy. After applying WR-01's fix this becomes `DEFAULT_VOL_INDICES if symbols is None else symbols` with no copy needed since `refresh_vol_indices` does not mutate the list.

**Fix:** `symbols = DEFAULT_VOL_INDICES if symbols is None else symbols`

### IN-02: `config.py` comment references internal module detail

**File:** `gex/config.py:187`

**Issue:** The inline comment on `DEFAULT_VOL_INDICES` says "Add symbols here — not in vol_index.py — per D-02." This is a valid convention note, but the "not in vol_index.py" wording leaks implementation guidance into a config constant that is also read by downstream phases. Convention enforcement belongs in a PLAN or PATTERNS doc, not in a constant's comment.

**Fix:** Trim to: `# CBOE vol-index symbols fetched by refresh_vol_indices(). D-02.`

---

_Reviewed: 2026-06-05_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/15-vol-index-data-layer/15-01-PLAN|15-01-PLAN]]
- [[_planning/gamma-omm/phases/15-vol-index-data-layer/15-01-SUMMARY|15-01-SUMMARY]]
- [[_planning/gamma-omm/phases/15-vol-index-data-layer/15-02-PLAN|15-02-PLAN]]
- [[_planning/gamma-omm/phases/15-vol-index-data-layer/15-02-SUMMARY|15-02-SUMMARY]]
- [[_planning/gamma-omm/phases/15-vol-index-data-layer/15-CONTEXT|15-CONTEXT]]
- [[_planning/gamma-omm/phases/15-vol-index-data-layer/15-DISCUSSION-LOG|15-DISCUSSION-LOG]]
- [[_planning/gamma-omm/phases/15-vol-index-data-layer/15-PATTERNS|15-PATTERNS]]
- [[_planning/gamma-omm/phases/15-vol-index-data-layer/15-RESEARCH|15-RESEARCH]]

<!-- LINKS:END -->
