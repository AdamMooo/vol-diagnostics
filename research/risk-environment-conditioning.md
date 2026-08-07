# Risk-Environment Read — Conditioning Methodology
Last updated: 2026-08-05 | Status: design note (pre-phase). Portable methodology for the planned non-directional risk-environment / regime read.

Cross-project provenance: the load-bearing lessons below were paid for in **regime-detection** and transfer directly. This note is the vol-diagnostics-specific synthesis. Keep the two in sync if either moves.

---

## What this is

A design charter for a **non-directional risk-environment read**: answering "is there too much risk in the market to justify putting on exposure right now — will this environment punish a writer" *without* any buy/sell/direction claim. Direction is the first moment (near-unforecastable in an efficient market). Risk is the second moment and higher — variance, skew, tail — which **clusters and is persistent**, hence estimable. The tool stays in the second-moment lane on purpose; that is the one lane where the statistics are on our side.

Academic license: Moreira & Muir (2017), *Volatility-Managed Portfolios* (JF) — scaling exposure down in high vol / up in low vol raises Sharpe, using **only volatility, never a directional forecast**. That is this tool's thesis, proven.

## Core frame: conditioning has a cost

"It depends on so many things" is not vagueness — it is the **definition of the problem**, and its professional name is **conditioning**. We don't want a rule (`backwardation → danger`); we want a *conditional distribution of forward risk outcomes* given today's environment.

The catch governs the whole design: **every variable conditioned on shrinks usable history** (curse of dimensionality). The tradeoff is bias–variance:
- condition on too little → base rate polluted by regimes unlike today (**biased**);
- condition on too much → base rate is a handful of lookalike days of noise (**high variance**).

The skill is finding the smallest set of axes that are nearly **sufficient** — each compressing a bundle of "it depends" into one scalar (this is *why* term-structure slope is prized: it encodes level + near-term fear + trend at once).

## Two justifications for "three axes" — keep them separate

They answer different questions and must not be conflated:

1. **Dimensionality → sets the axis COUNT.** Orthogonality research across four literature streams (via regime-detection) finds vol/risk space has only **~2–4 genuinely orthogonal axes**; everything else re-collapses onto them, especially in stress. So "three axes" is roughly the *true rank of the space*, not a sample-size compromise. A 4th axis correlated with the first three costs effective-N without adding information.
2. **Effective N → sets how finely you can BIN each axis** before a cell empties. This is a *resolution* question, not a count question.

The sample-size argument never justified "three" — the rank argument did. Lean on dimensionality for the count; use effective-N for bin granularity.

## Effective N, not analog-day count (the overlapping-observation trap)

A base rate reading "n=63 days like today, followed by forward-20d realized vol" is lying about its N. Those 63 forward windows **overlap** (consecutive windows share ~19 of 20 days), plus vol is autocorrelated in its own right. Effective independent N ≈ **history ÷ horizon**, further reduced by persistence — closer to single digits than 63. Registered in the regime-detection valuation charter as the **Stambaugh / Hodrick overlapping-observation problem**. The overlapping forward window is where a base rate quietly lies.

**Operational rule — overlap corrupts the error bar, not the point estimate:**
- The *shape* of the conditional distribution (median, quantiles) from the full overlapping sample is ~fine as a **point estimate**.
- What overlap destroys is **confidence** in it. Size the error bars with a **stationary / block bootstrap** (Politis–Romano) matched to vol's persistence; **Newey–West / HAC** is the parametric cousin once a cell is collapsed to a single statistic.
- **Credibility gate shows effective N and CI width**, not analog-day count. It will collapse faster than expected. This is the existing credibility-gating instinct pointed at the right denominator.

## Rank collapses in stress — and the collapse is itself a read

The ~3 orthogonal axes are a **calm-regime** rank. In stress, cross-axis correlation → 1 and effective rank collapses toward **one factor** ("everything is risk-off") — exactly when a writer cares most. Consequences:
- (a) Conditioning cells thin *further* in a crisis because the axes stop being independent → effective-N shrinks right as you read the tail.
- (b) The collapse itself — rising correlation *among our own axes* — is a legitimate **descriptive meta-signal** ("the tape is trading as a single factor now"). Not a new predictive axis; a measurement of the space losing rank. PCA-style rank estimated in calm windows *underestimates* this; estimate rank conditionally.

### Two convergences — opposite epistemic status (do not conflate)

"When these things all converge, the stress is real" is right, but there are **two** convergences and they mean opposite things:

- **Convergence A — axes *agree* while still independent.** Level high AND slope backwardated AND vol-of-vol rising, each pointing to risk *on its own*. This is **confirmation** — several roughly-independent reads voting together, which genuinely raises confidence.
- **Convergence B — axes *correlate*, i.e. stop being independent.** They fuse into one factor ("everything is risk-off"). This is **fragility / systemic coupling** — the "stress is real" state. Formal name: **correlation breakdown**; cleanest quantification is the **absorption ratio** (Kritzman, Li, Page & Rigobon 2011, *Principal Components as a Measure of Systemic Risk*) — the fraction of total variance captured by the top few PCs. High absorption = tightly coupled, one shock propagates everywhere, small perturbations cascade.

**The twist — the two interfere.** Once B happens, "A" becomes near-worthless as confirmation: three *correlated* axes agreeing is not three votes, it is **one vote counted three times** (effective-N again). So:
- agree **and still independent** → rare, genuinely strong;
- agree **because collapsed** → not confirmation at all; the *collapse* is the signal, the agreement is automatic.

The read must distinguish these, or it will report "they all agree!" as strong evidence at the exact moment agreement has become meaningless.

**Complementarity worth building:** the absorption/collapse meta-read lights up precisely as the Tier-1 base rates go dark (cells thin as axes fuse). Calm → lean on conditional base rates; coupling spikes → base rates thinning, but the collapse itself now carries the read. They hand off.

**Discipline caveat:** absorption/collapse is **coincident** ("stress is real *right now*"), not inherently *leading*. Shipping it as a *descriptive* "the tape has lost rank" read is clean today. Any *early-warning* claim (the AR-leads-drawdowns literature) must clear the full gauntlet (effective-N, confound, cross-market OOS) first.

## Output the distribution, never the verdict ("barometer, not switch")

HARD BOUNDARY (shared with regime-detection, where the CALM/STRESSED label was killed): ship the **shape of the payoff**, not a 🔴. The backwardation case proves why — selling premium into backwardation is **fat-tailed and bimodal: rich carry OR blow-up**; a single label throws the two-sidedness away. The dispersion *is* the "it depends." Surface components (level · percentile · drift · rarity · persistence · tail), not a collapsed state.

## Two-tier maturity split (non-compensatory)

- **Tier 1 — historically-grounded risk read.** Conditioned on the deep vol-index axes (VIX to 1990, VXN/RVX to 2009): **level, its derivative (vol-of-vol), term slope, VRP**. Real base rates.
- **Tier 2 — current-fragility overlay.** Dealer gamma (chain snapshots since ~2026-05) — **descriptive-only**, "amplifying / dampening *right now*," no historical base rate until it accrues depth.

**Rule is non-compensatory:** a shallow-history overlay must never be anchored to a base rate it hasn't earned, and its immaturity can't be offset by how mechanistically compelling it feels. No free pass for the best-founded member. Gamma is *shown, not scored*.

Constraint honored: term-structure slope siblings (VIX9D/VIX3M) are **SPY-only**; QQQ/IWM degrade gracefully.

## Mechanism-gate the axes — do not let a backtest pick them

Refuse any conditioning axis without a **written structural reason it survives being known**. Selecting variables by "which subset predicts best" is the D-10 rejection (designing around a desired conclusion). Slope earns its place because you can *say why* it bundles level + near-term fear + trend — not because it topped a horse race. Same bar on all three Tier-1 axes.

## Confound-check every conditional before trusting it

Sharpest regime-detection scar: average-return-by-state looked meaningful but was just the rate cycle; the honest metric was hedge-behavior-by-state. Apply the same to every cell.
- **Concrete test for slope:** condition slope **within level buckets** (or partial level out). If backwardation still shifts forward vol *holding level fixed*, slope carries own information; if the effect evaporates inside the buckets, slope was proxying level. A conditional statistic that hasn't ruled out its confound is not evidence yet.

## The tail is the weakest and most decision-relevant estimate

The fat right tail (e.g. "1-in-6 exceeded a 2% move") — the part that actually matters for a writer — rests on a handful of events in one market's ~2,500 sessions. Treat it as the least-trustworthy number:
- **EVT / peaks-over-threshold** — fit a Generalized Pareto to exceedances rather than counting k-of-N.
- **Cross-market pooling** — VXN/RVX and other markets (Japan/Europe) raise the effective tail sample; make out-of-sample confirmation non-negotiable (the dispersion-lead was killed in regime-detection when it didn't generalize). Never let the tail rest on four US days.

## Net architecture for vol-diagnostics

- **Tier 1 (base-rated):** level + derivative (vol-of-vol) + term slope — three axes, backed by the dimensionality argument, binned by effective-N.
- **Tier 2 (descriptive overlay):** dealer-gamma fragility — shown, not scored, no historical claim.
- **Output:** conditional **forward-risk distribution** (shape + tail), with a credibility gate that displays **effective N and CI width**, plus a **cross-axis-correlation meta-read** flagging when the space is losing rank.
- **Discipline:** mechanism-gated axis selection, confound-checked cells, EVT + cross-market pooling on the tail. No label, no direction, no hidden weighting.

Raw materials already present: `data/vol_index` (deep level), `vol/vrp_history` (carry), VIX9D/VIX3M term siblings, `gex/exposure_engine` (fragility), `monitor/ranker` (ECDF percentile, dual lookback). Missing: the derivative (vol-of-vol), the conditional forward-risk base rates with effective-N accounting, and the cross-axis-correlation meta-read.
