---
phase: 25-existing-computation-rigor-hardening
verified: 2026-07-26T00:00:00Z
status: passed
score: 4/4 success criteria verified
re_verification:
  previous_status: none
  note: initial verification
requirements_verified: [RIGOR-01, RIGOR-02]
---

# Phase 25: Existing Computation Rigor Hardening — Verification Report

**Phase Goal:** The existing VRP, RV20, vol-surface-fit, and skew/term-structure computations are verified correct against documented methodology and behave predictably (never silently-wrong) on edge-case inputs. Hardening of existing descriptive computations only — NO new predictive/prescriptive model logic.
**Verified:** 2026-07-26
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Success Criteria (Roadmap Contract)

| # | Criterion | Status | Evidence |
| --- | --- | --- | --- |
| 1 | All four computations checked vs documented methodology; discrepancies fixed or logged as intentional deviation | ✓ VERIFIED | `25-METHODOLOGY-AUDIT.md` exists with a per-computation table and a verdict each: RV20 / skew(25Δ) / term = VERIFIED CORRECT (no math change); VRP = INTENTIONAL DEVIATION (documented); surface fit = MATCHES DOCUMENTED INTENT. |
| 2 | Edge cases exercised by NEW tests, each producing a DEFINED result (graceful NaN/skip or loud raise), never silently-wrong | ✓ VERIFIED | 15 new edge tests across 4 files assert defined outcomes: singular RBF fit → None; spot≤0 → defined no-raise; missing structural column → loud KeyError; NaN vol-index close → None; <2 term points → `insufficient_data` sentinel; RV20 NaN/nonpositive→None, identical→0.0; VVIX NaN close→None; VRP NaN-mid-series dropped (n=39, no NaN); VRP single aligned point → defined dict (n=1, pct=100). |
| 3 | New edge tests added; `pytest engine/tests` count > 449 baseline, 100% pass | ✓ VERIFIED | Independently re-ran: **465 passed, 0 failed** in 26.72s. 465 > 449 baseline. |
| 4 | No new predictive/prescriptive logic; no formula changes to RV20/skew/term; VRP computation + "VRP" label UNCHANGED (doc-only) | ✓ VERIFIED | `git diff 8d04807~1 HEAD -- engine/vol/vrp_history.py` shows ONLY a 7-line docstring addition; computation line 88 (`vrp_hist = aligned["vi"] - aligned["rv"] * 100`) untouched. "VRP" label retained in card_model.py, app.py, report.py. RV20/skew/term diffs add only guard clauses (pd.isna, sentinel), no formula edits. |

**Score:** 4/4 success criteria verified

### CRITICAL: VRP Locked-Decision Check

| Check | Status | Evidence |
| --- | --- | --- |
| vrp_history.py docstring contains honest text | ✓ VERIFIED | Lines 3-9: "a practitioner vol-risk-premium proxy, NOT the Carr & Wu (2009) variance-swap VRP (`IV² − RV²`, variance units)". |
| report.py glossary/footnote contains honest text | ✓ VERIFIED | Lines 516-517: "a practitioner implied-minus-realized vol-point proxy, not the Carr-Wu variance-swap VRP (IV²−RV², variance units)". |
| Computation NOT changed to variance units | ✓ VERIFIED | Line 88 still `vi - rv*100` (vol points). Diff confirms no code-line change. |
| "VRP" identifier NOT renamed | ✓ VERIFIED | `git grep VRP` shows label intact across card_model.py, app.py, report.py, config keys. |

The locked decision ("document as intentional deviation, keep computation + label") was honored exactly. No FAIL condition triggered.

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `.planning/.../25-METHODOLOGY-AUDIT.md` | Per-computation audit with verdicts | ✓ VERIFIED | All four covered; verdict summary + traceability + accepted limitations. |
| `engine/vol/vrp_history.py` | Honest docstring, computation unchanged | ✓ VERIFIED | Docstring added; line 88 intact. |
| `engine/report/report.py` | Glossary footnote with honest text | ✓ VERIFIED | Lines 513-517. |
| `engine/vol/vol_metrics.py` | insufficient_data sentinel + pd.isna guards + compute_vrp removed | ✓ VERIFIED | Sentinel (L243), guards (L378/L437), `compute_vrp` gone (git grep: NONE). |
| `engine/surface/surface_interactive.py` | Symmetric try/except around _fit_rbf in all 3 builders | ✓ VERIFIED | surface (L88), diff (L263), movie (L416) all `except Exception: return None`. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| RIGOR-01 | 25-01/02/03 | Computations reviewed vs documented methodology, edge cases checked | ✓ SATISFIED | Methodology audit + all four verdicts; edge tests. Marked `[x]` in REQUIREMENTS.md. |
| RIGOR-02 | 25-01/02/03 | Test coverage expanded for edge cases, not just happy path | ✓ SATISFIED | 15 new edge tests; suite 465 (was 449). Marked `[x]`. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Full suite passes above baseline | `pytest engine/tests -q` | 465 passed, 0 failed | ✓ PASS |
| compute_vrp fully removed | `git grep "def compute_vrp"` | no matches | ✓ PASS |
| VRP module docstring honest text loads | present in file lines 3-9 | Carr/variance-swap distinction present | ✓ PASS |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| — | — | No TODO/FIXME/XXX/TBD/HACK in phase code additions | — | None found |

### Gaps Summary

None. All four roadmap success criteria are verified in the codebase, not just claimed in SUMMARY.md. The methodology-audit record exists and covers all four computations with a verdict each. Edge-case tests exist and assert defined behavior (None/sentinel/loud KeyError), and the full suite independently re-runs at 465 passed (>449 baseline, 100% green). The critical VRP locked-decision check passed on all four sub-checks: the computation stayed as a vol-point spread, the "VRP" label was not renamed, and both the module docstring and the email glossary carry the honest "practitioner proxy, not Carr-Wu variance-swap VRP" definition. RIGOR-01/02 are genuinely satisfied and correctly marked complete.

---

_Verified: 2026-07-26_
_Verifier: Claude (gsd-verifier)_

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
- [[_planning/vol-diagnostics/phases/25-existing-computation-rigor-hardening/25-03-SUMMARY|25-03-SUMMARY]]
- [[_planning/vol-diagnostics/phases/25-existing-computation-rigor-hardening/25-CONTEXT|25-CONTEXT]]
- [[_planning/vol-diagnostics/phases/25-existing-computation-rigor-hardening/25-METHODOLOGY-AUDIT|25-METHODOLOGY-AUDIT]]
- [[_planning/vol-diagnostics/phases/25-existing-computation-rigor-hardening/25-RESEARCH|25-RESEARCH]]

<!-- LINKS:END -->
