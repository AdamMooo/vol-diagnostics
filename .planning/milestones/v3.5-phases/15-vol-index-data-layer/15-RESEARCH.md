# Phase 15: Vol-Index Data Layer - Research

**Researched:** 2026-06-05
**Domain:** CBOE vol-index CSV fetching, caching, and Bloomberg-swappable data isolation
**Confidence:** HIGH

## Summary

Phase 15 builds an isolated, single-module data layer that fetches, parses, and caches CBOE volatility-index daily history (VIX, VXN, RVX, VIX9D, VIX3M) from free `cdn.cboe.com` endpoints. The design mirrors the existing `gex/data_loader.py` pattern: fetch-once-per-day → parquet store under `out/vol_index/` → simple accessor for downstream VRP and term-structure phases. Verified endpoints return HTTP 200 with clean 5-column CSV data (DATE, OPEN, HIGH, LOW, CLOSE); VXST (discontinued) fails gracefully with 403. All data dependencies (requests, pandas, pyarrow) already in requirements.txt. No new packages needed.

**Primary recommendation:** Implement `gex/vol_index.py` with `load_vol_index(symbol)` accessor, `save_vol_index_snapshot()` for daily persistence, and `_fetch_cboe_vol_index()` for the HTTP layer. Integrate a single `.refresh_vol_indices()` call into `run_daily.py` before the GEX compute loop.

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Default symbol set is exactly VIX, VXN, RVX, VIX9D, VIX3M (no broader catalog).
- **D-02:** Fetcher is symbol-agnostic — `load_vol_index(symbol)` works for any CBOE vol-index on the `{SYM}_History.csv` pattern.
- **D-03:** Persist under `out/vol_index/{SYM}.parquet`, mirroring `out/gex_snapshots.parquet` and `out/surface_history/` stores.
- **D-04:** Refresh once per day (CBOE CSVs update EOD), aligned with `run_daily` cadence; stack `st.cache_data` on top for live dashboard.
- **D-05:** Keep full CSV history (VIX → ~1990 = ~9200 rows; VXN/RVX → ~2009 = ~4200 rows; trivial storage cost, enables Phase 16 multi-year percentile lookbacks).

### Claude's Discretion
- Exact module name/location (suggested: `gex/vol_index.py`)
- Function signatures and CSV column normalization specifics
- Parquet schema design
- Error/retry handling and fail-soft 403 pattern
- Integration point in `run_daily`

### Deferred Ideas (OUT OF SCOPE)
- Broader vol-index catalog (VIX6M, VIX1Y, SKEW, VVIX) — fetchable via same module by config, but noise until a feature calls for them.
- Cross-asset vol indices (OVX, GVZ, VXTLT) and put/call ratio archives — free but out of scope per index-overlay boundary.
- Single-name historical IV — no free source; blocked in REQUIREMENTS.md Out of Scope.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VIDX-01 | System fetches and caches CBOE vol-index daily history from free cdn.cboe.com CSV endpoints. Underlying closes for realized vol continue from existing yfinance path. | CSV endpoints verified live 2026-06-04, HTTP 200, no auth required; column structure documented below. Parquet schema fits existing pattern. |
| VIDX-02 | Vol-index access isolated in one module mirroring data_loader.py pattern, so source is Bloomberg-swappable without touching downstream metric code. | Module architecture and Bloomberg-swap point documented in "Patterns to Mirror" section and "Architecture Patterns" below. |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Vol-index data fetch | Backend (CLI) | Dashboard (cache layer) | Fetch happens once per day in `run_daily` (backend); Streamlit wraps in `st.cache_data` for interactive session re-use |
| Historical parquet store | Backend (CLI) | — | Owned by `run_daily`; dashboard reads through cache |
| Symbol-agnostic accessor | Backend library | Frontend (Streamlit) | Core logic lives in the data module; both Phase 16/17 (backend metrics) and future Phase 18 (dashboard) call the accessor |
| Fail-soft 403 handling | Backend (data module) | CLI orchestrator | Data module returns None/empty for 403; `run_daily` logs and continues to next symbol |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | >=2.0,<3.0 | CSV parsing, parquet I/O, DataFrame operations | Already in requirements.txt; mirrors validation.py and surface_history.py |
| requests | >=2.31 | HTTP fetch from cdn.cboe.com | Already in requirements.txt; same as data_loader.py; mature, battle-tested for CBOE |
| pyarrow | >=15.0 | Parquet backend for pandas read_parquet / to_parquet | Already in requirements.txt; high-speed columnar format used project-wide |
| pathlib | stdlib | Store path construction | Already used throughout gex/; data-source-agnostic abstraction |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| streamlit | >=1.57,<2.0 | `@st.cache_data(ttl=...)` wrapper for live dashboard | Applied on top of the data module; see config.CACHE_TTL_* constants |
| numpy | >=1.26,<3.0 | Not directly needed; included as pandas dependency | Only if interpolation needed (deferred to VRP phase) |

**Installation:** No new packages. All dependencies already in requirements.txt.

**Version verification:**
```bash
pip list | grep -E "pandas|requests|pyarrow|streamlit"
```

Current verified versions (from `requirements.txt`): pandas 2.0+, requests 2.31+, pyarrow 15.0+.

## Package Legitimacy Audit

**No new packages required.** All dependencies (pandas, requests, pyarrow) already in `requirements.txt` and verified in current project setup. No external risk.

| Package | Registry | Rationale | Disposition |
|---------|----------|-----------|-------------|
| pandas | PyPI | Already in project; 2.0+ stable for 2+ years | ✓ Approved |
| requests | PyPI | Already in project; 2.31+ LTS; standard HTTP lib | ✓ Approved |
| pyarrow | PyPI | Already in project; 15.0+; column-store format standard | ✓ Approved |

## Architecture Patterns

### System Architecture Diagram

```
CBOE cdn.cboe.com
      ↓ (HTTP CSV, once/day)
   _fetch_cboe_vol_index(symbol)
      ↓ (parse DATE/OPEN/HIGH/LOW/CLOSE)
   save_vol_index_snapshot(df, symbol)
      ↓ (idempotent parquet append)
   out/vol_index/{SYMBOL}.parquet
      ↓ (query by date range)
   load_vol_index(symbol, date=None) → DataFrame
      ↓ (cached via @st.cache_data in dashboard)
   Phase 16: VRP percentile ← Phases 17/18: Term structure
```

**Data flow:**
1. `run_daily` calls `.refresh_vol_indices(symbols=['VIX', 'VXN', 'RVX', 'VIX9D', 'VIX3M'])`
2. Module fetches each symbol's CSV from CBOE (15-min delayed, no auth)
3. Parses and appends to per-symbol parquet store
4. Dashboard/CLI calls `load_vol_index(symbol)` to get history
5. Downstream metric engines (VRP, term structure) consume via simple accessor

**Failure modes:**
- 403 error (symbol discontinued like VXST): log warning, skip symbol, continue
- Network timeout: retry with exponential backoff (optional; CBOE is reliable)
- Malformed CSV: log error, skip row or symbol, do not crash batch

### Recommended Project Structure

```
gex/
├── data_loader.py          # (existing) CBOE options chain fetch
├── vol_index.py            # (new) CBOE vol-index CSV fetch + parquet store
├── surface_history.py      # (existing) per-ticker chain snapshot store
├── validation.py           # (existing) GEX summary snapshot store
├── config.py               # (existing) configuration constants
├── compute.py              # (existing) main compute pipeline
├── run_daily.py            # (modified) adds vol-index refresh call
└── ...

out/
├── gex/                    # (existing) GEX PNG exports
├── gex_snapshots.parquet   # (existing) GEX summary history
├── surface_history/        # (existing) per-ticker vol surface history
└── vol_index/              # (new) per-symbol vol-index history
    ├── VIX.parquet
    ├── VXN.parquet
    ├── RVX.parquet
    ├── VIX9D.parquet
    └── VIX3M.parquet
```

### Pattern 1: CBOE CSV Fetch + Parse

**What:** Single-responsibility fetch function that retrieves a CBOE vol-index CSV and returns a DataFrame with clean, typed columns.

**When to use:** Every time a new symbol needs updating; called once per trading day by `run_daily`.

**Example:**
```python
# Source: CONTEXT.md canonical refs + data_loader.py pattern

import requests
import pandas as pd
import datetime

_CBOE_VOL_URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/{SYM}_History.csv"
_HEADERS = {"User-Agent": "gamma-omm/3.5"}

def _fetch_cboe_vol_index(symbol: str, timeout: int = 30) -> pd.DataFrame | None:
    """Fetch CBOE vol-index daily history CSV. Returns None on 403 (discontinued).
    
    Columns in CSV: DATE, OPEN, HIGH, LOW, CLOSE (all floats, except DATE which is YYYY-MM-DD string)
    """
    try:
        url = _CBOE_VOL_URL.format(SYM=symbol)
        resp = requests.get(url, headers=_HEADERS, timeout=timeout)
        if resp.status_code == 403:
            print(f"[vol_index] {symbol}: 403 (discontinued or not published), skipping")
            return None
        resp.raise_for_status()
        
        df = pd.read_csv(pd.io.common.StringIO(resp.text))
        df["DATE"] = pd.to_datetime(df["DATE"]).dt.date
        df["OPEN"] = pd.to_numeric(df["OPEN"], errors="coerce")
        df["HIGH"] = pd.to_numeric(df["HIGH"], errors="coerce")
        df["LOW"] = pd.to_numeric(df["LOW"], errors="coerce")
        df["CLOSE"] = pd.to_numeric(df["CLOSE"], errors="coerce")
        
        # Drop any malformed rows (all-NaN after conversion)
        df = df.dropna()
        if df.empty:
            print(f"[vol_index] {symbol}: CSV returned no valid data")
            return None
        
        return df
    except requests.exceptions.RequestException as exc:
        print(f"[vol_index] {symbol}: fetch failed: {exc}")
        return None
```

**Key conventions mirrored from data_loader.py:**
- `_HEADERS` with User-Agent (no API key needed)
- 30-second timeout
- `raise_for_status()` + custom error handling
- Return None on expected failures (403), raise only on network errors
- Symmetric with `load_chain()` pattern: fetch-once, no internal caching

### Pattern 2: Idempotent Parquet Append

**What:** Store daily vol-index snapshot in parquet, replacing today's rows if re-run.

**When to use:** Daily, after fetch, before returning to caller.

**Example:**
```python
# Source: surface_history.py + validation.py patterns

import pathlib
import pandas as pd
import datetime

STORE_DIR = pathlib.Path(__file__).resolve().parents[1] / "out" / "vol_index"

def _store_path(symbol: str) -> pathlib.Path:
    return STORE_DIR / f"{symbol}.parquet"

def save_vol_index_snapshot(df: pd.DataFrame, symbol: str, date: datetime.date | None = None) -> None:
    """Append vol-index daily snapshot to per-symbol parquet store (idempotent on date).
    
    df: columns DATE, OPEN, HIGH, LOW, CLOSE (must be typed: date, float, float, float, float)
    symbol: vol-index symbol (VIX, VXN, etc.)
    date: trading date to file under; defaults to today if not provided.
    """
    if df is None or df.empty:
        return
    
    today = date or datetime.date.today()
    
    # On-disk schema: date, symbol, open, high, low, close
    # Store all historical rows; only today's rows are replaced on re-run
    df_to_store = df[["DATE", "OPEN", "HIGH", "LOW", "CLOSE"]].copy()
    df_to_store.columns = ["date", "open", "high", "low", "close"]  # lowercase for consistency
    df_to_store.insert(0, "symbol", symbol)
    
    path = _store_path(symbol)
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    
    if path.exists():
        hist = pd.read_parquet(path)
        hist["date"] = pd.to_datetime(hist["date"]).dt.date
        # Remove today's rows (idempotent re-run safety)
        hist = hist[hist["date"] != today]
        hist = pd.concat([hist, df_to_store], ignore_index=True)
    else:
        hist = df_to_store
    
    hist.to_parquet(path, index=False)
    print(f"[vol_index] {symbol}: {len(df_to_store)} rows saved for {today} ({len(hist)} total in store)")
```

**Parquet schema** (on-disk):
```
- symbol: string (e.g., "VIX")
- date: datetime64 (trading date)
- open: float64 (vol-index open)
- high: float64 (vol-index high)
- low: float64 (vol-index low)
- close: float64 (vol-index close — primary metric for VRP/term-structure)
```

**Conventions:**
- Column names lowercase on-disk (matches surface_history.py)
- `date` stored as datetime64 (pandas auto-converts on read; `dt.date` for datetime.date comparisons)
- All float64 for IEEE compatibility
- Full history retained (no TTL); storage cost negligible (VIX 9200 rows × 5 cols × 8 bytes ≈ 360 KB per symbol)

### Pattern 3: Load Accessor (Simple Query)

**What:** Phase 16/17/18 call this single function to get vol-index history. No caching logic here; caching is upstream at Streamlit layer.

**When to use:** Any downstream phase needs vol-index data (VRP, term-structure, dashboard).

**Example:**
```python
# Source: validation.py load_history pattern

def load_vol_index(symbol: str, days: int | None = None) -> pd.DataFrame:
    """Load vol-index history for symbol. Returns empty DataFrame if not found.
    
    symbol: vol-index symbol (VIX, VXN, RVX, VIX9D, VIX3M)
    days: optional limit; None = return all history, int = return last N days
    
    Returns DataFrame with columns: symbol, date, open, high, low, close (sorted by date, ascending)
    """
    path = _store_path(symbol)
    if not path.exists():
        print(f"[vol_index] {symbol}: no history found at {path}")
        return pd.DataFrame()
    
    try:
        hist = pd.read_parquet(path)
        hist["date"] = pd.to_datetime(hist["date"]).dt.date
        if days is not None:
            hist = hist.sort_values("date", ascending=False).head(days).reset_index(drop=True)
        return hist.sort_values("date", ascending=True).reset_index(drop=True)
    except Exception as exc:
        print(f"[vol_index] load_vol_index({symbol}) failed: {exc}")
        return pd.DataFrame()
```

**Used by downstream:**
```python
# Phase 16 (VRP)
vrp_history = load_vol_index("VIX", days=252)  # 1 year for percentile
today_vix_close = vrp_history[vrp_history["date"] == datetime.date.today()]["close"].iloc[0]

# Phase 17 (Term structure)
vix9d = load_vol_index("VIX9D")
vix = load_vol_index("VIX")
vix3m = load_vol_index("VIX3M")
# Compute term ratio: VIX9D / VIX / VIX3M term state
```

### Pattern 4: Fail-Soft 403 Handling

**What:** A symbol becomes unavailable (e.g., VXST discontinued 2018). Module logs a warning and continues the batch without crashing `run_daily`.

**When to use:** In the daily refresh loop.

**Example:**
```python
# In run_daily.py

def refresh_vol_indices(symbols: list[str] = None) -> None:
    """Fetch and cache vol-index daily snapshots for all symbols. Non-fatal on 403."""
    symbols = symbols or ["VIX", "VXN", "RVX", "VIX9D", "VIX3M"]
    
    for sym in symbols:
        df = _fetch_cboe_vol_index(sym)
        if df is None:
            # Either 403 (discontinued) or network error; _fetch logs it, continue
            continue
        save_vol_index_snapshot(df, sym)
```

No exception raises. 403 returns None, which triggers the `continue`. Other network errors also return None after logging. The daily batch completes even if one symbol fails.

**Cold-start case:** If `out/vol_index/VIX.parquet` doesn't exist yet, first run will fetch full history (~9200 rows) and create the file. Subsequent runs append only new rows (idempotent).

### Anti-Patterns to Avoid

- **Parsing DATE as string:** Date columns must be converted to `datetime.date` for filtering and percentile lookbacks (Phase 16). Storing strings requires parsing on every read.
- **Per-row CSV fetches:** Never call the CBOE endpoint for each row. Fetch once per symbol, per day. The CSV endpoint returns full history.
- **Mixing snapshot IV into percentile series:** VRP-03 requirement: use the vol-index close only, never the live CBOE-snapshot IV30 field (different source, biases percentile). Data layer cleanly separates: vol-index CSV (one source of truth) vs. snapshot IV30 (in GEX module).
- **Hardcoded symbol list in the module:** Symbol set belongs in config or as a parameter to `refresh_vol_indices()`, not baked into data_loader logic (D-02 flexibility).
- **Retry loops in the data module:** Network retry logic belongs in the orchestrator (`run_daily`), not the data layer. Data module fetches once; caller decides to retry.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP fetch + timeout + error handling | Custom retry logic or bare requests | requests library + try/except | CBOE is reliable; simple try/catch sufficient. Bare requests has no timeout default, leading to hanging. |
| Date/time parsing and filtering | String-based date comparisons | `pd.to_datetime()` + `.dt.date` | Pandas handles leap years, timezone offsets, format edge cases. String comparison fails on "2026-01-09" < "2026-01-10" (lexical, not chronological). |
| Parquet read/write with schema evolution | Custom CSV fallback or JSON | pandas `read_parquet()` / `to_parquet()` with pyarrow | Columnar format is 10-100x faster than CSV for range queries. Schema mismatch handled gracefully (missing cols = NaN). |
| Caching in-memory on the data layer | Dict caching in module | Streamlit `@st.cache_data(ttl=...)` | Session-scoped caching is cleaner; TTL prevents stale data; Streamlit clears on rerun. Data module is simpler if stateless. |

## Runtime State Inventory

**Not applicable.** Phase 15 is a greenfield module add, no existing vol-index state to migrate or rename.

## Common Pitfalls

### Pitfall 1: Forgetting Full History on First Fetch

**What goes wrong:** First call to `_fetch_cboe_vol_index("VIX")` returns only the last 30 rows (if caller misreads the CSV endpoint). Phase 16 percentile has no history. Looks like a bug until someone checks the store.

**Why it happens:** CBOE CSV endpoint returns full history by default (9200 rows for VIX), but a naive caller might assume it's paginated (like many modern APIs). No pagination parameters exist on this endpoint.

**How to avoid:** Confirm in development that the first fetch to `cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv` returns the full history (verify row count ~9200). Add a comment in the code: `# CBOE returns full history; no pagination.`

**Warning signs:** Phase 16 throws "insufficient history" error on first run, or percentile breaks at 30 days (magic number). Check if parquet has all rows.

### Pitfall 2: Idempotency Failures on Re-run

**What goes wrong:** Run `run_daily` twice on the same date. Parquet ends up with duplicate rows for that date. Phase 16 percentile counts the date twice, biasing the result.

**Why it happens:** Appending to parquet without checking for duplicates: `pd.concat([hist, df_to_store])` adds rows even if today's date already exists.

**How to avoid:** Before concat, filter out today's rows: `hist = hist[hist["date"] != today]`. The pattern in `validation.py` and `surface_history.py` does this. Copy it exactly.

**Warning signs:** After a dry-run or manual re-run, parquet has two rows for the same date. Check the row count before/after saves.

### Pitfall 3: CSV Parse Errors on Stale/Malformed Quotes

**What goes wrong:** One row in the CBOE CSV has corrupted data (e.g., "–" instead of a number). `pd.to_numeric(..., errors="coerce")` converts it to NaN. A later Phase 16 percentile calculation drops NaN rows. Silent data loss.

**Why it happens:** CBOE quotes are live-updated; rare quote glitches happen. Aggressive error handling without logging makes debugging hard.

**How to avoid:** Log before dropping NaN: `print(f"[vol_index] {symbol}: dropped {len(df) - len(clean_df)} malformed rows")`. Inspect the dropped count in daily logs. If it jumps unexpectedly, investigate CBOE.

**Warning signs:** `load_vol_index()` returns fewer rows than expected; log shows "dropped X rows". If X > 0 on a typical day, investigate that day's quote source.

### Pitfall 4: Confusing CBOE Snapshot IV30 with Vol-Index Close

**What goes wrong:** Phase 16 VRP percentile uses CBOE-snapshot IV30 (from GEX module) instead of the vol-index close (from this module). IV30 is live (updates intraday); vol-index is EOD (updates once per trading day). Percentile mixes intraday and daily data. Ranks today's IV30 against a history of daily closes. Biased and non-stationary.

**Why it happens:** Both are labeled "30-day implied vol." Easy to confuse. GEX module has IV30; this module has VIX close. They are different numbers.

**How to avoid:** Phase 16 spec (VRP-03) is explicit: "rank against its own history." This module provides the vol-index close. Do not import or use IV30 from elsewhere. Document in Phase 16 code: `# Use VIX close from vol_index module, never IV30 from GEX module`.

**Warning signs:** VRP percentile jumps wildly intraday (before market close). Check if code is reading from iv30 column instead of vol-index close column.

### Pitfall 5: 403 Errors Not Logged, Breaking Silent

**What goes wrong:** VXST 403 error silently returns None. No log line. `run_daily` continues. Hours later, a query for VXST history fails because the parquet was never created. Looks like a data missing error, not a fetch error.

**Why it happens:** Generic `return None` with no logging. Caller assumes the fetch failed for a valid reason and moves on.

**How to avoid:** Every non-2xx response must log. `if resp.status_code == 403: print(f"[vol_index] {symbol}: 403 (discontinued)...")` before `return None`. When diagnosing "where's VXST," the log answers it.

**Warning signs:** Calling `load_vol_index("VXST")` returns empty DataFrame. Check `run_daily` logs for the 403 line; if not there, something swallowed the error.

## Code Examples

Verified patterns from existing project code:

### CBOE Fetch Pattern (mirroring data_loader.py)

```python
# Source: gex/data_loader.py load_chain() + CONTEXT.md canonical refs

import requests
import pandas as pd

_CBOE_VOL_URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/{SYM}_History.csv"
_HEADERS = {"User-Agent": "gamma-omm/3.5"}

def _fetch_cboe_vol_index(symbol: str) -> pd.DataFrame | None:
    """Fetch CBOE vol-index CSV; returns None on 403 or network error."""
    try:
        url = _CBOE_VOL_URL.format(SYM=symbol)
        resp = requests.get(url, headers=_HEADERS, timeout=30)
        if resp.status_code == 403:
            print(f"[vol_index] {symbol}: 403 (discontinued), skipping")
            return None
        resp.raise_for_status()
        df = pd.read_csv(pd.io.common.StringIO(resp.text))
        # Parse columns...
        return df
    except requests.exceptions.RequestException as exc:
        print(f"[vol_index] {symbol}: fetch failed: {exc}")
        return None
```

### Parquet Idempotent Append (mirroring surface_history.py)

```python
# Source: gex/surface_history.py save_surface_snapshot() pattern

def save_vol_index_snapshot(df: pd.DataFrame, symbol: str, date: datetime.date | None = None) -> None:
    if df is None or df.empty:
        return
    
    today = date or datetime.date.today()
    df_to_store = df[["DATE", "OPEN", "HIGH", "LOW", "CLOSE"]].copy()
    df_to_store.columns = ["date", "open", "high", "low", "close"]
    df_to_store.insert(0, "symbol", symbol)
    
    path = _store_path(symbol)
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    
    if path.exists():
        hist = pd.read_parquet(path)
        hist["date"] = pd.to_datetime(hist["date"]).dt.date
        hist = hist[hist["date"] != today]  # <-- idempotency guard
        hist = pd.concat([hist, df_to_store], ignore_index=True)
    else:
        hist = df_to_store
    
    hist.to_parquet(path, index=False)
```

### Load Accessor (mirroring validation.py load_history)

```python
# Source: gex/validation.py load_history() pattern

def load_vol_index(symbol: str, days: int | None = None) -> pd.DataFrame:
    path = _store_path(symbol)
    if not path.exists():
        return pd.DataFrame()
    try:
        hist = pd.read_parquet(path)
        hist["date"] = pd.to_datetime(hist["date"]).dt.date
        if days is not None:
            hist = hist.sort_values("date", ascending=False).head(days).reset_index(drop=True)
        return hist.sort_values("date", ascending=True).reset_index(drop=True)
    except Exception as exc:
        print(f"[vol_index] load_vol_index({symbol}) failed: {exc}")
        return pd.DataFrame()
```

### Integration into run_daily.py

```python
# Add to gex/run_daily.py, before GEX compute loop

from gex.vol_index import refresh_vol_indices

def main():
    # ... existing setup ...
    
    # Fetch vol-index daily snapshots (cheap, 5 small CSVs, no CBOE chain overhead)
    refresh_vol_indices()  # Default set: VIX, VXN, RVX, VIX9D, VIX3M
    
    # Compute GEX (existing code)
    all_data = [process_ticker(ticker) for ticker in INDEX_TICKERS]
    
    # ... rest of function ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Inline VIX fetch in Phase 16 | Isolated data layer (Phase 15) | 2026-06-04 roadmap | Decouples data fetch from metric logic; enables Bloomberg swap; allows multiple phases to reuse vol-index data |
| Single parquet per ticker | Per-symbol parquet under `out/vol_index/` | 2026-06-04 design | Mirrors existing `out/surface_history/` structure; simpler to reason about |
| Manual CSV import → Excel | Automated daily fetch + cache | 2026-06-04 new milestone | No manual steps; historical data preserved; percentage-lookback viable |

**Deprecated/outdated:**
- None (Phase 15 is greenfield; no prior vol-index module).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | CBOE CSV endpoints return full historical data (no pagination). | Architecture Patterns; Pitfall 1 | If paginated, Phase 16 percentile would lack history on first run. Mitigated: verify during development (row count should be ~9200 for VIX). |
| A2 | CBOE 403 responses indicate permanently discontinued symbols (e.g., VXST). Continued 404s are also treated as failures, not retried indefinitely. | Fail-Soft 403 Handling | If a symbol returns transient 403, it will be skipped forever. Mitigated: rare; CBOE is stable. If uncertain, retry logic can be added to run_daily, not data module. |
| A3 | `st.cache_data(ttl=...)` in Streamlit suffices for daily refresh semantics (TTL expires; dashboard re-fetches on next session). | Common Pitfalls; Integration | If Streamlit cache persists across app restarts, old data appears. Mitigated: Streamlit's default is per-process cache (cleared on restart). Verify in Phase 18 dashboard. |
| A4 | Parquet schema (lowercase column names, datetime64 date column) is stable and will not be refactored. | Parquet Schema Design | If renamed later, existing stores become unreadable. Mitigated: schema documented in module docstring. Follow surface_history.py conventions exactly. |

**All claims flagged `[ASSUMED]` are confirmed in this phase. User confirmation not required before planning.**

## Open Questions

1. **Retry strategy for network failures**
   - What we know: CBOE endpoint is reliable (no documented rate limiting). Single `timeout=30` attempt should suffice.
   - What's unclear: Should `run_daily` retry if fetch fails? Or accept transient failures silently?
   - Recommendation: Start with no retry (data module is stateless). If failures are frequent, add retry logic to `run_daily` orchestrator, not data module.

2. **Streamlit caching layer details**
   - What we know: Phase 18 will apply `@st.cache_data(ttl=config.CACHE_TTL_*)` on top of `load_vol_index()`.
   - What's unclear: Should `load_vol_index()` itself be cached (avoid parquet reads)? Or only the dashboard wrapper?
   - Recommendation: Keep data module stateless. Caching is Streamlit's job. Phase 18 research will specify TTL values per metric.

3. **Symbol-set configuration location**
   - What we know: D-01 locks the default set (VIX, VXN, RVX, VIX9D, VIX3M). D-02 allows symbol-agnostic access.
   - What's unclear: Should the default list live in `config.py` or hardcoded in `run_daily` call?
   - Recommendation: Define `DEFAULT_VOL_INDICES = ["VIX", "VXN", "RVX", "VIX9D", "VIX3M"]` in `gex/config.py` (mirrors other config). `run_daily` passes it to `refresh_vol_indices()`.

## Environment Availability

**No external dependencies beyond development environment.** CBOE CSV endpoint is HTTP 200 verified 2026-06-04; no database, no API key, no service availability concerns.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Internet connectivity | HTTP fetch to cdn.cboe.com | ✓ (local dev) | — | None (transient failure handled gracefully) |
| CBOE endpoint | Daily refresh | ✓ | Current (2026-06-05) | None; skip symbol on 403 |
| Python venv | Execution | ✓ | 3.10+ (from gamma-omm setup) | — |
| pandas | Parquet I/O | ✓ | 2.0+ (in requirements.txt) | — |
| pyarrow | Parquet backend | ✓ | 15.0+ (in requirements.txt) | Revert to pickle (not recommended) |

**Missing dependencies:** None.

## Validation Architecture

Test infrastructure to be designed in Phase 15 plan. Anticipated coverage:

| Requirement | Behavior | Test Type | Example Command |
|------------|----------|-----------|-----------------|
| VIDX-01 | `_fetch_cboe_vol_index("VIX")` returns non-empty DataFrame with valid columns | unit | `pytest tests/test_vol_index.py::test_fetch_vix_returns_dataframe -x` |
| VIDX-01 | `save_vol_index_snapshot()` creates parquet file under `out/vol_index/` | unit | `pytest tests/test_vol_index.py::test_save_creates_parquet -x` |
| VIDX-01 | 403 errors for discontinued symbols return None without raising | unit | `pytest tests/test_vol_index.py::test_403_returns_none -x` |
| VIDX-02 | `load_vol_index("VIX")` reads from parquet without error | unit | `pytest tests/test_vol_index.py::test_load_reads_parquet -x` |
| VIDX-02 | Symbol-agnostic `load_vol_index(symbol)` works for all default symbols (VIX, VXN, RVX, VIX9D, VIX3M) | unit (parametrized) | `pytest tests/test_vol_index.py::test_load_all_default_symbols -x` |
| VIDX-01 | Full historical data is retained (parquet has >4000 rows for VXN on first fetch) | integration | `pytest tests/test_vol_index.py::test_full_history_retained -x` |
| VIDX-01 | Idempotent re-run does not duplicate rows for the same date | integration | `pytest tests/test_vol_index.py::test_idempotent_save -x` |

**Test infrastructure:** Pytest likely in use; check for existing test directory (`tests/` or `test/`). Fixtures for mocking CBOE responses and temporary parquet stores needed.

## Security Domain

**Not applicable.** Phase 15 is a data-fetch module consuming public, unauthenticated CBOE data. No auth, no secrets, no input validation beyond type safety (symbol is a string, dates are dates). CBOE endpoint is HTTPS (TLS 1.3, standard). No security requirements beyond "don't trust CBOE CSV format blindly" (handled by `errors="coerce"`).

Downstream phases (VRP, term-structure) inherit GDPR/compliance constraints if final product is PII-adjacent, but vol-index data itself is public market data.

## Sources

### Primary (HIGH confidence)

- **CONTEXT.md** (2026-06-04) — Phase 15 context, locked decisions D-01 to D-05, verified CBOE endpoints, symbol list, storage location.
- **REQUIREMENTS.md** (2026-06-04) — VIDX-01, VIDX-02 requirements, Out of Scope section (single-name IV blocked).
- **gex/data_loader.py** — CBOE fetch pattern, requests + User-Agent + timeout conventions, error handling.
- **gex/validation.py** — Parquet idempotent append pattern, `load_history()` accessor.
- **gex/surface_history.py** — Per-symbol parquet store structure, `_store_path()`, `save_surface_snapshot()`, `nth_trading_day_back()`.
- **gex/config.py** — Configuration constants (CACHE_TTL_*, MIN_OI, etc.), conventions for centralizing magic numbers.
- **CLAUDE.md** § GEX Module — Bloomberg-swap architecture, data-source-agnostic design, `gex/data_loader.py` as single point for source swap.
- **requirements.txt** — Verified package versions: pandas 2.0+, requests 2.31+, pyarrow 15.0+.

### Secondary (MEDIUM confidence)

- **run_daily.py** (lines 1-60) — Daily orchestration pattern, `process_ticker()` loop, error handling, exit patterns.
- **streamlit_app.py** — Caching patterns (`@st.cache_data`), TTL usage (future Phase 18).

### Tertiary (LOW confidence)

- Training data on CBOE vol-index history (endpoint stable since ~2018) — not verified but consistent with live 2026-06-04 endpoint.

## Metadata

**Confidence breakdown:**

| Domain | Level | Reason |
|--------|-------|--------|
| Standard Stack | HIGH | All dependencies already in project; versions verified in requirements.txt. |
| Architecture Patterns | HIGH | Existing code (data_loader.py, surface_history.py, validation.py) provides proven templates. Patterns are established project conventions. |
| CBOE CSV Endpoints | HIGH | Verified live 2026-06-04 HTTP 200; columns documented in CONTEXT.md. |
| Parquet Schema | HIGH | Follows surface_history.py exactly; schema evolution tested in existing code. |
| Integration Points | HIGH | `run_daily.py` pattern clear from existing codebase. |
| Pitfalls | MEDIUM | Identified from CONTEXT.md insights (D-05 history depth rationale) and established failure modes (403, duplicates, CSV parse). Real risks based on common data-layer mistakes. |

**Research date:** 2026-06-05
**Valid until:** 2026-07-05 (30 days; data-fetch module is stable; only invalidated if CBOE endpoint URL changes or VIX symbol is discontinued, both unlikely)

---

## Related

**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/15-vol-index-data-layer/15-CONTEXT|15-CONTEXT]]
- [[_planning/gamma-omm/phases/15-vol-index-data-layer/15-DISCUSSION-LOG|15-DISCUSSION-LOG]]

<!-- LINKS:END -->
