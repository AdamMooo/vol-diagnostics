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

## Key Decision
The vol surface and slope metrics are NOT being removed — they're being deprioritized
in visual hierarchy. The new positioning narrative + magnitude context + VRP become
the primary read; vol structure becomes the "dig deeper" layer.
