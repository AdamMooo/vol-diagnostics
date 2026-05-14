# GEX Methodology Audit
Last updated: 2026-05-13

## Executive Summary

- The core GEX formula (`gamma × OI × 100 × S² × 0.01`) is the industry-standard calculation used by SpotGamma, perfiliev.com's reference implementation, FlashAlpha, and every other practitioner source. The implementation is mathematically correct.
- The dealer-positioning assumption (retail buys, dealers short) is the universal heuristic but is structurally unverifiable from OI data alone. It holds well in aggregate for SPX/SPY but breaks at individual strikes and fails for any ticker with dominant institutional, vol-seller, or covered-call flow.
- The Zero-Gamma Level sweep is the correct approach; the only material concern is a consistency issue: GEX was built on CBOE-supplied greeks, but the ZGL sweep re-derives gamma via Black-Scholes with a hardcoded rate of 5%. These two gamma surfaces will not agree exactly.
- Delta-Flow as implemented (`|GEX| / S / 0.01`) is a derived constant, not a flow. It equals net GEX in different units and adds no independent information. Its name is misleading and should be relabeled or dropped.
- An OI-weighted vol surface is a real and buildable concept. CBOE delayed data is sufficient to construct it as a cross-sectional snapshot, but it will be stale and miss intraday repricing. Go verdict: **conditional go** for a static/EOD dashboard feature; **no-go** for intraday use without a live feed.

---

## Per-Metric Findings

### 1. GEX Formula

**Formula being used:** `gamma × OI × 100 × S² × 0.01`, calls positive, puts negative.

**Is this canonical?**

Yes. This is the standard industry formula for "dollar GEX per 1% move." The derivation is:

- `gamma × OI × 100` = total dollar-delta change per $1 move in spot across all contracts at that strike (raw dollar gamma in per-$1-move terms).
- Multiplying by `S` converts to per-1% move (since 1% of S = S × 0.01, and gamma is defined per $1 so you need one factor of S).
- Multiplying by `S` again is the standard Taylor expansion term for dollar P&L of a delta-hedged book: `½ Γ (ΔS)²`. With `ΔS = 0.01S`, this gives `½ Γ × 0.0001 × S²`. Most practitioners drop the `½` (it is a scaling constant and direction is what matters), giving `Γ × 0.0001 × S² = Γ × S² × 0.01`.

The `½` omission is consistent: perfiliev.com's canonical reference implementation, SpotGamma's support documentation, and GEXboard all use the full gamma (not half), and none apply the `½` coefficient. One outlier source (jackmeson1.github.io, citing Bloomberg's OMON) uses `0.5 × Γ × OI × S²`, which is theoretically more precise for P&L but produces numbers roughly half as large. **This is a known inter-platform inconsistency.** Your implementation matches the dominant practitioner convention.

**Sign convention:** Calls +, puts − is the universal standard. It represents dealer perspective: dealers assumed short puts (negative gamma) and long calls (positive gamma) on net. Bloomberg OMON reportedly shows absolute values only, bypassing the sign entirely.

**Source quality:** perfiliev.com (reference Python implementation, widely cited); SpotGamma support articles; GEXboard documentation; jackmeson1.github.io (cross-platform conflict analysis).

**Verdict:** Formula is correct and matches the dominant industry convention. The `½` vs full-gamma ambiguity is a cosmetic scaling issue, not an error, as long as levels are interpreted internally rather than compared to other platforms' absolute numbers.

---

### 2. Dealer Positioning Assumption

**What the model assumes:** Every unit of call OI means a dealer is short that call (positive gamma to the dealer, so positive GEX). Every unit of put OI means a dealer is short that put (negative gamma to dealer, so negative GEX).

**How defensible is this?**

Defensible in aggregate for large index products; fragile at the strike level and for single names.

The assumption works because in SPX/SPY historically, the dominant flow pattern is: institutions buy puts for tail hedges, retail/funds buy calls for leverage or income strategies, and dealers are the residual counterparty. In aggregate, this produces a world where dealers are net short options. Jonsson & Nyberg (2025 empirical study) found GEX has statistically significant predictive power for subsequent SPX returns, suggesting the aggregate assumption captures real flow.

**Where it breaks:**

1. **Institutional call buying** — when institutions buy calls outright (momentum, event-driven), dealers go short call gamma, which the model correctly captures. When institutions *sell* calls (covered call programs, structured note issuance), dealers go *long* call gamma — the model assigns the wrong sign.

2. **Vol sellers / income strategies** — any strategy where the non-dealer side sells options inverts the GEX sign at that strike. Short-dated income strategies (selling strangles, writing covered calls on equity holdings) are substantial in aggregate. The model treats all OI as dealer-short, which is wrong for these contracts.

3. **Institutional hedging programs** — large pension funds buying puts directly from dealers makes dealers long puts (positive gamma from puts), not negative as the model assumes.

4. **Single-name tickers** — the retail-buys assumption is weaker for non-index underlyings. A stock with concentrated institutional flow or heavy covered-call writing will have its GEX polarity inverted at affected strikes.

5. **Crypto (documented)** — Glassnode's 2023 research on crypto GEX found the assumption entirely inverted for crypto options, where participants are net long calls speculatively. They developed a taker-flow-based approach as a replacement.

**Published critiques:** GEXboard documentation explicitly notes "holds well at the aggregate level but can break at individual strikes with unusual positioning." Glassnode directly refuted the assumption for crypto. No major published paper has formally quantified the error rate for equity single-names.

**Verdict:** Sound for SPX/SPY aggregate regime analysis. Meaningfully degraded for single-name equities. Should be flagged in dashboard as an assumption, not a fact.

---

### 3. Zero-Gamma Level

**What the model does:** Sweeps spot ±15% of current spot on a 200-point grid, recomputes total net GEX at each hypothetical spot using Black-Scholes gamma (with hardcoded r=0.05, implied vols presumably from the existing chain), finds the zero crossing, linearly interpolates to the exact level.

**Is this the standard approach?**

Yes. The sweep-and-interpolate method is exactly what perfiliev.com's canonical implementation uses:

```python
zeroCrossIdx = np.where(np.diff(np.sign(totalGamma)))[0]
zeroGamma = posStrike - ((posStrike - negStrike) * posGamma/(posGamma - negGamma))
```

SpotGamma uses the same conceptual approach. SqueezeMetrics does not publish methodology detail but describes ZGL as the price where net GEX crosses zero. The 200-point grid over ±15% is finer than necessary (crossings happen at specific strikes, not between them) but harmless.

**The consistency problem:**

GEX was built using CBOE-supplied greeks. The ZGL sweep re-derives gamma from scratch using Black-Scholes with r=0.05 and presumably mid-IV from the chain. These two gamma surfaces are not guaranteed to agree because:

- CBOE uses its own pricing models and may apply different rates, dividend assumptions, or model inputs.
- The hardcoded r=0.05 is stale when the actual risk-free rate differs materially (e.g., if the actual 3-month T-bill rate is 4.2% or 5.3%, using 5.0% introduces a small but systematic bias in gamma for longer-dated strikes).
- Gamma is relatively insensitive to the risk-free rate (rho affects delta primarily, not gamma), so the error is small in practice — likely <1% on gamma for most strikes — but it is technically inconsistent.

**The 0DTE exclusion:**

Excluding 0DTE (min_dte=1) is methodologically defensible. SpotGamma historically excluded or downweighted 0DTE because same-day options expire at zero gamma at close regardless of strike, creating noise in the ZGL calculation. However, 0DTE now constitutes a significant fraction of SPX volume (~45% on some days as of 2024). Excluding them means the ZGL reflects the overnight/multi-day book, not intraday dealer exposure. This is a documented limitation, not an error.

**Verdict:** Approach is standard. Flag the r=0.05 as a hardcode that should track the actual risk-free rate (use 3-month T-bill). The CBOE-vs-BS gamma inconsistency is low impact for ZGL but should be documented.

---

### 4. Call/Put Walls

**What the model does:** Call Wall = strike with maximum positive GEX. Put Wall = strike with maximum absolute negative GEX.

**Is this the standard definition?**

Yes, this matches SpotGamma's published definition. From SpotGamma support: the Call Wall is the strike with the highest call gamma exposure; the Put Wall is the strike with the most negative (put) gamma exposure.

**Max GEX vs max OI vs max dollar-gamma:**

- Max OI (raw contracts) ignores moneyness and Greek-weighting. An illiquid deep-OTM strike with 10,000 open contracts but gamma of 0.001 generates trivial hedging flow. Max OI is the weakest predictor of support/resistance.
- Max GEX (what the model uses) correctly weights by gamma, so near-ATM strikes dominate. This is the correct measure for dealer hedging impact.
- Max dollar-gamma (`½ Γ OI S² × contract multiplier`) is algebraically equivalent to max GEX up to a constant (the `½` and the `0.01` scaling), so the same strike wins.

**Predictive evidence:**

No peer-reviewed paper has run a rigorous back-test of call/put wall predictiveness vs. max-OI levels. Practitioner literature (SpotGamma, FlashAlpha) asserts walls hold "most days" in low-volatility regimes but are breached during catalyst events. The mechanical basis is sound (large gamma concentration forces hedging at that strike), but the predictive claim is trader lore, not established empirical finding.

The effect is strongest in the final days before expiry when gamma is highest and the gamma concentration at specific strikes is most pronounced. It weakens significantly with >5 DTE.

**Verdict:** Correct definition. Max GEX is the right metric to use. Absence of rigorous back-test evidence is a weakness in the broader practitioner framework, not specific to this implementation.

---

### 5. Delta-Flow

**What the model computes:** `|Net GEX| / S / 0.01`

**What this actually is:**

Let Net GEX = `Γ_net × OI × 100 × S² × 0.01` (in dollars per 1% move).

Then `|Net GEX| / S / 0.01 = Γ_net × OI × 100 × S² × 0.01 / S / 0.01 = Γ_net × OI × 100 × S`.

This is just Net GEX rescaled from "dollars per 1% move" back to "dollars per $1 move" — i.e., total net dollar-delta sensitivity. It is a mathematical tautology: it expresses the same quantity as Net GEX in different units. It adds no new information.

**How it relates to actual dealer delta hedge flow:**

True dealer delta hedge flow for a $1 move in spot is:

`ΔHedge = Γ_net × OI × 100 × ΔS`

This is the shares that must be bought or sold per $1 move. The formula `|GEX| / S / 0.01` gives the same number as `Γ_net × OI × 100 × S`, which is NOT the hedge flow per $1 move — it has an extra factor of S. True hedge flow per $1 move is `Γ_net × OI × 100` (just the gamma times position, no S term). The current formula overstates the per-$1 hedge flow by a factor of S (hundreds to thousands).

**Is "Delta-Flow" a recognized term?**

No published source defines `|GEX| / S / 0.01` as a standard metric called "Delta-Flow." This appears to be an ad hoc derived quantity. It is not meaningless — it is proportional to net GEX — but it is redundant and its name implies a flow rate that it does not actually measure.

**Verdict:** This metric is a rescaled version of Net GEX. If the goal was "dollars of stock dealers must trade per $1 move," the correct formula is `Γ_net × OI × 100` (without S² or 0.01 scaling). The current formula gives a number S times too large for that interpretation. Recommend either: (a) drop Delta-Flow and just show Net GEX, or (b) rename it "Net Dollar-Delta Sensitivity" and clarify it is not a flow rate.

---

### 6. IV30

**What the model does:** Pulls IV30 directly from the CBOE delayed quotes JSON payload for each ticker.

**What is IV30?**

IV30 is a 30-day constant-maturity implied volatility calculated by interpolating between the two nearest option expirations bracketing the 30-day mark, weighting each by its proximity. The methodology is analogous to the VIX calculation (which uses a strip of strikes) but applied per-ticker using the at-the-money implied vol rather than a variance-swap replication.

CBOE supplies IV30 as a pre-computed value in their quotes payload. The exact weighting and interpolation methodology used by CBOE for their delayed quote IV30 is not publicly documented in detail — it is a vendor-computed number, not a direct market observable.

**Issues:**

1. **15-minute lag:** The delayed quotes feed introduces a 15-minute staleness on all values including IV30. In quiet markets this is irrelevant. In fast-moving markets (post-announcement, FOMC, NFP), the IV30 value may reflect a pre-event implied vol while the market has already repriced. For a dashboard showing regime analysis this is acceptable; for any live trading signal, it is not.

2. **CBOE's IV30 definition is vendor-specific:** Different data providers compute 30-day constant-maturity IV differently (vol-weighted, OI-weighted, single ATM strike, strip of strikes). CBOE's computation is one convention. It is not the same number as, say, ORATS IV30 or LiveVol IV30. Cross-platform comparisons are unreliable.

3. **No dividend adjustment visible in the data source:** For single-name equities, ignoring dividends in IV computation introduces model error for high-dividend stocks. Unknown whether CBOE accounts for this.

**Verdict:** Pulling IV30 from CBOE is the correct and simplest approach given the data source. The 15-minute lag and vendor-specific definition are known limitations to document. No action needed unless intraday responsiveness becomes a requirement.

---

## OI-Weighted Vol Surface

### What would this mean?

An OI-weighted vol surface takes the grid of `(strike, expiry, IV)` points from the options chain and computes a single summary IV weighted by open interest at each point:

**OI-Weighted IV (single number):**
`IV_oi = Σ(OI_i × IV_i) / Σ(OI_i)` across all strikes and expiries (or within a maturity bucket).

**OI-Weighted Surface (per-expiry slice):**
For each expiry, compute the OI-weighted average IV across strikes to get a term-structure of OI-weighted IV.

The concept exists in practice. MenthorQ's IV×OI indicator uses this approach to identify "sticky strikes" — where high OI concentration meets high IV, indicating maximum hedging pressure. Academic PCA work on vol surfaces (Cont & da Fonseca, 2002; subsequent refinements) uses vega-weighted or OI-weighted factor loadings to describe vol surface dynamics. This is not exotic — it is a reasonable aggregation choice.

### What would it tell you that you don't already have?

- The OI-weighted IV is a market-structure-informed average IV: strikes where the most contracts are open get the most weight. This is more informative than ATM IV alone because it captures where the actual exposure concentration is.
- Per-expiry OI-weighted IV gives a term structure that is "heavier" on the strikes where dealers actually have exposure, not just the ATM strip.
- Combined with the GEX surface you already have, you could identify strikes where high GEX + high IV coincide (maximum hedging pressure and maximum volatility sensitivity together).

### Feasibility with CBOE delayed data

**What you have:** Strike, expiry, OI, IV per contract — all in the delayed CBOE payload. This is sufficient to compute OI-weighted IV at any granularity (by strike, by expiry, or aggregate).

**What you don't have:** Intraday updates. At 15-minute lag, the OI-weighted surface is a snapshot from 15 minutes ago. OI itself is an end-of-day figure — it does not change intraday in the CBOE delayed quotes (OI is settled from the prior night's clearing). IV in the delayed payload reflects mid-quote implied vols from up to 15 minutes ago.

This means:
- The OI weights are stale by one full trading day (OI settled prior night).
- The IV values are stale by up to 15 minutes.
- The combined OI-weighted surface is a quasi-static picture, not a live surface.

For a **regime analysis dashboard** (what are the key strikes and their vol profile as of this morning?), this is perfectly usable. For intraday option flow tracking, it is inadequate.

### Implementation complexity

Low. Given the existing data pipeline:

1. Filter the options chain (same filters already applied: min OI=100, IV<300%, min_dte=1).
2. For each expiry bucket, compute `sum(OI_i × IV_i) / sum(OI_i)` across strikes.
3. Plot as a term-structure curve or heatmap.

No new data source required. Estimated implementation: 30-50 lines of Python added to the existing chain processing code, plus a new chart component.

**Optional enhancement:** Weight by vega instead of OI (or OI×vega). Vega-weighting gives more weight to strikes where IV changes matter most to P&L. This is the academically preferred weighting for vol surface aggregation but requires vega from the chain (which CBOE provides in the delayed payload as a Greek).

### Go/No-Go Verdict

**Go** for a static/morning-snapshot dashboard feature showing OI-weighted IV term structure. It is a real, defensible concept, buildable with existing data, low complexity, and additive to the existing GEX analysis.

**No-go** for intraday signal or for any claim that it reflects "current" market vol — the OI staleness (prior-night settlement) makes it a delayed picture by construction. Label it clearly as "OI-weighted IV (prior-session OI)" if implemented.

---

## What We're Doing Well

1. **GEX formula is correct.** `gamma × OI × 100 × S² × 0.01` matches the dominant practitioner standard. The sign convention is correct.

2. **Zero-Gamma Level approach is standard.** The sweep-and-interpolate method is what every major GEX platform uses. The ±15% range and 200-point grid are adequate.

3. **OI filter (min 100) and IV filter (<300%) are reasonable.** The IV cap removes clearly bad quotes (deeply distorted or erroneous options). The OI minimum removes illiquid strikes with no hedging significance.

4. **0DTE exclusion is defensible.** Excluding same-day options removes noise from strikes that will expire at zero gamma in hours, which would distort the overnight/multi-day regime picture. Document it as a feature, not a gap.

5. **Using CBOE-supplied greeks for GEX computation is better than self-computing.** CBOE's greeks incorporate their own model inputs and are consistent across the chain. Rolling your own BS computation risks inconsistency with the underlying IV surface.

6. **Call/Put Wall definition (max GEX by sign) is correct.** This is more analytically sound than max OI alone.

---

## What's Shaky or Wrong

### 1. Delta-Flow is a redundant metric with a misleading name (High severity)

`|Net GEX| / S / 0.01` equals `Γ_net × OI × 100 × S` — the same quantity as Net GEX rescaled from per-1%-move to per-$1-move, times an extra factor of S. It is not a flow. "Delta-Flow" implies a rate of delta hedging activity, but the number has units of dollars and does not change unless GEX changes. A PM who asks "what does Delta-Flow 4.2B mean?" cannot be given a clean answer because the formula does not correspond to a standard financial quantity.

Fix: Either drop it, or replace with `Γ_net × OI × 100` (shares to trade per $1 spot move, the correct hedge flow formula) and rename to "Dealer Hedge Shares per $1 Move."

### 2. ZGL uses a different gamma surface than GEX (Medium severity)

GEX is computed from CBOE greeks. ZGL sweep recomputes gamma from Black-Scholes with r=0.05. These will produce slightly different gamma values, meaning the ZGL is technically computed on a surface that is inconsistent with the GEX surface it is trying to find the zero crossing of. In practice the difference is small (gamma is not highly sensitive to r), but it is a methodological inconsistency. If a PM or quant asks to audit the ZGL calculation, this will be visible.

Fix: Use CBOE-supplied gamma in the ZGL sweep rather than recomputing via BS. This means iterating over the CBOE chain at each hypothetical spot, interpolating gamma values, rather than evaluating the BS formula. Alternatively, accept the inconsistency and document it.

### 3. Hardcoded r=0.05 is stale (Low-to-medium severity)

5% was approximately correct for the 2023-2024 Fed funds rate environment. If the rate environment shifts materially (cuts to 3%, or further hikes), this introduces a systematic error into the ZGL sweep. The fix is trivial: pull the current 3-month T-bill rate from a public source (FRED API, yfinance `^IRX`) and use it dynamically.

### 4. Dealer positioning assumption is presented as fact, not assumption (Medium severity)

The dashboard presumably displays GEX as a measure of dealer positioning. This is a model assumption, not an observable fact. For SPX/SPY in normal market conditions, it is reasonable. For single-name equities with institutional flow, covered-call programs, or vol-selling strategies, it can be directionally wrong at individual strikes. Any presentation to a PM team should include a one-line caveat that GEX assumes dealers are net short all options, which may not hold for specific tickers or strikes.

### 5. OI staleness is not surfaced (Low severity)

OI in the CBOE delayed quotes reflects prior-session settlement. If the dashboard displays OI-derived metrics (GEX, walls) as intraday figures without noting that the underlying OI is 12-24 hours old, users may assume these metrics update continuously. Volume-based flow (not currently implemented) would be the live signal; OI is always a lagged positioning picture.

---

## Recommended Actions

**Priority 1 — Fix or relabel Delta-Flow**
The current formula does not measure what the name implies. Either remove it from the dashboard or replace with `Γ_net × OI × 100` and label it "Dealer Hedge Shares per $1 Move" with units in shares (not dollars). This is the only outright incorrect item.

**Priority 2 — Fix hardcoded r=0.05**
Two-line change: fetch 3-month T-bill rate from `yfinance` (`^IRX`) at startup and use it in the ZGL Black-Scholes sweep. Document the source.

**Priority 3 — Add a methodology caveat to the dashboard**
One sentence somewhere visible: "GEX assumes dealers are net short all options. This holds in aggregate for index products and may not hold for individual strikes or single-name equities with heavy institutional or income-strategy flow."

**Priority 4 — Document the OI lag explicitly**
Label OI-derived metrics with "based on prior-session OI" or similar. This sets correct expectations for anyone using the dashboard intraday.

**Priority 5 — OI-Weighted Vol Surface (optional feature)**
If the team wants an additional vol surface view: implement OI-weighted IV term structure using existing chain data. Low complexity, real analytical value, clearly label as "prior-session OI weights." Consider also offering vega-weighted IV as an alternative weighting.

**Non-issue — GEX formula, sign convention, ZGL method, call/put wall definition, IV30 source**
These are all correct and match industry practice. No changes needed.

---

## Sources

- perfiliev.com — "How to Calculate Gamma Exposure (GEX) and Zero Gamma Level" — canonical Python reference implementation with exact formula and ZGL interpolation code: https://perfiliev.com/blog/how-to-calculate-gamma-exposure-and-zero-gamma-level/
- SpotGamma support — "GEX Explained": https://support.spotgamma.com/hc/en-us/articles/15214161607827-GEX-Gamma-Exposure-Explained-What-It-Is-and-How-SpotGamma-Uses-It
- SpotGamma support — "Call Wall": https://support.spotgamma.com/hc/en-us/articles/15297391724179-Call-Wall-What-It-Is-and-How-SpotGamma-Uses-It
- GEXboard — "What is Gamma Exposure": https://gexboard.com/learn/what-is-gamma-exposure — explicit statement that sign convention "holds well at aggregate level but can break at individual strikes"
- jackmeson1.github.io — "Gamma Wall Data Conflicts: Why SpotGamma ≠ SqueezeMetrics ≠ Bloomberg" (Oct 2025) — documents ½ Γ vs full Γ discrepancy across platforms: https://jackmeson1.github.io/finance/options/2025/10/19/gamma-wall-why-models-conflict/
- Glassnode — "Introducing: Taker-Flow-Based Gamma Exposure" — critique of dealer positioning assumption for crypto, taker-flow methodology: https://insights.glassnode.com/gamma-exposure/
- FlashAlpha Research — "Dealer Positioning & GEX: A Quantitative Approach": https://flashalpha.com/articles/dealer-positioning-gex-quantitative-approach-options-flow
- Jonsson & Nyberg (2025) — "Convexity in Motion: Leveraging Gamma Exposure to Predict Equity Market Returns" — empirical GEX predictive validity study (via Harbourfront Quant substack summary): https://harbourfrontquant.substack.com/p/gamma-exposure-and-s-and-p500-return
- MenthorQ — OI × IV indicator methodology: https://menthorq.com/guide/implied-volatility-open-interest/
- CBOE Volatility Index Mathematics Methodology: https://cdn.cboe.com/resources/indices/Cboe_Volatility_Index_Mathematics_Methodology.pdf
