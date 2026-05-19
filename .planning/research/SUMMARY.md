# Research Summary — GEX Interactive Dashboard v3.0

*Synthesized from STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md*

## Stack Additions

Two new packages only. Add to `requirements.txt` at Phase 3:

```
streamlit>=1.45,<2.0
plotly>=6.0,<7.0
```

Everything else is already present: `scipy.stats.norm` handles vanna/charm math; `pyarrow` handles parquet schema evolution; `matplotlib` with existing figure-return pattern stays unchanged.

## Feature Table Stakes (must-have)

- Net VEX scalar — "dealer delta shift per 1-vol-point move"
- Net CHEX scalar — "daily dealer buying/selling from time decay"
- Delta-hedge $/1% flow: `net_gex / (spot * 0.01)` — most PM-actionable number
- Colored regime cards (one per ticker) with flow metrics
- vs-yesterday comparison: UNCHANGED / FLIPPED / INTENSIFIED / EASED
- Streamlit Today tab + Historical tab structure
- Cross-asset overview chart (reuse `analytics.plot_overview()`)

**Differentiators (should-have):** VEX/CHEX by strike, charm by DTE bucket, ZGL history chart, regime persistence table, event study display.

**Defer:** Live intraday refresh, Bloomberg swap, predictive signals, IV surface.

## Architecture

| File | Change |
|------|--------|
| `gex/greeks_engine.py` | Add `_d1_d2()`, `bs_vanna()`, `bs_charm()`; extend `add_greeks()` |
| `gex/exposure_engine.py` | Add `compute_vex()`, `vex_by_strike()` — mirrors `compute_gex()` pattern |
| `gex/analytics.py` | `summarise(s_df, p_df, spot, vex_df=None)` — adds `vanna_exposure` key |
| `gex/validation.py` | `save_snapshot()` writes `vanna_exposure`; add `load_yesterday(ticker)` |
| `streamlit_app.py` | New file at project root — read-only, no import of emailer/run_daily |

`run_daily.py`, `report.py`, `emailer.py` — **no changes**.

## Watch Out For

| # | Pitfall | Phase | Prevention |
|---|---------|-------|-----------|
| 1 | **Charm T-floor blowup** — `1/T` → ±∞ on 0DTE rows | 1 | `T_MIN = 1/365` floor in valid mask; unit test T=0.0001 returns 0.0 |
| 2 | **win32com COM threading** — Streamlit session threads break COM apartment | 3 | `streamlit_app.py` must never import `gex.emailer` or `gex.run_daily` |
| 3 | **yfinance 429 on cold load** — 10 simultaneous pulls hit rate limits | 3 | Per-ticker `@st.cache_data(ttl=300)`, serial fetch with `time.sleep(0.3)` |
| 4 | **Parquet NaN propagation** — old rows lack `vanna_exposure` | 2 | `summary.get("vanna_exposure")` in `save_snapshot()`; all aggregations use `skipna=True` |
| 5 | **Unhashable list in cache_data** — `list[str]` raises `TypeError` | 3 | Use `tuple(selected_tickers)` as cache key; define `TICKERS` as module-level tuple |

## Confidence

Overall: **HIGH** — all four phases have well-documented patterns, no novel dependencies.

Flags for execution:
- Charm sign label must state direction explicitly in UI (sign alone is counterintuitive for PMs)
- Verify `zero_gamma_level` exists in parquet schema before Phase 4; if missing, Phase 2 must add it
- Event study needs 60+ sessions — gate with minimum-N check in Phase 4

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
