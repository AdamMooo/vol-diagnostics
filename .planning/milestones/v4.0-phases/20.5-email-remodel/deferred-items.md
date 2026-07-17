# Deferred Items — Phase 20.5

## test_data_health.py::TestRunIdempotencyGuard::test_force_overrides_guard fails in worktree only

**Found during:** 20.5-01 (Task 2 full-suite verification) and independently 20.5-02.
**Cause:** `engine/run_daily.py`'s `run()` calls `OUT_DIR.mkdir(exist_ok=True)` (no `parents=True`).
`out/` is gitignored and only exists in the main checkout where it's been created by prior
manual/daily runs. A fresh git worktree has no `out/` directory at all, so `out/gex`'s mkdir
raises `FileNotFoundError` (parent missing).
**Verified:** Same test passes cleanly in the main repo checkout (`C:/dev/vol-diagnostics`),
confirming this is a worktree-environment artifact, not a regression from either plan's changes.
**Scope:** Out of scope for 20.5-01/20.5-02 (unrelated file, pre-existing latent gap — `mkdir` should
arguably use `parents=True` or the test should ensure `out/` exists — but neither is touched
by these plans). Not fixed here per SCOPE BOUNDARY.

## Missing `pandas_market_calendars` in worktree venv (20.5-02 only)

**Found during:** 20.5-02 full-suite verification.
**Symptom:** `engine/tests/test_compute_oi_wiring.py` and `engine/tests/test_session.py` fail to
collect: `ModuleNotFoundError: No module named 'pandas_market_calendars'`.
**Cause:** Fresh worktree venv missing a dependency present in the main checkout's `.venv`.
Unrelated to `png_export.py`/`config.py` changes.
**Scope:** Not fixed here — environment gap, not a code defect.

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
**Phase siblings:**
- [[_planning/vol-diagnostics/phases/20.5-email-remodel/20.5-01-PLAN|20.5-01-PLAN]]
- [[_planning/vol-diagnostics/phases/20.5-email-remodel/20.5-01-SUMMARY|20.5-01-SUMMARY]]
- [[_planning/vol-diagnostics/phases/20.5-email-remodel/20.5-02-PLAN|20.5-02-PLAN]]
- [[_planning/vol-diagnostics/phases/20.5-email-remodel/20.5-02-SUMMARY|20.5-02-SUMMARY]]
- [[_planning/vol-diagnostics/phases/20.5-email-remodel/20.5-03-PLAN|20.5-03-PLAN]]
- [[_planning/vol-diagnostics/phases/20.5-email-remodel/20.5-04-PLAN|20.5-04-PLAN]]
- [[_planning/vol-diagnostics/phases/20.5-email-remodel/20.5-CONTEXT|20.5-CONTEXT]]
- [[_planning/vol-diagnostics/phases/20.5-email-remodel/20.5-DISCUSSION-LOG|20.5-DISCUSSION-LOG]]
- [[_planning/vol-diagnostics/phases/20.5-email-remodel/20.5-PATTERNS|20.5-PATTERNS]]

<!-- LINKS:END -->
