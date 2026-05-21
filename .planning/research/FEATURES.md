# Feature Landscape

**Domain:** PM-facing options positioning monitor (GEX/vol context)
**Milestone:** v3.2 — Actionable Positioning Context
**Researched:** 2026-05-21

## PM Use Case

> "Should I pay up for protection right now, and what's the dealer-driven vol environment telling me about whether I need to?"

30-second glance, not 10-minute analysis session. Every feature earns its pixel by answering part of this question or gets cut.

---

## Table Stakes

Features the PM **expects** on a positioning monitor that claims to be actionable. Missing = "why am I looking at this?"

| Feature | Why Expected | Complexity | Dependencies | Notes |
|---------|--------------|------------|--------------|-------|
| **Positioning narrative** | Raw GEX sign (+2.3B) is meaningless without "dealers long gamma → vol suppression → mean-reversion bias." Every professional GEX tool (SpotGamma, Menthor Q) explains the mechanism. A number without interpretation forces the PM to do the translation mentally — they won't. | **Low** | Existing `net_gex` sign from `summarise()` | Static text template keyed on sign. No model, no estimation. Two states: positive (dampening) and negative (amplifying). Could add a third for near-zero but avoid reinventing the killed regime label — threshold-free is the point. |
| **GEX percentile rank** | "$2.3B net GEX" means nothing without context. Is that high? Low? Normal? Percentile vs trailing history is the standard way to normalize non-stationary dollar-denominated metrics. SpotGamma shows "GEX Index" for exactly this reason. This is what killed the $200M neutral floor — percentile adapts automatically. | **Low** | Parquet snapshot history (`validation.py`); currently 44 rows across 11 sessions for SPY/QQQ/IWM. Needs ≥10 sessions per ticker for meaningful percentile. | Compute `(hist < current).mean() * 100`. Already have the pattern in the (soon-to-be-cut) strike slope percentile code in `streamlit_app.py` lines 223-228. Use 30d default, configurable to 90d. Display as "Xth pctile (Nd)" with "building context" fallback when N < 10. |
| **Output cuts** | Information overload is the #1 failure mode of quant dashboards shown to PMs. Hedge Sh/$1, % vs ZGL, strike slope, term slope — none change a PM decision (per the 2026-05-21 audit). Keeping them signals "we don't know what matters." Professional tools ruthlessly curate. | **Low** | Card HTML in `streamlit_app.py` `render_regime_card()`; Vol tab slope section; `compute.py` still computes slopes (can defer removal of compute, just stop displaying). | Cut from display first. Compute removal can follow in a cleanup pass — no user-facing impact. Vol surface demoted to collapsed expander, not a primary tab. |

## Differentiators

Features that **set this apart** from a generic GEX dashboard. Not expected, but directly answer the PM question in a way most positioning monitors don't.

| Feature | Value Proposition | Complexity | Dependencies | Notes |
|---------|-------------------|------------|--------------|-------|
| **VRP (IV30 − RV20)** | Bridges positioning and hedging cost — "are options cheap or expensive right now?" Most GEX monitors show positioning without hedging cost context. VRP directly answers "should I pay up for protection?" Positive VRP = options rich = less urgency. Negative VRP = options cheap relative to realized = potential opportunity. Well-established (Carr & Wu 2009). | **Medium** | IV30: already in `ChainSnapshot` from CBOE. RV20: **needs new data** — 20-day close-to-close realized vol. Options: (a) yfinance daily closes, (b) store spot in parquet and compute from history. Option (b) is preferable — spot is already stored in snapshots, just need ≥20 sessions of history. Currently have ~11 sessions, so RV20 will show "building context" initially. | RV20 = `std(log returns) * sqrt(252) * 100` over trailing 20 sessions. Annualized, in vol points, same units as IV30. VRP display: `IV30 − RV20` with label "rich" (positive) or "cheap" (negative). **Critical:** this is descriptive, not predictive. Don't imply trade signals. |
| **OI tilt** | Shows directional pressure — "is the market positioned for downside or upside?" Dollar-weighted because 100 OI at strike 600 is 10× the notional of 100 OI at strike 60. Most GEX dashboards show GEX by strike but don't aggregate the put/call OI balance into a single directional reading. | **Low** | Chain DataFrame already has `strike`, `oi`, `type` columns. Pure aggregation: `Σ(OI × strike × 100)` for puts vs calls. | Express as ratio or tilt percentage: `put_notional / (put_notional + call_notional)`. 50% = balanced. >50% = put-heavy (protection demand). <50% = call-heavy (upside positioning). Consider showing as a simple bar or gauge on the card. Avoid over-interpreting — covered calls inflate call OI without being bullish. Note this caveat in methodology. |
| **Front skew gauge with percentile** | Skew is already the project's strongest metric (Xing et al. 2010 — 10.9% alpha). Currently displayed as raw `+X.Xpp` on the card with full chart in Vol tab. Adding percentile rank transforms it from "here's a number" to "this is steep/flat relative to recent history." Skew percentile at a glance tells the PM whether tail protection is bid up relative to normal — directly addresses "should I pay up?" | **Low** | `front_skew` already in parquet snapshots; same percentile logic as GEX percentile. | Display: "Skew 25Δ: +X.Xpp (Yth pctile, Zd)" on the card. High percentile = steep skew = tail demand elevated = protection is expensive. Chart stays in Vol tab (or History tab) for trend context. |

## Anti-Features

Features to explicitly **NOT** build. Each would seem natural but would undermine the tool's integrity or the PM's trust.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Regime categorical label** (e.g., "POSITIVE REGIME", "NEUTRAL") | Already killed in v3.1 for good reason — the $200M neutral floor was hand-tuned and non-stationary. Percentile rank replaces this without arbitrary thresholds. Reintroducing any categorical label (even percentile-based like "high/low/normal") adds a discretionary boundary the PM will anchor on. | Show the percentile number. Let the PM interpret. If they want buckets, they'll mentally bucket 85th pctile as "high." |
| **Predictive signals / trade recommendations** | "GEX says buy/sell" is indefensible. GEX sign predicts next-day vol direction in some studies but effect sizes are small and sample-dependent. The tool is a **monitor**, not a signal generator. Any predictive framing invites backtesting, which will fail the Holm-Bonferroni bar (per v2.0 experience). | Frame everything as descriptive: "dealers are positioned X, which mechanically means Y." Never "therefore do Z." |
| **Intraday refresh / real-time mode** | CBOE CDN is 15-min delayed. OI is T-1 (OCC standard — true for all vendors including Bloomberg). Implying intraday freshness when the core data is stale is misleading. Day-traders will demand it; PMs thinking in weeks/months don't need it. | Show timestamp prominently. "CBOE delayed, 15-min lag · OI T-1" is already in the top bar. |
| **Color-coded alert thresholds** (red/yellow/green on VRP, skew, etc.) | Color thresholds are regime labels in disguise. "VRP > 3 = green" is the same problem as "$200M neutral = neutral regime." The thresholds will be wrong in the next vol regime. | Show numbers with percentile context. Accent bar driven by GEX sign (already exists) is the one color signal — it's binary and mechanically defensible. |
| **GEX heatmap (strike × DTE)** | Deferred in exploration notes. Aggregation decisions (by expiry week? individual expiry?), color scale (linear? log?), and relationship to existing strike bar chart are unresolved. Adding it now creates a second way to see the same positioning data without clarity on which is primary. | Defer to v3.3. The strike GEX bar chart already shows WHERE gamma concentrates. A heatmap adds the WHEN dimension but needs design work. |
| **Multi-asset composite score** | Tempting to combine SPY/QQQ/IWM into a single "market positioning" number. But weighting is arbitrary and hides the per-ticker signal that matters to PMs running different sleeve allocations. | Keep per-ticker cards. The 3-card layout IS the cross-asset view. |

## Feature Dependencies

```
Output Cuts ─── (independent, do first — clears visual space for new features)

Positioning Narrative ──→ needs: net_gex sign (existing)
                         no new data, no new computation

GEX Percentile ──→ needs: parquet history (existing, growing daily)
                   needs: ≥10 sessions per ticker for meaningful output
                   graceful degradation: "building context (Nd)" when N < 10

Front Skew Gauge ──→ needs: front_skew in parquet (existing)
                     same percentile logic as GEX percentile
                     implement together to share the percentile helper

VRP (IV30 − RV20) ──→ needs: IV30 (existing in ChainSnapshot)
                      needs: RV20 (NEW — compute from stored spot history)
                      needs: ≥20 sessions of spot data in parquet
                      currently ~11 sessions → will show "building" for ~2 weeks

OI Tilt ──→ needs: chain DataFrame (existing)
            pure aggregation, no history needed
            independent of other features
```

**Critical path:** VRP has the longest ramp-up (needs 20 sessions of spot history). Start storing spot immediately, show "building context" in the interim. All other features can ship day-one with existing data.

## MVP Recommendation

**Phase 1 — Ship immediately (all low complexity, existing data):**
1. Output cuts (CUT-01, CUT-02) — clear the noise first
2. Positioning narrative (NARR-01) — highest-impact, zero-data feature
3. OI tilt (CTX-02) — pure aggregation on existing chain data
4. GEX percentile + Front skew gauge (NARR-02, CTX-03) — same percentile logic, implement together; graceful "building context" degradation

**Phase 2 — Ships after data accumulation (~2 weeks):**
5. VRP display (CTX-01) — needs RV20 from 20+ sessions of spot history

**Defer:**
- GEX heatmap: design decisions unresolved, not blocking PM use case
- Composite scores: arbitrary weighting, per-ticker view is better

## Card Layout Recommendation (30-second glance)

The card needs to answer the PM question in a visual scan. Recommended layout:

```
┌─────────────────────────────────────────┐
│ SPY                          (accent bar)│
│─────────────────────────────────────────│
│ Spot   $583.20    +0.42% today          │
│ Net GEX  +2.31B   72nd pctile (28d)     │
│ γ-flip   578.5                          │
│ Walls    565 – 595                      │
│─────────────────────────────────────────│
│ IV30     14.2%     VRP +2.1pp (rich)    │
│ Skew 25Δ +6.8pp   85th pctile (28d)    │
│ OI Tilt  58% put-weighted              │
│─────────────────────────────────────────│
│ Dealers long gamma → vol suppression.   │
│ Selling rallies, buying dips. Mean-     │
│ reversion toward γ-flip expected.       │
└─────────────────────────────────────────┘
```

**Top section:** Position (what dealers are doing)
**Middle section:** Cost/pressure (what protection costs, where pressure is)
**Bottom section:** Narrative (plain-English mechanical interpretation)

The narrative is at the bottom because it's the synthesis — the PM reads the numbers first, then the interpretation confirms or contextualizes. Keep it to 2-3 sentences max.

## Complexity Assessment

| Feature | Code Changes | Data Changes | Risk |
|---------|-------------|--------------|------|
| NARR-01 Positioning narrative | Template text in card renderer | None | Very low — static text keyed on sign |
| NARR-02 GEX percentile | Percentile helper + card display | Read existing parquet | Low — pattern exists in codebase |
| CTX-01 VRP | RV20 computation + card display | Needs spot history ≥20d; may need yfinance for backfill | Medium — new data dependency, graceful degradation needed |
| CTX-02 OI tilt | Aggregation in compute pipeline + card display | None — uses existing chain DF | Low — pure arithmetic |
| CTX-03 Skew gauge | Percentile on existing metric + card display | Read existing parquet | Low — same as NARR-02 |
| CUT-01 Card cuts | Remove 4 fields from card HTML | None | Very low — deletion |
| CUT-02 Vol surface demotion | Move from tab to collapsed expander | None | Low — UI restructure only |

## Sources

- SpotGamma dashboard (GEX normalization, positioning narrative patterns) — industry standard reference
- Carr & Wu (2009), "Variance Risk Premiums" — VRP methodology backing
- Xing, Zhang & Zhao (2010, JFQA) — skew predictive value (10.9% alpha)
- Egebjerg & Kokholm (2024) — dealer hedging mechanism
- Garleanu, Pedersen & Poteshman (2009, RFS) — dealer positioning assumption
- Project exploration notes (`.planning/notes/actionable-positioning-pivot.md`) — output audit decisions
- Existing codebase audit (`streamlit_app.py`, `compute.py`, `validation.py`) — dependency analysis
