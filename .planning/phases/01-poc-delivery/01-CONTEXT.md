# Phase 1: POC Delivery & Calibration — Context

> **Milestone v2.1 — POC Delivery & Validation.** Originally drafted as Phase 6 of v2.0; lifted to Phase 1 of v2.1 on 2026-05-04 once it became clear that v2.0 (engine build) was complete and this work is a new cycle (audience: external quant team; mode: deliver + learn).

**Gathered:** 2026-05-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Re-scoped from the original roadmap "Validation Gates" framing. The original framing assumed an algorithmic recommendation engine that needed gates to certify before acting. The framework no longer prescribes — it describes state, exposure, and history. So Phase 6 is now:

**Polish, calibrate, and deliver the POC to the quant team for evaluation.**

Three concrete deliverables:
1. **Calibrated math** — swap the synthesized 90mny IV for Bloomberg-observed `30DAY_IMPVOL_90.0%MNY_DF` so put-skew premium and collar/CSP/strangle pricing are properly calibrated.
2. **Quant-readable notebook** — a `.ipynb` artifact with embedded charts, top-of-page current-state summary, and drill-down sections below. Generated from the existing `.py` engine modules.
3. **Walkthrough document** — markdown explaining each section, how to read it, and its limits, so the quant team can self-serve before any meeting.

Scope cap: **delivery + calibration + cleanup**. No new signals, no fund specialization (PDIV), no HMM/Markov-switching this phase.

</domain>

<decisions>
## Implementation Decisions

### Audience & cadence

- **D-01:** Primary audience = **quant team first.** They review math, stats, framework rigor. PM presentation comes after if quant blesses it.
- **D-02:** Cadence = **weekly review.** Designed for Monday-morning regime check, not daily glance or ad-hoc trigger.
- **D-03:** Most-important sections to lead with = **Section A (current state)** and **Section C (conditional history)**. Other sections support these.
- **D-04:** **Open question for the meeting:** Does the team already have a vol/regime panel we shouldn't duplicate? Capture in the walkthrough doc as an explicit ask.

### Output format

- **D-05 (revised 2026-05-04):** Output medium = **single HTML file.** `python build_report.py` → `out/sleeve_report_YYYYMMDD.html`. Self-contained, charts embedded as base64. Opens in any browser, shareable as a file attachment. Notebook format deferred — if team greenlights the POC and Cron2 deployment makes sense, that's a future phase.
- **D-06:** Generation = **manual.** `python build_report.py` Monday morning produces the report. No scheduler infra for POC.
- **D-07:** Layout = **top-down: current state → drill-down.** Section A leads (with week-over-week change vs prior run). Sections B/C/E/G/H follow as supporting context.
- **D-08:** Charts = **critical.** Invest in chart quality — labels, palette, regime shading, consistent styling. Quants scan charts before tables.

### Pruning / reframing existing code

- **D-09:** **Delete `validate.py`.** Walk-forward "find a rule that wins" framing was forecasting drift. The negative finding (no rule survives Holm correction, no rule beats passive OOS) is absorbed into framework understanding. Clean cut, no orphan module.
- **D-10:** **Section D — rename and reframe.** Currently "Closest Regime Analogs" with realized sleeve P&L from analogs (forecast-flavored). Rename to **"Past Periods That Looked Like Now"** and replace realized sleeve P&L with **realized environment** (what vol/skew/term/dd did in the period AFTER the analog match). Drops forecast framing, keeps the historical-context value.
- **D-11:** **Keep Section C bucket means + Welch's t-test + Holm-Bonferroni.** The "0 of 30 tests survive Holm" result is the most credibility-establishing thing in the dashboard. It is the exact rigor the quant team will check for. Do not condense or remove.
- **D-12 (revised 2026-05-04):** **Ship on free data. Bloomberg deferred.** Original decision was to swap synthesized 90mny IV before delivery. Reversed: Bloomberg usage is being cut back company-wide; POC has not yet been proven useful so the data pull is not justified. Build locally on CBOE+FRED free data. If the quant team greenlights the framework, Bloomberg calibration is a one-class swap (`BloombergCon` mirroring `FreeCon.bdh`). WALKTHROUGH.md must acknowledge the synthesized 90mny IV (slope=0.2 approximation) as a known limitation.

### Build environment

- **D-17 (added 2026-05-04):** **Local Python first, Cron2 later.** Build and run on a local venv. The locked Cron2 env is a future migration target, not the build environment. `python build_report.py` runs locally; if the team uses the POC, porting to Cron2 is a separate phase. This removes all locked-env constraints from this phase.

### Done & handoff

- **D-13:** Done bar = **notebook + Bloomberg-calibrated data + written walkthrough doc.** Three deliverables, all needed before showing the team.
- **D-14:** Handoff = **async first, then meeting.** Send the notebook + walkthrough; let them play with it for several days; then a focused discussion. Captures both gut and considered reactions.
- **D-15:** Sharpest feedback question to ask = **"What would have to be true for this to inform a real decision?"** Path-to-utility question. Surfaces missing pieces or trust gaps without leading.
- **D-16:** **Hard scope cap — explicitly OUT for this phase:** PDIV / fund specialization, Markov-switching/HMM, any new signals. Locked. This phase is delivery + Bloomberg + cleanup, period.

### Claude's Discretion

- Notebook chart styling (palette, regime shading details, font sizes) — Claude picks tasteful defaults.
- Walkthrough doc structure (section ordering, depth per section) — Claude drafts, user reviews.
- Section A "week-over-week change" computation (delta of pct-rank? raw value? both?) — Claude picks, flags the choice in the doc.
- Section D reframe specifics — Claude designs the "realized environment" output (which signals to show post-analog, time horizon, table layout).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project framing & locked decisions
- `.planning/PROJECT.md` — α-only / market-general scope; no PDIV (β); HMM (γ) optional.
- `.planning/STATE.md` — current progress, local POC dev path, Bloomberg-pending status.
- `options-quant.md` — project hub with constraints (Cron2 locked env, sleeves CC/CSP/Collar/Strangle, no predictive claims).
- `CLAUDE.md` — project operating manual.

### Prior phase context (v2.0 engine, archived)
- `.planning/phases-archive/v2.0-engine/01-extended-data-layer/01-CONTEXT.md` — data layer decisions D-01..D-13 (NYSE alignment, panel schema, deferred-field handling).

### Implementation reference
- `Data.ipynb` — confirmed working `con.bdh` patterns for Bloomberg swap (price, IV fields, USGG3M for risk-free).
- `local_data.py` — current free-source dispatch (CBOE+FRED) — Bloomberg swap point is `FreeCon._dispatch`.
- `data_layer.py`, `signals.py`, `backtest.py`, `dashboard.py`, `stats_rigor.py`, `sensitivity.py`, `run.py` — engine modules, untouched by this phase.

### Bloomberg / emds_client field reference
- `30DAY_IMPVOL_100.0%MNY_DF` — 30d ATM IV (confirmed working)
- `30DAY_IMPVOL_90.0%MNY_DF` — 30d 90% moneyness IV (confirmed working) — **this is the field that replaces our synthesized version**
- `90DAY_IMPVOL_100.0%MNY_DF` — 90d ATM IV (confirmed working)
- `PX_LAST` — price level

### Statistical rigor (locked, do not modify)
- `stats_rigor.py` — Holm-Bonferroni step-down, stationary block bootstrap. Both stay.
- Section C bucket means + p-values + Holm-corrected p — stays in dashboard verbatim.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable assets (engine layer — keep, do not modify in this phase)
- `local_data.FreeCon.bdh(ticker, field, start, end)` — current data dispatch. Bloomberg swap means adding a `BloombergCon` class with the same interface, and a config switch.
- `data_layer.build_panels()` — produces `Panels` dataclass with prices_panel, iv_panel, iv90_panel, iv90mny, skew_panel, vix, rf_rate. Schema unchanged after Bloomberg swap.
- `signals.build_signals()` — produces `Signals` dataclass with raw + pct + fragility. Unchanged.
- `backtest.run_backtest()` — produces `BacktestResults` with rolls / equity / stats per underlying. Unchanged.
- `dashboard.build_dashboard()` — produces text dashboard. Will be **replaced** as the primary output by a notebook builder, but the section helpers (section_a_state, section_c_buckets, etc.) become inputs to notebook cells.

### To delete this phase
- `validate.py` — entire module. Per D-09.
- `out/walkforward_*.txt` — orphan outputs from validate.py.
- Any imports of `validate` in `run.py` — clean up.

### To rebuild this phase
- New: notebook builder script (`build_report.py` or similar) that takes Panels/Signals/BacktestResults and emits a `.ipynb` file with embedded charts and section narratives. Pattern is the same shape as the deleted `build_dev_notebook.py` but using the now-stable engine modules.
- New: `WALKTHROUGH.md` — markdown doc explaining each section with how-to-read guidance.
- Modified: `dashboard.py` Section D — reframe to show realized environment (vol/skew/term/dd over T+1, T+2, T+3 months) instead of realized sleeve P&L.

### Integration points
- Bloomberg swap point: `local_data.py`. Add a class `BloombergCon` mirroring `FreeCon.bdh` interface that calls `emds_client.con.bdh`. Config flag (env var or constant) selects which.
- Walkthrough doc lives at repo root or `docs/`. Markdown so it renders on GitHub and reads in Obsidian.

</code_context>

<specifics>
## Specific Ideas

- **Walkthrough doc structure** (Claude proposes, user revises): one section per dashboard section, each with: (a) what it shows, (b) how to read it, (c) what it doesn't show / its limits, (d) how it was built (sample size, statistical method).
- **Top-of-notebook current-state strip**: a compact summary line — "{date} · SPX vrp Q3, term Q4, fragility 0.42 (calm) · NDX similar". Surfaces the answer in the first 3 seconds.
- **Week-over-week delta** in Section A: small inline column showing change in pct rank vs the same notebook run a week ago. Requires saving the latest snapshot to disk so next week's run can diff.
- **Holm result as a feature not a bug**: the walkthrough doc should explicitly call out "0 of 30 tests survive Holm correction" as a *feature* of the framework — it tells the team what they can and cannot defensibly claim.
- **Sharpest feedback question** = "What would have to be true for this to inform a real decision?" — written explicitly into the walkthrough doc as the question we want them to answer when they return feedback.

</specifics>

<deferred>
## Deferred Ideas

### Out for this phase, candidates for future phases
- **PDIV / fund-specialization (Phase β, originally Phase 7)** — already dropped 2026-05-04 per scope simplification. May return as a future phase if quant team asks for a fund-specific application after evaluating the market-general POC.
- **Markov-switching fragility flag (Phase γ, Phase 8)** — optional, untouched. Eligible only after Phase 6 ships and team requests it.
- **New signals** — six current signals + fragility composite are it. No additions until quant team validates the framework. Candidates for "future signals" include term-vol-of-vol, dispersion (intentionally out per project scope), credit-spread fragility component.
- **Automated weekly schedule** — current decision is manual run. If team uses the POC weekly and asks for automation, that's a future phase.
- **HTML/PDF export, Slack snapshot** — alternate output formats considered and rejected for POC. Could revisit if team asks.
- **Transaction cost calibration to specific broker** — current TC sensitivity uses a generic 0/5/10/20 bp grid. If team has a specific cost structure they trade, calibrate to it later.

### Open question to surface in the team meeting
- Does the team already have a vol/regime/sleeve-context dashboard we shouldn't duplicate? **Capture in the walkthrough doc as an explicit question for the team.**

### Reviewed during discussion, kept
- **Section D regime analog** — was a deletion candidate. Decision: keep but reframe to "realized environment" rather than "realized sleeve P&L" (D-10).
- **Bucket t-tests** — was a simplification candidate. Decision: keep verbatim because the Holm "0 survives" result is the credibility centerpiece.

</deferred>

---

*Milestone: v2.1 — POC Delivery & Validation*
*Phase: 01-poc-delivery*
*Context gathered: 2026-05-04*
