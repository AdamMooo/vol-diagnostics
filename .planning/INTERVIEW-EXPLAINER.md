# Vol-Diagnostics System: Interview Explainer
**Updated:** 2026-08-16  
**Audience:** PMs, engineers, interviewers learning the system

---

## 30-Second Version

"Vol-Diagnostics is a real-time options market diagnostic dashboard for a PM running covered calls and cash-secured puts. It shows whether implied volatility is cheap or rich (VRP), which way dealers are hedging (GEX), and how the vol surface is deforming under spot/vol shocks (vanna/volga). All in one dashboard; updated daily from free CBOE data."

---

## The Problem We Solve

An income-sleeve PM selling options (covered calls on SPY/QQQ/IWM, cash-secured puts) needs to know:

1. **Is IV rich or cheap right now?** (decision: size)
2. **How will dealers trade if the spot moves?** (decision: directional hedge)
3. **How stable is the vol surface?** (decision: risk management)

**Why it's hard:** Vol metrics are noisy day-to-day. You need historical context to tell if 20% IV is rich or cheap. And most free dashboards show static Greeks, not how the surface deforms.

---

## What We Show: Four Layers

### Layer 1: VRP (Vol Risk Premium) — Is IV Rich or Cheap?

**The metric:** `IV(30-day) − RV(20-day realized vol) `, ranked as a **percentile** against 10+ years of CBOE vol-index history.

**Intuition:**
- **Positive VRP** = IV > realized vol. Market is pricing extra vol. PMs sell into this.
- **Negative VRP** = IV < realized vol. Market is under-pricing vol. Options are cheap.
- **Percentile** = where does this spread sit vs history? 67th %ile = "rich" (highest 1/3). 33rd %ile = "cheap" (lowest 1/3).

**Why 10+ years?** A short window (e.g., last year) can lie. If rates were elevated all last year, "cheap relative to last year" just means "cheap relative to an already-elevated regime." 10 years includes low-vol and high-vol eras, so the percentile is honest.

**Example:** SPY 2026-08-16: VRP +3pp, 71st %ile → "Rich. Vol market is asking a premium; good day to sell."

**Academic backing:** VRP predicts realized vol (Carr & Wu 2009). We don't use it to predict returns (weak evidence), just to contextualize current pricing.

---

### Layer 2: GEX (Gamma Exposure) — How Will Dealers Trade?

**The metric:** Aggregate dealer gamma exposure from option open interest.

**Formula:** `Γ × OI × 100 × S² × 0.01` (per strike, summed across all strikes and expirations ≤90 DTE)

**Intuition:**
- **Positive GEX** = Dealers are net long gamma (stabilizers). If spot rises, they have to sell to hedge (sellers kick back, slowing rallies). Safe-ish.
- **Negative GEX** = Dealers are net short gamma (destabilizers). If spot rises, they have to buy to hedge (buyers push up, amplifying rallies). Risky.

**Why capped at 90 DTE?** Beyond 90d, positions are mostly end-investor written calls (misclassified as dealer short by the convention). The dealer-relevant gamma is front-end.

**Example:** SPY 2026-08-16: GEX −$200M → "Dealers are net short gamma. Market is levered; spot up 1% will self-amplify."

**What it means for you:** If you're short calls and GEX is negative, a spot move helps you (faster decay, vol crush). If GEX is positive, a spot move hurts you (dealers' selling pressure slows the decay).

**Academic backing:** Baltussen et al. (2021) shows gamma hedging is mechanically linked to intraday momentum. Barbon et al. (2021) quantifies the effect. Dim/Eraker/Vilkov (2023) find it's weaker in 0DTE (the most gamma-concentrated segment), a real caveat.

---

### Layer 3: Arbitrage Constraints — Is the Vol Surface Consistent?

**The problem we fixed:** RBF-fitted IV surfaces can violate three mathematical axioms:

1. **Butterfly** (∂²C/∂K² > 0): Option prices must be convex in strike. If they're not, you can buy a call spread + sell straddle for a free lunch.
2. **Calendar** (∂σ²T/∂T > 0): Total variance must increase with time. If 14-day vol is higher than 21-day vol (in variance terms), you have a calendar arbitrage.
3. **Tail stability**: Wings can't oscillate wildly beyond the data support or you're extrapolating nonsense.

**What we do:** Every daily surface is checked. If violations found, we re-fit with softer smoothing (auto-heal). If still broken, we log it.

**What you see:** Constraint audit in the logs. "✓ SURFACE CLEAN" or "✗ BUTTERFLY: 14 violations, min ρ(K) = −0.000032."

**Why it matters:** A broken surface = broken pricing. If you delta-hedge a call position using a surface that violates butterfly, your hedge is worth negative dollars. This catches data/fit quality issues early.

---

### Layer 4: Vanna/Volga — How Does the Surface Deform?

**New with Phase 1 (2026-08-16):** Second-order Greeks showing surface elasticity.

#### Vanna: ∂²C/∂S∂σ (delta-vega cross-gamma)

**Intuition:** How much delta changes when volatility shifts.
- **Typical:** Negative vanna. Higher spot → lower vol (inverse spot-vol correlation). When spot rallies, delta doesn't rise as much as it would in a flat-vol world because vol drops.
- **Signal:** Mean vanna ≈ −0.0005 to −0.001 is healthy (shows market is pricing the inverse relationship). Vanna close to 0 = market isn't pricing spot-vol link (unusual).

**What it means for you:** If you're long a call and vanna is negative, rallies hurt the call's vega less than gamma helps it (because vol drops). This is a headwind to realized gamma on the way up.

**Example:** SPY 2026-08-16: Vanna = −0.00065 → "Healthy. Market is pricing inverse spot-vol relationship."

#### Volga: ∂²C/∂σ² (vega-gamma in vol)

**Intuition:** How much vega changes when volatility shifts. Measures "vol-of-vol" pricing.
- **High volga** = market thinks volatility is volatile. Vol straddles are expensive.
- **Low volga** = market thinks volatility is stable. Vol straddles are cheap.

**What it means for you:** If you short a vol straddle when volga is high, you're on the right side. If you short when volga is low, you're fighting the market.

**Example:** SPY 2026-08-16: Volga = 0.0039 (moderate) → "Market is pricing moderate vol-of-vol. Not a screaming opportunity for a vol straddle."

#### Surface Stability Metric

**What it is:** RMS curvature of the vol surface. Detects regions where the surface is wobbly.

- **Low** (<0.08) = smooth, stable surface. Model-reliable.
- **High** (>0.08) = surface has high curvature. Could indicate bad data, illiquidity, or real wing behavior.

**What it means for you:** If stability drops suddenly, investigate. Could be a data issue (stale quotes, wide spreads) or real market stress.

---

## How It All Fits Together

### Daily Workflow

1. **Morning (async via GitHub Actions):**
   - Fetch SPY/QQQ/IWM chains from CBOE (free, delayed quotes)
   - Compute VRP (vs 10yr CBOE vol history), GEX, Greeks
   - Fit surfaces, check arbitrage constraints (soft repair if needed)
   - Compute vanna/volga grids
   - Generate HTML email + save parquet snapshots

2. **Dashboard (live, cached):**
   - Show cards: VRP (rich/cheap), IV30 (trend), Skew (25Δ)
   - Show vanna/volga metrics below momentum strip
   - Interactive 3D surface + compare + evolution
   - Positioning (OI walls, expected move)

3. **You (as PM):**
   - Skim the email or open the dashboard
   - Read: "VRP 71st %ile (rich), GEX −$200M (dealers destabilize), vanna −0.0006 (inverse spot-vol priced in)"
   - Decision: "Size down; wait for vol crush on rally or VRP normalization."

---

## Why Each Piece Matters

| Metric | Why | What it tells you |
|--------|-----|-------------------|
| **VRP %ile** | Most direct answer: is IV rich or cheap? | Sizing. High %ile = bigger positions. |
| **GEX sign** | Mechanical impact on short-gamma P&L | Hedging. Negative GEX = rallies self-amplify. |
| **GEX magnitude** | How large is the dealer impact? | Risk sizing. $500M GEX is market-moving. |
| **Vanna** | Is the market pricing spot-vol link? | Tail risk. Negative vanna = "vol drops on rallies" = head wind to your short calls. |
| **Volga** | Is vol-of-vol expensive? | Position sizing. High volga = expensive to hedge vol. |
| **Surface stability** | Is the fit reliable? | Data quality. Low stability = use wider bid-asks. |

---

## Common Misconceptions

### "GEX predicts returns."
**False.** GEX is a market structure read (dealers are short/long gamma), not a forward signal. It explains *mechanism* (gamma hedging = momentum), not *direction* (market will go up/down). Dim/Eraker/Vilkov (2023) even show GEX is a weak predictor in the 0DTE segment where gamma hedging should be strongest.

### "VRP > 0 always means sell."
**Not always.** VRP = 71st %ile + GEX positive (dealers stabilize) = you're selling into rich vol with hedging support. VRP = 71st %ile + GEX −$500M = you're selling into rich vol but dealers are destabilizing if spot moves. Different risk profile.

### "Vanna and volga are just academic fluff."
**Not at all.** Vanna tells you if your short-call decay thesis holds (does vol really drop on rallies?) and by how much. Volga tells you if vol mean-reversion is priced in. Both are tradeable.

### "The surface must be arbitrage-free."
**Correct, but with nuance.** A surface with tiny violations (e.g., ρ(K) = −0.000001) is "clean enough" in practice. We soft-repair to catch *large* violations that break hedging models. Perfect arbitrage-free surfaces (SVI, SABR) are slower to fit and not always more accurate in the wings.

---

## What You Can Explain in an Interview

### "Tell us about your vol system"
"I built a daily ops dashboard for implied vol diagnostics. It pulls free CBOE data, computes a vol risk premium (IV minus realized vol, ranked as a percentile against 10 years of history), dealer gamma exposure from open interest, and second-order Greeks (vanna/volga) to understand surface deformation.

The PM sees: is IV rich (sell) or cheap (buy), what happens to dealers' hedges if the spot moves (impacts short-gamma P&L), and whether the vol surface is stable. All in one HTML email and Streamlit dashboard.

Academic backing: VRP predicts realized vol (Carr & Wu), gamma hedging is mechanically linked to intraday momentum (Baltussen et al.), dealer positioning in index options is net-short (Gârleanu et al.). The system is descriptive only — no predictive claims."

### "What's the hardest part?"
"Fitting the vol surface accurately. The interpolation (RBF) can violate no-arbitrage axioms, which breaks downstream hedging models. We check for three constraints (butterfly, calendar, tail stability) and soft-repair by reducing smoothing if violations are found. That catches 90% of bad fits without slowing the daily run."

### "Why not just use Bloomberg?"
"Bloomberg is $25k/year, index-only, and doesn't update after close. We need daily runs for the email (weekday mornings), free data (CBOE quotes are delayed but consistent), and extensibility — we added arbitrage constraint checking and second-order Greeks ourselves. The tradeoff: CBOE data is 15-minute delayed; Bloomberg is real-time. For portfolio-level decisions (sizing), 15-minute delay is fine."

### "Why vanna and volga?"
"Vanna tells you if your thesis about vol crushing on rallies (typical for equities) is actually priced into the surface. If vanna is near zero, the market isn't pricing inverse spot-vol correlation — that's a signal. Volga tells you if vol-of-vol is expensive (vol straddles are priced in) or cheap (opportunity). Both are second-order sensitivities that don't show up in basic Greeks."

---

## Limitations (Be Honest)

1. **CBOE data is 15-min delayed.** Real-time requires Bloomberg or Refinitiv.
2. **GEX is a backward-looking mechanism read.** It doesn't predict direction, only explains flow structure.
3. **Vanna/volga are computed from the fitted surface.** If the fit is bad, so are the Greeks.
4. **No predictive claims.** The system is descriptive. Forecasting vol or returns requires separate work (regime detection, etc.).
5. **Index-only.** SPY/QQQ/IWM only. Extensible to single-name options but would need dealer-positioning data (not available free).

---

## Further Reading

- **VRP methodology:** Carr & Wu (2009). "Variance Risk Premiums." *Review of Financial Studies*.
- **Gamma hedging mechanism:** Baltussen, Da, Lammers & Martens (2021). "Hedging Demand and Market Intraday Momentum." *JFE*.
- **Dealer positioning (index options):** Gârleanu, Pedersen & Poteshman (2009). "Demand-Based Option Pricing." *RFS*.
- **Constraint checks:** Appendix in the vol-diagnostics codebase at `.planning/SURFACE-CONSTRAINTS-IMPLEMENTATION.md`.

---

## Quick Links

- **Dashboard:** https://40.233.113.63.nip.io (live, updated daily)
- **Codebase:** `/home/adam/dev/vol-diagnostics/`
- **Daily email logic:** `engine/run_daily.py`
- **Methodology deep review:** `research/methodology-deep-review.md` (peer-review audit trail)
- **Constraint details:** `.planning/ARBITRAGE-CONSTRAINTS-SUMMARY.md`
- **Phase 1 deployment:** `.planning/PHASE1_DEPLOYMENT.md`
