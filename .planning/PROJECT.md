# Options Quant — GEX Analysis Platform

*Last updated: 2026-07-27 — v6.0 covered-call tilt-timing model investigated and SHELVED (no timing edge in the evidence). No active milestone; v5.0 shipped 2026-07-27.*

## Current Milestone: (none — between milestones)

**Last shipped:** v5.0 Data Foundation + Microstructure Monitor (2026-07-27). See Previous Milestones + `.planning/MILESTONES.md`.

**v6.0 covered-call tilt-timing — investigated & SHELVED 2026-07-27.** Cheap pre-build tests (SPY, 2016–2026) found no evidence for *timing* a USCC↔VFV tilt on VRP: the forward-return difference rich-vs-cheap is noise (non-overlapping Welch p=0.74) and the forward-vol difference is only marginal (p=0.074, ~35 independent windows, in-sample, pre-multiple-testing/costs). A *static* covered-call sleeve already harvests VRP structurally; timing it adds no demonstrated edge. Killed before building — see `research/covered-call-spike-findings.md` + memory `v6-covered-call-model-decision`. The existing **descriptive** VRP-percentile read (dashboard + daily email) stands and remains the honest layer.

**Open (not a milestone):** OCI restore drill (BACKUP-02) — confirm `restore_from_oci` recovers `out/`. Backup itself live since 2026-07-23.

## Current State

**v5.0 Data Foundation + Microstructure Monitor shipped 2026-07-27** (Phases 23–27; OCI backup live since 2026-07-23). The dashboard + daily email run unattended on Oracle Cloud (`https://40.233.113.63.nip.io`); data collection + backup on GitHub Actions. Password gate removed — dashboard is intentionally public. v4.0 (cloud hosting) detail: `.planning/milestones/v4.0-ROADMAP.md`.

## What This Is

A vol/dealer-gamma diagnostics platform for an index income-sleeve PM (covered calls / cash-secured puts on SPY/QQQ/IWM). Computes VRP percentile (ranked against ~10yr of CBOE vol-index history), VIX term-structure, dealer positioning (GEX, capped ≤90 DTE) from live options chains (CBOE delayed quotes JSON — no API key), and delivers daily context via a scheduled HTML email and an interactive Streamlit dashboard, both cloud-hosted and running unattended.

## Core Value

How expensive is protection right now, where on the surface is that expensiveness concentrated, how is the surface moving over time, and what does it imply for portfolio overlays or option-writing sleeves? Descriptive/interpretive only — no predictive claims (that's the deferred options-writing/pricing model track).

## Runtime & Stack

- **Runtime:** local Python venv. `python -m gex.run_daily --send` → email (scheduled via Task Scheduler). `streamlit run streamlit_app.py` → dashboard (interactive).
- **Data:** CBOE delayed quotes JSON (`cdn.cboe.com` — free, no auth). Snapshots: `out/gex_snapshots.parquet`.
- **Stack:** pandas, numpy, scipy, matplotlib, requests, pyarrow, streamlit, plotly, pandas_market_calendars.
- **Tests:** pytest, 24 tests green (down from 77 post-v3.0 due to feature cuts per 2026-05-11 refactor).

## Key Files

| File | Purpose | Last Updated |
|------|---------|---|
| `gex/greeks_engine.py` | BS gamma, vanna, charm — vectorised with 0DTE guard | 2026-05-06 |
| `gex/exposure_engine.py` | GEX/VEX by strike; delta-hedge flow | 2026-05-11 (refactor: kept GEX only) |
| `gex/analytics.py` | Summary dict, defensible chart outputs | 2026-05-11 (refactor: removed CHEX, regime labels) |
| `gex/validation.py` | Parquet snapshot store, load_yesterday, load_history | 2026-05-06 |
| `gex/report.py` | HTML email body builder — defensible outputs only | 2026-05-11 (refactor: removed VEX, ZGL flow, regime label) |
| `gex/run_daily.py` | Daily orchestrator — 3 tickers, save + send | 2026-05-06 |
| `streamlit_app.py` | Interactive dashboard — Live + Historical tabs; defensible display only | 2026-05-11 (refactor: removed VEX/CHEX, regime label, badges) |
| `out/gex_snapshots.parquet` | Historical GEX snapshot store (30+ days) | Growing daily |

`.planning/notes/MODEL-READY-DATA-SPEC.md` — Model-ready depth/schema targets for the next modeling milestone (Phase 23, D-09).

## Requirements

### Validated / Implemented (v3.0–v3.1)

**Core Defensible Outputs** (all surfaces):
- ✓ Spot, Day %, IV30, 1-day σ (from IV30)
- ✓ Net GEX (sign + magnitude)
- ✓ Zero-gamma level and vs-ZGL %
- ✓ Single max-GEX call/put walls + distance from spot
- ✓ Δ-flow = |Net GEX| / (spot × 0.01)
- ✓ 30-session ZGL-vs-spot history chart (dashboard only)
- ✓ Accent bar (driven by net GEX sign; no categorical label)

**Greeks & Flow Engine:**
- ✓ GRKS-01/02/03/04 — Vanna + Charm in BS engine, `add_greeks()` enriches chain DF, 0DTE guard — v3.0
- ✓ EXP-01/02/03 — GEX by strike, net scalar in `summarise()`, parquet store — v3.1 (VEX removed)
- ✓ FLOW-01/02/03 — Delta-hedge $/1%, email table columns — v3.0

**Dashboard & Email:**
- ✓ DASH-01/02/03/04/05 — Streamlit app: regime cards (sign-driven color only), cross-asset chart, expanders, COM isolation — v3.0/v3.1
- ✓ HIST-01/02/03/04 — Historical tab: ZGL trend, regime persistence, streak counter, event study — v3.0 (streak removed v3.1)
- ✓ EMAIL-01/02/03 — HTML email: per-ticker cards, defensible fields, theme-adaptive styling — v3.0/v3.1

**UAT Sign-Off:**
- ✓ UAT-01/02/03/04 — All 4 Streamlit scenarios pass; dashboard launches without error — v3.1

### Removed / Not Defensible

| Output | Reason | Cut When |
|--------|--------|----------|
| VEX display | Vanna is BS-European; 5–15% error on American options | 2026-05-11 |
| CHEX display | Charm is second-order vol; less PM-readable; statistically thin | 2026-05-11 |
| Regime categorical label | $200M neutral floor is hand-tuned; non-stationary | 2026-05-11 |
| vs-yesterday badge | Daily OI roll dominates 5% threshold | 2026-05-11 |
| Regime streak counter | Depends on removed label | 2026-05-11 |
| VEX/GEX ratio | Depends on VEX | 2026-05-11 |
| Early-exercise flag | Fragile signal; not actionable for SPY/QQQ/IWM | 2026-05-11 |
| ZGL flow row | ~20% numerical differentiation error | 2026-05-11 |
| GEX-weighted wall cluster | Arbitrary band parameters | 2026-05-11 |

### Validated / Implemented (v3.2 Phase 6)

- ✓ CUT-01 — Hedge Sh/$1, % vs ZGL, strike slope, term slope removed from cards — Phase 6
- ✓ INFRA-01 — `gex/vol_metrics.py` with compute_skew_25d, compute_term_structure, compute_rv20, compute_vrp — Phase 6
- ✓ INFRA-02 — Parquet schema extended with rv20 + vrp columns; old snapshots load safely — Phase 6
- ✓ SURF-CLEAN — Vol surface stripped of GEX overlays (no meridians, no spot plane), Viridis colorscale — Phase 6

### Validated / Implemented (v3.3 Phase 10 — Dashboard Restructure)

- ✓ VIEW-01/02 — Local dashboard collapsed 5→4 tabs (Surface / Calculus+VRP / Evolution / Positioning); Skew + Term merged into the surface-calculus tab — Phase 10
- ✓ VIEW-03 — Two stored dates comparable via relative-horizon dropdowns (live/1d/5d/10d/20d/30d/60d) resolved through `nth_trading_day_back` — Phase 10
- ✓ VIEW-04 — Evolution tab: horizon radio (5/10/20) + 4 small-multiple panels (level/rms/skew_change/term_change) overlaying SPY/QQQ/IWM — Phase 10
- ✓ VIEW-05 — Restrained `config.PALETTE` token set (single source of truth, shared with Phase 11 email); honest convex-hull coverage holes; interactive 3D surface retained — Phase 10
- ✓ Carry/VRP block, 25Δ RR-history chart, and strike-GEX bar charts removed; Positioning tab is OI-led (`plot_oi_by_strike` with real call/put OI from `strike_oi`, gamma profile demoted to expander) — Phase 10
- ✓ Headless `vrp_headline` / `evolution_5d_summary` / `positioning_levels` in `gex/vol_metrics.py` as Phase 11 email plug-in points — Phase 10

### Validated / Implemented (v3.5 Phases 15–18, 16.5, 17.1, 18.1 — shipped 2026-06-24)

- ✓ CTX-01 — VRP display superseded by VRP percentile (vol-index − RV20, ranked vs history) — Phase 16, deepened to ~10yr lookback ad-hoc 2026-07-16
- ✓ CTX-02 — OI tilt → richer OI depth expansion (expiry concentration, day-over-day change, put/call split, top-decile flagging) — Phase 16.5
- ✓ CTX-03 — Front skew gauge with percentile rank; directional labeling ("puts pricier"/"calls pricier") added ad-hoc 2026-07-16 — Phase 16/18.1
- ✓ NARR-01/02 superseded by term-structure regime (VIX9D/VIX/VIX3M raw ratios) + convexity/expected-move (25Δ fly, ATM straddle EM) — Phases 17, 17.1
- ✓ CUT-02 — 3-page reorg (Regime/Surfaces/Positioning); vol surface demoted off page 1 — Phase 18
- ✓ SURF-UX — addressed via convex-hull coverage mask (honest NaN holes) — Phase 8/18
- ✓ Dashboard/email trust hardening — compact trust-tagged scorecards, 14-DTE primary dealer-impact framing — Phase 18.1

### Validated / Implemented (v4.0 Phases 19–22, 20.5 — shipped 2026-07-17)

- ✓ Dockerized full stack — Dockerfile, docker-compose (dashboard + scheduler + Caddy), volume-mounted parquet — Phase 19
- ✓ Idempotent daily collection — supercronic scheduler, health-check script — Phase 20
- ✓ Email rebuilt end-to-end — content priority order, mobile-safe 390px layout, snapshot-freshness + methodology disclosure — Phase 20.5
- ✓ Deployed live to Oracle Cloud (E2.1.Micro, Always Free) with real HTTPS via nip.io + Let's Encrypt — Phases 21–22
- ✓ Daily scheduler moved to GitHub Actions after an Oracle chromium/PNG-export hang — ad-hoc, same milestone
- ✓ Password gate removed — dashboard made intentionally public — ad-hoc 2026-07-16

### Validated / Implemented (v5.0 Phases 23–27 — shipped 2026-07-27)

- ✓ Data completeness audit + gap monitoring across collected series — Phase 23
- ✓ Retention/backup for `out/` — activated 2026-07-23 (`backup_to_oci` runs on every daily CI; bucket + 3 GitHub secrets set); restore drill (BACKUP-02) pending — Phase 23
- ✓ "Model-ready" data definition (schema, depth targets per series) — Phase 23 (`.planning/notes/MODEL-READY-DATA-SPEC.md`)
- ✓ Codebase organization + dead-code removal, CLAUDE.md sync — Phase 24
- ✓ Existing-computation rigor certification (RV20 / skew / term / VRP-as-documented-proxy) — Phase 25 (`25-METHODOLOGY-AUDIT.md`)
- ✓ ECDF severity-rank + hysteresis alert engine (`engine/monitor/`) — Phase 26
- ✓ Microstructure monitor UI — distribution board + per-row evidence panels + hybrid event-shaped email — Phase 27

### Out of Scope

| Feature | Reason |
|---------|--------|
| Bloomberg data swap | One-class change in data_loader.py — still deferred post-v4.0 |
| Vomma / second-order vol Greeks | Less PM-readable than vanna |
| New GEX signals / predictive scoring | Holm-Bonferroni-equivalent statistical-validation bar stays high even sole-owner |
| Sleeve allocation framework (v2.x) | Separate track |
| Live intraday refresh | CBOE CDN is delayed — real-time needs paid feed |
| Dispersion / implied-correlation | Out of scope |
| Live execution / order routing | Research tool only |

## Strategic Decisions

| Date | Decision | Why |
|------|----------|-----|
| 2026-05-26 | iv30 normalised to decimal at compute_ticker() call site before compute_vrp | Keeps compute_vrp() contract pure (decimal-only); unit mismatch was producing VRP ~17-18 instead of ~0.02 |
| 2026-05-26 | Vol surface overlays fully stripped; Viridis colorscale | GEX overlays demoted to Strikes tab per v3.2 reframe |
| 2026-05-21 | Pivot to PM-actionable positioning; cut non-decision metrics | Outputs audited against "does this change a PM decision?"; mathematical elegance deprioritized |
| 2026-05-21 | Add VRP (IV30 − RV20) as hedging cost context | Carr & Wu (2009) VRP; descriptive metric even without causal backing |
| 2026-05-21 | Kill strike slope, term slope, hedge sh/$1, % vs ZGL | None inform a PM decision; model constructs without predictive value |
| 2026-05-11 | Cut VEX/CHEX/regime labels per methodology audit | BS-European Greeks on American options add 5–15% error; categorical regime label depends on hand-tuned non-stationary floor; focus on defensible outputs only |
| 2026-05-06 | GSD sign convention: calls +, puts − | SpotGamma/retail standard. Positive net GEX = dealers net long gamma = stabilising |
| 2026-05-05 | Vanna over Vomma | Vanna (∂delta/∂vol) translates to dealer rehedging flow — PM-readable. Vomma is not. |
| 2026-05-05 | Streamlit additive — email pipeline preserved | Email is scheduled and working; dashboard adds interactivity without breaking existing workflow |
| 2026-05-06 | Replaced yfinance with CBOE delayed quotes JSON | Free, no auth, CBOE-native Greeks (American-style). data_loader.py rewritten. |
| 2026-05-05 | New milestone v3.0 — GEX Interactive Dashboard | GEX POC is production-grade; direction is depth (Greeks, flow, dashboard) not more signals |
| 2026-05-11 | Expected-1d-sigma display (from IV30) | Answers "how much might this move today?" without eyeballing gamma charts |
| 2026-05-11 | Single max-strike walls (not GEX-weighted cluster) | Empirically observable; no arbitrary band parameters |
| 2026-06-16 | VRP scalar + percentile share one vol-index-based series (never snapshot IV30) | Prevents the displayed VRP number and its percentile rank from ever drifting apart |
| 2026-06-23 | 14-DTE primary dealer-impact framing (GEX_PRIMARY_DTE), ≤90 DTE context kept | Most dealer-relevant tenor as the headline, full window still visible |
| 2026-06-24 | Dashboard routing locked to Regime / Surfaces / Positioning | Page-1 hierarchy: cross-index briefing + OI teaser above the 3-card snapshot |
| 2026-07-14 | Daily scheduler moved from an Oracle container to GitHub Actions | Oracle Micro (1 vCPU/1GB) couldn't run headless Chromium for PNG export reliably; Oracle now only serves dashboard + Caddy |
| 2026-07-16 | VRP percentile ranked against ~10yr (`VRP_DEEP_LOOKBACK_SESSIONS`), not a rolling 1yr window | A short window can only say "cheap vs. a possibly-already-elevated recent regime" — CBOE vol-index actually holds decades of history |
| 2026-07-16 | CLAUDE.md's "locked until team validates" language dropped; self-imposed statistical-validation discipline kept | No external team left to validate against post password-gate removal + Oracle deploy — still sole-owner, still no unvalidated signals |

## Known Open Items

| Item | Description | Status | Next Action |
|------|-------------|--------|---|
| Charm by DTE | Backlog 999.1 | Parked | Awaiting validated methodology |
| Test coverage expansion | Backlog 999.2 | Depends on 999.1 | — |
| Pre-distribution hardening | Backlog 999.3 | ~50% done out-of-phase, ~50% deferred | — |
| American-style BS for IWM | IWM uses European model — acknowledged early-exercise risk | Acceptable, unresolved | Revisit if it matters for a future modeling milestone |
| `engine/report/png_export.py` silent export failures | Swallows failures into a `print()` warning, returns None | Known debt (2026-07-14 punch list) | Low priority — partial-failure visibility already fixed one layer up in `run_daily.py` |
| Phase 16.5 UAT/verification gaps | 3 pending human scenarios; Phase 11 & 16.5 also flagged human_needed | Acknowledged at v4.0 close, deferred | See STATE.md Deferred Items |
| `out/` backup | Daily backup to OCI Object Storage | Activated 2026-07-23 (Phase 23), daily CI green | Restore drill (BACKUP-02) still to exercise |

## Evolution

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---

## Previous Milestones

### v5.0 — Data Foundation + Microstructure Monitor (shipped 2026-07-27)
Hardened the data foundation (completeness/gap audit, model-ready depth spec, dead-code cleanup, per-computation rigor certification) then, on a mid-milestone reframe, turned the descriptive daily report into a market-microstructure exception monitor: ECDF severity-rank + transition-with-hysteresis alert engine (`engine/monitor/`), distribution-board dashboard with per-row evidence panels, hybrid event-shaped email. Phases 23–27 (Phase 23 OCI backup activated 2026-07-23; restore drill pending). 15 plans, 364→501 tests, 10 days. Full detail: `.planning/MILESTONES.md`.

### v4.0 — Cloud Hosting (shipped 2026-07-17)
Containerized the full stack, hardened daily collection (idempotent + supercronic + health-check), rebuilt the email end-to-end (content + mobile-safe design), and deployed live to Oracle Cloud (Always Free E2.1.Micro) with real HTTPS. Scheduler later moved to GitHub Actions after an Oracle chromium hang. Password gate removed — dashboard now public. 5 phases (19, 20, 20.5, 21, 22), ~60 commits, 22 days. Full detail: `.planning/milestones/v4.0-ROADMAP.md`.

### v3.5 — Index Vol-Context Rebuild (shipped 2026-06-24)
Re-aimed the dashboard at the index income-sleeve PM: VRP percentile (vol-index − RV20, ranked vs history), VIX term-structure regime (SPY-only per CBOE), model-free expected move + 25Δ butterfly, richer OI depth analytics, trust-tagged compact scorecards, full 3-page reorg (Regime/Surfaces/Positioning). 8 phases (15–18 plus 16.5/17.1/18.1 inserts), 344 tests. Full detail: `.planning/milestones/v3.5-ROADMAP.md` (if archived) or ROADMAP.md phase history.

### v3.4 — Email-First Daily Report Polish (shipped 2026-06-02, Phase 14 superseded mid-flight)
Canonical card shared by email + dashboard (single source of truth for card fields); 1-day ΔIV email PNGs replacing static surface images. Accumulation-gating intent (Phase 14) carried forward into v3.5 Phase 18 rather than executed standalone.

### v3.3 — Surface Evolution & Daily Intelligence (shipped 2026-06-01)
Foundation-first surface validation: convex-hull coverage mask as the single source of truth (honest NaN holes), fit residuals. Surface evolution engine — ΔIV decomposed into level/rms/skew/term over 5/10/20 trading-day horizons, persisted daily. Dashboard restructured 5→4 tabs (Surface / Calculus+VRP / Evolution / Positioning). Richer daily email — surface + ΔIV PNG attachments (kaleido 1.3.0), OI call/put wall rows. 12 plans across phases 8–11. Accumulation note: surface_history began 2026-05-28, so evolution/percentile features are cold-started until ~5–20 trading days accrue — the gap that motivated v3.4's single-snapshot pivot.

### v3.0 — GEX Interactive Dashboard (shipped 2026-05-06)
Second-order Greeks (Vanna, Charm), VEX/CHEX exposure, delta-hedge flow, vs-yesterday labels, Streamlit dashboard (Live + Historical tabs). 10 plans, 77 tests, 2 days.

### v2.1 — POC Delivery & Validation (closed 2026-05-05)
Delivered sleeve allocation HTML report (`build_report.py`) to quant team. GEX POC shipped as parallel track (commit 972dc99).

### v2.0 — Sleeve Allocation Framework: Engine Build (closed 2026-05-04)
Seven modules, 74 tests, Holm-Bonferroni rigor. 0 of 30 bucket-mean tests survived correction — honest finding, not failure.

### v1.0 — Regime-Aware Fund Intelligence Notebook (pivoted 2026-04-30)
HMM GMM diagnostic on SPX. Pivoted because it never touched options-pricing data.

---
---
---
---
---
---
---
---
---
---
---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
<!-- LINKS:END -->
