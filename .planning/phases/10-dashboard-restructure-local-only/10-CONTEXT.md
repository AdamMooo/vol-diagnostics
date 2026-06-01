# Phase 10: Dashboard Restructure (local only) - Context

**Gathered:** 2026-05-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Restructure the **local** Streamlit dashboard (`streamlit_app.py`) around the surface calculus. Confirm the 4-tab layout, merge Skew+Term into a VRP-led "Calculus" tab, add an Evolution time-series tab, pivot the Flow tab to OI-led "Positioning", add stored-vs-stored surface comparison, and re-skin to a restrained **dark / Bloomberg-like** palette with honest coverage holes.

**No new vol computation.** Everything renders data already produced by `compute_ticker`, the history store, and the Phase 9 evolution engine. GARCH and any new modeling are explicitly out. Wiring this analysis into the daily **email is Phase 11** (RPT-01..05) — Phase 10 only makes the analysis email-ready (headless, reusable).

This phase clarifies HOW to render what already exists. New capabilities belong in other phases.
</domain>

<decisions>
## Implementation Decisions

### Tab architecture (VIEW-01)
- **D-01:** Final 4 tabs = **Surface · Calculus+VRP · Evolution · Positioning**. The code is *already* 4 tabs (`Surface, Skew, Term Structure, Flow Context`) — the standalone Carry tab was dropped in the Phase 7 refactor (`ad8b017`), so the roadmap's "5→4" is stale wording. The real move: merge Skew+Term (→3) + add the Evolution view (→4). Nothing is cut; VRP is rehomed; GEX is demoted but retained.
- **D-02:** The **Surface** tab keeps its `Today` / `Compare` sub-tabs (Today = live 3D surface + trust readout; Compare = two-date Δ-surface, see D-10/D-11).

### Calculus + VRP tab (VIEW-01, VIEW-02)
- **D-03:** The 3D surface owns **shape**. This merged tab carries only what the surface *can't* show — so it is **VRP-led + a scalar strip**, NOT a gallery of 2D surface slices. **Drop** the current 2D smile redraw (`plot_skew_25d_current`) and the ATM-term redraw (`plot_term_structure`) — both duplicate the surface (user: "I do not really love my skew and term structure tab as it is already shown in the 3d surface").
- **D-04:** VRP headline (the "real value" the user asked for) = `IV30 − RV20` shown big + 30-session **percentile** + a small **VRP sparkline** (is richness building or fading) + a one-line plain read (e.g. "vol rich +8.7pp, 82nd %ile — premium-selling favored, protection is expensive"). All from the existing history store (`iv30`/`rv20`/`vrp` persisted since Phase 6 INFRA-02). **No new vol modeling.**
- **D-05:** Scalar strip beneath VRP: **front skew** (pp + %ile), **term spread** (pp + %ile), **cross-ticker 25Δ RR** (SPY/QQQ/IWM). Each with percentile context; the cross-ticker RR is the one genuinely-not-on-a-single-surface item kept as a real comparison.
- **D-06:** Removals (VIEW-02, mostly pre-locked): the carry/VRP gauge (`plot_carry_vrp`), the rolling **25Δ RR-history chart** (the `skew_fig` block in the Skew tab), and the **strike-GEX bar charts** (`plot_strike_gex` is repurposed to OI — see D-08).

### Positioning tab — was "Flow Context" (VIEW-02)
- **D-07:** Pivot from GEX-led to **OI-led** (observable, no dealer assumption). GEX is retained **only** for: net dealer exposure (sign + magnitude), the **γ-flip** level, and the call/put **gamma walls**. Rationale (user): "GEX kinda makes it less nice… more ideal to have OI" + "make it more accurate and real… not too many assumptions." GEX needs the dealer-net-short assumption (Garleanu et al.); OI is the assumption-free version. Cross-ticker nuance to honor in copy: SPY GEX cleanest, **IWM trust OI over GEX**.
- **D-08:** Two charts. **Chart A** = pure **OI by strike** (call/put OI; same visual shape as today's `plot_strike_gex` bar chart, but plotting OI not GEX — zero assumptions). **Chart B** = ~2-month (~42-session) **price (spot) time-series** with **call wall · γ-flip · put wall** drawn as level lines, so the user reads at a glance how far spot sits from each. Walls/flip are **GEX-defined** and are **already persisted daily** in `out/gex_snapshots.parquet` (`call_wall`, `put_wall`, `zero_gamma_level`, `spot`), so the 2-month history is real on day one. Label the levels "model · assumes dealers net short." γ-flip is model-based either way (no OI equivalent).
- **D-09:** The gamma profile (`plot_gamma_profile`) is **demoted to an expander** ("how the flip/walls are derived") — it's the mechanism, not a daily signal.
- **Rationale captured (importance ranking for SPY/QQQ/IWM):** OI (highest observable) > net GEX (highest interpretive, if you accept the assumption) > γ-flip (watch-level) > gamma walls (lore) > gamma profile (mechanism). **This automates the user's manual TradingView wall/flip line-drawing.**

### Evolution tab (VIEW-04, EVOL-05)
- **D-10:** **Horizon radio (5 / 10 / 20, default 5d)** → **4 small-multiples** (level / rms / skew_change / term_change), each overlaying **SPY·QQQ·IWM**, with a zero line and a pp y-axis. Cross-ticker divergence (e.g. IWM moving alone) is visible per dimension — directly serves EVOL-05. Reads `load_evolution(ticker, horizon, days)`; accumulates forward, seeded by the EVOL-06 backfill.

### Two-date compare (VIEW-03)
- **D-11:** The Surface→Compare sub-tab uses **two relative-horizon dropdowns** `{live, 1d, 5d, 10d, 20d, 30d, 60d}`, resolved to **actually-stored trading sessions** via `nth_trading_day_back` (the same helper the evolution engine uses — NOT calendar arithmetic). Compare any A→B (live-vs-5d, 10d-vs-5d, …). Default **live vs 5d**. Dropdown self-limits to available history (60d greyed until enough accumulates).
- **D-12:** Compare is **visual-only** — the 3D Δ-surface (`plot_iv_change_surface`) for the chosen pair, mask-intersected (today ∩ prior, as the existing comparator already does). **Do NOT** show per-pair scalars: the rigorous level/rms/skew/term scalars live **only** in the Evolution tab (rolling-mean baseline). This keeps roles distinct and avoids two differently-computed "skew change" numbers. 1d is the noisiest pair (expiry roll + quote noise — the hazard that retired the vs-yesterday badge); kept but least informative, signal starts at 5d+.

### Palette & holes (VIEW-05)
- **D-13:** **Dark theme retained — Bloomberg-like.** (User initially picked light-everywhere, then reversed: "I do enjoy the darker themes… better and more Bloomberg-like.") This rehabilitates the amber accent — Bloomberg's signature is amber-on-black — so **refine** the current neon orange (`#f59e0b`) into a tasteful restrained terminal-amber, **mute** the neon green/red sign colors, keep the dense dark layout. Keep `plotly_dark`-style charts; keep Viridis surface (planner to sanity-check on dark, where it already sits). **Honest NaN coverage holes retained** (no change — VIEW-05 satisfied).
- **D-14:** Define the **accent token set once in `config.py`** (positive / negative / accent / surface) so the dashboard and the Phase 11 email read the same colors — single source of truth, mirroring how `compute_ticker` already feeds both surfaces. Migrate `REGIME_COLOR` (`report.py`) into these shared tokens.

### Email-readiness (in-scope design principle; wiring is Phase 11)
- **D-15:** Build each analysis piece as a **reusable, headless function** (not buried in Streamlit) so Phase 11 plugs them straight into the email without rebuilding: the VRP plain-read string, the evolution 5-day summary, the positioning levels (walls/flip + distance-to-spot), and the palette tokens. Mirrors the existing `compute_ticker` single-source-of-truth pattern. (User: "ensure we are getting some of the amazing analysis into the email" — full delivery is Phase 11 RPT-01..05.)

### Claude's Discretion
- Exact hex values for the restrained Bloomberg palette (planner, or an optional `/gsd-ui-phase` design contract).
- Whether Viridis stays or shifts to a more terminal-appropriate sequential on the dark background.
- Exact OI chart encoding (grouped bars vs diverging put/call columns) — keep it visually like the current strike-GEX chart.
- Evolution empty/cold-start caption wording (consistent with the existing "accumulates from `run_daily`" captions).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & requirements
- `.planning/ROADMAP.md` §"Phase 10: Dashboard Restructure (local only)" — goal + 5 success criteria (note: "5→4 tabs" wording is stale; code is already 4 — see D-01).
- `.planning/REQUIREMENTS.md` §"Dashboard Restructure (Phase 10 — local only)" — VIEW-01..05.
- `.planning/research/SUMMARY-v3.3.md` — v3.3 research (architecture approach, pitfalls).

### Code to modify / reuse (the edit surface)
- `streamlit_app.py` — **the main edit surface** (603 lines, 4 tabs). Current tabs: `Surface` (Today/∆Change sub-tabs), `Skew`, `Term Structure`, `Flow Context`. Boot/CSS/cards above the tabs are reusable.
- `gex/analytics.py` — `plot_strike_gex` (repurpose → OI by strike), `plot_gamma_profile` (→ expander), `plot_vol_surface` (:159), `plot_iv_change_surface` (:303, Compare Δ-surface), `plot_skew_25d_current`/`plot_term_structure` (**drop** — surface owns shape), `plot_carry_vrp` (**remove**), `summarise` (walls/zgl/spot), `coverage_mask`, `rbf_grid`.
- `gex/surface_evolution.py` — `load_evolution(ticker, horizon, days)` → Evolution small-multiples; `compute_evolution_scalars` is a pure fn but is **NOT** used in Compare (kept Evolution-only per D-12).
- `gex/surface_history.py` — `load_surface_snapshot`, `list_available_dates`, `nth_trading_day_back` → two-date Compare dropdowns.
- `gex/validation.py` — `load_history` returns persisted `spot`/`call_wall`/`put_wall`/`zero_gamma_level`/`net_gex`/`iv30`/`rv20`/`vrp`/`front_skew` → drives the 2-month price+levels chart (Chart B), the VRP sparkline, and percentiles.
- `gex/vol_metrics.py` — `compute_vrp`, skew, term (VRP headline + scalar strip).
- `gex/compute.py` — `compute_ticker` (single source of truth feeding dashboard + email; keep analysis headless per D-15).
- `gex/config.py` — existing `SURFACE_*` constants; **add the shared palette tokens** (D-14).
- `gex/report.py` — `REGIME_COLOR` migrates into shared config tokens; Phase 11 consumes them.

### Codebase conventions
- `.planning/codebase/CONVENTIONS.md`, `.planning/codebase/ARCHITECTURE.md` — pure-function compute, single source of truth, Windows pathlib.
- `.planning/phases/08-surface-validation/08-CONTEXT.md` — coverage mask / honest holes provenance (retained in this phase).
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `plot_strike_gex` → repurpose to **OI by strike** (Chart A) — same visual shape, OI not GEX.
- The existing "γ-flip vs Spot — 30 sessions" chart (`streamlit_app.py` Flow tab) → extend to the **~2-month price + walls/flip lines** (Chart B); all four series already persisted in `gex_snapshots.parquet`.
- `load_evolution` → Evolution tab small-multiples; data already idempotent per (date, ticker, horizon).
- `load_surface_snapshot` / `list_available_dates` / `nth_trading_day_back` → relative-horizon Compare dropdowns.
- `plot_iv_change_surface` → Compare 3D Δ-surface; already bounds DTE to the today∩prior intersection (mask-honest).
- History store columns (`iv30`/`rv20`/`vrp`/`front_skew`) → VRP headline + sparkline + percentiles + skew/term scalars with no new compute.
- `REGIME_COLOR` (`report.py`) → fold into shared config palette tokens.

### Established Patterns
- `compute_ticker` is the single source of truth (headless + Streamlit) → keep new analysis **headless** so the Phase 11 email reuses it (D-15).
- Project rejects hand-tuned non-stationary thresholds (twice) → palette/labels stay descriptive; GEX-derived levels are labelled as model constructs, never presented as bankable.
- Honest NaN holes (Phase 8 convex-hull mask) → retained in the surface and Δ-surface.
- 5-day narrative lead (RPT-05) → Evolution defaults to 5d; VRP + evolution summaries are written email-ready.

### Integration Points
- `streamlit_app.py` is the primary surface; `gex/config.py` gains palette tokens; Phase 11 (`gex/report.py`) consumes the shared tokens + the headless analysis functions.
</code_context>

<specifics>
## Specific Ideas

- **Visual north star: "more Bloomberg-like" dark terminal** — dense, restrained, amber-on-black accent.
- The Positioning tab **replaces hand-drawing call wall / γ-flip / put wall lines on TradingView** — the user's current manual workflow.
- VRP read literal: *"vol rich +8.7pp, 82nd %ile — premium-selling favored, protection is expensive right now."*
- Evolution small-multiples literal layout: horizon radio on top, then `level / rms / skewΔ / termΔ` stacked, SPY·QQQ·IWM overlaid per panel, zero line each.
</specifics>

<deferred>
## Deferred Ideas

- **GARCH tab / conditional-vol model** — a new analytical capability, NOT a restructure. Violates the descriptive-only + no-new-signals-until-validated guardrail (same bar that retired the regime label). Belongs in its own phase with methodology research. Legitimate future plug-in: sharpen VRP's realized-vol baseline (GARCH conditional vol vs naive RV20).
- **OI-defined walls** (max call-OI / max put-OI strikes) — more observable than GEX walls, but the scalar store keeps no historical chains, so OI walls could only show *today's* level until history accumulates forward. Deferred in favour of GEX-defined persisted walls (real 2-month history now).
- **Email background decision** (dark-terminal vs light-formal) under RPT-04 — **Phase 11**. Lean: a restrained dark email matches the Bloomberg dashboard, but light is the safer formal-business default; decide when building the email. The "get the amazing analysis into the email" ask = Phase 11 **RPT-01..05** in full (PNG surface + ΔIV attachments, content priority surfaces>walls>OI>gamma, evolution scalars w/ 5-day narrative lead, OI surfaced).
- **Front-vs-back VRP** (term-VRP decomposition) — borderline new compute; revisit if the single VRP read proves insufficient.

None of these are scope creep into other active phases — they're explicit later-phase punts or sub-options inside Phase 10's boundary.
</deferred>

---

*Phase: 10-dashboard-restructure-local-only*
*Context gathered: 2026-05-31*

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
