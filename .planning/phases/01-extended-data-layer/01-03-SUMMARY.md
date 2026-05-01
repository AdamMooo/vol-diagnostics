---
phase: 01-extended-data-layer
plan: 03
subsystem: data
tags: [jupyter, nbformat, pandas, panel-assembly, nyse-index, cross-asset]

# Dependency graph
requires:
  - phase: 01-extended-data-layer
    provides: "Section 0 NYSE_INDEX + UNDERLYINGS + CROSS_ASSET (Plan 01); raw_pulls dict-of-dicts and raw_cross dict from bdh_cached pulls (Plan 02)"
provides:
  - Section 1.4 — panel assembly (prices_panel, iv_panel, iv90_panel, iv90mny, skew_panel) via _to_series + _build_panel helpers, NYSE_INDEX-reindexed and D-04 truncated
  - Section 1.5 — cross-asset standalone Series (vix, vvix, rf_rate) via _to_named_series, same NYSE_INDEX + truncate_start, with assert-loop alignment contract
  - landed list — column-membership filter for panels (D-02 deferral surface)
  - truncate_start — module-level scalar = max of per-underlying first IV date (D-04)
affects: [01-04-qa-freshness, 02-signals, 03-sleeve-pricing, 04-scoring]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Panel-assembly closure: _to_series defends with .squeeze() + DataFrame fallback + DatetimeIndex normalize before reindex(NYSE_INDEX)"
    - "Column-membership filter: landed = underlyings with non-empty price + iv30_atm + iv30_90mny; deferred underlyings simply absent from panels (D-02)"
    - "D-04 truncation: truncate_start = max(per-underlying first IV date), then mask = NYSE_INDEX >= truncate_start applied to all panels and Series uniformly"
    - "Cross-asset alignment contract: assert s.index.equals(prices_panel.index) on every cross-asset Series — fails loudly if alignment drifts in future edits"

key-files:
  created:
    - .planning/phases/01-extended-data-layer/01-03-SUMMARY.md
  modified:
    - sleeve_alpha.ipynb

key-decisions:
  - "iv90mny vs iv90_panel naming kept per plan: iv90mny = 30D 90%-mny IV (D-06 skew leg), iv90_panel = 90D ATM IV (D-03 term-structure probe). Avoids the name collision in CONTEXT D-06's prose (which used iv90_panel for the skew leg)."
  - "skew_panel computed on column intersection (common_skew_cols) — drops columns where iv90mny is empty for that underlying rather than producing all-NaN columns. Phase 2 signal code can rely on every skew_panel column being computable."
  - "Empty-cross-asset path returns all-NaN Series with NYSE_INDEX (then sliced to truncate_start), not a missing key — keeps downstream .align / arithmetic behavior uniform whether VVIX or rf_rate landed or not."
  - "iv90_panel kept as a module-level identifier (not just an intermediate) so future term-structure work (Phase 2 SIG-04 follow-on) can import it without re-pulling."

patterns-established:
  - "Authoring-only execution carries forward from Plan 02: read JSON → mutate → write JSON. Cells stay valid nbformat v4. Acceptance via source-introspection grep, not kernel run."
  - "_to_series and _to_named_series share defensive shape-handling (.squeeze() → iloc[:, 0] fallback → DatetimeIndex.normalize() → reindex). Future cells reshaping single-column con.bdh frames should reuse this pattern."

requirements-completed: [DATA-12]

# Metrics
duration: 8min
completed: 2026-04-30
---

# Phase 1 Plan 03: Panel Assembly + Cross-Asset Series Summary

**Section 1.4 builds prices_panel / iv_panel / iv90_panel / iv90mny / skew_panel as wide DataFrames on NYSE_INDEX with D-04 shortest-IV truncation; Section 1.5 exposes vix / vvix / rf_rate as standalone Series sharing that index, with an assert-loop alignment contract.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-30
- **Completed:** 2026-04-30
- **Tasks:** 2
- **Files modified:** 1 (`sleeve_alpha.ipynb`: 12 cells → 14 → 16)

## Accomplishments

- Section 1.4 markdown header + panel-assembly code cell appended (Task 1, commit `445c844`)
- Section 1.5 markdown header + cross-asset Series code cell appended (Task 2, commit `be2e90e`)
- Plan 01 + Plan 02 cells (0-11) byte-identical to pre-plan baseline (verified via `git show 5729774:sleeve_alpha.ipynb` cell-by-cell JSON compare)
- `hmm.ipynb` byte-identical (tree hash `233a9552...` unchanged from Plan 02 baseline)
- All plan-level identifier checks pass: `prices_panel`, `iv_panel`, `iv90_panel`, `iv90mny`, `skew_panel`, `vix`, `vvix`, `rf_rate`, `truncate_start`, `.reindex(NYSE_INDEX)` all present
- Zero `.fillna` references anywhere in the notebook (D-08 honored — no imputation)

## Task Commits

1. **Task 1: Build prices_panel, iv_panel, iv90_panel, iv90mny, skew_panel** — `445c844` (feat)
2. **Task 2: Expose vix, vvix, rf_rate as standalone Series** — `be2e90e` (feat)

Plan-summary metadata commit: deferred to `docs(01-03): plan summary` once this file lands.

## Files Created/Modified

- `sleeve_alpha.ipynb` — appended 4 cells:
  - Cell 12 (markdown): Section 1.4 header + naming-convention note (iv90mny vs iv90_panel)
  - Cell 13 (code): `_to_series` + `_build_panel` helpers, `landed` filter, four `*_full` panel builds, D-04 `truncate_start` computation, mask-and-truncate of all four panels, `skew_panel` arithmetic
  - Cell 14 (markdown): Section 1.5 header + D-07 rationale (Series, not panel-bolt-on)
  - Cell 15 (code): `_to_named_series` (with empty-source path → all-NaN Series), three Series assignments, assert-loop alignment contract
- `.planning/phases/01-extended-data-layer/01-03-SUMMARY.md` — this file.

## Verification Status — Local vs Cron2

This plan ships **authoring-only** artifacts. The notebook has not been executed (locked Python env on this Windows machine has no `pandas` for the kernel-run side, no `con.bdh`, no Bloomberg-flavoured fields). Acceptance criteria the plan defines are pure JSON source-introspection greps — all pass.

### Verifiable now (verified)

- **All required panel/Series identifiers present** in concatenated cell sources via grep: `prices_panel`, `iv_panel`, `iv90_panel`, `iv90mny`, `skew_panel`, `vix`, `vvix`, `rf_rate`, `truncate_start`.
- **Reindex calls present** — `.reindex(NYSE_INDEX)` used in both `_build_panel` (per-underlying loop) and `_to_named_series` (cross-asset path).
- **No imputation** — zero `.fillna` calls anywhere in the notebook (D-08).
- **D-06 skew formula correct** — exact string `skew_panel = iv90mny[common_skew_cols] - iv_panel[common_skew_cols]` present in Section 1.4 source.
- **D-04 truncation logic correct** — `truncate_start = max(iv_first_dates) if iv_first_dates else NYSE_INDEX.min()` present; mask applied to all four `*_full` panels uniformly.
- **D-05 panel names match REQUIREMENTS.md verbatim** — `prices_panel`, `iv_panel`, `skew_panel` (the three canonical handoff panels). `iv90_panel` and `iv90mny` are intermediates.
- **D-07 standalone Series** — `vix`, `vvix`, `rf_rate` defined as `pd.Series` (the assert in Section 1.5 will fail at runtime if any of them isn't), not as columns of a panel.
- **D-08 no imputation in cross-asset empty path** — `pd.Series(index=NYSE_INDEX, dtype="float64", name=name)` produces an all-NaN Series, not a zero-filled or forward-filled one.
- **Section 1.5 alignment contract present** — `assert s.index.equals(prices_panel.index)` loop runs on `(vix, vvix, rf_rate)`; fails loudly on drift.
- **Plan 01 + 02 cells byte-identical** — cells 0-11 unchanged vs `5729774:sleeve_alpha.ipynb` (verified by JSON-serialized comparison).
- **`hmm.ipynb` byte-identical** — `git rev-parse HEAD:hmm.ipynb` returns `233a9552846767e7621880ac12122722a9435628` (matches Plan 01/02 baseline).
- **Notebook valid nbformat v4 JSON after each append** — `json.load` succeeds; cell count progressed 12 → 14 → 16 with no schema errors.
- **Diff stays additive** — `git diff` for both task commits shows only insertions, zero deletions, zero context-line modifications.

### Pending Cron2 run (cannot verify locally)

- **`landed` list contents.** Plan 02 ships `UNDERLYINGS = {SPX, QQQ, XIU, XSP}`; SPX/QQQ are required (Plan 02 raises if missing). `landed` is whichever subset has non-empty `price + iv30_atm + iv30_90mny` after the Cron2 pull. Whether XIU and/or XSP land is determinable only from the Cron2 stdout. **`[pending Cron2 run]`**
- **`iv90_panel` column count.** D-03 added 90D ATM IV as a probe; whether it's available for all `landed` underlyings or only some is a Cron2-side question. The `iv90_panel_full` build filters to underlyings with non-empty `iv90_atm`, so a sparse landing pattern degrades gracefully. **`[pending Cron2 run]`**
- **`truncate_start` value.** Will be `max(per-underlying first IV date across the landed set)`. SPX 30D IV history starts later than SPX price history; XIU/XSP IV history (if landed) likely starts later still. The actual date depends on which underlyings ended up in `landed` and what their first IV dates are. **`[pending Cron2 run]`**
- **`skew_panel` column count.** Equals `len([c for c in iv_panel.columns if c in iv90mny.columns])`. Should match `len(landed)` for the typical case where every underlying has both IV legs, but could be smaller if iv30_90mny is sparse for an underlying iv30_atm landed for. **`[pending Cron2 run]`**
- **Whether the assert in Section 1.5 fires.** It shouldn't — `_to_named_series` always returns a Series indexed on `NYSE_INDEX[NYSE_INDEX >= truncate_start]`, which equals `prices_panel.index` by construction. But the assert is the contract that proves it; any future edit that breaks alignment will trigger it. **`[verifies on Cron2 run]`**

After running Section 1.4 and 1.5 cells on Cron2, the operator should append captured outputs (the `Landed underlyings:` line, the `Truncating panels to start=...` line, panel `.shape` introspections) into this section to close out the four pending items.

## Decisions Made

- **Honored the planner's `iv90mny` vs `iv90_panel` naming choice verbatim.** The CONTEXT D-06 prose used `iv90_panel` to mean the 90%-mny skew leg, but D-03 also added 90D ATM IV — same notation collision the plan called out. Using `iv90mny` for the skew leg and `iv90_panel` for the term-structure probe keeps both identifiers expressive without overloading. Markdown cell explains the convention so the next reader doesn't have to chase it.
- **`skew_panel` built on column intersection, not full `landed` list.** If iv90mny is empty for some underlying that has iv_panel data, that underlying simply drops out of `skew_panel` rather than appearing as an all-NaN column. Phase 2 signal code can rely on `for col in skew_panel.columns:` always being valid skew data, no guard needed.
- **Empty-cross-asset path returns NaN-Series sliced to `truncate_start`, not raw NaN-Series.** The slice is what makes `s.index.equals(prices_panel.index)` true even when VVIX or rf_rate didn't land. Without the slice, the assert would fire on any operator who triggered the rf_rate-empty `warnings.warn` path in Plan 02.
- **`iv_first_dates` skips underlyings whose `iv_panel_full[u].dropna()` is empty.** Defensive against the impossible-but-cheap case where `landed` includes an underlying whose IV column ended up all-NaN after reindex (shouldn't happen given the `landed` filter requires non-empty `iv30_atm`, but the `if len(s):` guard costs nothing and prevents `max([])` from raising).

## Deviations from Plan

None — plan executed exactly as written. Cell sources match the plan's `<action>` blocks character-for-character (modulo the em-dash that the JSON encoder serializes as `—` per ensure_ascii=True). No Rule 1/2/3 auto-fixes triggered.

## Issues Encountered

- **Windows Python `print` crashes on Greek/em-dash characters by default** (the `cp1252` codec can't encode `α` or `—`). Resolved by setting `PYTHONIOENCODING=utf-8` for every introspection invocation. Same issue Plan 02 hit; same fix. Doesn't affect committed artifacts — the notebook stores em-dashes as `—` per the existing `ensure_ascii=True` convention.
- **Pre-existing `STATE.md` modification in working tree** at session start, untouched by this plan; left alone per `commit_docs: false` in `.planning/config.json`.
- **One scratch script (`_scratch_append.py` / `_scratch_append2.py`) created and immediately deleted per task** to drive the JSON append. Working-tree-clean by end of each task; never committed.

## User Setup Required

None — no external service configuration required. Cells run on Cron2 with the existing `con` connection and the `raw_pulls` / `raw_cross` already populated by Plan 02.

## Next Phase Readiness

- **Plan 01-04 (QA + freshness table) can read directly from the canonical handoff identifiers.** `prices_panel`, `iv_panel`, `iv90_panel`, `skew_panel` are wide DataFrames on the same index; `vix`, `vvix`, `rf_rate` are Series sharing that index. The DATA-11 freshness check needs a [underlying, field, last_bar_date, days_stale, status] table — the panels and Series are exactly the right shape for that.
- **Phase 2 signals can `.align(prices_panel)` against any cross-asset Series without surprises** (the assert in Section 1.5 is the contract).
- **Phase 3 BS pricing has `rf_rate` available** as a date-indexed Series; if Plan 02's `warnings.warn` path fired on Cron2, Phase 3 BS pricing will need to handle the all-NaN case (downstream concern, not Phase 1 work).
- **DATA-12 substantively complete on the authoring side.** Marking it complete in REQUIREMENTS.md is appropriate; the `landed`-list confirmation and `truncate_start` value are Cron2-side data observations rather than authoring-side requirements.
- **DATA-09 (NYSE-canonical alignment) reinforced.** Every panel and Series in this plan is built via `.reindex(NYSE_INDEX)` and sliced by `truncate_start`. TSX-only holidays will materialize as NaN in XIU/XSP columns when the cells run on Cron2 (D-09 expected behavior).
- No blockers.

## Self-Check: PASSED

**Files verified:**
- FOUND: `C:/dev/tq-hmm/sleeve_alpha.ipynb` (16 cells, valid nbformat v4 JSON, CRLF line endings, trailing newline)
- FOUND: `C:/dev/tq-hmm/.planning/phases/01-extended-data-layer/01-03-SUMMARY.md` (this file)

**Commits verified (`git log --oneline`):**
- FOUND: `445c844` (Task 1: build prices_panel, iv_panel, iv90_panel, skew_panel)
- FOUND: `be2e90e` (Task 2: expose vix, vvix, rf_rate as standalone Series)

**Identifier presence in `sleeve_alpha.ipynb` source (via `python -c` introspection):**
- FOUND: `prices_panel`, `iv_panel`, `iv90_panel`, `iv90mny`, `skew_panel`
- FOUND: `vix`, `vvix`, `rf_rate`
- FOUND: `truncate_start`, `landed`
- FOUND: `.reindex(NYSE_INDEX)` (used in both panel + Series builders)
- FOUND: `_to_named_series`, `index.equals(prices_panel.index)`
- ABSENT: `.fillna` (anywhere — D-08 satisfied)

**Skew formula:**
- FOUND exact string: `skew_panel = iv90mny[common_skew_cols] - iv_panel[common_skew_cols]`

**Truncation construct:**
- FOUND exact string: `truncate_start = max(iv_first_dates) if iv_first_dates else NYSE_INDEX.min()`

**`hmm.ipynb` integrity:**
- Pre-Plan-03 tree hash: `233a9552846767e7621880ac12122722a9435628`
- Post-Plan-03 tree hash: `233a9552846767e7621880ac12122722a9435628` (byte-identical)

**Plan 01 + Plan 02 cells preserved:**
- Cells 0-11 (markdown title, Section 0 setup, Section 1 + 1.1 cache wrapper, 1.2 raw_pulls, 1.3 raw_cross) — JSON-serialized comparison vs `5729774:sleeve_alpha.ipynb` shows all 12 cells byte-identical.

---
*Phase: 01-extended-data-layer*
*Completed: 2026-04-30*
