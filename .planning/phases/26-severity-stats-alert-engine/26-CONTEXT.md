# Phase 26: Severity Statistics & Alert Engine - Context

**Gathered:** 2026-07-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Every existing metric carries an honest "how unusual is this" measure — empirical-CDF percentile ranks on levels and 5-day changes (dual deep/1yr lookback), a transition-with-hysteresis alert rule, and alert bands derived from a ~1-episode/week false-alarm budget calibrated by replaying the ranker over stored history. Engine + persistence + calibration CLI only. **No UI and no email changes** — all surfaces are Phase 27. **No new signals** — this is a severity transform over already-computed values (no-hidden-scoring rule applies: raw percentile ranks only, no composite/anomaly scores).

</domain>

<decisions>
## Implementation Decisions

### Severity statistics
- **D-01:** Empirical percentile rank (ECDF) is the only severity measure — levels AND 5-day changes ranked against each metric's own history. No Gaussian z-scores (heavy tails/heteroskedasticity); robust z ((x−median)/MAD) only if a continuous score is ever needed later.
- **D-02:** Dual lookback per level rank: deep (full available history, generalizing `VRP_DEEP_LOOKBACK_SESSIONS`) + 1-yr (252 sessions). Both persisted and displayed; an alert can fire on either.
- **D-03:** Change severity: **k=5 only** (matches the evolution engine's primary horizon; 1d is noise, deliberately excluded there too). **Two-sided |Δ5d|** — one rank per metric for "moving abnormally fast either way"; direction appears in the alert text, not in separate bands.

### Alert rule & false-alarm budget
- **D-04:** Alerts fire on **band entry**, re-fire only on **escalation** (crossing a higher band, e.g. 99th); exit band lower than entry (hysteresis) so alerts don't flicker.
- **D-05:** Tolerated alarm rate: **~1 episode/week** across the whole monitor. Expected bands land ~97th–98th, but bands are NOT hardcoded from theory — they come from the calibration replay (D-06).
- **D-06:** Band calibration is a **permanent CLI deliverable** (e.g. `python -m engine.monitor.calibrate`): replays the ranker over stored histories, reports alert episodes/week per candidate band + hysteresis width, re-runnable as chain-metric history deepens. Chosen bands land in `engine/config.py` with the replay evidence noted.

### Metric inventory & credibility floors
- **D-07:** v1 inventory: VRP, 25Δ skew, 25Δ fly, surface-evolution level & RMS (×SPY/QQQ/IWM) + SPY-only term ratios (9D/30, 30/3M). Evolution scalars rank as **levels only** (they are already 5d changes — no change-of-change).
- **D-08:** Ranks are always computed and labeled with sample size n, but a metric may **fire alerts only with ≥252 sessions** of its own history. Consequence accepted: at ship only VRP + SPY term ratios alert (deep vol-index history); chain metrics (skew/fly/evolution, ~50 sessions since 2026-05) are visible-but-building until ~2027-05.
- **D-09:** IWM–SPY VRP spread NOT in v1 — stays seeded (`.planning/seeds/iwm-spy-vrp-spread-divergence.md`).
- **D-10:** Net GEX gets NO severity rank — sign is a present-tense state chip at display time (GEX-as-candidate decision, 2026-07-22).

### Persistence & output shape
- **D-11:** New **`out/monitor/`** parquet store, appended by `run_daily`, following existing store patterns: one row per metric×ticker×day (level rank deep + 1yr, |Δ5d| rank, n, band state) plus an **alert-events table**. Hysteresis reads yesterday's row. Phase 27 surfaces consume this store; nothing else recomputes ranks.
- **D-12:** Phase 26 does **not** touch the email. Verification is via CLI output + tests + the persisted store.

### Claude's Discretion
- Hysteresis exit-band width — set from the calibration replay's flicker analysis (which gap collapses multi-fire episodes to one), not a priori.
- Module layout (e.g. `engine/monitor/` package), store schema details, backfill approach for historical rows.
- How `calibrate` presents candidate bands (table format, episode listings).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design & rationale
- `.planning/notes/microstructure-monitor-design.md` — full monitor design decisions from the 2026-07-23 explore session (statistical rationale: persistence/ESS, multiple testing, lookback-as-regime-assumption, unequal depths). This CONTEXT.md operationalizes it for Phase 26.
- `.planning/research/questions.md` §"Alert band calibration (2026-07-23)" — the calibration question the `calibrate` CLI answers.

### Adjacent scope (do not implement here)
- `.planning/seeds/iwm-spy-vrp-spread-divergence.md` — deferred spread rows (post-v1).
- `.planning/todos/pending/email-boilerplate-cut.md` — Phase 27's email work; Phase 26 must not touch `engine/report/report.py`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `engine/vol/vrp_history.py` — existing deep-percentile machinery for VRP; the pattern (and its data path via `engine/data/vol_index.py`) generalizes to the ranker.
- `engine/data/validation.py` (`save_snapshot`/`load_history`), `engine/data/surface_history.py`, `engine/data/oi_history.py` — established parquet-store patterns for the new `out/monitor/` store; `engine/surface/surface_evolution.py` (`load_evolution`) supplies the 5d level/RMS scalars.
- `engine/config.py` — `VRP_DEEP_LOOKBACK_SESSIONS=2500`, `VRP_PERCENTILE_LOOKBACK=252`, `CARD_READ_MIN_SESSIONS=60` — new constants (alert floor 252, bands, hysteresis) live beside these.
- `scipy.stats.percentileofscore` already used in `app.py` for ad-hoc skew percentile — the engine version replaces such one-offs as the canonical source.

### Established Patterns
- Orchestration seam: `run_daily` appends to stores; dashboard/email only read. The monitor engine follows the same seam (D-11).
- Credibility gating: values below sample floors are labeled/omitted, never caveated-but-shown (see `build_card_read`).
- Sole-owner statistical discipline: multiple-testing awareness before any threshold ships (CLAUDE.md constraint) — the false-alarm budget IS that discipline for this phase.

### Integration Points
- `engine/run_daily.py` — appends daily monitor rows after existing snapshot saves.
- `engine/compute.py` (`compute_ticker`) — source of today's metric values; the ranker consumes its outputs plus stored histories, computing nothing new from chains.
- Known data gaps exist (6 missing sessions in gex/surface stores, e.g. 2026-07-01) — ranker must tolerate gaps; Phase 23's gap tooling is adjacent but not a dependency.

</code_context>

<specifics>
## Specific Ideas

- Alert text should name the **mechanism in words**, not dump numbers: "front skew 94th %ile, +2.1pp over 3 sessions — hedging demand bid" (style from the explore session).
- The unpackaged sketch direction (`.planning/sketches/MANIFEST.md` — "should I be worried?", calm authority, narrative-first) is Phase 27 input, noted here so it isn't lost.

</specifics>

<deferred>
## Deferred Ideas

- IWM–SPY VRP spread severity row (seeded — both legs deep, backfillable, but post-v1).
- Multi-horizon change ranks (k=1, 10, 20) — revisit after the replay shows what k=5 misses.
- Tier-2 conditional base rates ("after skew >90th, 5d RV ran 1.4× baseline, n=…") — separate validation work, later v5.0+/modeling milestone.
- Order-statistic confidence intervals on percentile ranks — cheap add if error bars ever wanted on the board.

### Reviewed Todos (not folded)
- `email-boilerplate-cut.md` — Phase 27 scope (email surface), referenced there.
- `2026-05-11-salvaged-from-legacy-task-board.md`, `2026-05-11-v3-2-pre-distribution-hardening.md` — keyword-only matches, unrelated to the monitor.

</deferred>

---

*Phase: 26-severity-stats-alert-engine*
*Context gathered: 2026-07-23*

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
<!-- LINKS:END -->
