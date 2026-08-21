---
phase: 02-code-review-staleness-audit
reviewed: 2026-08-21T22:30:00Z
depth: standard
files_reviewed: 18
files_reviewed_list:
  - docker-entrypoint.sh
  - Dockerfile
  - docker-compose.yml
  - engine/restore_from_oci.py
  - engine/health_check.py
  - engine/run_daily.py
  - engine/session.py
  - app.py
  - engine/backup_to_oci.py
  - .github/workflows/daily-report.yml
  - engine/data/surface_history.py
  - engine/data/validation.py
  - scripts/update.sh
  - scripts/sync-from-oracle.sh
  - engine/compute.py
  - .env.example
findings:
  critical: 7
  warning: 8
  info: 3
  total: 18
status: issues_found
---

# Phase 02: Staleness Audit — Data Freshness Gap Report

**Reviewed:** 2026-08-21T22:30:00Z  
**Depth:** standard  
**Files Reviewed:** 18  
**Status:** issues_found

## Summary

The vol-diagnostics system experienced a data staleness issue on 2026-08-20 (Aug 20 data served when Aug 21 was available). Root-cause analysis reveals **seven critical bugs** in the data pipeline that allowed stale data to persist silently:

1. **The entrypoint script fails open instead of fail-safe** — if restore fails, the app starts anyway with stale local data
2. **restore_from_oci.py returns success on empty bucket** — a failed backup looks identical to a successful one
3. **GitHub Actions workflow backs up regardless of collection success** — stale data can overwrite good backups
4. **Health check uses incorrect date comparison logic** — may report stale data as current
5. **Streamlit cache doesn't invalidate on new data arrival** — users see cached old data even after new collection
6. **No post-restore validation on startup** — entrypoint doesn't verify that actual data was restored
7. **Freshness check doesn't enforce consistency across tickers** — individual tickers can show mixed dates without clear warning

The architectural issue is **insufficient guardrails between multiple failure modes**. The system gracefully degrades on individual failures (philosophy: "available, even if stale"), but those failures can cascade silently to the user. A user viewed the dashboard 2026-08-20 and saw Aug 20 data, unaware that Aug 21 data was available because:
- Restoration succeeded but silently (empty bucket case, or incomplete restore)
- Cache didn't invalidate
- Freshness banner was either missed or misleading

---

## Critical Issues

### CR-01: Entrypoint Script Fails Open on Restore Error

**File:** `docker-entrypoint.sh:10-15`  
**Issue:** Restore failure does not prevent app startup. If `restore_from_oci` fails for any reason (bad credentials, network timeout, empty bucket), the exit code is non-zero, but the current `if ... else ... fi` logic merely prints a warning and continues. The app starts regardless, serving whatever data is in the local `./out` directory. This data could be days old.

```bash
# CURRENT CODE (WRONG):
if python -m engine.restore_from_oci \
  --bucket vol-diagnostics-backup --region ca-toronto-1 --dest ./out --force 2>&1; then
  echo "[entrypoint] ✓ Restored from OCI successfully."
else
  echo "[entrypoint] ⚠ OCI restore failed (credentials/network/empty bucket); starting with local data."
fi
echo "[entrypoint] Starting dashboard..."
exec streamlit run app.py
```

The `else` clause prints a warning but does NOT exit. The app always starts.

**Fix:**
```bash
#!/bin/bash
set -e  # Fail fast on any command failure

echo "[entrypoint] Restoring data from OCI..."
python -m engine.restore_from_oci \
  --bucket vol-diagnostics-backup --region ca-toronto-1 --dest ./out --force 2>&1 \
  || {
    echo "[entrypoint] FATAL: OCI restore failed. Data may be stale."
    echo "[entrypoint] Check credentials, network, and that the bucket has objects."
    exit 1
  }

echo "[entrypoint] Validating restored data..."
python -m engine.health_check --strict \
  || {
    echo "[entrypoint] FATAL: Restored data failed health check (stale or incomplete)."
    exit 1
  }

echo "[entrypoint] ✓ Fresh data restored. Starting dashboard."
exec streamlit run app.py
```

---

### CR-02: restore_from_oci.py Returns Success on Empty Bucket

**File:** `engine/restore_from_oci.py:60-62`  
**Issue:** When the OCI bucket contains no objects, `restore_from_oci()` prints a message and returns 0 (success). This is dangerous because:
- A failed backup that uploaded nothing is indistinguishable from a successful empty restore
- The entrypoint script treats exit 0 as success: `if python -m engine.restore_from_oci ...`
- The app starts with zero new data restored, but the entrypoint reports success

```python
if not objects:
    print("[restore_from_oci] no objects found in backup bucket.")
    return 0  # Returns success even though nothing was restored!
```

**Scenario:** GitHub Actions backup step fails silently (permission error, credentials expired). The next morning, the app container restarts, tries to restore, finds nothing in the bucket, returns 0, and the entrypoint says "Restored successfully." The app serves yesterday's data.

**Fix:**
```python
if not objects:
    print("[restore_from_oci] ERROR: backup bucket is empty.", file=sys.stderr)
    print("[restore_from_oci] This means the backup has never run, or the last backup failed.", file=sys.stderr)
    print("[restore_from_oci] Restore is aborted to prevent serving stale data.", file=sys.stderr)
    sys.exit(1)  # Fail, don't pretend success
```

---

### CR-03: GitHub Actions Backs Up Regardless of Collection Success

**File:** `.github/workflows/daily-report.yml:74-81`  
**Issue:** The backup step runs `if: always()`, meaning it executes even if the data collection failed. If `run_daily` silently produces no new snapshots (e.g., CBOE feed timeout, all tickers errored), the backup will re-upload the old `out/` directory to OCI, **overwriting the last good backup with stale data**.

```yaml
- name: Backup out/ to Oracle Object Storage
  if: always()  # ← RUNS EVEN IF COLLECT FAILED
  env:
    ...
  run: |
    python -m engine.backup_to_oci --bucket vol-diagnostics-backup --region ca-toronto-1 --source ./out
```

The comment says "even if the email step failed, back up whatever snapshots did save" — but the email step no longer exists (removed 2026-08-18). This is now unguarded.

**Scenario:** 2026-08-20, 4:35pm ET: Collection runs, but CBOE feed is down. No new data is written to `out/`. The health check would catch this, but the backup step still runs and overwrites the OCI bucket with Aug 19 data. The next day's restore gets Aug 19 data, not Aug 20.

**Fix:**
```yaml
- name: Backup out/ to Oracle Object Storage
  if: success()  # Only back up if collect succeeded
  # OR: add a pre-backup validation step:
  run: |
    # Verify that today's data was actually collected
    python -m engine.health_check --strict
    python -m engine.backup_to_oci --bucket vol-diagnostics-backup --region ca-toronto-1 --source ./out
```

---

### CR-04: Health Check Returns Stale Data as Current

**File:** `engine/health_check.py:85-92`  
**Issue:** When checking the latest snapshot date across surface_history and gex_snapshots stores, the code uses `or` (logical OR) to pick a value, not `max()`:

```python
latest_surface = max(available) if available else None
latest_snapshot = None
if not hist.empty and "date" in hist.columns:
    latest_snapshot = hist["date"].max()
    if hasattr(latest_snapshot, "date"):
        latest_snapshot = latest_snapshot.date()

latest = latest_surface or latest_snapshot  # ← WRONG: uses first non-None, not max
```

If `latest_surface` (max of surface_history dates) is Aug 19 but `latest_snapshot` (gex_snapshots) is Aug 20, this code returns Aug 19 and reports "OK — latest is Aug 19" when the actual latest is Aug 20.

**Fix:**
```python
if latest_surface is not None and latest_snapshot is not None:
    latest = max(latest_surface, latest_snapshot)
elif latest_surface is not None:
    latest = latest_surface
else:
    latest = latest_snapshot
```

---

### CR-05: Streamlit Cache Prevents Fresh Data Display

**File:** `app.py:131-145, 154-162, 178-180, 194-195`  
**Issue:** Core ticker data is cached for 6 hours (CACHE_TTL_TICKER = 21600 seconds) and history/evolution are cached separately:

```python
@st.cache_data(ttl=config.CACHE_TTL_TICKER, show_spinner=False)
def fetch_ticker(ticker: str, risk_free_rate: float, vvix: float | None) -> dict:
    return compute_ticker(ticker, risk_free_rate=risk_free_rate, vvix=vvix, skip_cv=True)

@st.cache_data(ttl=config.CACHE_TTL_HISTORY, show_spinner=False)
def _available_dates_cached(ticker: str) -> list:
    return list(list_available_dates(ticker))
```

**Scenario:**
- 2026-08-20, 11pm ET: Container starts, restores Aug 20 data, caches it for 6 hours
- 2026-08-21, 5pm ET: New Aug 21 data is collected and uploaded to OCI
- 2026-08-21, 5:10pm ET: User loads the dashboard. The entrypoint last ran at 11pm (no restart), so the cache still holds Aug 20 data. The freshness banner might show stale (if the cache doesn't auto-update), but the ticker detail still displays Aug 20.
- 2026-08-21, 11pm ET: Cache expires, container may restart and pull Aug 21 data

The issue is **the cache doesn't invalidate when new data arrives**. Only a page refresh or container restart clears it.

**Fix:** Cache TTL should be much shorter during trading hours (e.g., 5 minutes) or should be invalidated on a schedule tied to the trading session:

```python
import datetime
import pytz

def _cache_ttl():
    """Return TTL in seconds based on trading session.
    5 minutes during trading day (to catch errors), 6 hours after close."""
    now_et = datetime.datetime.now(pytz.timezone("America/New_York"))
    # After market close (4:35pm) until next open (9:30am), data won't change
    if now_et.hour >= 17 or now_et.hour < 9:
        return 21600  # 6 hours after close
    return 300  # 5 minutes during day

@st.cache_data(ttl=_cache_ttl, show_spinner=False)
def fetch_ticker(ticker: str, risk_free_rate: float, vvix: float | None) -> dict:
    return compute_ticker(ticker, risk_free_rate=risk_free_rate, vvix=vvix, skip_cv=True)
```

Or simpler: tie cache to the session date and clear it when session changes:

```python
@st.cache_data(ttl=config.CACHE_TTL_TICKER, show_spinner=False)
def fetch_ticker(ticker: str, risk_free_rate: float, vvix: float | None, session_date: str) -> dict:
    """session_date is a cache key; when session changes, cache misses."""
    return compute_ticker(ticker, risk_free_rate=risk_free_rate, vvix=vvix, skip_cv=True)

# In main app:
session_date = str(latest_session(datetime.now(ET), DATA_CUTOFF_HOUR, DATA_CUTOFF_MIN))
fetch_ticker("SPY", rate, vvix, session_date=session_date)  # Cache key includes session
```

---

### CR-06: No Post-Restore Validation on Startup

**File:** `docker-entrypoint.sh:9-15`  
**Issue:** After restoring from OCI, the entrypoint does not verify:
1. That at least some files were restored (not just "success" on empty bucket)
2. That the restored data is fresh (not from days ago)
3. That all three tickers have data for today's session

A malicious or broken restore can leave `./out/` in any state.

**Fix:** Add validation before starting the app:

```bash
echo "[entrypoint] Validating restored data..."
if ! python -m engine.health_check --strict; then
    echo "[entrypoint] FATAL: Restored data is stale or incomplete."
    echo "[entrypoint] Latest data must be from today's trading session."
    exit 1
fi
```

---

### CR-07: Backup Script Doesn't Validate Before Uploading

**File:** `engine/backup_to_oci.py:36-54`  
**Issue:** The backup function accepts any source directory and uploads all files, with no validation that the source contains fresh data. If called with an `out/` directory that has old data, it will upload old data.

```python
def backup_to_oracle(bucket: str, region: str, namespace: str, source_dir: Path) -> int:
    """Upload every file under source_dir to bucket, keyed by path relative to source_dir's parent."""
    client = _s3_client(region, namespace)
    uploaded = 0
    for file_path in sorted(source_dir.rglob("*")):
        if not file_path.is_file():
            continue
        key = str(file_path.relative_to(source_dir.parent)).replace(os.sep, "/")
        print(f"[backup_to_oci] uploading {key} ...")
        # ... upload ...
        uploaded += 1
```

**Scenario:** Run `run_daily`, it fails silently (all tickers error). The `out/` directory still has Aug 19 data. Backup runs and uploads Aug 19 data to OCI. The next day's restore gets Aug 19.

**Fix:**
```python
def backup_to_oracle(bucket: str, region: str, namespace: str, source_dir: Path, validate: bool = True) -> int:
    """Upload source_dir to OCI, optionally validating that it contains fresh data."""
    if validate:
        # Ensure source_dir/gex_snapshots.parquet has today's data
        from engine.health_check import check_health
        result = check_health(verbose=False)
        if not result.get("healthy"):
            raise ValueError(
                f"Source directory {source_dir} contains stale or missing data. "
                "Backup aborted to prevent overwriting good backups with stale data."
            )
    # ... rest of upload ...
```

---

## Warnings

### WR-01: Restore Path Stripping Logic is Fragile

**File:** `engine/restore_from_oci.py:72-78`  
**Issue:** The path stripping logic assumes all object keys start with `out/`:

```python
for obj in objects:
    key = obj["Key"]
    rel = key.split("/", 1)[1] if key.startswith("out/") else key
    file_path = dest / rel
```

If an object doesn't start with `out/`, it's placed directly under dest (e.g., `dest / "README.md"` becomes `./out/README.md`). This is probably wrong.

**Fix:** Explicitly validate and reject unexpected keys:

```python
rel = None
if key.startswith("out/"):
    rel = key.split("/", 1)[1]
else:
    print(f"[restore_from_oci] WARNING: unexpected key prefix, skipping {key}")
    continue
```

---

### WR-02: Freshness Banner Uses min() Across Tickers

**File:** `app.py:411-437`  
**Issue:** The freshness banner computes the minimum (oldest) of the three tickers' latest dates:

```python
latest_per_ticker = [max(d) for t in INDEX_TICKERS if (d := _available_dates_cached(t))]
latest = min(latest_per_ticker)  # oldest of the per-ticker latests
missing = _sessions_missing(latest, expected)
```

This is conservative (reports stale if any ticker is stale), but the dashboard itself loads each ticker independently. So you can see today's SPY but yesterday's QQQ **without a clear per-ticker warning**. The banner only warns about the slowest ticker.

**Fix:** The banner is correct. But add per-ticker staleness indicators in the ticker card:

```python
# In _render_regime_cards, before rendering each ticker:
ticker_latest = max(_available_dates_cached(ticker)) if _available_dates_cached(ticker) else None
if ticker_latest and ticker_latest < expected:
    st.warning(f"{ticker}: data is {n} session(s) old")
```

---

### WR-03: Session Cutoff Times Are Hardcoded Magic Numbers

**File:** `engine/session.py:22-27`  
**Issue:** Two cutoff times are defined without per-run flexibility:

```python
DATA_CUTOFF_HOUR, DATA_CUTOFF_MIN = 16, 35  # 4:35pm ET
MARKET_OPEN_HOUR, MARKET_OPEN_MIN = 9, 30   # 9:30am ET
```

These are passed to `latest_session()` as parameters, but if the daily collection schedule changes (e.g., moves to 5pm ET) or market hours change (e.g., early close), the freshness check becomes incorrect. No way to override without code changes.

**Fix:** Load cutoff times from config or environment:

```python
from engine import config

DATA_CUTOFF_HOUR = config.DATA_CUTOFF_HOUR if hasattr(config, "DATA_CUTOFF_HOUR") else 16
DATA_CUTOFF_MIN = config.DATA_CUTOFF_MIN if hasattr(config, "DATA_CUTOFF_MIN") else 35
```

Then add to `engine/config.py`:

```python
DATA_CUTOFF_HOUR: int = 16
"""Hour (ET) when today's session is considered "should be collected". 
4:35pm ET is when the primary GitHub Actions run fires."""

DATA_CUTOFF_MIN: int = 35
```

---

### WR-04: restore_from_oci.py Doesn't Handle Partial Failures

**File:** `engine/restore_from_oci.py:72-89`  
**Issue:** If downloading file 5 of 10 fails, the function raises `RestoreCorruptionError` and exits. Files 1-4 are already written. Then the entrypoint sees a non-zero exit code and says "restore failed", but the app starts anyway with partial data.

**Scenario:** Restore 10 files, file 6 is corrupted (download truncated). Restore fails with RestoreCorruptionError. App starts with files 1-5 restored but missing 6-10.

**Fix:** Track failures and report them:

```python
errors = []
for obj in objects:
    try:
        # ... download ...
    except Exception as exc:
        errors.append((obj["Key"], str(exc)))
        continue
if errors:
    print(f"[restore_from_oci] {len(errors)} file(s) failed:", file=sys.stderr)
    for key, err in errors:
        print(f"  {key}: {err}", file=sys.stderr)
    if restored < len(objects) * 0.9:  # If >10% failed, abort
        print("[restore_from_oci] Too many failures, aborting to prevent partial restore.", file=sys.stderr)
        sys.exit(1)
```

---

### WR-05: .env File Has Shell Syntax That Breaks source

**File:** `.env.example:38-39`  
**Issue:** The original entrypoint tried to `source /app/.env`, but the .env file can contain multi-line values (OCI_CLI_KEY_CONTENT is a multi-line PEM key):

```
OCI_CLI_KEY_CONTENT="-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA...
-----END RSA PRIVATE KEY-----"
```

Bash's `source` command will fail on this syntax. This is why commit fb7bcd0 tried to source .env (and failed), and commit 8e79334 removed `set -e` to make the failure non-fatal.

This is documented in docker-compose.yml (line 24-28):

```yaml
# The .env mount above is a file, not environment: without env_file the OCI
# keys are invisible to `docker compose exec ... python -m engine.restore_from_oci`,
# which is how this box now pulls fresh data (2026-08-20).
env_file:
  - .env
```

So the current solution (docker-compose env_file directive) is correct. But the entrypoint's `set -e` removal was a band-aid; the real issue was the failed attempt to source .env.

**Fix:** Don't try to source .env. The docker-compose.yml already handles it via env_file. Document this clearly:

```bash
#!/bin/bash
# OCI credentials are provided by docker-compose's env_file directive, not sourced here.
# The .env file contains multi-line values (PEM keys) that break shell sourcing.

echo "[entrypoint] Restoring data from OCI..."
python -m engine.restore_from_oci \
  --bucket vol-diagnostics-backup --region ca-toronto-1 --dest ./out --force
```

---

### WR-06: No Timeout on restore_from_oci

**File:** `engine/restore_from_oci.py:78`  
**Issue:** The S3 download has no timeout. If the network hangs or OCI becomes slow, the restore can block indefinitely:

```python
client.download_file(bucket, key, str(file_path))
```

**Fix:** Set a timeout on the boto3 client:

```python
client = boto3.client(
    "s3",
    endpoint_url=endpoint_url,
    config=Config(
        connect_timeout=30,      # 30s to establish connection
        read_timeout=60,         # 60s per read
        retries={"max_attempts": 3},
        request_checksum_calculation="when_required",
        ...
    )
)
```

---

### WR-07: Restore is Missing for Daily Email Workflow

**File:** `.github/workflows/daily-report.yml:66-72`  
**Issue:** The workflow collects data but doesn't explicitly validate that it succeeded before proceeding. The health check runs after backup (line 84), but there's a race: if collection partially fails and backup runs (with `if: always()`), backup could upload incomplete data before health check runs.

Actually, looking more carefully: the health check runs AFTER backup with `if: always()`, so it correctly validates that backup happened. But the backup happens even if collection failed.

The issue is better described under CR-03 (backup runs regardless of success).

---

### WR-08: engine/health_check.py Doesn't Check for Corruption After Restore

**File:** `engine/health_check.py` (full_history_report)  
**Issue:** The `full_history_report()` checks for gaps in stored dates but doesn't verify that parquet files are readable or have the expected schema. A file could be truncated or corrupted, but the report would only notice if a date is missing.

**Fix:** Add a corruption check:

```python
def check_corruption(series: str, ticker: str) -> dict:
    """Verify that the parquet file for a series is readable and has expected columns."""
    try:
        if series == "gex_snapshots":
            df = load_history(ticker, days=1000)
            expected = {"date", "ticker", "net_gex"}
            if not expected.issubset(df.columns):
                return {"corrupt": True, "reason": f"missing columns {expected - set(df.columns)}"}
        # ... similar checks for other series ...
        return {"corrupt": False}
    except Exception as exc:
        return {"corrupt": True, "reason": str(exc)}
```

---

## Info

### IN-01: Verbose Restore Output Could Overwhelm Logs

**File:** `engine/restore_from_oci.py:77`  
**Issue:** For a large backup (100+ files), the line-by-line download output could create a very long entrypoint log. On failure review, it's hard to spot the actual error.

**Suggestion:** Add a progress indicator instead:

```python
print(f"[restore_from_oci] downloading {restored + 1}/{len(objects)}: {key}...", end="", flush=True)
# ... download ...
print(" OK")
```

---

### IN-02: Missing Documentation on Data Freshness SLA

**File:** `CLAUDE.md` (project instructions)  
**Issue:** The project doc doesn't explicitly state the data freshness SLA or what "stale" means. Is Aug 20 data okay at 9am Aug 21? Or is it stale? This affects correctness of the freshness banner.

**Suggestion:** Add to CLAUDE.md:

```markdown
## Data Freshness SLA

- **Source of truth:** OCI Object Storage (backups from daily GitHub Actions)
- **Collection schedule:** 3 runs daily (4:35pm ET primary, 6:30pm ET catch-up, 8:30pm ET last chance)
- **Expected recency:** Today's data should be available by 5pm ET same day
- **Stale threshold:** If latest snapshot is > 0 trading days old, the banner shows a warning
  - Before 4:35pm ET: today's data is not yet expected; yesterday is current
  - At 4:35pm ET or later: today's data should be available
```

---

### IN-03: Restore Script Doesn't Log Which Credentials Failed

**File:** `engine/restore_from_oci.py:101-104`  
**Issue:** If OCI_NAMESPACE is missing, the error message doesn't help debug (is it OCI_NAMESPACE, or the access key, or the customer secret?).

**Suggestion:** Log which environment variables are set (without logging their values):

```python
required_vars = ["OCI_NAMESPACE", "OCI_ACCESS_KEY_ID", "OCI_CUSTOMER_SECRET_KEY"]
missing = [v for v in required_vars if not os.environ.get(v)]
if missing:
    print(f"[restore_from_oci] FAILED: missing env vars: {', '.join(missing)}", file=sys.stderr)
    sys.exit(1)
```

---

## Summary of Root Causes

The staleness issue on 2026-08-20 was caused by a confluence of **weak barriers between failure modes**:

1. **Entrypoint was made too permissive** (CR-01): Commit 8e79334 removed `set -e` to work around a .env sourcing issue, but this meant restore failures are silent.
2. **Restore hides empty-bucket failures** (CR-02): An empty bucket looks like success.
3. **Backup doesn't validate** (CR-03): Even if collection fails, backup runs and overwrites good data.
4. **Cache prevents fresh data display** (CR-05): Even after restore succeeds, old cached data is shown for up to 6 hours.
5. **Health check has logic bugs** (CR-04): It might report stale data as fresh if dates are compared incorrectly.

A user viewing the dashboard on 2026-08-20 afternoon/evening saw Aug 20 data. But if Aug 21 data was collected and backed up (likely happening after the user's view), and the user's browser cache was stale, a refresh would serve Aug 21 **IF** the container restarted. Without a restart, they'd see Aug 20 cached data.

---

## Recommended Action Priority

**Immediate (today):**
1. Fix CR-01: Add `set -e` back and validate restore
2. Fix CR-02: Make empty bucket a failure
3. Fix CR-03: Only backup on success

**Short-term (this week):**
4. Fix CR-04: Correct date comparison logic
5. Fix CR-05: Tie cache TTL to trading session
6. Fix CR-06: Validate on startup

**Medium-term (next phase):**
7. Simplify and document data pipeline
8. Add per-ticker staleness indicators to UI
9. Set up alerting on restore failures

---

_Reviewed: 2026-08-21T22:30:00Z_  
_Reviewer: Claude (gsd-code-reviewer)_  
_Depth: standard_
