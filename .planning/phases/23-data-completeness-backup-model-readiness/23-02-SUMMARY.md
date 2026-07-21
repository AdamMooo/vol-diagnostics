---
phase: 23-data-completeness-backup-model-readiness
plan: "02"
subsystem: infra
tags: [boto3, s3-compatible-api, oracle-object-storage, backup-restore, parquet]

# Dependency graph
requires:
  - phase: none (wave 1, depends_on: [])
    provides: n/a
provides:
  - "engine/backup_to_oracle() — uploads out/ to Oracle Object Storage via S3-compatible boto3 API, credentials from env vars only"
  - "engine/restore_from_oci() — dry-run-by-default, --force-gated restore with post-download parquet integrity checks"
  - "scripts/restore-from-backup.sh — runnable entry point into the tested restore module"
  - "boto3>=1.34,<2.0 in requirements.txt"
affects: [23-03 (GitHub Actions wiring + one-time OCI account setup, human-gated), 23-04]

# Tech tracking
tech-stack:
  added: ["boto3>=1.34,<2.0"]
  patterns:
    - "S3-compatible endpoint pattern: https://{namespace}.compat.objectstorage.{region}.oraclecloud.com, identical _s3_client() helper mirrored in both modules"
    - "Loud-failure convention for backup/restore (raise, never swallow) — deliberate deviation from engine/data/'s fail-soft read convention, documented in module docstrings"
    - "RestoreSafetyError / RestoreCorruptionError as named exception classes tied to specific STRIDE threat IDs (T-23-05, T-23-06)"

key-files:
  created:
    - engine/backup_to_oci.py
    - engine/restore_from_oci.py
    - scripts/restore-from-backup.sh
    - engine/tests/test_backup_to_oci.py
    - engine/tests/test_restore_from_oci.py
  modified:
    - requirements.txt

key-decisions:
  - "boto3 was already present in the local Python environment (1.43.46) — no install step needed at execution time; requirements.txt pin (>=1.34,<2.0) added per plan spec regardless so CI/fresh installs get it"
  - "All 6 backup tests + 8 restore tests written against mocked _s3_client per plan design — zero real network/OCI calls, consistent with the no-real-credentials-yet constraint for this plan"

requirements-completed: [BACKUP-01, BACKUP-02]

duration: 25min
completed: 2026-07-21
---

# Phase 23 Plan 02: Oracle Object Storage Backup & Restore Modules Summary

**boto3-based backup_to_oci.py (upload) and restore_from_oci.py (dry-run/force-gated download with parquet integrity checks) for Oracle Object Storage, both fully unit-tested against mocked S3 calls with zero real OCI credentials.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-07-21T19:36:00Z (approx, first Read call)
- **Completed:** 2026-07-21T20:01:55Z
- **Tasks:** 2 completed
- **Files modified:** 6 (2 new source modules, 1 new script, 2 new test files, 1 modified requirements.txt)

## Accomplishments
- `engine/backup_to_oracle()` uploads every file under a source dir to Oracle Object Storage, keyed by POSIX-style path relative to the source dir's parent, credentials sourced only from `OCI_ACCESS_KEY_ID`/`OCI_CUSTOMER_SECRET_KEY` env vars
- `engine/restore_from_oci()` implements the full safety contract from the plan: dry-run lists with zero disk writes, refuses to overwrite a populated destination without `--force`, strips the `out/` key prefix, and validates every downloaded `.parquet` file via `pd.read_parquet()` — raising `RestoreCorruptionError` on failure
- `scripts/restore-from-backup.sh` is a thin, runnable bash entry point matching the repo's existing `scripts/update.sh` convention (shebang, `set -euo pipefail`, `cd "$(dirname "$0")/.."`)
- 14 new tests (6 + 8), all mocking `_s3_client`, no real network/OCI calls required

## Task Commits

Each task followed the RED → GREEN TDD cycle:

1. **Task 1: engine/backup_to_oci.py + tests**
   - `dc1f4f2` (test) — 6 failing tests for `TestBackupToOracle`, requirements.txt gains boto3
   - `1f43b75` (feat) — `backup_to_oracle()`, `_s3_client()`, `main()` implemented, all 6 pass
2. **Task 2: engine/restore_from_oci.py + scripts/restore-from-backup.sh + tests**
   - `b9bacea` (test) — 8 failing tests for `TestRestoreFromOci` + `TestListBackupObjects`
   - `2be369c` (feat) — `restore_from_oci()`, `list_backup_objects()`, `RestoreSafetyError`, `RestoreCorruptionError`, `main()`, and the bash wrapper implemented, all 8 pass

**Plan metadata:** (this commit, following SUMMARY.md write)

## Files Created/Modified
- `engine/backup_to_oci.py` - `backup_to_oracle()` (upload), `_s3_client()` (shared boto3 client builder), `main()` CLI
- `engine/restore_from_oci.py` - `restore_from_oci()` (download + safety gates + integrity check), `list_backup_objects()`, `RestoreSafetyError`, `RestoreCorruptionError`, `main()` CLI
- `scripts/restore-from-backup.sh` - thin bash wrapper (`python -m engine.restore_from_oci "$@"`)
- `engine/tests/test_backup_to_oci.py` - `TestBackupToOracle` (6 tests)
- `engine/tests/test_restore_from_oci.py` - `TestRestoreFromOci` (6 tests) + `TestListBackupObjects` (2 tests)
- `requirements.txt` - added `boto3>=1.34,<2.0` after the `requests>=2.31` line

## Decisions Made
- None beyond what the plan specified — implementation followed the plan's exact function signatures, algorithm steps, and test behaviors as written.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**Pre-existing worktree environment gaps (out of scope, not caused by this plan's changes):**
- `engine/tests/test_compute_oi_wiring.py`, `engine/tests/test_data_loader.py`, `engine/tests/test_session.py` fail to collect in this worktree because `pandas_market_calendars` is not installed in the environment pytest is running under (confirmed pre-existing by running the same suite before this plan's commits — identical failure).
- `engine/tests/test_data_health.py::TestRunIdempotencyGuard::test_force_overrides_guard` fails because the worktree lacks an `out/gex` directory on disk (confirmed pre-existing the same way).
- Both are unrelated to `backup_to_oci.py`/`restore_from_oci.py` and out of this plan's file scope (`requirements.txt`, `engine/backup_to_oci.py`, `engine/tests/test_backup_to_oci.py`, `engine/restore_from_oci.py`, `engine/tests/test_restore_from_oci.py`, `scripts/restore-from-backup.sh`) — not fixed, per the scope-boundary rule. Full targeted suite excluding these 4 pre-existing failures: 357 passed, 0 failed (349 baseline + 8 new restore tests; the 6 new backup tests are counted within that 357).

## User Setup Required

None yet for this plan. Plan 23-03 (dependent, not yet executed) covers wiring these modules into the GitHub Actions daily job and the one-time OCI Object Storage account/bucket/credential setup — that plan is explicitly human-gated since it requires real OCI credentials this plan intentionally does not touch.

## Next Phase Readiness

- Both modules are fully implemented and unit-tested; ready for Plan 23-03 to wire `backup_to_oci` into `.github/workflows/daily-report.yml` and document the one-time OCI setup.
- No blockers. The only prerequisite for 23-03 is the human-provided OCI credentials (access key, secret key, namespace, bucket) — none of which this plan touches or requires.

---
*Phase: 23-data-completeness-backup-model-readiness*
*Completed: 2026-07-21*
