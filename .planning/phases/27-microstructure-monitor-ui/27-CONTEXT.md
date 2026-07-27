# Phase 27: Microstructure Monitor UI - Context

**Gathered:** 2026-07-26
**Status:** Ready for planning
**Source:** `.planning/notes/microstructure-monitor-design.md` (canonical design) + `.planning/todos/pending/email-boilerplate-cut.md` + Adam scope decision (plan-only, review before build)

<domain>
## Phase Boundary

Build the UI/consumption layer that surfaces Phase 26's already-built severity ranks + hysteresis alert engine (`engine/monitor/`). Two surfaces: the **dashboard** becomes state-shaped (a distribution board showing current abnormality of everything), the **email** becomes event-shaped (fires only on band entries/escalations). NO new signals, NO new computations — this consumes the monitor engine. Descriptive only; tier-2 conditional base rates stay DEFERRED. `app.py` currently has ZERO monitor wiring — this is greenfield integration.

**Requirements note:** Phase 27 has no formal REQUIREMENTS.md IDs (the monitor reframe was added 2026-07-23 without new requirement IDs). Success criteria below are derived from the canonical design doc and are the acceptance bar for this phase.
</domain>

<decisions>
## Locked Design Decisions (from microstructure-monitor-design.md — do NOT re-litigate)

### Dashboard architecture: scan → interrogate → contextualize
- **Landing = distribution board.** One row per metric×ticker (~15 rows). Each row: a horizontal **percentile strip**, **today's dot**, **deep + 1yr rank** both marked, and a **10-session trail** (the trail is load-bearing — motion-vs-parked is the whole microstructure question).
- **Row inventory v1:** VRP (deep + 1yr), 25Δ skew, 25Δ fly, term ratios (SPY only — no VXN/RVX 9D/3M siblings), 5d surface-evolution level & RMS.
- **Net-GEX sign = a state CHIP, not a ranked row** (GEX-as-candidate decision, 2026-07-22). IWM–SPY VRP spread is a deferred candidate row (seed) — NOT in v1.
- **Click a row → evidence panel:** metric-history chart with bands drawn + the *mechanism view* — skew row → smile overlay (today vs 5d); surface-evolution row → existing diff surface; VRP row → implied-vs-realized pair. Re-anchor existing 3D/surface work, do not demote it.
- **Third layer unchanged:** existing Surfaces / Positioning exploration tabs stay.
- **Chrome:** remove the current AMPLIFYING/MIXED risk bar (it led with demoted GEX). Freshness banner shrinks to a dot unless data is stale.

### Email = event-shaped
- Body = band entries + escalations only; near-empty ("nothing unusual") on normal days.
- Cut methodology caveat banner + glossary + deep-methodology footer → replace with ONE permanent "Methodology" link.
- Drop OI-by-expiry table + key-levels block from email (dashboard-only now).
- Add Δ-vs-yesterday context to what remains.

### Severity semantics (already built in Phase 26 — consume, don't rebuild)
- ECDF percentile ranks on levels AND |k-day changes|; dual lookback (deep + 1yr); alert on either.
- Transition-with-hysteresis alerts, false-alarm-budgeted bands.
- **Credibility floors:** chain metrics (~50 sessions since 2026-05) get percentiles labeled with n and can't fire deep-history claims until enough depth; VRP rides ~10yr vol-index history. Reuse Phase 26's credibility gating — do not show ranks the data can't support.

### Claude's Discretion
Exact Streamlit layout primitives (columns/containers/plotly strips), styling, how the 10-session trail is drawn (sparkline vs strip overlay), evidence-panel navigation mechanism (st.session_state row selection). USE the developing-with-streamlit skill.
</decisions>

<success_criteria>
## Success Criteria (derived — the acceptance bar)

1. Dashboard lands on a distribution board: ~15 metric×ticker rows (VRP deep+1yr, 25Δ skew, 25Δ fly, term-ratio SPY-only, 5d surface-evo level & RMS), each rendering a percentile strip + today's dot + deep & 1yr rank marks + a 10-session trail, sourced from `engine/monitor/` ranks.
2. Clicking/selecting a row opens an evidence panel with the metric-history chart (bands drawn) + the correct mechanism view for that metric type (smile overlay / diff surface / IV-vs-RV pair).
3. Net-GEX sign renders as a state chip (not a ranked row); Surfaces/Positioning tabs remain functional; the AMPLIFYING/MIXED risk bar is gone; freshness banner is a dot unless stale.
4. The daily email is event-shaped: renders band entries + escalations only, is near-empty on a no-alert day, methodology boilerplate/glossary/footer replaced by a single link, OI table + key-levels removed, Δ-vs-yesterday context present.
5. Credibility floors respected: rows/alerts for shallow chain metrics are labeled with n and cannot assert deep-history rarity until sufficient depth (reuses Phase 26 gating).
6. No new signals/computations introduced; tier-2 conditional base rates NOT added (deferred). `pytest engine/tests` stays 100% green (baseline 465); any new logic (email event-shaping, rank-to-row adapters) is tested.
7. `streamlit run app.py` launches without error and the board renders for SPY/QQQ/IWM.
</success_criteria>

<canonical_refs>
## Canonical References
- `.planning/notes/microstructure-monitor-design.md` — THE design contract
- `.planning/todos/pending/email-boilerplate-cut.md` — email cut specifics
- `engine/monitor/` (schema, ranker, hysteresis, monitor_store, calibration) — Phase 26 engine to consume
- `engine/report/report.py` — email builder to remodel; `engine/report/card_model.py` — card/read source
- `engine/surface/surface_interactive.py` (smile/diff payloads), `engine/vol/vrp_history.py` (IV-vs-RV) — mechanism-view sources to re-anchor
- `app.py` — dashboard to restructure (currently no monitor wiring)
- Streamlit work MUST use the `developing-with-streamlit` skill.
</canonical_refs>

<deferred>
## Deferred (NOT in v1)
- Tier-2 conditional base rates / measured-consequence annotations (await validation on deep history).
- IWM–SPY VRP spread row (candidate seed).
- Any new signal or predictive/prescriptive claim.
</deferred>

---

*Phase: 27-microstructure-monitor-ui*
*Context gathered: 2026-07-26 — design doc + Adam plan-only scope decision*

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
<!-- LINKS:END -->
