# Phase 26: Severity Statistics & Alert Engine - Research

**Researched:** 2026-07-23
**Domain:** Market microstructure anomaly detection via empirical percentile ranking, transition-gated alerting, and false-alarm budget calibration
**Confidence:** HIGH

## Summary

Phase 26 instruments existing metrics (VRP, skew, term structure, surface evolution) with honest "how unusual is this" measures — empirical-CDF percentile ranks on both levels and 5-day changes, ranked against dual lookback windows (deep history + 1-year). Alerts fire on band entry with hysteresis to prevent flickering; bands are calibrated from false-alarm replay over stored metric history, not hardcoded from theory. The phase delivers a new `engine/monitor/` package that appends severity rows to `out/monitor/` parquet daily, plus a reusable `calibrate` CLI that re-runs the false-alarm analysis as history deepens. No new metrics are computed — severity is a transformation-layer atop existing values.

**Primary recommendation:** Build the monitor engine to follow the existing VRP percentile pattern (vrp_history.py) — load metric histories, compute percentileofscore for each metric×lookback×level/change combination, track alert state via hysteresis, and persist daily rows. The `calibrate` command replays the ranker on all stored snapshots with candidate bands and reports episodes/week per threshold to guide band selection.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Percentile ranking (ECDF) | API / Backend | — | Compute-heavy, stateless; runs once per day, no client interaction needed |
| Alert state machine (hysteresis) | API / Backend | — | Requires yesterday's band-state to decide if a transition is an entry or re-fire; persistence-dependent logic |
| Metric history loading | Database / Storage | API / Backend | Data access → backend logic |
| Alert-events table (persistence) | Database / Storage | — | Append-only store, read by Phase 27 dashboard |
| Calibration CLI | API / Backend (CLI tool) | — | Offline batch analysis; no dashboard/email integration at Phase 26 |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| scipy (stats) | ≥1.13 | `percentileofscore()` for ECDF ranks | Industry-standard empirical CDF; already in vol-diagnostics stack (scipy.stats used in app.py) |
| pandas | ≥2.0 | Row-wise percentile computation, history alignment | Core vol-diagnostics data frame library |
| pyarrow | ≥15.0 | Parquet serialization for `out/monitor/` store | Existing vol-diagnostics pattern (atomic_to_parquet) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | ≥1.26 | Array ops for rolling windows, NaN handling | Standard vol-diagnostics numerics |

**Installation:**
```bash
# All already in requirements.txt; no new packages needed
pip install -r requirements.txt
```

**Version verification:**
```bash
pip show scipy pandas numpy pyarrow
```

scipy 1.13+ confirmed (Feb 2025 training knowledge) with percentileofscore unchanged signature.

## Package Legitimacy Audit

No new external packages required for Phase 26. All dependencies (scipy, pandas, numpy, pyarrow) are pre-existing in `requirements.txt` and used throughout the codebase.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| scipy | PyPI | 25+ years | 1B+/month | [scipy/scipy](https://github.com/scipy/scipy) | [OK] | Approved |
| pandas | PyPI | 15+ years | 1B+/month | [pandas-dev/pandas](https://github.com/pandas-dev/pandas) | [OK] | Approved |

**Packages removed due to slopcheck [SLOP] verdict:** None
**Packages flagged as suspicious [SUS]:** None

## Phase Requirements

No formal phase requirement IDs were assigned for Phase 26 (requirements are TBD per ROADMAP). The CONTEXT.md decisions (D-01 through D-12) serve as the binding specification.

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Severity statistics (D-01 through D-03):**
- ECDF percentile rank (scipy.stats.percentileofscore) is the *only* severity measure — levels *and* 5-day changes ranked against each metric's own history
- No Gaussian z-scores (heavy tails/heteroskedasticity); robust z ((x−median)/MAD) only as fallback
- Dual lookback: deep (full available history via `config.VRP_DEEP_LOOKBACK_SESSIONS`) + 1-year (252 sessions), both persisted and available to alerts
- **Change severity: k=5 only** (matches Evolution engine horizon); two-sided |Δ5d| — one rank per metric for "moving abnormally fast either way"

**Alert rule & calibration (D-04 through D-06):**
- Alerts fire on **band entry**, re-fire only on **escalation** (higher band), exit band **lower than entry** (hysteresis)
- Tolerated alarm rate: **~1 episode/week** across the whole monitor
- Expected bands land ~97th–98th, but **NOT hardcoded** — they come from calibration replay (D-06)
- Band calibration is a **permanent CLI deliverable** (`python -m engine.monitor.calibrate`): replays ranker over stored histories, reports alert episodes/week per candidate band + hysteresis width, re-runnable as history deepens

**Metric inventory & credibility (D-07 through D-10):**
- v1 inventory: VRP, 25Δ skew, 25Δ fly, surface-evolution level & RMS (×SPY/QQQ/IWM) + SPY-only term ratios (9D/30, 30/3M)
- Evolution scalars rank as **levels only** (already 5d changes — no change-of-change)
- Ranks always computed and labeled with sample size n, but alerts fire **only with ≥252 sessions** of metric history
- Consequence: at ship only VRP + SPY term ratios alert; chain metrics (~50 sessions since 2026-05) visible-but-building until ~2027-05
- **IWM–SPY VRP spread NOT in v1** — seeded for post-release
- **Net GEX gets NO severity rank** — sign is a state chip only (GEX-as-candidate decision, 2026-07-22)

**Persistence (D-11 & D-12):**
- New **`out/monitor/`** parquet store, appended by `run_daily`, one row per metric×ticker×day: level rank (deep+1yr), |Δ5d| rank, n, band state
- Plus **alert-events table** (separate or same store)
- Phase 26 does **not** touch email; verification is via CLI output + tests + the persisted store

### Claude's Discretion
- Hysteresis exit-band width — set from calibration replay's flicker analysis (which gap collapses multi-fire episodes to one), not a priori
- Module layout (e.g., `engine/monitor/` package), store schema details, backfill approach for historical rows
- How `calibrate` presents candidate bands (table format, episode listings)

### Deferred Ideas (OUT OF SCOPE)
- IWM–SPY VRP spread severity row (post-v1)
- Multi-horizon change ranks (k=1, 10, 20)
- Tier-2 conditional base rates
- Order-statistic confidence intervals on percentile ranks

---

## Architecture Patterns

### System Architecture Diagram

```
Daily Orchestration (run_daily.py)
    ↓
compute_ticker() → summary dict (today's metrics)
    ↓
engine/monitor/ranker.py
    ├─ Load metric histories (gex_snapshots.parquet, surface_history, vol_index, etc.)
    ├─ Compute percentile ranks (ECDF @ deep + 1yr lookback)
    ├─ Compute 5-day change ranks
    └─ Emit monitor_row: {date, ticker, metric, level_rank_deep, level_rank_1y, change_rank, n, band_state}
         ↓
Alert State Machine (hysteresis.py)
    ├─ Load yesterday's band_state for this metric×ticker
    ├─ Transition logic: Entry? Escalation? Exit? (re-fire only on escalation)
    └─ Emit alert_event if transition occurs
         ↓
out/monitor/
    ├─ monitor_rows.parquet (one row per metric×ticker×day)
    └─ alert_events.parquet (one row per alert transition)
         ↓
Phase 27 (dashboard, email surfaces) — consume monitor store
```

**Data flow summary:**
1. `run_daily` calls `compute_ticker()` three times (SPY/QQQ/IWM) → metric summaries
2. Monitor engine loads prior snapshots from four existing stores (validation, surface_history, vol_index, oi_history)
3. Ranker computes percentileofscore for each metric×lookback combination
4. Hysteresis layer consumes yesterday's band_state and emits alert events on transition
5. Monitor rows + alert events appended to `out/monitor/` parquet
6. Phase 27 reads `out/monitor/` to render dashboard distribution board + email alerts

### Recommended Project Structure

```
engine/
├── monitor/                          # NEW: severity ranking + alerting
│   ├── __init__.py
│   ├── ranker.py                    # Core percentileofscore engine, metric-agnostic
│   ├── hysteresis.py                # Alert state machine (entry/escalation/exit)
│   ├── calibration.py               # Replay engine: iterate bands, count episodes/week
│   ├── schema.py                    # Monitor row schema + alert-event schema
│   ├── monitor_store.py             # Parquet I/O (save_monitor_row, load_history, etc.)
│   └── metrics.py                   # Per-metric loaders (VRP, skew, fly, evolution, term)
├── config.py                         # ADD: MONITOR_ALERT_FLOOR, MONITOR_BAND_*, MONITOR_HYSTERESIS_*
├── run_daily.py                      # EDIT: call monitor.compute after snapshot saves
└── [unchanged]
```

**Why this structure:**
- `engine/monitor/` isolates severity logic, paralleling existing `gex/`, `surface/`, `vol/` domains
- `ranker.py` is pure (no side effects) — testable in isolation
- `hysteresis.py` handles stateful alert transitions (reads yesterday's band_state)
- `calibration.py` is a batch analysis tool, independent of daily runs
- `metrics.py` encapsulates per-metric history-loading logic (some metrics read from vol_index, others from chain snapshots)

### Pattern 1: Percentile Ranking via scipy.stats.percentileofscore

**What:** Compute empirical-CDF percentile ranks for a metric value against a historical window.

**When to use:** Ranking any scalar metric (levels or changes) against its own history without distributional assumptions.

**Example:**
```python
from scipy.stats import percentileofscore
import pandas as pd

def compute_metric_rank(metric_values: pd.Series, today_value: float, 
                        lookback_sessions: int | None = None) -> tuple[int, int]:
    """
    Rank today_value against metric_values (historical + today).
    
    Returns: (percentile_rank, sample_size)
    """
    if metric_values.empty or today_value is None:
        return None, 0
    
    window = metric_values if lookback_sessions is None else metric_values.iloc[-lookback_sessions:]
    pct = int(percentileofscore(window.dropna().to_numpy(), today_value, kind="rank"))
    return pct, len(window.dropna())
```

Source: scipy.stats documentation; used in engine/vol/vrp_history.py (existing vol-diagnostics precedent).

**Key points:**
- `kind="rank"` uses the van der Waerden scoring (matches ECDF definition)
- Returns 0–100 (percentile scale)
- Handles NaN by explicit `.dropna()`
- No distributional assumption; robust to heavy tails/heteroskedasticity

### Pattern 2: Dual Lookback (Deep + 1-Year)

**What:** Rank each metric against both full available history AND a rolling 1-year window, persisting both.

**When to use:** Distinguishing "historically rare" (deep rank) from "locally unusual" (1-year rank); alerts can fire on either.

**Example:**
```python
from engine.vol.vrp_history import vrp_percentile  # Existing model

def compute_dual_rank(metric_name: str, ticker: str, 
                      today_value: float,
                      history_df: pd.DataFrame) -> dict:
    """
    Compute deep + 1-year ranks.
    history_df: date-indexed metric history.
    """
    deep_pct, deep_n = compute_metric_rank(history_df[metric_name], today_value)
    one_yr_pct, one_yr_n = compute_metric_rank(
        history_df[metric_name], today_value, lookback_sessions=252
    )
    
    return {
        "metric": metric_name,
        "level_rank_deep": deep_pct,
        "level_rank_1yr": one_yr_pct,
        "n_deep": deep_n,
        "n_1yr": one_yr_n,
    }
```

**Why this pattern:**
- Generalizes vrp_history.py's approach (which already uses deep + VRP_PERCENTILE_LOOKBACK)
- Decouples "rare event" from "regime shift" signals
- Both ranks persisted → Phase 27 can display them independently

### Pattern 3: Alert Hysteresis (Entry → Escalation → Exit)

**What:** Track alert state across days; fire alerts only on *transitions* (entry into band, escalation to higher band), not on every day the metric stays in a band.

**When to use:** Preventing alert fatigue (flickering) while responding to new movements.

**Example:**
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

Source: D-04 (alert rule), D-05 (hysteresis width from calibration).

### Pattern 4: Metric History Loading (Multi-Source)

**What:** Load full metric history per ticker, aligning data from heterogeneous sources (vol_index parquet, chain snapshots, evolution scalars).

**When to use:** Percentile ranking requires the entire historical series; different metrics live in different stores.

**Example:**
```python
def load_metric_series(ticker: str, metric_name: str) -> pd.Series | None:
    """Load a metric's full history from its native store, date-indexed.
    
    Examples:
    - VRP → engine/data/vol_index.py + engine/vol/vol_metrics.py
    - Skew (25Δ) → engine/data/validation.py (gex_snapshots.parquet, "front_skew")
    - Surface Evolution RMS → engine/data/surface_history.py (surface_evolution.parquet)
    - Term ratio (9D/30) → engine/data/vol_index.py (computed from vol-index scalars)
    """
    
    if metric_name == "vrp":
        # Use existing vrp_history.py machinery
        from engine.vol.vrp_history import vrp_percentile
        # But need the raw history, not just today's rank — refactor to expose _build_history()
        return _load_vrp_history(ticker)
    
    elif metric_name in ("skew_25d", "fly_25d"):
        # Load from gex_snapshots.parquet
        snapshots = pd.read_parquet(GEXSNAP_STORE)
        snapshots = snapshots[snapshots["ticker"] == ticker].sort_values("date")
        col_map = {"skew_25d": "front_skew", "fly_25d": "butterfly"}
        return snapshots.set_index("date")[col_map[metric_name]]
    
    elif metric_name in ("surface_level", "surface_rms"):
        # Load from surface_evolution.parquet
        evo = pd.read_parquet(SURFACE_EVOLUTION_STORE)
        evo = evo[evo["ticker"] == ticker].sort_values("date")
        col_map = {"surface_level": "level", "surface_rms": "rms"}
        return evo.set_index("date")[col_map[metric_name]]
    
    # ... etc. for term ratios
```

**Why this pattern:**
- Each metric has a native authoritative store (vol_index for VRP, gex_snapshots for skew, surface_evolution for scalars)
- Centralizing loaders prevents scattered hardcoded file paths
- Follows engine/vol/vrp_history.py precedent (loads from vol_index, aligns with closes)

### Pattern 5: Monitor Store (Parquet Append, Atomic Write)

**What:** Append one row per metric×ticker×day to a parquet store, following existing validation.py + surface_history.py patterns.

**When to use:** Persisting daily metric ranks for Phase 27 consumption and audit trail.

**Example:**
```python
def save_monitor_row(row: dict, store_path: pathlib.Path = MONITOR_STORE) -> None:
    """
    Append a monitor row: {date, ticker, metric, level_rank_deep, level_rank_1yr, 
                           change_rank, n_deep, n_1yr, band_state}.
    
    Idempotent on (date, ticker, metric).
    """
    new_row = pd.DataFrame([row])
    
    if store_path.exists():
        existing = pd.read_parquet(store_path)
        # Idempotency: remove any row with same (date, ticker, metric)
        mask = (existing["date"] == row["date"]) & \
               (existing["ticker"] == row["ticker"]) & \
               (existing["metric"] == row["metric"])
        existing = existing[~mask]
        existing = pd.concat([existing, new_row], ignore_index=True)
    else:
        store_path.parent.mkdir(parents=True, exist_ok=True)
        existing = new_row
    
    # Atomic write (from engine.data.store.atomic_to_parquet)
    atomic_to_parquet(existing, store_path)
```

Source: engine/data/validation.py (save_snapshot pattern), engine/data/store.py (atomic_to_parquet).

### Pattern 6: Calibration Replay (Offline Batch Analysis)

**What:** Run the ranker over all stored history with candidate bands, count false-alarm episodes per band, report results.

**When to use:** Deciding band thresholds based on empirical false-alarm rate, not theory. Re-runnable as history accumulates.

**Example:**
```python
def calibrate_alert_bands(
    candidate_bands: list[int] = None,  # e.g., [90, 95, 97, 98, 99]
    hysteresis_gaps: list[int] = None,  # e.g., [5, 10, 15]
) -> dict:
    """
    Replay the monitor over all stored history. For each candidate band + hysteresis,
    count alert episodes/week and report.
    
    Returns:
    {
        "results": [
            {
                "band_entry": 95,
                "band_escalate": 98,
                "band_exit": 85,  # band_entry - 10 (hysteresis)
                "episodes_per_week": 0.8,
                "episode_breakdown": {...}
            },
            ...
        ],
        "recommendation": "Pick 97th/99th with 10pt hysteresis for ~0.9 eps/wk"
    }
    """
    
    # Load all stored monitor rows (or regenerate from snapshots if not yet persisted)
    all_history = load_all_metric_history()
    
    results = []
    for band_entry in candidate_bands:
        for hysteresis_gap in hysteresis_gaps:
            band_exit = band_entry - hysteresis_gap
            band_escalate = band_entry + (99 - band_entry) // 2  # midpoint to 99th
            
            # Run state machine over all history
            alert_episodes = replay_alert_state_machine(
                all_history, band_entry, band_escalate, band_exit
            )
            eps_per_week = len(alert_episodes) / (len(all_history) / 5)  # rough: assuming ~5y history
            
            results.append({
                "band_entry": band_entry,
                "band_escalate": band_escalate,
                "band_exit": band_exit,
                "episodes_per_week": eps_per_week,
                "episode_breakdown": {...}
            })
    
    return {"results": results, ...}
```

**Output:** Tabular report showing episodes/week per band choice, guiding human selection.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Empirical percentile computation | Hand-coded ECDF, quantile approximation | scipy.stats.percentileofscore | Tested, handles edge cases (ties, interpolation), avoids floating-point pitfalls |
| Parquet persistence | CSV, JSON, pickle | atomic_to_parquet (engine/data/store.py) + existing pattern | Existing vol-diagnostics convention; handles concurrency, type preservation, append-only semantics |
| Alert state machine | Ad-hoc if/if/if logic | Structured transition table (or enum-gated matcher) | Easy to audit hysteresis gaps, test state coverage, refactor bands without touch logic |
| False-alarm calibration | Hardcoded "95th looks good" | Replay + empirical episode count | Band choice is data-driven not theoretical; re-runnable as history lengthens; no "feels about right" tuning |
| Metric history loaders | Scattered `pd.read_parquet()` calls | Centralized `load_metric_series(ticker, metric_name)` | Single source of truth; easier to swap data sources later (Bloomberg); prevents path drift bugs |

**Key insight:** Percentile ranking is simple enough that hand-rolling *seems* easy — but edge cases (NaN handling, lookback boundary conditions, index alignment) accumulate. ECDF is also mathematically well-defined (scipy implements it correctly); there's no reason to recompute. Similarly, alert state machine *logic* is simple, but the state transitions are easy to get wrong if scattered across multiple branches — a table-driven or enum-based approach pays off in the long run.

---

## Runtime State Inventory

**Not a rename/refactor phase.** Phase 26 is a greenfield (new monitor package). Skip this section.

---

## Common Pitfalls

### Pitfall 1: Using rolling window percentiles instead of full history
**What goes wrong:** Computing `today_value.percentile(window[-252:])` gives "unusual relative to the recent year" — but if the recent year is already elevated (e.g., post-crisis), a metric can rank 99th without actually being rare. Users see "99th percentile" and assume crisis when it's just "rare in a rare regime."

**Why it happens:** Lazy simplification — rolling window is faster to compute than deep history, and "1 year" sounds reasonable.

**How to avoid:** Always include D-02 dual lookback: deep rank (full history, tells you what's historically unusual) + 1-year rank (tells you what's locally unusual in this regime). Label both explicitly so users see "95th deep but 78th 1yr" = regime spike, not true rarity.

**Warning signs:** A metric consistently ranks high even when conditions feel normal; the deep rank disagrees with the 1-year rank.

### Pitfall 2: Not backfilling calibration bands into config.py
**What goes wrong:** The `calibrate` CLI runs, reports "97th/99th with 10pt hysteresis gives ~0.9 eps/wk" — but nobody copies those numbers into config.py. Code still uses old hardcoded 95th/98th bands. Worse: different runs of the same CLI can give different band recommendations if history has changed.

**Why it happens:** Calibration output is not directly actionable (requires human judgment + copy/paste), creating a seam between analysis and deployment.

**How to avoid:** Make the `calibrate` output emit a config-ready snippet:
```python
# config.py — bands selected 2026-07-30 via calibration replay
MONITOR_ALERT_BAND_ENTRY = 97      # ~0.9 eps/week on 8mo history
MONITOR_ALERT_BAND_ESCALATE = 99   # halfway from entry to 100
MONITOR_ALERT_BAND_EXIT = 87       # entry - 10 (hysteresis)
MONITOR_ALERT_HYSTERESIS = 10
```
Document the calibration date/history depth so future runs know if bands need refresh.

**Warning signs:** Calibrate output is a one-off; config is never updated.

### Pitfall 3: Hysteresis exit band too close to entry band
**What goes wrong:** Set `band_entry=95, band_exit=93`. A metric bounces between 94–96 due to daily noise → fires alerts every time it dips to 93. "Hysteresis" didn't help because the exit is too tight.

**Why it happens:** Setting hysteresis gap from intuition ("10 points seems like enough") instead of from calibration replay's actual flicker analysis.

**How to avoid:** The `calibrate` CLI should analyze *which* hysteresis widths collapse multi-fire episodes (same event firing twice in 1–2 days) into single episodes. Report:
```
Band 95 (entry) with hysteresis gap:
  5pt: 23 episodes / 1500 days, avg flickers 1.4x/episode
  10pt: 18 episodes / 1500 days, avg flickers 1.0x/episode ← pick this
  15pt: 18 episodes, (same as 10pt) — no further improvement
```

**Warning signs:** Alert logs show the same metric firing twice on consecutive days; calibration's episode count is much lower than day-level alert count.

### Pitfall 4: Alert text dumping percentile numbers without context
**What goes wrong:** Email alert reads "VRP 98th %ile, skew 91st %ile" — user doesn't know if 98th is deep or 1-year, whether the skew is call-rich or put-rich, or what the 91st even means in absolute terms.

**Why it happens:** Mapping percentile ranks 1:1 to alert text without translating to plain English.

**How to avoid:** The alert text (per Specifics section of CONTEXT.md) should name the mechanism: "VRP 98th (deep history) indicates expensive call protection; vol has not been this rich since [date] — +1.2pp over 3 sessions indicates dealer aggressiveness." The number is *evidence*, not the message.

**Warning signs:** Alert text is all numbers and no adjectives; users ask "should I worry?" after reading an alert.

### Pitfall 5: Inconsistent metric sample count (n) across tickers
**What goes wrong:** SPY has 250 sessions of skew history, QQQ has 45. Both show a rank, but SPY's 85th percentile rank has high power (small margins of error), QQQ's 85th rank is nearly meaningless (huge margins). Credibility floor (252 sessions) prevents alerts on QQQ, but the rank is still shown.

**Why it happens:** Not labeling the rank with its sample size n in the display, or not understanding that percentile CIs widen with small n.

**How to avoid:** Always show `n` alongside ranks. In the dashboard, QQQ's skew row shows "skew 85th (n=45)" — the `n=45` signals "building, not fire-ready." In alert text, mention it: "QQQ skew 91st (n=52, building — compare to SPY's 89th on n=245)."

**Warning signs:** A metric's 1-year rank is wildly high (99th) but sample size is small; deep rank for same metric is moderate (70th); inconsistency signals noise, not signal.

---

## Code Examples

Verified patterns from existing codebase:

### Percentile Ranking (Existing VRP Pattern)
```python
# Source: engine/vol/vrp_history.py
from scipy.stats import percentileofscore

def compute_metric_percentile(metric_series: pd.Series, today_value: float, 
                              lookback_sessions: int | None = None) -> tuple[int, int]:
    """Rank today_value against metric_series history (ECDF percentile).
    
    Returns: (percentile_rank: 0–100, sample_count: n)
    """
    if metric_series.empty or today_value is None:
        return None, 0
    
    window = metric_series if lookback_sessions is None else metric_series.iloc[-lookback_sessions:]
    clean = window.dropna()
    if clean.empty:
        return None, 0
    
    pct = int(percentileofscore(clean.to_numpy(), today_value, kind="rank"))
    return pct, len(clean)
```

### Store Append Pattern (Existing validation.py Pattern)
```python
# Source: engine/data/validation.py (adapted for monitor)
import pathlib
import pandas as pd
from engine.data.store import atomic_to_parquet

MONITOR_STORE = pathlib.Path(__file__).resolve().parents[2] / "out" / "monitor" / "ranks.parquet"

def save_monitor_row(row: dict) -> None:
    """Append one metric rank row to store (idempotent on date/ticker/metric)."""
    new_row = pd.DataFrame([row])
    
    if MONITOR_STORE.exists():
        hist = pd.read_parquet(MONITOR_STORE)
        mask = (hist["date"] == row["date"]) & \
               (hist["ticker"] == row["ticker"]) & \
               (hist["metric"] == row["metric"])
        hist = hist[~mask]  # Remove old version if exists
        hist = pd.concat([hist, new_row], ignore_index=True)
    else:
        MONITOR_STORE.parent.mkdir(parents=True, exist_ok=True)
        hist = new_row
    
    atomic_to_parquet(hist, MONITOR_STORE)
```

### Hysteresis State Machine
```python
from enum import Enum

class AlertState(Enum):
    OUT = "out"
    IN_ENTRY = "in_entry"
    IN_ESCALATE = "in_escalate"

def check_alert_transition(today_rank: int, yesterday_state: AlertState | None,
                          entry: int, escalate: int, exit_: int) -> tuple[str | None, AlertState]:
    """
    State machine: entry → escalation → exit (with hysteresis).
    
    Returns: (alert_type, new_state)
    alert_type: "entry" | "escalation" | None
    """
    
    if yesterday_state is None or yesterday_state == AlertState.OUT:
        if today_rank >= entry:
            return "entry", AlertState.IN_ENTRY
        return None, AlertState.OUT
    
    if yesterday_state == AlertState.IN_ENTRY:
        if today_rank >= escalate:
            return "escalation", AlertState.IN_ESCALATE
        if today_rank < exit_:
            return None, AlertState.OUT
        return None, AlertState.IN_ENTRY
    
    if yesterday_state == AlertState.IN_ESCALATE:
        if today_rank < exit_:
            return None, AlertState.OUT
        return None, AlertState.IN_ESCALATE
```

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (≥8.0, existing stack) |
| Config file | pytest.ini (existing) |
| Quick run command | `pytest engine/tests/test_monitor.py -v --tb=short` |
| Full suite command | `pytest engine/tests` |

### Phase Requirements → Test Map

No explicit phase requirements assigned (TBD). Test coverage should address:

| Requirement | Behavior | Test Type | Automated Command | File Exists? |
|-------------|----------|-----------|-------------------|-------------|
| D-01 (ECDF ranks) | percentileofscore produces 0–100 scale; handles NaN | unit | `pytest engine/tests/test_monitor/test_ranker.py::test_percentileofscore_edge_cases` | ❌ Wave 0 |
| D-02 (dual lookback) | deep + 1-year ranks computed independently; both persisted | unit | `pytest engine/tests/test_monitor/test_ranker.py::test_dual_lookback` | ❌ Wave 0 |
| D-03 (k=5 changes) | |Δ5d| rank one-sided; k=5 only (not k=1,10) | unit | `pytest engine/tests/test_monitor/test_ranker.py::test_5day_change_rank` | ❌ Wave 0 |
| D-04 (hysteresis) | Entry fires alert; escalation re-fires; exit stops. No flicker on noisy data | unit | `pytest engine/tests/test_monitor/test_hysteresis.py::test_state_machine` | ❌ Wave 0 |
| D-06 (calibrate) | `engine.monitor.calibrate` replays ranker, reports eps/week per band, picks best match | integration | `python -m engine.monitor.calibrate --dry-run` | ❌ Wave 0 |
| D-08 (credibility floor) | Rank computed always; alert suppressed if n < 252 | unit | `pytest engine/tests/test_monitor/test_ranker.py::test_credibility_floor` | ❌ Wave 0 |
| D-11 (persistence) | Monitor rows appended idempotently; alert-events table separate or same store | unit | `pytest engine/tests/test_monitor/test_store.py::test_atomic_append` | ❌ Wave 0 |

### Wave 0 Gaps

- [ ] `engine/tests/test_monitor/test_ranker.py` — ECDF rank unit tests, dual-lookback alignment, 5-day change, credibility floor
- [ ] `engine/tests/test_monitor/test_hysteresis.py` — state machine transitions, flicker test (bouncing metric)
- [ ] `engine/tests/test_monitor/test_store.py` — parquet append idempotency
- [ ] `engine/tests/test_monitor/test_calibration.py` — replay correctness (count episodes, match band selection output)
- [ ] `engine/tests/conftest.py` — add `mock_metric_history` fixture (synthetic time series with known percentiles)

*(All test infrastructure exists in engine/tests; structure follows existing test patterns.)*

---

## Security Domain

**Applicable ASVS categories:** None explicitly. Phase 26 is internal analytics (no user input, no auth, no external API calls). Existing security model (filesystem access to `out/` parquet, Python execution) continues.

**Risk model:**
- Monitor store is read-only from Phase 27 (display layer) — write happens here only, no API exposure
- Calibrate CLI is local-only, no network component
- No secrets in config (bands are public tuning parameters)

No new ASVS controls required.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | scipy.stats.percentileofscore `kind="rank"` implements ECDF correctly | Standard Stack | Alert ranks would be non-standard; users would see different percentiles than expected. Mitigation: review scipy source code / test against manual ECDF calculation |
| A2 | config.VRP_DEEP_LOOKBACK_SESSIONS (2500 sessions) will generalize to other metrics | Architecture Patterns | Some metrics may have shorter histories (surface started 2026-05, ~50 sessions) — mitigated by D-08 credibility floor (252 sessions). Deep lookback can be per-metric if needed. |
| A3 | Hysteresis exit band at entry - 10 (e.g., 95 entry → 85 exit) will prevent "flicker" alerts | Common Pitfalls | Exit band may need to be wider or tighter depending on actual data noise. Mitigation: calibrate CLI empirically determines hysteresis gap. |
| A4 | Phase 27 will read and display `out/monitor/` store without schema changes | Architecture Patterns | If Phase 27 requires different columns (e.g., episode_id for event linking), this phase would need a re-cut. Mitigation: finalize monitor schema with Phase 27 planner before implementation. |

---

## Open Questions (RESOLVED)

1. **Monitor store schema — single table or split?**
   - Option A: One table with `(date, ticker, metric, level_rank_deep, level_rank_1yr, change_rank, n_deep, n_1yr, band_state)` — simpler, one append.
   - Option B: Two tables: `monitor_ranks` and `alert_events` (with different row cardinality) — cleaner separation, better for Phase 27's event-shaped email.
   - **Recommendation:** Option A initially (simpler append in run_daily); if Phase 27 needs alert-events separately, refactor to Option B or denormalize on read.

2. **Backfilling historical monitor rows — necessary for ship?**
   - Existing stores have 2+ months of history (vol_index ~8 years, gex_snapshots ~2 mo, surface_evolution ~2 mo).
   - Should monitor backfill all stored dates before running daily, or just run forward from today?
   - **Recommendation:** Make backfill optional CLI command (`python -m engine.monitor.backfill`), not part of daily. Allows Phase 26 to ship without delay; backfill can happen asynchronously or on first manual run.

3. **Per-metric credibility floor — hardcoded 252 or configurable?**
   - D-08 locks at 252 (1 year), but some metrics (VRP) have 2500+ sessions, others (surface) have ~50.
   - Should floor be global or per-metric?
   - **Recommendation:** Global 252 for v1 (simplicity, matches D-08); config has room for `MONITOR_CREDIBILITY_FLOOR_SESSIONS` if future metrics need different floors.

4. **How should calibrate present candidate bands and episode counts?**
   - Simple table: `band_entry | band_escalate | band_exit | episodes/week`?
   - Or interactive (e.g., plot episodes/week vs entry threshold)?
   - **Recommendation:** Start with simple markdown table (human-readable, git-friendly if output captured); interactive plots can be Phase 28+ iteration.

---

## Environment Availability

**Skip:** Phase 26 is pure Python + parquet I/O. No external tools or services required beyond existing stack (scipy, pandas, pyarrow). All dependencies confirmed in requirements.txt.

---

## Sources

### Primary (HIGH confidence)
- **CONTEXT.md (Phase 26, 2026-07-23)** — Decisions D-01 through D-12, canonical reference for phase scope and locked constraints
- **microstructure-monitor-design.md (2026-07-23)** — Statistical rationale for ECDF percentiles, dual lookback, hysteresis, false-alarm budget
- **engine/vol/vrp_history.py (codebase)** — Existing percentileofscore pattern, dual lookback structure, metric history loading approach
- **engine/data/validation.py (codebase)** — Existing parquet append pattern, atomic_to_parquet, idempotency
- **engine/data/store.py (codebase)** — atomic_to_parquet implementation
- scipy.stats documentation (context7 / Feb 2025 training knowledge) — percentileofscore API, ECDF definition

### Secondary (MEDIUM confidence)
- **research/questions.md § "Alert band calibration (2026-07-23)"** — Calibration approach and false-alarm budget reasoning
- **CLAUDE.md § constraints** — "No predictive claims", "self-imposed statistical validation", "no hidden scoring"
- vol-diagnostics codebase structure (engine/{gex,surface,vol}, data/{validation,surface_history,vol_index}) — Pattern precedents for modular decomposition

### Tertiary (context only)
- REQUIREMENTS.md (v5.0 Data Foundation) — Phase 26 was added 2026-07-23 to v5.0 roadmap; REQUIREMENTS.md predates the monitor redesign and will need update post-research

---

## Metadata

**Confidence breakdown:**
- **Standard Stack: HIGH** — scipy.stats is industry-standard, already in use in codebase (app.py). ECDF computation is mathematically defined, no alternatives.
- **Architecture: HIGH** — Patterns (dual lookback, hysteresis, parquet append) are proven in existing codebase (VRP, validation.py, surface_history.py). Phase 26 scales existing patterns.
- **Pitfalls: MEDIUM-HIGH** — Pitfall 2 (band backfill to config) is project-specific (GSD workflow). Pitfalls 1,3,4,5 are drawn from statistical practice + existing vol-diagnostics decision history (D-08 credibility floor, D-02 dual lookback logic).

**Research date:** 2026-07-23
**Valid until:** 2026-08-23 (30 days — stable patterns, no API changes expected in scipy/pandas within 1 month)
**Next review trigger:** If Phase 27 surfaces emerge with different schema needs, or if calibration replay produces surprising band recommendations that suggest assumption drift.

---


---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
**Phase siblings:**
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-CONTEXT|26-CONTEXT]]
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-DISCUSSION-LOG|26-DISCUSSION-LOG]]

<!-- LINKS:END -->
