# Phase 18: 3-Page Reorg + Email Parity + Gating - Context

**Gathered:** 2026-06-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Reorganize the dashboard into a three-page structure that is more useful for a
professional, longer-horizon index-overlay PM: page 1 leads with regime context
(VRP + term + snapshot), page 2 contains surface workflows (including evolution),
and page 3 contains dealer-positioning mechanics (GEX + OI depth). The same
canonical card numbers must drive both page 1 and daily email, while
history-dependent elements remain visible but explicitly gated as "building"
until enough sessions exist.

</domain>

<decisions>
## Implementation Decisions

### 3-page navigation structure
- **D-01:** Use **top-level tabs** as the primary page switch control.
- **D-02:** Place **Evolution on page 2** as a surface sub-section.
- **D-03:** Page 1 defaults to **all three ticker cards** (SPY/QQQ/IWM) for
  cross-index context.
- **D-04:** Pages 2 and 3 remain **single-ticker at a time** with a fast ticker
  toggle for heavy charts.

### Page-1 snapshot hierarchy (PM-facing)
- **D-05:** Page-1 compact card set is **regime-first**:
  VRP, VIX Term, IV30/EM, Skew+25Δ Fly, Net GEX, γ-flip.
- **D-06:** Add one **cross-index summary block** above ticker cards.
- **D-07:** Show only a **short OI/positioning teaser** on page 1; full OI table
  and GEX mechanics stay on page 3.
- **D-08:** Keep **trust tags visible by default** on page-1 labels.

### History gating UX
- **D-09:** For underpowered history, show metric with explicit
  **"building to N sessions"** state whenever possible.
- **D-10:** For gated chart sections, keep section visible with a clear
  **"needs ≥N sessions"** caption and no empty chart body.
- **D-11:** Use **metric-specific thresholds + actual current count** (not one
  generic threshold message).
- **D-12:** In email cold-start mode, show **building rows** for card-level
  history metrics but omit sections requiring full panel/chart context.

### Email parity contract
- **D-13:** Enforce **strict parity** for shared page-1/email fields: same field
  set, ordering, rounding, and formatting.
- **D-14:** Both surfaces must render from the same canonical pipeline:
  `build_card_fields()` output only (no per-surface field assembly).
- **D-15:** If a field is unavailable by design (e.g., VIX Term for QQQ/IWM),
  **omit it on both surfaces**.
- **D-16:** Parity mismatches should be surfaced as **warning-grade checks** (not
  hard test-fail gate for this phase).

### Claude's Discretion
- Wording for the cross-index summary paragraph and page-1 teaser copy.
- Exact warning mechanism for parity drift reporting (location + phrasing), while
  preserving D-13 through D-15.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and milestone constraints
- `.planning/ROADMAP.md` — Phase 18 goal/success criteria (VIEW-06/07, CUT-02,
  PAR-01, GATE-01/02).
- `.planning/REQUIREMENTS.md` — v3.5 interpretability and parity constraints.
- `.planning/STATE.md` — latest locked decisions and continuity notes.

### Canonical card and parity seam
- `engine/report/card_model.py` — `CardField`, `build_card_fields()`,
  `split_compact_fields()`, trust-tag assignment; single field contract.
- `engine/report/report.py` — email renderer consuming canonical fields and
  current omission behavior.
- `app.py` — dashboard page composition and card rendering entry points.

### Compute and history/gating inputs
- `engine/compute.py` — summary payload feeding both dashboard and email.
- `engine/data/validation.py` — snapshot history semantics used by card-level
  history reads.
- `engine/data/oi_history.py` — OI context/history for table-first positioning.
- `engine/surface/surface_history.py` — stored-session semantics for surface and
  evolution availability.

### Prior locked phase decisions (must carry forward)
- `.planning/phases/16-vrp-percentile/16-CONTEXT.md` — VRP series consistency +
  cold-start handling.
- `.planning/phases/16.5-oi-depth-expansion/16.5-CONTEXT.md` — table-first OI
  context and expiry-share conventions.
- `.planning/phases/17-term-structure-regime/17-CONTEXT.md` — SPY-only term
  ratio availability and omission logic for QQQ/IWM.
- `.planning/phases/17.1-convexity-expected-move/17.1-CONTEXT.md` — IV30/EM and
  25Δ Fly semantics in canonical cards.
- `.planning/phases/18.1-dashboard-trust-and-clarity-hardening/18.1-CONTEXT.md`
  — trust tags, 14-DTE primary framing, and quick/deep methods framing.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app.py` already has tabbed page structure (`Surface`, `Evolution`,
  `Positioning`) and can be re-grouped to 3-page architecture.
- `engine/report/card_model.py` already centralizes card values, trust tags, and
  compact-vs-detail splitting.
- `engine/report/report.py` already renders ticker cards from canonical card
  fields and supports omission of unavailable sections.

### Established Patterns
- Summary values are precomputed in `engine/compute.py`; renderers do not perform
  heavy calculations or I/O.
- Cold-start messaging is explicit ("building"/"need ≥N sessions"), not silent.
- OI interpretation is table-first and history-aware; GEX framing remains model
  construct with explicit caveat.

### Integration Points
- `app.py`: page split and placement (page 1 snapshot/cross-index summary, page 2
  surfaces+evolution, page 3 positioning/GEX/OI).
- `engine/report/card_model.py`: compact field priority order for page-1-first
  information hierarchy.
- `engine/report/report.py`: strict parity enforcement surface + warning pathway
  when drift is detected.

</code_context>

<specifics>
## Specific Ideas

- Page 1 should read like a **regime briefing** for high-conviction, medium-term
  overlay decisions, not an intraday panel.
- Cross-index summary should explicitly help compare SPY/QQQ/IWM context before
  drilling into deeper pages.
- Keep page-1 OI context to a teaser and route full explanatory mechanics to page
  3 to preserve clarity.

</specifics>

<deferred>
## Deferred Ideas

- Revisit parity checks as hard-fail test gate in a later hardening pass after
  tomorrow's review.

</deferred>

---

*Phase: 18-3-page-reorg-email-parity-gating*
*Context gathered: 2026-06-23*
