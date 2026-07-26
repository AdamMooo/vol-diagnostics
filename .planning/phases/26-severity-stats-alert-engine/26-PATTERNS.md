# Phase 26: Severity Statistics & Alert Engine - Pattern Map

**Mapped:** 2026-07-24
**Files analyzed:** 9 new/modified files
**Analogs found:** 8 / 9 (89%)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `engine/monitor/__init__.py` | config | N/A | `engine/gex/__init__.py` | exact |
| `engine/monitor/ranker.py` | service | CRUD | `engine/vol/vrp_history.py` | exact |
| `engine/monitor/hysteresis.py` | service | request-response | `engine/surface/surface_evolution.py` | role-match |
| `engine/monitor/calibration.py` | utility | batch | `engine/run_gex.py` | role-match |
| `engine/monitor/schema.py` | model | N/A | `engine/report/card_model.py` | role-match |
| `engine/monitor/monitor_store.py` | service | file-I/O | `engine/data/validation.py` | exact |
| `engine/monitor/metrics.py` | service | file-I/O | `engine/vol/vrp_history.py` | exact |
| `engine/config.py` | config | N/A | `engine/config.py` (existing) | exact |
| `engine/run_daily.py` | orchestration | request-response | `engine/run_daily.py` (existing) | exact |

## Pattern Assignments

### `engine/monitor/ranker.py` (service, CRUD)

**Analog:** `engine/vol/vrp_history.py`

**Imports pattern** (lines 1-19):
```python
from __future__ import annotations

import pandas as pd
from scipy.stats import percentileofscore

from engine import config
from engine.data.vol_index import load_vol_index
from engine.vol.vol_metrics import compute_rv20
```

**Core percentile-rank pattern** (lines 45-94):
```python
def vrp_percentile(ticker: str, lookback: int | None = None) -> dict:
    """Today's vol-index-based VRP, its percentile rank, and the sample count.
    
    Ranks today's VRP against ALL available aligned history by default.
    Pass an explicit `lookback` to rank against a shorter window instead.
    
    Returns {"vrp": float vol points, "pct": int 0-100, "n": int} when data is sufficient,
    else {"vrp": None, "pct": None, "n": 0} on empty vol-index, yfinance failure, or no
    date alignment. Never raises.
    """
    none_dict = {"vrp": None, "pct": None, "n": 0}
    
    # ... load metric history ...
    
    today_vrp = float(vrp_hist.iloc[-1])  # same definition as every history point
    window = vrp_hist if lookback is None else vrp_hist.iloc[-lookback:]
    pct = int(percentileofscore(window.to_numpy(), today_vrp, kind="rank"))
    return {"vrp": today_vrp, "pct": pct, "n": len(window)}
```

**Key points:**
- `percentileofscore(..., kind="rank")` produces 0–100 scale (ECDF)
- Returns dict with `pct`, `n`, and metric value for consistency
- Never raises; returns none-dict on any failure
- `lookback=None` uses full history; explicit lookback truncates window

**Apply to:** All ranker functions in `engine/monitor/ranker.py` — one function per metric (VRP, skew_25d, fly_25d, surface_level, surface_rms, term_ratios), each following this signature and error-handling pattern.

---

### `engine/monitor/monitor_store.py` (service, file-I/O)

**Analog:** `engine/data/validation.py`

**Store initialization pattern** (lines 30, and throughout):
```python
STORE = pathlib.Path(__file__).resolve().parents[2] / "out" / "gex_snapshots.parquet"

_FLOAT_COLS = (
    "zero_gamma_level", "call_wall", "put_wall",
    "front_skew", "put_25d_iv", "call_25d_iv", "iv30",
    ...
)
```

**Parquet append pattern (idempotent)** (lines 42–94):
```python
def save_snapshot(summary: dict, ticker: str, skew_df: pd.DataFrame | None = None,
                  date: datetime.date | None = None) -> None:
    """Append today's summary dict to the parquet store (idempotent on date+ticker)."""
    
    row = {
        "date": date or datetime.date.today(),
        "ticker": ticker,
        "spot": summary["spot"],
        ...
    }
    
    if STORE.exists():
        hist = pd.read_parquet(STORE)
        for col in _FLOAT_COLS:
            if col in hist.columns:
                hist[col] = hist[col].astype("float64")
        mask = (hist["date"] == row["date"]) & (hist["ticker"] == ticker)
        hist = hist[~mask]  # Remove old version if exists
        hist = pd.concat([hist, pd.DataFrame([row])], ignore_index=True)
    else:
        STORE.parent.mkdir(exist_ok=True)
        hist = pd.DataFrame([row])
    
    atomic_to_parquet(hist, STORE)
    print(f"[gex] Snapshot saved ({len(hist)} rows total): {STORE}")
```

**Key points:**
- Idempotency: mask removes rows with matching (date, ticker, [metric if multi-metric])
- concat with new row, then atomic write
- Type-cast float columns to ensure consistency on re-reads
- Always print confirmation with row count

**Apply to:** `save_monitor_row()` — one row per (date, ticker, metric), with columns: date, ticker, metric, level_rank_deep, level_rank_1yr, change_rank, n_deep, n_1yr, band_state.

---

### `engine/monitor/metrics.py` (service, file-I/O)

**Analog:** `engine/vol/vrp_history.py` (lines 22–43, metric loading) + `engine/data/validation.py` (list_snapshot_dates pattern)

**Multi-source metric loader pattern** (lines 22–42):
```python
def _fetch_closes_yf(ticker: str, period: str = "2520d") -> "pd.Series | None":
    """Daily closes from yfinance, date-indexed oldest-first. None on any failure; never raises.
    
    Mirrors compute._fetch_spot_history_yf but returns a date-indexed Series over a wider
    window so a rolling RV20 history can be aligned to the vol-index dates by date.
    """
    try:
        import yfinance as yf
        yf_ticker = ticker.replace(".", "-")
        hist = yf.Ticker(yf_ticker).history(period=period)
        if hist.empty or "Close" not in hist.columns:
            return None
        closes = hist["Close"].dropna()
        if len(closes) < 21:
            return None
        closes.index = pd.to_datetime(closes.index).date
        closes.index.name = "date"
        return closes.sort_index()
    except Exception as exc:
        print(f"[vrp_history] yf history failed for {ticker}: {exc}")
        return None
```

**Combined metric-load pattern** (inferred from RESEARCH.md Pattern 4):
```python
def load_metric_series(ticker: str, metric_name: str) -> pd.Series | None:
    """Load a metric's full history from its native store, date-indexed.
    
    Examples:
    - VRP → engine/data/vol_index.py
    - Skew (25Δ) → engine/data/validation.py (gex_snapshots.parquet)
    - Surface Evolution RMS → engine/data/surface_history.py
    - Term ratio (9D/30) → engine/data/vol_index.py
    """
    if metric_name == "vrp":
        return _load_vrp_history(ticker)  # refactored from vrp_history.py
    elif metric_name in ("skew_25d", "fly_25d"):
        snapshots = pd.read_parquet(GEXSNAP_STORE)
        snapshots = snapshots[snapshots["ticker"] == ticker].sort_values("date")
        col_map = {"skew_25d": "front_skew", "fly_25d": "butterfly"}
        return snapshots.set_index("date")[col_map[metric_name]]
    # ... etc. for surface, term ratios ...
```

**Apply to:** `engine/monitor/metrics.py` — one loader per metric type (VRP, skew, butterfly, surface_level, surface_rms, term_9d_30, term_30_3m). Each returns date-indexed pd.Series or None on failure. Never raises.

---

### `engine/monitor/hysteresis.py` (service, request-response)

**Analog:** `engine/surface/surface_evolution.py` (state-like computation pattern, lines 1–30, 60–80)

**State machine / conditional logic pattern** (from surface_evolution.py logic):
```python
def _construct_grid_axes(surface_df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Build shared DTE and %OTM grid axes from today's surface."""
    dte_max = min(float(surface_df["dte"].max()), float(config.SURFACE_DTE_MAX))
    dte_grid = np.linspace(5.0, dte_max, config.SURFACE_GRID_DTE)
    otm_grid = np.linspace(
        -config.SURFACE_PLOT_OTM_CLIP,
        config.SURFACE_PLOT_OTM_CLIP,
        config.SURFACE_GRID_LM,
    )
    return dte_grid, otm_grid
```

**Alert state-machine pattern** (from RESEARCH.md Pattern 3, lines 243–283):
```python
def check_alert_transition(today_rank: int, 
                          band_entry: int, 
                          band_escalate: int,
                          band_exit: int,
                          yesterday_state: str | None) -> tuple[str | None, str]:
    """
    Determine if an alert should fire, given today's rank and yesterday's state.
    
    yesterday_state: "out", "in_entry", "in_escalate", or None (first time).
    Returns: (alert_to_fire, new_state)
    
    Transitions:
    - out → in_entry (if rank >= band_entry) → FIRE alert
    - in_entry → in_escalate (if rank >= band_escalate) → RE-FIRE alert
    - in_* → out (if rank < band_exit, e.g., 80th < 95th entry) → no alert, clear state
    """
    
    if yesterday_state is None or yesterday_state == "out":
        # Check entry
        if today_rank >= band_entry:
            return "entry", "in_entry"
        return None, "out"
    
    if yesterday_state == "in_entry":
        # Already in band; check escalation
        if today_rank >= band_escalate:
            return "escalation", "in_escalate"
        # Check exit (lower than entry)
        if today_rank < band_exit:
            return None, "out"
        return None, "in_entry"
    
    if yesterday_state == "in_escalate":
        # Already escalated; check exit
        if today_rank < band_exit:
            return None, "out"
        # Stay in escalate (even if dropped below band_escalate, stay until exit)
        return None, "in_escalate"
```

**Apply to:** `engine/monitor/hysteresis.py` — one function per metric×ticker, reads yesterday's band_state from monitor store, emits alert event or None. May use enum or string-based states per Claude's discretion.

---

### `engine/monitor/schema.py` (model, N/A)

**Analog:** `engine/report/card_model.py` (lines 1–80 for dataclass and helper structure)

**Data structure pattern** (lines 1–56 of card_model.py):
```python
from __future__ import annotations

import math
import dataclasses
from typing import Any

import pandas as pd

from engine import config

# Re-export palette refs used by renderers
LABEL_GRAY = "#94a3b8"


# ── Formatting helpers (canonical — report.py imports from here) ──────────

def _fmt_b(val: float | None) -> str:
    if val is None:
        return "—"
    b = val / 1e9
    return f"{'+' if b >= 0 else ''}{b:.2f}B"

@dataclasses.dataclass
class CardField:
    """Single card field for display (used by both report.py and streamlit app.py)."""
    # ... field definitions ...
```

**Apply to:** `engine/monitor/schema.py` — define MonitorRow and AlertEvent dataclasses (or TypedDict). Minimum fields:
- MonitorRow: date, ticker, metric, level_rank_deep, level_rank_1yr, change_rank, n_deep, n_1yr, band_state
- AlertEvent: date, ticker, metric, alert_type (entry/escalation), transition_rank, prior_state

---

### `engine/monitor/calibration.py` (utility, batch)

**Analog:** `engine/run_gex.py` (lines 1–71, CLI orchestration + report pattern)

**CLI entry point pattern** (run_gex.py lines 35–71):
```python
def run(ticker: str = "SPY", save: bool = True) -> dict:
    print(f"[gex] Loading chain for {ticker}...")
    snapshot = load_chain(ticker)
    print(f"[gex] Spot: {snapshot.spot:.2f}  |  "
          f"Options loaded: {len(snapshot.chains):,}  |  "
          f"Expiries: {snapshot.chains['expiry'].nunique()}")
    
    # ... compute ...
    summary = summarise(strike_df, profile_df, spot=snapshot.spot)
    
    _print_summary(summary, ticker, snapshot.as_of)
    
    if save:
        OUT_DIR.mkdir(exist_ok=True)
        date_tag = snapshot.as_of.isoformat()
        # ... save outputs ...
        print(f"[gex] Saved: {path1}")
    
    return summary


def _print_summary(s: dict, ticker: str, as_of: datetime.date) -> None:
    print(f"\n{'='*50}")
    print(f"  {ticker} GEX SUMMARY — {as_of}")
    print(f"{'='*50}")
    # ... formatted output ...
```

**Entry point pattern** (bottom of run_gex.py, inferred):
```python
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="SPY")
    parser.add_argument("--no-save", action="store_true")
    args = parser.parse_args()
    
    run(ticker=args.ticker, save=not args.no_save)
```

**Apply to:** `engine/monitor/calibration.py` — main `calibrate()` function that:
1. Loads all metric histories
2. Iterates candidate bands + hysteresis gaps
3. Replays alert state machine over all history
4. Counts episodes/week per band choice
5. Prints human-readable table + recommendation
6. Optional: `--dry-run` flag to test without updating config

---

### `engine/monitor/__init__.py` (config, N/A)

**Analog:** `engine/gex/__init__.py`

**Package initialization pattern** (minimal):
```python
"""Severity ranking and alert engine."""
from __future__ import annotations
```

Or expose key functions if desired:
```python
from engine.monitor.ranker import compute_metric_ranks
from engine.monitor.hysteresis import check_alert_transition

__all__ = ["compute_metric_ranks", "check_alert_transition"]
```

**Apply to:** Create `engine/monitor/__init__.py` following minimal or re-export pattern. No additional logic needed.

---

### `engine/config.py` (config, N/A)

**Analog:** `engine/config.py` (existing file, lines 1–100)

**Config constant pattern** (lines 1–53):
```python
"""
Central configuration for vol-diagnostics. Magic numbers that were previously scattered
across modules — gathered here so the assumptions baked into the system are
visible in one place and tunable without grep-and-replace.

Each constant has a one-line rationale and, where applicable, the source paper
or empirical reason.
"""
from __future__ import annotations

# ── Chain filtering (engine.data.data_loader.load_chain defaults) ──────────────────────

MIN_OI: int = 100
"""Drop options with fewer than this many contracts of open interest."""

GEX_MAX_DTE: int = 90
"""Upper DTE bound for GEX / positioning analysis."""
```

**Add to config.py** (append to bottom or in a new Monitor section):
```python
# ── Monitor: severity ranking + alerting (engine.monitor.*) ──────────────────────

MONITOR_CREDIBILITY_FLOOR_SESSIONS: int = 252
"""Minimum sample count before a metric can fire alerts (1 year of trading days).
Ranks are always computed and labeled; alerts only fire when n >= this floor.
Consequence: at Phase 26 ship, only VRP + SPY term ratios alert; chain metrics
(skew, butterfly, surface evolution, ~50 sessions since 2026-05) alert at ~2027-05."""

MONITOR_ALERT_BAND_ENTRY: int = 97
"""Entry percentile threshold for alerts. Alerts fire when rank >= this value.
Selected 2026-07-XX via calibration replay on YY months of history.
Rationale: ~0.9 episodes/week, balancing sensitivity and false-alarm tolerance."""

MONITOR_ALERT_BAND_ESCALATE: int = 99
"""Escalation percentile threshold for re-firing alerts. Already-in-band metric
must reach this higher band to trigger a re-fire (prevents flicker on daily noise).
Rationale: halfway between entry and 100th."""

MONITOR_ALERT_BAND_EXIT: int = 87
"""Exit percentile threshold (hysteresis). Metric must drop below this to clear alert state.
Exit is lower than entry (band_entry - 10) to prevent flicker on noisy bounces.
Rationale: 10pt hysteresis gap from calibration replay flicker analysis."""

MONITOR_ALERT_HYSTERESIS_GAP: int = 10
"""Hysteresis width: entry - exit. Set from calibration replay's flicker analysis,
which shows this gap collapses multi-fire episodes (same event firing 1–2 days apart)
into single episodes. Wider gaps → fewer alerts; narrower gaps → more responsive."""
```

**Key points:**
- Include rationale one-liners referencing the decision letters (D-01, D-08, etc.)
- Include calibration date + history depth so future runs know if bands need refresh
- Values are derived from calibration replay, not hardcoded from theory
- All related to CONTEXT.md decisions (D-04, D-05, D-06, D-08)

---

### `engine/run_daily.py` (orchestration, request-response)

**Analog:** `engine/run_daily.py` (existing file, lines 1–56, structure)

**Orchestration seam pattern** (lines 14–40):
```python
from __future__ import annotations

import argparse
import datetime
import pathlib

from engine.compute import compute_ticker
from engine.data.validation import save_snapshot
from engine.data.surface_history import (
    save_surface_snapshot, nth_trading_day_back, load_surface_snapshot, list_available_dates,
)
from engine.data.oi_history import save_oi_snapshot, list_oi_dates
from engine.report import report as rpt
from engine.report import emailer
from engine.report import observation
# ... more imports ...

INDEX_TICKERS = ["SPY", "QQQ", "IWM"]
ALL_TICKERS = INDEX_TICKERS

OUT_DIR = pathlib.Path(__file__).resolve().parents[1] / "out" / "gex"
SNAPSHOT_STORE = pathlib.Path(__file__).resolve().parents[1] / "out" / "gex_snapshots.parquet"
```

**Daily loop pattern** (inferred from main orchestration):
```python
# In run_daily's main orchestration (e.g., in run() or __main__):
for ticker in ALL_TICKERS:
    summary = compute_ticker(ticker, today=today, ...)
    save_snapshot(summary, ticker, ...)
    save_surface_snapshot(ticker, surface_df, ...)
    save_oi_snapshot(ticker, oi_df, ...)
    # NEW: Append monitor rows + alert events
    monitor.compute_and_save_ticker(ticker, summary, today=today)
```

**Apply to:** `engine/run_daily.py` — after existing snapshot saves, call:
```python
from engine.monitor import ranker, hysteresis, monitor_store

# After line ~XX (all snapshot saves):
for ticker in ALL_TICKERS:
    monitor.compute_and_save_ticker(ticker, summary, today=today)
```

(Or encapsulate in `engine/monitor/ranker.py` as `compute_and_save_monitor_rows(ticker, all_data, today)`, called once per ticker in the loop.)

---

## Shared Patterns

### Percentile Ranking (ECDF via scipy.stats)
**Source:** `engine/vol/vrp_history.py` (lines 15, 93)
**Apply to:** All metric rank computations in `engine/monitor/ranker.py`
```python
from scipy.stats import percentileofscore

pct = int(percentileofscore(window.dropna().to_numpy(), today_value, kind="rank"))
```
- `kind="rank"` uses van der Waerden scoring (ECDF definition)
- Returns 0–100 integer percentile scale
- Handle NaN via explicit `.dropna()` before conversion to numpy
- Return tuple `(pct: int, n: int)` per vrp_percentile() pattern

### Parquet Store Append (Idempotent)
**Source:** `engine/data/validation.py` (lines 42–94) + `engine/data/store.py` (lines 24–39)
**Apply to:** All parquet writes in `engine/monitor/monitor_store.py`
```python
from engine.data.store import atomic_to_parquet

if STORE.exists():
    hist = pd.read_parquet(STORE)
    mask = (hist["date"] == row["date"]) & (hist["ticker"] == ticker) & (hist["metric"] == metric)
    hist = hist[~mask]  # idempotent: remove old version
    hist = pd.concat([hist, pd.DataFrame([row])], ignore_index=True)
else:
    STORE.parent.mkdir(parents=True, exist_ok=True)
    hist = pd.DataFrame([row])

atomic_to_parquet(hist, STORE)
print(f"[monitor] Row saved ({len(hist)} rows total): {STORE}")
```
- Always use `atomic_to_parquet()` to prevent truncation on crash
- Idempotency: mask by (date, ticker, metric) before concat
- Type-cast float columns to float64 on each read for consistency
- Print confirmation with row count

### Error Handling (Never Raise)
**Source:** `engine/vol/vrp_history.py` (lines 58–94)
**Apply to:** All metric loaders and state-machine functions
```python
def compute_metric_rank(metric_series: pd.Series, today_value: float) -> dict:
    """Never raises."""
    try:
        # ... computation ...
        return {"rank": pct, "n": n}
    except Exception as exc:
        print(f"[monitor] compute_metric_rank failed: {exc}")
        return {"rank": None, "n": 0}
```
- Wrap public functions in try/except; print diagnostic, return none-dict
- Private helpers can raise (caller handles)
- None-dict schema: match return type's null case exactly

---

## No Analog Found

Files with no close match in the codebase (planner should use RESEARCH.md patterns instead):

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `engine/monitor/calibration.py` | utility | batch | No existing batch replay tool in codebase; pattern derived from RESEARCH.md §Pattern 6 + general CLI structure from run_gex.py |

---

## Metadata

**Analog search scope:** `engine/{vol,data,surface,report,gex}/`, `engine/run_gex.py`, `engine/run_daily.py`, `engine/tests/test_*.py`
**Files scanned:** 43 engine modules total; 8 analog files closely read
**Pattern extraction date:** 2026-07-24
**Confidence:** HIGH — 8 of 9 new files map directly to existing analogs; only `calibration.py` (batch analysis) has no codebase precedent but is well-specified in RESEARCH.md.


---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
**Phase siblings:**
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-CONTEXT|26-CONTEXT]]
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-DISCUSSION-LOG|26-DISCUSSION-LOG]]
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-RESEARCH|26-RESEARCH]]

<!-- LINKS:END -->
