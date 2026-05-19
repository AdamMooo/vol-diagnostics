# Architecture: GEX Interactive Dashboard v3.0

**Project:** options-quant / GEX module
**Researched:** 2026-05-05
**Confidence:** HIGH — based on direct source reading + Streamlit official docs

---

## Current Module Boundary Map

```
data_loader.py
  load_chain(ticker) → ChainSnapshot(ticker, spot, as_of, chains df)
        |
        ↓
greeks_engine.py
  add_greeks(df, spot) → df + [T_years, gamma]          ← MODIFY: add vanna, charm
  bs_gamma(spot, strike, iv, T, r) → array              ← unchanged
  bs_vanna(...)                                          ← ADD
  bs_charm(...)                                          ← ADD
        |
        ↓
exposure_engine.py
  compute_gex(df, spot) → df + [gex]                    ← unchanged
  strike_gex(df) → strike-level agg                     ← unchanged
  gamma_profile(df, spot) → spot_grid df                ← unchanged
  compute_vex(df, spot) → df + [vex]                    ← ADD
  vex_by_strike(df) → strike-level agg                  ← ADD
        |
        ↓
analytics.py
  summarise(s_df, p_df, spot) → dict                    ← MODIFY: add vanna_exposure
  plot_strike_gex(...)                                   ← unchanged
  plot_gamma_profile(...)                                ← unchanged
  plot_overview(results)                                 ← unchanged (email)
  fig_to_b64(fig) → str                                  ← unchanged (email)
        |
   ┌────┴────────────────────────────────────────┐
   │                                             │
validation.py                              run_daily.py
  save_snapshot(summary, ticker)           ← MODIFY: add vanna_exposure col  orchestrates all
  event_study(ticker)                      ← unchanged                       10 tickers → email
  load_yesterday(ticker) → dict            ← ADD                             ← unchanged
        |
        ↓
  out/gex_snapshots.parquet
  columns: date, ticker, spot, net_gex, gamma_regime,
           zero_gamma_level, call_wall, put_wall
           + vanna_exposure (Phase 2 addition)
        |
        ↓
streamlit_app.py (NEW — Phase 3)
  @st.cache_data(ttl=300) load_ticker(ticker) → dict
  Tab 1: Live dashboard — regime cards, cross-asset chart, per-ticker expanders
  Tab 2: History — ZGL trend, regime persistence, event study output
```

---

## New vs Modified Files

| File | Status | Change |
|------|--------|--------|
| `gex/greeks_engine.py` | MODIFY | Add `bs_vanna()`, `bs_charm()`, extend `add_greeks()` to compute + append `vanna`, `charm` columns |
| `gex/exposure_engine.py` | MODIFY | Add `compute_vex()`, `vex_by_strike()`; VEX uses same sign + multiplier convention as GEX |
| `gex/analytics.py` | MODIFY | `summarise()` dict gets `vanna_exposure` key (net VEX at spot); no chart changes in this phase |
| `gex/validation.py` | MODIFY | `save_snapshot()` writes `vanna_exposure` column; add `load_yesterday(ticker) → dict` helper |
| `gex/run_daily.py` | NO CHANGE | Calls `save_snapshot(summary, ticker)`; picks up new keys automatically since it passes the full summary dict |
| `streamlit_app.py` | ADD (root) | New file. Imports from `gex.*` directly — no new gex module needed |

**Email pipeline is untouched.** `run_daily.py` → `report.py` → `emailer.py` chain does not know about vanna or Streamlit.

---

## Phase Integration Notes

### Phase 1 — Vanna + Charm Greeks

**Files:** `greeks_engine.py` only.

`bs_vanna` and `bs_charm` are pure functions with the same signature shape as `bs_gamma`. They share the `_d1_d2` computation. The cleanest implementation extracts a private `_d1_d2(spot, strike, iv, T, r)` helper so all three Greeks compute it once, then `add_greeks()` calls all three and appends `vanna`, `charm` columns.

```python
def _d1_d2(s, k, v, t, r):
    d1 = (np.log(s / k) + (r + 0.5 * v**2) * t) / (v * np.sqrt(t))
    d2 = d1 - v * np.sqrt(t)
    return d1, d2

# Vanna = -N'(d1) * d2 / (iv * spot)   [∂delta/∂vol — same sign, calls and puts]
# Charm = -N'(d1) * (2*r*T - d2*iv*sqrt(T)) / (2*T*iv*sqrt(T))
```

`add_greeks()` currently uses `bs_gamma(spot, strike, iv, T)` in a vectorised call. After the refactor it calls `_d1_d2` once and passes it to all three Greek functions to avoid recomputation.

No downstream breakage: callers only read columns they name explicitly.

### Phase 2 — VEX + PM Flow Metrics

**Files:** `exposure_engine.py`, `analytics.py`, `validation.py`.

`compute_vex()` is structurally identical to `compute_gex()` — same sign convention (calls +, puts −), same multiplier, but uses `vanna` instead of `gamma`. Add it alongside, not inside, `compute_gex()`.

`vex_by_strike()` mirrors `strike_gex()`.

`summarise()` receives `vex_df` (strike-level VEX) as a new argument. The return dict gains `vanna_exposure` (net VEX scalar). **Signature changes from `summarise(s_df, p_df, spot)` to `summarise(s_df, p_df, spot, vex_df=None)`** — default None keeps the email path passing without modification since run_daily.py doesn't pass vex_df.

`load_yesterday(ticker) → dict` reads the parquet, filters to `date == yesterday`, returns the row as a dict (or None if missing). Used only by Streamlit for delta_regime comparison. Does not affect run_daily.

`save_snapshot()` — add `vanna_exposure` to the `row` dict. Parquet schema evolves automatically since pyarrow infers schema from the DataFrame.

`delta_flow_per_pct` is a derived metric computed in Streamlit from the summary dict, not stored:
```
delta_flow_per_pct = net_vex * 0.01   # $/1% move in underlying
```
No new module needed.

### Phase 3 — Streamlit App

**File:** `streamlit_app.py` at project root.

**Backend:** Do NOT set `matplotlib.use("Agg")` in streamlit_app.py. Streamlit's process already runs headlessly — setting it explicitly can conflict. `run_daily.py` sets it for its own process; that's fine because they're separate processes.

**Figure lifecycle:** Every chart function in `analytics.py` returns an explicit `plt.Figure`. In Streamlit, always pass the figure explicitly to `st.pyplot(fig, clear_figure=True)` and call `plt.close(fig)` immediately after. Never use `plt.show()` or rely on the global pyplot state. This is the pattern already established in `run_daily.py` and must be replicated in the dashboard.

**Caching strategy:**

```python
@st.cache_data(ttl=300)
def load_ticker_data(ticker: str) -> dict:
    """Full pipeline: load_chain → add_greeks → compute_gex → compute_vex
       → strike_gex → vex_by_strike → gamma_profile → summarise.
       Returns summary dict + serializable DataFrames."""
    ...
    return {
        "summary": summary,       # dict — hashable
        "s_df": s_df,             # DataFrame — safe with cache_data (copies on return)
        "vex_df": vex_df,         # DataFrame
        "p_df": p_df,             # DataFrame
        "spot": snapshot.spot,
    }
```

Cache key is `(ticker,)` — Streamlit hashes function arguments automatically. TTL=300 means data refreshes every 5 minutes on rerun. This is appropriate: yfinance chain pulls are slow (2-4s per ticker) and chains don't change second-by-second.

**Do not cache matplotlib figures.** `st.cache_data` serialises return values via pickle; matplotlib Figure objects are not safely picklable across sessions. Generate figures on each rerun from the cached DataFrames — DataFrames are fast to re-plot.

**Session state usage:** Minimal. Only use `st.session_state` for UI controls that must persist across tab switches (e.g., selected ticker). Do not store DataFrames or figures in session state — that's what `@st.cache_data` is for.

**Import graph — no circular risk:**
```
streamlit_app.py
  → gex.data_loader      (no internal gex imports)
  → gex.greeks_engine    (no internal gex imports)
  → gex.exposure_engine  → gex.greeks_engine   (already exists, safe)
  → gex.analytics        → gex.report          (for TICKER_LABEL, REGIME_COLOR)
  → gex.validation       (no internal gex imports)
```
`gex.report` and `gex.emailer` are never imported by Streamlit. No new circular risk introduced.

### Phase 4 — History Tab

**File:** `streamlit_app.py` (extension).

```python
@st.cache_data(ttl=3600)
def load_history() -> pd.DataFrame:
    return pd.read_parquet(STORE)  # already a DataFrame — safe
```

TTL=3600 (1 hour) is fine: parquet only updates once daily at 4:30 PM ET. The history tab reads STORE directly; no new validation.py function needed beyond `load_yesterday()` already added in Phase 2.

`event_study()` in `validation.py` makes a live yfinance call — do not call it inside a Streamlit render path. If surfacing event study output, compute it once in a cached function with a long TTL or display pre-computed output from a stored column.

---

## Component Interaction Summary

```
Phase 1:  greeks_engine.py (self-contained math extension)

Phase 2:  exposure_engine.py → reads vanna col from Phase 1 output
          analytics.py       → reads vex_df from Phase 2
          validation.py      → reads vanna_exposure from summary dict

Phase 3:  streamlit_app.py   → reads from all gex.* modules
                               writes nothing (read-only dashboard)

Phase 4:  streamlit_app.py   → reads parquet written by run_daily.py
                               (async: daily job writes, Streamlit reads)
```

Build order is strict: 1 → 2 → 3 → 4. Phase 3 cannot render VEX cards without Phase 2 summary key. Phase 4 cannot show vanna history until Phase 2 has been running and saving the column.

---

## Key Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| `vex_df=None` default in `summarise()` | Keeps email pipeline (run_daily.py) passing without modification; Streamlit passes it explicitly |
| Figures generated per-render, not cached | matplotlib Figure is not safely picklable; DataFrames are cheap to re-plot |
| `streamlit_app.py` at project root | Streamlit convention; avoids `gex/` package-level `__main__` conflicts |
| `@st.cache_data(ttl=300)` per ticker | Isolates cache invalidation; one bad ticker doesn't bust others |
| No matplotlib.use("Agg") in Streamlit process | run_daily.py sets it for its own process; Streamlit is already headless |
| `plt.close(fig)` after every `st.pyplot()` | Prevents figure accumulation in memory across reruns |
| `load_yesterday()` in validation.py | Parquet read is the right home; keeps Streamlit app thin |

---

## Pitfall Flags by Phase

| Phase | Risk | Mitigation |
|-------|------|------------|
| 1 | `_d1_d2` vectorisation mask must match `add_greeks()` valid-row mask | Use same `valid = (T > 0) & (iv > 0) & (strike > 0) & (spot > 0)` guard already in bs_gamma |
| 2 | `summarise()` signature change breaks existing call sites | Default `vex_df=None`; add assertion that vex_df is provided if vanna_exposure requested |
| 2 | Parquet schema migration: old snapshots lack `vanna_exposure` | `pd.read_parquet` + concat handles missing columns as NaN automatically |
| 3 | PyplotGlobalUseWarning from implicit plt state | Always pass `fig` explicitly to `st.pyplot(fig)`; never call `plt.show()` |
| 3 | Streamlit reruns entire script on every widget interaction | Ensure `load_ticker_data()` is the outermost cached call; no side effects outside it |
| 4 | event_study() makes live yfinance call — slow in render path | Cache with long TTL or move to offline computation |

---

## Sources

- Source reading: `gex/greeks_engine.py`, `gex/exposure_engine.py`, `gex/analytics.py`, `gex/validation.py`, `gex/run_daily.py`, `gex/data_loader.py`
- Streamlit caching: https://docs.streamlit.io/develop/concepts/architecture/caching (HIGH confidence)
- Streamlit st.pyplot: https://docs.streamlit.io/develop/api-reference/charts/st.pyplot (HIGH confidence)
- Matplotlib thread safety in Streamlit: community consensus, multiple sources (MEDIUM confidence)

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
