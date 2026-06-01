---
phase: 11-richer-daily-report
plan: "03"
subsystem: gex
tags: [report, email, oi-walls, evolution-section, tdd]
dependency_graph:
  requires: [11-01]
  provides: [report-oi-walls, report-evolution-section, report-white-bg, report-png-note]
  affects: [gex/report.py, gex/tests/test_report.py]
tech_stack:
  added: []
  patterns: [tdd-red-green, cold-start-safe, html-kv-rows]
key_files:
  created:
    - gex/tests/test_report.py
  modified:
    - gex/report.py
decisions:
  - "evolution_section_html() is module-level pure function; returns None on cold start (all-None scalars)"
  - "Lead sentence uses SPY level as cross-ticker proxy; threshold ±0.5pp for moved higher/lower (D-12)"
  - "OI rows placed after Range row in right_rows — keeps GEX walls directly above OI walls for comparison (D-09)"
  - "png_note rendered via inline <p> with LABEL_GRAY color, not as a header/section (D-05)"
metrics:
  duration: ~2 min
  completed: "2026-06-01"
  tasks_completed: 2
  files_modified: 2
---

# Phase 11 Plan 03: Report Enrichments (White BG, OI Walls, Evolution Section) Summary

`report.py` extended with explicit #ffffff body background, OI Call/Put Wall rows in each ticker card, a cold-start-safe Evolution section at the top of the email, and a PNG fallback note slot — all backward-compatible with existing `build_email()` callers.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| RED | Failing tests for all new behaviors | a2519e9 | gex/tests/test_report.py |
| GREEN | Implement body bg, OI rows, evolution section, png note | a45b6c3 | gex/report.py, gex/tests/test_report.py |

## What Was Built

**Body background (D-01):** `<body>` tag in `build_email()` now carries `background:#ffffff` inline, ensuring the email renders on white in all clients regardless of dark-mode inheritance.

**OI wall rows (D-07, D-09):** `_ticker_card()` right column extended with two new rows after the Range row: "OI Call Wall" and "OI Put Wall" — formatted via the existing `_wall_value()` + `_pct_from_spot()` helpers. OI walls appear below GEX walls for side-by-side comparison. Both render "—" when the value is None. OI wall glossary entry added to methodology footer distinguishing assumption-free OI max from GEX-weighted walls.

**evolution_section_html() (D-10, D-11):** New module-level function. Checks all scalar keys (level/rms/skew_change/term_change) across all tickers for all-None (cold start) and returns `None` in that case — entirely omitted from the email. When data is present: renders `_section_header("Surface Evolution — 5-day")` + a one-line lead sentence based on SPY level (±0.5pp threshold) + a compact HTML table (Ticker × Level/RMS/Skew Chg/Term Chg) with pp-formatted values. All three tickers (SPY/QQQ/IWM) appear as rows.

**build_email() signature update:** Gains `evolution_data: dict | None = None` and `png_note: str | None = None` parameters with None defaults (backward compatible). Evolution section injected above ticker cards; png_note rendered as a muted `<p>` below ticker cards and above the methodology footer (D-05).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test Fix] HTML entity encoding in test_evolution_section_before_cards**
- **Found during:** Task 2 GREEN — test failure
- **Issue:** Test searched for `S&amp;P 500` but `TICKER_LABEL["SPY"] = "SPY  S&P 500"` outputs the literal `&` (not entity-escaped) since it's embedded in Python f-string, not passed through an HTML encoder
- **Fix:** Updated test to search for `SPY  S&P 500` (literal, no entity)
- **Files modified:** gex/tests/test_report.py
- **Commit:** a45b6c3

## Verification Results

- `gex/report.py` body tag: `background:#ffffff` confirmed (line 467)
- `gex/report.py` contains `def evolution_section_html(` (line 279)
- `gex/report.py` build_email() signature contains `evolution_data` and `png_note` (lines 375-376)
- `gex/report.py` _ticker_card() contains `oi_call_wall` and `oi_put_wall` rows (lines 220-221, 230-231)
- `pytest gex/tests/test_report.py -x -q` → 11 passed
- `pytest gex/tests/ -x -q` → 116 passed, 0 failures, 1 pre-existing warning

## TDD Gate Compliance

- RED gate: commit a2519e9 — `test(11-03): add failing tests for report.py enrichments`
- GREEN gate: commit a45b6c3 — `feat(11-03): enrich report.py with white bg, OI walls, evolution section, png note`

## Known Stubs

None — all new behaviors are wired to real data from the summary dict or passed-in parameters.

## Threat Flags

None — no new network endpoints or auth paths. evolution_data scalars are internal float computations from trusted parquet store (T-11-04: accept disposition confirmed). png_note is a hardcoded string from run_daily.py (T-11-05: accept disposition confirmed).

## Self-Check: PASSED

- gex/tests/test_report.py: exists, 11 test methods confirmed
- gex/report.py: evolution_section_html present, build_email has evolution_data + png_note params, body has background:#ffffff, _ticker_card has OI rows
- Commits a2519e9 and a45b6c3 exist in git log

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/agent-af8d7c2f5ca90d4f2/ROADMAP|ROADMAP]] · [[_planning/agent-af8d7c2f5ca90d4f2/STATE|STATE]]
**Phase siblings:**
- [[_planning/agent-af8d7c2f5ca90d4f2/phases/11-richer-daily-report/11-CONTEXT|11-CONTEXT]]
- [[_planning/agent-af8d7c2f5ca90d4f2/phases/11-richer-daily-report/11-DISCUSSION-LOG|11-DISCUSSION-LOG]]

<!-- LINKS:END -->
