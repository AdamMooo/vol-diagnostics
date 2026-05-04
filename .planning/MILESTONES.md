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

## v2.0 — Sleeve Allocation Framework: Engine Build (local POC)

**Status:** CLOSED — local POC complete
**Started:** 2026-04-30
**Closed:** 2026-05-04

**Goal:** Build the math/data/dashboard engine locally so it can iterate without Cron2 access — six signals + sleeve backtest + decision dashboard, all on free-source data with statistical rigor (Holm correction, block bootstrap).

**Shipped:**
- Phase 1 — Extended Data Layer: CBOE+FRED panels, NYSE-aligned, schema parity with Cron2 contract
- Phase 2 — Signal Engineering: RV, VRP, term, skew, trend, drawdown, fragility composite — causal 5y rolling pct rank
- Phase 3 — Sleeve Backtest: BS pricer with skew-aware put leg, monthly-roll P&L for CC/CSP/Collar/Strangle, 195 rolls
- Phase 4 — Decision Dashboard (replaced original "Scorecard" framing): state + mechanics + conditional history + analog + subperiod
- Phase 5 — PM-Grade Output: folded into the dashboard
- Sections G + H — TC sensitivity grid, tail-risk metrics
- Statistical rigor: Holm-Bonferroni FWE correction, stationary block bootstrap CI
- 74 tests (math correctness + pipeline invariants + property-based)

**Not shipped, intentionally:**
- Phase 6 (original "Validation Gates") — re-scoped and lifted to v2.1 Phase 1
- Phase 7 (PDIV / fund specialization) — dropped 2026-05-04, market-general framework only
- Phase 8 (Markov-switching fragility flag) — optional, deferred indefinitely
- Cron2 production run — deferred until v2.1 Bloomberg calibration

**Why closed:**
- Engine functionally complete and validated locally
- Mode shift from "build" to "deliver/calibrate/learn" warrants a milestone boundary
- Phases 1-5 archived under `.planning/phases-archive/v2.0-engine/`

**Lessons captured:**
- Forecasting framing kept creeping in (original Phase 4 scorecard, walk-forward validate.py); user explicitly redirected twice
- Statistical rigor (Holm correction → 0/30 tests survive) is the credibility centerpiece, not the failure
- Calibration of synthetic 90mny IV (slope=0.2 vs initial 0.5) materially changed sleeve Sharpe rankings — Bloomberg-observed values needed before any external claim

---

## v2.1 — POC Delivery & Validation

**Status:** ACTIVE
**Started:** 2026-05-04

**Goal:** Deliver the v2.0 engine to the quant team for evaluation. Calibrate via Bloomberg, package as a Jupyter notebook with quality charts, write a walkthrough doc, and surface the question *"What would have to be true for this to inform a real decision?"*

**Audience:** Quant team first; weekly Monday review cadence; async-then-meeting handoff.

**Phase 1 — POC Delivery & Calibration:** Bloomberg swap + notebook artifact + walkthrough doc + cleanup (delete validate.py, reframe Section D). Locked decisions in `.planning/phases/01-poc-delivery/01-CONTEXT.md`.

**Future phases (open):** driven by quant-team feedback — extensions, scope changes, go/no-go criteria. Not pre-defined.

**Hard scope cap (locked):** No PDIV / fund specialization, no Markov-switching/HMM, no new signals.
