---
phase: 01-extended-data-layer
plan: 04
subsystem: data
tags: [jupyter, nbformat, qa, freshness, missingness, data-11, d-13]

# Dependency graph
requires:
  - phase: 01-extended-data-layer
    provides: "Section 0 NYSE_INDEX + warnings/dt/mcal imports (Plan 01); panels prices_panel/iv_panel/iv90_panel/iv90mny/skew_panel + cross-asset Series vix/vvix/rf_rate (Plan 03)"
provides:
  - Section 1.6 — freshness_table DataFrame [underlying, field, last_bar_date, days_stale, status] with warn-not-raise on stale > 5 trading days (D-13)
  - Section 1.7 — qa_table DataFrame [panel, underlying, n, n_valid, miss_pct, first, last] for per-panel missingness diagnostics
  - _last_bar / _trading_days_stale helpers — module-level, reusable downstream
affects: [02-signals, 03-sleeve-pricing, 04-scoring, 05-pm-output]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Freshness verdict via NYSE-calendar trading-day arithmetic: mcal.get_calendar('NYSE').schedule(start_date=last_date, end_date=today), len(schedule) - 1 == days stale (clamped at 0). Weekend/holiday gap is not counted as staleness."
    - "warn-not-raise pattern: warnings.warn(...) on stale rows lets weekend/holiday refreshes complete instead of blocking the kernel. Threshold > 5 trading days = roughly a calendar week's worth of US market days."
    - "Plain-text print(df.to_string(index=False)) over display() — the freshness verdict copy-pastes into a PM email without HTML wrapping; works identically in Jupyter and a piped stdout capture."

key-files:
  created:
    - .planning/phases/01-extended-data-layer/01-04-SUMMARY.md
  modified:
    - sleeve_alpha.ipynb

key-decisions:
  - "Cross-asset Series (vix, vvix, rf_rate) included in freshness_table with underlying='—' rather than a panel name. Keeps the table single-shape (no two passes for PM to scan); the em-dash makes it visually obvious those rows aren't underlying-specific."
  - "Section 1.7 qa_table iterates only the 5 panels — cross-asset Series omitted from missingness QA because they're 1-D and miss_pct duplicates information already in freshness_table. Avoids redundant rows; the freshness verdict carries the empty/stale signal for those Series."
  - "Empty-panel guard in qa_table: 'n == 0' short-circuits miss_pct to 0.0 instead of dividing by zero. Defensive against the impossible-but-cheap case of an empty panel column slipping through (the landed-list filter in Plan 03 should prevent this, but the guard is free)."
  - "freshness_table column order matches D-13 spec verbatim: [underlying, field, last_bar_date, days_stale, status]. No reordering for visual prettiness — the planner-locked schema is the contract."

patterns-established:
  - "Authoring-only execution carries through Plan 04: read JSON → mutate cells → write JSON with indent=1, ensure_ascii=True, CRLF line endings, ASCII-only encoding (em-dashes serialize as \\u2014). All four plans of Phase 1 use the same write convention so byte-level diffs stay readable."
  - "Acceptance grep on concatenated cell sources (no kernel run) is the right test for authoring plans where the data side is server-locked. Plans 02/03/04 all use this pattern; Plan 04 extends it to verify the warn-not-raise discipline (no 'raise' inside Section 1.6/1.7 cells)."

requirements-completed: [DATA-11]

# Metrics
duration: 6min
completed: 2026-04-30
---

# Phase 1 Plan 04: QA / Freshness Table Summary

**Section 1.6 builds freshness_table over panels + cross-asset Series with NYSE-calendar trading-day staleness arithmetic and warn-not-raise per D-13; Section 1.7 prints per-(panel, underlying) missingness diagnostics. Phase 1 authoring is complete.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-04-30
- **Completed:** 2026-04-30
- **Tasks:** 2
- **Files modified:** 1 (`sleeve_alpha.ipynb`: 16 cells → 18 → 20)

## Accomplishments

- Section 1.6 markdown header + freshness_table code cell appended (Task 1, commit `da6e905`)
- Section 1.7 markdown header + qa_table code cell appended (Task 2, commit `959944b`)
- Plan 01 + 02 + 03 cells (0-15) byte-identical to pre-plan baseline (verified via `git show HEAD:sleeve_alpha.ipynb` JSON-cell compare both before and after Task 1)
- `hmm.ipynb` byte-identical (tree hash `233a9552...` unchanged from Plan 01/02/03 baseline)
- All plan acceptance greps pass: `freshness_table`, `days_stale`, `last_bar_date`, `warnings.warn`, `> 5`, `_trading_days_stale`, `qa_table`, `miss_pct`, `n_valid`, `qa_rows`
- Both DataFrame column lists present verbatim in source
- `raise` absent from cells 17 and 19 — D-13 warn-not-raise discipline holds

## Task Commits

1. **Task 1: Build and print freshness_table with staleness warning** — `da6e905` (feat)
2. **Task 2: Add panel-level missingness QA cell** — `959944b` (feat)

Plan-summary metadata commit: `docs(01-04): plan summary` follows this file.

## Files Created/Modified

- `sleeve_alpha.ipynb` — appended 4 cells:
  - Cell 16 (markdown): Section 1.6 header + D-13 warn-not-raise rationale
  - Cell 17 (code): `_last_bar` + `_trading_days_stale` helpers, panel/Series iteration into `rows`, `freshness_table` DataFrame, `print(...to_string(index=False))`, conditional `warnings.warn` on stale rows
  - Cell 18 (markdown): Section 1.7 header + D-09 cross-calendar NaN note
  - Cell 19 (code): `qa_rows` accumulator, panel iteration with `n / n_valid / miss_pct / first / last` per (panel, underlying), `qa_table` DataFrame, `print(...to_string(index=False))`
- `.planning/phases/01-extended-data-layer/01-04-SUMMARY.md` — this file.

## Verification Status — Local vs Cron2

This plan ships **authoring-only** artifacts. The notebook has not been executed (locked Python env on this Windows machine has no `pandas` for the kernel-run side, no `con.bdh`, no Bloomberg-flavoured fields). Acceptance criteria the plan defines are pure JSON source-introspection greps — all pass.

### Verifiable now (verified locally)

- **Plan-defined acceptance greps pass.** Task 1: `freshness_table`, `days_stale`, `last_bar_date`, `warnings.warn`, `> 5`, `_trading_days_stale` all present. Task 2: `qa_table`, `miss_pct`, `n_valid`, `qa_rows` all present.
- **freshness_table column list verbatim:** `"underlying", "field", "last_bar_date", "days_stale", "status"` — matches D-13 schema character-for-character (modulo em-dash JSON-escaping).
- **qa_table column list verbatim:** `"panel", "underlying", "n", "n_valid", "miss_pct", "first", "last"`.
- **Both `print(...to_string(index=False))` calls present** — freshness_table and qa_table both render in plain stdout, no HTML/`display()` dependency.
- **Section markdown headers present:** `### 1.6 Freshness check` and `### 1.7 Panel missingness QA`.
- **D-13 warn-not-raise discipline:** `warnings.warn` present in cell 17; `raise` absent from both cells 17 and 19. Stale data surfaces as a runtime warning, never a kernel halt.
- **Threshold rule:** `days_stale > 5` (strict) and `len(stale_rows) > 0` gate the warning — empty `stale_rows` triggers no warning at all (silent on a fresh-data day).
- **Empty/None branch correctness:** `last_bar_date = None` and `days_stale = None` for empty series; status `"empty"` (not `"stale"`) — empty series do NOT trigger the > 5 warning, since the check is `ds is not None and ds > 5`.
- **NYSE calendar arithmetic:** `_trading_days_stale` uses `mcal.get_calendar("NYSE").schedule(start_date=last_date, end_date=today)`, `len(schedule) - 1`, clamped at 0. Same calendar as `NYSE_INDEX`, so weekend/holiday gaps are not counted as staleness.
- **`today` computation:** `pd.Timestamp(dt.date.today())` — `dt` and `pd` are both imported in Plan 01 Section 0; `mcal` and `warnings` likewise. No new imports introduced.
- **Notebook still valid nbformat v4 JSON after each append** — `json.load` succeeds; cell count progressed 16 → 18 → 20 with no schema errors.
- **Cells 0-15 byte-identical across both task commits** — JSON-serialized comparison vs `git show HEAD:sleeve_alpha.ipynb` after each commit shows zero drift in prior cells. Diff stays additive.
- **`hmm.ipynb` byte-identical** — `git rev-parse HEAD:hmm.ipynb` returns `233a9552846767e7621880ac12122722a9435628` (matches Phase-1-baseline).
- **File encoding preserved:** ASCII-only bytes (em-dashes serialize as `—`), CRLF line endings throughout, file ends with CRLF + EOF — matches the existing notebook style.

### Pending Cron2 run (cannot verify locally)

This is the final plan in Phase 1, so the pending list is also the **phase-level Cron2 closeout list**:

- **Actual `freshness_table` row count.** Equals `sum(panel.columns count for the 5 panels) + 3 (cross-asset Series)`. With SPX + QQQ guaranteed and XIU/XSP/iv90 best-effort, the count varies between roughly `2 * 5 + 3 = 13` (SPX + QQQ only) and `4 * 5 + 3 = 23` (everything lands). **`[pending Cron2 run]`**
- **Actual `days_stale` values.** Will reflect the real lag between `con.bdh` last-trade dates and `dt.date.today()` on the day the cell runs. On a fresh weekday with same-day data, expect `days_stale = 0` for most rows; on Monday morning before data refresh, expect `days_stale = 1` (Friday is the last bar). The strict `> 5` threshold means a normal weekend gap should never trigger the warning. **`[pending Cron2 run]`**
- **Whether the staleness warning fires today.** It shouldn't — the `> 5` threshold is wide. If it does fire, the warning text identifies the worst row and prompts `force_refresh=True`. **`[pending Cron2 run]`**
- **Per-panel missingness %.** D-09 predicts ~5 NaN/yr per Canadian underlying (XIU, XSP) in NYSE-canonical reindex from TSX-only holidays — that's `~5 / ~252 ≈ 2%` miss_pct on those columns. SPX and QQQ should be `0%` miss across all panels. iv90_panel may be sparser (the 90D ATM IV probe in D-03 is best-effort). **`[pending Cron2 run]`**
- **Whether `iv90_panel` covers all `landed` underlyings.** D-03 added 90D ATM IV as a probe; it could land for the full landed set, a subset, or be entirely missing. Plan 03's column-intersection logic in `iv90_panel_full` degrades gracefully either way. **`[pending Cron2 run]`**
- **Visual sanity:** the printed `freshness_table` and `qa_table` should fit on one screen each (≤ ~25 rows). If row count exceeds that, the planner can revisit to add a per-panel summary roll-up — for v2.0 with at most 4 underlyings × 5 panels + 3 cross-asset = 23 rows, single-screen display is fine. **`[pending Cron2 run]`**

After running Section 1.6 and 1.7 cells on Cron2, the operator should append captured outputs (the printed `freshness_table`, the printed `qa_table`, any `UserWarning` traceback) into this section to close out the pending items.

## Phase 1 Authoring Closeout

**Plan 01-04 is the final plan in Phase 1.** Phase deliverables are authoring-complete:

- **Section 0** — Setup & Config (Plan 01 cells 0-5): UNDERLYINGS / CROSS_ASSET sets, CACHE_DIR, `nyse_index`, `NYSE_INDEX`, all imports (`pandas as pd`, `numpy as np`, `pathlib`, `datetime as dt`, `warnings`, `pandas_market_calendars as mcal`, `emds_client`).
- **Section 1.1** — `_cache_path` + `bdh_cached` parquet wrapper (Plan 01 cells 6-7).
- **Section 1.2** — `raw_pulls` per-underlying dict-of-dicts of `con.bdh` price + IV pulls with `_log_deferred` documenting non-landed fields (Plan 02 cells 8-9).
- **Section 1.3** — `raw_cross` cross-asset dict of `con.bdh` VIX, VVIX, USGG3M pulls (Plan 02 cells 10-11).
- **Section 1.4** — `prices_panel`, `iv_panel`, `iv90_panel`, `iv90mny`, `skew_panel` panel assembly with NYSE-canonical reindex and D-04 truncation to shortest IV history (Plan 03 cells 12-13).
- **Section 1.5** — `vix`, `vvix`, `rf_rate` cross-asset Series with `assert s.index.equals(prices_panel.index)` alignment contract (Plan 03 cells 14-15).
- **Section 1.6** — `freshness_table` printout + `warnings.warn` on stale > 5 trading days (Plan 04 cells 16-17).
- **Section 1.7** — `qa_table` per-panel missingness printout (Plan 04 cells 18-19).

**Goal-level verification (notebook runs end-to-end on a fresh Cron2 kernel and produces non-empty panels with the freshness table printing) is the user's gate, not the local executor's.** This Windows machine cannot run Cron2's locked Python env — every Phase 1 plan ships authoring-side artifacts and acceptance greps; the runtime verdict happens on Cron2.

### Identifiers exposed to Phase 2

- **Wide DataFrames:** `prices_panel`, `iv_panel`, `iv90_panel`, `iv90mny`, `skew_panel` (all NYSE-canonical, D-04-truncated)
- **Standalone Series:** `vix`, `vvix`, `rf_rate` (sharing `prices_panel.index`, asserted in Section 1.5)
- **Helpers reusable downstream:** `bdh_cached` (Plan 01), `_to_series` / `_build_panel` / `_to_named_series` (Plan 03), `_last_bar` / `_trading_days_stale` (Plan 04)
- **Module-level scalars:** `NYSE_INDEX`, `truncate_start`, `landed`, `UNDERLYINGS`, `CROSS_ASSET`, `CACHE_DIR`
- **Diagnostic outputs:** `freshness_table` (DataFrame, persistent in scope after Section 1.6 runs), `qa_table` (DataFrame, persistent after Section 1.7 runs)

Phase 2 (signals) can `from sleeve_alpha import *`-equivalent (cell-execute Sections 0-1) and immediately have all panels, Series, and the QA verdicts materialized. No re-pull, no re-truncation, no calendar arithmetic needed in signal cells.

## Decisions Made

- **Cross-asset Series rows in `freshness_table` use `underlying = "—"` (em-dash).** Keeps the table single-shape so a PM scans one DataFrame, not two. The em-dash visually distinguishes 1-D Series rows from per-underlying panel rows. JSON-serialized as `—` in the notebook source per the existing `ensure_ascii=True` convention.
- **Section 1.7 (`qa_table`) iterates panels only, not cross-asset Series.** The freshness_table already covers `vix`/`vvix`/`rf_rate` empty-or-not. Adding them to qa_table would duplicate that signal. The two QA cells split responsibilities cleanly: 1.6 = freshness + completeness, 1.7 = per-panel missingness depth.
- **Section 1.6 cell defines two helpers (`_last_bar`, `_trading_days_stale`) at the top before iteration.** Easier to read than nested helpers; kernel-scope availability for ad-hoc PM debugging on Cron2 if a row looks suspect.
- **Strict `>` (not `>=`) on the > 5 threshold.** D-13 specifies "stale > 5 trading days"; using `>` means exactly 5 days stale is still `fresh`. Matches the exact wording of the decision and gives one extra trading day of slack.
- **`stale` status check is `ds is not None and ds > 5`, not just `ds > 5`.** Avoids a `TypeError: '>' not supported between None and 5` when `last_bar_date is None`. `None > 5` raises in Python 3. The `ds is not None` guard is paired with the `lb is None` branch above for completeness.

## Deviations from Plan

None — plan executed exactly as written. Cell sources match the plan's `<action>` blocks character-for-character (modulo the em-dash JSON-escaping). No Rule 1/2/3 auto-fixes triggered. CLAUDE.md constraints (no inline comments, Cron2-only, no kernel run, locked env, `hmm.ipynb` untouched) all honored.

## Issues Encountered

- **Pre-existing `STATE.md` modification in working tree** at session start, untouched by this plan; left alone per `commit_docs: false` in `.planning/config.json`. Same as Plans 02 and 03.
- **Two scratch scripts (`_scratch_append_t1.py` / `_scratch_append_t2.py`)** created and immediately deleted per task to drive the JSON append. Working-tree-clean by end of each task; never committed. Same pattern as Plans 02/03.
- **Initial scratch draft used `json.dumps(..., indent=1)` with default `\n` line endings; corrected before write** to match the existing notebook's CRLF convention by post-processing `text.replace("\r\n", "\n").replace("\n", "\r\n")` and writing as ASCII bytes. Final notebook bytes match Plan 01/02/03 style exactly.

## User Setup Required

None — no external service configuration required. Cells run on Cron2 with the existing `con` connection and the `prices_panel` / `iv_panel` / `iv90_panel` / `iv90mny` / `skew_panel` / `vix` / `vvix` / `rf_rate` already in kernel scope from Sections 0-1.5.

## Next Phase Readiness

- **Phase 2 (signals) is unblocked.** All Phase 2 inputs exist as named identifiers in Section 1's kernel scope after a fresh-kernel run. The freshness_table is the gate the operator reads before running Phase 2 cells; if it shows `stale` rows, the operator re-runs Section 1.2/1.3 with `force_refresh=True` before signal computation.
- **DATA-11 substantively complete.** `freshness_table` schema and warn-not-raise wiring are both in place. Marking it complete in REQUIREMENTS.md is appropriate; Cron2-side observation of actual `days_stale` values is a runtime check, not an authoring requirement.
- **Phase 1 closeout.** All seven Phase 1 requirements (DATA-06 through DATA-12) are authored on the notebook side. The `goal-level` verdict — "notebook runs end-to-end on a fresh Cron2 kernel and produces non-empty panels with the freshness table printing" — is the user's gate, run on Cron2.
- **No blockers.**

## Self-Check: PASSED

**Files verified:**
- FOUND: `C:/dev/tq-hmm/sleeve_alpha.ipynb` (20 cells, valid nbformat v4.5 JSON, CRLF line endings, ASCII-only bytes, trailing CRLF)
- FOUND: `C:/dev/tq-hmm/.planning/phases/01-extended-data-layer/01-04-SUMMARY.md` (this file)

**Commits verified (`git log --oneline`):**
- FOUND: `da6e905` (Task 1: add freshness_table with days_stale > 5 warning)
- FOUND: `959944b` (Task 2: add panel-level missingness QA cell)

**Identifier presence in `sleeve_alpha.ipynb` source (via `python -c` introspection):**
- FOUND: `freshness_table`, `days_stale`, `last_bar_date`, `warnings.warn`, `> 5`, `_trading_days_stale`
- FOUND: `qa_table`, `miss_pct`, `n_valid`, `qa_rows`, `qa_table.to_string(index=False)`
- FOUND: `freshness_table.to_string(index=False)`
- FOUND: column-list strings exactly: `"underlying", "field", "last_bar_date", "days_stale", "status"` and `"panel", "underlying", "n", "n_valid", "miss_pct", "first", "last"`
- FOUND: section headers `### 1.6 Freshness check` and `### 1.7 Panel missingness QA`
- ABSENT: `raise` inside cells 17 and 19 (D-13 warn-not-raise discipline)

**`hmm.ipynb` integrity:**
- Pre-Plan-04 tree hash: `233a9552846767e7621880ac12122722a9435628`
- Post-Plan-04 tree hash: `233a9552846767e7621880ac12122722a9435628` (byte-identical)

**Plan 01 + 02 + 03 cells preserved:**
- Cells 0-15 (markdown title, Section 0 setup, Section 1 + 1.1 cache wrapper, 1.2 raw_pulls, 1.3 raw_cross, 1.4 panels, 1.5 cross-asset Series) — JSON-serialized comparison vs `git show HEAD~2:sleeve_alpha.ipynb` shows all 16 cells byte-identical after both Task 1 and Task 2 commits.

---
*Phase: 01-extended-data-layer*
*Completed: 2026-04-30*
*Final plan of phase — Phase 1 authoring complete.*
