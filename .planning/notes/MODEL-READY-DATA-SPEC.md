# Model-Ready Data Spec — Vol Diagnostics

Created: 2026-07-21
Last updated: 2026-07-21

This doc is the written bar the v5.0+ modeling milestone checks its data against
before building anything (SCHEMA-01, per D-09/D-10). It exists because this
project's data collection only cold-started ~2026-05-06 for 3 of the 4 series
(`gex_snapshots`, `surface_history`, `oi_history`) — only `vol_index` rides
CBOE's real multi-decade published history. Every depth target below is
grounded in a named estimator's sample-size convention or an explicit
"already deep enough" call — not an arbitrary round number.

## Summary Table

| Series | Min Sessions | Rationale (short) | Schema |
|--------|-------------|--------------------|--------|
| `gex_snapshots` | 750 | GARCH(1,1) sample-size convention (Ng & Lam 2006), literature midpoint of 500–1000 | date, ticker, spot, net_gex, zero_gamma_level, call_wall, put_wall, front_skew, put_25d_iv, call_25d_iv, iv30, strike_slope, term_slope, rv20, vrp, butterfly, coverage_pct, fit_rmse, max_resid, cv_rmse, coherence_violations, coherence_calendar, coherence_butterfly |
| `surface_history` | 251 | RV20 251-trading-day (~1yr) convention — one full seasonal cycle of surface dynamics | date, ticker, spot, dte, strike, moneyness, log_moneyness, iv_pct |
| `vol_index` | 2500 (`config.VRP_DEEP_LOOKBACK_SESSIONS`) | Already CBOE-published external history exceeding any plausible modeling requirement — restated here for traceability, not a new number | symbol, date, open, high, low, close |
| `oi_history` | 251 | Same reasoning as `surface_history` — per-day cross-sectional aggregate, one seasonal cycle is the bar | date, ticker, expiry, dte, call_oi, put_oi, oi, pct_of_total, put_call_ratio |

## Per-Series Rationale

### `gex_snapshots`

Target: **750 sessions** per ticker.

This store's scalar columns (`net_gex`, `vrp`, `rv20`, `zero_gamma_level`, etc.)
are the natural input to a GARCH-style time-series vol model if that's the
eventual model family. GARCH(1,1) sample-size guidance in the literature spans
500–1000 observations (Ng & Lam 2006, cited in 23-RESEARCH.md; corroborated by
the broader 500–2000 range surveyed there) — 750 is the literature's midpoint,
not a round guess.

Schema: `date, ticker, spot, net_gex, zero_gamma_level, call_wall, put_wall,
front_skew, put_25d_iv, call_25d_iv, iv30, strike_slope, term_slope, rv20,
vrp, butterfly, coverage_pct, fit_rmse, max_resid, cv_rmse,
coherence_violations, coherence_calendar, coherence_butterfly`.

### `surface_history`

Target: **251 sessions** per ticker.

Unlike `gex_snapshots`, this store is a per-day cross-sectional surface fit,
not a return series — a GARCH-style sample-size rule doesn't directly apply.
Anchor instead on the RV20 251-trading-day (~1yr) convention (Macrosynergy,
cited in 23-RESEARCH.md) as "one full seasonal cycle" of surface dynamics —
long enough to see a range of vol regimes without importing a return-series
estimator's requirements onto a cross-sectional fit.

Schema: `date, ticker, spot, dte, strike, moneyness, log_moneyness, iv_pct`.

### `vol_index`

Target: reuses `config.VRP_DEEP_LOOKBACK_SESSIONS = 2500` sessions.

This is CBOE-published external history (VIX to 1990, VXN/RVX to 2009)
already exceeding any plausible modeling requirement — no new number needed.
This series is explicitly called out as "already deep enough"; the constant
is restated here only for traceability with the code (see
`engine/health_check.py:MODEL_READY_TARGETS`).

Schema: `symbol, date, open, high, low, close`.

### `oi_history`

Target: **251 sessions** per ticker, same reasoning as `surface_history` —
a per-day cross-sectional aggregate (not a return series), so one seasonal
cycle is the bar, not a GARCH minimum.

Schema: `date, ticker, expiry, dte, call_oi, put_oi, oi, pct_of_total,
put_call_ratio`.

## Auditing Current Depth

Run `python -m engine.health_check --depth-audit` to report actual depth per
series/ticker against the targets above (built in Plan 23-04 Task 2, reusing
`_series_dates()` from Plan 23-01). Meeting the depth bar is necessary but not
sufficient — schema completeness and a clean Plan 23-01 full-history gap scan
(zero gaps) also matter before treating a series as model-ready.

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
<!-- LINKS:END -->
