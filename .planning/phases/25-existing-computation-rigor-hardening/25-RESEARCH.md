# Phase 25: Existing Computation Rigor Hardening - Research

**Researched:** 2026-07-26
**Domain:** Quantitative-finance methodology audit (realized vol, implied-vol risk premium, vol-surface interpolation, skew/term structure) + defensive edge-case hardening of existing Python code
**Confidence:** MEDIUM-HIGH — the four computations are simple/well-documented in code already; the main open item is a naming/methodology classification decision (VRP), not a math error

## Summary

This phase audits four already-shipped, already-tested computations (`compute_rv20`, the VRP-percentile engine, the RBF vol-surface fit, and skew/term-structure) against textbook/literature methodology, then adds edge-case tests that were never written because the original phases (6, 8, 9, 16, 17) tested happy-path behavior only. Nothing in the four computations is mathematically wrong. The RV20 estimator matches the standard close-to-close historical-volatility formula exactly (annualized, mean-centered, `ddof=1`). The 25Δ skew and ATM term-structure selection match the cited convention already in `config.py` (Xing, Zhang & Zhao 2010, JFQA). The vol-surface fit is a thin-plate-spline RBF with a convex-hull coverage mask — a legitimate, if non-parametric (non-arbitrage-constrained), smoothing choice, and the codebase already knows and documents its own limitation ("SVI would be needed to extrapolate further").

The one finding requiring a plan-level decision is naming: the codebase's "VRP" is `vol_index_close − RV20×100`, a **vol-points spread (IV − RV)**, not the Carr & Wu (2009) variance risk premium (`IV² − RV²`, a variance-units quantity, typically expressed as `100 × (VIX² − RV²) / VIX²`). This is a well-established, legitimate, commonly-used simplification in retail/institutional vol commentary (often called "vol premium" or "IV-RV spread") — but it is NOT the academic VRP, and the codebase's own comments already flag internal awareness of this (`"the vrp column ... is NEVER read here"`, `VRP-03` naming for the "clean" series). The phase must decide: (a) rename the field/labels to something accurate like "vol premium" or "IV−RV spread," or (b) keep the "VRP" label but add an explicit docstring/glossary disclaimer that it is a simplified vol-point spread, not the variance-swap VRP. Given `CLAUDE.md`'s "descriptive only, no predictive claims" constraint and the CARD label surfacing directly to the PM, option (b) with a prominent glossary/docstring fix is the lower-risk, smaller-diff path — but this is a decision for the plan, not something research should silently resolve.

Beyond the naming question, the actual hardening work is concrete and boundable: four functions currently have asymmetric exception-handling (`build_movie_payload` wraps its per-frame RBF fit in `try/except`; `build_surface_payload`/`build_diff_payload` do not), one classification default (`_classify_term_structure` returns `"normal"` for <2 points — a substantive-sounding label for an undefined case), one dead-code path (`compute_vrp()` in `vol_metrics.py` is no longer called from production — `vrp_history.vrp_percentile()` superseded it after the VRP-03 fix but the old function and its tests remain), and one latent NaN-vs-None gap (`compute_term_ratios._latest_close` returns `float(nan)` — which is truthy in Python — if the vol-index store's last row has a NaN close, so a stale/corrupt last row silently produces a NaN ratio instead of `None`).

**Primary recommendation:** Treat this as a verification-plus-test phase, not a rewrite. Fix the four concrete gaps found (asymmetric try/except on surface fits, `_classify_term_structure` degenerate-case label, `compute_term_ratios` NaN-close guard, and either retire or explicitly justify `compute_vrp()`'s continued existence), decide+document the VRP naming question, and write edge-case tests matching the existing `engine/tests` fixture-based style (synthetic `DataFrame`/`Series` fixtures, `monkeypatch` for I/O, `pytest.approx`, class-per-computation grouping).

## Architectural Responsibility Map

This is a single-process local Python pipeline, not a multi-tier web app — the "tiers" here are pipeline stages, not client/server boundaries.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| RV20 (realized vol) | Compute (`engine/vol/vol_metrics.py`) | Data (`engine/compute.py` spot history) | Pure function on a price Series; no I/O of its own |
| VRP percentile | Compute (`engine/vol/vrp_history.py`) | Data (`engine/data/vol_index.py`, yfinance) | Composes `compute_rv20` + CBOE vol-index store; owns its own I/O fetch |
| Vol-surface fit (RBF) | Compute (`engine/surface/surface_interactive.py`, `engine/gex/analytics.py`) | Presentation (`app.py`, `engine/report/report.py`) | `rbf_grid`/`coverage_mask` are the single source of truth; consumed by both dashboard and email |
| Surface evolution scalars | Compute (`engine/surface/surface_evolution.py`) | Data (`engine/data/surface_history.py` parquet) | Pure scalar function + idempotent parquet persistence layer |
| Skew (25Δ) / term structure | Compute (`engine/vol/vol_metrics.py`) | Presentation (`engine/report/card_model.py`) | Pure functions on the chain DataFrame; card_model formats for display only |

**Why this matters for the audit:** all four computations already live in the Compute tier as pure functions (no I/O, no Streamlit calls) per the existing `engine/vol/vol_metrics.py` docstring convention — this is good architecture and the phase should preserve it. Hardening work (try/except, guards) belongs in the same pure-function layer, not pushed up into `card_model.py` or `app.py`.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RIGOR-01 | Existing statistical/quant computations (VRP, RV20, vol surface fit, skew/term structure) reviewed for correctness against documented methodology, with edge cases checked | See "Reference Methodology" and "Current-Behavior Gap Findings" below — RV20/skew/term-structure formulas verified correct; VRP naming flagged as a decision item; 4 concrete code gaps identified for fix |
| RIGOR-02 | Test coverage expanded for these computations' edge cases, not just happy path | See "Edge-Case Catalog" and "Test Patterns" below — enumerates untested edge inputs per computation and the existing fixture/monkeypatch style new tests must match |
</phase_requirements>

## Reference Methodology Per Computation

### RV20 — `engine/vol/vol_metrics.py:compute_rv20`

**Implementation:**
```python
prices = spot_history.iloc[-21:].to_numpy(dtype=float)
log_returns = np.log(prices[1:] / prices[:-1])
return float(np.sqrt(252) * log_returns.std(ddof=1))
```

**Yardstick:** close-to-close realized/historical volatility — the standard textbook estimator (e.g. Hull, *Options, Futures, and Other Derivatives*): annualized sample standard deviation of daily log returns.
`σ_CC = sqrt(252/(n-1) · Σ(ln(Cₜ/Cₜ₋₁) − r̄)²)` [CITED: macrosynergy.com/research/six-ways-to-estimate-realized-volatility, flashalpha.com/articles/yang-zhang-vs-close-to-close-realized-volatility]

**Verdict:** MATCHES. `np.std(ddof=1)` centers on the sample mean by default (NumPy does not offer an uncentered "sum-of-squares" std via this call), so the implementation is the textbook mean-centered, `n-1`-denominator, `√252`-annualized estimator — not the zero-mean high-frequency Andersen–Bollerslev realized-variance convention (which is appropriate for intraday data, not this daily-close use case). No discrepancy found. Confidence: HIGH (formula cross-verified against 2 independent sources; code read directly).

**Known, accepted limitation (not a bug):** close-to-close is the least statistically efficient of the common RV estimators — Parkinson (high-low), Garman-Klass (OHLC), and Yang-Zhang (overnight-jump-aware) all have lower estimation variance for the same sample size. The codebase does not have OHLC granularity for the underlying spot series (yfinance daily close only, per `_fetch_closes_yf`), so switching estimators is not a drop-in fix — it would require a new data source. Out of scope for this phase; document as accepted simplification, not something to fix.

### VRP — `engine/vol/vrp_history.py:vrp_history_series` / `vrp_percentile`

**Implementation:** `vrp_hist = aligned["vi"] - aligned["rv"] * 100` — both terms in vol points (e.g. VIX close of 18.0 minus RV20×100 of 15.8 = 2.2).

**Yardstick claimed by the academic literature term "VRP":** Carr & Wu (2009), *Variance Risk Premia*, defines VRP as the difference between the risk-neutral (implied) variance and the physical (realized) variance — `IV² − RV²`, a **variance-units** quantity, commonly normalized as excess return `ER = 100 × (VIX² − RVol²) / VIX²` [CITED: engineering.nyu.edu/sites/default/files/2019-01/CarrReviewofFinStudiesMarch2009-a.pdf, en.wikipedia.org/wiki/Variance_risk_premium].

**Verdict: METHODOLOGY-NAME MISMATCH, flagged for plan-level decision.** The codebase's "VRP" is a **linear vol-point spread (IV − RV)**, not the academic **variance risk premium (IV² − RV²)**. This is NOT a math bug — IV-minus-RV in vol points is a widely used, legitimate simplification in practitioner/retail vol commentary (frequently just called "vol premium," "IV/RV spread," or loosely "VRP" in less rigorous sources) — but it is a different quantity with different scaling behavior (variance-unit VRP is convex in vol level; the vol-point spread is linear). The codebase's own internal comments already show awareness of a related, narrower issue: the `VRP-03` fix (2026-07-16, evident in `vrp_history.py` docstrings and `card_model.py:258-261`) already corrected an internal-consistency bug where the displayed VRP scalar and its percentile rank used to be computed from two different bases (CBOE `iv30` vs `vol_index`); that fix did NOT touch the underlying variance-vs-vol-points naming question, which predates it.

**Decision options for the plan (do not resolve here):**
1. **Document as intentional deviation** — add a docstring/glossary line ("VRP" here = IV−RV vol-point spread, not Carr-Wu variance risk premium) in `vrp_history.py`, `card_model.py`, and any user-facing glossary. Lowest-risk, smallest diff.
2. **Rename the field/label** — e.g. "Vol Premium" or "IV−RV Spread" everywhere the value surfaces (card label, email, docstrings, config comments). More accurate, larger diff (touches display layer + tests asserting on the "VRP" label string), and would need to preserve the internal Python name (`vrp_history.py`, `compute_vrp`) or do a broader rename — likely bigger than "hardening" scope.
3. **Compute the true variance-units VRP as an additional/alternative field** — out of scope per `RIGOR-01`'s "review EXISTING computations" framing (this would be new signal-adjacent work, arguably brushing against the "no new signals" constraint in `CLAUDE.md`).

Given `CLAUDE.md`'s "no new signals" and "small diffs" preferences, option 1 (document as intentional deviation, keep the label) is the path of least resistance and matches project norms — but this is Adam's call, not something to silently pick.

**Assumption flag:** the claim that vol-point IV−RV spreads are "widely used in practitioner commentary" is [ASSUMED] pattern-matching against general vol-trading knowledge, not verified against a specific named practitioner source in this session.

### Vol-surface fit — `engine/surface/surface_interactive.py`, `engine/gex/analytics.py:rbf_grid`/`coverage_mask`

**Implementation:** thin-plate-spline RBF interpolation (`scipy.interpolate.RBFInterpolator`) over std-normalized `(DTE, ln(K/S))` coordinates, with smoothing regularization (`SURFACE_INTERACTIVE_SMOOTHING=0.5`, `SURFACE_SMOOTHING=1.5` — tuned via leave-one-expiry-out CV, per `config.py` comments), plus a convex-hull (`Delaunay`) coverage mask that NaN-holes any grid cell outside the real quote cloud (extrapolation), never fabricating values beyond the data.

**Standard failure modes for vol-surface fitting (industry-standard, e.g. SVI/SABR literature context):**
- **Arbitrage violations** (calendar-spread arbitrage: total variance must be non-decreasing in DTE at fixed strike; butterfly arbitrage: the implied risk-neutral density must be non-negative) — this codebase's RBF fit has **no arbitrage constraints** at all. This is an accepted, documented limitation, not a bug to fix: the codebase is explicitly "descriptive only" (per `CLAUDE.md`) and does not claim the surface is a tradeable/arbitrage-free pricing surface — it is a smoothed visualization of quoted IVs. [ASSUMED: no evidence the phase intends to add SVI/arbitrage-free fitting — this would be new-model-adjacent work, likely out of scope per MODEL-01/02 deferral.]
- **Extrapolation beyond quoted strikes/expiries** — already solved via `coverage_mask`'s convex-hull gate (2026-06 fix, replacing an earlier kNN-radius mask that under-covered ~22% vs ~90% now — see `08-VERIFICATION.md` reference in `analytics.py` comments). HIGH confidence this is handled correctly; verified by reading `test_surface_holes.py`.
- **Degenerate single-expiry surfaces** — explicitly guarded: `build_surface_payload` requires `len(d_fit) >= 6` AND `d_fit["dte"].nunique() >= 2` (a single expiry is collinear — no 2D convex hull is possible), returning `None` cleanly. Same guard exists in `coverage_mask` (`len(np.unique(dte_v)) < 2` → all-False mask) and `build_diff_payload`/`build_movie_payload`. Verified present in all four surface-fit entry points.

**Verdict:** the interpolation and masking approach matches its own documented intent (smoothed, honest-about-holes visualization, not an arbitrage-free pricing surface) — no methodology mismatch found for what the code claims to be. Confidence: HIGH for the coverage-mask logic (test-verified); MEDIUM for the "no arbitrage constraints needed" framing (a value judgment, not a fact — flagging as a note rather than asserting it as settled).

**Current-gap found (exception-handling asymmetry, not a methodology error):** `build_movie_payload` wraps its per-frame `_fit_rbf` call in `try/except Exception` (comment: `"one bad session (singular fit, degenerate hull) must not kill the video"`) — but `build_surface_payload` and `build_diff_payload` do NOT wrap their RBF fit calls at all. If `RBFInterpolator` raises (e.g. `scipy.linalg.LinAlgError` on a near-singular design matrix from duplicate/near-duplicate `(dte, log_moneyness)` points — possible if CBOE returns duplicate strike rows for a thin/cold-start day), `build_surface_payload`/`build_diff_payload` will propagate the exception uncaught rather than degrading to `None` the way the sparse-data guard already does for the `<6 points` case. This is exactly the kind of inconsistency RIGOR-01 should catch: two of three near-identical functions defend against the same failure mode, one doesn't.

### Skew (25Δ) + Term Structure — `engine/vol/vol_metrics.py:compute_skew_25d`, `compute_term_structure`

**Yardstick:** 25-delta risk-reversal skew, `IV(25Δ put) − IV(25Δ call)`, is the standard convention in the empirical options-pricing literature for measuring the "smirk"/skew — cited in-repo as Xing, Zhang & Zhao (2010, *Journal of Financial and Quantitative Analysis*), already referenced in `config.py:149` (`SKEW_MIN_DTE`, `SKEW_PUT_DELTA`, `SKEW_CALL_DELTA` docstrings). [CITED: config.py in-repo citation — not independently re-verified against the JFQA paper in this session, since the citation is already an established, locked project decision per STATE.md 2026-05+ history.]

**Sign convention verified in code:** `skew = put_iv - call_iv` (line 183). Since OTM puts are typically richer than OTM calls in equity index markets (the "smirk"), a positive `skew` value means "puts pricier" — matches `card_model.py`'s explicit direction-stating format (per STATE.md decision "Skew (25Δ) card field states direction explicitly... instead of a bare signed number," 2026-07-16). Delta convention: CBOE put deltas are negative (`SKEW_PUT_DELTA = -0.25`), calls positive (`0.25`) — both target 25Δ magnitude, symmetric risk-reversal. HIGH confidence, verified directly against code + existing tests (`test_skew_25d_known_strikes`).

**Term-ratio convention:** only SPY has CBOE 9-day/3-month vol-index siblings (`VIX9D`/`VIX3M`); QQQ/IWM gracefully degrade to `None`/`None` — already documented and tested (`_TERM_SYMBOLS` dict, `test_term_ratios.py`), matching `CLAUDE.md`'s explicit "CBOE vol-index term siblings (verified 2026-06-23)" constraint. No gap found here beyond the NaN-close edge case below.

**Current-gap found (`_classify_term_structure` degenerate default):** `if len(points) < 2: return "normal"`. A single-point (or zero-point) term structure has no defined "shape" — labeling it `"normal"` asserts a specific claim (upward-sloping-ish, unremarkable curve) about data that cannot support any shape claim at all. This is the kind of "silently wrong" (vs. explicitly undefined) result the phase's success criteria calls out. A defined-correct behavior would be a distinct sentinel (e.g. `"insufficient_data"` or `None`) so the card/email layer can omit or caveat the field rather than asserting a specific curve shape it cannot support.

**Current-gap found (`compute_term_ratios` NaN-vs-None):**
```python
def _latest_close(symbol: str) -> float | None:
    df = load_vol_index(symbol)
    if df.empty:
        return None
    return float(df.iloc[-1]["close"])
```
If the vol-index parquet's last row has `close = NaN` (a plausible outcome of a partial/corrupt CBOE fetch that still wrote a row), `float(df.iloc[-1]["close"])` returns Python `nan` — which is **truthy** in Python (`bool(float('nan')) is True`). The downstream guard `(close_9d and close_30d)` will therefore treat a NaN close as "present," compute `nan / nan = nan`, and return a NaN ratio rather than `None`. Every consumer checking `is not None` (the standard pattern throughout this codebase, e.g. `_fmt_term_ratios`) would then receive a NaN it doesn't expect and hasn't guarded — a genuine silently-wrong path, not tested today (`test_term_ratios.py`'s "missing data" test only covers an *empty* DataFrame, not a NaN-valued last row).

### Dead-code note (adjacent to but not itself a methodology issue): `compute_vrp()` in `vol_metrics.py`

`compute_vrp(iv30, rv20)` (the simple `iv30 - rv20` function, decimal-fraction contract) is no longer called from `engine/compute.py` — confirmed via `grep`: the only non-test, non-planning-doc caller was removed when the VRP-03 fix routed the production VRP path entirely through `vrp_history.vrp_percentile()` (2026-07-16). `compute_vrp()` and its 3 unit tests remain in the codebase, exercising a function nothing in production calls anymore. Not a bug — but worth flagging for RIGOR-01's "correctness against documented methodology" lens: is this intentionally kept as a pure-function reference implementation, or is it stale and should be removed (CLEAN-01 territory, arguably; CLEAN phase already closed, so this phase is where it would get caught)? Recommend the plan either (a) delete it + its tests as dead code discovered during the audit, or (b) keep it but add a comment clarifying it's retained for [reason] and not on the production path — do not leave it silently orphaned and undocumented.

## Edge-Case Catalog

| # | Computation | Edge Input | Defined-Correct Behavior | Currently Tested? |
|---|-------------|-----------|--------------------------|---|
| E1 | RV20 | Fewer than 21 prices (thin history / cold-start) | Return `None` | Yes — `test_rv20_cold_start` |
| E2 | RV20 | NaN or ≤0 price in the 21-price window | Return `None` (guarded: `np.any(np.isnan(prices))`, `np.any(prices <= 0)`) | **No** — no test exercises this guard |
| E3 | RV20 | All 21 prices identical (zero realized vol) | Return `0.0` (not `None`, not NaN) — log returns all zero, `std(ddof=1)` of an all-zero array is `0.0`, not NaN | **No** |
| E4 | VRP | Empty vol-index store | Return `{"vrp": None, "pct": None, "n": 0}` | Yes — `test_empty_vol_index_returns_none_dict` |
| E5 | VRP | yfinance fetch fails/returns None | Same none-dict | Yes — `test_yfinance_failure_returns_none_dict` |
| E6 | VRP | No calendar overlap between vol-index dates and price-close dates | Same none-dict | Yes — `test_no_alignment_returns_none_dict` |
| E7 | VRP | Vol-index has a NaN close on some (non-last) historical dates | `dropna()` in `aligned = pd.DataFrame({"vi":..., "rv":...}).dropna()` drops those rows — series just has fewer aligned points, not a crash | **No** — no test with a NaN scattered mid-series |
| E8 | VRP | Single aligned data point (`n=1`) | `percentileofscore` of a 1-element array returns 100 (or 0, depending on `kind="rank"` tie behavior) — need to confirm this doesn't crash/misreport | **No** |
| E9 | Skew/term structure | Empty chain DataFrame | `valid.groupby("expiry")` on empty → loop body never runs → `{"front_month": None, "second_month": None}` (skew) / `{"points": [], "classification": "normal", "front_atm_iv": None, "back_atm_iv": None}` (term structure) | **No direct test on a literally empty df** (existing tests use "insufficient strikes," not zero rows) |
| E10 | Skew/term structure | Missing required column (e.g. no `"T_years"` or `"delta"` column at all) | `KeyError` raised (loud failure — acceptable per success criteria, but should be an intentional/tested contract, not an accident) | **No** |
| E11 | Term structure | Single-expiry chain (`len(points) == 1`) | Currently returns `"normal"` — **flagged above as the gap to fix**; correct behavior should be a distinct "undefined/insufficient" label | **No** |
| E12 | Term ratios | QQQ/IWM (no 9D/3M CBOE siblings) | `None`/`None` | Yes — `test_compute_term_ratios_qqq_graceful`, `_iwm_graceful` |
| E13 | Term ratios | Vol-index store's last row has `close = NaN` | Should return `None` for that leg (a NaN close is not a valid quote) — **currently returns NaN instead**, per the gap above | **No** |
| E14 | Term ratios | Vol-index store's last row has `close = 0.0` | `(close_9d and close_30d)` correctly treats `0.0` as falsy → returns `None` (defensive, arguably by-accident-but-correct) | **No** |
| E15 | Vol-surface fit | Fewer than 6 quotes in-band | `build_surface_payload`/`build_diff_payload`/`coverage_mask` all return `None`/all-False cleanly | Yes — `test_none_on_empty` |
| E16 | Vol-surface fit | Single-expiry chain (collinear points, no 2D hull) | `None` (guarded by `nunique() < 2` check in all 3 payload builders + `coverage_mask`'s `QhullError` catch) | Yes — `test_none_on_single_expiry` |
| E17 | Vol-surface fit | Duplicate/near-duplicate `(dte, log_moneyness)` points causing a near-singular RBF fit | `build_movie_payload` catches this per-frame (`try/except Exception: continue`); `build_surface_payload`/`build_diff_payload` do **not** catch it | **No** — and current behavior is inconsistent across the 3 builders (the gap flagged above) |
| E18 | Vol-surface fit | `spot <= 0` or `spot is None` passed to `rbf_grid`/`coverage_mask` | `np.log(strike / spot)` with `spot<=0` produces `inf`/`nan`/`-inf` log-moneyness, not a crash — but downstream behavior (mask, RBF fit quality) is unverified | **No** |
| E19 | Vol-surface fit | Surface DataFrame missing expected columns (`iv_pct`, `log_moneyness`, `strike`, `dte`) | `KeyError` (loud failure) | **No** |
| E20 | All four | `NaN` propagating through to a downstream display layer (`card_model.py`) that expects `None` for "no data" | Each `_fmt_*` helper in `card_model.py` checks `is None`, not `pd.isna()`/`np.isnan()` — any function that returns NaN instead of None (E13 above is the concrete instance found) will bypass the "insufficient history" messaging and could render `"nan"` literally in the email/dashboard | **No** — this is the cross-cutting risk the whole audit should watch for |

## Current-Behavior Gap Findings (Summary)

1. **VRP naming/methodology mismatch** — flagged above as a plan-level decision, not silently resolved here.
2. **`build_surface_payload`/`build_diff_payload` lack the `try/except` around `_fit_rbf` that `build_movie_payload` already has** — inconsistent defensive coverage for the same failure mode (near-singular RBF fit).
3. **`_classify_term_structure` returns `"normal"` (a substantive claim) for <2 points** instead of a distinct "insufficient data" sentinel.
4. **`compute_term_ratios._latest_close` returns a NaN float (truthy) instead of `None`** when the vol-index store's last row has a NaN close — breaks the `is not None` contract every consumer relies on.
5. **`compute_vrp()` in `vol_metrics.py` is dead code** (no production caller since the VRP-03 fix) — decide keep-with-comment vs. remove-with-tests.

None of these are "the math is wrong" findings — RV20, skew, and term-structure formulas all check out against their cited/standard methodology. The gaps are all in defensive coding (exception handling, None-vs-NaN discipline, degenerate-case labeling), which is exactly what RIGOR-02's edge-case test expansion should target.

## Test Patterns (match existing `engine/tests` style)

Observed conventions across `test_vol_metrics.py`, `test_vrp_history.py`, `test_surface_interactive.py`, `test_surface_holes.py`, `test_term_ratios.py` — new tests for this phase should follow the same shape:

- **Synthetic fixtures, no real data.** Chain/surface DataFrames built inline via `pytest.fixture` functions (`chain_df`, `term_df`, `_surface_df`, `_chain`) with hand-picked deterministic values so expected outputs can be computed by hand or by re-deriving the formula in the test itself (see `test_rv20_manual`'s independent NumPy re-derivation).
- **`monkeypatch` for all I/O** (`vrp_history.py` tests monkeypatch `load_vol_index` and `_fetch_closes_yf`; `test_term_ratios.py` uses `@patch("engine.data.vol_index.load_vol_index", ...)`). Never hits CBOE, yfinance, or real parquet in a unit test.
- **Class-per-computation grouping** (`class TestComputeRv20:`, `class TestComputeVrp:`, `class TestHappyPath:` / `class TestColdStart:` / `class TestDeepWindow:` / `class TestFailurePaths:` in `test_vrp_history.py`) — new edge-case tests should likely add a `class TestEdgeCases:` or extend the existing `TestFailurePaths`-style class per module rather than inventing a new file-level structure.
- **`pytest.approx` for float comparisons**, never bare `==` on computed floats.
- **Assert on the full dict shape** where a function returns a dict contract (`assert res == {"vrp": None, "pct": None, "n": 0}` pattern in `test_vrp_history.py`) — this is the right pattern for the None-vs-NaN gaps above: assert the *exact* value (`is None`, not just falsy) to catch a NaN regression.
- **`None` on empty/degenerate input, tested explicitly** (`test_none_on_empty`, `test_none_on_single_expiry`, `test_surface_still_one_valid_figure` on an empty DataFrame) — the existing surface tests already have this pattern; new RIGOR-02 tests for `build_surface_payload`/`build_diff_payload` exception-handling (E17) should follow `test_wing_extrapolation_creates_nan_holes`'s style of constructing a deliberately-adversarial synthetic chain (here: duplicate `(dte, log_moneyness)` rows) and asserting the function degrades to `None` rather than raising.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Detecting NaN vs None in a float-returning function | A custom `is_missing()` helper | `math.isnan()` / `pd.isna()` explicitly at every `is None` boundary already in the codebase (`card_model.py` `_fmt_*` helpers) | The bug class here is exactly "NaN silently passes an `is None` check" — the fix is adding the right existing stdlib/pandas call at the right boundary, not new infrastructure |
| Arbitrage-free vol-surface fitting (SVI/SABR) | A parametric arbitrage-free surface fitter | Nothing — out of scope this phase | RIGOR-01 audits the EXISTING descriptive RBF fit against its own documented intent (smoothed visualization), not against a different fitting paradigm; building SVI/SABR would be new-model-adjacent work per the MODEL-01/02 deferral |

**Key insight:** this phase's "don't hand-roll" risk is inverted from a typical greenfield phase — the risk isn't building unnecessary new infrastructure, it's over-scoping the audit into a rewrite. The four computations are small, already-tested pure functions; the fix set found above is all small, targeted patches (a try/except, a sentinel return value, a `pd.isna()` guard, a naming/docstring decision) — not new modules.

## Common Pitfalls

### Pitfall 1: Treating NaN as "no data" without checking explicitly
**What goes wrong:** A function returns `float('nan')` instead of `None` on a bad-data edge case; every downstream `is None` check silently passes it through, and `f"{value:.1f}"`-style formatting renders the literal string `"nan"` in a dashboard card or email.
**Why it happens:** `nan` is truthy in Python and passes through arithmetic (`nan + 1 == nan`, no exception) — there is no natural point where code "notices" NaN unless it explicitly checks for it.
**How to avoid:** at every function boundary that can return `None` for "insufficient/bad data," explicitly guard with `pd.isna(x)` / `math.isnan(x)` before deciding whether to return `None`, not just `x is None`.
**Warning signs:** any `float(df.iloc[-1][col])` pattern reading directly from a parquet/CSV store without an intervening `.dropna()` or `pd.isna()` check (found in `compute_term_ratios._latest_close`; worth grepping for the same pattern elsewhere, e.g. `compute_vvix_level` has an identical `float(df.iloc[-1]["close"])` line with the same latent risk).

### Pitfall 2: Confusing "guarded against the obvious edge case" with "guarded against all edge cases in the same function"
**What goes wrong:** `build_movie_payload` was hardened against RBF-fit failure (per-frame `try/except`) because a video with N frames is statistically far more likely to hit a bad session than a single-day surface — but the same failure mode exists in the single-day builders and was never back-ported.
**Why it happens:** hardening tends to happen where a bug was actually observed/reproduced (the movie feature, iterating over many days, surfaces rare failures more often), not systematically across all call sites sharing the same underlying risk.
**How to avoid:** when auditing, explicitly diff near-identical functions (`build_surface_payload` vs `build_diff_payload` vs `build_movie_payload`) for handling-pattern consistency, not just correctness in isolation.
**Warning signs:** a code comment explaining why one function has defensive handling ("...must not kill the video") is itself a signal to check whether sibling functions need the same handling.

### Pitfall 3: Assigning a substantive default label to an underdetermined case
**What goes wrong:** `_classify_term_structure([single_point]) == "normal"` — "normal" is not a neutral/null value, it's a specific claim about curve shape (upward-sloping, unremarkable) that a single point cannot support.
**Why it happens:** early-return guards are usually added to prevent a crash (e.g. `ivs[0]`/`ivs[-1]` indexing on an empty list), and the easiest safe return value gets reused rather than a purpose-built sentinel.
**How to avoid:** for classification functions, reserve a distinct "insufficient data" outcome distinguishable from every real classification, and make the caller (`card_model.py`) explicitly omit/caveat that outcome rather than displaying it as if it were a real read.
**Warning signs:** any early-return in a classifier that reuses one of the "real" output labels instead of a sentinel.

## Code Examples

### Existing pattern to extend: none-dict assertion style (from `test_vrp_history.py`)
```python
# Source: engine/tests/test_vrp_history.py (existing pattern to follow for new NaN-close tests)
def test_empty_vol_index_returns_none_dict(self, monkeypatch):
    monkeypatch.setattr(vrp_history, "load_vol_index", lambda sym: pd.DataFrame())
    res = vrp_history.vrp_percentile("SPY")
    assert res == {"vrp": None, "pct": None, "n": 0}
```
A new test for the `compute_term_ratios` NaN-close gap (E13) should follow this exact shape: monkeypatch `load_vol_index` to return a DataFrame whose last row has `close=float("nan")`, then assert `result["term_ratio_9d_30d"] is None` (not just falsy) — this assertion would currently FAIL against the existing code, which is the point: it documents the gap as a red test before the fix.

### Existing pattern to extend: adversarial synthetic chain (from `test_surface_holes.py`)
```python
# Source: engine/tests/test_surface_holes.py
def test_wing_extrapolation_creates_nan_holes():
    df = _chain([10, 20, 40, 70, 90], [-8, -4, 0, 4, 8])
    fig = plot_vol_surface(df, "SPY", SPOT)
    z = _z(fig)
    assert np.isnan(z).any()
```
A new test for E17 (duplicate points crashing `build_surface_payload`) should construct a chain with two rows at the exact same `(dte, log_moneyness)` (or extremely close, e.g. differing by float epsilon) and assert `build_surface_payload(...)` returns `None` (or a valid dict) rather than raising — currently this would need the `try/except` fix to pass.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| CBOE `iv30` snapshot field used as the VRP's implied-vol leg | `vol_index` (CBOE VIX/VXN/RVX daily close series) used exclusively, both for today's scalar and its percentile history | 2026-07-16 (VRP-03 fix) | Already resolved before this phase; not a re-open item, just context for why `compute_vrp(iv30, rv20)` is now dead code |
| kNN-radius coverage mask for the vol surface | Convex-hull (Delaunay) coverage mask | Phase 8/9 (per `08-VERIFICATION.md` reference in `analytics.py`) | Already resolved; coverage went from ~22% to ~90% on liquid names — no further action needed this phase |

**Deprecated/outdated:** `compute_vrp(iv30, rv20)` in `vol_metrics.py` — superseded by `vrp_history.vrp_percentile()`, no production caller remains.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Vol-point IV−RV spreads are "widely used" in practitioner/retail vol commentary as an informal "VRP" | Reference Methodology — VRP | Low — this is framing/context for the naming decision, not something the fix depends on being true; the fix works the same regardless |
| A2 | No arbitrage-constrained (SVI/SABR) vol-surface fitting is in scope or expected for this phase | Reference Methodology — Vol-surface fit | Medium — if Adam actually wants arbitrage-free fitting, this phase's scope is wrong; should be confirmed at discuss-phase, not assumed silently by the plan |
| A3 | The Xing, Zhang & Zhao (2010) citation already in `config.py` is accurate and does not need independent re-verification against the source paper | Reference Methodology — Skew | Low — this is a pre-existing, already-locked project decision (per STATE.md history back to Phase 6/16), not a new claim introduced by this research |

## Open Questions (RESOLVED)

Both open questions were resolved by Adam at `/gsd:discuss-phase 25` and locked in 25-CONTEXT.md; planned in phase 25.

1. **Does Adam want the VRP naming fixed (rename) or just documented (glossary/docstring disclaimer)?**
   - **RESOLVED (25-CONTEXT.md, Adam 2026-07-26):** DOCUMENT AS INTENTIONAL DEVIATION — keep the vol-point-spread computation unchanged AND keep the "VRP" identifier/label; add an honest one-line definition at first use (docstring in vrp_history.py + glossary/email footnote) stating it is a practitioner IV−RV proxy, not the Carr-Wu variance-swap VRP. No rename. Planned in 25-03.
   - What we knew: the vol-point spread is legitimate but mislabeled relative to the academic term.
   - What was unclear: whether "VRP" as a card label is load-bearing enough that renaming it would be more disruptive than valuable, vs. whether the mislabeling itself is worth the small diff to fix.

2. **Should `compute_vrp()` be deleted (dead code) or kept as a documented reference implementation?**
   - **RESOLVED:** DELETE + remove its tests — zero production callers (grep-confirmed), and CLAUDE.md prefers deleting unused code cleanly with no backwards-compat shims. Planned in 25-01 Task 3.
   - What we knew: it has zero production callers; its 3 tests exercise it.
   - What was unclear: whether keeping it as a "simple reference formula, not what's live" is intentional documentation value or accidental staleness.

## Environment Availability

No new external dependencies for this phase — it audits and hardens code already running against already-available data (CBOE vol-index parquet store, yfinance, existing `engine/tests` pytest infrastructure). Skipping the full audit table; nothing to newly provision.

## Package Legitimacy Audit

Not applicable — this phase installs no new packages. All work is against `numpy`, `pandas`, `scipy` (`RBFInterpolator`, `percentileofscore`, `Delaunay`), and `pytest`, all already in `requirements.txt` and already in production use.

## Security Domain

`security_enforcement` is absent from `.planning/config.json` (treated as enabled per protocol), but this phase has essentially no external attack surface: no new auth, session, or access-control code; no new user-facing input beyond data already parsed elsewhere (CBOE JSON, yfinance, parquet). The one applicable category:

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V5 Input Validation | Yes (narrow) | Explicit `pd.isna()`/`math.isnan()`/finite-value guards at every function boundary that decides "is this data present or missing" — exactly the gaps this phase's edge-case hardening targets (E2, E7, E13, E18) |
| V2/V3/V4 (Auth/Session/Access Control) | No | No new auth surface introduced |
| V6 Cryptography | No | No crypto/secrets touched |

No STRIDE threat table — this is a local single-user diagnostics tool with no network-facing trust boundary changed by this phase.

## Sources

### Primary (HIGH confidence)
- Direct code read: `engine/vol/vol_metrics.py`, `engine/vol/vrp_history.py`, `engine/surface/surface_interactive.py`, `engine/surface/surface_evolution.py`, `engine/gex/analytics.py` (rbf_grid/coverage_mask), `engine/config.py`, `engine/compute.py`
- Direct test read: `engine/tests/test_vol_metrics.py`, `test_vrp_history.py`, `test_surface_interactive.py`, `test_surface_holes.py`, `test_surface_evolution.py`, `test_term_ratios.py`
- `pytest engine/tests --collect-only` — confirmed live baseline of 449 tests (matches STATE.md, corrects the stale 364 figure in the roadmap/success-criteria doc)

### Secondary (MEDIUM confidence)
- [Carr & Wu (2009), Variance Risk Premia — NYU Engineering](https://engineering.nyu.edu/sites/default/files/2019-01/CarrReviewofFinStudiesMarch2009-a.pdf) — VRP = IV² − RV² definition, cross-checked against Wikipedia summary
- [Variance risk premium — Wikipedia](https://en.wikipedia.org/wiki/Variance_risk_premium)
- [Six ways to estimate realized volatility — Macrosynergy](https://macrosynergy.com/research/six-ways-to-estimate-realized-volatility/) — close-to-close formula cross-check
- [Yang-Zhang vs Close-to-Close — FlashAlpha Research](https://flashalpha.com/articles/yang-zhang-vs-close-to-close-realized-volatility) — confirms close-to-close as standard/common baseline estimator

### Tertiary (LOW confidence)
- None used as load-bearing for a specific claim — the Xing, Zhang & Zhao (2010) skew citation was NOT independently re-verified this session (already a locked, pre-existing project decision per `config.py` comments and STATE.md history; treated as given, not re-researched).

## Metadata

**Confidence breakdown:**
- Standard stack: N/A (no new libraries) — HIGH confidence all four computations use already-appropriate, already-in-use tooling (numpy/scipy/pandas)
- Architecture: HIGH — pure-function layering already correct; no architectural change needed
- Methodology correctness (RV20, skew, term-structure): HIGH — formulas verified against cited/standard sources, no discrepancy found
- Methodology naming (VRP): MEDIUM — the mismatch itself is HIGH confidence (cross-verified against 2 sources), but the right resolution is a judgment call flagged for discuss-phase, not a research-level fact
- Edge-case gaps (exception handling, NaN/None, degenerate labels): HIGH — read directly from source, not inferred

**Research date:** 2026-07-26
**Valid until:** effectively indefinite for the methodology-correctness findings (these are stable math facts); ~30 days for the "current test baseline = 449" figure since the codebase is under active development

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
<!-- LINKS:END -->
