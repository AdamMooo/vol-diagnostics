---
phase: "12-canonical-card"
plan: "03"
subsystem: "dashboard-renderer"
tags: [streamlit, card-model, delta, vrp, wall-labels]
dependency_graph:
  requires: [gex.card_model.CardField, gex.card_model.build_card_fields, gex.validation.load_prior_snapshot]
  provides: [streamlit_app.render_regime_card-canonical]
  affects: [streamlit_app.py, gex/tests/test_streamlit_app.py]
tech_stack:
  added: []
  patterns: [import-from-shared-layer, TDD red-green]
key_files:
  created: []
  modified:
    - streamlit_app.py
    - gex/tests/test_streamlit_app.py
decisions:
  - "render_regime_card delegates all field construction to build_card_fields(); no local field variables remain"
  - "patch target for load_prior_snapshot in tests is streamlit_app.load_prior_snapshot (not gex.validation.load_prior_snapshot) — from-import creates a direct reference"
  - "col.markdown call_args captured from MagicMock col argument, not from st.markdown — render_regime_card calls col.markdown not st.markdown"
metrics:
  duration: "~10 min"
  completed: "2026-06-01"
  tests_added: 7
  tests_total: 174
---

# Phase 12 Plan 03: Dashboard Renderer Canonical Card Summary

`render_regime_card()` refactored to iterate `build_card_fields()` output; VRP, delta suffixes, and wall type labels now driven by the shared layer, closing CARD-01/02/03/04 on the dashboard side.

## What Was Built

**streamlit_app.py** — `render_regime_card()` rewritten:
- Added imports: `CardField`, `build_card_fields` from `gex.card_model`; `load_prior_snapshot` from `gex.validation`; `date` from `datetime`
- `render_regime_card()` now: calls `load_prior_snapshot(ticker, date.today())` → passes to `build_card_fields(today_summary, prior_summary)` → builds `rc-grid` HTML by iterating `CardField` list
- Removed hand-coded `spot_str`, `net_gex_b`, `zgl_str`, `iv30_str`, `skew_str` local variables
- Removed `_derive_observations` call and `.rc-obs` div from card HTML
- `_derive_observations` function definition left in place (not called from `render_regime_card`; other code may reference it)
- Accent color logic unchanged (sign of net_gex → palette → bg)
- Net reduction: 22 lines removed, 10 added in `render_regime_card`

**gex/tests/test_streamlit_app.py** — `TestRegimeCardCanonical` class added (6 tests):
- CARD-02: VRP row present with value; VRP row present showing `—` when `vrp=None`
- CARD-04: `Call Wall (model)` / `Put Wall (model)` label assertions; `OI Call Wall (raw OI)` / `OI Put Wall (raw OI)` label assertions
- CARD-03: `(+` delta suffix present when prior row supplied; no `(+nan)` / `(+0.0)` when no prior row
- Helper `_render_regime_card_html` patches `streamlit_app.load_prior_snapshot` (correct patch site for from-imports); captures HTML from `col.markdown.call_args_list`

## Deviations from Plan

**1. [Rule 1 - Bug] Patch target corrected from gex.validation to streamlit_app**
- **Found during:** Task 2 test implementation
- **Issue:** Plan specified `mock.patch("gex.validation.load_prior_snapshot", ...)`. `streamlit_app` does `from gex.validation import load_prior_snapshot` — this creates a direct local reference in `streamlit_app`'s namespace. Patching `gex.validation.load_prior_snapshot` replaces the attribute on the source module but `streamlit_app.load_prior_snapshot` still points to the original object, so the patch has no effect.
- **Fix:** Patch target changed to `"streamlit_app.load_prior_snapshot"` — replaces the name in the module that actually calls it.
- **Files modified:** gex/tests/test_streamlit_app.py
- **Commit:** 1f3041b

**2. [Rule 1 - Bug] HTML capture via col.markdown, not st.markdown**
- **Found during:** Task 2 first test run (HTML was empty string)
- **Issue:** `render_regime_card` calls `col.markdown(...)` on its `col` argument, not `streamlit.markdown`. Patching `streamlit.markdown` doesn't intercept it.
- **Fix:** Helper captures from `col.markdown.call_args_list` on the `MagicMock()` col object.
- **Files modified:** gex/tests/test_streamlit_app.py
- **Commit:** 1f3041b

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or trust boundary changes. `load_prior_snapshot` reads local parquet only; values formatted from numeric inputs with no user-controlled strings reaching HTML (T-12-03/T-12-04 accepted per plan threat model).

## Self-Check: PASSED

- FOUND: streamlit_app.py (modified — `from gex.card_model import`)
- FOUND: gex/tests/test_streamlit_app.py (modified — `TestRegimeCardCanonical`)
- FOUND: commit 8a05878 (feat(12-03): refactor render_regime_card)
- FOUND: commit 1f3041b (test(12-03): add TestRegimeCardCanonical)
- 174 tests passing, 0 failures
- `python -m py_compile streamlit_app.py` exits 0

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/12-canonical-card/12-01-PLAN|12-01-PLAN]]
- [[_planning/gamma-omm/phases/12-canonical-card/12-01-SUMMARY|12-01-SUMMARY]]
- [[_planning/gamma-omm/phases/12-canonical-card/12-02-PLAN|12-02-PLAN]]
- [[_planning/gamma-omm/phases/12-canonical-card/12-02-SUMMARY|12-02-SUMMARY]]
- [[_planning/gamma-omm/phases/12-canonical-card/12-03-PLAN|12-03-PLAN]]
- [[_planning/gamma-omm/phases/12-canonical-card/12-CONTEXT|12-CONTEXT]]

<!-- LINKS:END -->
