# Feature Landscape — GEX Interactive Dashboard v3.0

**Domain:** Options dealer-flow analytics dashboard (PM-facing)
**Researched:** 2026-05-05
**Confidence:** HIGH (math verified against multiple primary sources; display conventions from SpotGamma, FlashAlpha, VannaCharm, Volland)

---

## Feature Summary Table

| Feature | Category | Complexity | PM-Readable | Dependencies |
|---------|----------|------------|-------------|--------------|
| Net VEX (single number) | Table stakes | Low | Yes — "dealer delta shift per 1-vol-point move" | vanna in greeks_engine |
| VEX by strike (bar chart) | Table stakes | Low | Partial — needs label | gex column → vex column in exposure_engine |
| Net CHEX (single number) | Table stakes | Low | Yes — "daily dealer buying/selling from time decay" | charm in greeks_engine |
| Delta-hedge $/1% flow | Table stakes | Low | Yes — direct dollar figure | net_gex already computed |
| Regime card with color | Table stakes | Low | Yes | analytics.summarise() already outputs regime |
| vs-yesterday regime delta | Table stakes | Medium | Yes — "regime unchanged / flipped / intensified" | parquet snapshots already exist |
| Streamlit dashboard shell | Table stakes | Medium | N/A — infrastructure | new file streamlit_app.py |
| Cross-asset overview chart | Table stakes | Low | Yes | plot_overview() already exists |
| VEX by expiry bar chart | Differentiator | Medium | Partial — needs expiry label formatting | expiry_gex() pattern already exists |
| Charm by expiry bar chart | Differentiator | Medium | Partial | same pattern |
| Historical tab: ZGL trend | Differentiator | Medium | Yes — "how far spot is from the flip level over time" | parquet snapshots |
| Historical tab: regime persistence table | Differentiator | Medium | Yes | parquet snapshots |
| Event study output | Differentiator | High | Partial — statistical output needs framing | validation.py already has stub |
| Vanna zero-level (VEX profile) | Defer | High | No — too abstract without context | requires profile recompute like gamma_profile() |
| Intraday refresh / live streaming | Defer | High | N/A | yfinance rate limits; not needed for PM use case |
| Predictive flow signals | Defer | High | N/A | out of scope per PROJECT.md |
| Per-ticker IV surface | Defer | High | No | new data layer; not in scope |

---

## Table Stakes Features

These are expected by anyone who has seen SpotGamma or Volland. Missing them makes the dashboard feel unfinished.

### 1. Net VEX — scalar

**What it is:** Aggregate vanna exposure across the full chain. Measures how many dollars of dealer delta shift occur per 1 vol-point (1%) move in IV.

**Formula:** `VEX = Σ (vanna_i × OI_i × 100 × spot) × sign`
where sign = +1 for calls, -1 for puts. (FlashAlpha convention, consistent with GEX sign convention already in the codebase.)

**BS vanna per share:** `vanna = -exp(-r*T) * N'(d1) * d2 / sigma`
Equivalently: `-vega * d2 / (S * sigma * sqrt(T))`. This is the analytical formula, vectorisable exactly like `bs_gamma` in `greeks_engine.py`.

**PM framing:** "If IV drops 1 point, dealers need to buy $X in {ticker} to rebalance their delta books." Positive net VEX = vol-compression rally tailwind (dealers buy as IV drops). Negative net VEX = vol-spike selling amplifier (dealers sell as IV rises).

**Complexity:** Low. One new function in `greeks_engine.py`, one new column in `exposure_engine.py`.

**Aggregation nuance:** Short-dated options near expiry contribute near-zero vanna (their vega is negligible). The vol-sensitivity story lives in medium- and back-end expirations. This means raw net VEX is dominated by 2-8 week options — generally correct, but worth noting when VEX by expiry reveals concentration.

### 2. VEX by Strike — bar chart

**What it is:** The strike-level decomposition of VEX, identical aggregation pattern to `strike_gex()`. Call vanna positive, put vanna negative, net shown per strike.

**Display convention (SpotGamma / FlashAlpha standard):** Calls in blue/green, puts in red. Spot line, call wall and put wall vlines reused from GEX chart. Same bar-width logic applies.

**PM framing:** "The largest green bar is where a vol drop would force the most dealer buying." Visually identical to the GEX bar chart — PMs who understand GEX will immediately read VEX.

**Complexity:** Low. `plot_strike_vex()` in `analytics.py` is a near-copy of `plot_strike_gex()`.

### 3. Net CHEX — scalar

**What it is:** Aggregate charm exposure. Measures how many dollars of dealer delta shift occur per one day of time passing, with no price move.

**Formula:** `CHEX = Σ (charm_i × OI_i × 100 × spot) × sign`

**BS charm per share:** `charm = -N'(d1) * (2*r*T - d2*sigma*sqrt(T)) / (2*T*sigma*sqrt(T))`
For the dealer-flow convention, charm is the daily delta decay rate. Positive net CHEX = time decay is pushing dealers toward selling (bearish drift). Negative net CHEX = time decay is pushing dealers toward buying (supportive drift). This is the FlashAlpha/SpotGamma sign convention.

**PM framing:** "By close today, dealers need to [buy/sell] $X in {ticker} simply because of time passing — no price move required." Most relevant on days approaching monthly/weekly expiry when near-the-money options have large charm.

**Complexity:** Low. Same implementation path as VEX.

### 4. Delta-Hedge $/1% Flow

**What it is:** `delta_hedge_flow = net_gex / (spot * 0.01)`. Converts net GEX from dollar-gamma units to the dollar amount of stock dealers must trade if spot moves 1%.

**PM framing:** "A 1% SPY move forces dealers to [buy/sell] $X." This is the most immediately actionable number for a PM: it translates abstract GEX into a concrete flow estimate they can compare to average daily volume.

**Complexity:** Low. Arithmetic on existing `net_gex`. Add as a field in `analytics.summarise()`.

**Note:** This is a first-order approximation. It assumes the dealer hedges instantaneously and the gamma profile is flat near current spot. Good enough for daily context; not suitable for intraday precision claims.

### 5. Regime Cards (colored)

**What it is:** One card per ticker in the Streamlit dashboard. Shows: ticker, spot, net GEX, regime badge, vs-flip distance, call wall, put wall. Color-coded by regime (green / red / grey). Existing `REGIME_COLOR` and `REGIME_BG` from `report.py` translate directly to Streamlit `st.metric` or custom HTML.

**PM framing:** The card is the unit of communication. One glance = regime state for that asset. Cards collapse to a summary row in the cross-asset view.

**Complexity:** Low. Streamlit `st.columns()` with HTML/CSS from the existing email template.

### 6. vs-Yesterday Regime Comparison

**What it is:** Load the previous session's snapshot from `gex_snapshots.parquet`, compare `gamma_regime` field. Emit one of: UNCHANGED / FLIPPED (pos→neg or neg→pos) / INTENSIFIED (net GEX magnitude grew >20%) / EASED (magnitude shrank >20%).

**PM framing:** "SPY: negative gamma, INTENSIFIED (net GEX now -$3.2B vs -$2.1B yesterday)." The delta matters more than the absolute level for a PM who already saw yesterday's email.

**Complexity:** Medium. Parquet keyed on `(date, ticker)` already exists. Requires a lookup function + comparison logic. The idempotent write in `validation.py` means yesterday's row is reliably present.

**Watch out for:** Weekends and holidays — "yesterday" must mean "previous trading session," not calendar -1 day. Requires a trading-calendar check or a "most recent prior date" query on the parquet index.

### 7. Streamlit Dashboard Shell

**What it is:** `streamlit_app.py` at the repo root. Layout: top-level tabs (Today / Historical). Today tab: cross-asset overview chart, regime cards in a responsive grid, per-ticker expanders with full analytics. Historical tab: ZGL trend chart, regime persistence table, event study output.

**Complexity:** Medium. No new data work — purely presentation. `st.tabs()`, `st.columns()`, `st.expander()`. The matplotlib figures already exist in `analytics.py`; wrap them with `st.pyplot()`.

**Email pipeline independence:** `streamlit_app.py` imports from `gex/` modules but does not modify them. `run_daily.py` → email stays untouched.

---

## Differentiators

Features that distinguish this from a basic GEX printout. Not expected on first contact, but valued by a PM who returns to the dashboard regularly.

### 8. VEX by Expiry

**What it is:** Bar chart with expirations on the x-axis, summed VEX per expiry. Highlights which expiry bucket is driving the aggregate vanna story.

**Why it matters:** Net VEX is dominated by 2-8 week options. But during vol events, short-dated options can briefly spike. The per-expiry view lets the PM see "is this a front-month story or a back-end story?" SpotGamma shows this as a secondary chart in their Vanna panel.

**Complexity:** Medium. `expiry_vex()` function mirrors `expiry_gex()`. Chart is a simple bar chart with expiry dates on x-axis. Formatting challenge: expiry dates as labels require rotation and a sensible date format (e.g., "Dec 20" not "2024-12-20").

**Aggregation nuance:** Filter to expirations within 0-45 DTE for the primary chart; show 45-90 DTE as a separate "back-end" bar. This is the industry standard — near-term and far-term have different interpretive weight.

### 9. Charm by Expiry

**What it is:** Same pattern as VEX by expiry but for charm. Most relevant in the 0-14 DTE bucket — charm spikes exponentially as expiry approaches.

**Why it matters:** Near-expiry charm is the "invisible bid/offer" that moves markets at open and into close on expiry weeks. A PM running covered calls on XLF wants to know if charm is supporting or pressuring the underlying heading into Friday expiry.

**PM framing:** Color-code by DTE bucket: 0-7 DTE (red — high urgency), 8-21 DTE (amber), 22+ DTE (grey). This immediately communicates urgency.

**Complexity:** Medium. Same as #8.

### 10. Historical Tab: Zero-Gamma Level Trend

**What it is:** Line chart of ZGL (zero-gamma level) per date for a selected ticker, overlaid with spot. Shows whether the gamma flip level is rising, falling, or converging with current price.

**Why it matters:** When spot is approaching ZGL from above (positive gamma regime eroding), that is a structural warning. The PM can see this over 20-30 sessions.

**Complexity:** Medium. ZGL is already stored in `gex_snapshots.parquet` (or needs to be added to the snapshot schema). Two-line chart with `spot` and `zero_gamma_level`.

### 11. Historical Tab: Regime Persistence Table

**What it is:** Rolling window table showing for each ticker: current regime, sessions in current regime streak, % of last 20 sessions in positive/negative/neutral. Color-coded.

**Why it matters:** A PM needs to know if today's negative gamma is day 1 of a new regime or day 12 of a persistent negative streak. Duration context changes how much weight to put on the signal.

**Complexity:** Medium. Pure parquet query and pandas groupby. No new data needed.

### 12. Event Study Output Display

**What it is:** Surface the output of `validation.py`'s event study in the Historical tab. Show: positive gamma days — next-day range distribution vs negative gamma days — next-day range distribution. Box plots or violin plots.

**PM framing:** "On the 47 positive-gamma days in the last 12 months, next-day SPY range averaged 0.6%. On 31 negative-gamma days, 1.1%." This is the validation artifact that earns credibility with a skeptical PM.

**Complexity:** High. The event study logic already exists in `validation.py` but needs enough historical data (60+ sessions) to produce meaningful distributions. The display itself is straightforward (Matplotlib box plot via `st.pyplot()`). The risk is that early data is sparse — build in a "minimum N sessions" gate before showing the chart.

---

## Anti-Features

Explicitly excluded. Revisiting these is scope creep.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Live intraday refresh | yfinance chain pulls are slow (~2-5s per ticker × 10 tickers). Auto-refresh at 1-5 min intervals will hit rate limits and create a poor UX. | Manual "Refresh" button. |
| Predictive scoring / signal | Holm-Bonferroni bar is high; GEX-based predictions are directional hypotheses, not validated signals. Adding a "bullish score" invites misuse. | Stick to descriptive: regime + flow mechanics. |
| Vomma (∂vega/∂vol) | Harder to explain than vanna. "How vol sensitivity changes with vol" is a second-order vol story, not a delta-hedging flow story. PMs won't use it. | Vanna tells the PM-relevant story cleanly. |
| Per-contract flow scanner | Unusual options activity / large print detection is a different product (Barchart / OptionsHawk territory). Requires a different data layer. | Out of scope for this project. |
| IV surface visualization | Skew charts, term structure plots — useful but orthogonal to the dealer-flow angle. Creates scope expansion without PM validation. | Defer to v4.x if desk asks for it. |
| Bloomberg data swap | One-class change in `data_loader.py`. Defer until team validates the yfinance-based dashboard. | Keep the swap documented in `CLAUDE.md`. |
| Order routing / execution | Research and decision-support only, per project constraints. | Hard boundary. |

---

## Feature Dependencies

```
greeks_engine.bs_vanna()    →  exposure_engine.compute_vex()  →  analytics.summarise() (net_vex field)
greeks_engine.bs_charm()    →  exposure_engine.compute_chex() →  analytics.summarise() (net_chex field)
analytics.summarise()       →  streamlit_app.py (Today tab — regime cards)
net_gex (existing)          →  delta_hedge_flow (arithmetic only, no new data)
gex_snapshots.parquet       →  vs_yesterday comparison
gex_snapshots.parquet       →  Historical tab (ZGL trend, regime persistence, event study)
exposure_engine.expiry_gex  →  exposure_engine.expiry_vex / expiry_chex  (pattern copy)
```

**Phase ordering implied by dependencies:**
- Phase 1: greeks_engine (vanna + charm) + exposure_engine (VEX + CHEX + delta_hedge_flow)
- Phase 2: analytics.summarise() extended + vs-yesterday comparison
- Phase 3: Streamlit shell + Today tab (depends on Phase 1 + 2 outputs)
- Phase 4: Historical tab (depends on Phase 3 shell + existing parquet)

---

## VEX Aggregation Nuances — Decision Record

Industry practice (FlashAlpha, VannaCharm, SpotGamma) aggregates VEX **across all strikes and all expirations** for the net scalar. Strike-level breakdown is the primary secondary view. Expiry-level breakdown is the tertiary view, most useful for identifying 0DTE vs front-month vs back-end concentration.

**Recommended approach for this project:**
1. Net VEX: full chain aggregate (Phase 1)
2. VEX by strike: bar chart, same visual language as GEX (Phase 3)
3. VEX by expiry: secondary chart in per-ticker expander (Phase 3, lower priority)

The expiry view is a differentiator, not table stakes. Build the strike view first; expiry view only if the PM desk asks for it during dashboard validation.

**Sign convention lock:** calls +, puts - for both VEX and CHEX. Consistent with existing GEX sign convention in `exposure_engine.py`. Do not invert.

---

## Charm Sign Convention — Note

FlashAlpha uses: positive CHEX = dealers selling (bearish), negative CHEX = dealers buying (supportive).
SpotGamma uses: charm chart is "opposite sign of vanna on each strike" — their framing is from the dealer's perspective as net short options.

These are equivalent under the standard dealer-short assumption already baked into the GEX engine. The key is that the **PM-facing label must state direction explicitly** — "net charm implies dealer buying of $X" — not just show a sign. The sign alone is unintuitive.

---

## Sources

- FlashAlpha VEX concept: https://flashalpha.com/concepts/vex
- FlashAlpha Vanna/Charm guide: https://flashalpha.com/articles/vanna-charm-second-order-greeks-guide
- FlashAlpha CHEX chart conventions: https://flashalpha.com/tools/charm-exposure
- SpotGamma Vanna/Charm: https://spotgamma.com/options-vanna-charm/
- VannaCharm platform intro: https://vannacharm.com/blog/introducing-vannacharm
- MenthorQ dealer hedging mechanics: https://menthorq.com/guide/dealer-hedging-mechanics/
- BS Greeks (analytical vanna formula): https://www.macroption.com/black-scholes-formula/
- Charm delta-decay mechanics: https://medium.com/@navnoorbawa/options-charm-and-delta-decay-how-hedge-funds-profit-from-dealer-hedging-flows-the-3-8-billion-eadcf46d24c9
- Greeks (finance) - Wikipedia: https://en.wikipedia.org/wiki/Greeks_(finance)

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
