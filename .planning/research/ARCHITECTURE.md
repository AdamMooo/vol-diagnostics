# Architecture Patterns

**Domain:** GEX positioning pipeline — v3.2 feature integration
**Researched:** 2025-01-27

## Recommended Architecture

### Design Principle: Extend compute.py's summary dict, don't restructure the pipeline

The existing pipeline is clean and linear:

```
data_loader.load_chain()
  → greeks_engine.add_greeks()
    → exposure_engine.compute_gex() / strike_gex() / gamma_profile() / vol_surface / skew
      → analytics.summarise()
        → compute.compute_ticker() assembles summary dict
```

Every downstream consumer (streamlit_app, report.py, validation.py, run_daily.py) reads from the summary dict returned by `compute_ticker()`. **The summary dict is the integration seam.** New v3.2 features should all flow through it.

### Component Map: New vs Modified

```
NEW modules:
  gex/positioning.py      — VRP, OI tilt, percentile rank, narrative text

MODIFIED (small):
  gex/compute.py          — call positioning functions, add results to summary dict
  gex/validation.py       — persist new fields (vrp, oi_tilt) to parquet; add load_history window param
  gex/config.py           — new constants (RV_WINDOW, VRP defaults, percentile window)

MODIFIED (medium):
  streamlit_app.py        — new card fields, narrative block, output cuts, vol surface demotion
  gex/report.py           — new card fields, narrative block, output cuts

UNCHANGED:
  gex/data_loader.py      — no new data needed from CBOE (RV comes from parquet history)
  gex/greeks_engine.py    — no changes
  gex/exposure_engine.py  — OI tilt uses chain df already produced here
  gex/analytics.py        — summarise() unchanged; charts unchanged except cuts
  gex/run_daily.py        — unchanged (already calls compute_ticker + save_snapshot)
```

### Why a Single New Module (`positioning.py`) Instead of Scattering

1. **VRP, OI tilt, percentile rank, and narrative are all positioning context** — they answer "what's the dealer environment?" not "what's the GEX math?" Conceptually distinct from `analytics.py` (which does GEX-specific summary + charts) and `exposure_engine.py` (which does GEX computation).

2. **analytics.py already has a clear mandate**: summarise GEX levels + produce Plotly charts. Adding VRP (which needs price history) and narrative text generation would blur its purpose.

3. **Single entry point for testing**: one module with pure functions, each taking well-defined inputs (summary dict, history df, chain df) and returning values. No side effects.

4. **Avoids circular dependencies**: positioning.py imports nothing from the rest of gex except config. compute.py calls it after building the summary dict.

---

## Component Boundaries

| Component | Responsibility | Inputs | Outputs |
|-----------|---------------|--------|---------|
| `positioning.py` | VRP, OI tilt, percentile rank, narrative | summary dict, history df, chain df | dict of positioning fields |
| `compute.py` | Pipeline orchestration | ticker string | summary dict (enriched with positioning) |
| `validation.py` | Parquet persistence + history retrieval | summary dict, ticker, days | save/load parquet |
| `report.py` | HTML email cards | summary dict | HTML string |
| `streamlit_app.py` | Dashboard rendering | summary dict | Streamlit UI |

---

## Data Flow: v3.2 Integration

### Current Flow (v3.1)
```
CBOE JSON → load_chain() → ChainSnapshot
  → add_greeks() → enriched df
  → compute_gex() → df with gex column
  → strike_gex() → s_df
  → gamma_profile() → p_df
  → vol_surface_data() → surface_df
  → compute_skew() → skew_df
  → summarise(s_df, p_df, spot, delta_hedge_flow) → summary dict
  → compute_ticker() adds: ticker, iv30, price_change_pct, front_skew, slopes
  → return {summary, s_df, p_df, spot, surface_df, skew_df}
```

### New Flow (v3.2) — additions marked with ★
```
CBOE JSON → load_chain() → ChainSnapshot
  → add_greeks() → enriched df
  → compute_gex() → df with gex column
  → strike_gex() → s_df
  → gamma_profile() → p_df
  → vol_surface_data() → surface_df
  → compute_skew() → skew_df
  → summarise(s_df, p_df, spot, delta_hedge_flow) → summary dict
  → compute_ticker() adds: ticker, iv30, price_change_pct, front_skew, slopes

  ★ positioning.compute_oi_tilt(df, spot) → oi_tilt dict
  ★ positioning.compute_rv20(history_df) → rv20 float
  ★ positioning.compute_vrp(iv30, rv20) → vrp float
  ★ positioning.compute_percentile_rank(net_gex, history_df) → pctile int
  ★ positioning.compute_skew_percentile(front_skew, history_df) → pctile int
  ★ positioning.generate_narrative(summary) → narrative string

  → summary dict now includes: oi_tilt, rv20, vrp, gex_percentile,
    skew_percentile, narrative
  → return {summary, s_df, p_df, spot, surface_df, skew_df}
```

### Key architectural decision: RV20 data source

RV20 needs 20 trading sessions of daily close prices. Two options:

**Option A: Use parquet snapshot history** (RECOMMENDED)
- `validation.load_history(ticker, days=25)` already returns spot prices per day
- RV20 = annualized std of log-returns over trailing 20 rows
- **Pro:** Zero new dependencies. Data already exists and grows daily.
- **Con:** Needs 20+ days of snapshots to produce a value. New deployments will show "building context" for ~4 weeks.
- **Con:** If run_daily misses a day, there's a gap (but this is already true for all history features).

**Option B: Fetch from yfinance or another source**
- `yf.download(ticker, period="1mo")` would get close prices
- **Pro:** Immediately available, doesn't depend on snapshot history.
- **Con:** Adds yfinance as a runtime dependency for the daily pipeline (currently only used for ^IRX rate, and that's already fragile). CBOE data doesn't include historical closes.
- **Con:** yfinance is unreliable (rate limits, API changes).

**Recommendation: Option A.** The parquet store already has spot prices. The "building context" period is acceptable — the dashboard already shows this pattern for slope percentiles. Add a `load_history(ticker, days=25)` call in compute.py and pass the history to positioning functions. For fresh deployments, VRP will show "—" until 20+ snapshots exist — same as existing percentile features.

---

## New Module: `gex/positioning.py`

### Function Signatures

```python
"""
Positioning context metrics — VRP, OI tilt, percentile rank, narrative.

All functions are pure: take data in, return values out. No side effects,
no file I/O, no network calls. compute.py orchestrates the calls.
"""

def compute_rv20(history_df: pd.DataFrame, window: int = 20) -> float | None:
    """
    Annualized realized vol from trailing daily close prices.
    
    history_df: from validation.load_history() — must have 'spot' and 'date' columns.
    Returns None if fewer than window+1 rows available.
    
    Formula: std(ln(S_t / S_{t-1})) * sqrt(252) * 100  (in %)
    """

def compute_vrp(iv30: float | None, rv20: float | None) -> float | None:
    """
    Volatility Risk Premium = IV30 - RV20, in percentage points.
    
    Positive VRP = options expensive relative to realized (normal).
    Negative VRP = options cheap relative to realized (unusual — stress or complacency).
    
    Carr & Wu (2009): VRP is compensation for bearing vol risk.
    Returns None if either input is None.
    """

def compute_oi_tilt(df: pd.DataFrame, spot: float) -> dict:
    """
    Dollar-weighted put vs call OI tilt.
    
    df: greeks-enriched chain df (has 'type', 'oi', 'strike', 'bid', 'ask' columns).
    
    Returns {
        'put_oi_dollars': float,    # total put OI × mid × 100
        'call_oi_dollars': float,   # total call OI × mid × 100
        'oi_tilt': float,           # put / (put + call), 0-1 range
        'oi_tilt_label': str,       # 'put-heavy' / 'balanced' / 'call-heavy'
    }
    
    Tilt > 0.55 = put-heavy (protection demand). Tilt < 0.45 = call-heavy.
    """

def compute_percentile_rank(
    value: float, 
    history_series: pd.Series, 
    min_obs: int = 10
) -> int | None:
    """
    Percentile rank of value vs trailing history.
    Returns 0-100 int or None if fewer than min_obs observations.
    Generic — used for net_gex, front_skew, vrp.
    """

def generate_narrative(summary: dict) -> str:
    """
    Mechanical positioning narrative from summary dict fields.
    
    Template-driven, not LLM. Covers:
    1. GEX sign → dampening vs amplifying (always)
    2. GEX percentile → "historically high/low/normal dealer gamma" (if available)
    3. VRP → "options rich/cheap relative to realized" (if available)
    4. OI tilt → directional pressure context (always)
    
    Returns 2-3 sentence string. No opinions, no forecasts — pure mechanical
    description of current state.
    """
```

### Integration in compute.py

```python
# In compute_ticker(), after existing summary assembly (line ~74):

from gex.positioning import (
    compute_rv20, compute_vrp, compute_oi_tilt,
    compute_percentile_rank, generate_narrative,
)
from gex.validation import load_history

# Load history for percentiles and RV
history = load_history(ticker, days=90)

# OI tilt — computed from the live chain df (already available)
oi_tilt = compute_oi_tilt(df, snapshot.spot)
summary["oi_tilt"] = oi_tilt["oi_tilt"]
summary["oi_tilt_label"] = oi_tilt["oi_tilt_label"]

# RV20 and VRP
rv20 = compute_rv20(history)
vrp = compute_vrp(snapshot.iv30, rv20)
summary["rv20"] = rv20
summary["vrp"] = vrp

# Percentile ranks
if not history.empty and "net_gex" in history.columns:
    summary["gex_percentile"] = compute_percentile_rank(
        summary["net_gex"], history["net_gex"].dropna()
    )
if not history.empty and "front_skew" in history.columns:
    summary["skew_percentile"] = compute_percentile_rank(
        summary.get("front_skew"), history["front_skew"].dropna()
    )

# Narrative — runs last, reads from enriched summary
summary["narrative"] = generate_narrative(summary)
```

---

## Parquet Schema Extension (validation.py)

Current schema:
```
date, ticker, spot, net_gex, zero_gamma_level, call_wall, put_wall,
front_skew, put_25d_iv, call_50d_iv, iv30, strike_slope, term_slope
```

New columns to add:
```
vrp, rv20, oi_tilt
```

The existing schema is forward-compatible by design (docstring says "older snapshots missing newer columns load as NaN on read"). Just add the new fields to `save_snapshot()`:

```python
row["vrp"] = summary.get("vrp")
row["rv20"] = summary.get("rv20")
row["oi_tilt"] = summary.get("oi_tilt")
```

Add to `_FLOAT_COLS` tuple.

---

## Output Cuts (CUT-01 / CUT-02)

### Card fields to remove

| Field | Where | Action |
|-------|-------|--------|
| Hedge Sh/$1 | report.py `_ticker_card`, streamlit `render_regime_card` | Delete row |
| % vs ZGL | report.py `_ticker_card` | Delete row |
| Strike slope | streamlit vol tab | Delete metric widget |
| Term slope | streamlit vol tab | Delete metric widget |

### Card fields to add

| Field | Where | Source |
|-------|-------|--------|
| VRP (IV30 − RV20) | report.py card right col, streamlit card | `summary["vrp"]` |
| OI Tilt | report.py card right col, streamlit card | `summary["oi_tilt"]` + label |
| GEX Percentile | report.py card right col, streamlit card | `summary["gex_percentile"]` |
| Skew Percentile | alongside existing skew value | `summary["skew_percentile"]` |

### Vol surface demotion (CUT-02)

In streamlit_app.py, the Vol tab currently shows: vol surface chart, slope metrics, skew term structure chart. Change to:
- Move skew term structure into Strikes tab (it's decision-relevant)
- Vol surface becomes a collapsed expander inside an "Advanced" section
- Remove slope metrics entirely (they're being cut per CUT-01)

### Narrative placement

**Streamlit:** Always-visible block between the card and the expander for each ticker. Uses `st.info()` or a styled markdown block. Not inside an expander — the whole point is it's the first thing you read.

**Email:** Below the card's KV table, before the divider rule. Same HTML row structure as existing observations, but more prominent (slightly larger font, full width).

---

## Patterns to Follow

### Pattern 1: Pure computation module with orchestrator integration
**What:** positioning.py contains only pure functions. compute.py calls them and puts results into summary dict. No new orchestration logic in positioning.py itself.
**Why:** Matches existing pattern — exposure_engine.py is pure computation, compute.py orchestrates. analytics.py is the one exception (has both summarise() and chart functions), and that's already slightly overloaded.

### Pattern 2: Graceful degradation with None
**What:** Every positioning function returns None when insufficient data. Summary dict carries None. Card renderers show "—" for None values.
**Why:** Already the pattern everywhere — front_skew, slopes, delta_hedge_flow all gracefully degrade. VRP will be None for ~20 days after fresh deploy; percentiles None for ~10 days. Dashboard already handles this with "building context" captions.

### Pattern 3: Summary dict as integration seam
**What:** All new values flow through summary dict. No new return keys in compute_ticker()'s top-level dict. No new DataFrames.
**Why:** Every consumer reads summary dict. Adding keys is backward-compatible (dict.get() with defaults). Adding new top-level return values would require changing every consumer.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Fetching price history inside positioning.py
**What:** Having positioning.py call validation.load_history() directly.
**Why bad:** Creates coupling between computation and I/O. Makes testing harder. Violates the pattern where compute.py handles all data loading.
**Instead:** compute.py loads history once, passes it to positioning functions.

### Anti-Pattern 2: Adding yfinance dependency for RV20
**What:** Using yfinance to fetch daily closes for realized vol.
**Why bad:** yfinance is already fragile (used only for risk-free rate with fallback). Adding it as a required dependency for a core feature means VRP breaks when yfinance breaks.
**Instead:** Use parquet snapshot history. Accept the cold-start period.

### Anti-Pattern 3: Putting narrative logic in report.py or streamlit_app.py
**What:** Template strings for narrative scattered across rendering code.
**Why bad:** Two renderers (email + dashboard) need the same narrative. Duplicating template logic means they'll diverge.
**Instead:** positioning.generate_narrative() returns a plain string. Both renderers display it as-is.

### Anti-Pattern 4: Adding new DataFrames to compute_ticker return
**What:** Returning e.g. `"oi_df": oi_breakdown_dataframe` alongside existing s_df, p_df.
**Why bad:** Every consumer (streamlit, run_daily) would need updating. OI tilt is a scalar — it belongs in summary dict, not as a separate df.
**Instead:** Scalars go in summary dict. No new DataFrames needed for v3.2.

---

## Build Order (Dependency-Driven)

```
Phase 1: positioning.py — pure functions, unit-testable
   No dependencies on other v3.2 work. Write + test in isolation.
   Functions: compute_rv20, compute_vrp, compute_oi_tilt, compute_percentile_rank
   
Phase 2: compute.py integration — wire positioning into pipeline
   Depends on Phase 1. Load history, call positioning functions, enrich summary dict.
   
Phase 3: validation.py — persist new fields
   Depends on Phase 2 (new fields in summary dict). Add vrp, rv20, oi_tilt to snapshot.
   
Phase 4: generate_narrative — needs full summary dict shape finalized
   Depends on Phase 2 (all fields available). Template logic over enriched summary.
   
Phase 5: Output cuts — remove fields from cards/charts
   Independent of Phases 1-4 but logically grouped with card changes.
   Can be done in parallel with Phase 4.
   
Phase 6: Card/rendering updates — add new fields + narrative to display
   Depends on Phases 2+4. Update report.py and streamlit_app.py together.
   Vol surface demotion (CUT-02) can be done here.
```

### Why this order:
- **Phases 1-2 first**: Core computation must exist before anything can display it
- **Phase 3 early**: Parquet persistence starts accumulating new fields immediately — every day of delay is a day of missing VRP/OI tilt history
- **Phase 4 after 2**: Narrative reads from the enriched summary dict, so dict shape must be stable
- **Phase 5 parallel-safe**: Cuts are independent deletions — no conflict with additions
- **Phase 6 last**: Rendering changes are the most visible and benefit from having all data fields finalized

---

## Scalability Considerations

Not applicable for this system (3 tickers, 1 user, runs once daily). The bottleneck is CBOE fetch latency (~2s per ticker), not computation. Adding positioning functions adds <50ms per ticker.

## Sources

- Existing codebase: compute.py, analytics.py, exposure_engine.py, validation.py, report.py, streamlit_app.py
- Carr & Wu (2009) — Variance Risk Premiums (referenced in PROJECT.md strategic decisions)
- Xing, Zhang & Zhao (2010, JFQA) — IV skew predictive power (already in codebase methodology)
- Project decisions in .planning/PROJECT.md v3.2 scope
