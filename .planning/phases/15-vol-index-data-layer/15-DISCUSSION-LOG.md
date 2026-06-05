# Phase 15: Vol-Index Data Layer — Discussion Log

**Date:** 2026-06-04
*Human-reference record. Downstream agents consume 15-CONTEXT.md, not this file.*

## Framing

Identified phase 15 as a thin infrastructure phase — most of it is clear-cut (fetch CSV → cache → expose accessor), with the meaty user-facing decisions living in phases 16/17. Presented 3 genuine gray areas; user chose to lock all 3.

## Areas Discussed

### 1. Symbol scope
- **Options:** the 5 needed (symbol-agnostic module) | broader catalog now
- **Selected:** the 5 needed — VIX/VXN/RVX/VIX9D/VIX3M; fetcher works for any symbol, broader set is config not code.
- **Rationale:** don't-grab-noise principle; broader catalog unused until a decision needs it.

### 2. Cache storage + freshness
- **Options:** parquet in out/ + daily refresh | live fetch + st.cache_data TTL
- **Selected:** parquet under `out/vol_index/{SYM}.parquet`, refreshed daily (EOD), st.cache_data layered on for the app.
- **Rationale:** mirrors existing gex_snapshots/surface_history stores; files have homes; survives restarts.

### 3. History depth
- **Options:** full history | windowed (~10yr)
- **Selected:** full (VIX→1990, VXN/RVX→2009).
- **Rationale:** trivial storage; enables any percentile lookback in Phase 16 without re-fetch.

## Claude's Discretion
Module name/location, function signatures, CSV normalization, parquet schema, error/retry — left to planner. One guard: 403 symbols (e.g. discontinued VXST) fail soft, don't crash the batch.

## Deferred
- Broader vol-index catalog (VIX6M/VIX1Y/SKEW/VVIX) — config add-on later.
- Cross-asset vol indices + put/call archives — out of v3.5 boundary.
- Single-name historical IV — no free source, blocked.

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/15-vol-index-data-layer/15-CONTEXT|15-CONTEXT]]

<!-- LINKS:END -->
