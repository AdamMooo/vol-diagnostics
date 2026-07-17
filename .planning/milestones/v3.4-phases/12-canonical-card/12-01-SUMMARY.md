---
phase: "12-canonical-card"
plan: "01"
subsystem: "card-model"
tags: [card-model, validation, snapshot, delta, formatting]
dependency_graph:
  requires: []
  provides: [gex.card_model.CardField, gex.card_model.build_card_fields, gex.validation.load_prior_snapshot]
  affects: [gex/report.py, streamlit_app.py]
tech_stack:
  added: []
  patterns: [dataclass, TDD red-green]
key_files:
  created:
    - gex/card_model.py
    - gex/tests/test_card_model.py
  modified:
    - gex/validation.py
    - gex/tests/test_validation_schema.py
decisions:
  - "Formatters moved to card_model.py; report.py will import from there in plan 02 — avoids duplication"
  - "iv30 already in _FLOAT_COLS and save_snapshot — no schema change needed, only load_prior_snapshot was missing"
  - "_wall_value in card_model.py uses plain text % (no HTML span) so it's renderer-agnostic; report.py can add span in plan 02"
metrics:
  duration: "~15 min"
  completed: "2026-06-01"
  tests_added: 32
  tests_total: 158
---

# Phase 12 Plan 01: Canonical Card Model Summary

CardField dataclass + build_card_fields() shared layer; load_prior_snapshot helper; iv30 schema confirmed.

## What Was Built

**gex/card_model.py** — new module, single source of truth for the per-ticker card:
- `CardField` dataclass: `label: str`, `value: str`, `sign: str`
- `build_card_fields(today_summary, prior_summary, extras)` — returns 14 `CardField` objects in canonical order
- All formatting helpers migrated here: `_fmt_b`, `_fmt_price`, `_fmt_pct`, `_fmt_skew`, `_fmt_hedge_shares`, `_pct_from_spot`, `_wall_value`, `_expected_1d_range_pct`, `_pin_location`, `_signed_color`
- Delta suffix logic: omitted when prior is None/NaN; applied for `iv30`, `net_gex`, `front_skew`
- OI walls labeled `(raw OI)`, GEX walls labeled `(model)` per CARD-04
- VRP field: `f"{vrp:+.1f}pp"` per CARD-02

**gex/validation.py** — `load_prior_snapshot(ticker, before_date, store=None) -> pd.Series | None` added:
- Returns most-recent row strictly before `before_date` for `ticker`
- Returns `None` if store missing, no qualifying rows, or any read error
- `iv30` confirmed already present in `_FLOAT_COLS` and `save_snapshot` row dict — no schema change needed

**Tests:** 32 new tests across `test_card_model.py` (25) and `test_validation_schema.py` (7 new assertions)

## Deviations from Plan

**1. [Rule 1 - Minor] _wall_value HTML span removed**
- **Found during:** Task 2 implementation
- **Issue:** report.py's `_wall_value` uses an HTML `<span>` for the distance %, which is email-renderer-specific; card_model.py's version is consumed by both email and dashboard renderers
- **Fix:** card_model.py `_wall_value` formats as plain `"level pct%"` text (renderer-agnostic). report.py will re-wrap in its `<span>` when it imports from card_model in plan 02.
- **Files modified:** gex/card_model.py
- **Impact:** No test impact — all tests pass; the visual difference is handled in plan 02 when report.py is updated

## Self-Check: PASSED

- FOUND: gex/card_model.py
- FOUND: gex/validation.py
- FOUND: gex/tests/test_card_model.py
- FOUND: gex/tests/test_validation_schema.py
- FOUND: commit ce61dcf (test: failing tests load_prior_snapshot)
- FOUND: commit a467690 (feat: load_prior_snapshot implementation)
- FOUND: commit 7b26d9e (test: failing tests CardField + build_card_fields)
- FOUND: commit 4d47b9b (feat: card_model.py implementation)
- 158 tests passing, 0 failures

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/12-canonical-card/12-01-PLAN|12-01-PLAN]]
- [[_planning/gamma-omm/phases/12-canonical-card/12-02-PLAN|12-02-PLAN]]
- [[_planning/gamma-omm/phases/12-canonical-card/12-03-PLAN|12-03-PLAN]]
- [[_planning/gamma-omm/phases/12-canonical-card/12-CONTEXT|12-CONTEXT]]

<!-- LINKS:END -->
