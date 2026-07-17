# Phase 10: Dashboard Restructure (local only) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-31
**Phase:** 10-dashboard-restructure-local-only
**Areas discussed:** Tab architecture, Calculus+VRP tab identity, VRP value, Positioning (OI/GEX) pivot, Evolution view, Two-date compare, Palette & holes

---

## Tab architecture — final tab set

| Option | Description | Selected |
|--------|-------------|----------|
| Surface · Calculus · Evolution · VRP | Replace GEX/Flow with a VRP tab | |
| Surface · Calculus · Evolution · Flow | Keep GEX; VRP folds into Calculus | |
| Surface · Calculus+VRP · Evolution · Flow | Keep all 4 functions; VRP joins the merged Calculus tab; GEX survives demoted | ✓ |

**User's choice:** Surface · Calculus+VRP · Evolution · Flow (densest tab = Calculus, accepted).
**Notes:** Code is already 4 tabs (Carry tab dropped in Phase 7 `ad8b017`); roadmap "5→4" is stale. Real move = merge Skew+Term + add Evolution. User added a free-text note up front: "clean up dead/not useful skew tabs" (in scope), "get a VRP tab going for real value" (in scope, reorganize), "and a GARCH tab" (deferred — new capability).

## Calculus+VRP tab identity (surface already shows shape)

| Option | Description | Selected |
|--------|-------------|----------|
| VRP-led + scalar strip | VRP headline + front-skew/term-spread/cross-ticker scalars; drop all 2D smile + ATM-term redraws | ✓ |
| Two charts + scalars | Keep cross-ticker RR chart + VRP chart + scalars | |
| Push scalars to cards, shrink tab | Move skew/term/VRP to regime cards; tab nearly disappears | |

**User's choice:** VRP-led + scalar strip.
**Notes:** User interrupted to make the call himself: "I do not really love my skew and term structure tab as it is already shown in the 3d surface." Confirmed the 2D smile + ATM-term redraws are dead weight → dropped.

## VRP value

| Option | Description | Selected |
|--------|-------------|----------|
| Headline + %ile + sparkline + read | Number + 30-session percentile + VRP sparkline + plain-language read | ✓ |
| Headline + %ile + read (no chart) | Same minus the sparkline | |
| Front vs back VRP | Term-VRP decomposition (borderline new compute) | |

**User's choice:** Headline + %ile + sparkline + read.
**Notes:** All from existing history store (iv30/rv20/vrp persisted Phase 6). No new modeling. Front-vs-back VRP → deferred.

## Positioning (OI/GEX) pivot

| Option | Description | Selected |
|--------|-------------|----------|
| OI-led, OI walls, GEX as labeled context | OI primary; small GEX readout | (superseded) |
| OI-led, OI walls, GEX dropped | Pure observable; no γ-flip | |
| Keep GEX-led, just make it honest | GEX primary + assumptions caption | |
| **User-refined design** | OI bar chart (pure OI, like current) + separate ~2-month price chart with call wall · γ-flip · put wall lines; GEX only for dealer exposure + flip + walls; gamma profile demoted | ✓ |

**User's choice:** User-refined (two AskUserQuestion attempts rejected in favour of conversation). Final: "I want… open interest chart that looks like the one we have but it is pure OI. Then… the price chart last 2 months with the call wall, gamma flip and put wall so it is easy to see how far we are… and make sure this is kinda less assumption based."
**Notes:** User: "GEX kinda makes it less nice… more ideal to have OI"; "still want gex but JUST for the dealer exposure and flip level"; "want the bar chart to be for OI"; "still want that gamma chart for the call and put gamma wall." Walls/flip GEX-defined (persisted daily → real 2-mo history); labeled model constructs. Claude provided an importance ranking of OI/GEX/flip/walls/profile for SPY·QQQ·IWM. Automates the user's manual TradingView line-drawing.

## Evolution view

| Option | Description | Selected |
|--------|-------------|----------|
| 4 small-multiples, tickers overlaid | Horizon radio (default 5d) + level/rms/skew/term panels, SPY·QQQ·IWM overlaid each | ✓ |
| Combined chart, per-ticker | All 4 scalars on one chart; pick ticker | |
| Headline scalar + detail | Lead one scalar cross-ticker; rest in expander | |

**User's choice:** 4 small-multiples, tickers overlaid.
**Notes:** Cross-ticker divergence visible per dimension (EVOL-05). Horizon single-select radio, default 5d (RPT-05 narrative lead).

## Two-date compare

| Option | Description | Selected |
|--------|-------------|----------|
| Two pickers, 'Today (live)' as option | Calendar date selectors | (refined) |
| Mode toggle live/stored | Radio between modes | |
| Two stored pickers only | Drop live compare | |
| **User-refined** | Two relative-horizon dropdowns {live,1d,5d,10d,20d,30d,60d} resolved to stored sessions; default live vs 5d; visual-only 3D Δ-surface | ✓ |

**User's choice:** User-refined dropdowns; **visual-only** (option a) for the per-pair scalars question.
**Notes:** User: "dropdown like (live, 1d, 5d, 10d, 20d, 30d, 60d)… compare 10d ago to 5d ago… make sure it makes sense and is effective." Claude flagged the methodological line: Compare = visual (point-to-point OK for eyeballing); Evolution = rigorous scalar (rolling baseline) — don't duplicate noisy point-to-point scalars. User chose (a) visual-only. 1d noted as noisiest rung.

## Palette & holes

| Option | Description | Selected |
|--------|-------------|----------|
| Restrain in place (dark dash + matched light email) | Keep dark; mute accents; shared config tokens | (final basis) |
| Light & formal everywhere | Both surfaces light/white | (chosen then reversed) |
| Just dial down, no shared tokens | streamlit only; email later | |

**User's choice:** Initially "Light & formal everywhere," then **reversed** to dark: "I do enjoy the darker themes as it is better and is more bloomberg like."
**Notes:** Dark retained → rehabilitates the amber accent (Bloomberg amber-on-black); refine neon orange → tasteful terminal-amber, mute sign colors, keep Viridis, honest NaN holes retained. Shared accent tokens in config.py for dashboard+email consistency. Email background (dark vs light) deferred to Phase 11 (RPT-04).

---

## Claude's Discretion

- Exact hex values for the restrained Bloomberg palette (planner / optional `/gsd-ui-phase`).
- Viridis vs a more terminal-appropriate sequential on dark.
- Exact OI chart encoding (grouped vs diverging columns) — keep it visually like the current strike-GEX chart.
- Evolution empty/cold-start caption wording.

## Deferred Ideas

- **GARCH tab / conditional-vol model** — new capability; descriptive-only + no-new-signals guardrail; own phase + methodology research. Future plug-in: sharpen VRP's RV baseline.
- **OI-defined walls** — more observable but no historical chains stored; deferred for GEX-defined persisted walls.
- **Email background (dark vs light)** + full "analysis into the email" — Phase 11 (RPT-01..05).
- **Front-vs-back VRP** (term-VRP) — borderline new compute; revisit if single VRP read is insufficient.

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/10-dashboard-restructure-local-only/10-CONTEXT|10-CONTEXT]]

<!-- LINKS:END -->
