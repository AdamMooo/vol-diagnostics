# GEX Methodology — Deep Literature Review
Last updated: 2026-05-13

---

## Per-Metric Academic Evidence

---

### 1. GEX Formula — Mathematical Derivation

**Verdict: Not in academic literature as a named construct; derivable from first principles in standard texts**

The formula `Γ × OI × 100 × S² × 0.01` does not appear, by that name or in that exact form, in any peer-reviewed finance journal, SSRN working paper, or major options textbook (Gatheral *The Volatility Surface*, Bergomi *Stochastic Volatility Modeling*, Carr & Madan). The formula is a practitioner construction, and its lineage traces through SpotGamma's public methodology documentation and Perfiliev's 2021 blog post, not an academic derivation.

**The derivation is nonetheless mathematically clean and can be reconstructed from standard results:**

The Black-Scholes gamma of a single option contract is `∂²C/∂S²`. For a portfolio of `OI × 100` shares underlying one contract, the dollar P&L of the delta-hedge from a $1 move in `S` is `Γ × OI × 100`. To express this in dollars-per-1%-move rather than dollars-per-$1-move, multiply by `S × 0.01` (since a 1% move equals `0.01 × S` dollars). That gives `Γ × OI × 100 × S × 0.01`. The extra factor of `S` in the standard formula (making it `S²`) arises because practitioners define gamma in units of `∂²C/∂S²` (dimensionless delta-per-dollar), so the full dollar-gamma — the change in dollar delta per 1% move — is:

```
Dollar GEX per 1% = Γ × OI × 100 × (0.01 × S) × S
                  = Γ × OI × 100 × S² × 0.01
```

This is the "dollar gamma" concept, which *does* appear in academic work under other names. Gatheral (2006) uses the "dollar gamma" `½ Γ S²` as the relevant quantity in continuous P&L decomposition (the dP&L = ½ Γ (dS)² term). Bergomi (2016) defines the dollar gamma similarly in his exposition of the P&L of a delta-hedged option. The aggregation over OI and the 0.01 normalization are practitioner conventions layered on top of these standard definitions — defensible but not themselves peer-reviewed.

**What the texts actually say:** Gatheral's *The Volatility Surface* (2006) identifies `Γ S²` as the key quantity governing P&L of a delta-hedged option under stochastic volatility. Bergomi's *Stochastic Volatility Modeling* (2016) defines dollar gamma in the same way in Chapter 1. Neither aggregates over open interest in the manner GEX does.

**Implication for the dashboard:** The formula is mathematically defensible but the dashboard cannot cite a peer-reviewed derivation. The appropriate citation is "consistent with the dollar gamma concept in Gatheral (2006), applied to aggregate open interest." The `0.01` normalisation is a reporting convention; it does not affect the sign or relative magnitudes of GEX across strikes.

---

### 2. GEX Predictive Power — Backtests

**Verdict: Moderate — emerging academic support for vol-predictive and return-predictive power, effect sizes modest and regime-dependent**

#### Jonsson & Nyberg (2025)

The most directly on-point paper. Available at Linköping University's DiVA portal (diva2:1972044); no SSRN number has been assigned as of this writing — it is a master's thesis, not a peer-reviewed journal article. Title: "Convexity in Motion: Leveraging Gamma Exposure to Predict Equity Market Returns and Improve Predictive Modeling."

- **Data:** Daily S&P 500, 2011–2025 (approximately 14 years)
- **Model:** ARDL (Autoregressive Distributed Lag), with GEX as a distributed lag predictor of index returns
- **Main result:** Changes in GEX are statistically significantly and positively associated with subsequent S&P 500 returns across multiple short horizons. Including GEX improves out-of-sample forecast accuracy versus GEX-excluding ARDL and random walk benchmarks (evaluated with Diebold-Mariano tests).
- **Caveat:** Results are "somewhat diminished in strength" in the post-2020 subsample. Effect sizes and exact p-values are not reported in the abstract or the secondary coverage reviewed here.
- **Interpretation for the dashboard:** Directional support, but it is a thesis, not a refereed paper. Weight accordingly.

#### Soebhag (2023) — *Journal of Empirical Finance*

"Option Gamma and Stock Returns." Published in *Journal of Empirical Finance*, Vol. 74, 2023. DOI: 10.1016/j.jempfin.2023.101269. SSRN: 4256259.

- **Data:** Cross-section of US individual stocks with listed options
- **Methodology:** Portfolio sorts on net gamma exposure at the individual stock level; Fama-MacBeth cross-sectional regressions
- **Main result:** Stocks with **high** net gamma exposure systematically **underperform** stocks with **low** net gamma exposure. High-net-gamma stocks also negatively predict future realized volatility. The effect is distinct from standard return predictors and survives factor-model adjustment.
- **Mechanism:** Non-informational (flow-based), not private information. Interpreted as a risk premium: low-net-gamma stocks are riskier, and investors require compensation.
- **Implication:** At the individual stock level, net gamma exposure predicts the cross-section of returns. This is complementary to (not identical to) the index-level GEX concept the dashboard uses.

#### Baltussen, Da, Lammers & Martens (2021) — *Journal of Financial Economics*

"Hedging Demand and Market Intraday Momentum." *Journal of Financial Economics*, Vol. 142, Issue 1, pp. 377–403, October 2021. DOI: 10.1016/j.jfineco.2021.05.002. SSRN: 3760365.

- **Data:** 60+ futures on equities, bonds, commodities, and currencies, 1974–2020
- **Main result:** The return in the last 30 minutes before the close is statistically and economically significantly predicted by the return earlier in the day. This intraday momentum is linked mechanically to gamma hedging demand from options market makers and leveraged ETFs.
- **Mechanism:** Short gamma hedging requires trading in the direction of price movement, creating momentum. This is the core mechanism underlying the stabilizing/destabilizing framing of GEX.
- **Implication for the dashboard:** This is probably the strongest peer-reviewed paper supporting the behavioral claim that underlies GEX. It does not test GEX as a specific metric, but it validates the mechanism.

#### Barbon, Beckmeyer, Buraschi & Moerke (2021) — SSRN 3925725

"Liquidity Provision to Leveraged ETFs and Equity Options Rebalancing Flows: Evidence from End-of-Day Stock Prices."

- **Main result:** A one-standard-deviation increase in options gamma imbalance (equivalent to net GEX exposure) depresses end-of-day returns by approximately 113% of the average return in the final 30 minutes. Leveraged ETF rebalancing flows increase end-of-day returns by 430% of average.
- **Mechanism:** Delta-hedging can have a *stabilizing* (reversal) or *destabilizing* (momentum-amplifying) effect depending on sign of dealer gamma, consistent with the GEX positive/negative framing.
- **Implication:** The largest quantified effect size in the literature for options-hedging-flow price impact — in the final 30 minutes, the effect is economically very large.

**What the literature does not yet show:** A direct OOS backtest of a daily trading strategy using GEX as the sole signal, with Sharpe ratio, max drawdown, and benchmark-adjusted returns reported in a peer-reviewed journal. The Jonsson & Nyberg paper is the closest but remains a thesis.

---

### 3. Dealer Positioning Assumption

**Verdict: Moderate — the "dealers are net short options" claim is empirically supported for index puts and in aggregate for equity options, but with important nuances**

The GEX framework treats open interest as dealer-short by convention (dealers sell options to end-users). Three bodies of evidence address this:

#### Garleanu, Pedersen & Poteshman (2009) — *Review of Financial Studies*

"Demand-Based Option Pricing." *Review of Financial Studies*, Vol. 22, Issue 10, pp. 4259–4299, October 2009. DOI: 10.1093/rfs/hhp005. SSRN: 1479109.

- **Data:** Proprietary CBOE dataset identifying aggregate positions of dealers and end-users
- **Main result:** End-users are **net long** index options, especially out-of-the-money puts. Dealers are correspondingly **net short**, consistent with GEX's signed convention for index products. This is one of the most direct empirical confirmations of the convention.
- **Caveat:** The dataset is from the early 2000s. The rise of retail options activity and 0DTE volume since 2020 may have altered the composition of the "end-user" side.

#### Hu, Kirilova, Muravyev & Ryu (2023) — SSRN 4633451

"Options Market Makers." Available on SSRN (October 2023).

- **Data:** Account-level data for KOSPI 200 index options, identifying 43 options market makers
- **Main result:** Only **4 of 43 market makers** continuously delta-hedge. The majority manage risk through rapid inventory rebalancing — buying and selling options to close positions — rather than delta-hedging the underlying. This is a significant caveat for GEX: the mechanism (dealers hedge by trading the underlying) applies only to the minority of market makers who actually delta-hedge.
- **Implication:** The GEX mechanism is directionally correct but quantitatively uncertain. Aggregate delta-hedging demand from dealers may be smaller than GEX implies if most market makers net their books rather than hedge.

#### Anderegg, Ulmann & Sornette (2022) — *Journal of International Money and Finance*

"The Impact of Option Hedging on the Spot Market Volatility." *Journal of International Money and Finance*, Vol. 124, 2022. DOI: 10.1016/j.jimonfin.2022.102627.

- **Data:** DTCC trade repository data for EURUSD and USDJPY FX options, October 2017 – June 2018
- **Main result:** Reconstructed dealer gamma exposure is **negative** (dealers net short) in both currency pairs during the sample period. A negative gamma exposure of approximately −$1 trillion leads to volatility increases of 0.7% in EURUSD and 0.9% in USDJPY.
- **Implication:** This is direct regulatory trade-repository evidence of net-short dealer positioning — not an assumption. The FX context is not identical to equities, but the structural dynamic is comparable.

#### Glassnode / Taker-Flow Alternative (2023)

Glassnode published a methodology paper introducing taker-flow-based GEX for crypto options (Deribit data). Their key finding is that in crypto markets, the OI-based assumption (dealers are short) breaks down because retail traders are often *buyers* of calls, and taker-flow analysis is needed to determine actual dealer direction. This methodological paper is not peer-reviewed but is technically rigorous and highlights a known limitation of the OI-sign convention that may be relevant to any equity-market extension.

**Net assessment:** The dealer-short-index-put assumption is empirically well-grounded (Garleanu et al. 2009, Anderegg et al. 2022). The GEX sign convention for puts (positive from short put = positive gamma for dealer) is consistent with the empirical record. The largest caveat is that not all market makers delta-hedge (Hu et al. 2023), which attenuates but does not eliminate the mechanism.

---

### 4. Zero-Gamma Level

**Verdict: Weak as a named construct — the concept is not directly tested in academic literature; adjacent pinning and clustering evidence is solid**

No academic paper explicitly tests "Zero-Gamma Level" or "gamma flip" as a price predictor. The concept is entirely practitioner-originated (SpotGamma's public methodology). However, three related bodies of academic evidence lend partial indirect support:

#### Ni, Pearson & Poteshman (2005) — *Journal of Financial Economics*

"Stock Price Clustering on Option Expiration Dates." *Journal of Financial Economics*, Vol. 78, Issue 1, pp. 49–87, October 2005. DOI: 10.1016/j.jfineco.2005.01.001. SSRN: 519044.

- **Data:** Optionable US stocks, 1996–2002
- **Main result:** On expiration dates, closing prices of optionable stocks cluster at option strike prices. Returns of optionable stocks are altered by an average of **at least 16.5 basis points** on each expiration date, translating to aggregate market capitalization shifts on the order of **$9 billion**.
- **Mechanism:** Delta-hedging by options market makers at strikes where net purchased positions are large drives prices toward those strikes. This is the "pinning" phenomenon: large open interest at a strike generates hedging flows that pin the underlying to that strike.
- **Implication for ZGL:** Pinning is not the ZGL concept directly, but it is the same underlying mechanism. Large OI strike concentration creates hedging-flow gravity wells. The ZGL represents the level where cumulative dealer gamma changes sign — a structurally analogous idea.

#### Buis, Pieterse-Bloem, Verschoor & Zwinkels (2024) — *Journal of Economic Dynamics and Control*

"Gamma Positioning and Market Quality." *Journal of Economic Dynamics and Control*, Vol. 164, July 2024. DOI: 10.1016/j.jedc.2024.104881. SSRN: 4109301.

- **Methodology:** Zero-intelligence market simulation with dynamic hedgers; theoretical analysis
- **Main result:** Positive net gamma positioning reduces volatility and increases market stability (mean-reverting regime). Negative net gamma increases volatility and makes markets more prone to failure (trend-following regime).
- **Implication for ZGL:** This is the cleanest academic support for the regime-change framing of ZGL. The paper validates the qualitative claim that crossing from positive to negative aggregate gamma changes the character of price action, even if it does not test the ZGL as a specific numerical level.

#### Baltussen et al. (2021) (see §2)

The intraday momentum mechanism implies that in negative-GEX regimes, directional moves accelerate into the close — consistent with the "below ZGL = trending/volatile" framing.

**What is absent:** No paper tests whether the specific price level at which cumulative GEX crosses zero functions as quantifiable support/resistance, produces statistically significant reversal or continuation, or predicts subsequent realized volatility with a tested threshold. The ZGL is an intuitively well-motivated construct, but its predictive validity as a numerical price level has not been peer-reviewed.

---

### 5. Hedge Shares/$1 (Dealer Delta Flow)

**Verdict: Moderate — the quantity is implicitly used throughout the delta-hedging price-impact literature; no paper defines it as "Hedge Shares/$1" but several measure its empirical effects**

The quantity `Γ_net × OI × 100` (shares dealers trade per $1 spot move) is the first derivative of the aggregate dealer delta hedge position with respect to S. This is exactly the "delta hedge demand" that price-impact models use. The literature addresses it from several angles:

#### Egebjerg & Kokholm (2024) — SSRN 4936978

"A Model for the Hedging Impact of Option Market Makers." Available on SSRN (2024).

- **Data:** High-frequency SPX option trade data
- **Main result:** Changes to the net option position of OMMs are closely linked to subsequent SPX futures returns. The model decomposes the price impact into a **gamma effect** (from existing inventory requiring rebalancing as S moves) and an **inventory effect** (from new trades changing the OMM's position). Both components are statistically significant. The gamma effect is quantitatively the larger of the two on most days.
- **Implication:** This is the most direct paper validating that `Γ_net × ΔS` is a real, measurable quantity driving futures returns. The "Hedge Shares/$1" metric corresponds to their gamma effect component.

#### Baltussen et al. (2021) (see §2)

The paper's mechanism is precisely the aggregate gamma-weighted hedge demand driving intraday prices. The economic magnitude is tested via futures return attribution.

#### O'Donovan, Yu & Zhang (2023) — SSRN 4567604

"Option Market Maker Hedging and Stock Market Liquidity."

- **Main result:** When option market makers hold a net short position, their dynamic hedging demands liquidity from the underlying, leading to market destabilization. The effect is stronger for stocks with limited liquidity supply. The authors document this using proprietary exchange data classifying traders by type.
- **Implication:** The Hedge Shares/$1 concept is correct in sign and direction. The paper additionally shows that it interacts with underlying stock liquidity — a nuance not captured by a scalar per-$1 metric.

#### Figlewski (1989) — *Journal of Finance* (historical baseline)

"Options Arbitrage in Imperfect Markets." *Journal of Finance*, Vol. 44, Issue 5, pp. 1289–1311, 1989. DOI: 10.1111/j.1540-6261.1989.tb02654.x.

- **Main result:** Simulated delta-hedge rebalancing under real market conditions shows large hedging errors due to transaction costs, discrete rebalancing, and uncertain volatility. This is the foundational paper on why aggregate dealer hedging flows are noisy rather than mechanically precise.
- **Implication:** A caveat for the Hedge Shares/$1 metric: real-world hedging is discrete and transaction-cost-constrained. The actual shares traded per $1 move will differ from `Γ_net × OI × 100` by a noise term that grows with transaction costs and rebalancing frequency.

**Key limitation not addressed by any paper:** The Hedge Shares/$1 metric sums gamma across all expirations, treating near-dated and far-dated options symmetrically. Near-dated gamma is more reliably hedged more frequently; far-dated gamma is often hedged less aggressively or vega-hedged rather than delta-hedged. No paper directly tests whether expiry-weighted gamma produces a better measure of realized hedging demand.

---

### 6. OI-Weighted Implied Volatility Surface

**Verdict: Moderate — OI-weighting has academic support as part of a combined OI-and-vega factor; pure OI-weighting vs. pure vega-weighting is not directly compared in a definitive study**

#### Cont & Da Fonseca (2002) — *Quantitative Finance*

"Dynamics of Implied Volatility Surfaces." *Quantitative Finance*, Vol. 2, Issue 1, pp. 45–60, 2002. DOI: 10.1088/1469-7688/2/1/304. SSRN: 295859.

- **Data:** Time series of option prices on S&P 500 and FTSE 100 indices
- **Methodology:** Karhunen-Loève decomposition (functional PCA) of daily changes in implied volatility across strikes and maturities
- **Main result:** The implied volatility surface can be described by **three orthogonal random factors**:
  - **Factor 1 (level):** A parallel shift of all implied volatilities — the dominant factor
  - **Factor 2 (slope):** A tilt of the surface along the moneyness dimension — the skew factor
  - **Factor 3 (curvature):** A "smile" deformation — bowing of the surface across strikes
- **Weighting used:** Karhunen-Loève decomposition is unweighted in the original paper (all strikes and maturities enter equally in the functional sense). OI or vega weighting is not used.
- **Implication:** The three-factor level/slope/curvature structure is the standard reference. The dashboard's OI-weighted per-expiry average collapses all three factors into a scalar, which loses the cross-strike information that defines factors 2 and 3.

#### Avellaneda et al. (2020) — *Journal of Financial Data Science* / arXiv 2002.00085

"PCA for Implied Volatility Surfaces." *Journal of Financial Data Science*, Vol. 2, Issue 2, 2020. arXiv: 2002.00085.

- **Data:** Implied volatilities for approximately 500 S&P 500 constituents, 56 strike-expiry combinations each, 2012–2017
- **Methodology:** Standard PCA applied to the tensor of individual-stock implied volatility surfaces
- **Main result:** The **market factor** (first PC) corresponds to a compounding of a weighted average of implied-volatility returns, where weights are proportional to each option's **open interest × vega** (combined). The paper shows that a pure OI-and-vega-weighted IV index is one of at least two significant factors in this cross-sectional implied volatility market.
- **Implication:** This is the strongest academic support for OI-weighting in IV construction. The paper specifically argues that OI-vega combined weights outperform either alone because OI captures economic significance while vega captures price sensitivity. A pure OI-weighted average (ignoring vega) is defensible but slightly suboptimal relative to this benchmark.

#### What the literature does not resolve

There is no head-to-head comparison of pure OI-weighting vs. pure vega-weighting vs. combined OI×vega-weighting for the specific purpose of constructing a per-expiry IV metric. The practitioner standard is vega-weighted (because it down-weights deep OTM options whose IV is noisy), but Avellaneda et al. suggest OI×vega is more economically meaningful. The dashboard's current OI-weighted approach is closer to the Avellaneda et al. recommendation than to the pure-vega convention — a reasonable choice, but not the textbook standard.

---

### 7. What the Literature Says We're Missing

**Top recommendation: Vanna exposure (`∂Δ/∂σ × OI`), with meaningful academic support for its independent predictive content beyond GEX**

#### (a) Vanna Exposure

Vanna is `∂²C/∂S∂σ = ∂Δ/∂σ` — the sensitivity of dealer delta to changes in implied volatility. When IV moves, dealers holding vanna exposure must rebalance their delta hedges in response to the vol move, not just the price move. This creates a distinct channel of hedging flow.

**DeLorenzo (2023) — SSRN 4669282**

"Impact of Option Dealer Flows on Equity Returns." SSRN: 4669282. December 2023. (Also available at vol.land/VollandWhitePaper.pdf.)

- **Data:** Proprietary Volland option dealer positioning data, daily and intraday
- **Main result:** Option dealers are **predominantly more sensitive to changes in implied volatility than to movements in the underlying equity.** This implies that the vanna channel — delta rebalancing forced by IV moves — is empirically larger than the gamma channel on many days. The paper additionally finds that 0DTE charm hedging has significant and persistent pattern-generating effects in the 0DTE context.
- **Caveat:** Volland's methodology for dealer positioning inference is proprietary and not independently validated. This is a working paper, not peer-reviewed.

The mechanism is theoretically sound: when the VIX moves significantly, the aggregate dealer delta position shifts by `Vanna_net × ΔIV`, requiring a trade of `Vanna_net × ΔIV × 100 × OI` shares in the underlying. On high-vol days, this flow may exceed gamma-driven flow. The dashboard currently has no metric for this.

#### (b) Charm Exposure

Charm is `∂Δ/∂t` — the sensitivity of dealer delta to the passage of time. Near expiration, delta changes sharply as time decays, requiring daily rebalancing even without any move in S or σ. This creates a persistent daily bias in aggregate dealer hedging direction.

**Flynn (2024) — SSRN 5054370**

"Charming! Retail Option Volume, Delta Hedging, and the Impact on Stock Prices." SSRN: 5054370. December 2024.

- **Main result:** Public demand for options creates a strong, persistent relationship with contemporaneous and future stock returns through the charm-induced delta rebalancing of net-short option dealers. The effect is distinct from information-based trading.
- **Mechanism:** As option positions decay over the trading day, the change in dealer delta position from charm is predictable. In aggregate, this biases the direction of dealer hedging flow on any given day, creating directional pressure that is largely orthogonal to GEX.

DeLorenzo (2023) additionally finds significant results for 0DTE charm in the 0DTE context. The charm channel is most relevant intraday and near expiration.

#### (c) Net Delta Exposure

Net delta exposure is the sum of `Δ × OI × 100` across all strikes and expirations (signed by dealer convention). This measures the aggregate dealer delta position — how many underlying shares they would need to sell or buy to close their hedge entirely. Unlike GEX (which captures sensitivity to the *next* move), net delta captures the *existing* directional exposure of the dealer book.

**O'Donovan, Yu & Zhang (2023) — SSRN 4567604** (see §5 above) and **Egebjerg & Kokholm (2024) — SSRN 4936978** (see §5) both decompose the inventory effect (related to net delta changes from new trades) separately from the gamma effect, and find both are statistically significant. This suggests net delta is information not already contained in GEX.

No paper directly provides a clean "net delta exposure" metric analogous to GEX. The practitioner tool MenthorQ offers one; it has not been independently backtested in peer-reviewed research.

#### (d) Implied Volatility Skew (25Δ put-call differential)

**Xing, Zhang & Zhao (2010) — *Journal of Financial and Quantitative Analysis***

"What Does the Individual Option Volatility Smirk Tell Us About Future Equity Returns?" *JFQA*, Vol. 45, Issue 3, pp. 641–662, 2010. DOI: 10.1017/S0022109010000220. SSRN: 1107464.

- **Data:** Individual US equities with listed options
- **Main result:** Stocks with the steepest volatility smirks (most expensive OTM puts relative to ATM calls) **underperform** stocks with the flattest smirks by **10.9% per year** on a risk-adjusted basis. The skew measure predicts the cross-section of stock returns over the following month.
- **Mechanism:** Informed traders with negative news prefer OTM puts; steep smirks reflect informed bearish positioning. The equity market is slow to incorporate this signal.
- **Implication:** Skew (OTM put IV minus ATM call IV) is probably the best-validated options-market predictor of directional equity returns in the academic literature — better validated than GEX for directional prediction at the individual stock level. At the index level, the CBOE SKEW index is widely tracked but has a more ambiguous academic track record.

**Priority ranking for "what to add next":**

| Rank | Metric | Academic Support | Implementation Difficulty |
|------|--------|-----------------|--------------------------|
| 1 | Vanna Exposure (`∂Δ/∂σ × OI × 100`) | Moderate (DeLorenzo 2023, mechanism well-grounded) | Medium — requires per-option vanna from BS formula |
| 2 | Skew (25Δ RR or OTM put-ATM call IV) | Strong for cross-section (Xing et al. 2010) | Low — requires two IV reads per expiry |
| 3 | Charm Exposure (`∂Δ/∂t × OI × 100`) | Emerging (Flynn 2024, DeLorenzo 2023) | Medium — requires per-option charm (theta of delta) |
| 4 | Net Delta Exposure (`Δ_net × OI × 100`) | Indirect support (Egebjerg 2024, O'Donovan 2023) | Low if greeks are CBOE-supplied |

---

## Key Papers — Full Citations

- Avellaneda, M., Boyer-Olson, D., Busca, J., & Friz, P. (2020). "PCA for Implied Volatility Surfaces." *Journal of Financial Data Science*, 2(2), 85–106. arXiv: 2002.00085. [The market factor from implied volatility PCA corresponds to an OI-and-vega-weighted average IV return; OI×vega weighting is one of at least two significant factors in US equity IV surfaces.]

- Anderegg, B., Ulmann, F., & Sornette, D. (2022). "The Impact of Option Hedging on the Spot Market Volatility." *Journal of International Money and Finance*, 124, 102627. DOI: 10.1016/j.jimonfin.2022.102627. [Using DTCC trade repository data on FX options, finds dealer gamma exposure is empirically negative (net short); a −$1 trillion GEX increases EURUSD volatility by 0.7% and USDJPY volatility by 0.9%.]

- Baltussen, G., Da, Z., Lammers, S., & Martens, M. (2021). "Hedging Demand and Market Intraday Momentum." *Journal of Financial Economics*, 142(1), 377–403. DOI: 10.1016/j.jfineco.2021.05.002. SSRN: 3760365. [Over 60 futures markets 1974–2020: last-30-minute return is significantly predicted by earlier-day return; mechanism is gamma hedging demand from options market makers and leveraged ETFs amplifying directional moves.]

- Barbon, A., Beckmeyer, H., Buraschi, A., & Moerke, M. (2021). "Liquidity Provision to Leveraged ETFs and Equity Options Rebalancing Flows: Evidence from End-of-Day Stock Prices." SSRN: 3925725. [A one-SD increase in options gamma imbalance depresses end-of-day returns by −113% of average last-30-minute return; delta-hedging can produce reversal (positive GEX regime) or momentum amplification (negative GEX regime).]

- Buis, B., Pieterse-Bloem, M., Verschoor, W. F. C., & Zwinkels, R. C. J. (2024). "Gamma Positioning and Market Quality." *Journal of Economic Dynamics and Control*, 164, 104881. DOI: 10.1016/j.jedc.2024.104881. SSRN: 4109301. [Zero-intelligence model simulation: positive net gamma reduces volatility and increases market stability; negative net gamma increases volatility and market fragility. Theoretical validation of the GEX sign framing.]

- Cont, R., & Da Fonseca, J. (2002). "Dynamics of Implied Volatility Surfaces." *Quantitative Finance*, 2(1), 45–60. DOI: 10.1088/1469-7688/2/1/304. SSRN: 295859. [Functional PCA of S&P 500 and FTSE implied volatility surfaces identifies three factors: level (parallel shift), slope (skew tilt), curvature (smile bowing). These three factors explain the bulk of daily IV surface variation.]

- DeLorenzo, J. (2023). "Impact of Option Dealer Flows on Equity Returns." SSRN: 4669282. [Using proprietary Volland dealer positioning data: dealers are more sensitive to IV changes (vanna channel) than underlying price moves (gamma channel) on many days; 0DTE charm dynamics generate significant persistent intraday patterns; working paper, not peer-reviewed.]

- Dim, C., Eraker, B., & Vilkov, G. (2023). "0DTEs: Trading, Gamma Risk and Volatility Propagation." SSRN: 4692190. [0DTE high open-interest gamma does not propagate past volatility; intraday 0DTE volume shocks do not amplify past index returns; findings contradict the narrative that 0DTE growth increases systemic fragility.]

- Egebjerg, S., & Kokholm, T. (2024). "A Model for the Hedging Impact of Option Market Makers." SSRN: 4936978. [Model with empirical SPX high-frequency data: gamma effect (price impact from rebalancing existing inventory) and inventory effect (price impact from hedging new trades) are both significant; changes in OMM net option position are closely linked to subsequent SPX futures returns.]

- Figlewski, S. (1989). "Options Arbitrage in Imperfect Markets." *Journal of Finance*, 44(5), 1289–1311. DOI: 10.1111/j.1540-6261.1989.tb02654.x. [Simulation of delta-hedge rebalancing under real market conditions: transaction costs, discrete rebalancing, and volatility uncertainty cause large hedging errors relative to the theoretical continuous-hedge ideal.]

- Flynn, M. J. (2024). "Charming! Retail Option Volume, Delta Hedging, and the Impact on Stock Prices." SSRN: 5054370. [Retail options demand creates strong, persistent relationship with contemporaneous and future stock returns through charm-induced delta rebalancing by net-short option intermediaries; effect is distinct from information-based trading.]

- Gârleanu, N., Pedersen, L. H., & Poteshman, A. M. (2009). "Demand-Based Option Pricing." *Review of Financial Studies*, 22(10), 4259–4299. DOI: 10.1093/rfs/hhp005. SSRN: 1479109. [Using CBOE proprietary dataset: end-users are net long index options, especially OTM puts; dealers are correspondingly net short. Direct empirical confirmation of the sign convention underlying GEX for index products.]

- Hu, J., Kirilova, A., Muravyev, D., & Ryu, D. (2023). "Options Market Makers." SSRN: 4633451. [Account-level KOSPI 200 data on 43 options market makers: only 4 of 43 continuously delta-hedge; most manage risk through rapid inventory rebalancing. Key caveat: the delta-hedging mechanism underlying GEX applies to a minority of market makers.]

- Jonsson, E., & Nyberg, C. (2025). "Convexity in Motion: Leveraging Gamma Exposure to Predict Equity Market Returns and Improve Predictive Modeling." Linköping University master's thesis. DiVA: diva2:1972044. [ARDL model on S&P 500 daily data 2011–2025: changes in GEX are statistically significantly positively associated with subsequent returns across multiple horizons; out-of-sample improvement confirmed by Diebold-Mariano test; strength is somewhat diminished post-2020. Not peer-reviewed.]

- Muravyev, D. (2016). "Order Flow and Expected Option Returns." *Journal of Finance*, 71(2), 673–708. DOI: 10.1111/jofi.12380. SSRN: 1963865. [Order imbalances in the options market reflect inventory risk; market makers in equity options hold large net long positions (not short) in certain contract types; inventory risk component of option price impact is five times larger than previously estimated.]

- Ni, S. X., Pearson, N. D., & Poteshman, A. M. (2005). "Stock Price Clustering on Option Expiration Dates." *Journal of Financial Economics*, 78(1), 49–87. DOI: 10.1016/j.jfineco.2005.01.001. SSRN: 519044. [Optionable stocks cluster at option strikes on expiration dates 1996–2002; average return alteration of at least 16.5 bps per expiration, representing ~$9 billion in aggregate market cap shifts; mechanism is delta-hedging by market makers at strikes with large net long end-user positions.]

- O'Donovan, J., Yu, G. Y., & Zhang, J. (2023). "Option Market Maker Hedging and Stock Market Liquidity." SSRN: 4567604. [Using proprietary exchange data: OMM net short positions demand liquidity from the underlying, destabilizing it; OMM net long positions supply liquidity, stabilizing it; effect is stronger for stocks with constrained liquidity supply.]

- Soebhag, A. (2023). "Option Gamma and Stock Returns." *Journal of Empirical Finance*, 74, 101269. DOI: 10.1016/j.jempfin.2023.101269. SSRN: 4256259. [Cross-section of US stocks: high net gamma exposure underperforms low net gamma exposure; low-net-gamma stocks have higher future realized volatility; effect is non-informational and represents a risk premium; distinct from standard factor model predictors.]

- Xing, Y., Zhang, X., & Zhao, R. (2010). "What Does the Individual Option Volatility Smirk Tell Us About Future Equity Returns?" *Journal of Financial and Quantitative Analysis*, 45(3), 641–662. DOI: 10.1017/S0022109010000220. SSRN: 1107464. [Stocks with steepest OTM-put-vs-ATM-call skew underperform flattest-skew stocks by 10.9% per year risk-adjusted; mechanism is informed negative-news trading in OTM puts; predictability is robust and distinct from other known predictors.]

---

## Confidence and Gaps Summary

| Dashboard Metric | Academic Support | Primary Gap |
|-----------------|-----------------|-------------|
| GEX formula (`Γ × OI × 100 × S² × 0.01`) | Mathematically derivable from Gatheral/Bergomi dollar-gamma; not peer-reviewed as GEX | No paper cites this specific formula |
| GEX sign convention (dealers net short) | Strong for index puts (Garleanu et al. 2009, Anderegg et al. 2022) | Weakened by Hu et al. 2023 (most MMs do not continuously delta-hedge) |
| GEX predicts realized vol | Moderate (Baltussen et al. 2021, Buis et al. 2024, Soebhag 2023) | No clean OOS journal-published backtest of daily GEX signal |
| GEX predicts returns | Emerging (Jonsson & Nyberg 2025, Soebhag 2023) | Only thesis-level for index GEX; journal evidence is cross-sectional |
| Zero-Gamma Level | Weak — no direct test; supported only by the mechanism papers | No paper tests ZGL as a specific numerical level |
| Call/Put Walls | No direct academic test | No paper tests GEX-max strikes as support/resistance levels |
| Hedge Shares/$1 | Moderate — validated implicitly by Egebjerg 2024, Baltussen 2021 | Not defined as a standalone metric in any paper |
| OI-weighted IV surface | Moderate — Avellaneda 2020 supports OI×vega; Cont 2002 is the baseline | No comparison of OI-only vs. vega-only vs. OI×vega weighting |
| Vanna exposure (missing) | Moderate — DeLorenzo 2023 shows vanna channel often dominates gamma | Working paper only; no peer-reviewed journal validation |
| Skew (missing) | Strong — Xing et al. 2010 is the benchmark at stock level | Index skew predictability is less well established than stock-level |
| Charm exposure (missing) | Emerging — Flynn 2024, DeLorenzo 2023 | Both are working papers; no journal publication yet |
