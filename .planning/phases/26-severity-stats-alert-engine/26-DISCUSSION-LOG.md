# Phase 26: Severity Statistics & Alert Engine - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-23
**Phase:** 26-severity-stats-alert-engine
**Areas discussed:** False-alarm budget, Change horizons (k), Metric inventory & floors, Alert state & output shape

---

## False-alarm budget

| Option | Description | Selected |
|--------|-------------|----------|
| ~1 episode/week | Bands ~97th–98th on replay; an alert stays a genuine always-read event | ✓ |
| ~2–3 episodes/week | Bands ~95th; more sensitivity, more noise | |
| Let the replay decide | No a-priori rate; pick band whose historical episodes all look worth reading | |

| Option | Description | Selected |
|--------|-------------|----------|
| Permanent CLI script | `python -m engine.monitor.calibrate` — replays ranker over stored history, re-runnable as history deepens | ✓ |
| One-off notebook | Calibrate once, hardcode bands with a comment | |

**Notes:** Hysteresis exit-band width delegated to Claude (set from replay flicker analysis).

---

## Change horizons (k)

| Option | Description | Selected |
|--------|-------------|----------|
| k=5 only | Matches evolution engine's primary horizon; halves test count vs multi-k | ✓ |
| k=1 and k=5 | Adds "broke overnight" lens; 1d noise-dominated, doubles change-tests | |
| k=5,10,20 | Full evolution grid; 3× tests, long-k moves ≈ regime drift already captured by level rank | |

| Option | Description | Selected |
|--------|-------------|----------|
| Two-sided \|Δ\| | One rank per metric, direction in alert text only | ✓ |
| Direction-aware | Alert only on the per-metric "risk" direction | |

---

## Metric inventory & floors

| Option | Description | Selected |
|--------|-------------|----------|
| As drafted | VRP, 25Δ skew, 25Δ fly, evolution level & RMS (×3) + SPY term ratios; evolution scalars level-only | ✓ |
| Drop the 25Δ fly | Thinnest, quote-noise-sensitive, partially redundant with skew | |
| Add IWM–SPY VRP spread now | Deep legs, backfillable; promote from seed | |

| Option | Description | Selected |
|--------|-------------|----------|
| 252 sessions / ~1yr | Only VRP + term ratios alert at ship; chain metrics join ~2027-05 | ✓ |
| 100 sessions / ~5mo | Chain metrics alert ~Oct 2026 on wide sampling error | |
| Keep 60 (CARD_READ_MIN_SESSIONS) | One consistent gate; loosest | |

---

## Alert state & output shape

| Option | Description | Selected |
|--------|-------------|----------|
| New out/monitor/ parquet store | run_daily appends severity rows + alert-events table; hysteresis reads yesterday's row | ✓ |
| Compute-on-read, no store | Deterministic replay everywhere; no frozen daily record | |
| Store ranks, derive alerts | One table; alerts as pure replay function | |

| Option | Description | Selected |
|--------|-------------|----------|
| Persist only | Phase 26 = engine + store + CLI; all surfaces in Phase 27 | ✓ |
| Minimal alert line now | One-line exceptions section in current email as stopgap | |

---

## Claude's Discretion

- Hysteresis exit-band width (from replay flicker analysis)
- Module layout (`engine/monitor/`), store schema details, backfill approach
- `calibrate` CLI output format

## Deferred Ideas

- IWM–SPY VRP spread row (seeded)
- Multi-horizon change ranks (k=1/10/20) — after replay shows what k=5 misses
- Tier-2 conditional base rates — later validation milestone
- Order-statistic CIs on percentile ranks

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
**Phase siblings:**
- [[_planning/vol-diagnostics/phases/26-severity-stats-alert-engine/26-CONTEXT|26-CONTEXT]]

<!-- LINKS:END -->
