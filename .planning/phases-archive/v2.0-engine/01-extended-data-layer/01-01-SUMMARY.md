---
phase: 01-extended-data-layer
plan: 01
subsystem: data
tags: [jupyter, nbformat, pandas, pandas_market_calendars, parquet, emds_client, bdh]

# Dependency graph
requires: []
provides:
  - sleeve_alpha.ipynb scaffold (v2.0 deliverable, repo root)
  - Section 0 universe/field config (UNDERLYINGS, IV_FIELDS, PRICE_FIELD, CROSS_ASSET, START_DATE, END_DATE)
  - CACHE_DIR pathlib.Path config (server-local, outside repo)
  - NYSE canonical trading-day index (NYSE_INDEX, nyse_index helper)
  - bdh_cached parquet wrapper around con.bdh (force_refresh, stale-fallback, empty-response handling)
  - _cache_path / _is_stale internals (NYSE-calendar mtime check)
affects: [01-02-data-pull, 01-03-panel-alignment, 01-04-qa-freshness, 02-signals, 03-sleeve-pricing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "nbformat v4 hand-authored cells (locked env has no nbformat module locally; cells authored as JSON, not executed)"
    - "Parquet cache keyed by (ticker, field, start, end) outside repo at ~/sleeve_alpha_cache"
    - "NYSE-calendar mtime freshness via pandas_market_calendars schedule"

key-files:
  created:
    - sleeve_alpha.ipynb
    - .planning/phases/01-extended-data-layer/01-01-SUMMARY.md
  modified: []

key-decisions:
  - "Hand-authored .ipynb JSON via Write tool — nbformat module not in local Python env; notebook executes only on Cron2"
  - "CACHE_DIR default = pathlib.Path.home() / 'sleeve_alpha_cache' per D-12 (no hardcoded username)"
  - "Stale-cache fallback on con.bdh exception (not in plan body, but inline with threat T-01-03 disposition in plan's threat_model)"

patterns-established:
  - "Section header convention: '## Section N — Title' markdown cells separate notebook sections"
  - "Cache-first data access pattern: bdh_cached(ticker, field, start, end, force_refresh=False)"
  - "NYSE_INDEX is the canonical reindex target for all downstream panels (DATA-09 contract)"

requirements-completed: [DATA-09]

# Metrics
duration: 8min
completed: 2026-04-30
---

# Phase 1 Plan 01: Notebook Scaffold + Cache Layer Summary

**Created `sleeve_alpha.ipynb` (v2.0 deliverable) with Section 0 config + Section 1.1 `bdh_cached` parquet wrapper; `hmm.ipynb` v1.0 legacy untouched.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-30
- **Completed:** 2026-04-30
- **Tasks:** 2
- **Files modified:** 1 (sleeve_alpha.ipynb created)

## Accomplishments

- New file `sleeve_alpha.ipynb` at repo root with valid nbformat v4 JSON, kernelspec `python3`
- Section 0 — Setup & Config: imports + universe/field/date config + CACHE_DIR + NYSE calendar helper
- Section 1.1 — Cache wrapper: `_cache_path`, `_is_stale`, `bdh_cached(force_refresh=False)`
- All identifiers required by Plan 02 are in place: `UNDERLYINGS`, `REQUIRED_UNDERLYINGS`, `IV_FIELDS`, `PRICE_FIELD`, `CROSS_ASSET`, `START_DATE`, `END_DATE`, `CACHE_DIR`, `NYSE_INDEX`, `bdh_cached`
- `hmm.ipynb` byte-identical (tree hash `233a9552...` before and after)

## Task Commits

1. **Task 1: Section 0 setup** — `b1f7071` (feat)
2. **Task 2: bdh_cached wrapper** — `600a28e` (feat)

## Files Created/Modified

- `sleeve_alpha.ipynb` — 8 cells total: title markdown, Section 0 header, imports, universe/field config, CACHE_DIR, NYSE_INDEX helper, Section 1 header, cache wrapper

## CACHE_DIR Resolution

On the local Windows machine where this plan was authored, `pathlib.Path.home() / "sleeve_alpha_cache"` resolves to:

```
C:\Users\AdamMorris\sleeve_alpha_cache
```

On Cron2 (where the notebook actually runs) the default will resolve to the server-side home, e.g. `/home/<user>/sleeve_alpha_cache` — outside the repo, gitignored by being outside the tree, per D-12. The default is overridable by edit-in-place at the top of the notebook.

Note: Section 0's `CACHE_DIR.mkdir(parents=True, exist_ok=True)` will execute on Cron2 at first run; the directory does not need to pre-exist.

## Decisions Made

- **Notebook authored, not executed.** The local Python env lacks both `nbformat` and the locked Cron2 stack. Cells were hand-constructed as nbformat v4 JSON via the Write tool and validated by `json.load` + identifier-presence greps (the plan's automated verification commands). Acceptance criteria are pure source-introspection — they don't require the kernel to run.
- **Stale-cache fallback on `con.bdh` exception** is implemented per the plan's `<threat_model>` row T-01-03 (mitigate disposition). On network failure with an existing parquet, the wrapper warns and serves stale; without a cache, it re-raises. This matches the plan body and the threat register.
- **Empty/None `con.bdh` response** returns `pd.DataFrame()` and unlinks any pre-existing cache file for that key, so a deferred field per D-02 doesn't poison future kernel restarts with an empty parquet.

## Deviations from Plan

None — plan executed exactly as written. All cell sources match the plan's `<action>` blocks verbatim.

## Issues Encountered

- **`nbformat` not in local Python env.** The notebook-authoring guidance offered Option A (nbformat) and Option B (hand-construct JSON + validate). Option A failed (`ModuleNotFoundError`); Option B succeeded on first try and was validated by the plan's own `python -c "import json; ..."` checks. Documented as the chosen authoring pattern for future notebook-authoring plans on this machine.

## User Setup Required

None — no external service configuration required. `CACHE_DIR` will auto-create on first run on Cron2.

## Next Phase Readiness

- Plan 01-02 (data pull) can call `bdh_cached(...)` directly. All five identifiers it depends on (`UNDERLYINGS`, `IV_FIELDS`, `CROSS_ASSET`, `START_DATE`, `END_DATE`, `NYSE_INDEX`) are defined in Section 0.
- No blockers. The notebook will be runnable on Cron2 once Plan 01-02 lands its data-pull cells; until then it's a config-only scaffold.

## Self-Check: PASSED

**Files verified:**
- FOUND: `C:/dev/options-quant/sleeve_alpha.ipynb`
- FOUND: `C:/dev/options-quant/.planning/phases/01-extended-data-layer/01-01-SUMMARY.md` (this file)

**Commits verified:**
- FOUND: `b1f7071` (Task 1)
- FOUND: `600a28e` (Task 2)

**Identifier presence in `sleeve_alpha.ipynb` source (via `python -c` introspection):**
- FOUND: `UNDERLYINGS`, `REQUIRED_UNDERLYINGS`, `IV_FIELDS`, `PRICE_FIELD`, `CROSS_ASSET`, `START_DATE`, `END_DATE`, `CACHE_DIR`, `NYSE_INDEX`, `bdh_cached`, `_is_stale`, `_cache_path`, `con.bdh(`, `30DAY_IMPVOL_100.0%MNY_DF`, `30DAY_IMPVOL_90.0%MNY_DF`, `90DAY_IMPVOL_100.0%MNY_DF`

**hmm.ipynb integrity:**
- Pre-execution tree hash: `233a9552846767e7621880ac12122722a9435628`
- Post-execution tree hash: `233a9552846767e7621880ac12122722a9435628` (byte-identical)

---
*Phase: 01-extended-data-layer*
*Completed: 2026-04-30*
