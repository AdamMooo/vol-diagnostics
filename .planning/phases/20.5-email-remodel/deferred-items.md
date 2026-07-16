# Deferred Items — Phase 20.5

## test_data_health.py::TestRunIdempotencyGuard::test_force_overrides_guard fails in worktree only

**Found during:** 20.5-01, Task 2 full-suite verification.
**Cause:** `engine/run_daily.py`'s `run()` calls `OUT_DIR.mkdir(exist_ok=True)` (no `parents=True`).
`out/` is gitignored and only exists in the main checkout where it's been created by prior
manual/daily runs. A fresh git worktree has no `out/` directory at all, so `out/gex`'s mkdir
raises `FileNotFoundError` (parent missing).
**Verified:** Same test passes cleanly in the main repo checkout (`C:/dev/vol-diagnostics`),
confirming this is a worktree-environment artifact, not a regression from this plan's changes
to `data_loader.py` / `compute.py`.
**Scope:** Out of scope for 20.5-01 (unrelated file, pre-existing latent gap — `mkdir` should
arguably use `parents=True` or the test should ensure `out/` exists — but neither is touched
by this plan). Not fixed here per SCOPE BOUNDARY.
