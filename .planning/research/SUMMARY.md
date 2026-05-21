# Research Summary — v3.2: Actionable Positioning Context

**Synthesized:** 2026-05-22
**Sources:** STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS-v3.2.md

---

## Executive Summary

v3.2 transforms the GEX dashboard from a raw-numbers monitor into a PM-actionable positioning tool. The core question it answers: "Should I pay up for protection right now, and what's the dealer-driven vol environment telling me?" Every feature earns its place by contributing to that 30-second answer — or gets cut. The work is primarily additive computation (VRP, OI tilt, percentile ranks, narrative text) layered onto an existing, stable pipeline, plus surgical removal of noise metrics that don't inform PM decisions.

The recommended approach is conservative and low-risk: **zero new dependencies**, one new module (`gex/positioning.py`) containing pure functions, and integration through the existing summary dict seam. The existing pipeline (CBOE → greeks → GEX → summarise → render) stays untouched. All new computation bolts onto `compute.py` after the current `summarise()` call. The parquet schema extends forward-compatibly — old rows get NaN for new columns.

The primary risk is **premature authority**: displaying percentile ranks and VRP readings before sufficient history exists to make them meaningful. The project has only 9 trading days of snapshot history. Percentiles need 30+ days; VRP needs 20+ days of price data. The mitigation is aggressive graceful degradation — show "Accumulating (N/30 days)" rather than noisy numbers — and sequencing features so that zero-data features (narrative, OI tilt, output cuts) ship first while history-dependent features ramp up. A secondary risk is narrative drift from description into prediction, which would repeat the credibility failure of v3.0's regime labels.

---

## Key Findings

### Stack (from STACK.md)

**No new dependencies.** Every v3.2 feature is implementable with the current stack.

| Feature | Implementation | Existing Libraries |
|---------|---------------|--------------------|
| RV20 | 20-day close-to-close log-return std × √252 | yfinance, numpy |
| GEX/Skew percentile | `scipy.stats.percentileofscore` on parquet history | scipy, pandas |
| VRP | IV30 − RV20 (arithmetic) | numpy |
| OI tilt | `Σ(OI × strike × 100)` grouped by call/put | pandas |
| Narrative | Hardcoded template strings keyed on GEX sign | none |

**Rejected additions:** `arch` (GARCH overkill), `openai` (narrative must be deterministic), `ta-lib` (RV20 is 5 lines of numpy), `fredapi` (yfinance already covers rates). The `pandas-datareader` dependency in requirements.txt is unused — consider removing in cleanup.

**RV20 data source divergence:** STACK.md recommends yfinance for immediate availability; ARCHITECTURE.md recommends parquet snapshot history to avoid adding yfinance as a core dependency. **Resolution: Use parquet history (Option A).** yfinance is already fragile (rate limits, API changes), and making VRP dependent on it means VRP breaks when yfinance breaks. Accept the 4-week cold-start. The parquet store already has spot prices growing daily. For fresh deployments, VRP shows "—" until 20+ snapshots exist.

### Features (from FEATURES.md)

**Table Stakes (must ship):**
1. **Positioning narrative** — Plain-English mechanical interpretation of GEX sign. Zero data dependency. Highest-impact, lowest-complexity feature.
2. **GEX percentile rank** — Normalizes raw dollar GEX into context ("is this high or low?"). Replaces the killed $200M neutral floor with an adaptive, threshold-free alternative.
3. **Output cuts** — Remove Hedge Sh/$1, % vs ZGL, strike slope, term slope. Demote vol surface to collapsed expander. Clears noise so new features have visual space.

**Differentiators (set this apart):**
4. **VRP (IV30 − RV20)** — Bridges positioning and hedging cost. "Are options cheap or expensive?" No competitor GEX tool shows this.
5. **OI tilt** — Dollar-weighted put/call balance. Directional pressure at a glance.
6. **Front skew gauge with percentile** — Transforms existing skew from raw number to contextualized reading.

**Anti-features (explicitly do NOT build):**
- Regime categorical labels (killed in v3.1 for good reason)
- Predictive signals / trade recommendations
- Color-coded alert thresholds (regime labels in disguise)
- GEX heatmap (defer to v3.3 — design decisions unresolved)
- Multi-asset composite score (arbitrary weighting hides per-ticker signal)
- Intraday refresh (CBOE is 15-min delayed, OI is T-1)

### Architecture (from ARCHITECTURE.md)

**One new module: `gex/positioning.py`** — pure functions for VRP, OI tilt, percentile rank, and narrative. No I/O, no side effects, no network calls. `compute.py` orchestrates all calls and passes data in.

**Integration seam: summary dict.** All new values added as keys to the existing summary dict. No new DataFrames, no new return values from `compute_ticker()`. Consumers (`streamlit_app.py`, `report.py`) read new keys via `dict.get()` with defaults — fully backward-compatible.

**Parquet schema: forward-compatible extension.** Add `rv20`, `vrp`, `oi_tilt` columns. Old rows get NaN. Stop populating `strike_slope` and `term_slope` (being cut from display). Don't delete existing columns.

**Key patterns to follow:**
1. Pure computation module + orchestrator integration (matches exposure_engine.py pattern)
2. Graceful degradation with None (matches existing front_skew, delta_hedge_flow patterns)
3. Summary dict as single integration seam (no new DataFrames)

**Anti-patterns to avoid:**
- Fetching data inside positioning.py (I/O belongs in compute.py)
- Putting narrative logic in renderers (two renderers = divergence risk)
- Adding new DataFrames to compute_ticker return (forces every consumer to update)

### Pitfalls (from PITFALLS-v3.2.md)

**Critical (will produce misleading readings):**

| # | Pitfall | Prevention |
|---|---------|------------|
| 1 | **Percentile on 9 days of history** — noise presented as signal, same class of error as the killed $200M neutral floor | Hard minimum: don't display below 30 observations. Show "Accumulating (N/30 days)". Config constant `PERCENTILE_MIN_HISTORY = 30`. |
| 2 | **Close-to-close RV understates during gap regimes** — VRP appears large positive when realized risk was actually high | Label explicitly "RV20 (close-to-close)". Annualize with √252. Document limitation. Plan Yang-Zhang upgrade path for v3.3+. |
| 3 | **OI tilt distorted by covered call programs** — SPY call OI structurally elevated, IWM similar | Never label "bullish/bearish" — only "call-heavy/put-heavy/balanced". Consider moneyness filter (0.85–1.15 K/S). Document limitation. |
| 4 | **Narrative drifts from description to prediction** — one wrong prediction poisons credible metrics | Hardcode exactly 2 narratives (positive/negative GEX). Ban words: "expect," "likely," "should," "will," "predict." Keep each metric's narrative independent — no compound signals. |

**Moderate:**
- VRP window mismatch (IV30 forward-looking vs RV20 backward-looking) around events — label windows explicitly
- Non-stationarity undermines fixed percentile windows — use 30-day default, not 90
- yfinance reliability if used for RV20 — mitigated by choosing parquet history instead
- Dashboard clutter: cutting 5 metrics and adding 5 new ones could net-zero — cut first, add second; max 6 KV metrics per card

---

## Implications for Roadmap

### Recommended Phase Structure

**Phase 1: Core Computation + Output Cuts**
- Create `gex/positioning.py` with all pure functions (compute_rv20, compute_vrp, compute_oi_tilt, compute_percentile_rank, generate_narrative)
- Wire into `compute.py` — enrich summary dict
- Update `validation.py` — persist new fields to parquet, add to `_FLOAT_COLS`
- Execute CUT-01 (remove 4 noisy card fields) and CUT-02 (demote vol surface)
- **Rationale:** Computation must exist before display. Cuts must happen before additions to avoid net-zero clutter. Parquet persistence starts immediately so history accumulates from day one.
- **Delivers:** Clean pipeline producing all new metrics. Cleaner cards (fewer noise metrics).
- **Pitfalls to guard:** Schema migration (Pitfall 11), NaN cascading when history insufficient.
- **Features:** CUT-01, CUT-02, all positioning computation

**Phase 2: Card Rendering + Narrative**
- Add VRP, OI tilt, GEX percentile, skew percentile to cards (both streamlit + report.py)
- Add positioning narrative as card footer
- Implement graceful degradation display ("Accumulating N/30 days", "—" for None values)
- **Rationale:** All data fields finalized in Phase 1. Rendering changes are the most visible — do them with stable data. Narrative is last because it reads from the full enriched summary dict.
- **Delivers:** PM-facing actionable cards with the 30-second answer.
- **Pitfalls to guard:** Narrative prediction drift (Pitfall 4), dashboard clutter (Pitfall 8), OI tilt labeling (Pitfall 3), percentile display threshold (Pitfall 1).
- **Features:** NARR-01, NARR-02, CTX-01, CTX-02, CTX-03 display

### Phase Grouping Rationale

Two phases, not six. The features are tightly coupled through the summary dict seam and the card layout. Splitting further (e.g., one phase per feature) would create multiple partial card states that each need UI testing. Two phases give a clean separation: **back-end computation** (testable in isolation with unit tests) then **front-end rendering** (testable visually).

### Research Flags

| Phase | Needs Research? | Why |
|-------|----------------|-----|
| Phase 1 | **No** | Standard patterns. Pure functions, dict enrichment, parquet column addition. Well-documented in ARCHITECTURE.md with exact function signatures and integration code. |
| Phase 2 | **Maybe — card layout only** | The card layout recommendation in FEATURES.md is detailed but untested. May need a quick design spike to validate the information hierarchy works at a glance. The rendering code changes (HTML in report.py, Streamlit widgets) are straightforward. |

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | **HIGH** | All libraries already in requirements.txt. No version conflicts. Verified locally. |
| Features | **HIGH** | Clear table-stakes/differentiator/anti-feature separation. PM use case well-articulated. Feature dependency graph is clean. |
| Architecture | **HIGH** | Single new module, existing integration seam, exact function signatures provided. Matches established codebase patterns. |
| Pitfalls | **HIGH** | 11 pitfalls identified across critical/moderate/minor. Prevention strategies are concrete and actionable. Draws on v3.0/v3.1 post-mortem lessons. |

### Gaps to Address During Planning

1. **RV20 source final decision:** STACK.md and ARCHITECTURE.md disagree (yfinance vs parquet history). This summary recommends parquet history. Confirm during Phase 1 implementation that `load_history()` returns spot reliably and has sufficient rows. If the cold-start UX is unacceptable, fall back to yfinance with caching.

2. **OI tilt moneyness filter:** PITFALLS recommends filtering to 0.85–1.15 K/S to reduce covered-call distortion. FEATURES.md and ARCHITECTURE.md don't mention this. Decide during Phase 1 whether to filter or show gross tilt with a caveat. Recommendation: start with gross tilt + documented limitation, add moneyness filter in v3.3 if PM feedback indicates distortion is confusing.

3. **Card layout validation:** The proposed card layout (FEATURES.md) is a mockup. No design spike is planned. Risk is low (it's Streamlit cards, easy to iterate), but the narrative footer length and metric density should be tested with real data before calling Phase 2 complete.

4. **Percentile minimum threshold:** PITFALLS recommends 30 observations minimum. STACK.md suggests 10. This summary recommends **30** — matching the pitfalls analysis. 10-point percentiles are noise. Ship the feature with graceful degradation; it becomes useful ~6 weeks after deployment.

---

## Key Constraints

1. **Thin history (9 days):** The parquet store has only 9 trading days for SPY/QQQ/IWM. Percentile ranks need 30+ days; RV20 from parquet needs 20+ days. Every day of delay in shipping Phase 1 (which starts persisting new fields) is a day of missing history. Start accumulation immediately.

2. **OI tilt structural distortion:** Covered call programs (XYLD, QYLD, pension overlays) inflate call OI systematically. OI tilt will read "call-heavy" for SPY by default — this is structural, not signal. Never label bullish/bearish. Track change-over-time once history permits.

3. **Narrative tone:** Must be mechanical description, never prediction. Hardcode exactly 2 base narratives (positive GEX = dampening, negative GEX = amplifying). Ban forward-looking language. One wrong prediction poisons the entire dashboard's credibility.

4. **No new dependencies:** The stack is frozen for v3.2. If a feature can't be built with current libraries, it's deferred.

5. **Annualization convention:** Use √252 (trading days) for RV. CBOE IV is already annualized (their convention). Document the ~1-3pp systematic bias from calendar-day vs trading-day annualization. Don't try to "fix" it.

---

## Sources (Aggregated)

**Academic:**
- Carr & Wu (2009), "Variance Risk Premiums," *Review of Financial Studies* — VRP methodology
- Xing, Zhang & Zhao (2010), "What Does the Individual Option Volatility Smirk Tell Us About Future Equity Returns?", *JFQA* — skew predictive value
- Egebjerg & Kokholm (2024) — dealer hedging mechanism
- Garleanu, Pedersen & Poteshman (2009, *RFS*) — dealer positioning assumptions
- Yang & Zhang (2000) — range-based RV estimator (upgrade path reference)

**Industry:**
- SpotGamma dashboard — GEX normalization, positioning narrative patterns
- yfinance API (Context7 docs) — verified download()/history() methods

**Internal:**
- Existing codebase: compute.py, analytics.py, exposure_engine.py, validation.py, report.py, streamlit_app.py
- v3.0/v3.1 post-mortems: regime label cut, VEX/CHEX cut
- Project audit: `.planning/notes/actionable-positioning-pivot.md`
- Snapshot data: `out/gex_snapshots.parquet` — 44 rows, 9 days for core tickers
