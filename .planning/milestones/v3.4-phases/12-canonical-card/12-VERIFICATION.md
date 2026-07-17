---
phase: "12-canonical-card"
verified: "2026-06-01T23:30:00Z"
status: passed
score: "4/4 requirements verified"
overrides_applied: 0
---

# Phase 12: Canonical Card Verification Report

**Phase Goal:** A single canonical per-ticker card definition drives both the email and the Streamlit dashboard — VRP, signed 1-session scalar deltas on iv30/skew/net GEX, and "(model)" vs "(raw OI)" wall labels — so the two surfaces cannot drift apart.

**Verified:** 2026-06-01  
**Status:** PASSED  
**Requirements Verified:** 4/4 (CARD-01, CARD-02, CARD-03, CARD-04)

---

## Requirements Coverage

| REQ-ID | Description | Status | Evidence |
|--------|-------------|--------|----------|
| CARD-01 | Single canonical per-ticker card definition is source of truth for both email and Streamlit dashboard; dashboard card renders same fields as email card | ✓ COVERED | `gex/card_model.py:build_card_fields()` is the shared layer; `gex/report.py:_ticker_card()` line 102 calls `build_card_fields()`; `streamlit_app.py:render_regime_card()` line 161 calls `build_card_fields()`. Both iterate the same `CardField` list (label, value, sign). Tests: `test_report.py::TestCanonicalCardEmail` (9 tests) + `test_streamlit_app.py::TestRegimeCardCanonical` (6 tests) all PASS. |
| CARD-02 | VRP (IV30 − RV20) appears as a scalar field on the canonical card | ✓ COVERED | `gex/card_model.py:build_card_fields()` line 247-250 builds VRP field: `CardField(label="VRP", value=f"{vrp:+.1f}pp" if vrp is not None else "—", ...)`. Email test: `test_report.py::TestCanonicalCardEmail::test_vrp_row_present_with_value` asserts VRP row and `"+2.7pp"` found in HTML. Dashboard test: `test_streamlit_app.py::TestRegimeCardCanonical::test_vrp_row_present_with_value` asserts VRP row and value in rendered HTML. Both PASS. |
| CARD-03 | IV30, front skew (25Δ), and net GEX each display signed 1-session delta vs prior snapshot (raw signed number, e.g. `18.5% (+0.8)`); delta gracefully omits suffix when no prior | ✓ COVERED | `gex/card_model.py` implements delta logic: `_delta_suffix_b()` (line 126-132) and `_delta_suffix_pp()` (line 135-140) guard against None/NaN prior values. `build_card_fields()` line 190, 233, 243 apply deltas to iv30, net_gex, front_skew. NaN-guard test: `test_card_model.py::TestDeltaSuffixNaNGuard` (3 tests) verify no fabricated `(+nan)` or `(+0.0)`. Email tests `test_report.py::TestCanonicalCardEmail::test_net_gex_delta_present_with_prior` (PASS) and `test_net_gex_delta_absent_without_prior` (PASS). Dashboard test `test_streamlit_app.py::TestRegimeCardCanonical::test_delta_present_when_prior_row_supplied` (PASS) and `test_no_delta_when_no_prior_snapshot` (PASS). Prior snapshot sourced via `gex/validation.py:load_prior_snapshot()` (line 94-115), which returns `None` gracefully when store missing or no qualifying row. |
| CARD-04 | GEX-derived walls labelled "(model)" and open-interest walls "(raw OI)", consistently in both email and dashboard | ✓ COVERED | `gex/card_model.py:build_card_fields()` lines 252-277 hardcode wall labels: `"Call Wall (model)"`, `"Put Wall (model)"`, `"OI Call Wall (raw OI)"`, `"OI Put Wall (raw OI)"`. Email tests `test_report.py::TestCanonicalCardEmail::test_call_wall_model_label`, `test_put_wall_model_label`, `test_oi_call_wall_raw_oi_label`, `test_oi_put_wall_raw_oi_label` all PASS. Dashboard tests `test_streamlit_app.py::TestRegimeCardCanonical::test_wall_labels_model` and `test_wall_labels_raw_oi` PASS. Both surfaces iterate the same `CardField.label` field, so labels are identical. |

---

## Implementation Architecture

### Single Source of Truth: `gex/card_model.py`

**`CardField` dataclass (lines 145-149):**
- `label: str` — field name
- `value: str` — formatted value, including delta suffix and wall labels
- `sign: str` — "positive" | "negative" | "neutral" — used by renderers for accent colors

**`build_card_fields(today_summary, prior_summary, extras=None) -> list[CardField]` (lines 154-281):**
- Accepts today's summary dict and optional prior_summary (from snapshot store or None)
- Returns 14 ordered CardField objects:
  1. Spot
  2. Day %
  3. IV30 / 1d σ (with delta and expected move)
  4. γ-flip
  5. vs γ-flip
  6. Net GEX (with delta)
  7. Hedge Shares/$1
  8. Skew (25Δ) (with delta)
  9. VRP (NEW — CARD-02)
  10. Call Wall (model) (labeled per CARD-04)
  11. Put Wall (model) (labeled per CARD-04)
  12. Range
  13. OI Call Wall (raw OI) (labeled per CARD-04)
  14. OI Put Wall (raw OI) (labeled per CARD-04)
- Formatting and delta logic encapsulated, with graceful None/NaN handling
- Wall labels fixed at definition time — no drift possible

### Email Renderer: `gex/report.py:_ticker_card()`

**Lines 101-108:**
```python
prior_row = load_prior_snapshot(ticker=r["ticker"], before_date=datetime.date.today())
fields = build_card_fields(today_summary=r, prior_summary=prior_row)
left_fields = fields[:5]
right_fields = fields[5:]
left_rows = "".join(_kv_cell(f.label, f.value) for f in left_fields)
right_rows = "".join(_kv_cell(f.label, f.value) for f in right_fields)
```
- Delegates all field construction and formatting to shared layer
- Splits fields into left (5) and right (9) columns for two-column email layout
- Renders each field via `_kv_cell(label, value)` — HTML agnostic
- Formatting helpers (`_fmt_b`, `_fmt_price`, etc.) imported from `gex.card_model` (line 16-21)

### Dashboard Renderer: `streamlit_app.py:render_regime_card()`

**Lines 160-166:**
```python
prior_row = load_prior_snapshot(ticker=ticker, before_date=date.today())
fields = build_card_fields(today_summary=summary, prior_summary=prior_row)
grid_html = "".join(
    f'<span class="rc-k">{f.label}</span>'
    f'<span class="rc-v">{f.value}</span>'
    for f in fields
)
```
- Delegates all field construction and formatting to shared layer
- Builds CSS-grid HTML by iterating the same CardField list
- Both surfaces consume identical labels and values — no divergence possible

### Prior Snapshot Store: `gex/validation.py`

**Schema (lines 12-16, 31-37):**
- Parquet store `out/gex_snapshots.parquet` persists daily snapshots
- Columns include: `date, ticker, spot, net_gex, zero_gamma_level, call_wall, put_wall, front_skew, put_25d_iv, call_25d_iv, **iv30**, ...`
- `iv30` confirmed present in `_FLOAT_COLS` (line 33) — no schema change needed for CARD-03

**`load_prior_snapshot(ticker, before_date, store=None) -> pd.Series | None` (lines 94-115):**
- Returns most-recent row strictly before `before_date` for `ticker`
- Returns `None` if store missing, no qualifying rows, or read error
- Called by both `_ticker_card()` and `render_regime_card()` with `date.today()`

---

## Test Coverage

| Test File | Test Class/Function | Tests | Status |
|-----------|-------------------|-------|--------|
| `gex/tests/test_card_model.py` | CardField structure | 2 | PASS |
| | BuildCardFieldsNoPrior (VRP, wall labels) | 12 | PASS |
| | BuildCardFieldsWithPrior (deltas) | 4 | PASS |
| | DeltaSuffixNaNGuard (graceful None/NaN) | 3 | PASS |
| | CardFieldSigns (sign propagation) | 4 | PASS |
| **Subtotal** | | **25 tests** | **PASS** |
| `gex/tests/test_report.py` | TestCanonicalCardEmail | 9 | PASS |
| | (VRP, wall labels, deltas, no NaN leak) | | |
| **Subtotal** | | **9 tests** | **PASS** |
| `gex/tests/test_streamlit_app.py` | TestRegimeCardCanonical | 6 | PASS |
| | (VRP, wall labels, deltas, no NaN leak) | | |
| **Subtotal** | | **6 tests** | **PASS** |
| **Full Suite** | `gex/tests/` | **174 tests** | **ALL PASS** |

---

## Code Quality

### Anti-Patterns Scan

- **Debt markers:** None found (no TODO, FIXME, XXX, TBD, HACK comments)
- **Stub indicators:** None (`build_card_fields()` returns complete field list; no placeholder implementations)
- **Error handling:** Graceful None/NaN guards in `_safe_prior()` (line 109-123), `_delta_suffix_b()` (line 126-132), `_delta_suffix_pp()` (line 135-140)

### Wiring Verification

| Module | Component | Import | Usage | Status |
|--------|-----------|--------|-------|--------|
| `gex/report.py` | _ticker_card | line 16-17: `from gex.card_model import CardField, build_card_fields` | line 102: `build_card_fields()` called | ✓ WIRED |
| | | line 22: `from gex.validation import load_prior_snapshot` | line 101: `load_prior_snapshot()` called | ✓ WIRED |
| `streamlit_app.py` | render_regime_card | line 11: `from gex.card_model import CardField, build_card_fields` | line 161: `build_card_fields()` called | ✓ WIRED |
| | | line 12: `from gex.validation import load_prior_snapshot` | line 160: `load_prior_snapshot()` called | ✓ WIRED |

### Data-Flow Trace (Level 4)

**Card field values come from:**
1. `today_summary` — passed from `compute_ticker()` output (already in production)
2. `prior_summary` — loaded via `load_prior_snapshot()` from parquet store
3. Formatters apply transformations (B units, pp, %, etc.) — deterministic, no external dependencies

**Example: Net GEX delta**
- Today: `net_gex` from `compute_ticker()`
- Prior: `net_gex` loaded from `out/gex_snapshots.parquet` (persisted daily)
- Delta: `_delta_suffix_b(today_val, prior_val)` computes raw difference
- Result: e.g., `+1.05B (+0.05B)`

All values are sourced from local data (no API calls, no external services). No data-hollow risk.

---

## Scope Adherence

### In Scope (Delivered)

✓ Single canonical `build_card_fields()` consumed by both renderers (CARD-01)  
✓ VRP field on card (CARD-02)  
✓ Signed 1-session deltas for iv30, front_skew, net_gex (CARD-03)  
✓ "(model)" vs "(raw OI)" wall labels (CARD-04)  
✓ Prior snapshot schema confirmed (iv30 already persisted)  
✓ Graceful handling when prior snapshot missing/NaN  

### Out of Scope (Correctly Excluded)

✗ VRP sparkline or percentiles (Phase 14 — accumulation gating)  
✗ 1-day ΔIV surface PNGs (Phase 13)  
✗ Dashboard 3D Surface page or Compare tab modifications (explicitly untouched)  
✗ New accumulation-dependent metrics  

---

## Verification Summary

**Goal:** A single canonical per-ticker card definition drives both email and Streamlit dashboard, with VRP, signed 1-session deltas, and clear OI-vs-GEX wall labelling.

**Achieved:** Yes. `gex/card_model.py:build_card_fields()` is the single source of truth. Both `gex/report.py:_ticker_card()` and `streamlit_app.py:render_regime_card()` call the same function, iterate its output, and render identical field labels and values. Wall labels are defined in `build_card_fields()` — no duplication, no drift risk. VRP field is present (CARD-02). Deltas are computed and formatted in the shared layer (CARD-03). All 4 requirements verified.

**Test Evidence:** 174 tests passing (25 card_model + 9 email + 6 dashboard + 134 existing); no failures; specific CARD tests confirm VRP presence, delta behavior, wall label consistency, and graceful NaN handling in both surfaces.

**Code Quality:** No debt markers, no stubs, proper wiring. Architecture enforces single source of truth — the two renderers cannot drift because they consume identical field definitions.

---

_Verified: 2026-06-01T23:30:00Z_  
_Verifier: Claude (gsd-verifier)_

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
- [[_planning/gamma-omm/phases/12-canonical-card/12-03-SUMMARY|12-03-SUMMARY]]
- [[_planning/gamma-omm/phases/12-canonical-card/12-CONTEXT|12-CONTEXT]]

<!-- LINKS:END -->
