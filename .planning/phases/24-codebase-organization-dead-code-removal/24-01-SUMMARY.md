---
phase: 24-codebase-organization-dead-code-removal
plan: 01
subsystem: engine
tags: [dead-code, static-analysis, cleanup, CLEAN-01]
requires: []
provides: ["clean static-analysis baseline for engine/ source + app.py"]
affects: [engine/compute.py, engine/report/report.py, engine/vol/vol_metrics.py, app.py]
tech_stack:
  added: []          # vulture + pyflakes installed ad-hoc in .venv only — NOT added to requirements.txt (one-time diagnostic)
  patterns: []
key_files:
  created: []
  modified:
    - app.py
    - engine/compute.py
    - engine/report/report.py
    - engine/vol/vol_metrics.py
decisions:
  - "Removed dead vrp_headline() entirely (zero callers) rather than just its two flagged params — addresses the root of the vulture findings."
  - "Kept two author-reserved params (build_card_fields.extras, _kv_cell.value_color) — both carry explicit docstring intent-to-retain; removal would be an API signature change beyond dead-symbol deletion."
  - "Test-file findings left untouched — engine/tests is excluded from the sweep target per the plan scope guard; suite stays 449 green."
metrics:
  duration: ~10 min
  completed: 2026-07-26
  tasks: 2
  files_changed: 4
  tests: 449
---

# Phase 24 Plan 01: Static-Analysis Dead-Code Sweep Summary

One-time vulture + pyflakes sweep over `engine/` source and `app.py`: removed a dead
`vrp_headline()` function and two redundant/unused imports, fixed two forward-ref
annotations that referenced unimported names, and triaged every remaining finding —
all with deletion-only diffs (no renames/moves). Suite stays 449 green; `run_gex SPY`
smoke clean.

## What Was Done

- Installed `vulture` + `pyflakes` ad-hoc in `.venv` (NOT tracked in requirements.txt — one-time diagnostic per project minimal-tooling bias).
- Ran `python -m pyflakes engine app.py` and `python -m vulture engine app.py --min-confidence 80`.
- Triaged every finding (table below); removed genuine dead code with smallest-possible diffs.
- Verified: full suite 449 passed, `python -m engine.run_gex --ticker SPY` exit 0.

## Triage

### Source (in-scope: `engine/` non-test + `app.py`)

| Finding | Tool | Disposition | Rationale |
|---------|------|-------------|-----------|
| `compute.py:39` local `import pandas as pd` in `_recent_closes` | pyflakes | **REMOVE** | Redundant — module already imports `pd` at top (line 10); local re-import unused. |
| `compute.py:65,108` undefined name `datetime` (annotations) | pyflakes | **FIX** | `from __future__ import annotations` made `datetime.date` annotations forward-ref strings referencing an unimported name. Added module-level `import datetime` — resolves the name; latent (Rule 1) since `get_type_hints()` would have raised. |
| `report.py:187` undefined name `pd` (annotation) | pyflakes | **FIX** | Forward-ref `"pd.DataFrame \| None"` referenced unimported pandas. Added `import pandas as pd`. |
| `app.py:3` unused import `datetime.timedelta` | pyflakes | **REMOVE** | Not referenced anywhere in `app.py`. |
| `vol_metrics.py:318 iv30_pct`, `:319 rv20_pct` (params of `vrp_headline`) | vulture | **REMOVE** | Params unused because the whole function is dead — `vrp_headline()` has **zero callers** across engine/, app.py, and tests (grep-confirmed). A "Phase 11 email plug-in point" never wired across 13+ phases. Removed the entire function (35 lines), resolving both param findings at the root. |
| `card_model.py:293` unused param `extras` | vulture | **KEEP** | Public `build_card_fields(today, prior, extras=None)` — docstring: "extras: reserved; ignored." Author-reserved API surface with 40+ call sites; removal is a signature change beyond dead-symbol deletion. |
| `report.py:49` unused param `value_color` | vulture | **KEEP** | `_kv_cell` — docstring: "value_color arg retained for signature compat but intentionally ignored." Explicit author intent-to-retain. |

### Out-of-scope (test files — `engine/tests/`)

Per the plan's scope guard ("the sweep target is `engine/` (source) + `app.py` only ...
tests excluded from the sweep target but must stay green") and the project minimal-diff
bias, all findings under `engine/tests/` were **left untouched** — not acted on. They are
genuine unused test imports / dead local vars (e.g. `test_oi_history.py` unused `mod`
re-imports, unused `pytest`/`importlib`/`pathlib` imports across ~15 test modules, and
vulture unused mock locals in `test_data_health.py`), but cleaning them is surrounding
cleanup outside the plan's stated sweep target. The suite stays 449 green regardless.
If a future phase wants test-file hygiene, this is the documented backlog.

## Verification

- `python -m pyflakes engine app.py` — **zero source findings** (only `engine/tests/*`, out-of-scope).
- `python -m vulture engine app.py --min-confidence 80` — source findings reduced to the two documented author-reserved KEEPs (`extras`, `value_color`); the rest are `engine/tests/*` (out-of-scope).
- `pytest engine/tests -q` — **449 passed** (no regression; baseline was 449).
- `python -m engine.run_gex --ticker SPY` — exit 0, clean summary + PNG/HTML export, no ImportError/AttributeError.
- `git diff --stat` — 4 files, +5/-37, **no renames/moves/added source files** (deletion-only).

## Deviations from Plan

**[Rule 1 — Latent bug] Fixed forward-ref annotations referencing unimported names.**
- **Found during:** Task 1 pyflakes sweep (`compute.py:65,108` `datetime`; `report.py:187` `pd`).
- **Issue:** Under `from __future__ import annotations`, these annotations are deferred strings, so the missing imports never raised at import time — but any runtime type-hint resolution (`typing.get_type_hints`) would `NameError`.
- **Fix:** Added `import datetime` to `compute.py` and `import pandas as pd` to `report.py`. Verified the added imports do NOT trigger new vulture/pyflakes findings (pyflakes counts forward-ref usage; vulture did not flag them).
- **Files:** `engine/compute.py`, `engine/report/report.py`. **Commit:** 923a3f9.

These were undefined-name findings (not the "unused import" category the plan primarily
targeted), surfaced by the required pyflakes run; fixing with a one-line import each is
the minimal correct disposition.

## Self-Check: PASSED

- Modified files exist: app.py, engine/compute.py, engine/report/report.py, engine/vol/vol_metrics.py — all present.
- Commit 923a3f9 present in git log.
- 449 tests green; CLI smoke exit 0.

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
**Phase siblings:**
- [[_planning/vol-diagnostics/phases/24-codebase-organization-dead-code-removal/24-01-PLAN|24-01-PLAN]]
- [[_planning/vol-diagnostics/phases/24-codebase-organization-dead-code-removal/24-02-PLAN|24-02-PLAN]]

<!-- LINKS:END -->
