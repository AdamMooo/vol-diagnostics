# Milestones

## v1.0 — Regime-Aware Fund Intelligence Notebook (HMM)

**Status:** PIVOTED — superseded by v2.0 before ship

**Started:** 2026-04-22
**Pivoted:** 2026-04-30

**Goal:** Fit a Hidden Markov Model on benchmark returns to identify latent market regimes, then characterize how a fund (RTA) behaves across those regimes.

**Shipped (Phases 1-2 + Phase 3 cells):**
- Phase 1 — Data Layer: fund NAV (Django ORM) + benchmark (Bloomberg) load, log returns, alignment, EDA — complete
- Phase 2 — Regime Model: 3-state Gaussian Mixture (mislabeled HMM) on SPX, Sharpe-rank labeling, posterior plot, seed stability — complete
- Phase 3 — Fund Analysis: regime-conditional stats, OLS alpha/beta, summary table — cells written, not yet server-run

**Not shipped:** Phases 3 server run, 4 (transitions), 5 (visualization polish), 6 (summary/caveats)

**Why pivoted:**
- Code uses `sklearn.mixture.GaussianMixture`, not an actual HMM — naming dishonesty
- Stated goal (options sleeve allocation framework) requires options-pricing data the v1.0 model never touched
- Single-fund × single-benchmark scope is too narrow for the audience (Purpose PM/IC, product team)
- HMM is a "cool plus" not a load-bearing decision tool for asset management

**Preserved:** `hmm.ipynb` left intact as legacy single-fund diagnostic. Phase planning artifacts in `.planning/phases/01-*`, `02-*`, `03-*` left untouched.

**Lessons captured:** `NOTES-from-regime-detection.md` (HMM stickiness, hysteresis, OOS validation) — applicable to the optional fragility flag in v2.0.

---

## v2.0 — Sleeve Allocation Framework

**Status:** ACTIVE
**Started:** 2026-04-30

See `.planning/PROJECT.md` Current Milestone section.
