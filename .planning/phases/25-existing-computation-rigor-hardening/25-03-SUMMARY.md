---
phase: 25-existing-computation-rigor-hardening
plan: 03
subsystem: vol-metrics-documentation
tags: [vrp, methodology-audit, documentation, edge-tests, rigor]
requires:
  - "engine/vol/vrp_history.py vrp_history_series / vrp_percentile (existing, unchanged math)"
  - "engine/report/report.py methodology_footer glossary"
provides:
  - "Honest first-use VRP definition (docstring + email glossary): practitioner IV-RV proxy, not Carr-Wu variance VRP"
  - "VRP NaN-mid-series (E7) + single-aligned-point (E8) edge tests"
  - "25-METHODOLOGY-AUDIT.md — per-computation audit record certifying all four computations"
affects:
  - "engine/vol/vrp_history.py (docstring only)"
  - "engine/report/report.py (glossary footnote only)"
  - "engine/tests/test_vrp_history.py (+2 tests)"
tech-stack:
  added: []
  patterns:
    - "Intentional-deviation logged at first use rather than renamed (small-diff, keep colloquial label)"
    - "Edge tests assert exact defined dicts (no NaN, no crash) via monkeypatched I/O"
key-files:
  created:
    - ".planning/phases/25-existing-computation-rigor-hardening/25-METHODOLOGY-AUDIT.md"
  modified:
    - "engine/vol/vrp_history.py"
    - "engine/report/report.py"
    - "engine/tests/test_vrp_history.py"
decisions:
  - "Kept VRP computation (vol_index - RV20x100) and the 'VRP' label unchanged — documented as intentional deviation per locked 25-CONTEXT, not renamed"
  - "n=1 percentileofscore behavior (returns 100 for the sole point) documented via exact assertion, not treated as a bug"
metrics:
  duration_min: 6
  completed: 2026-07-26
  tasks: 3
  files: 4
  tests_added: 2
  test_total: 465
---

# Phase 25 Plan 03: VRP Honest-Deviation Documentation + Methodology Audit Summary

Logged the codebase's "VRP" as an intentional methodology deviation — an implied-minus-realized vol-point spread (a practitioner vol-risk-premium proxy), NOT the Carr & Wu (2009) variance-swap VRP — in the first-use docstring and the user-facing email glossary, keeping the computation and label unchanged per the locked CONTEXT decision. Added the two untested VRP edge cases (NaN mid-series, n=1) and wrote the phase's methodology-audit record certifying all four computations.

## What Was Built

**Task 1 — Honest VRP definition (doc-only).** Extended the `vrp_history.py` module docstring with a first-use "What VRP means here" paragraph stating it is `vol_index_close − RV20×100` (vol points), a practitioner proxy, explicitly not the Carr-Wu variance-swap VRP (`IV²−RV²`). Extended the `report.py` `methodology_footer` VRP glossary line with the same distinction. The computation (`vrp_hist = aligned["vi"] - aligned["rv"] * 100`, line 80) and the "VRP" identifier/label are untouched — verified via `git diff` showing no change to any computing line, and the automated check confirming "Carr" is present in the module doc.

**Task 2 — VRP edge tests.** Added `TestEdgeCases` to `test_vrp_history.py`:
- **E7 (NaN mid-series):** a NaN vol-index close on a non-last date inside the aligned band → `aligned.dropna()` removes exactly one row (40→39 aligned points); asserts the output dict carries no NaN (`vrp` real, `pct` int in [0,100], `n==39`).
- **E8 (n=1):** 21 closes yield exactly one RV20 point → one aligned VRP point; asserts `percentileofscore` on a 1-element window returns a defined int (100), never a crash, with `n==1`.
Both monkeypatch `load_vol_index` and `_fetch_closes_yf` (no real I/O), asserting existing behavior — no computation change.

**Task 3 — Methodology-audit record.** Wrote `25-METHODOLOGY-AUDIT.md` covering all four computations with reference formula/citation, code location, and verdict: RV20 / skew(25Δ) / term-structure = VERIFIED CORRECT (no math change); VRP = INTENTIONAL DEVIATION (documented); surface fit = matches its documented descriptive-not-arbitrage-free intent. Includes gap-to-plan traceability (25-01/25-02/25-03), accepted limitations (close-to-close efficiency, no-arbitrage constraints), and the dead `compute_vrp` retirement note.

## Deviations from Plan

None — plan executed exactly as written. VRP computation and label unchanged per constraint; no architectural changes; no auth gates.

## Task Commits

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | VRP intentional-deviation docstring + glossary footnote | 6f734a2 (docs) | vrp_history.py, report.py |
| 2 | VRP NaN-mid-series + n=1 edge tests | 83b4a85 (test) | test_vrp_history.py |
| 3 | Methodology-audit record (4 computations) | 6161569 (docs) | 25-METHODOLOGY-AUDIT.md |

## Verification

- `pytest engine/tests/test_vrp_history.py` — 11 passed (was 9, +2 edge tests)
- Full suite `pytest engine/tests` — **465 passed** (463 baseline + 2 new), 100% green, net-increase confirmed (> 463)
- `import engine.vol.vrp_history` "Carr" assertion — ok
- `git diff engine/vol/vrp_history.py` — no change to line 80 computation; "VRP" label in card_model.py/app.py untouched
- Audit doc contains `compute_rv20` and `Carr` — ok

## Self-Check: PASSED

- `.planning/phases/25-existing-computation-rigor-hardening/25-METHODOLOGY-AUDIT.md` — FOUND
- `engine/vol/vrp_history.py` docstring "Carr" — FOUND
- `engine/report/report.py` glossary "Carr" — FOUND
- Commits 6f734a2, 83b4a85, 6161569 — all FOUND in git log

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
**Phase siblings:**
- [[_planning/vol-diagnostics/phases/25-existing-computation-rigor-hardening/25-01-PLAN|25-01-PLAN]]
- [[_planning/vol-diagnostics/phases/25-existing-computation-rigor-hardening/25-01-SUMMARY|25-01-SUMMARY]]
- [[_planning/vol-diagnostics/phases/25-existing-computation-rigor-hardening/25-02-PLAN|25-02-PLAN]]
- [[_planning/vol-diagnostics/phases/25-existing-computation-rigor-hardening/25-02-SUMMARY|25-02-SUMMARY]]
- [[_planning/vol-diagnostics/phases/25-existing-computation-rigor-hardening/25-03-PLAN|25-03-PLAN]]
- [[_planning/vol-diagnostics/phases/25-existing-computation-rigor-hardening/25-CONTEXT|25-CONTEXT]]
- [[_planning/vol-diagnostics/phases/25-existing-computation-rigor-hardening/25-METHODOLOGY-AUDIT|25-METHODOLOGY-AUDIT]]
- [[_planning/vol-diagnostics/phases/25-existing-computation-rigor-hardening/25-RESEARCH|25-RESEARCH]]

<!-- LINKS:END -->
