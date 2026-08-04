# Vol Diagnostics — Interview Positioning

*For a systematic option-writing / income-ETF desk (buy-write / cash-covered-put). Descriptive, non-directional — it conditions **how you run the writing program**, never where the market goes.*

Last updated: 2026-08-04

---

## The pitch (say this first — it disarms the trap)

> "It doesn't produce buy or sell calls, and I'd distrust anything that claimed to. A writing desk's edge is structural — implied vol trades above realized on average, and selling options harvests that variance risk premium. This tool doesn't create that edge. It tells the desk **when the premium is rich, where on the surface it's richest, and how much risk the regime carries** — so the same writing program runs with its eyes open instead of writing the same thing every roll."

There is nothing directional in it by design — and that is the point, not a gap.

---

## How a writing desk uses it

Every read maps to a decision a systematic overwriter already makes on every roll. None require a view on where the market goes.

| What it reads | The desk decision it conditions | Backing |
|---|---|---|
| **VRP percentile** | **Harvest intensity.** Rich vs its own ~10-yr history → lean into writing; cheap → pull back, move to spreads, or wait. Same tail risk, more or less pay. | **Strong** — best-evidenced read here |
| **Skew (25Δ)** | **Which side, which strike.** Steep skew = puts rich, calls cheap → cash-covered puts are well paid, upside calls are not. | **Strong** — Xing–Zhang–Zhao (2010) |
| **Term structure** | **Tenor & roll cadence.** Backwardation = rich front premium + near-term stress → write shorter, re-evaluate faster. Contango → roll favors longer-dated. | Standard vol term-structure |
| **Expected move + surface** | **Strike placement.** Set short strikes outside the 1σ cone the desk will accept assignment within. | Model-free, from ATM IV |
| **Dealer-gamma *sign*** | **Risk sizing & tail hedging — NOT direction.** Positive (contained) → moves smaller → short-vol posture safer. Negative (elevated) → moves larger either way → size down, widen strikes, hedge tails. | **Moderate**, magnitude only — Baltussen (2021), Anderegg (2022) |
| **SPY / QQQ / IWM divergence** | **Which underlying to overwrite.** IWM breaking from SPY = small-cap / breadth stress → tilt the sleeve to where premium fits the risk. | Cross-asset read |

**The honest nuance an informed interviewer will probe:** a high VRP percentile does *not* predict returns. My own pre-build test found no forward-return edge from timing the VRP tilt (`p = 0.74`) and I shelved that feature. So the claim is never "premium rich → market up." It's "premium rich → I'm paid more per unit of the risk I'm already carrying." **Risk compensation, not market timing.**

---

## Worked example — when it mattered

Dealer gamma was negative across SPY and QQQ, so the move-size regime read **elevated**. Then the index ran roughly **15% in a handful of sessions** and realized vol spiked — a violent move, exactly as the regime implied.

**But it went up, not down.** A directional tool would have been wrong here. This one wasn't, because it never called direction. It flagged that the shock absorbers were off: with dealers short gamma, hedging trades *with* the move, so whatever catalyst arrived got amplified. Direction came from the catalyst; **size came from the gamma regime.**

> "Gamma told me how hard it would move, not which way. Negative gamma never meant 'down' — it meant the brakes were off, and realized vol confirmed it."

**The counterfactual seals it:** the same catalyst in a *positive*-gamma regime would have looked different — more mean-reverting, fewer spikes, less one-directional follow-through, because dealer hedging leans *against* the move the whole way. Same news, dampened path. That asymmetry in return auto-correlation across gamma regimes is the Baltussen et al. (2021) intraday-momentum result.

---

## Tough questions, straight answers

**Q — Isn't dealer gamma (GEX) just retail SpotGamma noise?**
It's derivable from the dollar-gamma framework in Gatheral and Bergomi — not a black box. But I treat it with suspicion: it's demoted below the vol-surface reads, capped at ≤90 DTE, labeled a model construct, and I use only its *sign* for a magnitude read. I also engage the counter-evidence — Dim, Eraker & Vilkov (2023) find 0DTE gamma, the most concentrated pool, does *not* propagate to future vol. That paper sits in my methodology doc, not filed away.

**Q — Why skew for single names but gamma for the index?**
The dealer-net-short assumption GEX rests on is empirically strong for *index* options (Gârleanu, Pedersen & Poteshman 2009) but breaks for single names — market makers there are often net long (Muravyev 2016) and most don't continuously delta-hedge (Hu et al. 2023). So the single-name Explore view drops gamma entirely and leads with skew and raw OI. Skew is the read that's actually validated at the single-name level.

**Q — That's not the academic (Carr–Wu) variance risk premium.**
Correct — it's implied minus realized in vol *points*, not variance units. Deliberate: for vanilla option writing, premium is roughly linear in vol, so vol points map directly to how rich the premium is. Carr–Wu variance VRP is the right object for a variance-swap book, not a covered-call sleeve. I documented the choice in the code rather than quietly using one and labeling it the other.

**Q — How do you avoid overfitting a dashboard full of metrics?**
Statistical validation before anything ships — multiple-testing awareness and out-of-sample checks. The cleanest proof is what I *removed*: vanna and charm exposures, wall clusters, a hand-tuned regime label, a vs-yesterday classifier — each carried more assumption than evidence. And the VRP-timing tilt died on a null test rather than shipping.

**Q — Most of your history is only months long.**
True for the chain-derived metrics — they only accrue from my own daily snapshots since ~mid-2025, maturing toward ~2027. But the VRP percentile rides the CBOE vol-index's real depth (VIX back to 1990). Every read is credibility-gated: a metric only shows a rich/cheap band once it clears a session-count floor. A thin sample is omitted, not shown with a caveat.

**Q — How would this work on a real desk's data?**
The data source is isolated to a single class. Today it's the free CBOE delayed feed; a Bloomberg or OPRA drop-in is a one-class change — everything downstream (surface fit, VRP, positioning) is source-agnostic.

---

## What it deliberately will not do (lead with this if the room values rigor)

- **No direction.** No metric forecasts up or down. A writing desk doesn't need one, and I couldn't validate one.
- **No signals.** No buy/sell triggers, no composite score, no hidden weighting — every read maps one number through one labeled band.
- **Model constructs are labeled as such.** Dealer-gamma sign drives only a move-size regime; γ-flip and walls are not surfaced as price levels.
- **Claims are tiered to the evidence.** Strong for VRP and skew; moderate for dealer-gamma magnitude; explicitly unsupported for direction — and the dashboard says so.

---

## The 30-second demo path

1. **Open on the Regime tab.** "One sentence per ticker: is premium rich or cheap, and do moves tend contained or larger. The whole environment in a line."
2. **Point at the VRP card.** "Colored by rich/cheap against a decade of history, with the trend sparkline. This drives how hard the desk writes."
3. **Open a surface.** "Where the richness sits — skew tells me which side to sell, term tells me which tenor."
4. **Show the Explore tab on a single name.** "No dealer gamma here — the assumption doesn't hold for single names, so it leads with skew and raw OI. Same discipline, different regime."
5. **Open the sidebar methodology.** "Every claim tiered to its evidence, citations included. Nothing on the page overreaches what's behind it."

---

## Lines to land

- "A static overwriter writes the same thing every roll. This writes when it's paid, where it's paid, in size scaled to the regime."
- "There's nothing directional in it — that's the design, not the limitation."
- "Gamma told me how hard it would move, not which way."
- "I built something whose discipline about what it won't claim is the headline."

---

*Full literature review with SSRN/DOI citations: [`research/methodology-deep-review.md`](research/methodology-deep-review.md).*
