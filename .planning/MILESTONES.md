# Milestones — Options Quant

## v4.0 Cloud Hosting (Shipped: 2026-07-17)

**Phases:** 19, 20, 20.5, 21, 22 | **Plans:** 4 formal (Phase 20.5) + 4 ad-hoc phases (19, 20, 21, 22 executed directly, no formal plan docs)

### Delivered

Took the dashboard + daily email off a local laptop and onto the public internet, running unattended. Containerized the full stack, hardened daily data collection to survive restarts and double-fires, rebuilt the email end-to-end (content and mobile-safe design), and deployed live to Oracle Cloud's Always Free tier with real HTTPS.

### Key Accomplishments

1. Dockerized the full stack — Dockerfile, docker-compose (dashboard + scheduler + Caddy), volume-mounted parquet, SMTP emailer fallback
2. Idempotent `run_daily` + supercronic scheduler + health-check script — safe to double-fire, verifies last-snapshot date per ticker
3. Email rebuilt end-to-end — snapshot-freshness timestamp, methodology caveat banner, mobile-safe 390px width, filter-drop disclosure, higher-res PNG exports — verified via a real dry-run send
4. Deployed live to Oracle Cloud (E2.1.Micro, Always Free) at `https://40.233.113.63.nip.io` with a real Let's Encrypt cert via nip.io (A1.Flex ARM stayed capacity-constrained; retry loop left running in background)
5. Daily scheduler moved from an Oracle-hosted container to GitHub Actions after the Micro instance's first live cron fire hung mid-PNG-export (1 vCPU/1GB couldn't run headless Chromium reliably) — Oracle now just serves the dashboard + Caddy, GitHub Actions rsyncs `out/` down/up around each run
6. Password gate removed — dashboard made intentionally public ahead of linking it from a personal site
7. Ad-hoc fix along the way: VRP percentile widened from a rolling 1yr window to a real ~10yr lookback against CBOE's actual vol-index depth; skew field made directional

### Stats

- Timeline: 2026-06-24 → 2026-07-16 (22 days)
- ~60 commits, 76 files changed, +4510/−1203 lines
- Test count: 344 → 364

### Known Deferred Items at Close (8 — see STATE.md Deferred Items)

- Phase 16.5 UAT: 3 pending human scenarios; Phase 11 & 16.5 verification: human_needed
- 2 stale quick-tasks, 2 pending todos, 1 dormant seed (SEED-001) — all pre-date v4.0

---

## v3.5 — Index Vol-Context Rebuild

**Shipped:** 2026-06-24
**Phases:** 15–18 (incl. 16.5, 17.1, 18.1 inserts) | **Plans:** ~18

### Delivered

Re-aimed the dashboard at the index income-sleeve PM — VRP percentile with deep CBOE vol-index history, VIX term-structure regime (SPY-only; CBOE limitation documented), model-free expected move + 25Δ butterfly, richer OI depth analytics, trust-tagged compact scorecards, and a full 3-page dashboard reorg (Regime → Surfaces → Positioning) with environment-read hero page-1. Dockerized the full stack for cloud deployment.

### Key Accomplishments

1. Vol-index data layer — CBOE CSV fetch/cache for VIX/VXN/RVX + VIX9D/VIX3M; Bloomberg-swappable
2. VRP percentile — vol-index − RV20 ranked over 252-session history; cold-start aware
3. OI depth expansion — expiry concentration, day-over-day OI change, put/call split, top-decile flagging
4. Term-structure regime — SPY VIX9D/VIX/VIX3M raw ratios; QQQ/IWM graceful degradation
5. Convexity & expected move — front-expiry ATM straddle EM + 25Δ butterfly with percentile history
6. Dashboard trust hardening — compact trust-tagged scorecards, 14-DTE primary framing, methods quick/deep
7. 3-page reorg — environment-read hero (risk bar + narrative + key levels + VVIX + net delta), accumulation gating
8. Performance caching — all parquet/filesystem I/O cached in dashboard render path
9. Dockerize — Dockerfile, docker-compose (3 services), Caddy, SMTP emailer fallback

### Stats

- Timeline: 2026-06-05 → 2026-06-24 (20 days)
- Test count: 246 → 344
- 344 tests green

---

## v3.4 — Email-First Daily Report Polish

**Shipped:** 2026-06-02
**Phases:** 12–13 (Phase 14 superseded → Phase 18) | **Plans:** 4

### Delivered

Canonical card shared by email + dashboard; 1-day ΔIV email PNGs replacing static surface images.

---

## v3.3 — Surface Evolution & Daily Intelligence

**Shipped:** 2026-06-01
**Phases:** 8–11 | **Plans:** 12

### Delivered

Convex-hull surface validation, ΔIV evolution engine (5/10/20 horizons), dashboard restructure (5→4 tabs, stored-vs-stored compare, evolution view, OI-led Positioning), richer daily report with surface + ΔIV PNG attachments.

---

## v3.0 — GEX Interactive Dashboard

**Shipped:** 2026-05-06
**Phases:** 1–4 | **Plans:** 10

### Delivered

Extended GEX from a daily email into a live Streamlit dashboard with second-order Greeks (Vanna, Charm), PM flow analytics (delta-hedge $/1%, vs-yesterday regime labels), and a historical context tab (ZGL trend, regime persistence, streak counters, event study).

### Key Accomplishments

1. Added Vanna + Charm to Black-Scholes engine with 0DTE guard; extended `add_greeks()` and 31 tests
2. VEX/CHEX by strike; `delta_hedge_flow` = net_gex / (spot × 0.01); vs-yesterday classification in email table
3. Streamlit app: regime cards, cross-asset chart, per-ticker expanders; COM isolation (no emailer import)
4. Historical tab: 30-day ZGL trend, regime persistence table, streak counter, event study (20-session gate)
5. 77 tests green across the full gex module

### Stats

- Timeline: 2026-05-05 → 2026-05-06 (2 days)
- Files changed: 73 | Lines changed: +6263 / −4566
- Total Python LOC: ~7,275

### Known Deferred Items at Close (2 — see STATE.md)

- Phase 3 UAT: 4 pending human test scenarios
- Phase 3 verification: human_needed items

### Archive

- Roadmap: `.planning/milestones/v3.0-ROADMAP.md`
- Requirements: `.planning/milestones/v3.0-REQUIREMENTS.md`

---

## v2.1 — POC Delivery & Validation

**Shipped:** 2026-05-05

Delivered sleeve allocation HTML report (`build_report.py`) to quant team. Bayesian reframe: conditional summary leads, equity chart removed, Section E caveat added. GEX POC shipped as parallel track (commit 972dc99).

---

## v2.0 — Sleeve Allocation Framework: Engine Build

**Shipped:** 2026-05-04

Seven modules, 74 tests, Holm-Bonferroni rigor. 0 of 30 bucket-mean tests survived correction — honest finding, not failure.

---

## v1.0 — Regime-Aware Fund Intelligence Notebook

**Shipped / Pivoted:** 2026-04-30

HMM GMM diagnostic on SPX. Pivoted because it never touched options-pricing data.

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
<!-- LINKS:END -->
