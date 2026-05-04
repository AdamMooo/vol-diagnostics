# Options Quant — Sleeve Allocation Framework (α Engine)
## Walkthrough Guide — How to Read the Dashboard

**Purpose:** This document explains each section of the weekly decision dashboard, how to interpret it, and its statistical foundations. Written for the quant team reviewing the POC before any formal meeting.

**Core principle:** State + exposure + historical context. No scoring. No recommendations. The framework describes what is happening and what happened in similar periods. You synthesize the decision.

**First time?** Start with Sections A and C. Section A shows today's market conditions. Section C shows what happened to sleeves historically when signals looked like today.

**Sections at a glance:**

| Section | What it answers |
|---------|----------------|
| A — Current Market State | Where are today's signals relative to the last 5 years? |
| B — Sleeve Mechanics | What does each sleeve actually do? |
| C — Sleeve Returns by Signal Quartile | What did each sleeve return historically when a signal was high/low? |
| D — Past Periods That Looked Like Now | What happened to the market environment after similar past conditions? |
| E — Subperiod Stability | Is each sleeve's behavior consistent across different market regimes? |
| G — TC Sensitivity | How much does execution cost erode returns? |
| H — Tail-Risk Metrics | What does the left-tail look like for each sleeve? |

**Data note:** This POC runs on free public sources — CBOE (options data) and FRED (rates). The 90%-moneyness IV used for put-skew is synthesized (slope ≈ 0.2 approximation from ATM IV) because the real Bloomberg field (`30DAY_IMPVOL_90.0%MNY_DF`) is deferred pending team greenlight. All put-skew and collar/CSP/strangle calibration should be read with this caveat in mind.

---

### Section A — Current Market State

**What it shows:** Today's market conditions measured as percentile ranks on a 5-year rolling window. Six signals + a fragility composite.

**Signals displayed:**

| Signal | Definition | Interpretation |
|--------|-----------|----------------|
| `rv30` | 30-day realized volatility (annualized %) | quiet / normal / turbulent |
| `vrp` | Variance Risk Premium = IV₃₀ − realized vol | vol cheap / fair / vol rich |
| `term` | Term structure = IV₉₀ − IV₃₀ | inversion / flat / strong contango |
| `skew` | Put-skew = IV₉₀%-moneyness − IV₃₀%-ATM | tails cheap / normal / tails expensive |
| `trend` | 12-month log return | downtrend / sideways / uptrend |
| `dd` | Drawdown = pct below rolling 1-year high | in drawdown / mid / near highs |
| `fragility` | Composite of vrp + skew + term + dd | calm / mid / fragile |

**How to read it:**

- Percentile rank 0.00–0.33: signal in the **bottom third** of 5-year history ("low")
- Percentile rank 0.33–0.67: signal near **median** ("mid")
- Percentile rank 0.67–1.00: signal in the **top third** of 5-year history ("high")

Each signal is shown as a raw value + its percentile rank on the 5-year (1260-day) window.

**Example interpretation:** High fragility (vrp + skew + term + dd all elevated) combined with weak trend signals conditions that historically breed demand for defensive sleeve structures — collars, cash-covered puts.

**What it does NOT tell you:** The direction of the signal next week. Percentile ranks describe current position in the distribution, not momentum or reversion.

**Limitations:**

- The 5-year window is a POC choice; the optimal lookback is not calibrated and is deferred.
- Signals are lagged by construction. rv30 uses the past 30 days. This is **causally safe** (no forward-looking data), but the signal reads the immediate past, not the present moment.
- Fragility is a simple composite (equal weight); optimizing weights is deferred.
- 90%-moneyness IV is synthesized; see Data note above.

**Built with:** Causal rolling-window percentile rank over 5 years (1260 trading days). One-year warmup period before ranks begin (avoids ranking against an empty window).

---

### Section B — Sleeve Mechanics

**What it shows:** One-line description of each sleeve structure.

**Why it's here:** Context for understanding the conditional return tables in Section C. Section C shows how each sleeve performed when signals were in a given quartile — Section B explains what you are selling or buying when you enter each sleeve.

**Sleeve definitions:**

| Sleeve | Structure | Payoff Shape |
|--------|-----------|-------------|
| Spot Return | Long underlying index. Reference benchmark. | Uncapped long delta |
| Covered Call (CC) | Long underlying + short ~25Δ call, rolled monthly. | Long with capped upside above strike |
| Cash-Covered Put (CSP) | Cash earning risk-free + short ~25Δ put, rolled monthly. | Premium income; losses on sharp drops |
| Collar | Long underlying + long ~25Δ put + short ~25Δ call, rolled monthly. | Defined-risk band; floor + ceiling |
| Short Strangle | Cash + short ~20Δ call + short ~20Δ put, rolled monthly. | Vol-selling neutral; losses on large moves either way |

**Roll convention:** Monthly roll at expiry. Black-Scholes pricing for premium. Transaction costs shown separately in Section G.

**Built with:** Static reference text. No calibration; these are definitional.

---

### Section C — Sleeve Returns by Signal Quartile

**What it shows:** Historical mean monthly returns for each sleeve, broken down by the quartile of a signal **at the time the roll opened**. For each (underlying × signal × sleeve) combination, you see: mean return in Q1 (bottom 25%), Q2, Q3, Q4 (top 25%), plus statistical significance markers.

**Example:** "When VRP was in Q4 (top 25%), covered call returned +1.5% per month on average in the full backtest period."

**How to read it:**

1. Find today's signal percentile rank in Section A. Identify which quartile today's reading falls in (Q1: 0–0.25, Q2: 0.25–0.50, Q3: 0.50–0.75, Q4: 0.75–1.00).
2. Look at the mean returns for that quartile in Section C for each sleeve.
3. Check the significance marker: `**` = survives Holm-Bonferroni correction (strong evidence), `(raw)` = raw p<0.05 only (weak, may be false positive), blank = not significant at either threshold.

**What Holm-Bonferroni correction means:**

Because this dashboard runs many tests simultaneously — across underlyings × signals × sleeves — raw p-values are unreliable. With 30 tests, you expect 1–2 false positives even if there is no real pattern. Holm step-down procedure controls the family-wise error rate (FWE α=0.05): each test's threshold is adjusted based on how many tests are being run simultaneously.

- `n tests`: Total number of (underlying × signal × sleeve) comparisons in this run.
- `raw p<0.05`: How many would appear significant if we applied no multiple-testing correction.
- `Holm-survives`: How many still look significant after family-wise adjustment.

**Key insight — this is a feature, not a bug:**

The POC finding is that **0 of 30 tests survive Holm correction at FWE α=0.05**. This is the most credibility-establishing result in the entire dashboard. It tells you:

- The framework does **not** claim that today's VRP quartile predicts next month's sleeve return.
- The apparent differences between Q4 and Q1 mean returns are statistically indistinguishable from noise once multiple comparisons are accounted for.
- The rigor is the centerpiece. A framework that says "I do not find a tradable signal" is more trustworthy than one that finds a signal in every test.

The correct interpretation: use Section C for historical context and orientation, not as a mechanical rule. The quartile tables give you a sense of return magnitudes and shapes — not a decision rule.

**Limitations:**

- In-sample: these are historical mean returns from the backtest period, not out-of-sample predictions.
- Assumes the signal ↔ return relationship is stable across time. Walk-forward validation of this assumption is deferred.
- Lagged signals at roll open: realistic for trading (you observe the signal before opening the roll), but the signal captures the immediate-past environment, not next month's.
- Sample size: the number of observations per quartile per underlying is limited by the backtest period. Small samples amplify noise — consistent with 0 surviving Holm.

**Built with:** Welch's two-sample t-test for Q4 vs. Q1 contrast; Holm-Bonferroni FWE step-down correction (α=0.05); stationary block bootstrap for Sharpe confidence intervals (block length ≈ 6 months to span autocorrelation in monthly option returns).

---

### Section D — Past Periods That Looked Like Now

**What it shows:** K=12 historical periods where the signal vector (vrp, term, skew, trend, dd, fragility) was closest to today's current readings. For each matched period, the dashboard shows what the market environment **actually realized** in the following 1, 3, and 6 months.

**How to read it:**

1. "Today's vector" row: today's percentile ranks on the six signals.
2. "Closest analogs": K=12 dates from the historical backtest where the signal vector was nearest to today (smallest Euclidean distance in signal space).
3. For each matched date: the forward-realized environment — what vrp, skew, term, and dd actually did in the 1-month (≈21 trading days), 3-month (≈63 trading days), and 6-month (≈126 trading days) windows after that match.

**Example:** "In 2022-Q1, the signal vector was similar to today (vrp=0.60, term=0.30, skew=0.80, trend=0.25, dd=0.35, fragility=0.71). In the realized environment that followed: at 1 month, vrp dropped to 0.45, skew elevated further to 0.85. At 3 months, term moved into inversion at 0.18."

**Why this framing — pure historical co-movement:**

This section shows you the paths the environment took after similar starting conditions in the past. The intended use is context: "Historically, when conditions looked like this, the environment tended to evolve toward [X]. Given that trajectory, what sleeves would I want to be positioned in?"

Note that this is a starting point for your thinking, not a conclusion. The analogs are imperfect matches; the paths varied; the environment is shaped by macro events that the signal vector does not capture.

**What it is NOT:**

- **NOT a forecast** of where signals will go next month.
- **NOT a sleeve return prediction.** The forward-realized environment shows signals, not P&L.
- **NOT a recommendation** for which sleeve to select.
- **NOT claiming** "this pattern always leads to X." K=12 analogs from a 5-year history are a thin sample; the distribution of paths is wide.

The language used throughout is past tense and conditional: "realized," "historically," "in the period after." If any phrasing reads as forward-looking, treat it as imprecision and flag it.

**Limitations:**

- K=12 is an arbitrary POC choice. The sensitivity of the output to K (e.g., K=5, K=20) has not been tested.
- Assumes historical co-movements reflect the future. This is testable with regime-conditioned walk-forward; deferred to a future phase.
- Only 5 years of history (≈1260 trading days). Pre-2020 and post-2020 market dynamics may differ meaningfully from the current environment.
- Does not account for macro catalysts — Fed policy, earnings, geopolitical shocks — that drove the realized paths in the matched periods. Two periods can look identical on these six signals and have entirely different realized paths because of an exogenous event.
- Forward-realized signals are point estimates at T+21d, T+63d, T+126d. There is no confidence interval shown.

**Built with:** K-nearest neighbors in signal space (Euclidean norm over the six NEIGHBOR_FEATURES). Forward-realized signals: snap to the nearest valid trading date at each horizon; returns `None` if no future data exists (recent matches have no forward data yet).

---

### Section E — Subperiod Stability

**What it shows:** The same full-period sleeve statistics (CAGR, Sharpe, max drawdown, hit rate) recomputed on three approximately equal subperiods of the backtest history.

**How to read it:**

A single full-period Sharpe of +0.5 could mean consistently +0.5 across all regimes, or it could be averaging +0.8 in a benign period against −0.1 in a turbulent one. Section E disaggregates the headline number into its subperiod components.

**Example:** "Collar Sharpe is +0.5 full-period, but +0.8 in 2010–2015 (low-volatility bull) and +0.2 in 2016–2020 (late-cycle, higher-volatility). Caution: the collar's benefit is less stable in choppy markets."

A sleeve with stable Sharpe across all three subperiods has a more robust pattern than one that's a hero in one window and flat in another.

**What it does NOT tell you:** Whether subperiod differences are statistically significant. With short subperiod windows, precision is low. Use Section E for qualitative orientation ("does behavior persist?"), not quantitative inference.

**Limitations:**

- Subperiod boundaries are fixed and arbitrary; they are not detected from the data (e.g., not HMM regimes, not NBER recession markers).
- Small sample per subperiod (roughly 60 monthly rolls per subperiod per underlying) reduces precision substantially.
- Regime-conditioned analysis using HMM or Markov-switching is an optional extension deferred to a future phase.

**Built with:** Geometric compounded returns; annualized Sharpe computed with stationary block bootstrap (block length ≈ 6 months).

---

### Section G — Transaction Cost Sensitivity

**What it shows:** How sleeve Sharpe ratios and cumulative returns degrade as transaction costs increase. The grid tests four assumptions: 0 bp, 5 bp, 10 bp, 20 bp round-trip per leg.

**How to read it:** Find your actual execution cost. If your desk trades at roughly 2 bp per leg, the 5 bp column is a conservative estimate; the 20 bp column is very conservative. Use this to understand how much of the sleeve return is robust to realistic execution costs, and how much is sensitive to slippage.

**Example:** "Covered call Sharpe drops from 0.55 (0 bp) to 0.42 (10 bp). At 20 bp, Sharpe is 0.31. If your desk trades at ≤5 bp per leg, the covered call remains viable on a cost-adjusted basis."

**What it does NOT tell you:** Your actual execution cost. The grid is generic — it does not model bid-ask skew, market-impact, early exercise risk, or pin risk near expiry.

**Limitations:**

- Assumes symmetric costs (bid-ask spread is equal in both directions).
- Does not model market impact for larger notionals.
- Bid-ask skew and roll slippage are deferred. If your actual cost structure is specific to a broker desk or clearing arrangement, calibration to that structure would require a separate run.

**Built with:** TC sensitivity module (`sensitivity.py`). Sweeps the cost grid across the same monthly roll structure as the backtest.

---

### Section H — Tail-Risk Metrics

**What it shows:** Downside risk metrics for each sleeve that Sharpe alone does not capture: Expected Shortfall (ES, also called CVaR) and maximum monthly drawdown.

| Metric | Definition |
|--------|-----------|
| Expected Shortfall (ES, 5%) | Average loss in the worst 5% of monthly return observations |
| Max Monthly Drawdown | Largest single-month loss in the backtest period |

**Why it matters:** Sharpe ratio treats upside and downside volatility symmetrically. Options strategies are often negatively skewed — they earn premium frequently and lose large amounts rarely. Sharpe can overstate the attractiveness of premium-selling sleeves (CSP, strangle, covered call) if the tail is fat.

**How to read it:** A sleeve with a Sharpe of +0.5 and an ES(5%) of −8% looks different from one with a Sharpe of +0.5 and an ES(5%) of −2%. The first sleeve has more left-tail risk per unit of average return.

**Example:** "Short strangle: Sharpe 0.48, ES(5%) −7.2%. Collar: Sharpe 0.42, ES(5%) −3.1%. On a tail-risk-adjusted basis, the collar's lower Sharpe comes with substantially less left-tail exposure."

**Limitations:**

- Historical tail: ES is computed from the backtest return distribution. If future tails are fatter than history (regime change, black swan), this estimate understates true left-tail risk.
- Monthly resolution: extreme intra-month moves (flash crash, overnight gap) may be smoothed by the monthly roll structure.
- No stress-test scenarios: the dashboard does not show performance under 2020-COVID, 2008-GFC, or rate-shock scenarios separately.

**Built with:** Historical simulation ES (not parametric); tail computed from the full backtest monthly return series per sleeve per underlying.

---

## Questions for the Quant Team

These are the questions we want your input on before any follow-up discussion. No preparation needed — gut reactions are useful.

---

**Question 1: Does your team already have a vol/regime/sleeve-context dashboard?**

If so:
- How does it differ from this one? (signals, frequency, output format, who uses it)
- Are there specific signals or time periods you'd want recut or compared?
- Is there overlap we should avoid duplicating?

This is important context before any Phase 2 extension. We want to build on what you already have, not shadow it.

---

**Question 2: What would have to be true for this framework to inform a real decision?**

This is the sharp question. There is no correct answer — the answer surfaces what is missing or what you don't yet trust. Use it to guide your feedback:

- **Data problem?** Missing signals, stale sources, wrong tickers, wrong coverage universe.
- **Statistical rigor problem?** Sample size too small, multiple-testing concerns not adequately addressed, regime stability untested.
- **Model-specification problem?** Wrong signals chosen, wrong weighting, wrong lookback horizons.
- **Instrumentation problem?** Can't efficiently execute the sleeves at the notional sizes relevant to your allocation.
- **Framing problem?** The framework describes something useful, but the output format or language doesn't fit your workflow.
- **Something else?**

There is no expectation that this POC is ready for a capital allocation decision. The question is: what is the critical missing piece?

---

## Known Limitations Summary

A consolidated reference of the limitations described in each section above:

| Area | Limitation | Status |
|------|-----------|--------|
| 90%-moneyness IV | Synthesized (slope=0.2 approximation); real Bloomberg field deferred | Pending team greenlight |
| Signal lookback | 5-year window is a POC choice; not calibrated | Deferred |
| Fragility weights | Equal-weight composite; not optimized | Deferred |
| Section C tests | 0 of 30 survive Holm; no tradable signal found in backtest | By design — rigor feature |
| Walk-forward OOS | Out-of-sample validation deferred | Future phase if team greenlights |
| Section D K | K=12 neighbors arbitrary; sensitivity untested | Deferred |
| Section D paths | Point estimates at T+21d/63d/126d; no confidence interval | Deferred |
| Subperiod boundaries | Arbitrary; not regime-detected | Deferred |
| TC sensitivity | Generic 0/5/10/20 bp grid; bid-ask skew not modeled | Deferred |
| Tail risk | Historical simulation; no stress scenarios | Deferred |
| New signals | Six signals + fragility locked until team validates current set | Locked per scope |
| HMM/Markov switching | Optional extension, not in POC | Locked per scope |
| Automated schedule | Manual run (`python build_report.py`); no scheduler | Locked per scope |

---

## How to Generate the Report

```
python build_report.py
```

Produces `out/sleeve_report_YYYYMMDD.html` — a self-contained file with all sections embedded as base64 charts. No dependencies beyond a Python environment with the packages in `requirements.txt`. No Jupyter required to view it (opens in any browser).

For the raw text dashboard (useful for quick checks):

```
python run.py
```

Prints sections A–E, G–H to stdout.

---

## Changelog

- **2026-05-04:** v1 — POC framework with six signals + fragility composite. Section D reframed to "realized environment after analog match" (not forecast; not realized sleeve P&L). Bloomberg calibration deferred pending team greenlight. Ships on free CBOE + FRED data.

---

*For questions about the framework or this walkthrough, contact the quantitative team.*
