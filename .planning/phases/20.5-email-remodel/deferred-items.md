# Deferred Items — 20.5-email-remodel

## From Plan 02 (out of scope — pre-existing, unrelated to this plan's files)

- `engine/tests/test_compute_oi_wiring.py` and `engine/tests/test_session.py` fail to
  collect in this worktree venv: `ModuleNotFoundError: No module named 'pandas_market_calendars'`.
  Unrelated to png_export.py/config.py changes — pre-existing venv/dependency gap.
- `engine/tests/test_data_health.py::TestRunIdempotencyGuard::test_force_overrides_guard`
  fails with `FileNotFoundError` creating `out/gex` — the worktree's `out/` directory tree
  doesn't exist yet (fresh worktree checkout). Unrelated to this plan's files.
