---
phase: 24-codebase-organization-dead-code-removal
plan: 02
subsystem: docs
tags: [doc-sync, orientation, close-out, CLEAN-01, CLEAN-02]
requires: ["24-01"]
provides: ["CLAUDE.md engine tree/table 1:1 with disk; fz2 + 999.3 closed; CLEAN traceability corrected"]
affects: [CLAUDE.md, .planning/STATE.md, .planning/ROADMAP.md, .planning/REQUIREMENTS.md]
tech_stack:
  added: []
  patterns: []
key_files:
  created:
    - .planning/todos/done/2026-05-11-v3-2-pre-distribution-hardening.md
  modified:
    - CLAUDE.md
    - .planning/STATE.md
    - .planning/ROADMAP.md
    - .planning/REQUIREMENTS.md
    - .planning/quick/260514-fz2-dead-code-stale-ref-sweep/260514-fz2-SUMMARY.md
decisions:
  - "Reconciliation gate applied both directions: added table rows for session/oi_history/store (pre-existing table gaps surfaced by the orphan check), not just the plan-named monitor/ + Phase-23 modules."
  - "999.3 item (c) 'Regime sharpness' formally DEFERRED not implemented — a new GEX-derived signal contradicts the locked 'no new signals' + GEX-demoted product direction; implementing would violate small-diffs cleanup scope."
  - "vol-diagnostics.md hub left uncommitted — it carries pre-existing unrelated drift plus a hook auto-sync, out of this plan's file scope."
metrics:
  duration: ~15 min
  completed: 2026-07-26
  tasks: 2
  files_changed: 6
  tests: 449
---

# Phase 24 Plan 02: CLAUDE.md Doc-Sync + Stale-Item Close-Out Summary

Brought CLAUDE.md's `engine/` orientation into 1:1 agreement with the on-disk
package (both-directions orphan + phantom reconciliation) and closed the two stale
tracking items the phase folds in — the `260514-fz2` quick-task and backlog 999.3
Pre-Distribution — with recorded per-item dispositions. No feature code touched.

## Task 1 — CLAUDE.md engine tree + module table sync (commit 8b08f0a)

Much of the original plan delta was already satisfied by external commit `7dccfeb`
("docs: fix drift after phase 26"): the `monitor/` tree line and all three test-count
strings already read the live 449. Verified those, then closed the genuine remaining gap.

**Tree block edits:**
- Added Phase-23 root ops line: `health_check.py  backup_to_oci.py  restore_from_oci.py`.
- Added `metrics` to the `monitor/` subdomain line (it listed only schema/ranker/hysteresis/monitor_store/calibration).

**Module-purpose table — 12 rows added** (accurate one-liners drawn from reading each file's docstring, not memory):
- Root: `session`, `health_check`, `backup_to_oci`, `restore_from_oci`
- data/: `oi_history`, `store`
- monitor/: `schema`, `ranker`, `metrics`, `hysteresis`, `monitor_store`, `calibration`

`session`, `oi_history`, `store` were pre-existing table gaps (present in the tree, absent
from the table) surfaced by the both-directions reconciliation — added to satisfy the gate.

**Reconciliation (gate of record — manual, both directions):**
- Orphan check: every on-disk `engine/**/*.py` (33 modules) now has a backticked table row — PASS.
- Phantom check: every `engine/…py` path in the table exists on disk — PASS (no Plan-01 removal left listed).
- `grep -nE '[0-9]{3} (green|tests)' CLAUDE.md` → only 449 on all three lines (13/37/69). No stray 358/364.
- `grep -c monitor CLAUDE.md` → 8 (>0).
- `git diff CLAUDE.md` touched only the engine tree + module table (+14/-1). No other section.

## Task 2 — Close out fz2 + 999.3; fix REQUIREMENTS traceability (commit bf1123f)

### fz2 quick-task
Already `status: complete` (SUMMARY, commit 22ec33a — broken matplotlib save path in
`run_gex` fixed 2026-05-14). Only stale artifact was STATE.md's Deferred-Items row calling
it "missing" → changed to "resolved — completed 2026-05-14 (commit 22ec33a), confirmed
during Phase 24". Appended a "Verified resolved in Phase 24" note to the fz2 SUMMARY. No re-run.

### 999.3 Pre-Distribution — disposition of its 4 items
Grepped current source for each; 3 shipped out-of-phase, 1 deferred:

| Item | Disposition | Evidence |
|------|-------------|----------|
| (a) Snapshot timestamp in email header | **SHIPPED** | `engine/report/report.py:291-303` "Snapshot {ts} ET · OI T-1 · Greeks 15-min delayed"; `snapshot.as_of` threaded via `engine/compute.py:190` |
| (b) Methodology caveat banner above cards | **SHIPPED** | `engine/report/report.py:307` `_methodology_caveat_banner()`, rendered at `report.py:539,570` |
| (c) Gamma-profile slope / "Regime sharpness" row | **DEFERRED** | Not present anywhere in `engine/`. Counter to locked "no new signals" + GEX-demoted direction; a new GEX signal needs statistical validation first. Implementing here would violate cleanup small-diffs scope. |
| (d) Filter-drop transparency | **SHIPPED** | `engine/report/report.py:496` "Filters removed {…} of raw chain OI"; `min_oi`/`max_iv` drop at `engine/data/data_loader.py:111` |

Recorded these dispositions in the todo file, moved it `todos/pending/ → todos/done/`,
flipped its frontmatter to `status: resolved`. ROADMAP.md backlog row `999.3 | Partial` →
`Closed` with the split disposition. STATE.md Deferred-Items todo row → resolved.

### REQUIREMENTS.md traceability
CLEAN-01 and CLEAN-02 both pointed at "Phase 26" (stale from the 2026-07-21 renumber, old 26 → 24).
Corrected both rows' Phase column to "Phase 24". Marked CLEAN-02 complete (line 28 checkbox `[x]` +
traceability Status → Complete) now that the doc-sync gate passed.

### Verification
- `grep -A2 260514-fz2 STATE.md | grep missing` → fz2's own row is "resolved" (the -A2 hit is the unrelated 260621-v8g row, still legitimately "missing").
- `grep -iE '999.3.*Partial' ROADMAP.md` → nothing.
- `grep -E 'CLEAN-0[12].*Phase 26' REQUIREMENTS.md` → nothing.
- `git status --short | grep '\.py$'` → no engine/ or app.py source edits this plan (docs/tracking only).

## Deviations from Plan

**[Reconciliation-scope] Added `session`/`oi_history`/`store` table rows beyond the plan-named modules.**
- **Found during:** Task 1 both-directions orphan check.
- **Issue:** These three were in the tree but had no module-purpose table row — pre-existing gaps, not Plan-01 fallout. The plan's must-have ("every on-disk module appears in tree AND table") required them.
- **Fix:** Added accurate one-line rows from each file's docstring. Within the plan's "engine tree + module table only" diff boundary.
- **Commit:** 8b08f0a.

No other deviations. No auth gates. No architectural changes.

## Known Stubs

None — documentation and tracking edits only.

## Self-Check: PASSED

- CLAUDE.md, STATE.md, ROADMAP.md, REQUIREMENTS.md, fz2 SUMMARY — all present and modified.
- todos/done/2026-05-11-v3-2-pre-distribution-hardening.md — present (moved from pending/).
- Commits 8b08f0a (Task 1) and bf1123f (Task 2) present in git log.
- Both-directions engine reconciliation PASS; test counts read 449; CLEAN traceability = Phase 24.

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
**Phase siblings:**
- [[_planning/vol-diagnostics/phases/24-codebase-organization-dead-code-removal/24-01-PLAN|24-01-PLAN]]
- [[_planning/vol-diagnostics/phases/24-codebase-organization-dead-code-removal/24-01-SUMMARY|24-01-SUMMARY]]
- [[_planning/vol-diagnostics/phases/24-codebase-organization-dead-code-removal/24-02-PLAN|24-02-PLAN]]

<!-- LINKS:END -->
