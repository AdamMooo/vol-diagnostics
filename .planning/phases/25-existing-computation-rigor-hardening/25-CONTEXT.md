# Phase 25: Existing Computation Rigor Hardening - Context

**Gathered:** 2026-07-26
**Status:** Ready for planning
**Source:** Research (25-RESEARCH.md) + Adam decision on the VRP methodology question

<domain>
## Phase Boundary

Audit the four EXISTING descriptive computations (VRP, RV20, vol-surface-fit, skew/term-structure) against documented methodology, and harden their edge-case behavior so they never return a silently-wrong number. Hardening + tests + honest documentation only — NO new predictive/prescriptive model logic (MODEL-01/02 stay deferred). Test baseline is 449 (not the stale 364 in ROADMAP).
</domain>

<decisions>
## Implementation Decisions (LOCKED)

### VRP methodology/naming — DOCUMENT AS INTENTIONAL DEVIATION (Adam, 2026-07-26)
The code's "VRP" is `vol_index − RV20×100` — an implied-minus-realized **vol-point spread**, NOT the Carr & Wu (2009) variance-swap VRP (`IV²−RV²`, variance units). Decision:
- **Keep the computation unchanged** — the vol-point spread is the theoretically-aligned richness signal for vanilla covered-call/CSP writing (vanilla premium ≈ linear in IV via vega), and it's the more interpretable read for the income-sleeve PM. Do NOT switch to variance units (that would be new model logic + less interpretable).
- **Keep the `VRP` identifier/label** — practitioners colloquially call IV−RV "the vol risk premium," so a full rename is unnecessary churn.
- **Add an honest one-line definition at first-use**: a docstring in `engine/vol/vrp_history.py` AND a glossary/email footnote stating it is "implied minus realized vol, in points — a practitioner vol-risk-premium proxy, not the Carr-Wu variance-swap VRP." This is the "intentional deviation" log that success criterion 1 requires.

### RV20 / skew(25Δ) / term-structure — VERIFIED CORRECT (no math change)
Research cross-checked these against standard methodology (close-to-close realized vol annualized √252 mean-centered; Xing/Zhang/Zhao 2010 25Δ convention; SPY-only term ratio via VIX9D/VIX3M). No formula changes — the phase's job for these is edge-case hardening + tests, not correction.

### Edge-case hardening targets (from research)
- **Exception-handling asymmetry:** `build_movie_payload` wraps its RBF surface fit in try/except but `build_surface_payload`/`build_diff_payload` do not — same near-singular-fit failure mode, inconsistent. Harden consistently.
- **NaN-vs-None contract break:** `compute_term_ratios._latest_close` returns a truthy NaN float instead of `None` when the vol-index store's last row has a NaN close — violates the `is not None` contract downstream consumers rely on. Fix + test.
- **`_classify_term_structure` returns "normal"** (a substantive claim) for <2 points instead of an "insufficient data" sentinel. Return a distinct sentinel + test.
- **`compute_vrp()` in `vol_metrics.py`** — research flags it as dead (superseded by `vrp_history.vrp_percentile()`). Planner: verify zero non-test callers; remove if safe, else keep with a one-line deprecation note. (Small item — do NOT let it expand scope.)

### Claude's Discretion
Exact test fixtures/synthetic-chain construction (match existing engine/tests style), precise sentinel values, docstring wording.
</decisions>

<canonical_refs>
## Canonical References
- `.planning/phases/25-existing-computation-rigor-hardening/25-RESEARCH.md` — methodology yardsticks, edge-case catalog, current-gap findings, test-pattern notes
- `engine/vol/vol_metrics.py`, `engine/vol/vrp_history.py` — RV20/VRP/skew/term computations
- `engine/surface/surface_interactive.py`, `engine/surface/surface_evolution.py` — surface fit + ΔIV scalars
- `C:\dev\vol-diagnostics\CLAUDE.md` — "Removed for rigor" list (do not reintroduce); conventions
</canonical_refs>

<deferred>
## Deferred Ideas
- Any variance-units VRP / variance-swap replication — out of scope (new model logic).
- New signals of any kind — locked out.
</deferred>

---

*Phase: 25-existing-computation-rigor-hardening*
*Context gathered: 2026-07-26 via research + Adam VRP decision*

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
**Phase siblings:**
- [[_planning/vol-diagnostics/phases/25-existing-computation-rigor-hardening/25-RESEARCH|25-RESEARCH]]

<!-- LINKS:END -->
