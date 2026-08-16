# IV Surface Arbitrage Audit Report
**Date:** 2026-08-16  
**Scope:** Vol-diagnostics engine/surface/ and engine/gex/ modules  
**Status:** CRITICAL — Three axioms of market microstructure under risk

---

## Executive Summary

The current IV surface fitting engine uses **Thin-Plate Spline (TPS) RBF interpolation** to construct a smooth 2D surface across (DTE, log-moneyness) space. While this produces visually coherent surfaces and fits observed quotes well in-sample, **it enforces zero explicit constraints on the three fundamental arbitrage-free axioms**:

1. **Vertical (Butterfly) Arbitrage:** ∂²C/∂K² > 0 (option price convexity)
2. **Horizontal (Calendar) Arbitrage:** ∂(σ²·t)/∂t > 0 (total variance must increase with time)
3. **Tail Stability:** Extreme strikes must not diverge; outer wings must remain economically bounded

**Impact:** A noisy quote set, quotes with bid-ask crossing, or even innocent outliers can cause the fitted surface to **generate negative risk-neutral PDFs, violate call-spread parity, or predict cheaper long-dated vol than short-dated at a given strike**. These are not theoretical; they are tradeable violations that expose the model to arbitrage losses.

---

## Part 1: Current Implementation Analysis

### 1.1 RBF Configuration
**Location:** `engine/surface/surface_interactive.py:29–34` and `engine/gex/analytics.py:117–144`

```python
def _fit_rbf(dte_v, log_m, iv_v, smoothing):
    pts = np.column_stack([dte_v, log_m])
    std = pts.std(axis=0)
    std[std < 1e-6] = 1.0
    rbf = RBFInterpolator(pts / std, iv_v, kernel="thin_plate_spline", smoothing=smoothing)
    return rbf, std
```

**Facts:**
- **Kernel:** Thin-plate spline: φ(r) = r² ln(r)
- **Smoothing:** config.SURFACE_SMOOTHING = 1.5 (or SURFACE_INTERACTIVE_SMOOTHING = 0.5 for the dashboard)
- **Normalization:** Point data scaled by per-axis std before fitting (affine-invariant but not axis-aligned)
- **Clipping:** Post-fit IV clipped to [0, ∞) at line 87 and 144

**Why This Is Risky:**

1. **TPS is a **natural spline** — it minimizes bending energy globally but makes NO LOCAL guarantees on curvature sign.** A smooth function with positive second derivative in one region can absolutely have negative second derivative in another. The RBF can wiggle.

2. **Smoothing reduces overfitting but does NOT encode financial constraints.** The smoothing parameter λ trades MSE against bending energy — it is purely statistical, not economic. A noisy wing with one outlier quote will still pull the spline upward locally.

3. **Coordinate scaling (std-normalization) is necessary for numerical stability**, but it **rescales derivatives**. A fitted ∂²IV/∂K² in the scaled space will map back to a different second derivative in the original K-space. This must be inverted before checking convexity.

4. **Cubic clipping at 0** creates a **discontinuity in the first derivative** where IV sits exactly at 0.00. If the RBF predicted a slightly negative IV, clipping it to 0 introduces a kink. Far from the origin, this matters less, but in the body of the surface it can violate smoothness assumptions.

---

### 1.2 Coverage Masking (Convex Hull)
**Location:** `engine/gex/analytics.py:147–183`

```python
def coverage_mask(surface_df, spot, dte_grid, otm_grid, *, dte_floor=5, clip=None):
    # ... compute convex hull of real quotes ...
    hull = Delaunay(pts / pts_std)
    return (hull.find_simplex(grid_norm) >= 0).reshape(DTE.shape)
```

**What it does right:**
- Honest: only interpolates, never extrapolates beyond the convex hull of real quotes.
- Prevents wild tail divergence by masking unsupported cells as NaN.

**What it does wrong:**
- **Creates holes in the outer DTE/wing corners** where the surface is sparsest and arguably most economically sensitive (extreme strikes, long-dated).
- **Prevents any modeling of the skew tail structure** — the most volatile and directional part of the surface.
- **Holes propagate into downstream analytics:** surface-evolution scalars, email reports, dashboard visualizations all show "no data" where traders most care about tail risk.

---

### 1.3 Arbitrage Violation Scenarios

#### Scenario A: Negative Probability Density (Butterfly Arbitrage)

**How it happens:**
1. Market quotes a wing with a few wide bids/asks (typical for far-OTM SPY puts, QQQ calls).
2. RBF fits smoothly through these noisy quotes.
3. Locally, the fit overshoots/undershoots → creates a concave dip in the option-price space.
4. The implied probability density ρ(K) = ∂²C/∂K² becomes negative over some strike range.

**Economic consequence:**
- A trader can buy a butterfly spread (buy K₁ and K₃, sell 2×K₂) and lock in a profit *ex-post* if the market corrects the surface.
- The surface predicts a calendar arbitrage: the option price curve is not convex.

**Current mitigation:** None. The audit must check whether ∂²C/∂K² stays positive.

#### Scenario B: Calendar Arbitrage (Variance Not Monotonic)

**How it happens:**
1. Front-month expirations (7-30 DTE) often show elevated wings due to gamma flow and hedging.
2. Longer-dated (90+ DTE) wings are smoother, lower absolute IV.
3. The RBF fits both layers independently → can create a region where longer-dated *total variance* σ²·t is **lower** than shorter-dated at the same strike.

**Economic consequence:**
- A trader can sell a long-dated call and buy a short-dated call, locking in a profit.
- The market is internally inconsistent: it predicts the market will calm down and then heat up again.

**Current mitigation:** None. The audit must check whether ∂(σ²·t)/∂t > 0 at all (K, t) pairs.

#### Scenario C: Tail Blowup (Unbounded Wing Divergence)

**How it happens:**
1. Convex hull ends at the most extreme quotes (e.g., K/S = 0.80 on SPY puts).
2. Beyond that, the mask sets cells to NaN.
3. Users see "no surface" at the tail → can't model tail risk, can't compare days.

**Economic consequence:**
- Loss of visual and quantitative insight into the most directional part of the surface.
- Inability to track structural changes in tail skew without manually hunting for outlier quotes.

**Current mitigation:** Coverage masking (convex hull). This is honest but expensive in terms of user experience and downstream analytics.

---

## Part 2: Identified Constraint Violation Points

### Point 1: RBF Surface Curvature
**File:** `engine/gex/analytics.py:139–144`  
**Issue:** No check on ∂²IV/∂K² or ∂²C/∂K² at grid points.

```python
IV = rbf(grid_pts / pts_std).reshape(DTE.shape)
return np.clip(IV, 0.0, None)  # ← Only clipping lower bound; no convexity check
```

**Risk Level:** **HIGH** — Grid curvature can be negative locally; not detected.

---

### Point 2: Term Structure Monotonicity
**File:** `engine/surface/surface_evolution.py:305–318`  
**Issue:** No enforcement of ∂(σ²·t)/∂t > 0 during baseline stacking or diff computation.

```python
IV_baseline_mean = np.nanmean(IV_baseline_stack, axis=0)  # (30, 40)
IV_diff = IV_today - IV_baseline_mean
```

**Risk Level:** **MEDIUM** — Baseline averaging can smooth away calendar structure; not explicitly validated.

---

### Point 3: Surface Interpolation Boundary Behavior
**File:** `engine/surface/surface_interactive.py:84–88`  
**Issue:** RBF can extrapolate beyond the convex hull's support before masking applies.

```python
IV = np.clip(rbf(np.column_stack([DTE.ravel(), OTM.ravel()]) / std).reshape(DTE.shape), 0.0, None)
mask = coverage_mask(d_fit, spot, dte_grid, otm_grid, dte_floor=fit_floor, clip=clip)
IV = np.where(mask, IV, np.nan)  # ← Only masked AFTER clipping
```

**Risk Level:** **MEDIUM** — RBF can produce large negative IVs in the tails, then clipped to 0, creating discontinuities in masked regions.

---

### Point 4: Wing Tail Behavior
**File:** `engine/gex/analytics.py:143–144`  
**Issue:** No explicit tail parameterization; relying on convex hull for boundary control.

```python
return np.clip(IV, 0.0, None)
```

**Risk Level:** **MEDIUM** — Tail skew structure is lost beyond the convex hull; cannot model or track it.

---

## Part 3: Missing Diagnostics

The current codebase computes:
- Fit RMSE (residual error)
- Coverage percentage (hull support area)

But does **NOT** compute:
- **Butterfly arbitrage metric:** min(∂²C/∂K²) across the grid (should be > 0)
- **Calendar arbitrage metric:** min(∂(σ²·t)/∂t) across the grid (should be > 0)
- **Tail stability metric:** wing IV gradient and curvature at the boundary
- **Density histogram:** estimated risk-neutral PDF to visually check for negative regions

---

## Summary of Violations

| Axiom | Current Status | Risk | Detection |
|-------|---|---|---|
| **Butterfly (∂²C/∂K² > 0)** | Not enforced; not detected | HIGH | Requires numerical second derivatives |
| **Calendar (∂(σ²·t)/∂t > 0)** | Not enforced; not detected | MEDIUM | Requires term structure audit per strike |
| **Tail Stability** | Convex hull masking (lossy) | MEDIUM | Requires tail parameterization or wing audit |

---

## Recommendation

**Implement a three-layer constraint system:**

1. **Layer 1 (Strict):** Add post-fit diagnostics to detect violations and **flag surfaces as unsafe**.
2. **Layer 2 (Soft):** Wrap the RBF with a constraint checker that iteratively softens smoothing or re-weights outliers if violations detected.
3. **Layer 3 (Structural):** Offer an optional SVI or piecewise-linear wing fitting mode to guarantee tail stability and monotonicity by construction.

The goal: **preserve the interactive dashboard's speed and visual quality while guaranteeing that every published surface is arbitrage-free by construction.**

---

**Next:** Implementation of strict constraint checks and optional SVI/linear wing fallback.
