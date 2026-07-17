# Phase 18: 3-Page Reorg + Email Parity + Gating - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-23
**Phase:** 18-3-page-reorg-email-parity-gating
**Areas discussed:** 3-page navigation structure, page-1 snapshot hierarchy, history gating UX, email parity contract

---

## 3-page navigation structure

| Option | Description | Selected |
|--------|-------------|----------|
| Top-level tabs across the main body | Primary page switch pattern | ✓ |
| Sidebar radio selector | Cleaner chrome but less glanceable | |
| Segmented control under ticker selector | Compact but custom wiring | |

**User's choice:** Top-level tabs across the main body.
**Notes:** This keeps switching obvious and low-friction for daily use.

| Option | Description | Selected |
|--------|-------------|----------|
| Page 2 (Surfaces) as a sub-section | Evolution grouped with surface workflows | ✓ |
| Page 1 snapshot context | Keep evolution near cards | |
| Page 3 positioning | Tie evolution to dealer mechanics | |

**User's choice:** Evolution on page 2.
**Notes:** Treated as part of surface analysis, not top snapshot.

| Option | Description | Selected |
|--------|-------------|----------|
| All three ticker cards by default | Cross-index context first | ✓ |
| Single default ticker (SPY) | Focused view first | |
| Remember last active ticker | Personalized default | |

**User's choice:** All three by default.
**Notes:** Supports cross-market comparison in the lead view.

| Option | Description | Selected |
|--------|-------------|----------|
| Single ticker at a time with toggle | Cleaner heavy-chart interaction | ✓ |
| Render all tickers at once | Full parallel view | |
| Follow page-1 selection behavior | Coupled behavior | |

**User's choice:** Single ticker at a time for pages 2 and 3.
**Notes:** Keeps heavy visual sections readable.

---

## Page-1 snapshot hierarchy

| Option | Description | Selected |
|--------|-------------|----------|
| Regime-first compact set | VRP, VIX Term, IV30/EM, Skew+Fly, Net GEX, γ-flip | ✓ |
| Current broader compact set | Keep more top-line rows | |
| OI-first compact set | Promote OI into top six | |

**User's choice:** Regime-first compact set.
**Notes:** Aligns with longer-horizon conviction context.

| Option | Description | Selected |
|--------|-------------|----------|
| Include cross-index summary block | One paragraph above cards | ✓ |
| Per-ticker only | No global block | |
| One-line banner only | Minimal global summary | |

**User's choice:** Include cross-index summary block.
**Notes:** Desired to frame market context before detail.

| Option | Description | Selected |
|--------|-------------|----------|
| OI teaser on page 1; full context page 3 | Preserve hierarchy | ✓ |
| Full OI table on page 1 | Maximum visibility | |
| Hide OI from page 1 entirely | Strict separation | |

**User's choice:** OI teaser only on page 1.
**Notes:** Full mechanics remain in positioning page.

| Option | Description | Selected |
|--------|-------------|----------|
| Keep trust tags visible by default | Immediate confidence framing | ✓ |
| Hide tags by default | Cleaner look | |
| Show tags only for model fields | Partial tagging | |

**User's choice:** Keep tags visible by default.
**Notes:** Trust framing should stay explicit.

---

## History gating UX

| Option | Description | Selected |
|--------|-------------|----------|
| Show metric with explicit building state | Keep visibility with context | ✓ |
| Hide until threshold met | Strict readiness gating | |
| Placeholder without counts | Minimal gating text | |

**User's choice:** Show with explicit "building to N sessions."
**Notes:** Visibility preferred over silent omission.

| Option | Description | Selected |
|--------|-------------|----------|
| Keep section visible with clear caption | "Needs ≥N sessions" state | ✓ |
| Hide whole section | Remove pre-ready sections | |
| Blank chart shell + warning | Show scaffold | |

**User's choice:** Keep visible with clear caption, no empty chart.
**Notes:** Avoids confusion from blank visuals.

| Option | Description | Selected |
|--------|-------------|----------|
| Metric-specific thresholds + current count | Precise readiness feedback | ✓ |
| Unified threshold message | Simpler copy | |
| No counts | Generic insufficient-history note | |

**User's choice:** Metric-specific thresholds with actual counts.
**Notes:** User wants explicit context on readiness.

| Option | Description | Selected |
|--------|-------------|----------|
| Building rows for card metrics + omit panel sections | Hybrid cold-start behavior | ✓ |
| Omit all history-dependent content | Strict omission | |
| Keep rows with placeholders everywhere | Fully visible placeholders | |

**User's choice:** Hybrid behavior (building rows + omit panel sections).
**Notes:** Keeps email informative while avoiding empty structures.

---

## Email parity contract

| Option | Description | Selected |
|--------|-------------|----------|
| Strict parity | Same fields/order/format/rounding | ✓ |
| Value parity only | Format may differ | |
| Core parity only | Secondary divergence allowed | |

**User's choice:** Strict parity.
**Notes:** Page 1 and email must stay aligned.

| Option | Description | Selected |
|--------|-------------|----------|
| One canonical pipeline (`build_card_fields`) | No per-surface field assembly | ✓ |
| Dashboard local transforms allowed | Small dashboard differences | |
| Email local transforms allowed | Small email differences | |

**User's choice:** Canonical pipeline only.
**Notes:** Explicitly rejected separate field assembly paths.

| Option | Description | Selected |
|--------|-------------|----------|
| Omit unavailable rows on both surfaces | Symmetric omission | ✓ |
| Show N/A row on both | Symmetric placeholders | |

**User's choice:** Omit unavailable rows on both surfaces.
**Notes:** Clarified after confusion in prior prompt.

| Option | Description | Selected |
|--------|-------------|----------|
| Hard failure gate for mismatches | CI-blocking parity contract | |
| Warning-only parity checks | Non-blocking visibility | ✓ |

**User's choice:** "should just be a warning."
**Notes:** Mismatch handling should alert but not block this phase.

---

## Claude's Discretion

- Final wording and placement for page-1 cross-index summary.
- Warning-channel implementation details for parity drift signaling.

## Deferred Ideas

- Potential upgrade of parity mismatches from warning-only to hard-fail in a later hardening pass.
