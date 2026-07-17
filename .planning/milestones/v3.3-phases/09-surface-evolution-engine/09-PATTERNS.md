# Phase 9: Surface Evolution Engine - Pattern Map

**Mapped:** 2026-05-30
**Files analyzed:** 5 new/modified files
**Analogs found:** 5 / 5

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `gex/surface_evolution.py` | service | CRUD (parquet) + compute | `gex/validation.py` | exact |
| `gex/surface_history.py` (extend) | helper | request-response | `gex/surface_history.py` (existing) | exact |
| `gex/config.py` (modify) | config | constants | `gex/config.py` (existing) | exact |
| `gex/run_daily.py` (modify) | orchestrator | request-response | `gex/run_daily.py` (existing) | exact |
| `gex/tests/test_surface_evolution.py` | test | unit + integration | `gex/tests/test_rbf_grid.py`, `gex/tests/test_coverage_mask.py` | role-match |

---

## Pattern Assignments

### `gex/surface_evolution.py` (service, CRUD + compute)

**Analog:** `gex/validation.py`

**Responsibility:** Compute and persist evolution metrics (level, rms, skew_change, term_change) to an idempotent parquet store. Mirrors the snapshot validation store pattern exactly.

**Imports pattern** (`gex/validation.py:21-26`):
```python
from __future__ import annotations

import datetime
import pathlib

import pandas as pd
```

**Store path constant** (`gex/validation.py:28`):
```python
STORE = pathlib.Path(__file__).resolve().parents[1] / "out" / "gex_snapshots.parquet"
```
**For Phase 9, adapt to:**
```python
STORE = pathlib.Path(__file__).resolve().parents[1] / "out" / "surface_evolution.parquet"
```

**Float column list pattern** (`gex/validation.py:31-37`):
```python
_FLOAT_COLS = (
    "zero_gamma_level", "call_wall", "put_wall",
    "front_skew", "put_25d_iv", "call_25d_iv", "iv30",
    "strike_slope", "term_slope",
    "rv20", "vrp",
    "coverage_pct", "fit_rmse", "max_resid", "cv_rmse", "coherence_violations",
)
```
**For Phase 9, create:**
```python
_FLOAT_COLS = ("level", "rms", "skew_change", "term_change", "coverage")
```

**Idempotent save pattern** (`gex/validation.py:40-89`):
```python
def save_snapshot(summary: dict, ticker: str, skew_df: pd.DataFrame | None = None) -> None:
    """Append today's summary dict to the parquet store (idempotent on date+ticker)."""
    # ... row construction ...
    
    if STORE.exists():
        hist = pd.read_parquet(STORE)
        for col in _FLOAT_COLS:
            if col in hist.columns:
                hist[col] = hist[col].astype("float64")
        mask = (hist["date"] == row["date"]) & (hist["ticker"] == ticker)
        hist = hist[~mask]
        hist = pd.concat([hist, pd.DataFrame([row])], ignore_index=True)
    else:
        STORE.parent.mkdir(exist_ok=True)
        hist = pd.DataFrame([row])
    
    hist.to_parquet(STORE, index=False)
    print(f"[gex] Snapshot saved ({len(hist)} rows total): {STORE}")
```
**For Phase 9, adapt to 3-key dedup (date + ticker + horizon):**
```python
def save_evolution_row(date: datetime.date, ticker: str, horizon: int, ...) -> None:
    """Append or replace a single (date, ticker, horizon) row."""
    row = {"date": date, "ticker": ticker, "horizon": horizon, ...}
    
    if STORE.exists():
        hist = pd.read_parquet(STORE)
        for col in _FLOAT_COLS:
            if col in hist.columns:
                hist[col] = hist[col].astype("float64")
        mask = (hist["date"] == row["date"]) & (hist["ticker"] == ticker) & (hist["horizon"] == horizon)
        hist = hist[~mask]
        hist = pd.concat([hist, pd.DataFrame([row])], ignore_index=True)
    else:
        STORE.parent.mkdir(parents=True, exist_ok=True)
        hist = pd.DataFrame([row])
    
    hist.to_parquet(STORE, index=False)
```

**Load pattern** (`gex/validation.py:92-102`):
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
**For Phase 9, adapt to optional horizon filter:**
```python
def load_evolution(ticker: str, horizon: int | None = None, days: int = 30) -> pd.DataFrame:
    """Load evolution metrics, optionally filtered by horizon."""
    if not STORE.exists():
        return pd.DataFrame()
    try:
        hist = pd.read_parquet(STORE)
        hist["date"] = pd.to_datetime(hist["date"]).dt.date
        hist = hist[hist["ticker"] == ticker].sort_values("date", ascending=False)
        if horizon is not None:
            hist = hist[hist["horizon"] == horizon]
        return hist.head(days).reset_index(drop=True)
    except Exception as exc:
        print(f"[surface_evolution] load_evolution failed for {ticker}: {exc}")
        return pd.DataFrame()
```

---

### `gex/surface_history.py` (extend with helper)

**Analog:** `gex/surface_history.py` (existing)

**Responsibility:** Add `nth_trading_day_back(ticker: str, anchor_date: datetime.date, n: int) -> datetime.date | None` helper to resolve horizons against stored trading-day list.

**Existing list function** (`gex/surface_history.py:82-92`):
```python
def list_available_dates(ticker: str) -> list[datetime.date]:
    path = _store_path(ticker)
    if not path.exists():
        return []
    try:
        hist = pd.read_parquet(path, columns=["date"])
        dates = pd.to_datetime(hist["date"]).dt.date.unique()
        return sorted(set(dates), reverse=True)
    except Exception as exc:
        print(f"[surface_history] list_available_dates failed for {ticker}: {exc}")
        return []
```

**New helper to add** (RESEARCH.md Q4, lines 218-237):
```python
def nth_trading_day_back(ticker: str, anchor_date: datetime.date, n: int) -> datetime.date | None:
    """
    Find the date that is N trading sessions before anchor_date.
    
    Returns the actual date N positions back in the descending sorted list of 
    available dates. If fewer than N+1 stored dates exist (including today), returns None.
    
    Example:
        If list_available_dates returns [today, -1d, -2d, -5d, -6d, -10d, ...]
        nth_trading_day_back(ticker, today, 5) → -5d (the 6th item, counting from 0)
    """
    available = list_available_dates(ticker)
    if anchor_date not in available:
        return None
    idx = available.index(anchor_date)
    if idx + n >= len(available):
        return None
    return available[idx + n]
```

---

### `gex/config.py` (modify — add evolution region thresholds)

**Analog:** `gex/config.py` (existing)

**Pattern:** Central location for all magic constants with one-line rationale per constant. New section after line 94 (coverage mask comment).

**Add new section after SURFACE_SMOOTHING** (`gex/config.py:81-94`):
```python
# ── Surface evolution scalar region definitions ──────────────────────────────

SURFACE_EVOLUTION_PUT_WING_CLIP: float = -5.0
"""Put-wing region threshold (% OTM) for skew_change metric.
Moneyness values < this threshold (e.g., −8%, −10%) are "put wing"; 
chosen symmetric with call wing to balance put-call skew representation."""

SURFACE_EVOLUTION_CALL_WING_CLIP: float = 5.0
"""Call-wing region threshold (% OTM) for skew_change metric.
Moneyness values > this threshold are "call wing"; symmetric with put wing."""

SURFACE_EVOLUTION_DTE_FRONT_MAX: int = 30
"""Front-month DTE ceiling for term_change metric.
Front region = [dte_floor=5, this value]. Shorter-dated contracts."""

SURFACE_EVOLUTION_DTE_BACK_MIN: int = 90
"""Back-month DTE floor for term_change metric.
Back region = [this value, SURFACE_DTE_MAX=180]. Longer-dated contracts."""

SURFACE_EVOLUTION_ATM_CLIP: float = 2.0
"""ATM band width (% OTM) for term_change metric.
ATM region = [−this value, +this value]. Defines which cells are ATM."""
```

---

### `gex/run_daily.py` (modify — add non-blocking evolution pass)

**Analog:** `gex/run_daily.py` (existing)

**Responsibility:** Add a second loop after the snapshot save loop to trigger evolution computation for all tickers.

**Integration point pattern** (`gex/run_daily.py:49-102`, specifically lines 96-101 for non-blocking observation try/except):
```python
# Existing snapshot save loop (lines 60-71):
for ticker in ALL_TICKERS:
    print(f"  {ticker}...", end=" ", flush=True)
    data = process_ticker(ticker)
    all_data.append(data)
    s = data["summary"]
    if not s.get("error"):
        save_snapshot(s, ticker, skew_df=data.get("skew_df"))
        save_surface_snapshot(data.get("surface_df"), ticker, spot=s["spot"])
        # ... print summary ...
    else:
        print(f"ERROR: {s['error']}")

# Existing observation try/except (lines 96-101):
try:
    note_path = observation.append_to_daily_note(index_results, today)
    if note_path:
        print(f"[gex-daily] Observation block appended: {note_path}")
except Exception as exc:
    print(f"[gex-daily] Observation log failed (non-blocking): {exc}")
```

**Add new non-blocking evolution pass after snapshot loop, before email build** (after line 71, before line 73):
```python
# ──────── NEW: non-blocking evolution pass (second loop) ────────
print("\n[run_daily] Computing surface evolution...")
from gex.surface_evolution import update_evolution
for ticker in INDEX_TICKERS:
    try:
        update_evolution(ticker, today)
    except Exception as exc:
        print(f"  [WARN] {ticker} evolution failed (non-blocking): {exc}")

# ──────── existing email build (line 73+) ────────
```

**Non-blocking pattern from observation block:** wrap in try/except, print warning on failure, do NOT raise or return early. Email proceeds regardless.

---

### `gex/tests/test_surface_evolution.py` (new unit + integration tests)

**Analog:** `gex/tests/test_rbf_grid.py` and `gex/tests/test_coverage_mask.py`

**Test structure pattern** (`gex/tests/test_rbf_grid.py:1-26`):
```python
"""[Brief description of the feature being tested]."""
from __future__ import annotations

import numpy as np
import pandas as pd

from gex import config
from gex.analytics import rbf_grid  # or other shared helpers


def _fixed_surface_df(spot: float = 500.0) -> pd.DataFrame:
    """Deterministic OTM scatter for reproducible tests."""
    rows = []
    for dte in [7, 14, 30, 60, 90, 120]:
        for ks in [0.90, 0.95, 1.0, 1.05, 1.10]:
            rows.append({
                "dte": float(dte),
                "strike": spot * ks,
                "iv_pct": 20.0 + (1.0 - ks) * 12.0 + dte * 0.01,
                "log_moneyness": np.log(ks),
                "moneyness": ks,
            })
    return pd.DataFrame(rows)


def test_descriptive_name():
    """What the test validates."""
    spot = 500.0
    df = _fixed_surface_df(spot)
    # ... arrange, act, assert ...
    assert ...
```

**Test files to create:**

1. **`gex/tests/test_surface_evolution.py`** — unit + integration tests
   - `test_nth_trading_day_back_resolves_horizons` — verify 5/10/20 day resolution
   - `test_nth_trading_day_back_cold_start` — returns None if <N+1 sessions exist
   - `test_scalar_level_is_mean_diffs` — level = nanmean(IV_diff_masked)
   - `test_scalar_rms_ignores_nan` — rms uses nanmean of squared diffs
   - `test_skew_change_wing_split` — put-wing and call-wing regions computed correctly
   - `test_term_change_front_back` — front vs back DTE regions, ATM band
   - `test_mask_intersection_and_logic` — baseline masks intersected with AND
   - `test_evolution_idempotent_on_rerun` — 3-key dedup (date, ticker, horizon)
   - `test_backfill_consistency` — backfill produces same scalars as daily ingestion
   - `test_cold_start_returns_none` — no row written if horizons unavailable

2. **`gex/tests/test_surface_history.py` (extend)** — add nth_trading_day_back tests
   - Import and test the new helper against the existing parquet store

**Fixture pattern** (`gex/tests/test_coverage_mask.py:15-27`):
```python
def _chain(dtes, pct_otms, spot=500.0):
    rows = []
    for dte in dtes:
        for p in pct_otms:
            ks = 1.0 + p / 100.0
            rows.append({
                "dte": float(dte),
                "strike": spot * ks,
                "iv_pct": 20.0 + (-p) * 0.3 + dte * 0.01,
                "log_moneyness": np.log(ks),
                "moneyness": ks,
            })
    return pd.DataFrame(rows)
```

---

## Shared Patterns

### Parquet Idempotency
**Source:** `gex/validation.py:76-88` and `gex/surface_history.py:46-54`

**Pattern:** Read existing store → filter out old rows matching the dedup key → concatenate new row → write back. Windows-safe via `pathlib.Path` + pandas `to_parquet`.

**Apply to:** All CRUD operations on `surface_evolution.parquet` (create, update, load).

```python
# Dedup key for validation.py: (date, ticker)
mask = (hist["date"] == row["date"]) & (hist["ticker"] == ticker)
hist = hist[~mask]

# Dedup key for surface_history.py: (date, ticker)
hist["date"] = pd.to_datetime(hist["date"]).dt.date
hist = hist[hist["date"] != today]

# Dedup key for surface_evolution.py: (date, ticker, horizon)
mask = (hist["date"] == row["date"]) & (hist["ticker"] == ticker) & (hist["horizon"] == horizon)
hist = hist[~mask]
```

### Grid Axis Sharing
**Source:** `gex/analytics.py:159-186` (`rbf_grid` and `coverage_mask`)

**Pattern:** Both today's grid and every baseline-day grid are constructed identically from the same DTE and %OTM axis ranges, ensuring shapes match and cells correspond by position. Spot normalization uses the stored spot from that day, not a global scalar.

**Apply to:** Every call to `rbf_grid` and `coverage_mask` in `surface_evolution.py`.

```python
# Construct axes once, reuse for all baseline comparisons
dte_max = min(surface_df["dte"].max(), config.SURFACE_DTE_MAX)
dte_grid = np.linspace(5, dte_max, config.SURFACE_GRID_DTE)
otm_grid = np.linspace(-15, 15, config.SURFACE_GRID_LM)

# Both today and prior use the same axes with their own spot
IV_today = rbf_grid(surface_today, spot_today, dte_grid, otm_grid)
IV_prior = rbf_grid(surface_prior, spot_prior, dte_grid, otm_grid)
```

### Mask Intersection
**Source:** RESEARCH.md Q2 (lines 153-156) + Phase 8 validation

**Pattern:** Before computing any scalar on grid differences, intersect all coverage masks using boolean AND so only cells where all days have support are included. NaN outside this intersection is correct.

**Apply to:** Every scalar computation (level, rms, skew_change, term_change).

```python
mask_intersection = mask_today
for mask_prior in mask_baseline_list:
    mask_intersection = mask_intersection & mask_prior

IV_diff_masked = np.where(mask_intersection, IV_diff, np.nan)
level = np.nanmean(IV_diff_masked)
```

### Non-Blocking Try/Except
**Source:** `gex/run_daily.py:96-101`

**Pattern:** Wrap the call in try/except, print a warning on failure, and do NOT raise or return early. The calling orchestrator (email, observation, evolution) continues regardless.

**Apply to:** The evolution pass inside `run_daily.run()`.

```python
try:
    update_evolution(ticker, today)
except Exception as exc:
    print(f"  [WARN] {ticker} evolution failed (non-blocking): {exc}")
    # continue to next ticker or next block
```

---

## No Analog Found

None — all files are extensions or closely analogous to existing patterns.

---

## Metadata

**Analog search scope:** `gex/` (validation, surface_history, config, run_daily, analytics), `gex/tests/` (rbf_grid, coverage_mask)

**Files scanned:** 7 (validation.py, surface_history.py, config.py, run_daily.py, analytics.py, test_rbf_grid.py, test_coverage_mask.py)

**Pattern extraction date:** 2026-05-30

---

## PATTERN MAPPING COMPLETE

**Phase:** 09 - Surface Evolution Engine
**Files classified:** 5
**Analogs found:** 5 / 5 (100%)

### Coverage
- Files with exact analog: 5
- Files with role-match analog: 0
- Files with no analog: 0

### Key Patterns Identified
1. **Parquet idempotency pattern** — Read-filter-concat-write with 3-key dedup (date, ticker, horizon) mirrors `validation.py` and `surface_history.py` exactly.
2. **Shared grid axes** — Today and all baseline grids use identical (DTE, %OTM) axes; spot normalization per day via returned `load_surface_snapshot` tuple.
3. **Mask intersection before scalars** — Coverage masks AND'd across all days before any statistical computation; NaN outside intersection is correct.
4. **Non-blocking second pass** — Evolution computation wrapped in try/except in `run_daily.py:~72`; failure never blocks email (pattern from observation block lines 96-101).
5. **Config constants for region definitions** — Put/call wing clips and DTE front/back thresholds added to `config.py` with documented rationale, ensuring consistency across horizons and tickers.
6. **Test fixtures and assertions** — Unit tests reuse deterministic surface fixtures (`_fixed_surface_df`, `_chain`) and verify exact numerics via `np.testing.assert_allclose` (Phase 8 pattern).

### Ready for Planning
Pattern mapping complete. Planner can now reference analog patterns in PLAN.md files. Concrete read-first locations:
- Parquet idempotency: `gex/validation.py:76-88` (3-key dedup pattern)
- Grid construction: `gex/analytics.py:159-186` (rbf_grid + coverage_mask signatures)
- Non-blocking integration: `gex/run_daily.py:96-101` (observation try/except pattern)
- Test fixtures: `gex/tests/test_rbf_grid.py:13-25` and `gex/tests/test_coverage_mask.py:15-27`
- Config pattern: `gex/config.py:54-89` (section structure with rationale)

---

*Phase: 09-surface-evolution-engine*
*Mapped: 2026-05-30*

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/09-surface-evolution-engine/09-RESEARCH|09-RESEARCH]]

<!-- LINKS:END -->
