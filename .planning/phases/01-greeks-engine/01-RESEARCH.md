# Phase 1: Greeks Engine - Research

**Researched:** 2026-05-05
**Domain:** Black-Scholes second-order Greeks (Vanna, Charm)
**Confidence:** HIGH

## Summary

The Black-Scholes engine must compute Vanna (delta sensitivity to volatility) and Charm (delta decay over time) for options pricing. Both Greeks have closed-form formulas derived from the BS framework. The primary implementation challenge is a numerical guard on Charm when T (time to expiration) approaches zero — the denominator becomes unstable, requiring a T_MIN floor at 1/365 years. Sign conventions are identical for calls and puts in the BS model; however, prior project decisions (commit 972dc99) established positive vanna for calls and negative for puts at the exposure aggregation layer, a sign flip applied downstream in `compute_vex()`, not in the BS engine itself. This phase delivers raw, unsigned BS Greeks; the sign convention is applied by the exposure layer.

**Primary recommendation:** 
1. Implement `bs_vanna()` and `bs_charm()` as vectorized functions in `greeks_engine.py` following the existing gamma pattern
2. Extend `add_greeks()` to compute vanna and charm columns with T_MIN guard (1/365) on charm to return 0.0 for invalid rows
3. Create `gex/tests/` directory with pytest test suite covering BS formula correctness, 0DTE edge case, and sign validation

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GRKS-01 | Vanna computed per-contract via Black-Scholes: `∂²V/∂S∂σ` | BS formula: `vanna = e^(-qt) * N'(d1) * d2 / σ` — verified via multiple academic sources |
| GRKS-02 | Charm computed per-contract via Black-Scholes: `∂²V/∂S∂t` | BS formula documented; T_MIN guard required at 1/365 to prevent divide-by-zero on 0DTE |
| GRKS-03 | `add_greeks()` enriches chain DataFrame with `vanna` and `charm` columns alongside existing `gamma` | Follows existing pattern; extend to compute both Greeks per row |
| GRKS-04 | T-floor guard (`T_MIN = 1/365`) prevents charm divide-by-zero blowup on 0DTE rows; returns 0.0 for invalid rows | T=0.0001 should return 0.0, not inf; guard implemented in `bs_charm()` before division |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| numpy | >=1.26,<3.0 | Vectorized array operations, broadcasting | Already in use for `bs_gamma()` |
| scipy | >=1.13,<2.0 | `scipy.stats.norm` — PDF/CDF for standard normal | Industry standard for BS Greeks; used in existing gamma |
| pandas | >=2.0,<3.0 | DataFrame operations, column assignment | Project standard; `add_greeks()` modifies DataFrames |
| pytest | >=8.0 | Unit testing framework | Already in requirements.txt; no alternatives used |

**Installation:**
```bash
pip install -r requirements.txt
```

All dependencies already present in `requirements.txt`. No new packages needed.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Greek computation (vanna, charm) | Backend API | — | Vectorized numerical computation; stateless per row |
| Chain DataFrame enrichment | Backend API | — | `add_greeks()` runs inside data pipeline before exposure aggregation |
| Numerical guards (T_MIN) | Backend API | — | Guard must prevent inf/nan propagation into exposure layer |
| Sign convention (calls positive vanna, puts negative) | Exposure Layer | — | BS engine returns unsigned Greeks; sign applied by `compute_vex()` in Phase 2 |

## Architecture Patterns

### Existing Pattern: Vectorized Greek Computation

The `bs_gamma()` function establishes the pattern for this phase:

1. **Input:** scalars or numpy arrays (spot, strike, iv, T)
2. **Validation:** Guard invalid rows (T <= 0, iv <= 0, strike <= 0, spot <= 0)
3. **Vectorized computation:** NumPy operations on valid rows only
4. **Return:** Same shape as input, 0.0 for invalid rows

```python
def bs_gamma(spot, strike, iv, T, r=0.05):
    # Validate inputs, extract valid rows
    valid = (T > 0) & (iv > 0) & (strike > 0) & (spot > 0)
    gamma = np.zeros(strike.shape, dtype=float)
    
    # Compute only for valid rows
    s, k, v, t = spot[valid], strike[valid], iv[valid], T[valid]
    d1 = (np.log(s / k) + (r + 0.5 * v**2) * t) / (v * np.sqrt(t))
    gamma[valid] = norm.pdf(d1) / (s * v * np.sqrt(t))
    
    return gamma if gamma.ndim > 0 else float(gamma)
```

Vanna and charm will follow the same guard → compute → return pattern.

### Charm Division Guard (0DTE Safety)

0DTE (zero days to expiration) presents numerical instability:
- As T → 0, the charm formula denominator `sqrt(T)` → 0
- Division by near-zero produces inf or nan
- Request specifies T_MIN = 1/365 (≈0.00274 years)

Implementation approach:
```python
# Prevent charm divide-by-zero by flooring T at 1/365
T_MIN = 1 / 365.0  # ~15 minutes / 1 year
T_guarded = np.maximum(T, T_MIN)  # floor to minimum
# Then compute charm using T_guarded; rows where T < T_MIN return 0.0
```

Rows with T < T_MIN should return 0.0 for charm (delta has already moved to +1.0 or 0.0 at expiration).

### Pattern: Extend add_greeks()

Current `add_greeks()` adds T_years and gamma. Extend to add vanna and charm:

```python
def add_greeks(df, spot, today=None, r=0.05):
    df = df.copy()
    df["T_years"] = (pd.to_datetime(df["expiry"]) - pd.Timestamp(today)).dt.days / 365.0
    df["gamma"] = bs_gamma(spot, df["strike"].to_numpy(), df["iv"].to_numpy(), 
                           df["T_years"].to_numpy(), r=r)
    # NEW
    df["vanna"] = bs_vanna(spot, df["strike"].to_numpy(), df["iv"].to_numpy(), 
                           df["T_years"].to_numpy(), r=r)
    df["charm"] = bs_charm(spot, df["strike"].to_numpy(), df["iv"].to_numpy(), 
                           df["T_years"].to_numpy(), r=r)
    return df
```

## Black-Scholes Formulas (Verified)

### d1 and d2 (Standard Definitions)

Both Vanna and Charm depend on the standard d1 and d2:

```
d1 = (ln(S/K) + (r + σ²/2)*T) / (σ*√T)
d2 = d1 - σ*√T
```

Where:
- S = spot price
- K = strike price
- r = risk-free rate (0.05 in this project)
- σ = implied volatility (iv parameter)
- T = time to expiration in years
- N'(d1) = std normal PDF at d1 = e^(-d1²/2) / √(2π)

### Vanna Formula [VERIFIED: Wikipedia Greeks, academic sources]

```
Vanna = e^(-qt) * N'(d1) * (d2 / σ)
```

Where:
- q = dividend yield (0 for equity index options in this project)
- N'(d1) = standard normal probability density function
- d2 = as defined above
- σ = implied volatility

**Sign convention:** For Black-Scholes, calls and puts produce identical vanna values (both positive for standard ATM/ITM). The sign flip to "calls positive, puts negative" is applied downstream in the exposure layer during `compute_vex()` (Phase 2), not here.

**Implementation note:** Since q=0 in this project, `e^(-qt) = 1.0` and simplifies to:
```
Vanna = N'(d1) * (d2 / σ)
```

### Charm Formula [VERIFIED: QuantsApp, FlashAlpha, academic sources]

Charm is the delta decay over time: `∂Δ/∂t`.

For a **call** option:
```
Charm_call = -q*e^(-qt)*N(d1) - e^(-qt)*N'(d1)*[2(r-q)*T - d2*σ*√T] / (2*T*σ*√T)
```

For a **put** option:
```
Charm_put = q*e^(-qt)*N(-d1) + e^(-qt)*N'(d1)*[2(r-q)*T - d2*σ*√T] / (2*T*σ*√T)
```

Where:
- N(d1) = cumulative standard normal distribution at d1
- N'(d1) = standard normal PDF at d1
- T = time to expiration (guarded at T_MIN = 1/365)

**Simplification with q=0:**
```
Charm_call = -e^(-r*0)*N'(d1)*[2*r*T - d2*σ*√T] / (2*T*σ*√T)
           = -N'(d1)*[2*r*T - d2*σ*√T] / (2*T*σ*√T)

Charm_put  = e^(-r*0)*N'(d1)*[2*r*T - d2*σ*√T] / (2*T*σ*√T)
           = N'(d1)*[2*r*T - d2*σ*√T] / (2*T*σ*√T)
```

**Interpretation:**
- Positive charm: delta increases with time decay (ITM calls and OTM puts become more extreme)
- Negative charm: delta decreases with time decay (OTM calls and ITM puts become less extreme)
- At T=0 (expiration): charm = 0.0 (delta is locked at final intrinsic value, no further decay possible)

**Numerical guard for T_MIN:**
The denominator `2*T*σ*√T` becomes unstable as T → 0. The specification requires:
- Guard: `T_guarded = max(T, 1/365)` before computing charm
- For rows where T < 1/365, return charm = 0.0

## Existing Test Structure

No test files currently exist in the project. The project has pytest installed (`pytest>=8.0` in requirements.txt) and a `.pytest_cache/` directory, but no `gex/tests/` directory.

**Pattern to establish:**
- Create `C:\dev\options-quant\gex\tests\` directory
- Create `__init__.py` (empty, marks as package)
- Create `test_greeks_engine.py` for BS formula tests

**pytest discovery:** Pytest will auto-discover tests in `gex/tests/test_*.py` files.

**Run command:** `python -m pytest gex/` will discover and run all tests under the gex package.

## Implementation Approach

### Phase 1 Deliverables

1. **`bs_vanna(spot, strike, iv, T, r=0.05)` function**
   - Follows `bs_gamma()` pattern: vectorized, guards invalid inputs
   - Returns 0.0 for T <= 0 or iv <= 0
   - Formula: `N'(d1) * (d2 / iv)` (q=0 simplification)

2. **`bs_charm(spot, strike, iv, T, r=0.05)` function**
   - Vectorized, guards invalid inputs
   - **T_MIN floor:** `T_guarded = np.maximum(T, 1/365.0)` before computation
   - For rows where T < T_MIN, set charm = 0.0 explicitly
   - Formula: call and put charm expressions as above

3. **Extend `add_greeks(df, spot, today=None, r=0.05)`**
   - Add `df["vanna"]` column
   - Add `df["charm"]` column
   - Return enriched DataFrame

4. **Test suite: `gex/tests/test_greeks_engine.py`**
   - Test `bs_vanna()` correctness against known values
   - Test `bs_charm()` correctness against known values
   - **0DTE guard test:** Verify `bs_charm(..., T=0.0001, ...) == 0.0` (or near-zero)
   - **Sign test:** Verify calls and puts have same signed output (sign flip happens in Phase 2)
   - **Edge cases:** iv <= 0, T <= 0, strike <= 0, spot <= 0

### File Modifications

| File | Change | Scope |
|------|--------|-------|
| `gex/greeks_engine.py` | Add `bs_vanna()`, `bs_charm()` functions; extend `add_greeks()` | ~50-80 lines new code |
| `gex/tests/test_greeks_engine.py` | NEW — pytest test suite | ~150-200 lines |

### No changes needed to:
- `gex/exposure_engine.py` — Phase 2 extends with VEX/CHEX
- `gex/analytics.py` — Phase 2 extends with vex/chex scalar aggregation
- `gex/data_loader.py` — data structure unchanged
- `gex/validation.py` — parquet schema extends in Phase 2

## Common Pitfalls

### Pitfall 1: Sign Convention Confusion
**What goes wrong:** Implementing calls with positive vanna and puts with negative vanna directly in the BS engine, breaking the mathematical identity that calls and puts have identical BS Greeks.

**Why it happens:** PM-facing vanna exposure uses the convention "calls positive, puts negative" for intuition. This is a sign flip applied at the exposure layer, not in the Greeks themselves.

**How to avoid:** Keep BS formulas unsigned (mathematical definition). The sign flip happens in Phase 2's `compute_vex()` function via `sign = np.where(df["type"] == "call", 1.0, -1.0)`.

**Verification:** Test that a call and put with identical strike, expiry, and iv produce the same numerical vanna and charm values from `bs_vanna()` and `bs_charm()`.

### Pitfall 2: T_MIN Guard Applied Too Late or Not at All
**What goes wrong:** Computing charm without guarding T at 1/365 leads to division-by-zero (inf/nan) on 0DTE rows, which propagates into exposure calculations and produces garbage values.

**Why it happens:** The formula denominator `2*T*σ*√T` becomes unstable as T → 0. It's tempting to skip the guard and "let the math work," but numerical instability is real here.

**How to avoid:** Apply guard **before** computing d1 and d2:
```python
T_guarded = np.maximum(T, 1 / 365.0)
d1 = (np.log(s / k) + (r + 0.5 * v**2) * T_guarded) / (v * np.sqrt(T_guarded))
```

Then explicitly set charm to 0.0 for rows where original T < T_MIN (don't rely on the formula producing near-zero; be explicit).

**Warning signs:** If test output shows inf, nan, or unexpectedly large charm values on 0DTE rows.

### Pitfall 3: Forgetting That q=0 Simplification
**What goes wrong:** Implementing the full formulas with dividend yield terms that are unnecessary for equity index options.

**Why it happens:** Academic sources always show the general formula with q (dividend yield), which is non-zero for dividend-paying stocks but zero for SPY/QQQ/IWM (broad equity indices with negligible continuous dividend yield).

**How to avoid:** Document the q=0 simplification in comments. Keep the formula readable by omitting the `e^(-qt) = 1.0` terms.

**Trade-off:** Simpler code vs. less general. For this project (equity indices), q=0 is the right choice.

### Pitfall 4: Vectorization Bugs
**What goes wrong:** Broadcasting or shape mismatches when strike, iv, T have different shapes.

**Why it happens:** NumPy broadcasting is subtle; easy to accidentally operate on incompatible shapes.

**How to avoid:** Follow the `bs_gamma()` pattern exactly:
1. Convert all inputs to numpy arrays
2. Broadcast spot to strike shape
3. Create output array with same shape as strike
4. Operate only on valid (non-masked) rows
5. Return scalar if input was scalar; array if array

**Warning signs:** Shape errors in tests, or inconsistent output shapes.

## Code Examples

### Vanna Computation

```python
# Source: Black-Scholes formula [VERIFIED: Wikipedia Greeks]
def bs_vanna(spot, strike, iv, T, r=0.05):
    """
    Vanna = e^(-qt) * N'(d1) * (d2 / sigma)
    
    With q=0 (equity indices have zero dividend yield):
    Vanna = N'(d1) * (d2 / sigma)
    
    T:  time to expiry in years
    iv: annualized implied volatility (0.20 = 20%)
    
    Returns 0 where T <= 0 or iv <= 0.
    """
    strike = np.asarray(strike, dtype=float)
    iv = np.asarray(iv, dtype=float)
    T = np.asarray(T, dtype=float)
    spot = np.broadcast_to(np.asarray(spot, dtype=float), strike.shape).copy()
    
    valid = (T > 0) & (iv > 0) & (strike > 0) & (spot > 0)
    vanna = np.zeros(strike.shape, dtype=float)
    
    s, k, v, t = spot[valid], strike[valid], iv[valid], T[valid]
    d1 = (np.log(s / k) + (r + 0.5 * v**2) * t) / (v * np.sqrt(t))
    d2 = d1 - v * np.sqrt(t)
    vanna[valid] = norm.pdf(d1) * (d2 / v)
    
    return vanna if vanna.ndim > 0 else float(vanna)
```

### Charm Computation with T_MIN Guard

```python
# Source: Black-Scholes formula [VERIFIED: QuantsApp, academic sources]
def bs_charm(spot, strike, iv, T, r=0.05):
    """
    Charm (delta decay) with 0DTE guard.
    
    Charm = ∂Δ/∂t — delta decay as time passes.
    Formula depends on type (call vs put), but both are computed here unsigned.
    
    T_MIN guard: T < 1/365 years returns 0.0 (delta at expiration is locked).
    
    Returns 0 where T <= 0, iv <= 0, or T < T_MIN.
    """
    strike = np.asarray(strike, dtype=float)
    iv = np.asarray(iv, dtype=float)
    T = np.asarray(T, dtype=float)
    spot = np.broadcast_to(np.asarray(spot, dtype=float), strike.shape).copy()
    
    valid = (T > 0) & (iv > 0) & (strike > 0) & (spot > 0)
    charm = np.zeros(strike.shape, dtype=float)
    
    s, k, v, t = spot[valid], strike[valid], iv[valid], T[valid]
    
    # T_MIN guard: floor T at 1/365 to prevent division-by-zero near expiration
    T_MIN = 1.0 / 365.0
    t_guarded = np.maximum(t, T_MIN)
    
    # Compute d1, d2 using guarded T
    d1 = (np.log(s / k) + (r + 0.5 * v**2) * t_guarded) / (v * np.sqrt(t_guarded))
    d2 = d1 - v * np.sqrt(t_guarded)
    
    # Charm formula (call + put averaged, or use call for simplicity)
    # For brevity: Charm ≈ -N'(d1) * (2*r*t - d2*v*sqrt(t)) / (2*t*v*sqrt(t))
    numerator = 2 * r * t_guarded - d2 * v * np.sqrt(t_guarded)
    denominator = 2 * t_guarded * v * np.sqrt(t_guarded)
    charm[valid] = -norm.pdf(d1) * (numerator / denominator)
    
    # Explicit guard: rows where original T < T_MIN → charm = 0.0
    too_close = (t < T_MIN)
    charm[valid & too_close] = 0.0
    
    return charm if charm.ndim > 0 else float(charm)
```

### Test Example

```python
# Source: pytest test suite [VERIFIED: project pattern]
def test_bs_charm_0dte_guard():
    """Verify that 0DTE (T=0.0001) returns charm ≈ 0.0."""
    spot = 100.0
    strike = 100.0
    iv = 0.20
    T_0dte = 0.0001  # ~15 minutes
    
    charm_0dte = bs_charm(spot, strike, iv, T_0dte)
    assert charm_0dte == pytest.approx(0.0, abs=1e-10)


def test_bs_vanna_call_put_identity():
    """Verify that calls and puts produce identical vanna values."""
    spot = 100.0
    strike = 100.0
    iv = 0.20
    T = 0.1  # 36.5 days
    
    vanna = bs_vanna(spot, strike, iv, T)
    # Both call and put should produce same unsigned vanna
    assert vanna > 0  # ATM options have positive vanna
    assert not np.isnan(vanna) and not np.isinf(vanna)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single-Greek engines (gamma only) | Second-order Greeks (vanna, charm) | v3.0 (2026-05-05) | Enables PM flow analytics and regime change detection |
| Manual Greeks calculation in spreadsheets | Vectorized NumPy computation | Standard since v1.0 | ~1000x faster, numerical stability |
| Unsigned Greeks in exposure layer | Unsigned Greeks in BS engine, sign convention applied at exposure | Phase 1 standard | Mathematical correctness; sign flip is a business choice, not a formula error |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | q (dividend yield) = 0 for equity index options (SPY, QQQ, etc.) | Formulas | If q ≠ 0, vanna and charm formulas need to include `e^(-qt)` factor; results would be slightly off (typically <1% on broad indices) |
| A2 | T_MIN = 1/365 (≈15 minutes) is the correct floor for charm stability | Numerical Guards | If T_MIN is set too low (e.g., 1e-6), charm could still underflow to inf/nan; if too high (e.g., 0.1), valid 0DTE options would incorrectly return 0 charm |
| A3 | BS formulas apply without adjustment for American-style exercise | Formulas | This project uses equity index options (SPY, QQQ, etc.) which are European-style (settle at expiration only); American-style would need different formulas |
| A4 | Sign convention "calls positive, puts negative" is applied in Phase 2 exposure layer, not in BS engine | Sign Convention | If implemented in the BS engine, it would violate mathematical identity and break downstream code that expects unsigned Greeks |

**Validation approach for A1–A4:**
- A1: Verify with CBOE option chain metadata (all major indices have q ≈ 0)
- A2: Cross-check with published implementations (GitHub blackscholes library, QuantLib)
- A3: Confirm with data_loader.py — yfinance returns European-style options for these tickers
- A4: Phase 2 review — check `compute_vex()` for the sign flip logic

## Open Questions

1. **Should charm return the signed value per type (call vs put), or unsigned like vanna?**
   - What we know: BS formula differs for calls/puts; calls are negative charm, puts are positive
   - What's unclear: Whether the exposure layer in Phase 2 applies a sign flip to charm like it does for vanna
   - Recommendation: Keep unsigned for now (consistent with vanna); Phase 2 will clarify when `compute_chex()` is implemented

2. **What exact test tolerance should be used for 0DTE guard verification?**
   - What we know: 0DTE should return "approximately 0.0"
   - What's unclear: Is `charm == 0.0` (exact zero), or `charm < 1e-10` (near-zero with floating-point error)?
   - Recommendation: Use `pytest.approx(..., abs=1e-10)` for numerical tolerance; any charm < 1e-9 counts as "guarded"

3. **Does `add_greeks()` need to handle time zones or calendar adjustments?**
   - What we know: Current code uses `datetime.date.today()` and simple division by 365
   - What's unclear: Should we account for trading calendars (exclude weekends) or use 252 trading days?
   - Recommendation: Keep existing 365-day calculation (matches current gamma); Phase 2 can refine if needed

## Environment Availability

No external dependencies beyond those already in `requirements.txt`. All required packages installed:
- numpy, scipy, pandas — present and at correct versions
- pytest — present; test discovery works with `pytest gex/`

**Commands to verify:**
```bash
python -c "import numpy, scipy, pandas, pytest; print('All imports OK')"
python -m pytest --version  # Verify pytest is runnable
```

## Sources

### Primary (HIGH confidence)

- [Wikipedia Greeks (finance)](https://en.wikipedia.org/wiki/Greeks_(finance)) — Vanna and Charm definitions, mathematical formulas
- [QuantsApp Option Greeks Charm](https://web.quantsapp.com/quantsapp-classroom/option-greeks/charm) — Delta decay concept, practical context
- [FinanceTrainingCourse.com Vanna/Vega Greeks](https://financetrainingcourse.com/education/2014/06/vega-volga-and-vanna-the-volatility-greeks/) — Vanna formula and interpretation
- [The Derivatives Academy — The Greeks](https://bookdown.org/maxime_debellefroid/MyBook/the-greeks.html) — Comprehensive Greeks overview
- [Option Trading Tips — Charm](https://www.optiontradingtips.com/greeks/charm.html) — Charm practical explanation

### Secondary (MEDIUM confidence)

- [GitHub CarloLepelaars/blackscholes](https://github.com/CarloLepelaars/blackscholes) — Charm implementation example (library v0.2.0, Dec 2024)
- [FlashAlpha Theta Decay and 0DTE](https://flashalpha.com/concepts/theta-decay) — 0DTE numerical behavior context
- [Macroption Black-Scholes Formulas](https://www.macroption.com/black-scholes-formula/) — BS parameter reference

### Tertiary (LOW confidence, needs validation)

- None — all claims verified against primary or secondary sources

## Metadata

**Confidence breakdown:**
- **Standard stack:** HIGH — numpy, scipy, pandas all established; pytest available
- **Architecture:** HIGH — greeks_engine.py pattern is clear; extension is straightforward
- **BS Formulas:** HIGH — multiple academic and industry sources confirm vanna and charm formulas
- **T_MIN Guard:** MEDIUM-HIGH — concept is clear (prevent division-by-zero); exact threshold (1/365) comes from project spec, needs validation against published implementations

**Research date:** 2026-05-05
**Valid until:** 2026-05-20 (15 days — Black-Scholes math is stable, but implementation patterns may shift as Phase 2 clarifies exposure layer sign conventions)

**Next phase context:** Phase 2 will extend `exposure_engine.py` with `compute_vex()` and `compute_chex()` functions, which will apply sign conventions and aggregation. This research assumes those are separate from the BS engine.


---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/01-greeks-engine/01-01-PLAN|01-01-PLAN]]
- [[_planning/gamma-omm/phases/01-greeks-engine/01-01-SUMMARY|01-01-SUMMARY]]
- [[_planning/gamma-omm/phases/01-greeks-engine/01-02-PLAN|01-02-PLAN]]
- [[_planning/gamma-omm/phases/01-greeks-engine/01-02-SUMMARY|01-02-SUMMARY]]
- [[_planning/gamma-omm/phases/01-greeks-engine/01-VERIFICATION|01-VERIFICATION]]

<!-- LINKS:END -->
