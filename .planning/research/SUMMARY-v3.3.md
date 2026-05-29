# Project Research Summary — v3.3 "Surface Evolution & Daily Intelligence"

**Project:** gamma-omm (institutional vol diagnostics, descriptive / non-predictive)
**Domain:** Change-over-time analytics layered on an existing RBF/TPS implied-vol surface, plus a richer daily email
**Researched:** 2026-05-29
**Confidence:** HIGH on stack/architecture/validation mechanics; MEDIUM on PCA and daily-report content conventions

## Executive Summary

v3.3 builds the "calculus of the surface" — ΔIV decomposition, surface velocity, multi-horizon comparison, and a richer daily email — on top of the existing TPS vol surface. The dominant fact across all four research streams is that **every one of those metrics reads off one object: an RBF thin-plate-spline surface that extrapolates unboundedly into regions with no quotes, masked only by a `np.clip(IV, 0, None)` that hides the symptom while keeping the disease.** A velocity number, a skew-change scalar, or a PCA factor computed on a fabricated corner is worse than useless — it manufactures signal where there is none, the same "hand-tuned non-stationary" trap the project already retired twice (the $200M GEX floor, the categorical regime label).

The recommended approach is **foundation-first, gated**. Phase 8 produces a *coverage mask* (cKDTree nearest-neighbour / convex-hull over real quote locations) plus a fit-honesty layer (residuals, leave-one-expiry-out CV, no-arb sanity flags, documented smoothing). That mask becomes the **single source of truth for "where the surface is real,"** and Phases 9/10/11 are forbidden from computing, displaying, or emailing any value in an uncovered cell. The same research converges hard on two CUT recommendations: **stay on TPS — verify, do not calibrate (no SVI/SABR)**, and **cut PCA** because its first three factors are level/slope/skew, which the tool already measures directly — building PCA is "build SVI when honest flags would do" creep.

Risk is concentrated in two places. (1) The stack greenlight is wrong: `kaleido==0.2.1` hangs indefinitely on Windows against the installed plotly 6.7.0 — the correct path is `kaleido>=1.0,<2.0` + a one-time `get_chrome` fetch, with an HTML-attachment fallback if that machine can't run the download. (2) Surface evolution invites two silent bugs — differencing two independently-extrapolated grids, and treating "5 days back" as calendar days rather than stored trading sessions. Both are mitigated by reusing the Phase 8 mask (intersected across both days) and resolving horizons against `list_available_dates` + `pandas_market_calendars`. Email charts must be **2D heatmaps, not 3D**, and the report should **lead with the 5d horizon** (1d ΔIV is mostly expiry-roll + quote noise — the same hazard that killed the v3.1 vs-yesterday badge).

## Key Findings

### Recommended Stack

Validation (feature 1) and evolution (feature 2) need **ZERO new dependencies** — LOO/leave-one-expiry-out CV, residuals, coverage masks, and the ΔIV decomposition are all hand-rollable on existing scipy (`RBFInterpolator`, `scipy.spatial`), numpy, pandas, pyarrow, and `pandas_market_calendars`. scikit-learn is explicitly rejected (RBFInterpolator isn't an sklearn estimator; the adapter would be more code than a ~15-line hand-rolled loop). The **only** new dependency is for PNG export — and the greenlit pin is wrong.

**Core technologies:**
- **kaleido `>=1.0,<2.0`** (NEW, only addition) — static PNG export. `kaleido==0.2.1` is built for plotly 5.x and **hangs indefinitely** on Windows with the installed plotly 6.7.0. Path A: install kaleido v1, run `kaleido.get_chrome_sync()` once per machine, call `fig.write_image(path)` (no `engine=` arg). Fallback (Path B / locked-down machine): attach the existing self-contained HTML artifact.
- **scipy (existing, 1.17.1)** — `RBFInterpolator` refits for CV; `scipy.spatial.cKDTree`/`Delaunay` for the coverage mask (already inside pinned scipy — no new install).
- **numpy / pandas / pyarrow (existing)** — ΔIV decomposition, residual tables, extended evolution parquet schema.
- **pandas_market_calendars (existing)** — resolve "1/5/20 trading days back" to real session dates.

### Expected Features

**Must have (Phase 8 table stakes — blocking):**
- **Coverage / extrapolation mask** — cKDTree/convex-hull over real quotes; NaN-hole the exterior. Highest value/cost ratio; the reason Phase 8 exists.
- **Fit residual diagnostic** — RMSE + max residual (pp) of RBF vs input quotes.
- **Smoothing sensitivity sweep** — replace unjustified `smoothing=1.5` magic number; move to `config.py`.
- **No-arb sanity checks** — calendar + butterfly; report PASS/FAIL + locations, **never repair**.

**Should have (Phase 9+ differentiators):**
- **3-scalar ΔIV decomposition (level / term / skew)** on the masked grid; needs no history, ships first.
- **Surface velocity** — Frobenius norm of masked ΔIV / horizon-days.
- **Multi-horizon (1d / 5d / 20d)** — **lead with 5d**; 1d is mostly expiry-roll + quote noise.
- **Cross-ticker surface-change comparison** — SPY/QQQ/IWM (IWM divergence = domestic-stress read).

**Defer / CUT:**
- **PCA — CUT (confirm not merely deferred).** First 3 factors = level/slope/skew, already measured; tiny non-stationary sample, sign-ambiguous.
- **SVI / SSVI / SABR — CUT.** Calibration engine, fragile on noisy CBOE quotes; verify with no-arb *checks*, don't calibrate. v4.x only.
- Intraday/real-time evolution, "fair value" forecasting, high-res grid — all rejected.

### Architecture Approach

Integration into a clean existing codebase. The leverage move is extracting **`analytics.rbf_grid`** (duplicated in `plot_vol_surface` and `plot_iv_change_surface`) to one module-level helper in Phase 8, so surface render, diagnostics RMS, and the evolution engine share one interpolation definition. Diagnostics are a pure `exposure_engine.surface_diagnostics()` called in `compute.py::compute_ticker` and persisted via the scalar store — computed headless.

**Major components:**
1. **`analytics.rbf_grid` (NEW, extracted, Phase 8)** — one definition, three consumers. Most leveraged refactor in v3.3.
2. **`exposure_engine.surface_diagnostics` (NEW, Phase 8)** — coverage %, fit RMS, per-expiry counts; persisted via `validation.save_snapshot` (additive columns).
3. **`surface_evolution.py` (NEW, Phase 9)** — reads *both* sides from `surface_history` (deterministic), reuses `rbf_grid`, writes idempotent `(date × ticker × horizon)` rows; non-blocking second pass in `run_daily.run`.
4. **`surface_history.nth_trading_day_back` (NEW, Phase 9)** — index descending `list_available_dates`, not calendar math.
5. **Streamlit 5→4 tabs (MODIFIED, Phase 10)** — `Surface | Skew & Term | Surface Evolution | Flow Context`; remove the carry/VRP block (no standalone Carry tab — `plot_carry_vrp` lives inside `tab_term`).
6. **`analytics.save_fig_png` + email attachments (NEW/MODIFIED, Phase 11)** — `emailer.send` already accepts `attachments=`; only risk is the kaleido spike.

### Critical Pitfalls

1. **TPS extrapolating into empty corners, masked by zero-clip** — build the coverage mask, NaN-hole unsupported cells, instrument clip touch-count. **Phase 8.**
2. **ΔIV differencing two independently-extrapolated grids** — intersect both days' masks, scale colourmap off masked cells only. **Phase 9.**
3. **"Nth day back" ≠ N trading sessions** — resolve against stored dates + `pandas_market_calendars`; label actual prior date. **Phase 9.**
4. **Kaleido hangs / 3D PNGs unreadable** — kaleido v1, warm-up + timeout, **2D heatmaps**, fail-soft. **Phase 11.**
5. **PCA over-interpretation on tiny non-stationary sample** — **cut it**; if ever built, ≥40 sessions, pinned signs, masked vectors. **Cut/defer.**
6. **Naive LOO-point CV flatters** — adjacent strikes correlated; use leave-one-*expiry*-out, report CV only with coverage %. **Phase 8.**

## Implications for Roadmap

Suggested **4 phases** (matches architecture build order). The foundation-first gate is the spine: nothing downstream computes a trustworthy delta until the interpolation is unified and the mask exists.

1. **Phase 8 — Surface Validation (the gate).** Extract `rbf_grid`; coverage mask; fit residuals; per-expiry strike gate; documented smoothing; no-arb flags; diagnostics persisted; Streamlit readout. **Gate output: the mask is the single source of truth Phases 9/10/11 import.**
2. **Phase 9 — Evolution Engine.** `surface_evolution.py` + `nth_trading_day_back`; 3-scalar decomposition on intersected mask; velocity; idempotent parquet; non-blocking trigger.
3. **Phase 10 — Dashboard Restructure.** 5→4 tabs; merge Skew+Term; remove carry/VRP block; stored-vs-stored compare; evolution time-series; backfill to avoid cold-start. 3D stays dashboard-only.
4. **Phase 11 — Richer Daily Report.** kaleido spike first; `save_fig_png`; 2D heatmaps; PNG/attachment wiring fail-soft; copy leads with 5d.

**Ordering rationale:** hard dependency chain (9 reuses 8's mask; 10 reads 9's store; 11 surfaces both). Backfill sub-task at start of Phase 9/10.

### Research Flags
- **Needs spike: Phase 11 (kaleido)** — confirm `kaleido>=1.0` + `get_chrome` + `write_image` works on the target Windows machine before committing to PNG embedding; else HTML-attachment fallback. Highest-risk integration point.
- **Standard patterns (skip research): Phases 8, 9, 10** — validation recipe, ΔIV convention, and Streamlit restructure are all fully specified line-by-line.

### Open Decisions for the User
1. **kaleido v1 + Chrome vs HTML-attachment fallback** — do NOT use `kaleido==0.2.1` (hangs) and do NOT downgrade plotly to 5.x (regresses signed-off 3D charts).
2. **Confirm "remove Carry" = delete the carry/VRP block inside the Term Structure tab** — no standalone Carry tab exists.
3. **Confirm PCA is CUT, not deferred.**

### Confidence
**Overall: HIGH.** Stack HIGH (verified against installed venv + issue tracker; greenlit pin provably wrong). Features HIGH on validation/PCA conventions, MEDIUM on daily-report content. Architecture HIGH (codebase read directly). Pitfalls HIGH on mechanics, MEDIUM on PCA small-sample stats.

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
