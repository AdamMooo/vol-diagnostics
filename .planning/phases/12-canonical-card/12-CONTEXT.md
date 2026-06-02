# Phase 12: Canonical Card - Context

**Gathered:** 2026-06-01
**Status:** Ready for planning
**Source:** Conversational discuss (resume-work session 2026-06-01) — design locked with user

<domain>
## Phase Boundary

Make the per-ticker card a single source of truth shared by the daily email (`gex/report.py`) and the Streamlit dashboard (`streamlit_app.py`) so the two stop drifting, and enrich it with VRP, scalar vs-yesterday deltas, and clear OI-vs-GEX wall labelling. Single-snapshot (plus at most yesterday) only — no new accumulation-dependent metrics.

**In scope:** the per-ticker card/regime-card in both surfaces, plus the shared field/value layer that feeds them.
**Out of scope:** the dashboard's 3D Surface page + Compare tab (left untouched), the email PNG attachments (Phase 13), accumulation gating (Phase 14).
</domain>

<decisions>
## Implementation Decisions

### Canonical card = the richer EMAIL card, ported TO the dashboard (CARD-01)
- Email is the product; it sets the canonical shape. The dashboard regime card is currently leaner (Spot, Net GEX, γ-flip, Skew, IV30 + a small obs line) and must be brought up to the email card's field set.
- "Single source of truth" = a shared field/value layer (e.g. a `build_card_fields(...)` helper or small card-model module) that returns the ordered list of (label, formatted value, sign/kind) for ONE ticker. Both renderers iterate that list. The two renderers keep their own HTML flavor — email = inline-styled table cells (`_kv_cell`/`_kv_table` in `report.py`), dashboard = the existing CSS-class markdown card in `streamlit_app.py` — but the field set, values, formatting, and deltas come from the shared layer. This is what prevents drift; do NOT try to share the literal HTML.
- Current email card field inventory (the target set): LEFT = Spot, Day %, IV30 / 1d σ, γ-flip, vs γ-flip; RIGHT = Net GEX, Hedge Shares/$1, Skew (25Δ), Call Wall, Put Wall, Range, OI Call Wall, OI Put Wall. Plus VRP (CARD-02) and deltas (CARD-03).

### VRP onto the card (CARD-02)
- Add VRP (IV30 − RV20) as a scalar field. It is already computed by `compute_ticker` (`data["vrp"]`, a decimal fraction; display in pp). Currently shown in the dashboard's Calculus+VRP tab but ENTIRELY ABSENT from the email — this closes that gap.
- VRP scalar only here (the sparkline + percentile are history-dependent and belong to Phase 14 gating, not this card).

### Scalar vs-yesterday deltas (CARD-03)
- iv30, front_skew (25Δ), and net_gex each show a signed 1-session delta vs the prior stored snapshot, as a raw signed number appended to the value (e.g. `18.5% (+0.8)`, `-3.2pp (-0.4)`, `+1.20B (+0.15)`).
- This is the honest scalar change — explicitly NOT the retired categorical "positive/negative/neutral" vs-yesterday badge (which was killed because the OI roll dominated a 5% threshold). No threshold, no label — just the number.
- Prior values come from the existing GEX snapshot store `out/gex_snapshots.parquet` (the ~15-day store). Use `gex/validation.py` helpers (`load_history` / `load_yesterday`) — most-recent prior session row strictly before the current date, per ticker.
- VERIFIED snapshot columns today: `date, ticker, spot, net_gex, gamma_regime, zero_gamma_level, call_wall, put_wall, vanna_exposure, front_skew, put_25d_iv, call_50d_iv`. So **net_gex and front_skew deltas work immediately** (already persisted). **iv30 is NOT persisted** — CARD-03's iv30 delta requires adding iv30 to the `save_snapshot` schema (follow the existing rv20/vrp schema-extension precedent, INFRA-02; old snapshots must still load safely). iv30 deltas only begin accruing for sessions saved AFTER that schema change — until a prior row carries iv30, the iv30 delta is omitted.
- Delta gracefully omits its suffix (renders just the base value, no parens) when no prior row exists OR the prior column is absent/NaN. Never render `(+nan)`, `(+0.0)`-from-missing, or a delta against a fabricated zero.

### OI-vs-GEX wall labelling (CARD-04)
- GEX-derived walls (Call Wall / Put Wall) are model constructs (assume dealers net short — Garleanu et al.); OI walls (OI Call Wall / OI Put Wall) are assumption-free raw open interest.
- Label GEX walls "(model)" and OI walls "(raw OI)" with a one-line inline distinction, consistently in BOTH email and dashboard, so the two wall types are never confused.

### Constraints carried from the project
- No hand-tuned cutoffs (load-bearing project rule). The deltas are raw numbers — no magnitude threshold.
- Email card values must inherit client light/dark theme (no card background; the existing `_kv_cell` intentionally ignores per-value color and relies on the +/- sign). Keep that behavior.
- Windows paths via pathlib / existing helpers.
- No comments unless the *why* is non-obvious; small diffs; no surrounding cleanup.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The two card renderers (the things being unified)
- `gex/report.py` — `_ticker_card(r)` builds the email card; `_kv_cell`/`_kv_table` are the row helpers; `_wall_value`, `_fmt_*` are the formatters. The richer card = canonical shape.
- `streamlit_app.py` — `render_regime_card(col, summary, spot)` + `_derive_observations` build the dashboard regime card (currently leaner). `render_regime_cards` drives the row of 3.

### Where the values come from
- `gex/compute.py` — `compute_ticker(ticker)` is the single pipeline producing the `summary` dict + `vrp`/`rv20`/`term_structure` used by both surfaces.
- `gex/validation.py` — parquet snapshot store: `save_snapshot`, `load_history`, `load_yesterday`. Source of the prior-session values for CARD-03 deltas. Confirm which columns are persisted (net_gex, front_skew present; verify iv30).
- `gex/vol_metrics.py` — `vrp_headline` and the VRP/skew/term computations.
- `gex/config.py` — `PALETTE` shared token set.

### Shared palette / styling
- `config.PALETTE` is already the single source of truth for color tokens shared by email + dashboard (established Phase 10/11). Reuse it.
</canonical_refs>

<specifics>
## Specific Ideas

- Prefer a small shared helper (e.g. `gex/card_model.py` with `build_card_fields(summary, prior_summary, extras) -> list[CardField]`) over duplicating the field list in both renderers. The renderers map `CardField` → their own HTML. This is the cleanest "single source of truth" that respects the two different output targets.
- A `CardField` carries: label, formatted value string (already including any delta suffix), and a sign hint (for the email's +/- color reliance / dashboard accent). Formatting (pp, B, %, signed) lives in the shared layer so email and dashboard format identically.
- Deltas: compute once in the shared layer from (today_summary, prior_summary). Keep the formatting identical across surfaces.
</specifics>

<deferred>
## Deferred Ideas

- VRP sparkline + VRP/skew percentiles — history-dependent; Phase 14 gating, not this card.
- The 1-day ΔIV surface PNGs — Phase 13.
- "Large OI blocks expiring soon" — deferred from v3.4 entirely (needs parameter-free design).
</deferred>

---

*Phase: 12-canonical-card*
*Context gathered: 2026-06-01 via conversational discuss (resume-work session)*

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
