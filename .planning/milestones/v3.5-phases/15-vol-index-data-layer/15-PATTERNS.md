# Phase 15: Vol-Index Data Layer - Pattern Map

**Mapped:** 2026-06-05
**Files analyzed:** 3 (new + modified)
**Analogs found:** 3 / 3

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `gex/vol_index.py` | service (data module) | CRUD (fetch → store → load) | `gex/data_loader.py` + `gex/surface_history.py` | exact |
| `gex/run_daily.py` | orchestrator (CLI) | request-response (batch scheduler) | `gex/run_daily.py` (existing lines 1-100) | role-match |
| `gex/config.py` | config | configuration constants | `gex/config.py` (existing lines 1-184) | role-match |

## Pattern Assignments

### `gex/vol_index.py` (service, CRUD fetch→store→load)

**Primary Analog:** `gex/data_loader.py` (fetch pattern) + `gex/surface_history.py` (store pattern)

#### Imports Pattern (data_loader.py lines 14-26)

```python
from __future__ import annotations

import datetime
from dataclasses import dataclass

import pandas as pd
import requests

from gex import config
```

**Rationale:** Mirror the project's imports: `__future__` annotations for type-hint forward-compatibility, stdlib modules first, pandas + requests for HTTP + data handling, local `config` import for magic numbers.

#### CBOE Fetch Pattern (data_loader.py lines 24-120)

```python
_CBOE_URL = "https://cdn.cboe.com/api/global/delayed_quotes/options/{ticker}.json"
_HEADERS = {"User-Agent": "options-quant/1.0"}

def load_chain(ticker: str = "SPY", ...) -> ChainSnapshot:
    """Fetch from CBOE and return standardized dataclass."""
    url = _CBOE_URL.format(ticker=ticker)
    resp = requests.get(url, headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    # ... parse payload, return typed result
```

**Apply to vol_index.py:** Use the same pattern but for CSV endpoint:
- `_CBOE_VOL_URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/{SYM}_History.csv"`
- Same `_HEADERS` user-agent convention
- Same 30-second timeout
- `resp.raise_for_status()` for error handling
- **Special case:** Return `None` on 403 (discontinued symbol) with logging, don't raise
- Parse DataFrame columns and return typed result

**Key excerpt:** `requests.get(url, headers=_HEADERS, timeout=30)` + custom error handling for 403.

#### Parquet Store Pattern (surface_history.py lines 22-65)

```python
STORE_DIR = pathlib.Path(__file__).resolve().parents[1] / "out" / "surface_history"

def _store_path(ticker: str) -> pathlib.Path:
    return STORE_DIR / f"surface_{ticker}.parquet"

def save_surface_snapshot(
    surface_df: pd.DataFrame,
    ticker: str,
    spot: float,
    date: datetime.date | None = None,
) -> None:
    """Append today's OTM chain points to the per-ticker parquet store."""
    if surface_df is None or surface_df.empty:
        return
    
    today = date if date is not None else datetime.date.today()
    df = surface_df[["dte", "strike", "moneyness", "log_moneyness", "iv_pct"]].copy()
    df.insert(0, "date", today)
    df.insert(1, "ticker", ticker)
    
    path = _store_path(ticker)
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    
    if path.exists():
        hist = pd.read_parquet(path)
        hist["date"] = pd.to_datetime(hist["date"]).dt.date
        hist = hist[hist["date"] != today]  # <-- idempotency guard
        hist = pd.concat([hist, df], ignore_index=True)
    else:
        hist = df
    
    hist.to_parquet(path, index=False)
    print(f"[surface_history] {ticker}: {len(df)} rows saved for {today} "
          f"({len(hist)} total rows in store)")
```

**Apply to vol_index.py:** Directly copy this pattern:
- `STORE_DIR = pathlib.Path(__file__).resolve().parents[1] / "out" / "vol_index"`
- `_store_path(symbol)` helper returning per-symbol parquet path
- **Idempotency guard:** `hist = hist[hist["date"] != today]` before concat (critical for dry-runs)
- Lowercase column names on-disk (date, symbol, open, high, low, close)
- Print summary line with row counts and total store size
- Explicit date handling: optional `date` parameter defaults to `datetime.date.today()`

**Key excerpt:** The idempotency pattern (lines 54-58) is load-bearing — copy exactly.

```python
if path.exists():
    hist = pd.read_parquet(path)
    hist["date"] = pd.to_datetime(hist["date"]).dt.date
    hist = hist[hist["date"] != today]
    hist = pd.concat([hist, df], ignore_index=True)
else:
    hist = df

hist.to_parquet(path, index=False)
```

#### Load Accessor Pattern (validation.py lines 118-129)

```python
def load_history(ticker: str, days: int = 30) -> pd.DataFrame:
    if not STORE.exists():
        return pd.DataFrame()
    try:
        hist = pd.read_parquet(STORE)
        hist["date"] = pd.to_datetime(hist["date"]).dt.date
        hist = hist[hist["ticker"] == ticker].sort_values("date", ascending=False)
        return hist.head(days).reset_index(drop=True)
    except Exception as exc:
        print(f"[validation] load_history failed: {exc}")
        return pd.DataFrame()
```

**Apply to vol_index.py:** Create `load_vol_index(symbol, days=None)`:
- Check path exists; return empty DataFrame if not (no exceptions to caller)
- Read parquet, convert date column to `datetime.date` for filtering
- Optional `days` parameter: if provided, return last N days (most-recent first, then sort ascending)
- Catch all exceptions, log, return empty DataFrame (fail-soft accessor)
- Always sort by date ascending (oldest first) before returning to caller

**Key excerpt:** Fail-soft error handling and sort order (ascending for consistency with historical data consumers).

---

### `gex/run_daily.py` (orchestrator, request-response batch)

**Analog:** `gex/run_daily.py` (existing lines 1-100)

#### Integration Point (run_daily.py lines 1-35)

```python
from __future__ import annotations

import argparse
import datetime
import pathlib

import pandas_market_calendars as mcal
import pytz

from gex.compute import compute_ticker
from gex.validation import save_snapshot
from gex.surface_history import save_surface_snapshot, nth_trading_day_back, load_surface_snapshot
from gex import report as rpt
from gex import emailer
from gex import observation
from gex.png_export import export_png
from gex.analytics import plot_iv_change_heatmap
from gex.surface_evolution import load_evolution
from gex.vol_metrics import evolution_5d_summary

INDEX_TICKERS = ["SPY", "QQQ", "IWM"]
ALL_TICKERS = INDEX_TICKERS
```

**Apply to run_daily.py modifications:**
- Add import: `from gex.vol_index import refresh_vol_indices`
- Add to the import block (after line 22, before INDEX_TICKERS definition)
- Call `refresh_vol_indices()` early in `run()` function, before GEX compute loop (see example below)

#### Orchestration Pattern (run_daily.py lines 94-100)

```python
def run(dry_run: bool = False) -> None:
    today = datetime.datetime.now(ET).date()

    if not is_trading_day(today):
        print(f"[gex-daily] {today} is not a NYSE trading day — skipping.")
        return
    
    # ... existing setup code ...
```

**Apply to run_daily.py modifications:**
- After the trading-day check (after line 99), call:
  ```python
  # Fetch vol-index daily snapshots (cheap, 5 small CSVs, no CBOE chain overhead)
  refresh_vol_indices()  # Default set: VIX, VXN, RVX, VIX9D, VIX3M
  ```
- Place this before the GEX compute loop (`all_data = [process_ticker(ticker) for ticker in INDEX_TICKERS]`)
- No error handling needed; `refresh_vol_indices()` is fail-soft (logs 403s, continues on network errors)

---

### `gex/config.py` (configuration, constants)

**Analog:** `gex/config.py` (existing lines 150-184)

#### Config Pattern (config.py lines 150-184)

```python
# ── Streamlit caching ──────────────────────────────────────────────────────────

CACHE_TTL_TICKER: int = 300
"""Seconds to cache compute_ticker() results in the Streamlit app. 5 minutes
roughly matches the CBOE delayed-quote refresh rhythm — quotes won't change
meaningfully inside this window."""

CACHE_TTL_HISTORY: int = 1800
"""Seconds to cache parquet history reads. 30 minutes is fine — history is
append-only and only changes once a day when run_daily fires."""

HISTORY_DAYS: int = 30
"""Rolling lookback (days) for the History tab charts (γ-flip vs spot, skew).
Long enough to see regime shifts; short enough to fit in one screen."""
```

**Apply to config.py additions:**
- Add a new section after line 184:
  ```python
  # ── Vol-index data layer (Phase 15) ──────────────────────────────────────────

  DEFAULT_VOL_INDICES: list[str] = ["VIX", "VXN", "RVX", "VIX9D", "VIX3M"]
  """Default set of CBOE vol-index symbols fetched daily by run_daily.refresh_vol_indices().
  Symbol-agnostic fetcher allows Phase 17 (term structure) to probe sibling symbols.
  See CONTEXT.md D-01."""

  CACHE_TTL_VOL_INDEX: int = 3600
  """Seconds to cache load_vol_index() results in the Streamlit dashboard.
  1 hour is fine — vol-index history is append-only and updates once per trading day.
  Mirrors CACHE_TTL_HISTORY for consistency."""
  ```
- Follow the docstring style: constant name, type, default value on first line; rationale in docstring.
- Reference decision IDs (D-01) and phase context for clarity.

---

## Shared Patterns

### Error Handling — Fail-Soft 403 (applies to vol_index.py)

**Source:** `gex/data_loader.py` (implicit) + `gex/surface_history.py` (lines 86-87 exception handling)

**Apply to:** `_fetch_cboe_vol_index()` in vol_index.py

```python
def _fetch_cboe_vol_index(symbol: str, timeout: int = 30) -> pd.DataFrame | None:
    """Fetch CBOE vol-index daily history CSV. Returns None on 403 (discontinued)."""
    try:
        url = _CBOE_VOL_URL.format(SYM=symbol)
        resp = requests.get(url, headers=_HEADERS, timeout=timeout)
        if resp.status_code == 403:
            print(f"[vol_index] {symbol}: 403 (discontinued or not published), skipping")
            return None
        resp.raise_for_status()
        # ... parse CSV ...
        return df
    except requests.exceptions.RequestException as exc:
        print(f"[vol_index] {symbol}: fetch failed: {exc}")
        return None
```

**Key convention:** Always log before returning None (idempotent diagnostic; when diagnosing "where's VXST," logs answer it). Never raise on expected failures (403); only raise_for_status() for other HTTP errors, which then get caught and logged.

### Path Construction — Pathlib Pattern (applies to vol_index.py)

**Source:** `gex/validation.py` line 28 + `gex/surface_history.py` lines 22-26

**Apply to:** `STORE_DIR` and `_store_path()` in vol_index.py

```python
STORE_DIR = pathlib.Path(__file__).resolve().parents[1] / "out" / "vol_index"

def _store_path(symbol: str) -> pathlib.Path:
    return STORE_DIR / f"{symbol}.parquet"
```

**Key convention:** Use `pathlib.Path(__file__).resolve().parents[1]` (project root), not relative paths. This works across Windows/POSIX and doesn't break on `cd` changes.

### Logging Convention — Module Prefix (applies to vol_index.py)

**Source:** `gex/data_loader.py` (implicit "options-quant" style) + `gex/surface_history.py` line 63

**Apply to:** All print statements in vol_index.py

```python
# Good:
print(f"[vol_index] {symbol}: 403 (discontinued), skipping")
print(f"[vol_index] {symbol}: {len(df_to_store)} rows saved for {today} ({len(hist)} total in store)")

# Not:
print(f"Fetched {symbol}...")  # Missing module prefix
```

**Key convention:** Always prefix with `[module_name]` for grep-ability and audit trails. Makes it easy to filter logs by data layer vs. compute vs. report.

---

## No Analog Found

None. All three files have direct analogs in the existing codebase.

---

## Metadata

**Analog search scope:** 
- `gex/*.py` (21 files examined)
- `.planning/` (context + research reviewed)

**Pattern extraction method:**
- Fetch pattern: `gex/data_loader.py` (requests + timeout + 403 handling + type return)
- Store pattern: `gex/surface_history.py` (idempotent parquet append + path construction)
- Load pattern: `gex/validation.py` (fail-soft accessor + exception handling)
- Config pattern: `gex/config.py` (constant definition style + docstring format)
- Orchestration: `gex/run_daily.py` (import style + function integration point)

**Files scanned:** 21 Python modules in gex/ directory; 3 chosen as primary analogs based on role match (data module, orchestrator, config).

**Pattern extraction date:** 2026-06-05

---

## Key Takeaways for Planner

1. **vol_index.py is a composite pattern:** Fetch logic mirrors `data_loader.py` (requests + timeout + custom error handling); store/load logic mirrors `surface_history.py` + `validation.py` (idempotent parquet + fail-soft accessor).

2. **run_daily.py modification is minimal:** Single import line + single function call in the main `run()` orchestrator before the GEX compute loop. Pattern already established by existing `save_surface_snapshot()` calls in that module.

3. **config.py addition is straightforward:** Add two constants (DEFAULT_VOL_INDICES list + CACHE_TTL_VOL_INDEX integer) in the existing Streamlit caching section, following the docstring format.

4. **Idempotency is load-bearing:** The `hist = hist[hist["date"] != today]` guard in the parquet save must be copied exactly. This prevents duplicate rows on dry-runs or manual re-runs.

5. **Fail-soft 403 handling is non-negotiable:** Symbol may be discontinued (VXST example in RESEARCH.md). Always log before returning None. No exceptions to caller.

6. **All dependencies already in requirements.txt:** pandas, requests, pyarrow, pathlib (stdlib). No new packages needed.


---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/15-vol-index-data-layer/15-CONTEXT|15-CONTEXT]]
- [[_planning/gamma-omm/phases/15-vol-index-data-layer/15-DISCUSSION-LOG|15-DISCUSSION-LOG]]
- [[_planning/gamma-omm/phases/15-vol-index-data-layer/15-RESEARCH|15-RESEARCH]]

<!-- LINKS:END -->
