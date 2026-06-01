---
phase: 11-richer-daily-report
plan: "01"
subsystem: gex
tags: [kaleido, png-export, oi-walls, compute-pipeline, tdd]
dependency_graph:
  requires: []
  provides: [kaleido-installed, oi_call_wall, oi_put_wall]
  affects: [gex/compute.py, requirements.txt]
tech_stack:
  added: [kaleido>=1.0,<2.0, choreographer, logistro, orjson, simplejson]
  patterns: [tdd-red-green, None-safe-guard, mocked-pipeline-test]
key_files:
  created: []
  modified:
    - requirements.txt
    - gex/compute.py
    - gex/tests/test_compute_wiring.py
decisions:
  - kaleido 1.3.0 installed (1.x series), smoke test passed on Windows with plotly 6.x
  - OI walls use call_oi/put_oi columns from strike_oi merge (not type=='C'/'P' — strike_oi aggregates by side)
  - Guard uses fillna(0).gt(0).any() before idxmax — handles NaN and zero-OI cases
metrics:
  duration: ~15 min
  completed: "2026-06-01"
  tasks_completed: 2
  files_modified: 3
---

# Phase 11 Plan 01: Kaleido Gate + OI Walls Summary

kaleido 1.3.0 installed and smoke-tested on Windows; OI call/put wall keys added to compute_ticker() summary dict with None-safe guard.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Pin kaleido in requirements.txt + smoke test | 2282778 | requirements.txt |
| 2 RED | Failing tests for oi_call_wall / oi_put_wall | 0922cc8 | gex/tests/test_compute_wiring.py |
| 2 GREEN | Implement OI walls in compute_ticker() | 9141e8b | gex/compute.py |

## What Was Built

**Task 1 — kaleido gate:** Added `kaleido>=1.0,<2.0` to requirements.txt. Installed kaleido 1.3.0 (with choreographer, logistro, orjson, simplejson dependencies). Ran smoke-test spike: trivial Plotly scatter → `write_image()` → PNG. Passed without hanging. kaleido 1.x uses a headless Chrome subprocess managed by the choreographer library, not the subprocess-lock approach of 0.2.1 that deadlocks on Windows.

**Task 2 — OI walls:** Added 4 new tests (RED) covering key presence, None-safe behavior, and max-OI strike selection. Implemented OI wall logic in `compute.py` after the coherence_violations block. Logic uses `call_oi`/`put_oi` columns from the `strike_oi` merge (not a `type` column — `strike_oi` pivots by side already). Guard: `fillna(0).gt(0).any()` before `idxmax` — safe for empty DataFrame, all-NaN, or all-zero OI. All 16 tests pass.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Implementation Correction] Used call_oi/put_oi columns instead of type=='C'/'P'**
- **Found during:** Task 2 implementation
- **Issue:** PATTERNS.md showed `s_df['type'] == 'C'` but `strike_oi()` returns a pivoted DataFrame with `call_oi`/`put_oi` columns aggregated by strike — there is no `type` column in s_df after the merge
- **Fix:** Used `s_df['call_oi']` and `s_df['put_oi']` directly; updated test fixtures to mock `strike_oi` returning the correct column structure
- **Files modified:** gex/compute.py, gex/tests/test_compute_wiring.py
- **Commit:** 9141e8b

## Verification Results

- `pip show kaleido` → Version: 1.3.0 (1.x confirmed)
- `requirements.txt` contains `kaleido>=1.0,<2.0`
- `pytest gex/tests/test_compute_wiring.py -x -q` → 16 passed
- `gex/compute.py` contains `summary["oi_call_wall"]` and `summary["oi_put_wall"]`
- Smoke test: `fig.write_image('out/kaleido_smoke_test.png')` → "SMOKE TEST PASSED"

## Known Stubs

None — OI wall values are computed from live chain data in `compute_ticker()`.

## Threat Flags

None — no new network endpoints or auth paths introduced. pip install from PyPI (official Plotly project, legitimacy pre-verified in RESEARCH.md).

## Self-Check: PASSED

- requirements.txt: kaleido line present
- gex/compute.py: oi_call_wall and oi_put_wall assignments present
- gex/tests/test_compute_wiring.py: 4 new test methods present
- Commits 2282778, 0922cc8, 9141e8b all exist in git log

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/11-richer-daily-report/11-01-PLAN|11-01-PLAN]]
- [[_planning/gamma-omm/phases/11-richer-daily-report/11-02-PLAN|11-02-PLAN]]
- [[_planning/gamma-omm/phases/11-richer-daily-report/11-03-PLAN|11-03-PLAN]]
- [[_planning/gamma-omm/phases/11-richer-daily-report/11-04-PLAN|11-04-PLAN]]
- [[_planning/gamma-omm/phases/11-richer-daily-report/11-CONTEXT|11-CONTEXT]]
- [[_planning/gamma-omm/phases/11-richer-daily-report/11-DISCUSSION-LOG|11-DISCUSSION-LOG]]
- [[_planning/gamma-omm/phases/11-richer-daily-report/11-PATTERNS|11-PATTERNS]]
- [[_planning/gamma-omm/phases/11-richer-daily-report/11-RESEARCH|11-RESEARCH]]

<!-- LINKS:END -->
