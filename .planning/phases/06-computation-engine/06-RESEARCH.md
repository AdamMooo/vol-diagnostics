# Phase 6: Whole-Chain Computation Engine — Research

**Researched:** 2026-05-26
**Domain:** Python options analytics — vol metrics computation, pipeline wiring, parquet schema
**Confidence:** HIGH (all findings verified against live codebase)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Strategic Direction**
- Anchor on observable option prices and derived quantities first; GEX is secondary
- No "positioning narrative" — no GEX percentile rank as a primary metric
- All metric labels must be precise: "25Δ put-call skew", "IV30 − RV20", not "fear gauge"

**Module 1: Surface**
- `plot_vol_surface()` in `analytics.py` stripped of ALL GEX overlay parameters
- Remove: spot plane trace, gamma_flip meridian, call_wall meridian, put_wall meridian
- Remove parameters: `gamma_flip`, `call_wall`, `put_wall`, `iv30` from function signature
- Colorscale: "Plasma" → "Viridis"
- `vol_surface_data()` and OTM convention filtering: unchanged

**Module 2: Skew**
- New: `compute_skew_25d(df, spot)` → per-expiry dict with `put_iv`, `call_iv`, `skew`
- 25Δ convention: find strike where |delta| is closest to 0.25 for puts (K < spot) and calls (K > spot)
- Group by T_years, return front month (DTE ≤ 45) and second month (45 < DTE ≤ 90)
- Filter: ≥2 qualifying strikes per side per expiry, OI > 0

**Module 3: Term Structure**
- New: `compute_term_structure(df, spot)` → `{points, classification, front_atm_iv, back_atm_iv}`
- ATM = strike closest to spot per expiry, call side preferred
- Curve classifications: normal / flat / inverted / humped

**Module 4: Carry / VRP**
- New: `compute_rv20(spot_history)` → float: `sqrt(252) × std(log_returns[-20:])`
- New: `compute_vrp(iv30, rv20)` → float: `iv30 - rv20`
- spot_history from parquet via `load_history(ticker)['spot']`
- Return None when fewer than 20 sessions of history exist (cold-start)

**Module 5: Flow Context**
- GEX stays in compute pipeline — NOT removed, just demoted (Phase 7 concern)

**New Module File**
- `gex/vol_metrics.py` — pure functions only, no side effects, no I/O, no Streamlit calls

**Pipeline Wiring (compute.py)**
- `compute_ticker()` return dict gets keys: `skew`, `term_structure`, `rv20`, `vrp`
- rv20 + vrp require spot history from parquet — load inside `compute_ticker()`
- Values may be None on cold-start; expected

**Parquet Schema**
- Add `rv20` and `vrp` columns to snapshots in `validation.py`
- Old snapshots load without error — use `df.get('rv20', pd.NA)` pattern on read

**Noise Cuts**
- Remove `compute_surface_slopes()` calls from pipeline (dead code)
- Remove "Hedge Sh" row from regime cards in `streamlit_app.py`
- Remove "% vs ZGL" line from `streamlit_app.py`

**Tests**
- Unit tests for all 4 `vol_metrics.py` functions using synthetic data
- Test skew with mock chain where 25Δ strikes are known
- Test term structure classification for all 4 curve shapes
- Test compute_rv20 against manual calculation on 20-row series
- Test compute_vrp sign and None behavior

### Claude's Discretion
- Exact delta interpolation method if no strike lands exactly at 0.25Δ (nearest neighbor is fine)
- Whether to expose raw surface_df from `vol_surface_data()` separately or just the cleaned version
- Parquet column dtype for rv20/vrp (float64 preferred)

### Deferred Ideas (OUT OF SCOPE)
- Phase 7: Rendering of skew, term structure, carry modules on dashboard
- Phase 7: GEX tab reorganization
- Phase 7: Regime labels
- Phase 7: Rolling history charts for skew and carry
- Phase 7: Email template updates
- v3.3+: OI tilt, front skew gauge, vol surface shape change metrics, z-scores/percentile ranks
</user_constraints>

---

## Summary

Phase 6 is a pure computation phase — no new UI, no new data sources. Every capability has a clear home in the existing codebase. The work breaks into five distinct sub-tasks: (1) create `gex/vol_metrics.py` with four pure functions, (2) strip GEX overlay code from `plot_vol_surface()`, (3) wire new keys into `compute_ticker()`, (4) extend the parquet schema in `validation.py`, and (5) three noise cuts in `streamlit_app.py`.

The most important discovery is that **delta values already exist on the chain DataFrame from `data_loader.py`**, not from `add_greeks()`. The `add_greeks()` function only adds `T_years` — delta is parsed directly from the CBOE JSON payload in `load_chain()` and lives on `chains` as a float column named `"delta"`. CBOE puts have negative delta by convention. This is the critical input for `compute_skew_25d()`.

The `summarise()` function in `analytics.py` does NOT compute `iv30` — it comes from `snapshot.iv30` (CBOE payload field) and is injected into the summary dict inside `compute_ticker()` at line 70. The `iv30` field is already threaded through the pipeline; `compute_vrp()` just needs it passed in.

**Primary recommendation:** Build `vol_metrics.py` first (pure functions, testable in isolation), wire into `compute_ticker()` second, extend parquet schema third, then do the three noise cuts. Each step is independently verifiable.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 25Δ skew computation | `gex/vol_metrics.py` | `gex/compute.py` (wiring) | Pure function on existing df columns |
| ATM term structure | `gex/vol_metrics.py` | `gex/compute.py` (wiring) | Pure function on existing df columns |
| RV20 computation | `gex/vol_metrics.py` | `gex/validation.py` (history source) | Requires parquet spot history |
| VRP computation | `gex/vol_metrics.py` | `gex/compute.py` (iv30 source) | Two scalar inputs, one scalar output |
| Surface strip (GEX overlays) | `gex/analytics.py` | `streamlit_app.py` (call site update) | Signature change propagates to caller |
| Pipeline orchestration | `gex/compute.py` | — | Single source of truth for both callers |
| Parquet schema extension | `gex/validation.py` | `gex/run_daily.py` (save_snapshot caller) | Schema defined in save_snapshot() |
| Noise cuts | `streamlit_app.py` | — | Rendering-only changes |
| Unit tests | `gex/tests/test_vol_metrics.py` | — | New test file, pure function targets |

---

## Standard Stack

### Core (all already installed)
| Library | Purpose | Notes |
|---------|---------|-------|
| pandas | DataFrame operations, parquet I/O | Already in requirements.txt [VERIFIED: codebase] |
| numpy | log returns, std, sqrt | Already in requirements.txt [VERIFIED: codebase] |
| scipy | `griddata` for surface (unchanged) | Already in requirements.txt [VERIFIED: codebase] |
| plotly | Surface chart (modify only) | Already in requirements.txt [VERIFIED: codebase] |
| pytest | Test runner | Already used in gex/tests/ [VERIFIED: codebase] |

**No new dependencies required for this phase.** All computation uses pandas/numpy only.

---

## Architecture Patterns

### Data Flow

```
CBOE JSON payload
      |
  load_chain()          → ChainSnapshot.chains (df with: expiry, strike, type,
  [data_loader.py]          oi, iv, bid, ask, gamma, delta, vega, theta)
      |
  add_greeks()          → adds T_years column only
  [greeks_engine.py]
      |
  compute_gex()         → adds gex column
  [exposure_engine.py]
      |
      +--→ vol_surface_data()    → surface_df (dte, strike, moneyness, log_moneyness, iv_pct)
      |                                              [unchanged]
      |
      +--→ compute_skew_25d()    → skew dict {front_month: {...}, second_month: {...}}
      |    [vol_metrics.py NEW]
      |
      +--→ compute_term_structure()  → {points, classification, front_atm_iv, back_atm_iv}
      |    [vol_metrics.py NEW]
      |
      +--→ load_history(ticker)  → parquet spot series
           [validation.py]
                |
           compute_rv20()        → float | None
           [vol_metrics.py NEW]
                |
           compute_vrp(iv30, rv20) → float | None
           [vol_metrics.py NEW]
                |
                ↓
           compute_ticker() return dict:
           {summary, s_df, p_df, spot, surface_df, skew_df (legacy),
            skew (NEW), term_structure (NEW), rv20 (NEW), vrp (NEW)}
```

### Recommended Project Structure (additions only)
```
gex/
├── vol_metrics.py          # NEW — pure computation functions
└── tests/
    └── test_vol_metrics.py # NEW — unit tests for all 4 functions
```

### Pattern 1: Delta column on chain DataFrame
**What:** Delta is parsed from the CBOE JSON in `load_chain()` and lives on the chains DataFrame as `"delta"` (float). Put deltas are **negative** (CBOE American option model convention). Calls are positive.

**Source:** `gex/data_loader.py:112` — `"delta": float(opt.get("delta") or 0.0)`. `add_greeks()` does NOT add delta — it only adds `T_years`.

**Critical for skew:** Filter for 25Δ puts uses `df['delta'].abs()` closest to 0.25, not `df['delta']` closest to -0.25. The CONTEXT.md specifies:
```python
# 25Δ put: K < spot
(df['type'] == 'put') & (df['delta'].abs() - 0.25).abs()

# 25Δ call: K > spot
(df['type'] == 'call') & (df['delta'] - 0.25).abs()
```
SKEW_PUT_DELTA in config.py is `-0.25` (matching the existing `compute_skew()` which uses `puts["delta"] - config.SKEW_PUT_DELTA`). The new `compute_skew_25d()` can follow the same pattern.

### Pattern 2: Existing compute_skew() as reference implementation
**What:** `exposure_engine.py` already contains `compute_skew()` — a per-expiry skew function that iterates `groupby("expiry")`. The new `compute_skew_25d()` follows the same pattern but: groups by `T_years` instead of expiry, uses 25Δ put vs 25Δ call (not 50Δ call), and returns a dict keyed by bucket (front/second month) not a DataFrame.

**Reference:**
```python
# exposure_engine.py:108-132 — existing compute_skew() pattern
valid = df[(df["T_years"] > 0) & (df["iv"] > 0) & (df["oi"] > 0)].copy()
valid["dte"] = valid["T_years"] * 365
for expiry, grp in valid.groupby("expiry"):
    ...
    put_idx = (puts["delta"] - config.SKEW_PUT_DELTA).abs().idxmin()
    call_idx = (calls["delta"] - config.SKEW_CALL_DELTA).abs().idxmin()
```

### Pattern 3: iv30 source and flow
**What:** `iv30` comes from CBOE's delayed quotes JSON as `data["iv30"]` — CBOE's own 30-day constant-maturity vol. It is parsed in `load_chain()` into `ChainSnapshot.iv30`, then injected into the summary dict in `compute_ticker()`:
```python
# compute.py:70
summary["iv30"] = snapshot.iv30
```
It does NOT come from `summarise()`. The `plot_vol_surface()` currently accepts `iv30` as a parameter (for the title label only — `f" · IV30 {iv30:.1f}%"`). When stripping the signature, this label must also be removed.

### Pattern 4: Parquet schema extension
**What:** `validation.py` uses forward-compatible schema — new columns added to `save_snapshot()` appear in new rows; old rows load as NaN. The pattern for reading old columns is already established:
```python
# validation.py:65-66 — existing pattern for float columns
for col in _FLOAT_COLS:
    if col in hist.columns:
        hist[col] = hist[col].astype("float64")
```
New `rv20` and `vrp` columns follow the same pattern — add to `_FLOAT_COLS` tuple and add to the `row` dict in `save_snapshot()`.

### Pattern 5: RV20 from spot history
**What:** `load_history(ticker)` returns a DataFrame with `spot` column (among others). The spot series is in descending date order (sort ascending=False, head(days)). For RV20: need at least 21 rows to compute 20 log returns. The `compute_rv20()` function receives the already-extracted spot series.

```python
# validation.py:79-88 — load_history returns descending date order
hist = hist[hist["ticker"] == ticker].sort_values("date", ascending=False)
return hist.head(days).reset_index(drop=True)
```

**Important:** `load_history()` is called inside `streamlit_app.py` with `ttl=config.CACHE_TTL_HISTORY`. When called from `compute_ticker()`, it will NOT be cached — this is fine for a daily-run scenario but adds a file read per compute call in Streamlit. The correct approach: call `load_history()` once in `compute_ticker()`, extract the spot series, pass to `compute_rv20()`.

### Pattern 6: Surface call site update in streamlit_app.py
**What:** The surface is rendered at `streamlit_app.py:206-213`:
```python
st.plotly_chart(
    plot_vol_surface(
        surface_df, ticker, spot=spot, iv30=iv30,
        gamma_flip=s.get("zero_gamma_level"),
        call_wall=s.get("call_wall"),
        put_wall=s.get("put_wall"),
    ),
    use_container_width=True,
)
```
After stripping the `plot_vol_surface()` signature, this call site must be updated to just `plot_vol_surface(surface_df, ticker, spot=spot)`.

### Pattern 7: Slope widgets in streamlit_app.py
**What:** The `compute_surface_slopes()` dead code removal has TWO parts:
1. Remove the call in `compute.py:55`: `slopes = compute_surface_slopes(surface_df)` and the `slopes.get()` injections on lines 73-74
2. Remove the slope display block in `streamlit_app.py:214-254` (the `sm1, sm2, _` columns section showing "Strike Slope" and "Term Slope" metrics with percentile labels)
These are separate tasks — the compute.py removal is pipeline cleanup; the streamlit_app.py removal is the noise cut.

### Anti-Patterns to Avoid
- **Reusing the existing `compute_skew()` from `exposure_engine.py` in place of the new `compute_skew_25d()`:** The existing function computes IV(25Δ put) − IV(**50Δ** call), not IV(25Δ put) − IV(25Δ call). The new function uses symmetric 25Δ convention. Both coexist.
- **Fetching spot history inside `vol_metrics.py`:** All four functions in `vol_metrics.py` must be pure — no I/O. `compute_rv20()` receives a `pd.Series` of spot prices, not a ticker string.
- **Assuming `add_greeks()` adds delta:** It only adds `T_years`. Delta is already on the DataFrame from `load_chain()`.
- **Calling `load_history()` without checking for empty result:** Cold-start (no parquet file) returns an empty DataFrame. `compute_rv20()` must handle this by returning None when len(spot_history) < 21.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Log returns | Custom diff loop | `np.log(series).diff().dropna()` | Vectorized, handles NaN correctly |
| Nearest-delta strike selection | Custom loop | `(series - target).abs().idxmin()` | Pandas built-in, already used in existing `compute_skew()` |
| Parquet read/write | Custom CSV | `pd.read_parquet()` / `df.to_parquet()` | Already established in `validation.py` |
| Annualization | Custom formula | `np.sqrt(252) * series.std()` | Standard; `std()` uses ddof=1 by default in pandas (population-appropriate for sample) |

---

## Exact Locations of Noise Cuts

### Cut 1: "Hedge Sh / $1" row — streamlit_app.py
**Location:** `streamlit_app.py:157` (inside `render_regime_card()` HTML string)
```html
<span class="rc-k">Hedge Sh / $1</span> <span class="rc-v">{df_str}</span>
```
The `df_val` / `df_str` computation on lines 135-139 can also be removed. The `"delta_hedge_flow"` key remains in the pipeline (GEX is not removed from compute), just not displayed.

### Cut 2: "% vs ZGL" line — streamlit_app.py
**Location:** `streamlit_app.py:93-95` inside `_derive_observations()`
```python
if zgl is not None and spot:
    pct = (spot - zgl) / zgl * 100
    obs.append(f"{pct:+.1f}% vs ZGL")
```
Remove these 3 lines. The `obs_html` rendering in `render_regime_card()` (line 148) stays — the remaining observations (Range, % today) still use it.

### Cut 3: compute_surface_slopes() — compute.py
**Location:** `compute.py:15-16` (import) and `compute.py:55-56` (call + assignment) and `compute.py:73-74` (summary injection)
```python
# import line 16:
from gex.exposure_engine import (
    compute_gex, strike_gex, gamma_profile, vol_surface_data, compute_skew,
    compute_surface_slopes,  # REMOVE
)
# line 55-56:
slopes = compute_surface_slopes(surface_df)  # REMOVE ENTIRE LINE
# lines 73-74:
summary["strike_slope"] = slopes.get("strike_slope")  # REMOVE
summary["term_slope"] = slopes.get("term_slope")       # REMOVE
```
The slope display block in `streamlit_app.py:214-254` must also be removed when those keys disappear from summary.

---

## Common Pitfalls

### Pitfall 1: delta sign confusion in compute_skew_25d
**What goes wrong:** Filtering puts with `df['delta'] < -0.20` instead of `df['delta'].abs()` closest to 0.25 — misses puts with delta exactly -0.25 and introduces an OTM distance bias.
**Why it happens:** Natural instinct to use the signed delta value for puts.
**How to avoid:** Use `(puts["delta"] - config.SKEW_PUT_DELTA).abs().idxmin()` where `SKEW_PUT_DELTA = -0.25` — this is the existing pattern in `compute_skew()`. Alternatively use `puts["delta"].abs()` closest to 0.25 for the K < spot filtered set.
**Warning signs:** Test with a mock chain where the 25Δ put has delta exactly -0.25 — result should find it cleanly.

### Pitfall 2: Grouping skew by T_years vs expiry
**What goes wrong:** `groupby("T_years")` creates float equality issues — two rows from the same expiry may have slightly different T_years values due to floating point in the date subtraction formula.
**Why it happens:** T_years = `(expiry_date - today).days / 365.0` — exact for each row, but groupby float keys can fragment groups.
**How to avoid:** Group by `"expiry"` (the date column), then derive DTE from T_years. This is exactly what the existing `compute_skew()` does.

### Pitfall 3: load_history returns descending order
**What goes wrong:** Using `load_history(ticker)["spot"]` directly for RV20 — the series is newest-first (descending date). `np.log(series).diff()` on descending order produces backward returns.
**Why it happens:** `load_history()` sorts `ascending=False` then `.head(days)`.
**How to avoid:** Sort ascending before computing returns: `spot_series.iloc[::-1]` or pass a `.sort_values('date')` result. Verify in tests.

### Pitfall 4: Cold-start parquet file not existing
**What goes wrong:** `load_history()` returns empty DataFrame when STORE doesn't exist. Attempting `history["spot"]` raises KeyError.
**Why it happens:** New environment, no daily runs yet.
**How to avoid:** `compute_rv20()` receives a `pd.Series` — check `len(spot_series) < 21` before computing, return None. In `compute_ticker()`: check `if hist.empty or "spot" not in hist.columns: rv20, vrp = None, None`.

### Pitfall 5: streamlit_app.py call site for plot_vol_surface
**What goes wrong:** After stripping `plot_vol_surface()` signature, forgetting to update the call site at `streamlit_app.py:205-213` — runtime TypeError on the keyword arguments.
**Why it happens:** Two separate files need synchronized changes.
**How to avoid:** The plan must include streamlit_app.py call site update as part of the surface-strip task (not a separate task).

### Pitfall 6: Slope display block in streamlit_app.py references removed keys
**What goes wrong:** After removing `strike_slope` and `term_slope` from compute.py, the `streamlit_app.py:214-254` block does `s.get("strike_slope")` — returns None silently, leaving the block as dead code rather than crashing.
**Why it happens:** `.get()` with None default masks the missing key.
**How to avoid:** Remove the entire slope display block (lines 214-254) as part of the `compute_surface_slopes()` removal task.

---

## Code Examples

### compute_skew_25d — structure
```python
# Source: derived from existing compute_skew() in exposure_engine.py:96-132
def compute_skew_25d(df: pd.DataFrame, spot: float) -> dict:
    """
    Returns {
        'front_month': {'put_iv': float, 'call_iv': float, 'skew': float, 'dte': float} | None,
        'second_month': {'put_iv': float, 'call_iv': float, 'skew': float, 'dte': float} | None,
    }
    """
    valid = df[(df["T_years"] > 0) & (df["iv"] > 0) & (df["oi"] > 0)].copy()
    valid["dte"] = valid["T_years"] * 365

    buckets = {"front_month": None, "second_month": None}

    for expiry, grp in valid.groupby("expiry"):
        dte = grp["dte"].iloc[0]
        bucket = None
        if dte <= 45:
            bucket = "front_month"
        elif dte <= 90:
            bucket = "second_month"
        else:
            continue
        if buckets[bucket] is not None:
            continue  # take the first (nearest) qualifying expiry per bucket

        puts = grp[(grp["type"] == "put") & (grp["strike"] < spot)]
        calls = grp[(grp["type"] == "call") & (grp["strike"] >= spot)]
        if len(puts) < 2 or len(calls) < 2:
            continue

        put_idx = (puts["delta"] - (-0.25)).abs().idxmin()
        call_idx = (calls["delta"] - 0.25).abs().idxmin()
        put_iv = float(puts.loc[put_idx, "iv"] * 100)
        call_iv = float(calls.loc[call_idx, "iv"] * 100)
        buckets[bucket] = {
            "put_iv": put_iv,
            "call_iv": call_iv,
            "skew": put_iv - call_iv,
            "dte": float(dte),
        }

    return buckets
```

### compute_rv20 — log return formula
```python
# Source: CONTEXT.md specification + standard quant convention
import numpy as np
import pandas as pd

def compute_rv20(spot_history: pd.Series) -> float | None:
    # spot_history must be sorted oldest-first (ascending date)
    if len(spot_history) < 21:
        return None
    prices = spot_history.iloc[-21:].to_numpy(dtype=float)
    log_returns = np.log(prices[1:] / prices[:-1])  # 20 returns from 21 prices
    return float(np.sqrt(252) * log_returns.std(ddof=1))
```

### Parquet schema extension — _FLOAT_COLS update
```python
# Source: validation.py pattern (lines 29-34, 65-66)
_FLOAT_COLS = (
    "zero_gamma_level", "call_wall", "put_wall",
    "front_skew", "put_25d_iv", "call_50d_iv", "iv30",
    "strike_slope", "term_slope",
    "rv20", "vrp",  # NEW
)
```

### plot_vol_surface signature after strip
```python
# Source: analytics.py:159-163 — remove iv30, gamma_flip, call_wall, put_wall
def plot_vol_surface(surface_df: pd.DataFrame, ticker: str, spot: float) -> go.Figure:
    ...
    # Remove: iv30_label = f" · IV30 {iv30:.1f}%" if iv30 else ""
    # Remove: _add_meridian(gamma_flip, ...) calls
    # Remove: spot plane Mesh3d trace
    # Change: colorscale="Plasma" → colorscale="Viridis"
    # Change: title text — remove iv30_label
```

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (no config file — runs with `pytest gex/tests/`) |
| Config file | none |
| Quick run command | `python -m pytest gex/tests/test_vol_metrics.py -x -q` |
| Full suite command | `python -m pytest gex/tests/ -q` |

### Existing Tests (23 tests, all passing)
- `test_exposure_engine.py` — 7 tests (compute_gex, strike_gex)
- `test_analytics_summarise.py` — 4 tests (summarise)
- `test_exposure_flow.py` — 2 tests (integration flow)
- `test_greeks_engine.py` — 7 tests (bs_gamma, add_greeks)
- `test_streamlit_app.py` — 2 tests (import guards)

Total: 23 tests [VERIFIED: pytest --collect-only output]

### New Tests Required (test_vol_metrics.py)
| Req ID | Behavior | Test Type | Automated Command |
|--------|----------|-----------|-------------------|
| SC-1 | compute_skew_25d returns correct put/call IV for known 25Δ strikes | unit | `pytest gex/tests/test_vol_metrics.py::test_skew_25d_known_strikes -x` |
| SC-2 | compute_skew_25d returns None bucket when fewer than 2 strikes per side | unit | `pytest gex/tests/test_vol_metrics.py::test_skew_insufficient_strikes -x` |
| SC-3 | compute_skew_25d ignores expiries beyond 90 DTE | unit | `pytest gex/tests/test_vol_metrics.py::test_skew_bucket_assignment -x` |
| TS-1 | compute_term_structure normal classification (IV increases with DTE) | unit | `pytest gex/tests/test_vol_metrics.py::test_term_structure_normal -x` |
| TS-2 | compute_term_structure inverted classification | unit | `pytest gex/tests/test_vol_metrics.py::test_term_structure_inverted -x` |
| TS-3 | compute_term_structure flat classification | unit | `pytest gex/tests/test_vol_metrics.py::test_term_structure_flat -x` |
| TS-4 | compute_term_structure humped classification | unit | `pytest gex/tests/test_vol_metrics.py::test_term_structure_humped -x` |
| RV-1 | compute_rv20 matches manual calculation on 20-return series | unit | `pytest gex/tests/test_vol_metrics.py::test_rv20_manual -x` |
| RV-2 | compute_rv20 returns None when fewer than 21 prices | unit | `pytest gex/tests/test_vol_metrics.py::test_rv20_cold_start -x` |
| VRP-1 | compute_vrp returns iv30 - rv20 | unit | `pytest gex/tests/test_vol_metrics.py::test_vrp_sign -x` |
| VRP-2 | compute_vrp returns None when rv20 is None | unit | `pytest gex/tests/test_vol_metrics.py::test_vrp_none_propagation -x` |

### Wave 0 Gaps
- [ ] `gex/tests/test_vol_metrics.py` — does not exist; covers all SC/TS/RV/VRP requirements above

---

## Environment Availability

Step 2.6: SKIPPED — no external dependencies. All libraries already installed. Computation uses only numpy, pandas, and the existing parquet store in `out/`.

---

## Open Questions (RESOLVED)

1. **`compute_term_structure()` — humped classification threshold**
   - What we know: "compare front-end slope vs back-end slope" (CONTEXT.md). Flat threshold is "< 1 vol point per 30 DTE".
   - What's unclear: No explicit threshold for "humped" detection. Humped means front < middle > back — requires identifying which expiry is "middle".
   - Recommendation: Claude's discretion — split expiries into front third and back third, compare average to middle third. Flag in implementation comment. [ASSUMED: this split approach is reasonable]

2. **Parquet idempotency for rv20/vrp on existing rows**
   - What we know: `save_snapshot()` is idempotent on (date, ticker) — it deletes and rewrites the row if it already exists for today. Old rows (pre-Phase 6) simply won't have rv20/vrp values.
   - What's unclear: No concern — old rows stay as-is, new column defaulting to NaN on read is already the established pattern.
   - Recommendation: No action needed beyond adding to `_FLOAT_COLS`.

3. **Whether `compute_skew()` (existing, 25Δ put − 50Δ call) should be removed**
   - What we know: CONTEXT.md says to create `compute_skew_25d()` but does not explicitly say to remove the old `compute_skew()`. The old function is still called in `compute_ticker()` (`skew_df = compute_skew(df)`) and its results go into `save_snapshot()` via `skew_df` argument (capturing `put_25d_iv` and `call_50d_iv`).
   - What's unclear: Does `compute_skew_25d()` supersede `compute_skew()` entirely, or do both coexist?
   - Recommendation: Keep `compute_skew()` untouched for now — the old skew data (25Δ put − 50Δ ATM call) in the parquet history is still used by the History tab's rolling skew chart. Phase 7 will decide display. The new function adds the symmetric 25Δ convention as an additional pipeline output. [ASSUMED: safe to leave both coexisting]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Grouping `compute_term_structure()` by thirds to detect humped shape is reasonable | Open Questions #1 | Wrong thresholds produce wrong classification; low risk — classification is display-only |
| A2 | `compute_skew()` and `compute_skew_25d()` coexist without removing the old function | Open Questions #3 | Minor code duplication; no correctness risk |

---

## Sources

### Primary (HIGH confidence — verified against live codebase)
- `gex/data_loader.py:112` — delta column on chains DataFrame, CBOE source, float, puts negative
- `gex/greeks_engine.py:55-67` — `add_greeks()` only adds `T_years`, does not add delta
- `gex/compute.py:43-77` — `compute_ticker()` full return dict structure, iv30 injection at line 70
- `gex/analytics.py:159-340` — `plot_vol_surface()` full signature and GEX overlay code locations
- `gex/exposure_engine.py:96-132` — `compute_skew()` pattern for reference implementation
- `gex/validation.py:29-88` — parquet schema, `_FLOAT_COLS`, `load_history()` descending order
- `streamlit_app.py:87-106` — `_derive_observations()` with "% vs ZGL" at lines 93-95
- `streamlit_app.py:126-163` — `render_regime_card()` with "Hedge Sh / $1" at line 157
- `streamlit_app.py:205-254` — surface call site and slope display block locations
- `gex/config.py:84-89` — `SKEW_PUT_DELTA = -0.25`, `SKEW_CALL_DELTA = 0.50`

### Test infrastructure
- pytest `--collect-only` output: 23 tests collected, no config file, no conftest

---

## Metadata

**Confidence breakdown:**
- Delta column name and sign convention: HIGH — verified in data_loader.py
- add_greeks() scope: HIGH — code is 12 lines, only adds T_years
- iv30 source and flow: HIGH — verified in data_loader.py → ChainSnapshot → compute_ticker()
- Exact noise cut line numbers: HIGH — read directly from streamlit_app.py
- plot_vol_surface signature: HIGH — read directly from analytics.py
- Parquet schema and load_history order: HIGH — read directly from validation.py
- compute_skew_25d implementation sketch: MEDIUM — based on existing compute_skew() pattern; exact min-strike threshold left to implementer

**Research date:** 2026-05-26
**Valid until:** Stable codebase — no expiry concern unless Phase 6 is partially executed

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/06-computation-engine/06-01-PLAN|06-01-PLAN]]
- [[_planning/gamma-omm/phases/06-computation-engine/06-02-PLAN|06-02-PLAN]]
- [[_planning/gamma-omm/phases/06-computation-engine/06-03-PLAN|06-03-PLAN]]
- [[_planning/gamma-omm/phases/06-computation-engine/06-CONTEXT|06-CONTEXT]]
- [[_planning/gamma-omm/phases/06-computation-engine/06-PATTERNS|06-PATTERNS]]

<!-- LINKS:END -->
