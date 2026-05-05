---
gsd_state_version: "1.0"
milestone: "v2.1 — POC Delivery & Validation"
status: active
last_updated: 2026-05-05 (Phase 2 complete — section_short_vol_environment shipped)
context_gathered: Phase 2
plans_ready: false
authored_local: true
cron2_pending: false
local_poc_active: true
progress: 6
---

# Project State

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-05-04 for v2.1)
See: `.planning/MILESTONES.md` (v2.0 closure recorded 2026-05-04)
See: `.planning/ROADMAP.md` (v2.1 roadmap, Phase 1 complete)

**Core value:** Calibrated, quant-readable description of options-overlay environment + exposure mechanics + historical context for the quant team's weekly review. State + history, never prescriptive.

**Current focus:** v2.1 post-Phase-1 iteration. HTML report is the deliverable (not a notebook). Bayesian reframe shipped — conditional context leads the report. Next work: open data quality items or quant-team feedback.

## Current Position

Milestone: **v2.1 — POC Delivery & Validation**
Phase: **2 of 2+ — COMPLETE.** Phase 2 shipped 2026-05-05.
Status: HTML report fully operational. Phase 2 adds signal-conditioned historical distributions section (Short-Vol Environment) to the report.
Last activity: 2026-05-05 — Phase 2: `section_short_vol_environment(sigs, panels)` added to `dashboard.py`; wired into `build_report.py` replacing `section_market_outcomes`. Percentile tables (p10/25/50/75/90 + n) for VRP capture ratio, move magnitude, IV change across 4 signal quartiles × 4 signals. Today's quartile marked `*`.

Progress: [██████████] 100% (Phase 1 + Bayesian reframe — report ready to send)

## Performance Metrics

**v2.0 final velocity (closed):**
- Engine modules shipped: 7 (`local_data`, `data_layer`, `signals`, `backtest`, `dashboard`, `stats_rigor`, `sensitivity`)
- Tests: 74 passing
- Statistical rigor: Holm-Bonferroni, stationary block bootstrap
- Honest finding: 0 of 30 bucket-mean tests survive Holm correction at FWE α=0.05

**v2.1 velocity (active):**
- Phase 1 plans completed: 5 (01-02 validate.py cleanup, 01-03 Section D reframe, 01-04 HTML report generator, 01-05 chart styling, 01-06 WALKTHROUGH.md)
- Post-phase: Bayesian reframe (conditional summary, equity chart removal, Section E caveat)

## Accumulated Context

### Decisions (carried forward)

**Bayesian reframe (2026-05-04):**
- HTML report leads with `section_today_conditional()` — conditional bridge from today's signal quartiles to historical sleeve returns
- Growth-of-$1 equity chart deleted — was the loudest unconditional strategy-ranking signal; data still in Section E stats
- Section E carries explicit caveat: "unconditional reference class over 2010–2026 (sustained equity bull market)"
- Section order: conditional summary → A → signal chart → B → C → D → E → G → H (C before E so conditional frame lands first)
- No new math — `section_today_conditional()` pulls from the same bucket computation as Section C

**v2.0 closure (2026-05-04):**
- Engine build complete on free CBOE+FRED data; mode shift to deliver/learn warranted milestone boundary
- Phases 1-5 archived under `.planning/phases-archive/v2.0-engine/`

**v2.1 Phase 1 execution (2026-05-04):**
- Deliverable is HTML report (`build_report.py` → `out/sleeve_report_YYYYMMDD.html`), not a Jupyter notebook — notebook deliverable dropped as scope simplification
- Bloomberg calibration deferred; free-data POC ships as-is; Bloomberg is a one-class swap when team greenlights
- WALKTHROUGH.md at repo root; covers all sections + two team questions

**Scope cap (locked):**
- No PDIV, no HMM, no new signals — locked until team validates current set
- Audience: quant team first; async handoff then meeting

**Earlier (carried from v2.0):**
- Strategy menu = CC + CSP + Collar + Short Strangle (drop dispersion)
- Universe = SPX + NDX index level (POC)
- Insight framing = state + exposure + history; never prescriptive

### Pending Todos

- **Send async to quant team** — Send `out/sleeve_report_YYYYMMDD.html` + `WALKTHROUGH.md`. Async first, then meeting.
- **UAT** — Open `out/sleeve_report_20260504.html` in browser; verify conditional summary renders and n/mean values match Section C for today's quartiles.
- **NDX skew identity bug** — both underlyings share the same CBOE SKEW signal; readings always identical. Data accuracy issue, separate phase after team feedback.

### Blockers/Concerns

- Bloomberg calibration deferred (not blocking) — free-data POC is the deliverable. Bloomberg is a one-class swap in `local_data.py` when team greenlights production.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| v1.0 | All v1.0 phases (HMM diagnostic) | Closed without ship | 2026-04-30 |
| v2.0 | Phase 7 (PDIV / fund specialization) | Dropped, market-general scope only | 2026-05-04 |
| v2.0 | Phase 8 (Markov-switching fragility flag) | Optional, deferred indefinitely | 2026-05-04 |
| v2.1 | Bloomberg calibration | Deferred pending team greenlight; one-class swap | 2026-05-04 |
| v2.1 | New signals beyond six + fragility composite | Locked OUT until team validates current set | 2026-05-04 |
| v2.1 | NDX skew identity bug | NDX/SPX share same CBOE SKEW signal — data accuracy fix | 2026-05-04 |
| v2.1 | NDX iv90_atm synthesis | Uses SPX term-structure ratio — same category as skew bug | 2026-05-04 |
| v2.1 | Automated weekly schedule | Manual run for POC; revisit if team adopts weekly cadence | 2026-05-04 |
| v2.1 | TC sensitivity calibration to broker desk | Generic 0/5/10/20bp grid; desk-specific calibration deferred | 2026-05-04 |

## Session Continuity

Last session: 2026-05-04
Stopped at: Bayesian reframe complete. Conditional summary leads report, equity chart gone, Section E reframed, WALKTHROUGH.md updated. Planning docs cleaned up.
Resume: UAT the HTML report, then send async to quant team. Next dev work: NDX skew identity bug or await team feedback.
