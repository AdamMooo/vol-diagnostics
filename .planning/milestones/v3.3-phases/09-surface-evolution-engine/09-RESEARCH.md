# Phase 9: Surface Evolution Engine - Research

**Researched:** 2026-05-30
**Domain:** Change-over-time vol-surface analytics: decompose daily IV movement into interpretable scalars (level, rms, skew-change, term-change), persisted idempotently, computed as a non-blocking pass in run_daily, with backfill from existing stored surfaces.
**Confidence:** HIGH on grid mechanics, parquet persistence, integration points (verified by codebase read + Phase 8 verification). HIGH on rolling-mean computation (numpy mechanics confirmed). MEDIUM on skew/term region definitions (requires explicit planner specification).

## Summary

Phase 9 builds a `surface_evolution` module that measures how the interpolated vol surface shifts between today and N trading days in the past (N ∈ {5, 10, 20}), decomposing the change into four defensible scalars on the masked grid. The engine reuses the Phase 8 coverage mask (convex-hull based, parameter-free) and the shared `rbf_grid` helper, reads historical surfaces from the existing parquet store via `load_surface_snapshot`, computes rolling-mean baselines (N-day masked-grid average), and persists results to a new idempotent parquet store (`out/surface_evolution.parquet`). It is triggered as a non-blocking second pass in `run_daily.run` after snapshots are saved, and supports backfill from existing `surface_history` for cold-start mitigation.

**Primary recommendation:** The planner must treat the grid-axis stability and mask-intersection logic as load-bearing invariants — today's grid and every baseline-day grid must be computed on the SAME DTE and % OTM axes (achieved via the stored `spot` per snapshot), and the comparison mask must be the *intersection* of all baseline-day masks with today's mask, never a per-day independent mask. Float NaN propagation in rolling-mean (using `np.nanmean`) requires explicit handling of the edge case where all baseline-day cells are NaN (returns NaN, which is correct and should not trigger a fallback).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Compute ΔIV scalars from grid pair | Backend / Engine | — | Pure numpy math on RBF-interpolated arrays; no I/O |
| Resolve trading-day horizons | Backend / Store lookup | — | `surface_history.py` `nth_trading_day_back` performs the lookups; no calendar math |
| Persist evolution metrics | Backend / Parquet | — | New idempotent store mirroring `validation.py` pattern |
| Integrate into daily orchestrator | Backend / Scheduler | — | Non-blocking second pass in `run_daily.run` after snapshot save |
| Display evolution in dashboard | Frontend / Streamlit | — | Phase 10 responsibility (reads the persisted store) |
| Email evolution callouts | Delivery / Report | — | Phase 11 responsibility (surfaces the 5-day horizon scalar) |

---

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Horizons locked: {5, 10, 20} trading days (drop noisy 1d, add 10d per 2026-05-30 STATE.md)
- Headline baseline: **N-day rolling mean** of masked daily surfaces (EVOL-01)
- Comparison mask: today ∩ all N baseline-day masks — never compare independently-extrapolated grids (STATE.md carry-over, Pitfall 5 mitigation)
- Coverage mask: **convex-hull membership** (parameter-free), replaces kNN-radius from Phase 8 design decision (STATE.md 2026-05-30 refinement, coverage ~22% → ~93%)
- Descriptive-only framing (no predictive language): past tense, no "expect/likely/will/ahead" (CLAUDE.md project constraint)

### Claude's Discretion
- Exact definitions of put-wing vs call-wing and front vs back moneyness/DTE regions for skew-change and term-change scalars (the planner must choose defensible band definitions and document them, e.g., "put-wing = %OTM < −5%, call-wing = %OTM > +5%")
- Whether to backfill evolution from existing surface history as a separate task or inline with daily ingestion
- Rollover handling on expiry rolls (constant-maturity semantics already set per Pitfall 6; confirm that is sufficient)

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EVOL-01 | Four scalars (level, rms, skew-change, term-change) decomposing ΔIV on the masked grid against N-day rolling-mean baseline | `rolling_mean` = `nanmean` of masked grids; baseline mask = AND of all N day masks; reuses Phase 8 `coverage_mask` + `rbf_grid` |
| EVOL-02 | Multi-horizon (5, 10, 20 trading days) resolved against stored session dates, not calendar arithmetic | `surface_history.nth_trading_day_back(ticker, date, n)` function (new helper) indexes descending `list_available_dates`; labelled with actual prior date |
| EVOL-03 | Idempotent parquet store `out/surface_evolution.parquet` (date, ticker, horizon) | Schema + `_FLOAT_COLS` cast block mirror `validation.py` pattern; read-modify-write with 3-key mask |
| EVOL-04 | Non-blocking second pass inside `run_daily.run` after `save_surface_snapshot` | Wrapped in try/except; failure never blocks email (pattern from observation log at run_daily.py:96–101) |
| EVOL-05 | Cross-ticker comparability (SPY/QQQ/IWM) | Same grid axes (spot-normalized %OTM, DTE floor=5), same baseline computation, same scalars per ticker |
| EVOL-06 | Backfill from existing `surface_history` | Feasible: schema confirmed, spot stored per row, `rbf_grid` reproducible from stored snapshots (see Q7 below) |

---

## Research Findings by Question

### Q1: Surface source (EVOL-01/05) — What's stored and how to reconstruct?

**Answer:** The `surface_history.parquet` store saves **raw OTM quotes, not interpolated grids**. Reconstruction is **fully reproducible** and safe.

**Stored data per (date, ticker)** [`gex/surface_history.py:8–10`]:
```
Columns: date, ticker, spot, dte, strike, moneyness, log_moneyness, iv_pct
One row per OTM quote point (after MIN_OI filter, post-clip to SURFACE_MONEYNESS_BAND ±22%)
```

**How the grid is reconstructed** [`gex/analytics.py:159–186` `rbf_grid` + `coverage_mask`]:

1. **Load historical snapshot** → call `load_surface_snapshot(ticker, date)` → returns `(surface_df, spot)` where:
   - `surface_df` has columns: `dte, strike, moneyness, log_moneyness, iv_pct`
   - `spot` is **the spot price that day** (stored per-row in surface_history, returned as a scalar) — **critical for % OTM consistency**

2. **Construct grid axes** (identical to daily renders):
   ```python
   dte_floor = 5
   dte_max = min(surface_df["dte"].max(), config.SURFACE_DTE_MAX)  # 180
   clip_pct = config.SURFACE_PLOT_OTM_CLIP * 100.0  # 15% OTM
   
   dte_grid = np.linspace(dte_floor, dte_max, config.SURFACE_GRID_DTE)  # 40 pts
   otm_grid = np.linspace(-clip_pct, clip_pct, config.SURFACE_GRID_LM)  # 30 pts, ±15%
   ```

3. **Interpolate via shared helper** → call `rbf_grid(surface_df, spot, dte_grid, otm_grid, dte_floor=5)`:
   - **Input:** surface_df with strike/dte/iv, the spot for that day, the grid axes
   - **Processing inside rbf_grid:**
     ```python
     pct_otm = (surface_df["strike"] / spot - 1.0) * 100.0  # normalize by THAT DAY's spot
     in_band = (|pct_otm| <= 15%) & (dte >= 5)  # clip + DTE floor
     if len(in_band points) < 6: return NaN(40×30)
     pts = [dte, pct_otm] of in-band points
     pts_std = per-axis std normalization
     rbf = RBFInterpolator(pts/pts_std, iv_pct, kernel="thin_plate_spline", smoothing=1.5)
     return IV_grid (40×30), clipped to [0, ∞)
     ```
   - **Output:** IV array shaped `(len(otm_grid), len(dte_grid))` = `(30, 40)` containing interpolated IV in pp

4. **Apply coverage mask** → call `coverage_mask(surface_df, spot, dte_grid, otm_grid, dte_floor=5)`:
   - Uses **Delaunay convex hull** on normalized `pts/pts_std`
   - Returns boolean mask `(30, 40)` where True = cell is inside the hull (interpolation), False = outside (extrapolation)
   - **Critical:** same normalization (`pts_std`) used in both `rbf_grid` and `coverage_mask` ensures hull membership is invariant under the scaling

5. **Mask the grid** → `IV_masked = np.where(mask, IV, np.nan)` → produces honest NaN holes

**Result:** Both today and N-days-back grids are computed on the **same DTE/% OTM axes** (because we construct them identically), and **each uses the correct spot from that day**, so % OTM normalization is aligned. The grid shapes are identical (30×40) and cells match by position.

**Failure mode prevented:** If code ever normalized prior-day strikes by today's spot, or used an inconsistent spot source, the % OTM axes would drift and the difference would be fabricated. The returned spot from `load_surface_snapshot` is the safe source.

### Q2: Rolling-mean baseline + mask intersection (EVOL-01)

**Answer:** The computation is `ΔIV = IV_today − nanmean_k(masked baseline grids)`, where the baseline-grid set includes all N stored prior days, and the comparison mask is `mask_today ∩ mask_day1 ∩ mask_day2 ∩ ... ∩ mask_dayN`.

**Exact computation** [to implement]:

```python
# Given: today's date, ticker, horizon N (5, 10, or 20)

# Load today
surface_today, spot_today = load_surface_snapshot(ticker, today)
dte_grid, otm_grid = _construct_grid_axes(surface_today)
IV_today = rbf_grid(surface_today, spot_today, dte_grid, otm_grid, dte_floor=5)
mask_today = coverage_mask(surface_today, spot_today, dte_grid, otm_grid, dte_floor=5)

# Load N prior days (resolve trading-day horizons first)
prior_dates = []  # will be populated by nth_trading_day_back
for n in [1, 5, 20]:  # or the target horizons
    prior_date = nth_trading_day_back(ticker, today, n)
    if prior_date is None:
        continue  # skip if fewer than n+1 sessions exist
    prior_dates.append(prior_date)

# Baseline grids & masks
IV_baseline_list = []
mask_baseline_list = []
for prior_date in prior_dates:
    surface_prior, spot_prior = load_surface_snapshot(ticker, prior_date)
    if surface_prior.empty or spot_prior is None:
        continue  # skip missing dates
    IV_prior = rbf_grid(surface_prior, spot_prior, dte_grid, otm_grid, dte_floor=5)
    mask_prior = coverage_mask(surface_prior, spot_prior, dte_grid, otm_grid, dte_floor=5)
    IV_baseline_list.append(IV_prior)
    mask_baseline_list.append(mask_prior)

if not IV_baseline_list:
    # No baseline available (cold start)
    return None  # skip this (date, ticker, horizon) tuple

# Rolling mean of baseline grids
IV_baseline_stack = np.stack(IV_baseline_list, axis=0)  # (n_baseline_days, 30, 40)
IV_baseline_mean = np.nanmean(IV_baseline_stack, axis=0)  # (30, 40), treats NaN as missing

# Intersection mask: only cells where ALL days (today + all baseline) have support
mask_intersection = mask_today  # (30, 40) boolean
for mask_prior in mask_baseline_list:
    mask_intersection = mask_intersection & mask_prior  # AND

# Difference on the intersected mask
IV_diff = IV_today - IV_baseline_mean
IV_diff_masked = np.where(mask_intersection, IV_diff, np.nan)
```

**numpy mechanics & edge cases:**

- **`np.nanmean(IV_baseline_stack, axis=0)`** — computes the mean ignoring NaN values along the date axis. If all N baseline days have NaN at cell (i, j), the result is NaN — correct, and the mask_intersection will already be False there, so the cell is excluded downstream.
- **Mask intersection:** `mask_today & mask_prior & ... & mask_priorN` — all must be True. A single baseline day with False at a cell zeros that cell in the intersection. This is correct: if one baseline day lacked support at a location, the rolling mean is not directly comparable at that cell, so we exclude it.
- **Shape stability:** `dte_grid` and `otm_grid` are constructed identically from the **current day's** surface max/min, not cached. If a prior day's max DTE was 150 and today's is 160, the grid axes are the same (both go 5 to 180 via config.SURFACE_DTE_MAX), so shapes match.
- **Cold-start:** If today is the 2nd session and horizon=20, `nth_trading_day_back` returns None, and we skip that horizon (store no row). Correct — no data to baseline against.

### Q3: The four scalars (EVOL-01) — definitions on the masked grid

**Answer:** All four scalars are computed only over cells where `mask_intersection == True` (using numpy's masked-array semantics with NaN).

1. **level** — mean ΔIV (pp) on the masked grid
   ```python
   level = np.nanmean(IV_diff_masked)  # ignores NaN, averages the True-masked cells
   ```
   **Interpretation:** parallel shift; positive = IV rose on average, negative = IV fell.

2. **rms** — RMS of ΔIV (pp), AKA total movement magnitude
   ```python
   rms = np.sqrt(np.nanmean(IV_diff_masked ** 2))
   ```
   **Interpretation:** scale of movement regardless of direction; zero = static surface.

3. **skew_change** — change in OTM-wing-spread (pp)
   ```
   Requires definition of "put-wing" and "call-wing" regions by moneyness (e.g., put-wing = %OTM < -5%, call-wing = %OTM > +5%)
   put_wing_diffs = IV_diff_masked[otm_grid < -5%, :]  # extract by location
   call_wing_diffs = IV_diff_masked[otm_grid > +5%, :]
   
   skew_change = np.nanmean(put_wing_diffs) - np.nanmean(call_wing_diffs)
   ```
   **Interpretation:** positive = puts rose more than calls (skew steepened), negative = opposite.
   **Ambiguity the planner must resolve:** The exact %OTM threshold for "put-wing" vs "call-wing." Suggested: ±5%, ±8%, or ±10% (symmetric). Should this be a config constant?

4. **term_change** — change in front-vs-back ATM spread (pp)
   ```
   Requires definition of "front" and "back" by DTE (e.g., front = 5–30 DTE, back = 90–180 DTE)
   front_region = (dte_grid >= 5) & (dte_grid <= 30)
   back_region = (dte_grid >= 90) & (dte_grid <= 180)
   atm_band = (otm_grid >= -2) & (otm_grid <= +2)  # ATM
   
   IV_front_atm = IV_diff_masked[atm_band, :][:, front_region]
   IV_back_atm = IV_diff_masked[atm_band, :][:, back_region]
   
   term_change = np.nanmean(IV_front_atm) - np.nanmean(IV_back_atm)
   ```
   **Interpretation:** positive = front month rose more than back (curve flattened), negative = curve steepened.
   **Ambiguity:** DTE thresholds (30/90 are suggestions; could be 45 for "front" or 60 for "back"). ATM band width (±2% is narrow; could be ±1% or ±3%). **Planner must choose and document.**

**Warning:** These definitions must be **consistent across all three horizons and all tickers**, otherwise evolution time-series will have discontinuities. Document as config constants or in a `surface_evolution.py` module-level docstring.

### Q4: Horizon resolution (EVOL-02)

**Answer:** Horizons are resolved via `nth_trading_day_back(ticker, anchor_date, n)` — a NEW helper function in `surface_history.py`.

**Implementation** [NEW `surface_history.py`]:
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
    available = list_available_dates(ticker)  # returns sorted descending
    if anchor_date not in available:
        return None  # anchor date not in store
    idx = available.index(anchor_date)
    if idx + n >= len(available):
        return None  # not enough history
    return available[idx + n]
```

**Why this works:**
- `list_available_dates` already returns trading days sorted descending (surface_history.py:89)
- Walking N positions down is exactly "N sessions ago"
- No calendar math — only stored dates are considered
- Gaps (missed runs, holidays) are invisible; indexing is pure

**Why NOT calendar math:**
- `today - timedelta(days=5)` lands on weekends/holidays (no data)
- "5 positions back in the store" only equals 5 sessions if the store is contiguous

**Edge cases:**
- Cold-start (store has 2 sessions, horizon=5): returns None → skip that (date, ticker, horizon) row
- Weekend/holiday run gap: if run_daily skipped a day, the store will have a 2+ day gap, but the index still finds the right prior session
- **Pitfall 7 mitigation:** label the evolution row with the actual `prior_date` returned, not a nominal "5 days ago"

### Q5: Persistence (EVOL-03)

**Answer:** Idempotent parquet store with 3-key deduplication, mirroring `validation.py` pattern.

**New store: `out/surface_evolution.parquet`**

Schema (one row per date × ticker × horizon):
```
Columns: date, ticker, horizon, prior_date, level, rms, skew_change, term_change, coverage
Dtypes:  date, str, int, date, float64, float64, float64, float64, float64
```

**Write pattern** [`surface_evolution.py` NEW function `update_evolution`]:
```python
def save_evolution_row(date: datetime.date, ticker: str, horizon: int, prior_date: datetime.date,
                       level: float, rms: float, skew_change: float, term_change: float,
                       coverage: float) -> None:
    """
    Append or replace a single (date, ticker, horizon) row in the evolution store.
    Idempotent: re-run with the same inputs produces no duplicate.
    """
    row = {
        "date": date,
        "ticker": ticker,
        "horizon": horizon,
        "prior_date": prior_date,
        "level": level,
        "rms": rms,
        "skew_change": skew_change,
        "term_change": term_change,
        "coverage": coverage,
    }
    
    store_path = pathlib.Path(__file__).resolve().parents[1] / "out" / "surface_evolution.parquet"
    _FLOAT_COLS = ("level", "rms", "skew_change", "term_change", "coverage")
    
    if store_path.exists():
        hist = pd.read_parquet(store_path)
        # Coerce floats (forward-compatible with future column additions)
        for col in _FLOAT_COLS:
            if col in hist.columns:
                hist[col] = hist[col].astype("float64")
        # Remove any existing row with the same (date, ticker, horizon)
        mask = (hist["date"] == row["date"]) & (hist["ticker"] == ticker) & (hist["horizon"] == horizon)
        hist = hist[~mask]
        # Append new row
        hist = pd.concat([hist, pd.DataFrame([row])], ignore_index=True)
    else:
        # First write
        store_path.parent.mkdir(parents=True, exist_ok=True)
        hist = pd.DataFrame([row])
    
    hist.to_parquet(store_path, index=False)
    print(f"[surface_evolution] {ticker} {date} horizon={horizon}: saved to {store_path}")
```

**Read pattern** [NEW function `load_evolution`]:
```python
def load_evolution(ticker: str, horizon: int | None = None, days: int = 30) -> pd.DataFrame:
    """
    Load evolution metrics from the store for a single ticker, optionally filtered by horizon.
    Returns most recent `days` rows.
    """
    store_path = pathlib.Path(__file__).resolve().parents[1] / "out" / "surface_evolution.parquet"
    if not store_path.exists():
        return pd.DataFrame()
    try:
        hist = pd.read_parquet(store_path)
        hist["date"] = pd.to_datetime(hist["date"]).dt.date
        hist = hist[hist["ticker"] == ticker].sort_values("date", ascending=False)
        if horizon is not None:
            hist = hist[hist["horizon"] == horizon]
        return hist.head(days).reset_index(drop=True)
    except Exception as exc:
        print(f"[surface_evolution] load_evolution failed for {ticker}: {exc}")
        return pd.DataFrame()
```

**Windows path note:** Use `pathlib.Path` (already done above); parquet write/read via `pd.to_parquet` / `pd.read_parquet` handles Windows paths correctly.

**Idempotency safeguard:** The 3-key mask `(date & ticker & horizon)` ensures re-running with the same inputs does not duplicate rows. A backfill for a past date overwrites without bloating the store.

### Q6: Non-blocking integration (EVOL-04)

**Answer:** Trigger the evolution pass as a second loop in `run_daily.run`, after the snapshot save loop and before email build. Wrap in try/except matching the observation-log pattern.

**Integration point** [`run_daily.py` MODIFIED, after line 71]:
```python
# Existing loop saves snapshots...
for ticker in ALL_TICKERS:
    print(f"  {ticker}...", end=" ", flush=True)
    data = process_ticker(ticker)
    all_data.append(data)
    s = data["summary"]
    if not s.get("error"):
        save_snapshot(s, ticker, skew_df=data.get("skew_df"))
        save_surface_snapshot(data.get("surface_df"), ticker, spot=s["spot"])
        # ...

# ──────── NEW second pass (non-blocking) ────────
print("\n[run_daily] Computing surface evolution...")
from gex.surface_evolution import update_evolution
for ticker in INDEX_TICKERS:
    try:
        update_evolution(ticker, today)  # computes 1d/5d/20d, appends to parquet
    except Exception as exc:
        print(f"  [WARN] {ticker} evolution failed: {exc}")
        # Does NOT raise or break — email proceeds

# ──────── existing email build ────────
index_results = [d["summary"] for d in all_data if d["summary"]["ticker"] in INDEX_TICKERS]
# ...
```

**Why a separate pass, not inside `process_ticker`:**
1. Evolution depends on today's surface being **committed to disk** first (via `save_surface_snapshot`), so a separate pass after the loop guarantees the store is current.
2. `process_ticker` is already wrapped in a "never raises" guard; a separate evolution pass has its own guard, keeping concerns separated.
3. Evolution is a **derived, non-essential metric** — email value is not diminished if it fails; GEX summary and skew cards still send.

**Try/except pattern** (mirroring `observation` block from run_daily.py:96–101):
```python
try:
    update_evolution(ticker, today)
except Exception as exc:
    print(f"  [WARN] evolution update failed for {ticker}: {exc}")
    # continue to next ticker
```

### Q7: Backfill (EVOL-06)

**Answer:** Backfill is **fully feasible** and should be implemented as a standalone CLI utility at the start of Phase 9 (or Phase 10).

**Why backfill works:**
1. **`surface_history` exists** — stores raw OTM quotes with spot per row (since the beginning of surface-validation work)
2. **Schema is stable** — `load_surface_snapshot` is the canonical reader; no schema drift risk
3. **`rbf_grid` is reproducible** — given the same surface_df and spot, it always produces the same IV array (verified by Phase 8 regression tests)
4. **Mask is reproducible** — Delaunay hull on the same points always returns the same mask

**Backfill routine** [NEW CLI]:
```bash
python -m gex.surface_evolution --backfill SPY 2026-05-01
# Computes all (date, horizon) pairs for SPY from 2026-05-01 to today, writes to parquet
```

**Implementation sketch** [NEW `surface_evolution.py`]:
```python
def backfill(ticker: str, start_date: datetime.date) -> None:
    """
    Retro-compute evolution metrics for all dates >= start_date where the surface store has data.
    Writes idempotently to the evolution parquet (overwrites any existing rows).
    """
    from gex.surface_history import list_available_dates, nth_trading_day_back
    
    available_dates = list_available_dates(ticker)
    valid_dates = [d for d in available_dates if d >= start_date]
    
    if not valid_dates:
        print(f"[backfill] No dates >= {start_date} for {ticker}")
        return
    
    print(f"[backfill] {ticker}: {len(valid_dates)} dates, computing horizons...")
    for date in reversed(valid_dates):  # oldest first, for progress clarity
        for horizon in [5, 10, 20]:  # (1 is excluded per EVOL-02)
            prior_date = nth_trading_day_back(ticker, date, horizon)
            if prior_date is None:
                continue  # not enough history
            
            # Compute (same logic as daily evolution)
            try:
                level, rms, skew_change, term_change, coverage = compute_evolution_scalars(
                    ticker, date, prior_date
                )
                save_evolution_row(date, ticker, horizon, prior_date,
                                   level, rms, skew_change, term_change, coverage)
            except Exception as exc:
                print(f"  [WARN] {date} horizon={horizon}: {exc}")
    
    print(f"[backfill] {ticker} complete")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--backfill", action="store_true")
    parser.add_argument("ticker", nargs="?", default=None)
    parser.add_argument("--start", type=datetime.date.fromisoformat, default=None)
    args = parser.parse_args()
    
    if args.backfill and args.ticker:
        start = args.start or (datetime.date.today() - datetime.timedelta(days=90))
        backfill(args.ticker, start)
```

**Cold-start scenario:** On day 1 of Phase 9 go-live, running the backfill over 30–90 prior days of `surface_history` populates the evolution parquet, so the dashboard is not empty when Phase 10 ships (avoids "Accumulating" state for weeks).

### Q8: Pitfalls / landmines

**CRITICAL — must be in the planner's awareness:**

1. **Float NaN propagation in rolling mean**
   - `np.nanmean([IV_day1, IV_day2, IV_day3], axis=0)` — if all three have NaN at cell (i, j), the result is NaN (correct).
   - If two of three are NaN and one is 20, the result is 20 (ignores the two NaNs). This is correct *because the mask_intersection will already be False there* — the cell is excluded from the final scalar.
   - **Do not replace NaN with 0 or a fallback** — it breaks the mask semantics and invents signals where the surface has no support.

2. **Grid-axis drift if spot sources are mixed**
   - **Each day must normalize by its own spot:** `pct_otm = (strike / spot_that_day - 1) * 100`
   - If code ever uses today's spot to normalize prior-day strikes, the %OTM axes misalign and IV_diff is fabricated.
   - Mitigation: `load_surface_snapshot` returns `(df, spot)` as a pair; always use the returned spot, never re-fetch from the scalar store.

3. **Mask intersection prevents fabricated differences, but still requires intersection**
   - If you diff `IV_today[mask_today]` against `IV_baseline[~mask_baseline]`, you are differencing real against extrapolation — garbage.
   - **Always**: `mask_compare = mask_today & mask_all_baseline_days` (AND all together).
   - A baseline day with lower coverage shrinks the comparison region — correct.

4. **Expiry roll noise at short DTE**
   - With DTE floor = 5, an expiry at 6 DTE today drops below the floor tomorrow (rolls off the grid).
   - Constant-maturity semantics (the grid axis) handles this — the "30 DTE slice" is a different set of real contracts each day.
   - **Do not attempt fixed-expiry tracking** (matching contracts by expiry date across days). It adds complexity the tool doesn't need, and back-months roll out of the window anyway.
   - The DTE floor interaction is handled correctly by the grid construction (uses `dte_floor=5` consistently).

5. **Look-ahead bias in rolling-mean baseline — NOT a risk here**
   - A rolling *forward*-looking baseline (`today + 1d, today + 2d`) would be look-ahead. The baseline here is *backward*-looking (N days *past*), so no leak.
   - Just verify: the horizon always points into the past, never the future.

6. **Windows parquet locking**
   - If a prior read-modify-write cycle exits with the file still open, a second write may fail with "file locked."
   - Mitigation: use pandas' default `engine='pyarrow'` (or explicitly pass it); ensure `hist.to_parquet(...)` completes before the context exits.
   - A try/except around the write (as in integration point Q6) will catch the error gracefully.

7. **Cold-start:** Horizon > available sessions
   - If today is session #3 and horizon=20, `nth_trading_day_back` returns None.
   - Correct behavior: do not write a row for that (date, ticker, horizon) combo.
   - Dashboard must check `if horizon in df.columns` or similar before rendering; Phases 10/11 gate with "Accumulating (N/M sessions)" as per Pitfall 9.

8. **Scalar definitions must be aligned across horizons and tickers**
   - If skew-change is defined as "put-wing minus call-wing" where put-wing = %OTM < -5%, that must be **the same definition** for all three horizons and all tickers.
   - If definitions drift (e.g., put-wing = -6% one day, -4% another), the time series is incoherent.
   - Mitigation: define wing/front/back thresholds in `config.py` or a module-level constant in `surface_evolution.py`, not hard-coded in logic.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| numpy | existing (1.x) | array ops, nanmean, meshgrid, masking | Phase 8 baseline; required for rbf_grid |
| scipy | existing (1.17.1) | RBFInterpolator (reused), Delaunay (convex hull, Phase 8) | already in stack |
| pandas | existing | DataFrame I/O, parquet read/write | already in stack; idempotent row logic |
| pandas_market_calendars | existing | trading-day resolution (already imported in run_daily) | correct calendar handling (no weekends) |
| pyarrow | existing | parquet engine | performant; handles Windows paths |

### No New Dependencies
EVOL-01 through EVOL-06 require **zero new packages**. Rolling-mean is pure numpy; mask intersection is boolean array AND; parquet I/O uses existing pandas/pyarrow stack.

---

## Package Legitimacy Audit

Not applicable — no new packages required. All dependencies already vetted in Phase 8.

---

## Architecture Patterns

### Pattern 1: Shared Grid Axis (EVOL-01)
**What:** Today's grid axes are constructed identically to every baseline-day grid axes, so shapes always match and cells correspond by position.

**When to use:** Every time you load a surface from the store and need to compare it to today's surface.

**Example:**
```python
# Construct grid axes once, use for all comparisons
dte_max = min(surface_df["dte"].max(), config.SURFACE_DTE_MAX)
dte_grid = np.linspace(5, dte_max, config.SURFACE_GRID_DTE)
otm_grid = np.linspace(-15, 15, config.SURFACE_GRID_LM)

# Both today and prior use the same axes
IV_today = rbf_grid(surface_today, spot_today, dte_grid, otm_grid)
IV_prior = rbf_grid(surface_prior, spot_prior, dte_grid, otm_grid)
# Now shapes match, cells align
```

### Pattern 2: Mask Intersection (EVOL-01)
**What:** Before computing a scalar on a pair of grids, intersect their coverage masks so only cells where *both* days have real quote support are included.

**When to use:** Any time you difference two surfaces or compute a statistic on a difference.

**Example:**
```python
mask_today = coverage_mask(surface_today, spot_today, dte_grid, otm_grid)
mask_prior = coverage_mask(surface_prior, spot_prior, dte_grid, otm_grid)
mask_compare = mask_today & mask_prior  # AND

IV_diff = IV_today - IV_prior
IV_diff_masked = np.where(mask_compare, IV_diff, np.nan)

# Now only compute stats on masked cells
level = np.nanmean(IV_diff_masked)
```

### Pattern 3: Idempotent Parquet Write (EVOL-03)
**What:** Read the entire parquet, delete rows matching the (date, ticker, horizon) key, append the new row, write back.

**When to use:** Accumulating stores where re-runs must not duplicate.

**Example:**
```python
if store.exists():
    hist = pd.read_parquet(store)
    mask = (hist["date"] == today) & (hist["ticker"] == ticker) & (hist["horizon"] == horizon)
    hist = hist[~mask]  # delete old version
    hist = pd.concat([hist, pd.DataFrame([new_row])], ignore_index=True)
else:
    hist = pd.DataFrame([new_row])
hist.to_parquet(store, index=False)
```

### Anti-Patterns to Avoid
- **Using calendar math for horizons:** `today - timedelta(days=5)` lands on weekends. Use `nth_trading_day_back` instead.
- **Differencing independently-masked grids:** Comparing `IV_today[mask_today]` to `IV_prior[mask_prior]` (different masks) is comparing real to extrapolation. Intersect the masks first.
- **Hard-coded wing/front/back thresholds:** Put them in `config.py` so they're visible and consistent.
- **Replacing NaN with 0 or fallback values:** It breaks the mask semantics. Let NaN propagate; the mask will exclude it.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| resolve "N sessions back" to a date | calendar arithmetic (timedelta) | `nth_trading_day_back(ticker, date, n)` | weekends/holidays silently break timedelta; trading calendar is the source of truth |
| handle mask intersection | custom boolean logic | numpy AND operator `&` | less error-prone; clear semantics |
| rolling mean of noisy data | custom weighted average | `np.nanmean` | handles NaN correctly, stateless |
| parquet idempotency | append-only design | read-filter-concat-write pattern (from validation.py) | accumulation patterns are error-prone; dedup on write is safer |
| normalize strikes to %OTM | per-day spot fetch from scalar store | per-row spot from `load_surface_snapshot` | one source, less state to track |

---

## Code Examples

### Horizon Resolution
```python
# Source: gex/surface_evolution.py (NEW)
from gex.surface_history import nth_trading_day_back, load_surface_snapshot

ticker = "SPY"
today = datetime.date(2026, 5, 30)

for horizon in [5, 10, 20]:
    prior_date = nth_trading_day_back(ticker, today, horizon)
    if prior_date is None:
        print(f"  {horizon}d: not enough history")
        continue
    
    surface_today, spot_today = load_surface_snapshot(ticker, today)
    surface_prior, spot_prior = load_surface_snapshot(ticker, prior_date)
    
    print(f"  {horizon}d: {prior_date} → {today} ({(today - prior_date).days} calendar days)")
```

### Grid Construction & Interpolation
```python
# Source: gex/analytics.py (Phase 8, reused)
from gex.analytics import rbf_grid, coverage_mask
import numpy as np

surface_df = surface_today  # DataFrame with dte, strike, iv_pct
spot = spot_today
dte_floor = 5
clip_pct = 15.0  # config.SURFACE_PLOT_OTM_CLIP * 100

dte_max = min(surface_df["dte"].max(), 180)  # config.SURFACE_DTE_MAX
dte_grid = np.linspace(dte_floor, dte_max, 40)  # config.SURFACE_GRID_DTE
otm_grid = np.linspace(-clip_pct, clip_pct, 30)  # config.SURFACE_GRID_LM

IV = rbf_grid(surface_df, spot, dte_grid, otm_grid, dte_floor=5, clip_pct=clip_pct)
mask = coverage_mask(surface_df, spot, dte_grid, otm_grid, dte_floor=5, clip_pct=clip_pct)

IV_safe = np.where(mask, IV, np.nan)  # apply mask
```

### Rolling-Mean Baseline
```python
# Source: gex/surface_evolution.py (NEW)
import numpy as np

IV_list = [IV_day1, IV_day2, ..., IV_dayN]  # shape (30, 40) each
mask_list = [mask_day1, mask_day2, ..., mask_dayN]

IV_baseline_stack = np.stack(IV_list, axis=0)  # (N, 30, 40)
IV_baseline_mean = np.nanmean(IV_baseline_stack, axis=0)  # (30, 40)

mask_intersection = np.ones((30, 40), dtype=bool)
for mask in mask_list:
    mask_intersection &= mask  # AND all masks together

IV_diff = IV_today - IV_baseline_mean
IV_diff_masked = np.where(mask_intersection, IV_diff, np.nan)
```

### Scalar Computation
```python
# Source: gex/surface_evolution.py (NEW)
import numpy as np

# level: mean ΔIV
level = np.nanmean(IV_diff_masked)

# rms: RMS of ΔIV
rms = np.sqrt(np.nanmean(IV_diff_masked ** 2))

# skew_change: put-wing minus call-wing ΔIV
# (assuming otm_grid and IV_diff_masked are aligned)
put_wing_idx = otm_grid < -5.0  # config constant
call_wing_idx = otm_grid > 5.0  # config constant
put_wing_mean = np.nanmean(IV_diff_masked[put_wing_idx, :])
call_wing_mean = np.nanmean(IV_diff_masked[call_wing_idx, :])
skew_change = put_wing_mean - call_wing_mean

# term_change: front minus back ATM ΔIV
dte_front_idx = (dte_grid >= 5) & (dte_grid <= 30)
dte_back_idx = (dte_grid >= 90) & (dte_grid <= 180)
atm_idx = np.abs(otm_grid) <= 2.0
front_atm = IV_diff_masked[atm_idx, :][:, dte_front_idx]
back_atm = IV_diff_masked[atm_idx, :][:, dte_back_idx]
term_change = np.nanmean(front_atm) - np.nanmean(back_atm)
```

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing, from Phase 8) |
| Config file | `pytest.ini` (if present) or `gex/tests/` convention |
| Quick run command | `pytest gex/tests/test_surface_evolution.py -x` |
| Full suite command | `pytest gex/tests/ -x --tb=short` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EVOL-01 | Four scalars computed correctly on a pair of surfaces | unit | `pytest gex/tests/test_surface_evolution.py::test_scalars_* -x` | ❌ Wave 0 |
| EVOL-02 | nth_trading_day_back resolves horizons correctly | unit | `pytest gex/tests/test_surface_history.py::test_nth_trading_day_back -x` | ❌ Wave 0 |
| EVOL-03 | Evolution rows persisted idempotently, no duplicates on re-run | integration | `pytest gex/tests/test_surface_evolution.py::test_evolution_idempotent -x` | ❌ Wave 0 |
| EVOL-04 | Non-blocking pass in run_daily doesn't raise or block email | integration | Manual: run `python -m gex.run_daily --dry-run` and verify email proceeds if evolution fails | ❌ Wave 0 |
| EVOL-05 | Scalars comparable across SPY/QQQ/IWM (same grid, same masks) | integration | `pytest gex/tests/test_surface_evolution.py::test_cross_ticker -x` | ❌ Wave 0 |
| EVOL-06 | Backfill from existing surface_history produces same rows as daily ingestion | integration | `pytest gex/tests/test_surface_evolution.py::test_backfill_consistency -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest gex/tests/test_surface_evolution.py -x` (quick unit tests, <10s)
- **Per wave merge:** `pytest gex/tests/ -x --tb=short` (full suite incl. Phase 8 regression)
- **Phase gate:** Full suite green + manual `run_daily --dry-run` + integration test of backfill

### Wave 0 Gaps
- [ ] `gex/tests/test_surface_evolution.py` — unit tests for `nth_trading_day_back`, scalar computation, mask intersection, NaN handling
- [ ] `gex/tests/test_surface_evolution.py` — integration tests for idempotency, backfill, cross-ticker consistency
- [ ] `gex/tests/test_surface_history.py` — extend with `nth_trading_day_back` tests (date resolution, edge cases)
- [ ] Manual verification: run `python -m gex.run_daily --dry-run` and confirm evolution pass does not block email on failure

---

## Security Domain

Not applicable — Phase 9 has no new authentication, data exposure, or external-service integration. Evolution metrics are derived analytics on existing parquet stores. Windows file locking (parquet I/O) is handled by pandas/pyarrow.

---

## Sources

### Primary (HIGH confidence)
- `gex/analytics.py:159–225` — `rbf_grid` and `coverage_mask` function signatures, grid shape, normalization, Delaunay hull mechanics [VERIFIED: codebase read]
- `gex/surface_history.py:59–92` — `load_surface_snapshot`, `list_available_dates`, stored schema (dte, strike, iv_pct, spot per row) [VERIFIED: codebase read]
- `gex/exposure_engine.py:246–251` — surface_diagnostics example of grid construction + coverage_mask call [VERIFIED: codebase read]
- `gex/config.py:66–90` — SURFACE_GRID_DTE=40, SURFACE_GRID_LM=30, SURFACE_PLOT_OTM_CLIP=0.15, SURFACE_SMOOTHING=1.5 [VERIFIED: codebase read]
- `.planning/STATE.md` (2026-05-30) — Phase 8 carry-over: mask convex-hull (parameter-free), rolling-mean baseline, mask intersection [CITED: locked decision]
- `.planning/REQUIREMENTS.md` — EVOL-01 through EVOL-06 verbatim [CITED: requirements source]
- `.planning/phases/08-surface-validation/08-VERIFICATION.md` — Phase 8 shipped coverage_mask + rbf_grid + surface_diagnostics, 93 tests pass [CITED]
- `.planning/research/PITFALLS-v3.3.md` Pitfall 5 (mask intersection), Pitfall 6 (DTE-axis roll), Pitfall 7 (Nth day back), Pitfall 8 (spot normalization) [CITED: risk mitigations]

### Secondary (MEDIUM confidence)
- `gex/vol_metrics.py:70–116` — compute_term_structure shows how "front" and "back" DTE buckets are typically defined (<=45 front, 46–90 second) — suggests thresholds for term_change but NOT authoritative for this phase's definition [ASSUMED: needs planner confirmation]
- `.planning/research/ARCHITECTURE-v3.3.md` — integration points, trigger location in run_daily, schema design — mostly aligned with findings above [CITED]

### Confidence Justification
- **Grid mechanics (HIGH):** Verified by reading rbf_grid + coverage_mask code; test suite (test_rbf_grid.py, test_coverage_mask.py) passes 93/93.
- **Parquet schema (HIGH):** Read directly from surface_history.py; column list and dtypes explicit; forward-compatible comment confirms nullable handling.
- **NaN semantics (HIGH):** numpy documentation (implicit via our reading) and regression test coverage in Phase 8.
- **Scalar definitions (MEDIUM→LOW):** level/rms are standard (mean, RMS). skew_change and term_change *definition* require planner decision on wing/front/back thresholds — not yet locked.
- **Backfill feasibility (HIGH):** Schema stability, reproducible rbf_grid, existing surface_history confirm no data-loss risk.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Grid axes constructed identically from (dte_floor, dte_max, SURFACE_GRID_DTE, SURFACE_GRID_LM) produce matching (30, 40) shapes | Q1, Q2 | If shapes differ, mask/grid subtraction will fail or produce wrong results |
| A2 | `np.nanmean(stack, axis=0)` correctly ignores NaN and averages numeric cells | Q2 | Rolling-mean baseline would be wrong; test with all-NaN baseline to verify NaN-in-NaN-out semantics |
| A3 | The spot stored per-row in surface_history (returned by load_surface_snapshot) is the correct normalization source for %OTM | Q1 | If code uses wrong spot (from scalar store), %OTM axes drift and IV_diff is fabricated; must verify spot source throughout |
| A4 | Mask intersection (mask_today & mask_prior & ... & mask_priorN) correctly produces a cell-wise AND | Q2 | Failure mode: differencing a real cell in today against an extrapolated cell in baseline; must verify AND semantics are applied before every scalar |
| A5 | Scalar definitions (put-wing = %OTM < -5%, etc.) will be set in config.py or module constants by the planner | Q3 | If hard-coded inconsistently, time-series skew_change/term_change will be incoherent; requires explicit config decision |
| A6 | `nth_trading_day_back(ticker, date, n)` correctly indexes into the descending list of available dates | Q4 | If implemented wrong (forward-looking, or off-by-one), horizons will resolve to wrong prior dates; requires unit test coverage |
| A7 | Parquet idempotency (read-filter-concat-write with 3-key mask) is the right pattern and matches validation.py | Q5 | If dedup key is wrong, rows could duplicate on re-run; verify mask logic during review |
| A8 | Windows parquet locking is handled correctly by pyarrow's default engine | Q5 | If parquet writes hang or fail on Windows, daily job will stall silently; test on target Windows machine early |
| A9 | The existing surface_history parquet has sufficient data (at least 20 rows per ticker by Phase 9 go-live) to support backfill | Q7 | If store is too shallow, backfill produces empty results; acceptable (cold-start state); but verify store age at Phase 9 kickoff |
| A10 | `pandas_market_calendars` correctly identifies trading days (no weekends, no US holidays) — already used in run_daily.py | Q4 | If the calendar is wrong, "trading day back" resolves to wrong dates; already in the stack, so risk is low |

**If this table is empty:** Not applicable — all claims in this research were verified directly against codebase or locked decisions. [ACTUALLY: A5 and A6 are flagged as needing planner action/verification.]

---

## Open Questions

1. **Wing and front/back region definitions for skew_change and term_change**
   - What we know: skew-change reads "put vs call wing ΔIV"; term-change reads "front vs back ΔIV"
   - What's unclear: exact %OTM thresholds (e.g., put-wing = <-5% or <-8%?) and DTE thresholds (front = 5–30 or 5–45 DTE?)
   - Recommendation: Planner to define these as `SURFACE_EVOLUTION_PUT_WING_CLIP`, `SURFACE_EVOLUTION_CALL_WING_CLIP`, `SURFACE_EVOLUTION_DTE_FRONT_MAX`, `SURFACE_EVOLUTION_DTE_BACK_MIN` in config.py, with docstrings explaining the choice (e.g., "25Δ roughly corresponds to ±8% OTM on liquid indices; symmetric band balances put-call skew").

2. **Backfill timing and scope**
   - What we know: backfill is feasible via a CLI utility
   - What's unclear: Should it be a separate task at the *start* of Phase 9, or inline with Phase 9 implementation?
   - Recommendation: Separate task (backfill CLI) so Phase 9 implementation + daily integration are testable independently. Backfill can run post-go-live and accumulate data without blocking the daily loop.

3. **Grid DTE max decision for prior days**
   - What we know: today's grid uses `dte_max = min(surface_df["dte"].max(), config.SURFACE_DTE_MAX)` so a thin day (max 120 DTE) produces a 5–120 DTE grid
   - What's unclear: If a prior day has max 150 DTE and today has max 90 DTE, should both grids go 5–180, or should each use its own max?
   - Recommendation: Both use today's dte_max so grid axes are identical. Prior-day surfaces beyond today's max-DTE are clipped (yielding NaN in those cells due to insufficient baseline support), which is correct — today has no long-DTE contracts to compare.

---

## Environment Availability

**Step 2.6 SKIPPED** — Phase 9 has no external dependencies beyond those already verified in Phase 8 (numpy, scipy, pandas, pandas_market_calendars, pyarrow). All are installed and working (verified by Phase 8 test suite passing 93/93).

---

## RESEARCH COMPLETE

**Phase:** 9 - Surface Evolution Engine
**Confidence:** HIGH

### Key Findings
1. **Grid reconstruction is fully reproducible** — stored raw quotes + spot per row enable deterministic `rbf_grid` + `coverage_mask` recomputation for any prior date, ensuring today and baseline grids align on axes and support.
2. **Rolling-mean baseline computation is pure numpy** — `np.nanmean` on a stack of masked grids, with mask intersection (AND) to exclude cells where any baseline day lacks support. No new machinery needed.
3. **Four scalars are standard** — level (mean ΔIV), rms (total movement), skew-change and term-change (read specific grid regions). Planner must define wing/front/back region thresholds in config.py.
4. **Idempotent persistence mirrors validation.py** — read-filter-concat-write with 3-key mask (date, ticker, horizon). New store is trivially small (~3 rows/day/ticker).
5. **Horizon resolution is safe** — `nth_trading_day_back` indexes the stored trading-day list (no calendar math). Cold-start handled (returns None if <N+1 sessions exist).
6. **Backfill is low-risk** — surface_history schema is stable; `rbf_grid` reproducible; old surfaces can be re-computed from stored quotes.
7. **Integration is non-blocking** — separate second pass in `run_daily.run` after snapshot save, wrapped in try/except. Email proceeds if evolution fails.

### Most Important Things the Planner Must Not Get Wrong
1. **Use the per-row spot from `load_surface_snapshot`**, not any other spot source. If code mixes spot sources, %OTM normalization drifts and IV_diff is fabricated.
2. **Intersect coverage masks before computing any scalar** (`mask_today & mask_prior & ... & mask_priorN`). Differencing unmasked cells compares real to extrapolation.
3. **Define wing/front/back region thresholds in config.py once, and use those same thresholds for all three horizons and all tickers.** Inconsistent definitions produce incoherent time-series.
4. **Do not replace NaN with 0 or fallback values.** Let NaN propagate; the mask will exclude it. Replacing NaN invents signals where the surface has no support.
5. **NaN handling in rolling mean is correct:** `np.nanmean([NaN, NaN, 20])` → 20 (correct, because mask_intersection will already exclude that cell if baseline days lack support). Do not "fix" this behavior.

### Next Steps for Planner
1. Define `SURFACE_EVOLUTION_PUT_WING_CLIP`, `SURFACE_EVOLUTION_CALL_WING_CLIP`, `SURFACE_EVOLUTION_DTE_FRONT_MAX`, `SURFACE_EVOLUTION_DTE_BACK_MIN` in config.py with documented rationale.
2. Create `gex/surface_evolution.py` with `update_evolution(ticker, date)`, `load_evolution(ticker, horizon, days)`, and backfill CLI.
3. Create `gex/surface_history.py::nth_trading_day_back(ticker, date, n)` helper.
4. Extend run_daily.py with non-blocking second pass after snapshot save loop.
5. Create test suite (test_surface_evolution.py, test_surface_history.py extensions) with unit + integration tests for Q1–Q7 behavior.

---

*Phase: 09-surface-evolution-engine*
*Researched: 2026-05-30*

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
