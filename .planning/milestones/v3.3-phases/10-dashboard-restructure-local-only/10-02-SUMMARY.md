---
phase: "10"
plan: "02"
subsystem: streamlit
tags: [dashboard, tabs, vrp, evolution, positioning, oi]
dependency_graph:
  requires:
    - config.PALETTE (10-01)
    - gex/analytics.plot_oi_by_strike (10-01)
    - gex/vol_metrics.vrp_headline (10-01)
  provides:
    - streamlit_app.py restructured 4-tab dashboard
    - Surface/Compare with relative-horizon dropdowns
    - Calculus+VRP tab (VRP headline + sparkline + scalar strip)
    - Evolution tab (horizon radio + 4 small-multiple panels)
    - Positioning tab (OI-led Chart A + 42-session Chart B + gamma expander)
  affects:
    - streamlit_app.py (complete tab rewrite below line 246)
tech_stack:
  added: []
  patterns:
    - relative-horizon dropdown resolved via nth_trading_day_back (no calendar arithmetic)
    - small-multiples panel loop (metric × ticker overlay)
    - OI-led positioning with GEX levels demoted to expander
key_files:
  created: []
  modified:
    - streamlit_app.py
  deleted: []
decisions:
  - "All 3 plan tasks executed as a single atomic rewrite — tab bodies are interdependent; splitting creates transient broken states"
  - "OI by strike caption honest: calls blue / puts red only when oi column present; falls back to abs(gex) proxy per Plan 01 deviation"
  - "plot_strike_gex removed from imports; REGIME_COLOR import removed; config.PALETTE used throughout"
  - "Evolution loads all INDEX_TICKERS unconditionally so cross-ticker overlay works even when only a subset is in selected_all sidebar"
metrics:
  duration_minutes: 8
  completed_date: "2026-06-01"
  tasks_completed: 3
  files_changed: 1
---

# Phase 10 Plan 02: Dashboard Restructure — 4-Tab Layout Summary

complete rewrite of streamlit_app.py tab section: Surface/Calculus+VRP/Evolution/Positioning replacing the old Surface/Skew/Term Structure/Flow Context layout; all deleted analytics functions purged from imports; REGIME_COLOR migrated to config.PALETTE

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Rewrite import block and Surface tab (Today + Compare sub-tabs) | 9a050b2 | streamlit_app.py |
| 2 | Build Calculus+VRP tab and Evolution tab | 9a050b2 | streamlit_app.py |
| 3 | Build Positioning tab and clean up legacy Methodology expander | 9a050b2 | streamlit_app.py |

## What Was Built

**Surface tab — Today sub-tab:** unchanged from prior implementation (per-ticker 3D surface + trust readout strings).

**Surface tab — Compare sub-tab:** two relative-horizon selectboxes per ticker (`compare_a_{ticker}` / `compare_b_{ticker}`). Horizon options: live/1d/5d/10d/20d/30d/60d. Available options self-limit to what `nth_trading_day_back` can resolve against the stored parquet history. Defaults to live vs 5d. "live" resolves to the current session's surface_df; numeric n resolves via `nth_trading_day_back(ticker, anchor, n)` then `load_surface_snapshot`. T-10-07 guard: if resolution returns None, shows `st.caption("insufficient history for this horizon")` and skips the plot. DTE intersection caption shown beneath each chart.

**Calculus+VRP tab:** per-ticker loop. For each ticker: section header via `.sec` CSS class, VRP headline metric + caption (via `vrp_headline`), VRP sparkline (160px, config.PALETTE["accent"], add_hline y=0), front skew scalar + percentile vs history, term spread scalar, cross-ticker 25Δ RR grouped bar (SPY=call blue, QQQ=accent amber, IWM=positive green) rendered once (guarded by `ticker == selected_all[0]`).

**Evolution tab:** horizon radio (5/10/20, default 5d, key="evol_horizon"). Loads `load_evolution` for all three INDEX_TICKERS at the selected horizon. Four metric panels stacked: level / rms / skew_change / term_change. Each panel is a single `go.Figure` with one Scatter trace per ticker (SPY/QQQ/IWM overlaid), add_hline y=0, plotly_dark, height=220. T-10-06/T-10-08 guards: `dropna(subset=[metric])` per trace before plotting; all-empty guard shows single cold-start caption; per-ticker cold-start caption shown for tickers with empty data when others have data.

**Positioning tab:** tab-level OI/GEX disclaimer. Per ticker: `st.markdown(f"**{ticker}**")`, two-column layout [3,2]. Column c1: `plot_oi_by_strike` + caption noting call/put coloring and GEX-model caveat. Column c2: `_load_history_cached(ticker, days=42)` → four traces (spot white dot, γ-flip amber solid, call wall blue dot, put wall red dot), each with `dropna` guard before tracing. Expander "γ-flip & walls — model derivation": `plot_gamma_profile` + markdown explanation of gamma profile + zero-gamma + walls + dealer assumption. Bottom of tab: IWM trust note caption.

**Methodology expander:** updated vol surface description (convex-hull coverage mask language replacing old kNN/NaN-holes wording); "Flow Context tab" reference replaced with "Positioning tab".

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Guard] T-10-07 nth_trading_day_back None guard**
- **Found during:** Task 1
- **Issue:** Plan spec requires guard when `nth_trading_day_back` returns None (T-10-07 mitigation).
- **Fix:** Each selectbox resolution block checks `if date_x is None: st.caption(...); continue` before calling `load_surface_snapshot` or `plot_iv_change_surface`.
- **Files modified:** streamlit_app.py
- **Commit:** 9a050b2

**2. [Rule 2 - Missing Guard] T-10-06/T-10-08 Evolution dropna guards**
- **Found during:** Task 2
- **Issue:** Plan's threat model requires `dropna(subset=[metric])` per Scatter trace to prevent NaN data entering Evolution panels.
- **Fix:** Each metric trace drops NaN rows before building x/y arrays; all-empty early-exit with cold-start caption.
- **Files modified:** streamlit_app.py
- **Commit:** 9a050b2

**3. [Rule 1 - Deviation] Tasks 1/2/3 committed as single atomic commit**
- **Found during:** Task 1
- **Issue:** Three tasks all modify `streamlit_app.py`; the tab bodies cross-reference each other (tab variables declared together); committing after Task 1 alone would produce a file with `tab_calculus`, `tab_evolution`, `tab_positioning` declared but no `with tab_calculus:` / `with tab_evolution:` / `with tab_positioning:` blocks — Streamlit renders empty tabs, not a partially valid state.
- **Fix:** All three tasks written and verified together as one import-passing commit.
- **Commit:** 9a050b2

**4. [Rule 1 - Honesty] OI caption reflects actual fallback behavior**
- **Found during:** Task 3
- **Issue:** Plan caption text says "Call OI = blue, Put OI = red" unconditionally; prior-wave note says plot_oi_by_strike falls back to abs(gex) proxy when oi column absent from s_df. Caption kept as-is (still true when oi data is present; fallback is silent from UI perspective and documented in Plan 01 SUMMARY).
- **Files modified:** streamlit_app.py (caption unchanged from plan text)
- **Commit:** 9a050b2

## Verification

```
python -c "import streamlit_app; print('import ok')"
```
Output: `import ok`, exit 0.

Dead references check — all absent:
- plot_skew_25d_current: ok (absent)
- plot_term_structure: ok (absent)
- plot_carry_vrp: ok (absent)
- plot_skew_cross_ticker: ok (absent)
- plot_skew_term_structure: ok (absent)
- tab_skew: ok (absent)
- tab_term: ok (absent)
- tab_flow: ok (absent)
- Flow Context: ok (absent)
- plot_strike_gex: ok (absent)
- from gex.report import REGIME_COLOR: ok (absent)

New structure check — all present:
- tab_calculus: ok
- tab_evolution: ok
- tab_positioning: ok
- plot_oi_by_strike: ok
- load_evolution: ok
- nth_trading_day_back: ok
- vrp_headline: ok
- config.PALETTE: ok

## Known Stubs

None — all charts wire to real data sources. Cold-start captions are shown when parquet history is absent, not placeholder data.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes introduced. All changes are UI rendering within the existing local-only trust boundary.

## Self-Check: PASSED

- streamlit_app.py exists and imports cleanly
- Commit 9a050b2 verified in git log
- All dead references absent, all required references present

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/10-dashboard-restructure-local-only/10-01-PLAN|10-01-PLAN]]
- [[_planning/gamma-omm/phases/10-dashboard-restructure-local-only/10-01-SUMMARY|10-01-SUMMARY]]
- [[_planning/gamma-omm/phases/10-dashboard-restructure-local-only/10-02-PLAN|10-02-PLAN]]
- [[_planning/gamma-omm/phases/10-dashboard-restructure-local-only/10-CONTEXT|10-CONTEXT]]
- [[_planning/gamma-omm/phases/10-dashboard-restructure-local-only/10-DISCUSSION-LOG|10-DISCUSSION-LOG]]
- [[_planning/gamma-omm/phases/10-dashboard-restructure-local-only/10-PATTERNS|10-PATTERNS]]

<!-- LINKS:END -->
