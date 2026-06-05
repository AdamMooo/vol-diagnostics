---
phase: "06-computation-engine"
plan: "02"
subsystem: "gex"
tags: ["vol-surface", "streamlit", "noise-cuts", "analytics"]
dependency_graph:
  requires: []
  provides: ["plot_vol_surface-stripped-signature", "streamlit-noise-cuts"]
  affects: ["streamlit_app.py", "gex/analytics.py"]
tech_stack:
  added: []
  patterns: ["TDD red-green", "signature strip", "display noise removal"]
key_files:
  created:
    - "gex/tests/test_vol_surface_strip.py"
  modified:
    - "gex/analytics.py"
    - "streamlit_app.py"
decisions:
  - "Leave methodology expander text (mentions Hedge Sh / $1) unchanged — it is documentation, not display noise"
  - "TDD applied to analytics.py changes; streamlit_app.py edits covered by existing test suite"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-26"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 3
requirements:
  - INFRA-02
  - CTX-02
---

# Phase 06 Plan 02: Surface Strip and Noise Cuts Summary

**One-liner:** Stripped four GEX overlay params from `plot_vol_surface()`, changed colorscale to Viridis, and removed three noise metrics from the Streamlit dashboard (slope block, % vs ZGL, Hedge Sh / $1 row).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| RED | Failing tests for signature strip | f3c3cfe | gex/tests/test_vol_surface_strip.py |
| 1 GREEN | Strip GEX overlays from plot_vol_surface, Viridis | dc66959 | gex/analytics.py |
| 2 | Update call site and three noise cuts | 0062b35 | streamlit_app.py |

## What Changed

**gex/analytics.py — `plot_vol_surface()`:**
- Signature reduced from 7 params to 3: `(surface_df, ticker, spot)` only
- `iv30`, `gamma_flip`, `call_wall`, `put_wall` removed entirely
- `colorscale` changed from `"Plasma"` to `"Viridis"`
- `_meridian_iv()` helper removed
- `_add_meridian()` helper removed
- Three `_add_meridian()` call sites removed
- Translucent spot-plane `Mesh3d` trace removed
- `iv30_label` variable and title interpolation removed
- `legend=dict(...)` removed from `update_layout` (no legend items remain)

**streamlit_app.py — four edits:**
1. Call site: `plot_vol_surface(surface_df, ticker, spot=spot)` — no overlay args
2. Slope display block removed (strike_slope, term_slope, _pctile_label, sm1/sm2 columns, ~41 lines)
3. `% vs ZGL` observation removed from `_derive_observations()`
4. `Hedge Sh / $1` row removed from `render_regime_card` HTML and `df_val`/`df_str` computation

## Test Results

- 23 existing tests: all pass
- 6 new tests (test_vol_surface_strip.py): all pass
- Total: 29 passed, 0 failed

## Deviations from Plan

### Minor deviation

**Acceptance criterion `grep "Hedge Sh"` — residual match in methodology expander**

- **Found during:** Task 2 post-edit verification
- **Issue:** The plan's grep criterion `grep "Hedge Sh\|df_str\|df_val\|delta_hedge_flow"` would match a line in the methodology expander (line 333): `- **Hedge Sh / $1** — Γ_net × OI × 100...`
- **Decision:** Left unchanged. That line is academic methodology documentation, not a display metric. Removing it would suppress legitimate rigor context from the "Methodology & Assumptions" expander. The actual display code (df_val, df_str computation + HTML row) was removed correctly.
- **Files modified:** none (intentional non-removal)

## Known Stubs

None — all changes are deletions or signature reductions. No placeholder values introduced.

## Threat Flags

None — changes are pure removals. No new trust boundaries introduced. `plot_vol_surface` accepts the same `surface_df` and `spot` inputs as before; fewer parameters means a smaller attack surface.

## Self-Check: PASSED

- gex/analytics.py: FOUND
- streamlit_app.py: FOUND
- gex/tests/test_vol_surface_strip.py: FOUND
- 06-02-SUMMARY.md: FOUND
- Commits f3c3cfe, dc66959, 0062b35: all verified in git log
- 29 tests pass, 0 failed

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/agent-a5f61cc1c0eb582b7/ROADMAP|ROADMAP]] · [[_planning/agent-a5f61cc1c0eb582b7/STATE|STATE]]
**Phase siblings:**
- [[_planning/agent-a5f61cc1c0eb582b7/phases/06-computation-engine/06-01-PLAN|06-01-PLAN]]
- [[_planning/agent-a5f61cc1c0eb582b7/phases/06-computation-engine/06-02-PLAN|06-02-PLAN]]
- [[_planning/agent-a5f61cc1c0eb582b7/phases/06-computation-engine/06-03-PLAN|06-03-PLAN]]

<!-- LINKS:END -->
