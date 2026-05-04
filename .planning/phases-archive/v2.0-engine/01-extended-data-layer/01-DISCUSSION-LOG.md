# Phase 1: Extended Data Layer - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-30
**Phase:** 01-extended-data-layer
**Areas discussed:** Universe rollout, Panel data structure, Multi-calendar alignment, Caching / re-pull

---

## Universe rollout

### Q1: How aggressive should the Phase 1 pull be on the universe?

| Option | Description | Selected |
|--------|-------------|----------|
| All four upfront, defer-on-fail | Probe SPX/QQQ/XIU/XSP in one block; log + continue on field-miss | ✓ |
| SPX/QQQ first, XIU/XSP later | Engine green on US first, Canadian probe in Phase 1.1 | |
| SPX-only first | Conservative single-underlying spike | |

**User's choice:** All four upfront, defer-on-fail.

### Q2: When `con.bdh` returns nothing for an IV field, what should the loader do?

| Option | Description | Selected |
|--------|-------------|----------|
| Log + defer | Print field tried, row count, "deferred" marker; cell stays green | ✓ |
| Raise an error | Hard fail forces resolution | |
| Substitute a proxy | E.g. VIX-implied for missing IV | |

**User's choice:** Log + defer.

### Q3: Which optional fields should Phase 1 also probe?

| Option | Description | Selected |
|--------|-------------|----------|
| 90D ATM IV (term-structure) | Pulls forward STATE.md todo; SIG-06 fragility composite needs term-shape | ✓ |
| VVIX | Optional fragility-composite input; one-line addition to VIX pull | ✓ |
| 60D ATM IV | Mid-tenor for richer term-structure | |
| Skew leg at 110% moneyness | Symmetric upside skew; useful for collar pricing | |

**User's choice:** 90D ATM IV + VVIX.

### Q4: History start date — IV history is shorter than price history.

| Option | Description | Selected |
|--------|-------------|----------|
| Truncate prices to IV history | Align everything to shortest IV-available start | ✓ |
| Keep prices full, IV starts when available | Two date ranges in panel; allows long-history trend | |
| You decide | Claude picks based on SIG-04 needs | |

**User's choice:** Truncate prices to IV history.

---

## Panel data structure

### Q1: Shape of the canonical panels (`prices_panel`, `iv_panel`, `skew_panel`)?

| Option | Description | Selected |
|--------|-------------|----------|
| Wide DataFrame per measure | One DF per measure, columns = underlyings, index = trading days | ✓ |
| MultiIndex DataFrame | Single DF with hierarchical columns (date × underlying × measure) | |
| Dict of wide DataFrames | Same content as wide, wrapped in a dict | |

**User's choice:** Wide DataFrame per measure (date × underlying).

### Q2: Where do VIX, VVIX, risk-free rate live?

| Option | Description | Selected |
|--------|-------------|----------|
| Separate named Series | `vix`, `vvix`, `rf_rate` as standalone Series alongside panels | ✓ |
| Bolt onto prices_panel as columns | Convenient but conceptually wrong | |
| Fourth panel: `macro_panel` | Symmetric with other panels but adds a name | |

**User's choice:** Separate named Series.

### Q3: Calendar handling for missing dates within a single underlying?

| Option | Description | Selected |
|--------|-------------|----------|
| Reindex to NYSE calendar, leave NaN | Canonical NYSE index, no imputation | ✓ |
| Reindex + forward-fill | Convenient for plotting but lies about freshness | |
| Drop missing | Inner-join across all series | |

**User's choice:** Reindex + leave NaN.

---

## Multi-calendar alignment

### Q1: When NYSE and TSX disagree, what is the canonical index?

| Option | Description | Selected |
|--------|-------------|----------|
| NYSE-only canonical, TSX series reindexed | TSX-only holidays → NaN for XIU/XSP; NYSE-only holidays drop entirely | ✓ |
| Union calendar with explicit NaN | NYSE ∪ TSX; ~10 mostly-empty days/yr | |
| Intersection calendar (NYSE ∩ TSX) | Both markets open; loses ~10 SPX/QQQ days/yr | |
| Skip — only matters if XIU/XSP land | Defer to Phase 1.1 | |

**User's choice:** NYSE-only canonical, TSX series reindexed.
**Rationale captured:** US-led overlay menu (PDIV, SPX/QQQ-anchored sleeves).

---

## Caching / re-pull

### Q1: Should Phase 1 cache `con.bdh` pulls to parquet?

| Option | Description | Selected |
|--------|-------------|----------|
| Parquet cache + freshness toggle | Pull writes parquet; reload checks mtime (>1 trading day = re-pull); explicit `force_refresh=True` | ✓ |
| Always re-pull | Hits `con.bdh` every kernel restart | |
| One-shot pull, manual snapshot | Load once, comment out cell | |
| You decide | Claude picks based on iteration patterns | |

**User's choice:** Parquet cache + freshness toggle.

### Q2: Where should the cache live?

| Option | Description | Selected |
|--------|-------------|----------|
| `data/cache/` (gitignored) | Local cache inside repo, never committed | |
| `.cache/` at repo root | Outside `data/`, top-level dir | |
| Server-side scratch dir | Cron2 server's user scratch, outside repo | ✓ |

**User's choice:** Server-side scratch dir.

### Q3: Server-side scratch path?

| Option | Description | Selected |
|--------|-------------|----------|
| `~/sleeve_alpha_cache/` | User home dir, persistent | |
| `/tmp/sleeve_alpha_cache/` | System tmp, may be wiped | |
| Same pattern as deck-auto / hmm.ipynb cache | Mirror existing convention | |
| TBD — capture as a config-cell variable | Top-of-notebook config (`CACHE_DIR = pathlib.Path(...)`) | |

**User's choice (free text):** "well i am on a server no github just store it in a foldr on the server and if it is parquet files it will be small"
**Captured as:** Server-side folder outside the repo (no GitHub commits), parquet files (small, no size concerns). Specific path surfaced as a top-of-notebook `CACHE_DIR` config variable; reasonable default `~/sleeve_alpha_cache/`.

### Q4: Freshness check format?

| Option | Description | Selected |
|--------|-------------|----------|
| Stale-table + inline `warnings.warn` | Print `[underlying, field, last_bar_date, days_stale, status]`; warn if any > 5 | ✓ |
| Print-only | Quiet, easy to miss | |
| Raise on stale | Blocks weekend / holiday runs | |

**User's choice:** Stale-table + inline `warnings.warn`.

---

## Claude's Discretion

- Exact `con.bdh` field-probe order and loop / dict-comprehension shape
- Log message format for deferred fields
- Cache key format and parquet schema
- QA cell layout beyond freshness table (`n` per underlying, missingness %, first/last bar dates)
- Cell breaks and markdown headings within Section 1 of `sleeve_alpha.ipynb`
- Colour palette / figure scaffolding
- Specific 3M T-bill field choice for risk-free (whatever returns clean via `con.bdh`)

## Deferred Ideas

- 60D ATM IV → Phase 2 if 30D vs 90D too coarse
- 110%-mny skew leg → Phase 3, only if trivially available; otherwise parametric upside skew
- TSX-canonical / intersection / union calendars → revisit only if universe pivots Canada-led
- Dated snapshot parquets (SLV-07 / OUT-05) → Phase 5 owns these; distinct from Phase 1's kernel-restart cache
- Canadian T-bill for XIU/XSP option pricing → not on v2.0 menu; US 3M T-bill universal
- PDIV current overlay rule capture → Phase 7/β prerequisite, stays in STATE.md todos
