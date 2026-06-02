# Phase 14: Accumulation Gating - Context

**Gathered:** 2026-06-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Gate history-dependent UI elements in the Streamlit dashboard behind explicit `≥5 sessions` guards with clear captions, so cold-start sessions never display empty charts or NaN values. Verify the daily email is cold-start safe (evolution section and ΔIV PNG paths already handle cold-start; this phase adds tests to lock that behaviour against regression). Underlying engines and parquet stores are untouched — display only.

</domain>

<decisions>
## Implementation Decisions

### Session threshold (GATE-01)
- **D-01:** Universal floor of N=5 sessions for all guarded elements. Consistent with the existing silent `>=5` floor already in the VRP/skew percentile code. Applied uniformly to: evolution-tab small-multiples, VRP sparkline, VRP/skew percentile captions, and the 42-session spot-vs-levels chart.
- **D-02:** The 42-session chart keeps its "named" window (42 sessions max lookback) but now requires ≥5 sessions of actual history before rendering. This is separate from the 42-session window size.

### Gate posture and caption wording (GATE-01)
- **D-03:** When below threshold: **hide the element entirely** (do not render the chart or metric at all) and show a single `st.caption()` in its place. No empty axes, no placeholder frame.
- **D-04:** Caption wording (standard across all gated elements):
  ```
  "Needs ≥5 sessions — accumulates from run_daily runs forward."
  ```
  Per-element variants are fine if the element has a distinct name (e.g., "VRP history needs ≥5 sessions — accumulates from run_daily runs forward."), but N=5 and the "accumulates from run_daily" clause are fixed.
- **D-05:** VRP and skew percentile captions: currently the percentile is silently omitted below 5 sessions. This phase adds an explicit `st.caption("Needs ≥5 sessions — accumulates from run_daily runs forward.")` where the percentile line would appear, so the user sees a reason rather than nothing.

### Email cold-start (GATE-02)
- **D-06:** GATE-02 is hardening only — no current failure paths have been observed. The evolution section already returns `None` from `evolution_section_html()` when all scalars are None (cold start), and the ΔIV PNG loop already skips per-ticker when no prior snapshot exists.
- **D-07:** Implementation = tests only. Add a cold-start integration test that:
  1. Mocks `evolution_5d_summary()` to return all-None scalars for all tickers and confirms `build_email()` produces no evolution section in the output HTML.
  2. Mocks `nth_trading_day_back()` to return `None` for all tickers and confirms `_build_png_attachments()` returns an empty list without error.
  No new guard logic needed in `run_daily.py` or `report.py`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §GATE-01, §GATE-02 — full requirement text

### Existing guards (read before writing new ones — avoid duplication)
- `streamlit_app.py` lines ~291–345 — surface comparison tab: `sufficient_history` check per horizon key; per-ticker "insufficient history" captions. Pattern to follow.
- `streamlit_app.py` lines ~391–398 — VRP percentile: `if len(vrp_hist_series) >= 5` silent guard. Needs explicit caption added.
- `streamlit_app.py` lines ~451–456 — skew percentile: `if len(skew_series) >= 5` with caption. Already shows session count; update wording to match D-04.
- `streamlit_app.py` lines ~520–522 — evolution all_empty caption. Already exists; extend to ≥5 row check.
- `streamlit_app.py` lines ~647–651 — 42-session chart: `if not hist42.empty` guard + "no history yet" caption. Replace with ≥5 check + D-04 wording.

### Email cold-start paths (GATE-02 — already handled, tests needed)
- `gex/report.py` line ~154–169 — `evolution_section_html()`: returns `None` on cold start when all scalars across all tickers are None. Test target.
- `gex/run_daily.py` lines ~60–67 — `_build_png_attachments()`: `nth_trading_day_back()` → `None` → `continue`; empty list returned cleanly. Test target.

### Codebase conventions
- `.planning/codebase/CONVENTIONS.md` — snake_case, pure-function compute, error handling only at boundaries
- `.planning/codebase/ARCHITECTURE.md` — shared pipeline pattern; output adapters are pure display/delivery wrappers. Guards belong in the display layer, not the engine.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_load_history_cached(ticker, days)` in `streamlit_app.py` — returns hist DataFrame; already cached. Used by VRP sparkline, skew percentile, and 42-session chart. Check `len(hist)` against 5 for each element.
- `load_evolution(ticker, horizon, days)` in `gex/surface_evolution.py` — returns DataFrame; `df.empty` → cold-start. Extend to `len(df) < 5` check.
- `evolution_section_html(evolution_data)` in `gex/report.py` — already None-safe on cold start. No changes needed; test coverage only.

### Established Patterns
- Guard pattern already in codebase (surface comparison tab, lines ~291–345): compute a `sufficient_history` bool per ticker/horizon, then branch on it. Follow this pattern for the new guards.
- Caption pattern: `st.caption("...")` directly below the gated section header. See evolution tab line ~522.
- Test pattern: mock at the boundary (`load_history`, `nth_trading_day_back`, `evolution_5d_summary`) — see existing `gex/tests/` for import-level mock patterns.

### Integration Points
- All dashboard guards are isolated to `streamlit_app.py` — no changes to engines, validators, or parquet stores.
- Email tests go in `gex/tests/` — new file or extend `test_run_daily_pngs.py` / `test_report.py` (check which exists).

</code_context>

<specifics>
## Specific Ideas

- N=5 is the single threshold — do not introduce per-element magic numbers. One constant is cleaner.
- Caption wording is fixed per D-04 — do not vary it per element beyond swapping in the element name.
- The 42-session chart guard replaces the existing "no history yet" caption with the standard D-04 wording once the ≥5 check is in place.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 14-accumulation-gating*
*Context gathered: 2026-06-01*

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
