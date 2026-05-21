# Domain Pitfalls — v3.2: Actionable Positioning Context

**Domain:** Adding VRP, percentile rankings, OI tilt, and positioning narratives to an existing dealer GEX monitor
**Researched:** 2026-05-21
**Context:** v3.2 milestone — Actionable Positioning Context

---

## Critical Pitfalls

Mistakes that produce misleading readings or cause rework.

### Pitfall 1: Percentile Rankings on 9 Days of History

**What goes wrong:** GEX percentile rank (NARR-02) is meaningless with the current snapshot depth. SPY/QQQ/IWM have only 9 observations in `gex_snapshots.parquet`. A "95th percentile" reading from 9 data points is literally the maximum observation — it tells you nothing about distributional extremity.

**Why it happens:** The feature feels simple (just `scipy.stats.percentileofscore`), so implementation races ahead of data accumulation. The dashboard shows a number, and users trust it because it *looks* authoritative.

**Consequences:** PM sees "GEX at 12th percentile" and treats it as meaningful context. With 9 observations, this is noise presented as signal — exactly the thing v3.1 cut (the $200M neutral floor was the same class of error).

**Prevention:**
1. **Hard minimum threshold:** Do not display percentile rank below 30 observations. Show "Accumulating (N/30 days)" instead. 30 is the bare minimum for a percentile to start stabilizing; 60+ is better.
2. **Config constant:** Add `PERCENTILE_MIN_HISTORY: int = 30` to `config.py` alongside `HISTORY_DAYS`.
3. **Same rule for skew percentile** (CTX-03) — it shares the same history store.
4. **Calendar-day vs trading-day clarity:** The store grows by 1 row per ticker per trading day. 30 trading days ≈ 6 calendar weeks from now. Plan the feature to ship immediately but display gracefully-degraded output until history is sufficient.

**Detection:** If you're ever dividing a distribution into quantiles with fewer than ~25 observations, you're decorating noise.

---

### Pitfall 2: Close-to-Close RV Understates Realized Vol During Gap-Heavy Regimes

**What goes wrong:** VRP = IV30 − RV20. If RV20 is computed as `std(log_returns) × √252` using close-to-close prices only, it misses intraday volatility entirely. During gap-heavy but mean-reverting markets (overnight gaps that reverse intraday), close-to-close RV can be 30–50% lower than a range-based estimator. VRP appears large and positive (options "expensive") when in reality realized risk *was* high — it just didn't show in closes.

**Why it happens:** Close-to-close is the simplest estimator and works fine 80% of the time. The 20% where it fails is exactly when VRP matters most — volatile markets where the PM is making hedging decisions.

**Consequences:** Dashboard says "VRP +8pp → options rich, no urgency to hedge" during a period of genuine high realized vol that close-to-close missed. PM under-hedges.

**Prevention:**
1. **Start with close-to-close but acknowledge it.** Label it explicitly: "RV20 (close-to-close)" — not just "RV20". This isn't a Yang-Zhang vs Parkinson debate for v3.2; it's about honest labeling.
2. **Plan upgrade path:** Yang-Zhang (uses OHLC) is the right next step. It requires daily OHLC data. CBOE delayed quotes provide intraday snapshot prices, not historical OHLC bars. You'll need a separate data source (yfinance history, or stored daily bars).
3. **Do NOT use Parkinson alone** — it assumes no drift and overestimates during trending markets. Yang-Zhang handles drift + jumps.
4. **Guard against NaN cascading:** If price history is shorter than 20 days (first-run scenario), RV20 is undefined → VRP is undefined → card should show "N/A" not zero.
5. **Annualization matters:** IV30 from CBOE is already annualized. RV must be annualized identically (×√252 for trading days). Mixing √365 and √252 produces a ~3pp systematic bias in VRP.

**Detection:** If VRP is persistently positive (>5pp) for more than 2 weeks, sanity-check RV20 against actual market experience. Persistent positive VRP is real (the variance risk premium exists structurally), but >8-10pp sustained is suspicious with close-to-close.

---

### Pitfall 3: OI Tilt Distorted by Covered Call Programs and Index Reconstitution

**What goes wrong:** Dollar-weighted put/call OI ratio (CTX-02) is presented as "directional pressure" — put-heavy book implies bearish positioning. But SPY, QQQ, and especially IWM carry massive covered-call overlay programs (BuyWrite ETFs like XYLD, QYLD; pension programs; structured products). These programs systematically sell calls, inflating call OI without any bullish *speculative* intent. Similarly, protective put programs inflate put OI without fresh bearish conviction.

**Why it happens:** OI is a single number per strike — it doesn't distinguish hedgers from speculators, institutional from retail, opening from closing. You're reading the sum and attributing intent.

**Consequences:**
- SPY call OI is structurally elevated → OI tilt reads "call-heavy" → PM interprets as bullish positioning → reality is it's just covered-call supply.
- Around index reconstitution dates (quarterly), OI spikes in affected names → tilt readings become meaningless for 1-2 weeks.
- ETF creation/redemption flows distort OI for SPY/QQQ without any options-market-driven signal.

**Prevention:**
1. **Do NOT label OI tilt as "bullish" or "bearish."** Label it "call-heavy" / "put-heavy" / "balanced" — pure description, no directional interpretation.
2. **Track the tilt's *change* over time, not its level.** The structural programs create a baseline; changes in tilt from that baseline are the signal. This requires history (same 30-day accumulation problem as percentile ranks).
3. **Consider filtering by moneyness band.** OTM puts and OTM calls are more likely to reflect speculative/hedging intent than deep ITM positions (which are often assignment artifacts or delta-one substitutes). Filter to, say, 0.85–1.15 K/S.
4. **Document the limitation** in the methodology footer. "OI tilt reflects gross open interest including market-maker hedging, covered-call overlay programs, and protective put allocations. It is not a sentiment indicator."

**Detection:** If SPY OI tilt is consistently call-heavy by 60%+ across all snapshots, that's the structural covered-call floor, not signal.

---

### Pitfall 4: Narrative Generation That Implies Prediction

**What goes wrong:** The positioning narrative (NARR-01) starts as a mechanical explanation ("dealers are long gamma → they sell rallies, buy dips → dampening effect") but gradually drifts into forward-looking language: "expect mean-reversion," "breakout likely," "vol compression ahead." This crosses from description to prediction — exactly the kind of over-claiming that gets a quant tool discredited when the prediction fails.

**Why it happens:** Mechanical descriptions feel insufficient. The temptation is to add "so what" — which becomes "what will happen" rather than "what is the current state." This is the same failure mode as the regime labels that v3.1 cut.

**Consequences:** PM reads "vol amplification expected" → it doesn't happen → PM loses trust in the entire dashboard, including the defensible parts. One wrong prediction poisons the credible metrics.

**Prevention:**
1. **Hardcode the narrative text.** Do NOT generate it dynamically from templates that combine multiple signals. There are exactly 2 narratives (positive GEX, negative GEX) + 1 edge case (near-zero/insufficient data). Write them once, review them for forward-looking language, and freeze.
2. **Banned words list:** "expect," "likely," "should," "will," "predict," "ahead," "upcoming." Use only present-tense mechanical language: "dealers ARE long gamma," "this TENDS to dampen," "historically associated with."
3. **No conditional narratives combining GEX + VRP + OI tilt.** The temptation is "negative GEX + negative VRP = aggressive hedging expected." This is a model — and an untested one. Keep each metric's narrative independent.
4. **Test the narrative on a skeptical PM:** If the language makes a promise, rewrite it. "Dealers are positioned to dampen moves at these levels" is fine. "Moves will be dampened" is not.

**Detection:** Read every narrative string and ask: "If this doesn't happen, does the dashboard lose credibility?" If yes, rewrite.

---

## Moderate Pitfalls

### Pitfall 5: VRP Window Mismatch Creates Event-Date Artifacts

**What goes wrong:** IV30 is forward-looking (30 calendar days of expected vol). RV20 is backward-looking (20 *trading* days ≈ 28 calendar days of realized vol). They're not measuring the same window. VRP = IV30 − RV20 is an approximation that's standard in academic literature (Carr & Wu 2009 use similar mismatched windows), but it can mislead around events.

**Prevention:**
- Before a known catalyst (FOMC, earnings), IV30 spikes for the event premium. RV20 doesn't reflect it yet. VRP surges positive — this is real (event premium), but showing "+12pp VRP" without context will confuse a PM who knows vol is about to realize.
- **Label with windows:** "IV30 vs RV20" not just "VRP." Transparency about what's being compared prevents misinterpretation.
- **Don't chase window matching.** Using RV30 (30 trading days) to "match" IV30 introduces more staleness. The 20-trading-day convention exists because it balances responsiveness and stability. Keep it.

---

### Pitfall 6: Non-Stationarity Undermines Fixed Percentile Windows

**What goes wrong:** GEX percentile rank vs trailing 30–90 days assumes the distribution of net GEX is roughly stationary over that window. It's not. Market regime shifts (e.g., vol regime change, structural shift in options market participation) make old observations from a different regime misleading.

**Prevention:**
1. **Use 30 trading days, not 90.** Shorter windows adapt faster to regime changes. 90-day windows sound more robust statistically but include observations from potentially different regimes.
2. **Don't use percentile as a mean-reversion signal.** "95th percentile GEX" does NOT mean GEX will revert. Non-stationary processes can stay extreme for extended periods.
3. **Consider showing the raw history chart alongside the percentile** — a PM can visually assess whether the distribution looks stable. A number alone hides regime breaks.

**Detection:** If percentile readings cluster at extremes (consistently >80th or <20th) for more than 5 sessions, the window is likely spanning a regime break. The percentile is comparing current regime to old regime — not measuring extremity within current regime.

---

### Pitfall 7: Data Source Mismatch for RV20

**What goes wrong:** IV30 comes from CBOE delayed quotes (the authoritative source for options data). RV20 requires historical daily closes, which CBOE doesn't provide. Using yfinance for price history introduces a second data vendor — with its own quirks (adjusted vs unadjusted prices, dividend handling, occasional missing days).

**Prevention:**
1. **Use adjusted close from yfinance.** SPY/QQQ/IWM pay dividends; unadjusted closes create artificial return spikes on ex-dates that inflate RV.
2. **Cache historical prices in the parquet store.** Don't call yfinance on every dashboard refresh. Store daily closes alongside the GEX snapshot — same store, same refresh cycle.
3. **Fallback gracefully.** If yfinance fails (it does, intermittently), show IV30 without VRP rather than crashing or showing stale VRP. VRP is context, not core.
4. **Spot is already stored** in `gex_snapshots.parquet`. If yfinance is unreliable, you could compute RV from stored spot history — but only once you have 20+ consecutive trading days per ticker (SPY/QQQ/IWM are at 9 today).

---

### Pitfall 8: Dashboard Clutter Negating the Declutter Goal

**What goes wrong:** v3.2 is simultaneously cutting 5 metrics (hedge sh/$1, % vs ZGL, strike slope, term slope, vol surface demotion) and adding 5 new ones (narrative, GEX percentile, VRP, OI tilt, skew gauge). Net card complexity stays the same or increases. The PM-actionability pivot fails because the card is still overwhelming.

**Prevention:**
1. **Information hierarchy matters more than count.** The narrative should be the largest text element. Percentile/VRP/OI tilt should be compact single-line metrics with minimal chrome.
2. **Cut first, add second.** Implement CUT-01 and CUT-02 in a separate phase/commit before adding new metrics. This forces you to experience the cleaner card before filling it back up.
3. **Maximum 6 metrics per card.** Current defensible core: Spot/Day%, IV30, Net GEX, ZGL, Call Wall, Put Wall = 6. New additions (VRP, percentile, OI tilt) must *fit within* the card, not extend it. Use the narrative as a footer, not a new card section.

---

## Minor Pitfalls

### Pitfall 9: Annualization Constant Mismatch

**What goes wrong:** IV from CBOE uses √365 (calendar days) internally. If you annualize RV with √252 (trading days), there's a systematic ~3pp difference at typical vol levels. This isn't a bug per se — both conventions are used in practice — but VRP sign can flip on this basis alone when true VRP is near zero.

**Prevention:** Pick one convention, document it, and stick with it. √252 for RV is standard. CBOE IV is already annualized (their convention). The mismatch is small and structural — don't try to "fix" it by re-annualizing CBOE IV. Just document: "VRP may carry a small systematic bias (~1-3pp) from calendar-day vs trading-day annualization."

---

### Pitfall 10: Front Skew Gauge Redundancy with Existing Skew Term Structure

**What goes wrong:** CTX-03 adds a front-month skew percentile gauge to the card, while the existing skew term structure chart already shows the same front-month skew value. If the gauge and chart show slightly different numbers (due to different filtering, rounding, or expiry selection), it undermines credibility.

**Prevention:**
- **Same computation, same code path.** The gauge value must come from the same `compute_skew()` call that feeds the chart. Don't recompute.
- **Make clear which expiry "front" means.** The current `SKEW_MIN_DTE = 7` filter skips <7 DTE expirations. "Front month" on the gauge must use the same filter.

---

### Pitfall 11: Storing New Metrics Without Schema Migration

**What goes wrong:** Adding VRP, OI tilt, and GEX percentile to the parquet store means new columns. The store is forward-compatible (old rows get NaN for new columns on read), but if you add columns inconsistently across code paths (e.g., `save_snapshot` adds VRP but `load_history` doesn't expect it), you get silent failures.

**Prevention:**
- Add new columns to `_FLOAT_COLS` tuple in `validation.py`.
- Update `save_snapshot()` to include all new fields in the `row` dict.
- Don't rename or reorder existing columns (the docstring already warns about this).
- Test with a fresh parquet (no old rows) AND the existing 44-row store.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| NARR-01: Positioning narrative | Drifts from description to prediction | Hardcode 2 narrative texts; ban forward-looking words |
| NARR-02: GEX percentile | Only 9 days of history for core tickers | Show "Accumulating (N/30)" until 30 observations; ship feature but degrade display gracefully |
| CTX-01: VRP display | Close-to-close RV understates during gaps; annualization mismatch | Label "RV20 (close-to-close)"; use √252; guard NaN when history < 20 days |
| CTX-01: VRP display | yfinance as second data source | Cache prices; fallback to IV30-only display on yfinance failure |
| CTX-02: OI tilt | Covered call programs inflate call OI structurally | Never label "bullish/bearish"; show change-from-baseline; filter by moneyness |
| CTX-03: Front skew gauge | Redundancy with existing skew chart | Same code path, same expiry filter |
| CUT-01/02: Metric removal | Adding same complexity back via new metrics | Cut first, add second; max 6 metrics per card |
| All new metrics | Schema migration for parquet store | Add to `_FLOAT_COLS`; update `save_snapshot()`; test both empty and populated stores |

## Integration Pitfalls (Cross-Feature)

### The Compound Signal Temptation

**What goes wrong:** Once you have GEX sign + VRP + OI tilt + skew percentile on the same card, the temptation is to combine them into a composite score or traffic-light system. "Negative GEX + negative VRP + put-heavy OI = RED." This is an untested model disguised as a summary — the same class of error as the v3.0 regime labels.

**Prevention:** Each metric stands alone. No composite scoring in v3.2. If a composite signal is ever built, it requires backtesting against actual PM decision outcomes — that's a v4.x research project, not a dashboard feature.

### History Accumulation Race Condition

**What goes wrong:** GEX percentile, skew percentile, and OI tilt change-detection all need ≥30 days of history. VRP needs ≥20 days of price history. These features ship in v3.2 but most will show "N/A" or "Accumulating" for 4-6 weeks. If all features are degraded simultaneously, the v3.2 release feels empty — just cuts without additions.

**Prevention:**
- **VRP can work immediately** if yfinance provides 20+ days of historical closes (it will — these are mega-cap ETFs).
- **Narrative works immediately** — it's based on current-day GEX sign, no history needed.
- **Percentile and OI tilt change require waiting.** Set expectations: v3.2 is a *structural* release. The full value materializes after 30 trading days of data accumulation.
- **Communicate this in the dashboard:** "New metrics are accumulating history. Full percentile context available after [date]."

---

## Sources

- Project audit: `.planning/notes/actionable-positioning-pivot.md` (2026-05-21)
- Research questions: `.planning/research/questions.md` (RQ-001, RQ-002)
- Snapshot data: `out/gex_snapshots.parquet` — 44 rows, 9 days for core tickers (SPY/QQQ/IWM), verified via direct inspection
- Carr & Wu (2009), "Variance Risk Premiums," *Review of Financial Studies* — VRP methodology and window conventions
- Xing, Zhang & Zhao (2010), "What Does the Individual Option Volatility Smirk Tell Us About Future Equity Returns?", *JFQA* — skew metric convention
- Yang & Zhang (2000), "Drift Independent Volatility Estimation Based on High, Low, Open, and Close Prices," *Journal of Business* — range-based RV estimator
- v3.0/v3.1 post-mortems: regime label cut, VEX/CHEX cut — pattern recognition for v3.2 pitfall avoidance
