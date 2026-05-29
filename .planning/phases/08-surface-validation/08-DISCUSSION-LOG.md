# Phase 8: Surface Validation (the gate) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-29
**Phase:** 08-surface-validation
**Areas discussed:** Mask strictness, Trust readout UI, No-arb / surface-coherence surfacing, Smoothing sweep form

---

## Mask method

| Option | Description | Selected |
|--------|-------------|----------|
| kNN, data-adaptive radius | cKDTree; NaN cell if nearest quote > k×median-NN distance (normalized space) | ✓ |
| Convex hull only | Delaunay hull, keep interior — parameter-free but under-masks expiry gaps | |
| Hybrid: hull + kNN cap | Inside hull AND within kNN cap — strictest, two mechanisms | |

**User's choice:** kNN, data-adaptive radius.
**Notes:** Quotes cluster at discrete expiries, so convex hull keeps fabricated IV in interior DTE gaps. Data-adaptive radius avoids a fixed non-stationary cutoff.

## kNN radius (k)

| Option | Description | Selected |
|--------|-------------|----------|
| k=2.0, config.py + sweep | Within 2× typical quote gap; holes true expiry gaps | ✓ |
| k=1.5, stricter | More aggressive holing | |
| You decide via the sweep | Let the sweep pick k | |

**User's choice:** k=2.0, in config.py, sweep-justified.

## Trust readout — classification

| Option | Description | Selected |
|--------|-------------|----------|
| Raw numbers, no thresholds | Coverage % · Fit RMS · Max resid as plain values | ✓ |
| Raw + one data-relative cue | RMS vs its own trailing percentile | |
| Traffic-light badge | Green/amber/red on fixed thresholds | |

**User's choice:** Raw numbers, no thresholds.
**Notes:** Consistent with twice-applied rejection of hand-tuned cutoffs; NaN holes already show coverage visually.

## Trust readout — placement

| Option | Description | Selected |
|--------|-------------|----------|
| Metric row above surface | Compact st.metric/caption row pinned above 3D surface, always visible | ✓ |
| Caption under title | One small line under the surface title | |
| Diagnostics expander | Collapsed expander below the surface | |

**User's choice:** Metric row above surface.

## No-arb / surface-coherence checks (VALID-04)

| Option | Description | Selected |
|--------|-------------|----------|
| Chip in row + expander | PASS/FAIL chip in metric row + violation expander | |
| Headless + persist only | Compute/persist/log, no UI | (superseded) |
| Full panel now | Dedicated violation panel on Surface tab | |
| **Keep, reframed as quiet fit-QA** | Rename no-arb → surface coherence; headless compute + persist + log, no Phase 8 UI; cut later if perpetual FAIL | ✓ |
| Cut VALID-04 entirely | Drop the checks; mask + RMS are the honesty layer | |

**User's choice:** Keep, reframed as quiet fit-QA.
**Notes:** User rejected the arbitrage framing outright — "we are not a hedge fund optimizing on stats arb... it'll be gone in milliseconds." Original 3-option question (chip / headless / full panel) was interrupted and reformulated into the cut-vs-keep-reframed decision. Result: checks survive purely as surface-consistency QA, computed headless, persisted, no dashboard UI in Phase 8; VALID-04 wording to be updated in REQUIREMENTS.md + ROADMAP SC#5.

## Smoothing sweep form (VALID-03)

| Option | Description | Selected |
|--------|-------------|----------|
| Re-runnable script + config docstring | gex/surface_sweep.py sweeps smoothing + k; values + rationale in config docstring | ✓ |
| One-time markdown table | Run once, commit table; docstring cites it | |
| Inline in config docstring only | Sweep results pasted as a comment table | |

**User's choice:** Re-runnable script + config docstring.
**Notes:** One script justifies two magic numbers (smoothing on RMSE/max-resid, k on coverage%/hole-count). Keep 1.5 / k=2.0 unless the sweep argues otherwise.

## Claude's Discretion

- Mask persisted form (boolean grid vs recompute-from-quotes).
- Regression-check mechanism for the rbf_grid refactor (must be objective).
- Module home for `surface_diagnostics()`.

## Deferred Ideas

- Rich coherence-check dashboard surfacing → Phase 10 only if checks prove informative.
- Cutting coherence checks entirely → live option if persisted history shows constant FAIL.

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/08-surface-validation/08-CONTEXT|08-CONTEXT]]

<!-- LINKS:END -->
