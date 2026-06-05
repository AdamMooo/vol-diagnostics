# Phase 6: Whole-Chain Computation Engine — Context

**Gathered:** 2026-05-26
**Status:** Ready for planning
**Source:** Strategic reframe conversation — full product blueprint

---

<domain>
## Phase Boundary

Phase 6 delivers the computation engine for an institutional vol diagnostics tool. The dashboard is being reframed: observable option prices and derived quantities (IV surface, skew, term structure, VRP) are the primary truth set. GEX is a secondary contextual layer.

Phase 6 responsibility: **compute everything, display nothing**. Pure functions, clean data pipeline, noise removed. Phase 7 renders it.

**Product sentence:** A whole-chain volatility diagnostics dashboard that helps PMs judge the cost of protection, the shape of downside risk pricing, and the attractiveness of vol carry for overlay and option-writing decisions.

</domain>

<decisions>
## Implementation Decisions

### Strategic Direction (Locked)
- Anchor on observable option prices and derived quantities first; GEX is inferred dealer behavior (model-dependent) and must be clearly secondary
- No "positioning narrative" — this is dealer-lore, not chain truth
- No GEX percentile rank as a primary metric — percentile without economic interpretation is weak
- All metric labels must be precise: "25Δ put-call skew", "IV30 − RV20", not "fear gauge" or "dealer trap"

### Module 1: Surface (compute change)
- `plot_vol_surface()` in `gex/analytics.py` must be stripped of ALL GEX overlay parameters
- Remove: spot plane trace, gamma_flip meridian, call_wall meridian, put_wall meridian
- Remove: `gamma_flip`, `call_wall`, `put_wall`, `iv30` parameters from function signature
- Change colorscale from "Plasma" to "Viridis" (matches institutional reference aesthetic)
- Axes stay the same: log(K/S) × DTE × IV% — these are correct
- `vol_surface_data()` and its OTM convention filtering remain unchanged

### Module 2: Skew (new computation)
- New function: `compute_skew_25d(df, spot)` → returns dict per expiry with `put_iv`, `call_iv`, `skew` keys
- 25Δ convention: find the strike where |delta| is closest to 0.25 for puts (K < spot) and calls (K > spot) per expiry
- delta values already exist on the dataframe from `greeks_engine.py` (`add_greeks()`)
- Group by expiry (T_years), compute per-expiry skew = IV(25Δ put) − IV(25Δ call)
- Return at minimum: front month (DTE ≤ 45), second month (45 < DTE ≤ 90)
- Filter: must have at least 2 qualifying strikes per side per expiry, else None for that expiry
- OI filter: only strikes with OI > 0 qualify

### Module 3: Term Structure (new computation)
- New function: `compute_term_structure(df, spot)` → returns list of `{dte, atm_iv}` dicts sorted by DTE
- ATM definition: strike closest to spot for each expiry (minimize |K − spot|), call side preferred
- Group by expiry, pick ATM strike, return IV for that strike
- Curve classification: compare front-end slope vs back-end slope
  - normal: IV increases with DTE (contango)
  - flat: slope near zero (< 1 vol point per 30 DTE)
  - inverted: front IV > back IV (backwardation)
  - humped: front and back lower than middle
- Return dict: `{points: [...], classification: str, front_atm_iv: float, back_atm_iv: float}`

### Module 4: Carry / VRP (new computation)
- New function: `compute_rv20(spot_history)` → float (annualized realized vol over last 20 sessions)
- RV20 formula: `sqrt(252) × std(log_returns[-20:])` where log_returns = log(S_t / S_{t-1})
- spot_history comes from parquet store (already exists via `gex/validation.py`)
- New function: `compute_vrp(iv30, rv20)` → float (`vrp = iv30 - rv20`)
- iv30 = 30-day ATM implied vol (already computed in `gex/analytics.py` as `iv30` key in summary)
- Return None for both when fewer than 20 sessions of history exist (cold-start)
- VRP label: "vol carry / VRP" — not "fear gauge"

### Module 5: Flow Context (existing GEX, demoted — Phase 7 concern)
- GEX, net gamma, zero-gamma level stay in pipeline but move to a separate tab in Phase 7
- Phase 6 does NOT remove GEX from compute pipeline — it stays, just not surfaced as primary

### New Module File
- Create `gex/vol_metrics.py` containing: `compute_skew_25d()`, `compute_term_structure()`, `compute_rv20()`, `compute_vrp()`
- Pure functions only — no side effects, no I/O, no Streamlit calls
- Each function has unit-testable inputs and outputs

### Pipeline Wiring (compute.py)
- `compute_ticker()` return dict gets new keys: `skew`, `term_structure`, `rv20`, `vrp`
- `skew` = output of `compute_skew_25d(df, spot)`
- `term_structure` = output of `compute_term_structure(df, spot)`
- `rv20` + `vrp` require spot history from parquet — load inside `compute_ticker()` or pass as arg
- Values may be None on cold-start (< 20 sessions); this is expected

### Parquet Schema
- Add `rv20` and `vrp` columns to snapshots written by `gex/validation.py`
- Old snapshots must load without error — use `df.get('rv20', pd.NA)` pattern when reading

### Noise Cuts (still required)
- Remove `compute_surface_slopes()` calls from pipeline — dead code after slope widgets are cut
- "Hedge Sh" row in dashboard regime cards — cut (Phase 7 concern for rendering, but pipeline should not produce it)
- "% vs ZGL" line — cut (Phase 7 concern)
- These are cuts to `streamlit_app.py` rendering, not to compute pipeline — note for planner: these are Phase 6 scope per ROADMAP success criteria items 4 and 6

### Tests
- Unit tests for all 4 new `vol_metrics.py` functions using synthetic data
- Test `compute_skew_25d()` with a mock chain where 25Δ strikes are known
- Test `compute_term_structure()` classification for all 4 curve shapes with synthetic IV data
- Test `compute_rv20()` against manual calculation on a 20-row series
- Test `compute_vrp()` sign and None behavior

### Claude's Discretion
- Exact delta interpolation method if no strike lands exactly at 0.25Δ (nearest neighbor is fine)
- Whether to expose raw surface_df from `vol_surface_data()` separately or just the cleaned version
- Parquet column dtype for rv20/vrp (float64 preferred)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing computation pipeline
- `gex/exposure_engine.py` — `vol_surface_data()` (surface), `compute_surface_slopes()` (dead code to remove)
- `gex/analytics.py` — `plot_vol_surface()` (strip GEX overlays here), `summarise()` (iv30 already computed here)
- `gex/greeks_engine.py` — `add_greeks()` adds delta values to df (25Δ skew computation depends on this)
- `gex/compute.py` — `compute_ticker()` orchestrates pipeline; new keys go here
- `gex/validation.py` — parquet snapshot store; schema change goes here
- `gex/config.py` — surface config constants; check for slope-related constants to remove

### Dashboard (rendering context — Phase 7, but understand the interface)
- `streamlit_app.py` — rendering; Phase 6 noise cuts (items 4 and 6 in success criteria) happen here

### Project constraints
- `CLAUDE.md` — no new signals beyond six locked signals; this constraint applies to GEX signals, not vol surface metrics which are derived directly from prices
- `gex/config.py` — SPY/QQQ/IWM only, full chain per ticker

</canonical_refs>

<specifics>
## Specific Implementation Details

### 25Δ skew — delta sign convention
Puts have negative delta in Black-Scholes convention. When filtering for 25Δ puts: `(df['type'] == 'put') & (df['delta'].abs() - 0.25).abs() < threshold`. When filtering for 25Δ calls: `(df['type'] == 'call') & (df['delta'] - 0.25).abs() < threshold`.

### RV20 from parquet
`gex/validation.py` has `load_history(ticker)` which returns a DataFrame of snapshots. Each snapshot contains `spot`. Use `load_history(ticker)['spot']` to get the spot price series, then compute log returns.

### iv30 source
Already in `summarise()` output dict as `iv30` key. Pass this through `compute_ticker()` return dict so Phase 7 can use it for VRP display.

### Surface colorscale
Change `colorscale="Plasma"` to `colorscale="Viridis"` in `plot_vol_surface()`. That's the only colorscale change needed.

### Reference image aesthetic
The institutional reference surface shows: purple (low vol) → yellow-green (high vol), clean grid lines, no annotations, minimal chrome. Viridis achieves this.

</specifics>

<deferred>
## Deferred to Phase 7

- Rendering of skew, term structure, and carry modules on dashboard
- GEX tab reorganization and labeling as "Microstructure / Execution Context"
- Regime labels (calm / rich protection / event stress / dislocated front end)
- Rolling history charts for skew and carry
- Email template updates

## Deferred to v3.3+
- OI tilt (TILT-01)
- Front skew gauge (SKEW-01)
- Vol surface shape change metrics (daily/weekly surface diff)
- z-scores and percentile ranks for skew/term structure

</deferred>

---

*Phase: 06-computation-engine*
*Context gathered: 2026-05-26 — strategic reframe to institutional vol diagnostics*

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
