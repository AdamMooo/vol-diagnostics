---
phase: "12-canonical-card"
plan: "02"
subsystem: "email-renderer"
tags: [email, card-model, report, delta, vrp, wall-labels]
dependency_graph:
  requires: [gex.card_model.CardField, gex.card_model.build_card_fields, gex.validation.load_prior_snapshot]
  provides: [gex.report._ticker_card-canonical]
  affects: [gex/report.py, gex/tests/test_report.py]
tech_stack:
  added: []
  patterns: [import-from-shared-layer, TDD green]
key_files:
  created: []
  modified:
    - gex/report.py
    - gex/tests/test_report.py
decisions:
  - "_ticker_card() delegates all field construction to build_card_fields(); no local field logic remains"
  - "Formatting helpers removed from report.py body; single import block from gex.card_model"
  - "load_prior_snapshot called inside _ticker_card with datetime.date.today(); prior_row passed to build_card_fields"
  - "wall values from card_model._wall_value are plain text (no HTML span); accepted — _kv_cell renders them in the value cell without a span"
metrics:
  duration: "~10 min"
  completed: "2026-06-01"
  tests_added: 9
  tests_total: 167
---

# Phase 12 Plan 02: Email Renderer Canonical Card Summary

`_ticker_card()` refactored to iterate `build_card_fields()` output; VRP row, delta suffixes, and wall type labels now driven by the shared layer.

## What Was Built

**gex/report.py** — `_ticker_card()` rewritten:
- Imports `CardField`, `build_card_fields` from `gex.card_model`
- Imports `load_prior_snapshot` from `gex.validation`
- All 10 formatting helper bodies removed from module body; replaced with single import block from `gex.card_model`
- `_ticker_card()` now: calls `load_prior_snapshot(ticker, datetime.date.today())` → passes to `build_card_fields(today_summary=r, prior_summary=prior_row)` → splits into `fields[:5]` (left) and `fields[5:]` (right) → iterates via `_kv_cell(f.label, f.value)` for each
- Accent bar color logic unchanged (driven by `net_gex` sign, HTML layout concern)
- Error path unchanged
- Net reduction: 138 lines removed, 13 added

**gex/tests/test_report.py** — 9 new tests in `TestCanonicalCardEmail`:
- CARD-02: VRP row present with value; VRP row present showing `—` when `vrp=None`
- CARD-04: `Call Wall (model)` and `Put Wall (model)` label assertions; `OI Call Wall (raw OI)` and `OI Put Wall (raw OI)` label assertions
- CARD-03: net_gex delta `(+...)` suffix present when prior row supplied; absent (no `(+nan)`, no `(+0...`) when no prior row; no `nan` leak when no prior snapshot
- `_minimal_result` fixture updated with `vrp=None`, `rv20=None` defaults

## Deviations from Plan

**1. [Rule 1 - Minor] _wall_value HTML span not restored**
- **Found during:** Task 1 implementation review
- **Issue:** The plan's context note said "report.py must restore its own span/HTML wrapping" for `_wall_value`. However, the plan action (step 3e–g) says to call `_kv_cell(f.label, f.value)` directly using `CardField.value` from `build_card_fields()`. The `CardField.value` for wall fields is already the plain-text output of `card_model._wall_value`. Adding a span wrapper would require overriding `CardField.value` selectively, which contradicts the "iterate the list" architecture.
- **Decision:** Plain-text wall values (e.g., `"510  +2.0%"`) render correctly in `_kv_cell`'s value `<td>`. The HTML span was cosmetic (bold + margin on the distance %). Removed cleanly; no functional gap.
- **Files modified:** gex/report.py (no span restoration)

## Self-Check

- FOUND: gex/report.py (modified)
- FOUND: gex/tests/test_report.py (modified)
- FOUND: commit cc7bb6c (feat(12-02): refactor _ticker_card())
- FOUND: commit 5e9ea1c (test(12-02): add TestCanonicalCardEmail)
- 167 tests passing, 0 failures

## Self-Check: PASSED

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/12-canonical-card/12-01-PLAN|12-01-PLAN]]
- [[_planning/gamma-omm/phases/12-canonical-card/12-01-SUMMARY|12-01-SUMMARY]]
- [[_planning/gamma-omm/phases/12-canonical-card/12-02-PLAN|12-02-PLAN]]
- [[_planning/gamma-omm/phases/12-canonical-card/12-03-PLAN|12-03-PLAN]]
- [[_planning/gamma-omm/phases/12-canonical-card/12-CONTEXT|12-CONTEXT]]

<!-- LINKS:END -->
