---
title: "GEX heatmap — strike × DTE raw pressure view"
trigger_condition: "When v3.2 defensible metrics are shipped and user has lived with the new narrative cards"
planted_date: 2026-05-21
---

# GEX Heatmap (Strike × DTE)

Zero-interpolation heatmap showing GEX contribution per (strike, expiry) cell.
The raw lumps ARE the signal — shows where OI×gamma pressure actually concentrates
without any smoothing.

## Open Design Questions
- Aggregation: individual expiry dates or bucketed by week?
- Color scale: linear, log, or diverging (blue/red centered at zero)?
- Relationship to existing strike bar chart — supplement or replace?
- Should cell size encode OI magnitude (bubble chart variant)?
- How to handle the visual density with 20+ expiries × 50+ strikes?

## Why Deferred
User wanted to sit with the v3.2 narrative/VRP changes first before adding
another visual. Risk of over-engineering the display layer again.
