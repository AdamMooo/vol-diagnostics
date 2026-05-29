# Feature Research — v3.3 "Surface Evolution & Daily Intelligence"

**Domain:** Institutional vol-desk / quant diagnostics tooling (descriptive, no predictive claims)
**Researched:** 2026-05-29
**Confidence:** HIGH on surface-validation and PCA conventions (academic + practitioner sources agree); MEDIUM on daily-report content (practitioner blogs, not primary literature)

---

## Framing for the consumer

This milestone builds analytics **on top of** the existing RBF/TPS vol surface (`gex/analytics.py::plot_vol_surface`, raw points persisted by `gex/surface_history.py`). The single most important architectural fact: **most of v3.3 depends on the surface being trustworthy first.** A ΔIV-decomposition, a PCA, or a "surface velocity" number computed on an overfit / hallucinated-in-the-extrapolation-zone surface is worse than useless — it manufactures signal where there is none.

So the natural gate is: **Phase 8 = Surface Validation (table stakes, blocking). Phases 9+ = evolution/report analytics (build on the validated surface).**

The current TPS implementation has two specific honesty problems the validation phase must address:
1. **`smoothing=1.5` is a hand-tuned magic number** — same class of sin as the retired "$200M neutral floor." It needs a defensible selection method (LOOCV) or at minimum a documented sensitivity sweep.
2. **RBF extrapolates into the convex hull's exterior with no flag** — the comment "no convex-hull NaN cliffs, graceful extrapolation" is exactly the thing that makes a surface look smooth and authoritative in regions where there is *zero* market data. A coverage mask is the fix.

---

## Feature Landscape

### Table Stakes (a vol-desk tool is not credible without these)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Coverage / extrapolation mask** | Showing interpolated IV where no quotes exist is the cardinal sin of surface tooling. Desks always distinguish "fitted from data" vs "extrapolated guess." | LOW | `scipy.spatial.ConvexHull` + `Delaunay.find_simplex(grid_pts) < 0` → boolean mask of cells outside the hull of real (dte, %OTM) quotes. Render masked cells greyed/hatched, or set opacity. ~20 lines. **This is the highest-value, lowest-cost item in the milestone.** |
| **Fit residual diagnostic (raw quote vs fitted)** | "How well does the surface actually reproduce the quotes it was built from?" is the first question any quant asks. | LOW | Evaluate RBF at the *input* (dte, %OTM) points, compare to input `iv_pct`. Report RMSE and max abs residual in vol points (pp). A residual table or residual-vs-strike scatter. With `smoothing=1.5` residuals are non-zero by construction — that's fine and honest. |
| **No-arbitrage sanity checks (calendar + butterfly)** | Static-arbitrage-free is THE definition of a valid surface (Gatheral). A surface that admits arbitrage is mathematically broken. | MEDIUM | **Calendar:** total variance w(k,T) = (IV²·T) must be non-decreasing in T at fixed moneyness → check `np.diff` along DTE axis ≥ 0 (small tolerance). **Butterfly:** call price convex in strike → equivalently Gatheral's g(k) ≥ 0, or the cheaper proxy: implied *total variance* convex in k per slice. Report as PASS/FAIL counts + locations of violations, not a hard reject. Descriptive, not enforcing. |
| **Smoothing-parameter sensitivity sweep** | `smoothing=1.5` is currently unjustified. Desks document how the picture changes under the free parameter. | LOW | Re-fit at smoothing ∈ {0.5, 1.5, 5, 15}, report RMSE + max ΔIV across the grid. Lets you state "the skew shape is stable across smoothing" or flag if it isn't. |
| **ATM term-structure line + 25Δ skew (already exist)** | Standard surface read-outs. Already implemented (`plot_term_structure`, `compute_skew`). | — | Carry forward; v3.3 adds the *change* versions. |

### Differentiators (the "calculus of the surface" — this is the milestone's edge)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **ΔIV field, common-grid (already exists)** | `plot_iv_change_surface` already differences two RBF grids on a shared %OTM/DTE mesh. Foundation for everything below. | — | Already built. **Must inherit the coverage mask** — differencing two extrapolated regions doubles the lie. |
| **Three-scalar ΔIV decomposition: level / term / skew** | Reduces a whole ΔIV field to 3 PM-readable numbers. This is the convention that makes "the surface moved" actionable without staring at a 3D blob. | MEDIUM | See **Decomposition convention** below — fully specified. Pure numpy on the differenced grid. |
| **PCA of historical surface changes (level/slope/curvature)** | Cont & da Fonseca (2002): daily ΔIV surfaces are driven by ~3 orthogonal factors explaining the bulk of variance — interpretable as level, slope (term), curvature (skew). Lets you say "today's move was 80% a level shift" with empirical backing. | MEDIUM-HIGH | Needs ~30+ daily snapshots (you're accumulating them now). Stack each day's ΔIV grid as a flattened vector → `np.linalg.svd` or `sklearn.PCA`. Report variance-explained per factor + project today's move onto the factors. **Gate: needs enough history; honest "insufficient history" until ~40 sessions.** |
| **Multi-horizon comparison (1d / 5d / 20d)** | Same ΔIV decomposition computed vs prior session, ~1 week, ~1 month. Distinguishes a one-day spasm from a regime drift. | LOW | Just re-run the decomposition with `df_prior` = snapshot at t−1, t−5, t−20. Convention: business days, nearest-available snapshot. UI = 3 small-multiples or a toggle. |
| **Surface "velocity" scalar** | Single magnitude-of-change number — Frobenius norm of the ΔIV grid (masked to covered cells), normalised by horizon in trading days → "pp of IV per day." Trend-able over time. | LOW | `np.sqrt(np.nanmean(IV_diff[mask]**2)) / horizon_days`. One scalar, percentile-rankable like GEX. Keep it descriptive — it's a speedometer, not a forecast. |
| **Cross-ticker surface-change comparison** | SPY vs QQQ vs IWM ΔIV decomposition side by side — divergence (IWM skew steepening while SPY flat) is a domestic-stress read consistent with the project's existing IWM rationale. | LOW | Reuses the 3 scalars per ticker → grouped bar, mirrors `plot_skew_cross_ticker`. |

### Anti-Features (seductive, but wrong for a solo descriptive tool)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Switch TPS → full SVI/SSVI fit** | SVI is "the" desk standard and is arbitrage-free *by construction* when calibrated correctly. | SVI is a **per-slice 5-parameter calibration** (a + b(ρ(k−m) + √((k−m)²+σ²))) with a fragile non-linear optimiser; SSVI adds cross-slice no-arb constraints. That's a pricing/calibration engine — months of work, many failure modes, and overkill for a *descriptive* free-data tool. The arbitrage guarantee only holds if calibration converges, which on noisy CBOE delayed quotes it often won't. | **Stay on TPS + add the validation layer.** TPS gives a smooth surface; the no-arb *checks* (not enforcement) tell you when the data itself is inconsistent. State explicitly: "we interpolate and verify, we do not calibrate an arbitrage-free parametric model." Revisit SVI only if a desk consumer demands a tradable/priceable surface (→ v4.x, Bloomberg-tier data). |
| **SABR fit** | Famous, desk-standard for rates/FX smile. | Designed for a *single* expiry smile around a forward; needs a forward and β assumption; same calibration fragility as SVI; no native term-structure handling. Wrong tool for an equity-index full-surface descriptive view. | TPS for the surface; if you want a parametric *slice* read, a simple quadratic-in-log-moneyness per expiry is enough to extract skew/curvature scalars. |
| **Enforce / repair arbitrage (project to nearest arb-free surface)** | "Make the surface clean." | Repairing arbitrage *alters the data* — you'd be reporting a fiction that looks tidy. Violates the project's descriptive-only constraint. Violations are themselves signal (stale quotes, illiquid wings). | **Report** violations, never repair. A flagged butterfly violation in the −15% wing is information: that wing's quotes are untrustworthy → which feeds the coverage mask. |
| **Real-time / intraday surface evolution** | "Watch it move live." | CBOE CDN is delayed; intraday ΔIV is dominated by quote staleness and bid-ask noise, not real information. | Daily cadence only — matches the existing `run_daily` pipeline and the data's actual resolution. |
| **gvol-style implied "fair value" or vol-of-vol forecasting** | gvol/SpotGamma sell forward-looking vol products. | Predictive claim — banned by project constraints. | Velocity + PCA are *descriptive* ("what moved, how much, along which factor"), never "what vol will do." |
| **High-res grid (e.g. 100×80) to look polished** | Smoother render. | Manufactures false precision between sparse quotes; current 40×30 already over-resolves a chain with ~15 strikes × ~6 expiries of real OTM data. | Keep coarse grid; the coverage mask makes the honest sparsity visible, which is the point. |

---

## The ΔIV decomposition convention (specified for implementation)

Given the existing common-grid `IV_diff = IV_today − IV_prior` (shape `[n_otm, n_dte]`, units = vol points / pp), over the **covered region only** (apply the convex-hull mask):

**1. Level (parallel shift), pp.**
`level = nanmean(IV_diff[mask])`
The bulk move of the whole surface. This is PCA factor 1 in Cont–da Fonseca.

**2. Term change (calendar slope shift), pp per 30 DTE.**
De-mean by level, then regress the residual against DTE at ATM (|%OTM| small, e.g. ≤ 2%):
`term = polyfit(dte_atm, (ΔIV_atm − level), 1)[0] * 30`
Positive = far-dated vol rose relative to near (term steepening / contango build). Mirrors the existing `compute_surface_slopes` term_slope scaling (×30 DTE) — **reuse that scaling so the two numbers are comparable.**

**3. Skew change (wing-asymmetry shift), pp per 10% moneyness.**
At the front expiry band (DTE ≤ 45), de-meaned by level, regress residual against %OTM:
`skew = polyfit(pct_otm_front, (ΔIV_front − level), 1)[0] * 10`
Negative = downside wing richened faster than upside (put skew steepening). Scale to "per 10% OTM" to match the existing strike-slope convention (current code uses ×log(1.10); for a %OTM axis use ×10 so units read as "pp per 10% move").

**Convention notes (state these verbatim in the UI / WALKTHROUGH):**
- All three are **linear-fit model constructs with no predictive backing** — same disclaimer already applied to `compute_surface_slopes`.
- Sign conventions: level >0 = vol up; term >0 = curve steepening to the back; skew <0 = downside protection bid.
- Compute on the **masked** grid only — never let extrapolated cells drive the regression.
- The three should approximately reconstruct the field: `IV_diff ≈ level + term·(dte−atm)/30 + skew·(otm)/10 + residual`. Report the residual RMS as a goodness-of-decomposition number.

This is the cheap, transparent cousin of the PCA. **Ship the 3-scalar decomposition first (no history needed, works on any 2 snapshots); add PCA later once ≥40 sessions exist** to confirm the level/term/skew axes are actually the empirical principal components and not just imposed structure.

---

## Daily vol report — what to lead with (signal vs noise)

Practitioner consensus (SpotGamma, MenthorQ, Trading Volatility, Volland) on lead content, mapped to what this tool already has / should add:

**Lead (signal):**
1. **Spot + 1-day expected σ** (have it) — the "how much might it move" anchor.
2. **Net GEX sign + zero-gamma level / vol trigger** (have it) — the single most-cited actionable level; dealers long-gamma (suppressive) vs short-gamma (amplifying).
3. **Front 25Δ skew + its change** (have skew; v3.3 adds change) — demand for downside protection; the *change* is the news.
4. **Term-structure state (contango/backwardation) + change** (have classification; add change) — backwardation flags near-term event risk.
5. **Surface velocity + level/term/skew decomposition** (v3.3 new) — one-line "the surface did X today."

**Context (secondary):**
- Call/put walls + distance (have it) — support/resistance from positioning.
- VRP / IV30 vs RV20 (have it) — rich/cheap framing.
- GEX percentile rank (v3.2) — is today's positioning extreme.

**Noise (de-emphasise or cut):**
- Day-over-day OI churn / vs-yesterday badges — already cut in v3.1 for good reason (daily OI roll dominates thresholds). Same hazard applies to a naive day-over-day surface diff: **a 1d ΔIV is mostly the expiry roll + quote noise; the 5d/20d horizons carry the real signal.** Lead with 5d for the surface-evolution read; show 1d but caveat it.
- Anything in the extrapolated wing region — gate behind the coverage mask.
- High-decimal precision on velocity/skew scalars — round to 0.1 pp; the data doesn't support more.

---

## Feature Dependencies

```
Coverage mask (convex hull)
    └──gates──> ΔIV field display
                    └──feeds──> 3-scalar decomposition (level/term/skew)
                                    └──aggregates──> surface velocity
                                    └──extends──> multi-horizon (1d/5d/20d)
                                    └──extends──> cross-ticker comparison

Fit residual + no-arb checks + smoothing sweep
    └──validate──> the surface itself ──gates──> ALL evolution analytics

Historical snapshots (≥40 sessions)
    └──required──> PCA of surface changes
                       └──confirms──> the level/term/skew axes are empirical
```

### Dependency Notes
- **Everything downstream requires the validation layer (Phase 8).** A decomposition or velocity on an unvalidated/over-smoothed/extrapolated surface is the exact "hand-tuned non-stationary" trap the project already retired once. This is the hard gate.
- **Coverage mask must propagate into `plot_iv_change_surface` and every scalar.** The mask is computed once from the union/intersection of both days' real quote hulls.
- **3-scalar decomposition does NOT need history** — works on any two snapshots → ship before PCA.
- **PCA needs ≥~40 daily ΔIV grids** — you're accreting them now in `surface_history.py`; until then, honest "insufficient history."
- **Multi-horizon needs the parquet store to span 20 business days** — already accumulating; nearest-available-snapshot fallback for gaps/holidays (you have `pandas_market_calendars`).

---

## MVP Definition

### Launch With (Phase 8 — Validation, blocking)
- [ ] **Coverage/extrapolation mask** — convex hull of real quotes; grey out exterior cells. Highest value/cost ratio.
- [ ] **Fit residual diagnostic** — RMSE + max residual (pp) of RBF vs input quotes.
- [ ] **Smoothing sensitivity sweep** — replaces the unjustified `1.5` magic number with a documented choice (or adopt LOOCV-selected smoothing).
- [ ] **No-arb checks** — calendar (total variance non-decreasing in T) + butterfly (variance convex in k); report PASS/FAIL + violation locations, never repair.

### Add After Validation (Phase 9 — Evolution)
- [ ] **3-scalar ΔIV decomposition** (level/term/skew) on masked grid — trigger: Phase 8 mask exists.
- [ ] **Surface velocity scalar** — trigger: decomposition exists.
- [ ] **Multi-horizon (1d/5d/20d)** — trigger: parquet spans 20 business days.
- [ ] **Cross-ticker surface-change comparison** — trigger: decomposition exists for all 3 tickers.

### Future Consideration (v3.4+ / v4.x)
- [ ] **PCA of surface changes** — defer until ≥40 sessions; confirms decomposition axes empirically.
- [ ] **SVI/SSVI parametric surface** — defer to v4.x and only if a desk consumer needs a priceable/tradable surface (Bloomberg-tier data). Not for a free-data descriptive tool.
- [ ] **LOOCV auto-tuned smoothing** — nice upgrade over a static swept value; defer unless the sweep shows instability.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Coverage/extrapolation mask | HIGH | LOW | P1 |
| Fit residual diagnostic | HIGH | LOW | P1 |
| No-arb checks (calendar + butterfly) | MEDIUM | MEDIUM | P1 |
| Smoothing sensitivity sweep | MEDIUM | LOW | P1 |
| 3-scalar ΔIV decomposition | HIGH | MEDIUM | P2 |
| Surface velocity | MEDIUM | LOW | P2 |
| Multi-horizon (1d/5d/20d) | MEDIUM | LOW | P2 |
| Cross-ticker surface-change | MEDIUM | LOW | P2 |
| PCA of surface changes | MEDIUM | HIGH | P3 |
| SVI/SSVI switch | LOW (for this tool) | HIGH | P3 / out-of-scope |

## Competitor / reference feature analysis

| Feature | SpotGamma / MenthorQ | gvol / ORATS | Our descriptive approach |
|---------|----------------------|--------------|--------------------------|
| Surface fit | proprietary, smoothed | SVI/SSVI parametric, arbitrage-free | TPS interpolation + validation layer (verify, don't calibrate) |
| Skew/curvature scalars | 25Δ skew, "vol trigger" | slope (pp per 10Δ), derivative (curvature per 10Δ) | 25Δ skew + level/term/skew ΔIV scalars (pp per 10% / per 30 DTE) |
| Surface change | heatmaps, "vol regime" | term-structure & skew time series | ΔIV decomposition + velocity + (later) PCA — descriptive only |
| Coverage honesty | rarely shown | implied by parametric fit | explicit convex-hull mask — our differentiator on honesty |

## Sources

- [Gatheral & Jacquier, Arbitrage-free SVI volatility surfaces (arXiv 1204.0646)](https://arxiv.org/pdf/1204.0646) — calendar + butterfly no-arb conditions, total-variance monotonicity, g(k)≥0 (HIGH)
- [No arbitrage global parametrization for the eSSVI surface (arXiv 2204.00312)](https://arxiv.org/pdf/2204.00312) — SSVI cross-slice no-arb (HIGH)
- [Cont & da Fonseca, Dynamics of Implied Volatility Surfaces (Quantitative Finance 2002)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=295859) — the canonical 3-factor level/slope/curvature PCA (HIGH)
- [Kobayashi, An Empirical Decomposition of Implied Volatility Surfaces (SSRN)](https://www.ssrn.com/abstract=6013774) — level / skew-vertex / curvature / wing-asymmetry decomposition (MEDIUM)
- [ORATS — Modeling the IV Surface: slope & derivative conventions](https://orats.com/blog/modeling-the-implied-volatility-surface-skewness-and-kurtosis) — slope = ΔIV per 10Δ, derivative = curvature scalar, units (MEDIUM)
- [scipy.interpolate.RBFInterpolator manual](https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.RBFInterpolator.html) — smoothing parameter semantics (HIGH)
- [rbf package LOOCV smoothing selection](https://rbf.readthedocs.io/en/stable/interpolate.html) — LOOCV / GML auto-tuning precedent (MEDIUM)
- [SpotGamma — Gamma Exposure (GEX)](https://spotgamma.com/gamma-exposure-gex/) and [MenthorQ daily report guide](https://menthorq.com/guide/free-daily-report-explained/) — daily-report lead content, vol trigger, walls (MEDIUM, practitioner)

---
*Feature research for: institutional vol-desk surface evolution & daily intelligence (descriptive)*
*Researched: 2026-05-29*

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
