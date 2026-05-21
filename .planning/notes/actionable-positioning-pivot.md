---
title: "Actionable positioning pivot — vol surface is overcooked, need mechanical narratives"
date: 2026-05-21
context: "gsd-explore session — user feedback on v3.1 dashboard"
---

# Actionable Positioning Pivot

## The Problem

The GEX dashboard shows mathematically correct outputs (vol surface, skew term
structure, strike/term slopes) but fails to answer the user's actual question:
**"What are dealers forced to do, how much does it matter, and what's the pressure
around current levels?"**

The vol surface is over-smoothed (50×40 grid, linear interpolation, p97 cap) and
has drifted into academic territory. The skew metric floats without connecting to
the positioning narrative. Numbers like +2.3B net GEX lack magnitude context.

## What's Defensible to Add

### 1. Positioning Narrative (always visible)
Text block on the card explaining what current GEX sign means mechanically:
- Positive net GEX → dealers long gamma → sell rallies, buy dips → vol suppression
  → mean-reversion toward γ-flip
- Negative net GEX → dealers short gamma → chase moves → vol amplification →
  momentum/breakout risk
- Backed by Egebjerg & Kokholm (2024) dealer hedging mechanism

### 2. GEX Percentile Rank
Today's net GEX vs trailing 30–90 day history from parquet snapshots.
Avoids hand-tuned dollar thresholds (non-stationary — why we killed the $200M
neutral cutoff). Adapts as history accumulates.

### 3. VRP Context (IV30 − RV20)
- IV30: already have from CBOE
- RV20: 20-day realized vol from price closes (yfinance or stored history)
- VRP = IV30 − RV20
- Positive VRP = options expensive = dealers collecting premium = less hedging urgency
- Negative VRP = dealers underwater = aggressive hedging = bigger market impact
- Well-established in academic literature (Carr & Wu 2009)

### 4. OI Tilt
Dollar-weighted put vs call OI: Σ(OI × strike × 100) by side.
Shows directional pressure — is the book put-heavy or call-heavy?
Already have the chain data, just need aggregation.

### 5. Front Skew Gauge with Percentile
Compact metric on the card (already have front_skew value).
Add percentile rank vs history, same as GEX percentile.
Term structure chart stays in the Vol tab for deeper dig.

## Deferred (Needs More Thought)

### GEX Heatmap (strike × DTE)
Raw OI×gamma heatmap — zero interpolation, each cell = one (strike, expiry) pair.
Shows where pressure actually lives without smoothing.
**Deferred because:** Need to decide on aggregation (by expiry week? individual expiry?),
color scale (linear? log?), and whether it replaces or supplements the strike bar chart.

## What Stays
- Vol surface (moves to supplemental position, not primary)
- Strike GEX bars, gamma profile, γ-flip, walls, delta-hedge flow
- History tab (γ-flip vs spot, skew history)
- Methodology & assumptions footer

## Output Audit (2026-05-21)

Every output scored against: **"Does this change a PM decision?"**

### CUT (no PM value)
1. **Hedge Sh / $1** — mechanism trivia, no one trades off this number
2. **% vs ZGL** — derivative of a model construct with no predictive backing
3. **Strike Slope** (pp/10% K/S) — unintuitive, no predictive value, model construct
4. **Term Slope** (pp/30 DTE) — same; crude linear fit, noisy
5. **Vol Surface** — demoted to collapsed/optional section (not a primary tab)

### KEEP (earns its spot)
- **Net GEX** — with sign narrative + percentile rank (new)
- **IV30** — with VRP pairing (new)
- **Skew 25Δ** — strongest metric (Xing et al. 2010), add percentile
- **GEX by Strike** bar chart — shows WHERE gamma concentrates
- **Gamma Profile** — lightweight, useful
- **γ-flip vs Spot** history — positioning evolution
- **Skew history** — trending skew matters
- **% today** — basic context

### ADD (new for v3.2)
- **Positioning narrative** — always-visible mechanical explanation of GEX sign
- **GEX percentile** — vs trailing 30–90d history
- **VRP** — IV30 − RV20, hedging cost context
- **OI tilt** — dollar-weighted put/call pressure
- **Skew gauge** — front-month percentile on card

## PM Use Case (crystallized)
**"Should I pay up for protection right now, and what's the dealer-driven vol
environment telling me about whether I need to?"**

This is NOT a day-trading tool ("spot above call wall, expect pin"). It's a
hedging cost advisor + vol regime monitor for PMs thinking in weeks/months.

## Validation Plan
1. **Dogfood** — use personally for 2–4 weeks, journal which outputs change decisions
2. **Peer feedback** — share with 1–2 PMs, observe engagement vs ignored outputs
3. **Basic backtest** — does GEX-sign × VRP explain next-week RV or sleeve P&L?

## Key Decision
Strip academic elegance. Keep positioning signal. Add PM-facing context.
Vol surface demoted to optional deep-dig. Slope metrics killed entirely.
