---
phase: 07-institutional-dashboard-rendering
plan: "01"
subsystem: gex/analytics
tags: [charts, plotly, vol-diagnostics, tdd]
dependency_graph:
  requires: []
  provides: [plot_skew_25d_current, plot_term_structure, plot_carry_vrp]
  affects: [streamlit_app.py, gex/compute.py]
tech_stack:
  added: []
  patterns: [empty-data-guard, plotly-dark-template, hovertemplate-extra]
key_files:
  created: [gex/tests/test_analytics_charts_p7.py]
  modified: [gex/analytics.py]
decisions:
  - "classification label from plot_term_structure injected verbatim from vol_metrics — no editorial gloss"
  - "plot_carry_vrp uses `or 0.0` pattern for None inputs — Bar renders 0 not TypeError"
  - "unit conversion responsibility stays with caller — analytics.py renders, does not convert"
metrics:
  duration: "1m 41s"
  completed: 2026-05-26
---

# Phase 7 Plan 01: Analytics Chart Functions Summary

**One-liner:** Three Plotly rendering primitives for Phase 7 vol-diagnostics tabs — skew, term structure, and VRP carry — with full None/empty guards and 6 smoke tests.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing smoke tests | ed2ae3d | gex/tests/test_analytics_charts_p7.py |
| 1/2 (GREEN) | Implement all 3 chart functions | aa56018 | gex/analytics.py |

## What Was Built

Three functions appended to `gex/analytics.py` (after `plot_skew_term_structure`, line 301):

- **`plot_skew_25d_current(skew, ticker)`** — bar chart of 25Δ put-call skew for front/second month expiries. Amber bars (#f59e0b). Empty guard returns titled empty figure when both buckets are None.

- **`plot_term_structure(ts, ticker)`** — ATM IV scatter line chart. Classification word ("normal" / "flat" / "inverted" / "humped") injected verbatim into title with no editorial suffix. Empty guard on `points == []`.

- **`plot_carry_vrp(iv30_pct, rv20_pct, vrp_pp, ticker)`** — grouped bar chart of IV30 vs RV20. VRP spread shown in title as "+2.2pp" or "n/a (cold start)". None inputs render as 0.0 via `or 0.0` guard. Caller responsible for unit conversion (pct, not decimal).

All three follow the existing `plotly_dark` template and `margin=dict(t=50, b=40, l=65, r=20)` convention from the rest of analytics.py.

## Test Results

- 6 new smoke tests: **6 passed**
- Full suite: **66 passed** (60 existing + 6 new), 0 regressions

## Deviations from Plan

None — plan executed exactly as written. TDD gate sequence followed: RED commit (ed2ae3d) before GREEN commit (aa56018).

## TDD Gate Compliance

| Gate | Commit | Message |
|------|--------|---------|
| RED | ed2ae3d | test(07-01): add failing smoke tests for 3 Phase 7 chart functions |
| GREEN | aa56018 | feat(07-01): add plot_skew_25d_current, plot_term_structure, plot_carry_vrp to analytics.py |

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or file access patterns introduced. All inputs are dict/float values from compute_ticker() (local in-process data).

## Self-Check: PASSED

- `gex/analytics.py` modified: FOUND
- `gex/tests/test_analytics_charts_p7.py` created: FOUND
- RED commit ed2ae3d: FOUND
- GREEN commit aa56018: FOUND
- 66 tests pass: VERIFIED

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/07-institutional-dashboard-rendering/07-01-PLAN|07-01-PLAN]]
- [[_planning/gamma-omm/phases/07-institutional-dashboard-rendering/07-02-PLAN|07-02-PLAN]]
- [[_planning/gamma-omm/phases/07-institutional-dashboard-rendering/07-PATTERNS|07-PATTERNS]]
- [[_planning/gamma-omm/phases/07-institutional-dashboard-rendering/07-RESEARCH|07-RESEARCH]]

<!-- LINKS:END -->
