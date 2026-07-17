# Retrospective — Options Quant

---

## Milestone: v3.0 — GEX Interactive Dashboard

**Shipped:** 2026-05-06
**Phases:** 4 | **Plans:** 10

### What Was Built

- Vanna + Charm in BS engine with 0DTE guard; 31 tests
- VEX/CHEX by strike; delta-hedge $/1%, vs-yesterday email labels; 16 tests
- Streamlit dashboard: regime cards, cross-asset chart, per-ticker expanders; COM isolation
- Historical tab: ZGL trend (30-day), regime persistence table, streak counter, event study with 20-session gate; 7 tests

### What Worked

- Strict phase dependency order (1→2→3→4) meant each phase had a clean API contract to build on — no integration surprises
- `add_greeks()` pattern from Phase 1 carried cleanly into Phase 2's VEX/CHEX computation
- `streamlit_app.py` never importing emailer/run_daily was enforced from day one — made the Historical tab refactor easy
- Parquet-first snapshot store with idempotent keying meant no migration issues when schema extended

### What Was Inefficient

- Phase 3 UAT was left in `partial` state — 4 scenarios untested at milestone close; should have been cleared before closing
- Coverage gaps on data_loader, report, emailer, run_daily carried in as unaddressed debt
- Some American-style options (IWM) risk was acknowledged late rather than designed around from the start

### Patterns Established

- Email pipeline and Streamlit as parallel, fully decoupled outputs — validate one without touching the other
- `_classify_vs_yesterday()` label pattern (UNCHANGED / FLIPPED / INTENSIFIED / EASED) — reusable for other metrics
- Per-ticker `@st.cache_data(ttl=300)` + serial fetch + sleep(0.3) as yfinance 429 mitigation

### Key Lessons

- Test fixtures that don't match real data (the `gamma` column gap) silently pass and then fail in integration — fixture should mirror what the live pipeline produces
- Human UAT items should be resolved within the phase, not deferred to milestone close

---

## Milestone: v4.0 — Cloud Hosting

**Shipped:** 2026-07-17
**Phases:** 5 (19, 20, 20.5, 21, 22) | **Plans:** 4 formal (Phase 20.5) + 4 ad-hoc

### What Was Built

- Dockerized full stack: Dockerfile, docker-compose (dashboard + scheduler + Caddy), volume-mounted parquet, SMTP emailer fallback
- Idempotent `run_daily` + supercronic scheduler + health-check script
- Email rebuilt end-to-end: snapshot-freshness line, methodology caveat banner, mobile-safe 390px width, filter-drop disclosure, higher-res PNGs
- Live deploy to Oracle Cloud (E2.1.Micro, Always Free) with real HTTPS via nip.io + Let's Encrypt

### What Worked

- Deploying to the E2.1.Micro AMD64 fallback shape rather than waiting on A1.Flex ARM capacity unblocked the whole milestone — "good enough now" beat "ideal later"
- Real end-to-end dry-run/send verification (not just unit tests) caught the VRP lookback-window gap that unit tests never would have surfaced
- Ad-hoc phases (19–22) executed directly without formal PLAN/SUMMARY docs moved faster for infra work with no ambiguity to negotiate

### What Was Inefficient

- Oracle's first live cron fire hung mid-PNG-export because headless Chromium on a 1 vCPU/1GB instance was never load-tested before going live — cost a same-day scramble to move the scheduler to GitHub Actions
- 6 manual test-trigger iterations were needed to get the GitHub Actions path green (rsync missing on runner, rsync missing on Oracle, root-owned files, flaky ssh-keyscan, empty secret) — each fixable in isolation but not caught by a single pre-flight check
- PROJECT.md and REQUIREMENTS.md were not kept current through v3.5/v4.0 — this milestone close required reconstructing ~6 weeks of drift in one pass

### Patterns Established

- Config-driven visual constants (`KALEIDO_SCALE_FACTOR`) mirror the existing `KALEIDO_CAMERA_EYE` convention — one place to tune rendering, no magic numbers in call sites
- Deploy fixes belong in `fix(deploy):`-prefixed commits distinct from `feat(deploy):` — made the Oracle session's git log self-narrating

### Key Lessons

- Load-test the actual failure mode (headless browser on a memory-constrained VM) before trusting a scheduler to fire unattended in production
- A percentile/rank display is only as trustworthy as its lookback window — "cheap" or "rich" implicitly claims a comparison basis, and that claim should be able to survive being asked "cheap compared to what?"
- Update PROJECT.md at every milestone close, not just some — the cost of catching up compounds with each skipped one

### Cost Observations

- Sessions: ~4 across the milestone (Dockerize, Oracle deploy day, Email Remodel day, this close)
- Notable: the Oracle deploy day did in one session what its ROADMAP phase estimate implied would take longer — capacity-shape pragmatism (E2.1.Micro over waiting for A1.Flex) was the main accelerant

---

## Cross-Milestone Trends

| Milestone | Phases | Plans | Timeline | Tests |
|-----------|--------|-------|----------|-------|
| v3.0 | 4 | 10 | 2 days | 77 |
| v2.1 | — | — | — | — |
| v2.0 | — | — | — | 74 |
| v4.0 | 5 | 4 formal + 4 ad-hoc | 22 days | 344 → 364 |

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
<!-- LINKS:END -->
