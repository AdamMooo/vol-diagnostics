---
phase: 01-extended-data-layer
plan: 02
subsystem: data
tags: [jupyter, nbformat, pandas, emds_client, bdh, raw-pulls]

# Dependency graph
requires:
  - phase: 01-extended-data-layer
    provides: "Section 0 config (UNDERLYINGS, REQUIRED_UNDERLYINGS, IV_FIELDS, PRICE_FIELD, CROSS_ASSET, START_DATE, END_DATE) and bdh_cached wrapper from Plan 01"
provides:
  - Section 1.2 — raw_pulls dict-of-dicts: per-underlying price + 30D ATM IV + 30D 90mny IV + 90D ATM IV pulled via bdh_cached, with [landed]/[deferred] stdout log per (underlying, field)
  - Section 1.3 — raw_cross dict: VIX, VVIX, USGG3M risk-free pulled via bdh_cached
  - _probe helper (in notebook scope) for use by future raw-pull cells if needed
  - RuntimeError guards on missing required underlyings (SPX/QQQ price+iv30_atm) and missing VIX
  - warnings.warn fallback path on empty rf_rate (D-13 alternate-field documentation)
affects: [01-03-panel-alignment, 01-04-qa-freshness, 02-signals, 03-sleeve-pricing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Probe-and-log pattern: empty con.bdh response logs [deferred] and returns empty DataFrame; cell stays green"
    - "Required-vs-best-effort split: REQUIRED_UNDERLYINGS raise, others defer"
    - "Single-shared _probe closure used by both per-underlying and cross-asset pull loops"

key-files:
  created:
    - .planning/phases/01-extended-data-layer/01-02-SUMMARY.md
  modified:
    - sleeve_alpha.ipynb

key-decisions:
  - "Authoring-only execution: cells appended via json.load → mutate → json.dump (no nbformat module locally; no kernel run; Cron2-only execution per CLAUDE.md)"
  - "_probe defined in Section 1.2 cell (not Section 0) so its scope sits with the raw-pull code that uses it; Section 1.3 reuses by reference, no redefinition"
  - "rf_rate empty path uses warnings.warn (not raise) per D-13; VIX empty path raises per SIG-06 dependency in REQUIREMENTS.md"

patterns-established:
  - "Append-only notebook authoring: read JSON, append cells dict to nb['cells'], write back with indent=1 + ensure_ascii=True + CRLF + trailing newline (matches Plan 01 formatting style)"
  - "Acceptance via source-introspection: identifier-presence greps over concatenated cell sources are the verification surface for authoring-only plans"

requirements-completed: [DATA-06, DATA-07, DATA-08, DATA-10]

# Metrics
duration: 12min
completed: 2026-04-30
---

# Phase 1 Plan 02: Raw Data Pulls (Per-Underlying + Cross-Asset) Summary

**Section 1.2 (`raw_pulls` per-underlying price + 3 IV fields) and Section 1.3 (`raw_cross` VIX/VVIX/USGG3M) authored as nbformat v4 cells with [landed]/[deferred] logging and required-field RuntimeError guards.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-04-30
- **Completed:** 2026-04-30
- **Tasks:** 2
- **Files modified:** 1 (`sleeve_alpha.ipynb`: 8 cells → 12 cells)

## Accomplishments

- Section 1.2 markdown header + code cell appended (Task 1, commit `653b5f9`)
- Section 1.3 markdown header + code cell appended (Task 2, commit `fe20fb7`)
- All Plan 01 cells preserved unchanged (cells 0-7 byte-identical)
- `hmm.ipynb` byte-identical (tree hash `233a9552...` before and after both tasks)
- Acceptance grep checks pass for all 12 required identifiers (`raw_pulls`, `_probe`, `[deferred]`, `[landed]`, `REQUIRED_UNDERLYINGS`, `iv30_atm`, `iv30_90mny`, `iv90_atm`, `raw_cross`, `CROSS_ASSET`, `VIX pull returned empty`, `warnings.warn`)

## Task Commits

1. **Task 1: Section 1.2 per-underlying probe cells** — `653b5f9` (feat)
2. **Task 2: Section 1.3 cross-asset pull cells** — `fe20fb7` (feat)

Plan-summary metadata commit: deferred to `docs(01-02): plan summary` once this file lands.

## Files Created/Modified

- `sleeve_alpha.ipynb` — appended 4 cells: 1.2 markdown header, 1.2 code cell (`raw_pulls` + `_probe` + per-underlying pull loop + REQUIRED_UNDERLYINGS guard), 1.3 markdown header, 1.3 code cell (`raw_cross` + CROSS_ASSET pull loop + VIX-empty guard + rf_rate-empty warn).
- `.planning/phases/01-extended-data-layer/01-02-SUMMARY.md` — this file.

## Verification Status — Local vs Cron2

This plan ships **authoring-only** artifacts. The notebook has not been executed (locked Python env on this Windows machine has no `emds_client`, no `con.bdh`, no Bloomberg-flavoured fields). The acceptance criteria the plan defines are pure JSON source-introspection greps and they all pass. The runtime questions the plan's `<output>` section asks can only be answered after Cron2 runs the cells. Split below.

### Verifiable now (verified)

- **Cells authored with planned identifiers and field names** — confirmed via grep (`UNDERLYINGS`, `IV_FIELDS`, `PRICE_FIELD`, `CROSS_ASSET`, `REQUIRED_UNDERLYINGS`, `START_DATE`, `END_DATE`, `bdh_cached`, `raw_pulls`, `raw_cross`).
- **Deferred-field logging path in place** — `_probe` returns empty DataFrame and prints `[deferred] {label} / {field}: empty response from con.bdh` on empty/None response; verifiable via cell source.
- **Required-underlying RuntimeError guard in place** — Section 1.2 code cell raises if any of `REQUIRED_UNDERLYINGS = ("SPX", "QQQ")` returns empty for `price` or `iv30_atm`; verifiable via cell source (matches plan's `<action>` block verbatim).
- **VIX-empty RuntimeError guard in place** — Section 1.3 raises if `len(raw_cross["vix"]) == 0`; verifiable via cell source.
- **rf_rate-empty `warnings.warn` path in place** — Section 1.3 emits a warning (does not raise) if `len(raw_cross["rf_rate"]) == 0`, with the alternate-field hint per D-13; verifiable via cell source.
- **VVIX empty silently allowed** — no check on `raw_cross["vvix"]`; verifiable via cell source (consistent with D-03).
- **Plan 01 cells untouched** — `git diff` for both task commits is purely additive (only new cells appended after the bdh_cached wrapper cell).
- **`hmm.ipynb` byte-identical** — `git rev-parse HEAD:hmm.ipynb` returns `233a9552846767e7621880ac12122722a9435628` (matches Plan 01 baseline).
- **Notebook is valid nbformat v4 JSON after each append** — `json.load` succeeds, cell count goes 8 → 10 → 12 with no schema errors.

### Pending Cron2 run (cannot verify locally)

- **Which underlyings landed vs deferred.** Plan 01 ships `UNDERLYINGS = {SPX, QQQ, XIU, XSP}`; SPX/QQQ are required and will raise if empty, XIU/XSP are best-effort and will print `[deferred]` if `con.bdh` returns nothing. The actual outcome (XIU clean? XSP clean? sparse history?) is captured only in the cell stdout when this runs on Cron2. **`[pending Cron2 run]`**
- **Whether 90D ATM IV (`90DAY_IMPVOL_100.0%MNY_DF`) is universally available or sparse.** Pulled per-underlying via `IV_FIELDS["iv90_atm"]`. D-03 calls it "pulls forward the term-structure todo from STATE.md" — fields and probe path are wired; landing pattern is a Cron2-side question. **`[pending Cron2 run]`**
- **Whether VVIX landed.** Pulled in Section 1.3 via `CROSS_ASSET["vvix"]` against `VVIX Index PX_LAST`; D-03 marks VVIX as "cheap one-line addition; optional fragility-composite input" so empty is silently allowed. Whether VVIX returned a non-empty Series is determinable only from Cron2 stdout. **`[pending Cron2 run]`**
- **Which risk-free field was used.** Section 1.3 calls `bdh_cached("USGG3M Index", "PX_LAST", ...)`. If that returns empty on the actual Cron2 instance, `warnings.warn` fires and Phase 1 ships with `rf_rate` empty per D-13's documented fallback; downstream BS pricing (Phase 3) will then have to swap in an alternate field. Whether USGG3M PX_LAST works on this Cron2 instance — or whether the warn path triggers — is **`[pending Cron2 run]`**.

After running Section 1.2 and 1.3 cells on Cron2, the operator should append the captured `[landed]`/`[deferred]` stdout into this section to close out the four pending items.

## Decisions Made

- **`_probe` lives inside Section 1.2's code cell, not Section 0.** Keeps the helper colocated with its only callsites (Section 1.2 per-underlying loop and Section 1.3 cross-asset loop). Section 1.3 references `_probe` as a forward-declared name — fine in notebook execution order, since 1.2 runs before 1.3. Plan body specified this layout verbatim.
- **`rf_rate` empty path uses `warnings.warn`, not `raise`.** Per D-13 the field name on this particular Cron2 instance may not be USGG3M; raising would block the entire downstream pipeline on a recoverable issue. The warning surfaces at the bottom of Section 1 so it's visible, and Phase 1 can ship with `rf_rate` empty per D-13's documented "alternate-field path" provision; Phase 3 BS pricing then has the option to fall back to a different 3M proxy.
- **VIX empty path does `raise`, unlike rf_rate.** SIG-06 fragility composite is a downstream non-negotiable per the requirements list; quietly continuing past empty VIX would silently break Phase 2 signals. RuntimeError on empty VIX is the right call.
- **JSON output formatting matched existing notebook style** (`indent=1`, `ensure_ascii=True`, CRLF line endings, trailing newline) so each task's diff stays a clean append rather than a whitespace re-flow of the whole file.

## Deviations from Plan

None — plan executed exactly as written. All cell sources match the plan's `<action>` blocks verbatim. No Rule 1/2/3 auto-fixes triggered.

## Issues Encountered

- **Windows console can't print Unicode by default.** First attempt at the inspector script crashed on `α` (em-dash and Greek alpha appear in cell sources). Resolved by setting `PYTHONIOENCODING=utf-8` for the bash invocation. Doesn't affect committed artifacts — the notebook itself stores em-dashes as `—` (escaped) since `ensure_ascii=True` is the format Plan 01 established.
- **Pre-existing `STATE.md` modification in working tree** at session start, untouched by this plan; left alone per `commit_docs: false` in `.planning/config.json`.

## User Setup Required

None — no external service configuration required. The cells will run on Cron2 with the existing `con` connection (instantiated by the server's startup code, not by the notebook).

After running on Cron2, the operator should:
1. Capture the stdout `[landed]`/`[deferred]` lines from Section 1.2 and 1.3.
2. Append them into the "Pending Cron2 run" subsection of this SUMMARY (or update STATE.md once the Cron2 run lands).
3. Note any unexpected `warnings.warn` from Section 1.3 (rf_rate empty) — that's a Phase 3 prerequisite to capture.

## Next Phase Readiness

- Plan 01-03 (panel alignment) can read directly from `raw_pulls` and `raw_cross`. The dict-of-dicts shape (`raw_pulls[underlying][field] = DataFrame`) and the Series-shaped cross-asset entries are the documented handoff per the plan's `<objective>`.
- DATA-06, DATA-07, DATA-08, DATA-10 substantively complete on the authoring side — the cells are in place, the field names match `IV_FIELDS` from Plan 01, and the deferred-field log satisfies "probe and document" per D-02. Marking these complete in REQUIREMENTS.md is appropriate; the Cron2-side data-landing confirmation is captured as an open item in this SUMMARY rather than as an incomplete requirement.
- DATA-09 was completed in Plan 01-01 (NYSE_INDEX); DATA-11 (freshness check) and DATA-12 (canonical panels) remain for Plans 01-03 and 01-04.
- No blockers.

## Self-Check: PASSED

**Files verified:**
- FOUND: `C:/dev/tq-hmm/sleeve_alpha.ipynb` (12 cells, valid nbformat v4 JSON)
- FOUND: `C:/dev/tq-hmm/.planning/phases/01-extended-data-layer/01-02-SUMMARY.md` (this file)

**Commits verified:**
- FOUND: `653b5f9` (Task 1: Section 1.2 per-underlying probe)
- FOUND: `fe20fb7` (Task 2: Section 1.3 cross-asset pulls)

**Identifier presence in `sleeve_alpha.ipynb` source (via `python -c` introspection):**
- FOUND: `raw_pulls`, `_probe`, `[deferred]`, `[landed]`, `REQUIRED_UNDERLYINGS`
- FOUND: `iv30_atm`, `iv30_90mny`, `iv90_atm`
- FOUND: `raw_cross`, `CROSS_ASSET`, `VIX pull returned empty`, `warnings.warn`

**`hmm.ipynb` integrity:**
- Pre-Task-1 tree hash: `233a9552846767e7621880ac12122722a9435628`
- Post-Task-2 tree hash: `233a9552846767e7621880ac12122722a9435628` (byte-identical)

**Plan 01 cells preserved:**
- Cells 0-7 (markdown title + Section 0 + Section 1 header + bdh_cached wrapper) untouched in both task diffs (purely additive — new cells inserted after cell 7).

---
*Phase: 01-extended-data-layer*
*Completed: 2026-04-30*
