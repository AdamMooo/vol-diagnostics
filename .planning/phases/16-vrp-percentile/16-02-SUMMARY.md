---
phase: 16-vrp-percentile
plan: 02
subsystem: vol-metrics
tags: [vrp, percentile, vol-index, card, par-01, vrp-03]
requires: [gex.vrp_history.vrp_percentile, config.VRP_PERCENTILE_LOOKBACK]
provides: [summary.vrp-vol-index-basis, summary.vrp_pct, summary.vrp_pct_n, card_model.VRP-field]
affects: [gex/report.py, streamlit_app.py]
tech-stack:
  added: []
  patterns: [precompute-in-engine, pure-card-builder, par-01-single-seam, vrp-03-single-series]
key-files:
  created: []
  modified: [gex/compute.py, gex/card_model.py, gex/tests/test_card_model.py, gex/tests/test_compute_wiring.py]
decisions:
  - "Displayed VRP scalar switched from snapshot.iv30 − RV20 to vol_index − RV20 (LOCKED CONTEXT) — scalar and percentile share one series, cannot drift"
  - "vrp_pct/vrp_pct_n precomputed in compute_ticker; build_card_fields stays I/O-free"
  - "One VRP CardField at index 8 (after Skew) reaches both email and dashboard via the PAR-01 seam"
  - "Cold-start labels actual count ('building to 252'); None vrp/pct → 'insufficient history', never NaN"
metrics:
  duration: ~12m
  completed: 2026-06-16
requirements: [VRP-01, VRP-02, VRP-03]
---

# Phase 16 Plan 02: VRP Percentile Wiring Summary

Wired the 16-01 VRP-percentile engine into the live pipeline: the displayed VRP scalar now uses the vol-index basis (vol_index − RV20), the percentile is precomputed in `compute_ticker`, and a single `CardField` surfaces VRP + labeled percentile in both the daily email and the Streamlit dashboard through the one PAR-01 seam.

## What Was Built

- **`gex/compute.py`** — Imported `vrp_percentile`; dropped the now-unused `compute_vrp` import. Replaced the snapshot-IV30 VRP block: `summary["vrp"]` now derives from `vrp_percentile(ticker)["vrp"]` (vol points, VRP-03 clean), and `summary["vrp_pct"]` / `summary["vrp_pct_n"]` are precomputed alongside. `summary["rv20"]` still populated from the existing spot_series path for unchanged consumers. Widened `_fetch_spot_history_yf` default `35d → 400d` so a 252-session RV20 series is buildable. Return-dict `"vrp"` key and docstring updated to the vol-index basis.
- **`gex/card_model.py`** — Added pure `_fmt_vrp(vrp, vrp_pct, vrp_pct_n)` formatter (no I/O) and a `CardField(label="VRP", ...)` inserted at index 8 (after Skew, before Call Wall). Threshold reads `config.VRP_PERCENTILE_LOOKBACK` — no hard-coded lookback. Sign via existing `_get_sign(vrp)`.
- **`gex/tests/test_card_model.py`** — Added `TestVRPCardField`: full-lookback label, cold-start ("building to N"), insufficient-history fallback (vrp None and pct-None-with-scalar), scalar-only, and sign positive/negative. (The pre-staged EXPECTED_LABELS/field-order/formatted-value assertions also now pass.)
- **`gex/tests/test_compute_wiring.py`** — Updated for the new VRP basis: mock `vrp_percentile` and `_fetch_spot_history_yf` (no network in tests); cold-start test now asserts `vrp` None via the engine's None-dict plus `vrp_pct`/`vrp_pct_n`.

## VRP Card Output (verified)

- Full lookback: `+2.7pp · 74th %ile · 252-session lookback`
- Cold-start: `+2.7pp · 74th %ile · 120 sessions (building to 252)`
- Fallback (None): `insufficient history`
- 14 fields total; VRP lands in the right column (`fields[5:]`) next to Skew — email layout reads cleanly, no report.py change needed (cosmetic split confirmed).

## Verification

- `python -m pytest gex/tests/test_card_model.py gex/tests/test_vrp_history.py -q` → **38 passed**.
- `python -c "from gex.compute import compute_ticker"` → imports cleanly.
- Full suite: **205 passed, 6 failed** — the 6 failures are pre-existing and out of scope (see Deferred Issues).
- Grep gates: no hard-coded lookback in VRP logic (sole `252` hit is the pre-existing `252**0.5` annualization in `_expected_1d_range_pct`); no I/O added to `card_model.py`.

## Deviations from Plan

**1. [Rule 1 - Test correction] Updated test_compute_wiring cold-start for the new VRP basis**
- **Found during:** Full-suite verification (Task 2).
- **Issue:** `test_cold_start_rv20_and_vrp_are_none` encoded the OLD contract (vrp = iv30 − rv20, None when `load_history` empty). Under the LOCKED CONTEXT decision, `vrp` no longer depends on the spot_series path — it comes from `vrp_percentile`. The unmocked engine + widened fetch made the test hit the network and return real values.
- **Fix:** Mocked `vrp_percentile` (None-dict) and `_fetch_spot_history_yf` (None) in all three test bodies so they are deterministic and network-free; cold-start now asserts vrp None via the engine plus `vrp_pct`/`vrp_pct_n`.
- **Files modified:** `gex/tests/test_compute_wiring.py`
- **Commit:** b7e818c

## Deferred Issues (out of scope)

6 pre-existing failures in `gex/tests/test_run_daily_pngs.py` — the suite patches `gex.run_daily.plot_iv_change_surface`, an attribute that no longer exists on `run_daily.py` (the test was last touched in Phase 13; run_daily last in Phase 15). Not caused by this plan. Logged to `deferred-items.md`.

## Commits

- `c7e5a08` feat(16-02): switch VRP scalar to vol-index basis, precompute percentile in compute_ticker
- `2b7d72e` test(16-02): add failing tests for VRP card field (RED)
- `f5654f0` feat(16-02): add VRP CardField sourced from precomputed summary (GREEN)
- `b7e818c` test(16-02): update compute_wiring for vol-index VRP basis

## TDD Gate Compliance

Task 2 RED (`test(16-02)` @ 2b7d72e — VRP field missing, StopIteration) → GREEN (`feat(16-02)` @ f5654f0). Task 1 carried its own pre-staged tests (card_model EXPECTED_LABELS already in RED before this plan) plus the static-import verify. No refactor commit needed.

## Self-Check: PASSED

- FOUND: gex/compute.py, gex/card_model.py, gex/tests/test_card_model.py, gex/tests/test_compute_wiring.py
- FOUND commits: c7e5a08, 2b7d72e, f5654f0, b7e818c

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/16-vrp-percentile/16-01-PLAN|16-01-PLAN]]
- [[_planning/gamma-omm/phases/16-vrp-percentile/16-01-SUMMARY|16-01-SUMMARY]]
- [[_planning/gamma-omm/phases/16-vrp-percentile/16-02-PLAN|16-02-PLAN]]
- [[_planning/gamma-omm/phases/16-vrp-percentile/16-CONTEXT|16-CONTEXT]]
- [[_planning/gamma-omm/phases/16-vrp-percentile/16-RESEARCH|16-RESEARCH]]
- [[_planning/gamma-omm/phases/16-vrp-percentile/deferred-items|deferred-items]]

<!-- LINKS:END -->
