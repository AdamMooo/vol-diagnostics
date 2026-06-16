# Page-1 Card — Canonical Definition Spec

**Created:** 2026-06-16 · **Status:** authoritative contract for Phases 17 / 17.1 / 18
**Purpose:** Freeze the page-1 card's field set, order, exact per-field definitions, and
footnote-weight rules — so "raw numbers, PM judges" stays honest. 17 / 17.1 / 18 implement
*against this doc*. Changing a field's basis means changing this doc first.

Governing requirement: **VIEW-07 — page-1 is simplified for at-a-glance readability.**
Every add below is footnote-weight or it doesn't ship.

---

## 1. Page split (Phase 18 reorg)

The current `build_card_fields` is one flat 14-field list. Phase 18 splits it:

| Page | Fields | Role |
|------|--------|------|
| **1 — Vol Regime** | the 6 regime metrics below + freshness + qualifiers | lead at-a-glance read |
| **2 — Surfaces** | 3D surface, skew/term detail, ΔIV | strike×tenor inspection |
| **3 — GEX** | γ-flip, vs γ-flip, Net GEX, hedge shares, walls (model + OI), range/pin | path / mechanical-flow context |

GEX fields are **demoted, not deleted** (VIEW-06). Page-3 GEX keeps its `(model)` / `(raw OI)`
labels and gains a calc-timestamp; walls are probabilistic zones, never hard levels.

---

## 2. Page-1 field order (LOCKED — decision-sequence, not model taxonomy)

```
1. IV30            ← how much vol is priced
2. VRP + %ile      ← is that richness real?           (Phase 16 ✅)
3. Expected Move   ← how large is the near move?      (Phase 17.1 — see §4)
4. Term Structure  ← where on the curve / front stress (Phase 17)
5. Skew (25Δ RR)   ← directional asymmetry            (built)
6. Fly (25Δ)       ← tail / convexity demand          (Phase 17.1)
   ── footnotes ──
   freshness strip · reliability cue · event flag
```

Rationale: "should I care about selling premium here?" (1–2) → "how big / what tenor?" (3–4)
→ "what shape?" (5–6). Expected move precedes term because it anchors overwrite sizing and
strike-distance intuition.

---

## 3. Per-field canonical definitions

Status: **FROZEN** = verified against current code, do not change without editing this doc.
**TARGET** = convention the unbuilt phase must implement to.

| # | Field | Definition / formula | Basis & units | Sign convention | Source · timescale | Status · code |
|---|-------|----------------------|---------------|-----------------|--------------------|---------------|
| 1 | IV30 | CBOE-published 30-day constant-maturity IV, taken directly (not our interpolation) | % annualized vol | n/a | CBOE delayed quote · **~15-min delayed** | FROZEN · `compute.py` `summary["iv30"]` |
| 2 | VRP + %ile | `vol_index − RV20`, ranked by `percentileofscore(kind="rank")` over ≤252-session series built from the *same* `vol_index − RV20` definition | vol points (pp); percentile 0–100 | + = vol rich (implied over realized) | vol-index close (VIX/VXN/RVX) + yfinance closes · **EOD** | FROZEN · `vrp_history.py`, `_fmt_vrp` |
| 2a | RV20 | std of 20 most-recent daily log returns, ×√252, ddof=1 | annualized, decimal | n/a | yfinance closes · EOD | FROZEN · `vol_metrics.compute_rv20` |
| 3 | Expected Move | **front-expiry ATM-straddle implied move**, expiry/DTE labeled — see §4 for the basis decision | ±% of spot (and/or ± price) | n/a | option chain · ~15-min delayed | TARGET · Phase 17.1 |
| 4 | Term Structure | raw ratios `VIX9D/VIX` and `VIX/VIX3M` (SPY); QQQ/IWM degrade to whatever CBOE publishes, else "N/A — single point" | dimensionless ratio | >1 front-rich = backwardation/stress; <1 = contango/calm | CBOE vol indices · EOD | TARGET · Phase 17 (TERM-01/02) |
| 5 | Skew (25Δ RR) | front-month (≤45 DTE) `25Δ put_iv − 25Δ call_iv` | vol points (pp) | + = puts richer (downside bid) | option chain · ~15-min delayed | FROZEN · `vol_metrics.compute_skew_25d` `front_skew` |
| 6 | Fly (25Δ) | front-month `½(25Δ put_iv + 25Δ call_iv) − ATM_iv` | vol points (pp) | + = wings richer (tail demand) | option chain · ~15-min delayed | TARGET · Phase 17.1 (SHAPE-01) |

ATM IV (for Fly) = `compute_term_structure` front-expiry ATM point. 25Δ legs reuse
`compute_skew_25d`'s exact delta-nearest selection — Fly and Skew **must** draw the same
25Δ legs so they're mutually consistent.

---

## 4. DECISION for Phase 17.1 — which "expected move"?

Two distinct things exist; do not conflate:

- **A. existing `iv30/√252`** (`card_model.py:78`) — a generic **1-day 1σ** move from IV30.
  Always 1-day, IV-approximation, event-blind.
- **B. front-expiry ATM-straddle move** (17.1 proposal) — to-expiry, straddle-implied,
  expiry-anchored, event-sensitive.

**Recommendation (resolve at 17.1 plan time):** **B becomes the page-1 "Expected Move"**
(it anchors overwrite sizing and strike distance, expiry-labeled). A's `1d σ` is either
dropped from page 1 or demoted to page-2 detail — it should NOT sit on page 1 labeled
ambiguously next to B. Whichever is chosen, the label states expiry + formula explicitly.

---

## 5. Footnote-weight adds (trustworthiness, not new views)

All three are muted, sub-line, never compete visually with the 6 metrics (VIEW-07).

- **Freshness strip** → Phase 18. Must be **per-source honest** — the card mixes timescales:
  IV30/skew/fly/expected-move are ~15-min delayed; VRP/RV20/term are EOD; OI walls are T+1.
  A single "as of" would itself mislead. Show the governing timestamp(s) + underlying spot move
  since the read. This is the precision-illusion guard.
- **Reliability cue** → Phase 18. **Derive from existing Phase 8 infra** (`coverage_mask`,
  fit residuals, QA gate) — do NOT build a new metric. When skew/fly/expected-move are computed
  off thin/stale wings, the card quietly flags lower confidence.
- **Event flag** → Phase 17.1 (folded in, per decision 2026-06-16). Binary "front expiry spans a
  known macro date (FOMC / CPI / NFP / OPEX)" marker, footnote-weight. Index ETFs only → no
  earnings, small fixed macro calendar. **No event study, no historical analysis** (the removed
  event-study direction is not reintroduced).

---

## 6. Keep / Add / Drop / Reorder summary

| Action | Item |
|--------|------|
| **Keep** | IV30, VRP+%ile, Skew (25Δ RR) — already canonical |
| **Add** | Term structure (P17), Fly + front-expiry Expected Move (P17.1), freshness + reliability (P18), event flag (P17.1) |
| **Drop from page 1** | GEX block → page 3; ambiguous `1d σ` → resolve per §4 |
| **Reorder** | to §2 sequence (lock target now; 17.1/18 implement) |

---

## 7. Anti-creep guardrails (do not reintroduce on page 1)
Categorical regime labels · realized cone · risk-neutral density · put/call ratios · VVIX ·
event *study* (vs the binary flag) · dealer-hedging causal claims · intraday. All previously
scoped out; page 1 stays raw-number + footnote-qualifier only.

---

*Referenced by: Phase 17 CONTEXT, Phase 17.1 CONTEXT, Phase 18 CONTEXT. Edit this doc before
changing any field basis.*

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
