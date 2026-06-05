---
phase: 06-computation-engine
plan: "04"
subsystem: gex
tags: [gap-closure, vrp, testing, methodology]
dependency_graph:
  requires: ["06-01", "06-03"]
  provides: ["correct VRP values in parquet snapshots", "effective cold-start mock isolation"]
  affects: ["gex/compute.py", "gex/vol_metrics.py", "gex/tests/test_vol_metrics.py", "gex/tests/test_compute_wiring.py", "streamlit_app.py"]
tech_stack:
  added: []
  patterns: ["decimal-fraction convention for vol metrics", "mock.patch.object for import-bound names"]
key_files:
  created: []
  modified:
    - gex/compute.py
    - gex/vol_metrics.py
    - gex/tests/test_vol_metrics.py
    - gex/tests/test_compute_wiring.py
    - streamlit_app.py
decisions:
  - "iv30 normalised at the call site (compute.py) rather than inside compute_vrp — keeps the function contract pure and decimal-only"
  - "mock.patch.object(compute_mod, 'load_history') is the correct pattern when the name is imported into a module's namespace"
metrics:
  duration: "~8 min"
  completed: 2026-05-26
  tasks_completed: 3
  tests_before: 59
  tests_after: 60
---

# Phase 06 Plan 04: Gap Closure Summary

**One-liner:** Closed CR-01 BLOCKER (VRP percentage vs decimal unit mismatch producing economically meaningless values), WR-01 (ineffective mock targeting wrong namespace), WR-02 (stale GEX meridian methodology text), and IN-01 (dead variable) — 60 tests green.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | CR-01: Normalise iv30 to decimal before compute_vrp | cf5cfc5 | gex/compute.py, gex/vol_metrics.py, gex/tests/test_vol_metrics.py |
| 2 | WR-01: Fix ineffective mock namespace | 2a6b13c | gex/tests/test_compute_wiring.py |
| 3 | WR-02 + IN-01: Stale methodology text and dead variable | 0b41a85 | streamlit_app.py, gex/tests/test_vol_metrics.py |

## Changes Made

### Task 1 — VRP Unit Fix (BLOCKER CR-01)

`gex/compute.py` previously called `compute_vrp(snapshot.iv30, rv20)` where `snapshot.iv30` is a CBOE percentage (e.g., 18.0 for 18% vol) and `rv20` is already a decimal fraction (~0.158). The subtraction produced ~17.84 instead of ~0.022 — economically meaningless and silently corrupt in every parquet snapshot written since the feature was added.

Fix: added `iv30_decimal = (snapshot.iv30 / 100.0) if snapshot.iv30 is not None else None` before the `compute_vrp` call. The function body is unchanged — the decimal-fraction contract is now enforced at the call site.

`gex/vol_metrics.py` docstring updated to document the decimal-fraction convention explicitly. `test_vrp_sign` updated from `compute_vrp(25.0, 20.0)` to `compute_vrp(0.18, 0.158)` (decimal inputs, ~0.022 result). Added `test_vrp_realistic_range` asserting result is in [0.001, 0.10].

### Task 2 — Mock Namespace Fix (WARNING WR-01)

`mock.patch("gex.validation.load_history")` patches the name in the `gex.validation` module but `gex.compute` imports `load_history` via `from gex.validation import load_history` — the name is bound in `gex.compute`'s namespace. The old patch was never intercepting the call, so `test_cold_start_rv20_and_vrp_are_none` was passing by coincidence (network/file not available in test environment), not by design.

Fix: replaced with `mock.patch.object(compute_mod, "load_history", return_value=pd.DataFrame())` — matches the pattern already used for all other mocks in that fixture.

### Task 3 — Stale Text + Dead Variable (WR-02 + IN-01)

`streamlit_app.py` methodology expander described the vol surface as "Annotated with γ-flip, call wall, and put wall meridians" — these GEX overlays were removed in the v3.2 reframe. Replaced with accurate text noting removal and pointing to the Strikes tab.

`test_rv20_manual` had two dead assignments (`arr = np.array(prices)` and `log_returns = ...`) that were computed but never used. Removed.

## Deviations from Plan

None — plan executed exactly as written.

## Verification

Full suite: `python -m pytest gex/tests/ -q` → **60 passed, 0 failed**

Spot-checks all confirmed:
- `compute_vrp(0.18, 0.158)` → `VRP=0.0220` (in [0.001, 0.10])
- `gex.validation.load_history` absent from test_compute_wiring.py; `patch.object(compute_mod, ...)` present
- `"Annotated with"` absent from streamlit_app.py; `"removed per v3.2 reframe"` present
- `log_returns` and `arr = np.array(prices)` absent from test_vol_metrics.py

## Known Stubs

None.

## Threat Flags

None — all changes are pure numeric normalization and test/documentation updates; no new network endpoints, auth paths, or file access patterns introduced.

## Self-Check: PASSED

- gex/compute.py: contains `iv30_decimal` — confirmed
- gex/vol_metrics.py: contains "decimal fractions" in docstring — confirmed
- gex/tests/test_vol_metrics.py: contains `compute_vrp(0.18, 0.158)` — confirmed; `compute_vrp(25.0, 20.0)` absent — confirmed
- gex/tests/test_compute_wiring.py: `gex.validation.load_history` absent — confirmed
- streamlit_app.py: `Annotated with` absent — confirmed
- Commits cf5cfc5, 2a6b13c, 0b41a85 all present in git log

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/agent-afb7feb0f7904cd31/ROADMAP|ROADMAP]] · [[_planning/agent-afb7feb0f7904cd31/STATE|STATE]]
**Phase siblings:**
- [[_planning/agent-afb7feb0f7904cd31/phases/06-computation-engine/06-01-PLAN|06-01-PLAN]]
- [[_planning/agent-afb7feb0f7904cd31/phases/06-computation-engine/06-01-SUMMARY|06-01-SUMMARY]]
- [[_planning/agent-afb7feb0f7904cd31/phases/06-computation-engine/06-02-PLAN|06-02-PLAN]]
- [[_planning/agent-afb7feb0f7904cd31/phases/06-computation-engine/06-02-SUMMARY|06-02-SUMMARY]]
- [[_planning/agent-afb7feb0f7904cd31/phases/06-computation-engine/06-03-PLAN|06-03-PLAN]]
- [[_planning/agent-afb7feb0f7904cd31/phases/06-computation-engine/06-03-SUMMARY|06-03-SUMMARY]]
- [[_planning/agent-afb7feb0f7904cd31/phases/06-computation-engine/06-04-PLAN|06-04-PLAN]]

<!-- LINKS:END -->
