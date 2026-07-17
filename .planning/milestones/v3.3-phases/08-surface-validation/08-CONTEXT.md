# Phase 8: Surface Validation (the gate) - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Prove the interpolated vol surface isn't overfit. Produce a **coverage mask + fit-honesty layer** that becomes the single source of truth for "where the surface is real" — imported by Phases 9/10/11. Where there's no quote support, the surface shows an honest NaN hole, not fabricated IV.

Delivers: shared `rbf_grid` helper (kills the duplicated interpolation), coverage mask (the exported gate artifact), per-ticker fit residuals persisted daily, `smoothing` moved to config with a documented sweep, surface-coherence sanity checks (report-only), and a Streamlit trustworthiness readout.

This phase clarifies HOW. New capabilities (evolution engine, dashboard restructure, richer email) are Phases 9–11.
</domain>

<decisions>
## Implementation Decisions

### Coverage mask (VALID-01)
- **D-01:** Mask method = **kNN over real quote locations** (`scipy.spatial.cKDTree`), not convex hull. A grid cell is NaN'd if its nearest real quote — in **normalized DTE/%OTM space** (reuse the existing per-axis std normalization from the RBF blocks) — exceeds radius `r`. Rationale: quotes cluster at discrete expiries, so a convex hull keeps fabricated IV in interior DTE gaps (missing expiries); kNN holes those gaps too.
- **D-02:** `r = COVERAGE_KNN_K × median(nearest-neighbor distance among real quotes)`. Data-adaptive — scales to today's chain density, so it is **not a fixed non-stationary cutoff** (avoids the trap that retired the $200M GEX floor and regime label).
- **D-03:** `COVERAGE_KNN_K = 2.0` default, lives in `config.py`, justified by the sensitivity sweep (D-12). `k=2.0` keeps cells within ~2× the typical quote gap while holing true missing-expiry gaps.
- **D-04:** The mask is exported as **the single artifact downstream phases consume**. Phase 9 will intersect two days' masks; build the mask so it is reusable, not buried inside the plot function. (Exact persisted form — boolean grid vs recompute-from-stored-quotes — left to planning; see Deferred.)

### rbf_grid extraction (VALID-05)
- **D-05:** Extract the duplicated RBF logic (`analytics.py:217` in `plot_vol_surface`, `analytics.py:350` in `plot_iv_change_surface`'s local `_rbf_grid`) into **one shared module-level helper** in `analytics` — three consumers: surface render, diagnostics RMS, and (Phase 9) the evolution engine.
- **D-06:** Surface must render **identically** to before (regression-checked — method left to planning; see Deferred). The clip `np.clip(IV, 0, None)` behavior moves into the helper; instrument/keep it but the mask is what hides unsupported cells now, not the clip.

### Fit diagnostics (VALID-02)
- **D-07:** Compute **RMSE + max residual (pp)** of the RBF fit against input quotes, plus **leave-one-EXPIRY-out CV** (not leave-one-point-out — adjacent strikes are correlated and flatter the error). Hand-rolled refit loop on existing scipy; **scikit-learn rejected** (RBFInterpolator isn't an sklearn estimator).
- **D-08:** Diagnostics computed **headless in `compute_ticker`** (via a pure `surface_diagnostics()` function) and **persisted daily** to the scalar snapshot store (`validation.save_snapshot` — additive columns; old snapshots must still load).

### Trust readout (VALID-06)
- **D-09:** Show **raw numbers only** — `Coverage 87% · Fit RMS 0.9pp · Max resid 2.1pp`. **No thresholds, no green/amber/red badge, no "trustworthy/stressed" label.** The NaN holes already show coverage visually; the PM reads the number and judges. Consistent with the project's twice-applied rejection of hand-tuned non-stationary cutoffs.
- **D-10:** Placement = a **compact metric row pinned directly above the 3D surface** on the Surface tab, always visible (no expander, no click). Satisfies "at a glance."

### Surface coherence checks — was "no-arbitrage" (VALID-04)
- **D-11:** **Reframe VALID-04 from "no-arbitrage checks" to "surface-coherence checks."** Rationale (user): we are not a stats-arb desk; on free *delayed* CBOE quotes a genuine arb is gone in milliseconds and untradable — so these checks have **zero value as a trading signal**. Their only legitimate role here is **fit-quality QA**: calendar total-variance monotonicity (variance must rise with maturity) and butterfly convexity (no negative implied density) confirm the *fitted surface is internally consistent* — a broken-fit flag in the same family as a coverage hole.
  - Compute **headless in `compute_ticker`**; persist PASS/FAIL + violation count to the snapshot; log PASS/FAIL + violation locations to stdout.
  - **No dashboard UI in Phase 8** (rich display, if ever, is Phase 10 territory).
  - **Never auto-repairs** the surface (unchanged from original VALID-04).
  - **Watch condition:** if it perpetually FAILs on delayed/crossed/wide quotes, the persisted history will show that and we **cut it** — it's noise, not a flag.
  - **Action for executor:** update the *wording* of VALID-04 in `REQUIREMENTS.md` and Phase 8 SC#5 in `ROADMAP.md` from "no-arbitrage" → "surface coherence," and drop the dashboard-surfacing implication.

### Sensitivity sweep (VALID-03)
- **D-12:** `smoothing=1.5` moves to `config.py` (`SURFACE_SMOOTHING`). Documented by a **re-runnable standalone script** `gex/surface_sweep.py` that sweeps **both** `smoothing` and `COVERAGE_KNN_K`:
  - `smoothing` scored on **RMSE / max-residual** (fit accuracy vs over-flattening the skew).
  - `k` scored on **coverage % / hole-count**.
  - Chosen values + a one-line rationale live in the `config.py` docstring, citing `surface_sweep.py`. Re-runnable so the justification stays live, not frozen.
  - Keep `1.5` and `k=2.0` unless the sweep clearly argues otherwise — then lock whatever the sweep shows.

### Claude's Discretion
- Exact persisted form of the coverage mask (boolean grid array vs recompute-from-stored-quotes) — decide in planning with Phase 9's intersection need in mind (D-04).
- Regression-check mechanism for the rbf_grid refactor (golden-array assert vs numerical equality test vs visual) — planning's call, but it must be objective, not eyeball-only (D-06).
- Module home for `surface_diagnostics()` — research summary suggests `exposure_engine`; planner confirms against current import graph.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & requirements
- `.planning/ROADMAP.md` §"Phase 8: Surface Validation (the gate)" — goal + 6 success criteria. **Note:** SC#5 wording changes per D-11 (no-arb → surface coherence).
- `.planning/REQUIREMENTS.md` §"Surface Validation (Phase 8 — the gate)" — VALID-01..06. **Note:** VALID-04 wording changes per D-11.
- `.planning/research/SUMMARY-v3.3.md` — full v3.3 research; §"Architecture Approach", §"Critical Pitfalls" (items 1, 6), §"Recommended Stack" (zero new deps for Phase 8) are directly load-bearing here.

### Code to modify / reuse
- `gex/analytics.py:159` `plot_vol_surface` — duplicated RBF block at :217 (`smoothing=1.5`, `np.clip(IV,0,None)`); source of the extraction.
- `gex/analytics.py:303` `plot_iv_change_surface` — local `_rbf_grid` at :338–354, the second duplicate; collapse into the shared helper.
- `gex/exposure_engine.py:48` `vol_surface_data` — produces the OTM IV scatter the surface/diagnostics consume; likely home for `surface_diagnostics()`.
- `gex/validation.py:38` `save_snapshot` — scalar parquet store; extend with additive diagnostic columns (RMSE, max_resid, coverage_pct, coherence flags). `load_history` at :83.
- `gex/config.py:56–99` — existing `SURFACE_*` constants; add `SURFACE_SMOOTHING`, `COVERAGE_KNN_K` here.
- `gex/compute.py` `compute_ticker` — headless call site for diagnostics + coherence checks.

### Codebase conventions
- `.planning/codebase/CONVENTIONS.md`, `.planning/codebase/ARCHITECTURE.md` — established patterns (pure functions, scalar store, Windows pathlib).
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **RBF interpolation** already written twice (`analytics.py:217`, `:350`) with identical params (`kernel="thin_plate_spline"`, `smoothing=1.5`, per-axis std normalization, `np.clip(IV,0,None)`) — extraction is mechanical, low-risk.
- **Per-axis normalization** (`pts_std`, with `<1e-6 → 1.0` guard) is the right space for the kNN distance metric — reuse it for the mask.
- **Scalar snapshot store** (`validation.py`) already idempotent on (date, ticker) and already does additive-column loading (`_FLOAT_COLS` astype) — diagnostics columns slot in cleanly.
- **Config surface block** (`config.py:56–99`) already centralizes grid/clip/DTE constants — smoothing + k belong beside them.

### Established Patterns
- Pure compute functions feed `compute_ticker`, which both the daily email and Streamlit consume (single source of truth) — diagnostics + coherence follow this (headless, no UI coupling).
- Project rejects hand-tuned non-stationary thresholds (twice). Drives D-02 (data-adaptive radius) and D-09 (no trust badge).
- Surface DTE floor = 5, OTM clip from `SURFACE_PLOT_OTM_CLIP` (±15%) — the mask operates on the same clipped/floored point set the RBF sees.

### Integration Points
- Mask is the **exported gate artifact** Phase 9 intersects across days — design for reuse outside the plot function.
- Diagnostics persist via `save_snapshot` so Phase 9/10 read fit history with no new store.
</code_context>

<specifics>
## Specific Ideas

- Trust readout literal: `Coverage 87%   Fit RMS 0.9pp   Max 2.1pp` as a metric row above the surface.
- Coherence checks framed as **fit QA, not arbitrage** — the user explicitly rejected the arb framing ("we are not a hedge fund optimizing on stats arb... it'll be gone in milliseconds"). Keep all PASS/FAIL language about *surface consistency*, never about tradable opportunity.
- Sweep table is the proof artifact for two magic numbers at once (`smoothing`, `k`) — one script, `python -m gex.surface_sweep`.
</specifics>

<deferred>
## Deferred Ideas

- **Mask persisted form** (boolean grid vs recompute-from-quotes) — resolve in planning, not a user-vision decision.
- **Regression-check mechanism** for the refactor — planning's call (must be objective).
- **Rich no-arb / coherence dashboard surfacing** — explicitly NOT in Phase 8; revisit in Phase 10 only if the checks prove informative (not perpetually FAIL).
- **Cutting coherence checks entirely** — live option if the persisted history shows constant FAIL on delayed quotes; revisit post-Phase-8.

None of these are scope creep — they're sub-decisions inside Phase 8's boundary or explicit later-phase punts.
</deferred>

---

*Phase: 08-surface-validation*
*Context gathered: 2026-05-29*

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
