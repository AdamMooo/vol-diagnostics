---
phase: 27-microstructure-monitor-ui
plan: 03
subsystem: ui
tags: [streamlit, plotly, evidence-panel, rank-space, smile-overlay, diff-surface, vrp, cold-start]

# Dependency graph
requires:
  - phase: 27-microstructure-monitor-ui (plan 01)
    provides: monitor_reader.load_rank_trail (full history) + vrp_history.vrp_components (vi/rv legs)
  - phase: 27-microstructure-monitor-ui (plan 02)
    provides: distribution board + selected_monitor_row (ticker, metric) selection hand-off
provides:
  - "Evidence panel (_render_evidence_panel) — scan→interrogate step; opens on board row selection"
  - "Rank-space rank-history chart with the config alert bands (entry/escalate/exit) as hline references"
  - "Per-metric mechanism dispatch reusing existing builders: smile overlay (skew/fly), diff surface (surface_level/rms), IV-vs-RV pair (vrp), term-ratio history (term)"
  - "Credibility caption flagging shallow history so a rank isn't mis-read as deep-history rarity"
affects: [27-04-event-email]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Nested @st.fragment (evidence panel inside the board fragment) — verified supported in Streamlit 1.59.2"
    - "Bands drawn in rank-space only (add_hline on a 0-100 axis), never on a raw value chart (RESEARCH Pitfall 2)"
    - "Pure figure-builder helpers (return go.Figure | None) split from the st.* fragment for unit-testability"
    - "Mechanism dispatch driven off the metric name via a _METRIC_MECHANISM map; reuse existing surface/VRP builders verbatim (no new signal)"
    - "Every mechanism branch degrades to a caption on None/sparse source (T-27-05)"

key-files:
  created: []
  modified:
    - app.py
    - engine/tests/test_app.py

key-decisions:
  - "Both plan tasks (rank chart + mechanism dispatch) live in one cohesive _render_evidence_panel fragment; committed atomically as a single feat rather than splitting hunks of the same function"
  - "Smile overlay uses build_surface_payload's smile_fit[0] (nearest fitted DTE) vs ks_grid for today and 5d — reuses the existing RBF fit, no new smile math"
  - "5d-ago surface resolved via _resolve_prior_surface, mirroring _surface_compare_section's anchor + nth_trading_day_back lookup"
  - "Unknown metrics fall back to the plain ratio value-history line (safe default, no engine reuse)"
  - "Sub-section headers use bold markdown (not a bespoke CSS class) to avoid depending on undefined styles"

patterns-established:
  - "Interrogate-layer evidence panel consuming Plan-01 reads + Plan-02 selection, cold-start safe"
  - "Rank-space band overlay as the canonical 'bands drawn' chart"

requirements-completed: [SC-2, SC-5, SC-6]

# Metrics
duration: ~20min
completed: 2026-07-27
---

# Phase 27 Plan 03: Microstructure Monitor Evidence Panel Summary

**Clicking a distribution-board row now opens an evidence panel: a rank-space rank-history chart with the config alert bands (entry/escalate/exit) drawn as reference lines, plus the correct mechanism view per metric family — near-expiry smile overlay (skew/fly), reused diff surface (surface_level/rms), implied-vs-realized VRP legs (vrp), and term-ratio value history — reusing the existing surface/VRP builders with no new signal.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-26T23:59Z
- **Completed:** 2026-07-27
- **Tasks:** 2 (rank chart + mechanism dispatch — landed in one cohesive fragment)
- **Files modified:** 2

## Accomplishments
- Added `@st.fragment _render_evidence_panel(selected, all_data)` dispatched from the board's `selected_monitor_row` selection, replacing the Plan 02 stub caption.
- Rank-space history chart (`_rank_history_figure`): `level_rank_deep` / `level_rank_1yr` / `change_rank` traces on a fixed 0-100 axis with `MONITOR_ALERT_BAND_ENTRY/ESCALATE/EXIT` as `add_hline` reference lines (RESEARCH Pitfall 2 — the bands are percentiles, drawn in rank-space only, never on a raw-value chart).
- Credibility caption (`_credibility_caption`) flags deep history below `MONITOR_CREDIBILITY_FLOOR_SESSIONS` as "not a deep-history rarity claim" (SC-5); a separate sparse note renders when ≤2 rank points exist.
- Per-metric mechanism dispatch (`_metric_mechanism` + helpers), all reusing existing builders (SC-6, no new math):
  - skew_25d / fly_25d → near-expiry smile overlay (`build_surface_payload` slices, today vs 5d).
  - surface_level / surface_rms → diff surface (`build_diff_payload` → `render_diff_html`), verbatim reuse.
  - vrp → implied (`vi`) vs realized (`rv×100`) legs from `vrp_components`.
  - term_9d_30 / term_30_3m → ratio value history from the monitor trail's `value` column.
- Every mechanism branch degrades to a caption on None/sparse source (T-27-05); sparse cold-start (1-2 rank points) renders markers, not an error.
- 7 new tests; suite 486 → 493 green; `app.py` imports/launches cleanly.

## Task Commits

1. **Evidence panel — rank-space band chart + per-metric mechanism views + tests** - `864cf56` (feat)

_The plan's two tasks (rank chart + mechanism dispatch) are inseparable hunks of the single `_render_evidence_panel` fragment, so they were committed atomically rather than splitting partial hunks of one function._

**Plan metadata:** (this SUMMARY + STATE/ROADMAP) committed separately.

## Files Created/Modified
- `app.py` — Added `vrp_components` import; `_load_rank_trail_full_cached` (n=None trail); evidence helpers `_metric_mechanism`, `_credibility_caption`, `_rank_history_figure`, `_smile_slice`, `_smile_overlay_figure`, `_vrp_iv_rv_figure`, `_term_ratio_figure`, `_resolve_prior_surface`; the `@st.fragment _render_evidence_panel`; replaced the board's Plan 02 evidence stub with a call to it.
- `engine/tests/test_app.py` — 7 Phase 27 Plan 03 tests: panel wiring contract (SC-2/SC-6), rank-space bands (SC-2), sparse/empty safety, credibility caption (SC-5), mechanism map coverage, mechanism figure None-degradation (T-27-05), mechanism figure happy-path.

## Decisions Made
- Committed both tasks as one atomic feat since the rank chart and mechanism dispatch are hunks of the same fragment (splitting would have meant staging partial hunks of one function).
- Smile overlay reuses `build_surface_payload`'s `smile_fit[0]` (nearest fitted DTE) against `ks_grid` for both dates — the existing RBF fit, no new smile/RBF code.
- Split all figure construction into pure `go.Figure | None` helpers so the drawing logic is unit-testable without a Streamlit runtime; the `st.*` glue lives only in the fragment.

## Deviations from Plan

None of substance — plan executed as written. One structural note: the plan lists two tasks, but both map to hunks of the single `_render_evidence_panel` fragment, so they were delivered in one atomic commit (`864cf56`) rather than two. No behavior or scope change.

## Issues Encountered
- Verified nested `@st.fragment` (evidence panel inside the already-fragment board section) is supported in Streamlit 1.59.2 via an `AppTest` probe before relying on it — no exception, both fragments render.

## Cold-Start Note
By design the panel is sparse right now: `out/monitor/ranks.parquet` holds ~2 dates and zero alerts have fired, so the rank-history chart shows 1-2 marker points with a sparse caption and the bands sit above the data. The mechanism views likewise caption-degrade where surface/VRP history is too short. This is the documented Phase 26/27 cold-start contract, not a bug — it fills in as `run_daily` accrues sessions.

## Threat Model Compliance
- **T-27-05 (DoS via sparse/None mechanism-view source):** mitigated — every dispatch branch guards None/sparse with a caption; tested (`test_phase27_mechanism_figures_degrade_on_none_source`). Reused surface/VRP builders already degrade to None on near-singular fits (Phase 25).
- **T-27-06 (info disclosure):** accepted per plan — no new data class or egress; read-only reshape/reuse of local parquet + surface snapshots.

## Known Stubs
None. The Plan 02 evidence stub caption is removed; all panels are wired to real reads (`load_rank_trail`, `vrp_components`, `build_surface_payload`/`build_diff_payload`). Sparse/empty renders are the intended cold-start contract, not stubs.

## Threat Flags
None — no new network endpoints, auth paths, or trust-boundary surface. Read-only reshape/reuse of already-persisted local ranks and surface snapshots.

## Next Phase Readiness
- Scan→interrogate loop complete (board + evidence panel). Plan 04 (event-shaped email) is unblocked; it consumes `load_recent_alert_events` from Plan 01, independent of this UI work.

## Self-Check: PASSED
- FOUND (modified): app.py
- FOUND (modified): engine/tests/test_app.py
- FOUND commit: 864cf56 (feat evidence panel + tests)
- FOUND: _render_evidence_panel in app.py
- FOUND: 493 tests green (486 → 493, +7)
- FOUND: app.py imports cleanly ("app.py imported OK")

---
*Phase: 27-microstructure-monitor-ui*
*Completed: 2026-07-27*
