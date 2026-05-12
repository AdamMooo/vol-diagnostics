# Phase 2: Exposure + PM Flow - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend the GEX exposure layer to compute Vanna Exposure (VEX) and Charm Exposure (CHEX) per strike, add PM flow analytics (delta-hedge $/1% move, vs-yesterday regime label), and surface both in the daily email summary table. Parquet snapshot gains a `vanna_exposure` column for Phase 4 history.

Email pipeline (run_daily.py → Outlook COM) is additive only — no existing behavior changes.

</domain>

<decisions>
## Implementation Decisions

### VEX/CHEX Exposure Layer

- **D-01:** Sign convention identical to GEX: calls positive (+1), puts negative (−1). Formula: `sign * vanna * oi * 100 * spot * 0.01` (EXP-01) and `sign * charm * oi * 100 * spot * 0.01` (EXP-02). Both follow the existing `compute_gex()` pattern in `exposure_engine.py`.
- **D-02:** Add `compute_vex()` and `compute_chex()` functions to `exposure_engine.py` mirroring `compute_gex()`. Add `strike_vex()` and `strike_chex()` aggregators mirroring `strike_gex()`.

### summarise() Architecture

- **D-03:** `summarise()` signature extended with optional keyword args: `net_vex=None`, `net_chex=None`, `delta_hedge_flow=None`. Caller (`process_ticker` in `run_daily.py`) computes these scalars before calling `summarise()` and passes them in. Keeps the summarise() signature clean — no new DataFrame parameters.
- **D-04:** `delta_hedge_flow = net_gex / (spot * 0.01)` computed in `process_ticker()` after `summarise()` call and injected into the summary dict.

### vs-Yesterday Label Logic

- **D-05:** Four-label classification using ±5% UNCHANGED band:
  - **FLIPPED**: regime sign changed (positive ↔ negative, or either ↔ neutral)
  - **INTENSIFIED**: same regime, `|net_gex_today|` > `|net_gex_yesterday| * 1.05`
  - **EASED**: same regime, `|net_gex_today|` < `|net_gex_yesterday| * 0.95`
  - **UNCHANGED**: same regime, magnitude within ±5% band
- **D-06:** `load_yesterday(ticker)` in `validation.py` returns the previous *trading session* row — use market calendar logic (reuse `pandas_market_calendars` already imported in `run_daily.py`) to find prior trading day, not calendar day minus one.
- **D-07:** If no prior snapshot exists for the ticker (first run, or gap in history), vs-yesterday label is `None` and the email cell shows `—`.

### Parquet Schema

- **D-08:** Add `vanna_exposure` column only (per EXP-04). Charm exposure is a transient flow metric, not a level worth historicising. Old rows get NaN on read via `pd.read_parquet()` natural behavior with mismatched schema.

### Email Summary Table

- **D-09:** Two new columns appended to the existing per-ticker table row:
  - `Δ-flow`: formatted as `$X.XB/1%` (e.g. `$8.4B/1%`). Absolute value — direction already conveyed by regime.
  - `vs-Yesterday`: text label (UNCHANGED / FLIPPED / INTENSIFIED / EASED), or `—` if no prior data.
- **D-10:** Table column order: Ticker | Spot | Net GEX | Regime | ZGL | Δ-flow | vs-Yesterday. No changes to existing column formatting.

### Claude's Discretion

- Exact HTML styling for the two new email columns (match existing table CSS)
- Whether `load_yesterday()` returns a dict or a row Series (Series is simpler, dict more explicit — Claude's call)
- Error handling if parquet read fails during vs-yesterday lookup (should not crash the daily run — return None gracefully)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Code to Extend

- `gex/exposure_engine.py` — Pattern for compute_gex(), strike_gex(); VEX/CHEX follow this exactly
- `gex/analytics.py` — summarise() function signature and return dict to extend
- `gex/validation.py` — save_snapshot() schema; load_yesterday() is a new function here
- `gex/run_daily.py` — process_ticker() is where flow analytics are computed and injected; email pipeline must stay intact
- `gex/report.py` — Email HTML builder; summary table structure to extend

### Requirements

- `.planning/REQUIREMENTS.md` — EXP-01 through EXP-04, FLOW-01 through FLOW-04 (all Phase 2)
- `.planning/ROADMAP.md` — Phase 2 success criteria (success criteria #3 specifies load_yesterday() contract)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `compute_gex(df, spot)` in `exposure_engine.py` — VEX/CHEX functions mirror this exactly (same signature, same sign convention, different greek column)
- `strike_gex(df)` — `strike_vex(df)` and `strike_chex(df)` are identical pattern
- `is_trading_day()` + `pandas_market_calendars` in `run_daily.py` — reuse for `load_yesterday()` trading day lookup
- `save_snapshot()` in `validation.py` — extend with `vanna_exposure` field; idempotent on date+ticker already handled

### Established Patterns

- All exposure functions return a modified copy (`df = df.copy()`) — maintain this
- `summarise()` returns a plain dict — extend with new keys, don't change existing keys
- `process_ticker()` in `run_daily.py` catches all exceptions and returns an error dict — vs-yesterday lookup failure must be handled the same way (no uncaught exceptions)

### Integration Points

- `run_daily.py:process_ticker()` — call site for new VEX/CHEX computation and flow analytics
- `analytics.summarise()` — extend return dict with `net_vex`, `net_chex`, `delta_hedge_flow`, `vs_yesterday`
- `report.py` — extend HTML table to show Δ-flow and vs-Yesterday columns
- `validation.save_snapshot()` — add `vanna_exposure` to the row dict

</code_context>

<specifics>
## Specific Ideas

- Email table format chosen: `| Ticker | Spot | Net GEX | Regime | ZGL | Δ-flow | vs-Yesterday |` with `$X.XB/1%` for delta-flow and text label for vs-yesterday.
- vs-yesterday ±5% UNCHANGED band was explicitly chosen (tighter than ±10% default, more sensitive to regime shifts).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-exposure-pm-flow*
*Context gathered: 2026-05-05*

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/02-exposure-pm-flow/02-01-PLAN|02-01-PLAN]]
- [[_planning/gamma-omm/phases/02-exposure-pm-flow/02-01-SUMMARY|02-01-SUMMARY]]
- [[_planning/gamma-omm/phases/02-exposure-pm-flow/02-02-PLAN|02-02-PLAN]]
- [[_planning/gamma-omm/phases/02-exposure-pm-flow/02-02-SUMMARY|02-02-SUMMARY]]
- [[_planning/gamma-omm/phases/02-exposure-pm-flow/02-03-PLAN|02-03-PLAN]]
- [[_planning/gamma-omm/phases/02-exposure-pm-flow/02-03-SUMMARY|02-03-SUMMARY]]
- [[_planning/gamma-omm/phases/02-exposure-pm-flow/02-04-PLAN|02-04-PLAN]]
- [[_planning/gamma-omm/phases/02-exposure-pm-flow/02-04-SUMMARY|02-04-SUMMARY]]
- [[_planning/gamma-omm/phases/02-exposure-pm-flow/02-DISCUSSION-LOG|02-DISCUSSION-LOG]]
- [[_planning/gamma-omm/phases/02-exposure-pm-flow/02-PATTERNS|02-PATTERNS]]
- [[_planning/gamma-omm/phases/02-exposure-pm-flow/02-RESEARCH|02-RESEARCH]]

<!-- LINKS:END -->
