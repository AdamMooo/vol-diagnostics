# Phase 18: 3-Page Reorg + Email Parity + Gating - Pattern Map

**Mapped:** 2026-06-24

## Primary Reuse Targets

| File to modify | Closest analog | Why |
|---|---|---|
| `app.py` | `app.py` | Existing tab/page composition and section extractors already present |
| `engine/report/card_model.py` | `engine/report/card_model.py` | Canonical field ordering/formatting/trust-tag seam |
| `engine/report/report.py` | `engine/report/report.py` | Email consumes canonical fields and already has cold-start omit behavior |
| `engine/tests/test_app.py` | `engine/tests/test_app.py` | Existing UI contract tests for compact split + trust tags |
| `engine/tests/test_report.py` | `engine/tests/test_report.py` | Existing email parity and omission tests |
| `engine/tests/test_card_model.py` | `engine/tests/test_card_model.py` | Existing compact field order/trust-tag contract tests |

## Confirmed Code Patterns

### 1. Canonical card parity seam
- Dashboard path uses:
  - `load_prior_snapshot(...)`
  - `build_card_fields(today_summary=..., prior_summary=...)`
  - `split_compact_fields(...)`
- Email path uses the same `build_card_fields(...)` + `split_compact_fields(...)`.

**Implication for Phase 18:** keep page-1 snapshot and email on this seam; do not add renderer-local field assembly.

### 2. Compact-vs-detail hierarchy contract
- `split_compact_fields()` already exists in `card_model.py`.
- `COMPACT_PRIMARY_LABELS` defines default compact ordering.

**Implication for Phase 18:** implement regime-first compact set by updating this canonical list/selection logic, not by per-renderer filtering.

### 3. Metric-specific history gating language
- `card_model.py` already emits explicit strings like:
  - `... sessions (building to {lookback})`
- `compute.py` already precomputes history-dependent read values with floor logic.

**Implication for Phase 18:** reuse and extend existing per-metric gating strings/counts; avoid generic "insufficient data" only messaging for page-1 metrics.

### 4. Cold-start section omission pattern
- `report.py` omits evolution section when values are absent.
- `app.py` uses explicit captions/info when history depth is insufficient.

**Implication for Phase 18:** card-level history reads can show "building" rows; panel-level components should stay omitted/captioned rather than empty shells.

## Concrete Excerpts to Mirror

### Dashboard canonical seam (from `app.py`)
```python
prior_row = load_prior_snapshot(ticker=ticker, before_date=date.today())
fields = build_card_fields(today_summary=summary, prior_summary=prior_row)
primary_fields, detail_fields = split_compact_fields(fields)
```

### Email canonical seam (from `engine/report/report.py`)
```python
prior_row = load_prior_snapshot(ticker=r["ticker"], before_date=datetime.date.today())
fields = build_card_fields(today_summary=r, prior_summary=prior_row)
primary_fields, detail_fields = split_compact_fields(fields)
```

### Card-model gating pattern (from `engine/report/card_model.py`)
```python
return f"{base} · {vrp_pct_n} sessions (building to {lookback})"
```

## Pattern Guardrails for Planner

1. Keep page split in `app.py` only (no new app entry points).
2. Keep canonical parity in `card_model.py` as single source of truth.
3. Keep email parity checks warning-grade (per Phase 18 context), not hard fail.
4. Keep term-ratio omission symmetric for unavailable tickers across both surfaces.

## PATTERN MAPPING COMPLETE
