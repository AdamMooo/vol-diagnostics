# Phase 23: Data Completeness, Backup & Model-Readiness Audit - Research

**Researched:** 2026-07-21
**Domain:** Data integrity & health check extension, backup/restore infrastructure, model-readiness specification
**Confidence:** HIGH (stack patterns verified against codebase), MEDIUM-HIGH (Oracle backup auth), MEDIUM (model-readiness depth targets — grounded in literature but project-specific)

## Summary

This phase extends the existing `engine/health_check.py` tail-freshness checker to scan the FULL date range of four data stores (`gex_snapshots`, `surface_history`, `vol_index`, `oi_history`) across three tickers (SPY/QQQ/IWM) for internal gaps — not just checking if the latest snapshot is fresh. It adds off-VM backup of `out/` to Oracle Object Storage via a new GitHub Actions step (reusing existing SSH auth + adding a new OCI credential secret), and defines a written spec of minimum-depth targets for each series before a predictive/prescriptive model could be built on it. The three slices (gap detection, backup/restore, model-readiness audit) are merged into one phase because they share the same "make data trustworthy before modeling" narrative arc and the audit already depends on the gap scanner.

**Primary recommendation:** 
1. Extend `engine/health_check.py` with a full-history gap scanner (walk NYSE trading calendar against stored dates per series/ticker) — keep existing tail-check, add new full-history mode runnable as `--full-history` flag
2. Add backup step to `.github/workflows/daily-report.yml` using boto3 + Oracle S3-compatible endpoint, authenticated with a new `OCI_CUSTOMER_SECRET_KEY` (and `OCI_ACCESS_KEY_ID`) GitHub secret
3. Define model-ready depth targets in `.planning/notes/MODEL-READY-DATA-SPEC.md` grounded in GARCH/RV/percentile-ranking literature; audit current depth per series and report gaps

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Gap findings surface via the existing GitHub Actions `--strict` gate only (`.github/workflows/daily-report.yml` already runs `python -m engine.health_check --strict` daily). No dashboard panel.
- **D-02:** Extend `engine/health_check.py` rather than write a separate gap-audit script.
- **D-03:** Extend coverage from 2 series (`surface_history`, `gex_snapshots`) to all 4 (`vol_index`, `oi_history` added).
- **D-04:** Full-history scan required (not just tail-freshness check). Walk the NYSE session calendar across the store's full date range per series/ticker to catch silent mid-history gaps.
- **D-05:** `vol_index` (VIX/VXN/RVX/VIX9D/VIX3M/VVIX) is CBOE-published historical CSV data, not our own daily collection — missing sessions most often mean CBOE didn't publish (holiday, outage) rather than our fetch failing. Treat as "no data expected" only when it doesn't correspond to a valid NYSE trading day still expected to have OI/surface data.
- **D-06:** Back up `out/` to Oracle Cloud Object Storage (Always Free tier, 10 GB), under the same Oracle account hosting the VM.
- **D-07:** Extend the existing `.github/workflows/daily-report.yml` run rather than add a second scheduled job — backup as one more step in that same job.
- **D-08:** Restore path must be a runnable script (not prose) — e.g. `scripts/restore-from-backup.sh` or `.ps1`, mirroring existing `scripts/migrate-data.ps1` / `scripts/update.sh` pattern.
- **D-09:** Model-ready spec lives in `.planning/notes/MODEL-READY-DATA-SPEC.md`, linked from PROJECT.md (not inlined).

### Claude's Discretion
- Exact report format (CLI table vs. JSON vs. both) — extend existing `check_health()` `--json` / human-readable pattern
- Whether full-history scan runs on every `--strict` invocation or as a separate periodic/manual command
- Backup cadence / retention policy for the Object Storage bucket
- The actual minimum-depth-per-series numbers (flagged for research, D-10) — must be grounded in stated quant rationale

### Deferred Ideas (OUT OF SCOPE)
- None raised during discussion

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-01 | A report/script identifies missing-session gaps per data series (`gex_snapshots`, `surface_history`, `vol_index`, `oi_history`) per ticker | Full-history gap scanner extends `check_health()` to walk NYSE calendar against stored dates |
| DATA-02 | Gap findings are surfaced somewhere visible (health-check output), not just sitting silently | `--strict` gate already fails build; extend to include full-history findings in existing output |
| BACKUP-01 | `out/` parquet stores are backed up somewhere other than the single Oracle VM | New GitHub Actions step pushes to Oracle Object Storage via boto3 S3-compatible API |
| BACKUP-02 | A documented/automated restore path exists — not just backup, but way to rebuild if Oracle instance is lost | New `scripts/restore-from-backup.sh` (or `.ps1`) script that downloads from Object Storage and rehydrates `out/` tree |
| SCHEMA-01 | A written spec defines, per data series, the minimum depth (sessions) and schema needed before a predictive/prescriptive model could be built | `.planning/notes/MODEL-READY-DATA-SPEC.md` with table: series → min sessions (grounded in GARCH/RV/percentile literature) → required columns |
| SCHEMA-02 | Current actual depth per series is measured against those targets | Extend `check_health()` or new audit subcommand to report current depth per series/ticker vs. targets |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Full-history gap detection | Data/Backend | — | Operates on parquet file system; logic runs in Python during daily CI job, no UI needed (D-01) |
| Backup orchestration | API/Backend + CI/CD | — | Triggered by GitHub Actions job; lives in workflow YAML + Python backup helper |
| Restore (dry-run capable) | API/Backend + Scripts | — | Runnable CLI script that fetches from Object Storage, reconstructs `out/` tree on local machine or re-deployed VM |
| Model-readiness audit | Data/Backend | — | Reports depth/schema vs. spec; runs as Python CLI (integrated into `check_health()` or separate subcommand) |
| Health-check output | API/Backend | Frontend (for dashboarding, but explicitly deferred) | Existing `check_health()` returns dict; output format extensible; D-01 forbids new dashboard panel |

## Standard Stack

### Core (Existing, No Changes)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | ≥1.5 | Parquet read/write, DataFrame operations | Already required in `requirements.txt`; all data stores use `pd.read_parquet()` |
| pandas-market-calendars | (version from requirements.txt) | NYSE trading calendar for gap detection | Already imported in `engine/health_check.py`; provides `nyse.schedule()` for calendar arithmetic |
| Python | 3.11 | Runtime | Project standard; GitHub Actions uses `actions/setup-python@v5` with 3.11 |

### New Libraries (Minimal Add)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| boto3 | ≥1.26 | AWS SDK for Python; Oracle Object Storage S3-compatible API access | Backup step in GitHub Actions; also supports local restore script; simpler than OCI SDK for this use case (see D-06 research) |
| (Optional) oci | ≥2.0+ | Oracle Cloud Infrastructure native Python SDK | Only if choosing OCI API over boto3; NOT recommended unless needing Instance Principals auth later |

**Installation:**
```bash
pip install boto3>=1.26
# oci is optional; do not add unless explicitly decided to use native OCI SDK over S3-compatible API
```

**Version verification:** 
```bash
pip index versions boto3
# Expected: 1.34+ (current as of 2026-07); S3-compatible API stable for years
```

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| boto3 + S3-compatible API | OCI Python SDK + config-file auth | OCI SDK is native but requires `~/.oci/config` and API key setup; boto3 reuses existing S3-familiarity and GitHub secret pattern |
| boto3 + S3-compatible API | OCI CLI + shell scripts | OCI CLI adds CLI dependency; less portable across dev/CI environments |
| boto3 + GitHub secret | Temporary STS credentials via OIDC | OIDC more secure (no long-lived secrets) but requires GitHub's OIDC trust setup with OCI — simpler to start with secret, upgrade later |

**Recommendation:** Use **boto3 + S3-compatible API + GitHub secret** for Phase 23. It's the simplest correct path: S3-compatible endpoint is already documented by Oracle for Object Storage, boto3 is lightweight, and GitHub secret reuses the existing `secrets.ORACLE_SSH_KEY` pattern. OIDC + OCI SDK can be a future upgrade after this phase establishes the pattern.

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| boto3 | PyPI | 8+ yrs | 100M+/wk | [github.com/boto/boto3](https://github.com/boto/boto3) | [OK] | Approved — production-standard AWS SDK |
| oci | PyPI | 7+ yrs | 500k+/wk | [github.com/oracle/oci-python-sdk](https://github.com/oracle/oci-python-sdk) | [OK] | Optional; approved if chosen |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

*All packages were verified against PyPI and cross-referenced with official source repositories.*

## Architecture Patterns

### System Architecture Diagram

```
GitHub Actions (daily-report.yml)
  ├─ Pull `out/` from Oracle VM via rsync+SSH
  ├─ Run daily collection (run_daily.py)
  │   └─ Emit new snapshots → out/gex_snapshots.parquet
  │                        → out/surface_history/surface_{ticker}.parquet
  │                        → out/vol_index/{VIX,VXN,…}.parquet
  │                        → out/oi_history/oi_{ticker}.parquet
  ├─ [NEW] Health check (engine.health_check --strict --full-history)
  │   ├─ Walk NYSE calendar for each series
  │   ├─ Compare to stored dates; report gaps
  │   └─ Fail build if gaps detected (--strict)
  ├─ [NEW] Backup to Oracle Object Storage (boto3 S3-API)
  │   ├─ Upload out/* to OCI bucket
  │   └─ Track backup completion
  ├─ Push updated `out/` back to Oracle VM via rsync+SSH
  └─ Report results (email, GH Actions log)

Restore Flow (independent, on-demand):
  scripts/restore-from-backup.sh
    ├─ Fetch out/* from Oracle Object Storage (boto3 S3-API)
    ├─ Reconstruct local out/ tree
    └─ Dry-run: verify reconstruction without overwriting
```

### Recommended Project Structure

```
engine/
  ├─ health_check.py          # [EXTEND] add --full-history mode + full-history scanner logic
  ├─ data/
  │   ├─ validation.py         # gex_snapshots.parquet (date column, single file)
  │   ├─ surface_history.py    # surface_{ticker}.parquet (date, per-ticker files)
  │   ├─ vol_index.py          # {VIX,VXN,…}.parquet (date, per-symbol files, CBOE historical CSV)
  │   ├─ oi_history.py         # oi_{ticker}.parquet (date, per-ticker files)
  │   └─ store.py              # atomic_to_parquet() helper (unchanged)
  ├─ tests/
  │   └─ test_data_health.py   # [EXTEND] add full-history gap tests
  └─ ... (unchanged)

scripts/
  ├─ restore-from-backup.sh    # [NEW] or .ps1 — bash preferred if running on both local+Oracle
  ├─ update.sh                 # (unchanged)
  ├─ migrate-data.ps1          # (unchanged)
  └─ ...

.github/workflows/
  └─ daily-report.yml          # [EXTEND] add backup step before final health-check

.planning/notes/
  └─ MODEL-READY-DATA-SPEC.md  # [NEW] per D-09
```

### Pattern 1: Full-History Gap Scanner

**What:** Extend `engine/health_check.py:check_health()` to walk the NYSE trading calendar against stored dates in each parquet store, detecting sessions with zero data when data was expected.

**When to use:** On every CI `--strict` invocation (or as separate `--full-history` flag if runtime is a concern). The existing tail-freshness check stays; this adds the gap-interior detection.

**Algorithm:**

```python
# Pseudocode for full_history_scan(ticker, series_name, store_path)
def full_history_scan(ticker: str, series_name: str, store_path: Path) -> dict:
    """
    Walk NYSE calendar from first stored session to today.
    For each trading day, check if it has a row in the store.
    
    Args:
        ticker: 'SPY', 'QQQ', 'IWM' (or vol-index symbol like 'VIX')
        series_name: 'gex_snapshots' | 'surface_history' | 'vol_index' | 'oi_history'
        store_path: Path to parquet file or directory
    
    Returns:
        {
            'ticker': str,
            'series': str,
            'earliest': date,           # earliest date in store
            'latest': date,             # latest date in store
            'total_sessions': int,      # days from earliest to latest (not counting gaps)
            'gaps': [                   # list of missing sessions
                {'date': date, 'reason': 'NYSE closed' | 'data missing'}
            ],
            'gap_count': int
        }
    
    Steps:
    1. Read parquet, extract unique dates per store schema:
       - gex_snapshots: filter by ticker, get unique dates
       - surface_history: ticker-specific file, get unique dates
       - vol_index: symbol-specific file, get unique dates
       - oi_history: ticker-specific file, get unique dates
    
    2. Find min(dates), max(dates)
    
    3. Get NYSE calendar schedule from min to max via pandas_market_calendars
    
    4. For each NYSE session in that calendar:
       if session NOT in stored dates:
           if session is today AND market hasn't closed yet: skip (ongoing)
           else: record as gap
    
    5. For vol_index only (D-05): if a session is missing but CBOE didn't publish that day
       (e.g., CBOE holiday, data outage), mark as "no data expected" (don't flag as error)
       — but flag it if the same date DOES have GEX/surface/OI data (i.e., we collected
       other data that day, so CBOE should have published)
    
    6. Return gap count and details
    """
```

**Example output:**

```
[gex_snapshots] SPY
  Earliest: 2026-05-06, Latest: 2026-07-21, Sessions: 52 (expected: 52, no gaps)

[surface_history] SPY
  Earliest: 2026-05-06, Latest: 2026-07-21, Sessions: 52
  Gaps: 1
    - 2026-06-15 (data missing; GEX + OI data present that day — likely fetch failure)

[vol_index] VIX
  Earliest: 1990-01-02, Latest: 2026-07-18, Sessions: ~9,100
  Gaps: 3 (all CBOE holidays — skipped)
    - 2026-07-04 (CBOE closed — expected)
    - 2026-12-25 (CBOE closed — expected)
    - 2026-01-01 (CBOE closed — expected)

[oi_history] SPY
  Earliest: 2026-05-06, Latest: 2026-07-21, Sessions: 52 (no gaps)
```

### Pattern 2: Backup to Oracle Object Storage

**What:** Add a GitHub Actions step that uploads `out/` to Oracle Cloud's S3-compatible Object Storage endpoint, authenticated with a Customer Secret Key.

**When to use:** Runs automatically as part of the daily `.github/workflows/daily-report.yml` pipeline, after data collection and before final health-check.

**GitHub Actions step (YAML):**

```yaml
- name: Backup out/ to Oracle Object Storage
  if: always()  # run even if earlier steps failed, so incomplete data is still backed up
  env:
    OCI_ACCESS_KEY_ID: ${{ secrets.OCI_ACCESS_KEY_ID }}
    OCI_CUSTOMER_SECRET_KEY: ${{ secrets.OCI_CUSTOMER_SECRET_KEY }}
  run: |
    python -m engine.backup_to_oci \
      --bucket vol-diagnostics-backup \
      --region ca-toronto-1 \
      --source ./out
```

**Python helper (`engine/backup_to_oci.py`):**

```python
import argparse
import os
from pathlib import Path
import boto3

def backup_to_oracle(bucket: str, region: str, source_dir: Path):
    """Upload out/ tree to Oracle Object Storage via S3-compatible API.
    
    Args:
        bucket: bucket name (e.g., 'vol-diagnostics-backup')
        region: Oracle region (e.g., 'ca-toronto-1')
        source_dir: local directory to backup (e.g., Path('./out'))
    
    Requires env vars:
        OCI_ACCESS_KEY_ID: Customer Access Key from OCI User settings
        OCI_CUSTOMER_SECRET_KEY: Customer Secret Key
    
    Uses Oracle's S3-compatible endpoint:
        https://{namespace}.compat.objectstorage.{region}.oraclecloud.com
    
    Where {namespace} is derived from the OCI tenancy.
    """
    access_key = os.environ['OCI_ACCESS_KEY_ID']
    secret_key = os.environ['OCI_CUSTOMER_SECRET_KEY']
    namespace = os.environ.get('OCI_NAMESPACE', 'derived-at-runtime')
    
    # Connect to Oracle Object Storage via S3-compatible endpoint
    endpoint_url = f"https://{namespace}.compat.objectstorage.{region}.oraclecloud.com"
    
    s3_client = boto3.client(
        's3',
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )
    
    # Recursively upload all files in out/
    for file_path in source_dir.rglob('*'):
        if file_path.is_file():
            key = str(file_path.relative_to(source_dir.parent))
            print(f"[backup] uploading {key} ...")
            s3_client.upload_file(str(file_path), bucket, key)
    
    print(f"[backup] complete. {bucket} updated.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--bucket', required=True)
    parser.add_argument('--region', required=True)
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    
    backup_to_oracle(args.bucket, args.region, args.source)
```

### Pattern 3: Restore from Backup

**What:** Standalone script that downloads `out/` from Oracle Object Storage and reconstructs a working parquet tree locally or on a re-deployed VM.

**When to use:** On-demand, after VM loss or to set up a new environment with historical data.

**Script (`scripts/restore-from-backup.sh` — bash preferred for cross-platform):**

```bash
#!/usr/bin/env bash
# Restore out/ from Oracle Object Storage backup.
# Requires: boto3 installed, OCI_ACCESS_KEY_ID and OCI_CUSTOMER_SECRET_KEY env vars set.
#
# Usage:
#   OCI_ACCESS_KEY_ID=... OCI_CUSTOMER_SECRET_KEY=... ./scripts/restore-from-backup.sh --dry-run
#   OCI_ACCESS_KEY_ID=... OCI_CUSTOMER_SECRET_KEY=... ./scripts/restore-from-backup.sh

set -euo pipefail

DRY_RUN=false
BUCKET="vol-diagnostics-backup"
REGION="ca-toronto-1"
OUT_DIR="./out"

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run) DRY_RUN=true; shift ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

# Derive namespace from OCI tenancy (typically stored in config, or ask user)
# For simplicity, assume it's passed as env var or hardcoded after first setup
NAMESPACE="${OCI_NAMESPACE:-}"
if [ -z "$NAMESPACE" ]; then
    echo "Error: OCI_NAMESPACE not set. Set it to your OCI object-storage namespace."
    exit 1
fi

ENDPOINT_URL="https://${NAMESPACE}.compat.objectstorage.${REGION}.oraclecloud.com"

mkdir -p "$OUT_DIR"

if [ "$DRY_RUN" = true ]; then
    echo "[restore] DRY RUN mode — listing objects only, not downloading"
else
    echo "[restore] Downloading from $ENDPOINT_URL/$BUCKET ..."
fi

# Python one-liner to do the download (avoids Bash complexity with boto3)
python3 <<'PYTHON_EOF'
import os
import sys
from pathlib import Path
import boto3

bucket = "vol-diagnostics-backup"
region = "ca-toronto-1"
namespace = os.environ["OCI_NAMESPACE"]
endpoint_url = f"https://{namespace}.compat.objectstorage.{region}.oraclecloud.com"
out_dir = Path("./out")
dry_run = "$DRY_RUN" == "true"

s3_client = boto3.client(
    's3',
    endpoint_url=endpoint_url,
    aws_access_key_id=os.environ["OCI_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["OCI_CUSTOMER_SECRET_KEY"],
    region_name=region,
)

response = s3_client.list_objects_v2(Bucket=bucket)
if "Contents" not in response:
    print("[restore] No objects found in backup bucket.")
    sys.exit(0)

print(f"[restore] Found {len(response['Contents'])} objects to restore")

for obj in response["Contents"]:
    key = obj["Key"]
    file_path = Path(key)
    
    if dry_run:
        print(f"  {key} ({obj['Size']} bytes)")
    else:
        print(f"  [restore] downloading {key} ...")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        s3_client.download_file(bucket, key, str(file_path))

if not dry_run:
    print("[restore] download complete.")
    print(f"[restore] out/ tree reconstructed to {out_dir.resolve()}")
PYTHON_EOF
```

### Anti-Patterns to Avoid

- **Scanning only the tail:** `check_health()` currently only checks `max(dates) >= expected_date`. This misses mid-history gaps (e.g., a day the scheduler crashed weeks ago). Full-history scan is necessary per D-04.
- **Hard-coding boto3 credentials in code:** Always read from environment variables (`OCI_ACCESS_KEY_ID`, `OCI_CUSTOMER_SECRET_KEY`) or config files, never hardcode them.
- **Treating CBOE missing data as an error:** D-05 distinguishes between "we should have collected this but didn't" (error) and "CBOE didn't publish" (expected). The scanner must cross-reference: if GEX/OI/surface data exists for a date but vol_index doesn't, flag it; if none exist, assume CBOE holiday.
- **Backup without restore testing:** D-08 requires a restore script, not just "we upload files." Must be tested at least once (dry-run acceptable) to verify the data can actually be reconstructed.
- **Mixing backup cadences:** D-07 says extend the existing daily job, not add a second cron. Avoid separate scheduled backup tasks.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| NYSE trading calendar arithmetic | Custom date loop / holiday list | `pandas_market_calendars.get_calendar("NYSE").schedule()` | Calendar is complex (floats, half-days); the library is standard in quant Python |
| S3 / Object Storage API | Raw HTTP requests to Oracle endpoint | boto3 (S3-compatible) or OCI SDK | Handles retries, auth, multipart uploads, headers correctly; don't reinvent |
| Parquet reading/writing | Manual pickle / JSON serialization | `pd.read_parquet()` / `pd.to_parquet()` via `atomic_to_parquet()` | All stores already use parquet; columnar format is efficient + schema-aware |
| Date serialization (parquet ↔ Python) | String parsing in loops | `pd.to_datetime().dt.date` vectorized | All stores use this pattern already; leverage it |

**Key insight:** The core gap-scanning logic is the only "new" code. The rest (backup, restore, audit output) reuse existing patterns (boto3 is standard, script style matches `migrate-data.ps1` / `update.sh`, test pattern matches `test_data_health.py`).

## Runtime State Inventory

**Not applicable** — this is not a rename/refactor/migration phase. The phase does not rename runtime state or change existing system identities.

## Common Pitfalls

### Pitfall 1: Missing CBOE holidays in gap detection

**What goes wrong:** vol_index gaps on CBOE holidays (e.g., 2026-07-04) are flagged as errors, breaking the `--strict` gate even though data collection did its job correctly.

**Why it happens:** CBOE publishes historical CSV data, not on-demand; holidays simply don't have rows. Conflating "no data in vol_index" with "something broke" is wrong — it's expected.

**How to avoid:** In `full_history_scan()`, cross-reference: if a date is missing from vol_index BUT has data in gex_snapshots/surface_history/oi_history (i.e., we collected on that day), flag it. If NONE of the series have that date, assume CBOE didn't publish (per D-05).

**Warning signs:** Health-check fails on US market holidays; `--strict` blocks the build on July 4 / Thanksgiving even though all three tickers collected fine.

### Pitfall 2: Forgetting the OCI_NAMESPACE derivation

**What goes wrong:** Backup step in GitHub Actions fails silently or with a generic "endpoint not found" error because the S3-compatible endpoint URL is malformed.

**Why it happens:** Oracle Object Storage S3-compatible endpoint format is `https://{namespace}.compat.objectstorage.{region}.oraclecloud.com`, where `{namespace}` is tenant-specific. It's not the same as the bucket name or account ID.

**How to avoid:** Store `OCI_NAMESPACE` as a GitHub secret (alongside the credentials) or derive it programmatically from OCI API (but simpler to just store it). Document this in the backup script and the ORACLE-CLOUD-SETUP.md update.

**Warning signs:** boto3 connection test succeeds locally but fails in GitHub Actions; error message mentions "InvalidEndpoint" or "Could not connect to the endpoint URL."

### Pitfall 3: Restore script assumes all files can be re-downloaded as-is

**What goes wrong:** Restore completes but `engine.health_check --strict` on the re-downloaded data fails because timestamps/column types got corrupted during upload/download.

**Why it happens:** Parquet is a binary format; if the S3 upload/download doesn't preserve byte-for-byte integrity, reading the file later will fail or produce NaN data.

**How to avoid:** Test restore with a dry-run first (`--dry-run` flag); download a small subset and run `pd.read_parquet()` on it locally before declaring success.

**Warning signs:** Dry-run succeeds but actual restore followed by `health_check` reports NaN or missing columns; parquet read errors in the restore verification step.

### Pitfall 4: Full-history scan is too slow

**What goes wrong:** Adding full-history scan to every `--strict` invocation (which runs daily in CI) slows the job down enough to hit GitHub Actions timeout (6 hours default).

**Why it happens:** Walking NYSE calendar from 2026-05-06 to today and checking each date against 4 stores × 3 tickers = lots of parquet reads and comparisons. If not optimized (vectorized operations instead of loops), it balloons.

**How to avoid:** Implement the scan efficiently:
  1. Load each parquet once into memory (full store)
  2. Extract dates vectorized (one `.unique()` call per store, not a loop)
  3. Walk calendar once, check membership in a set (O(1) lookup)
  Don't make a parquet read per date or per store; consolidate reads.

**Warning signs:** `python -m engine.health_check --strict --full-history` takes > 2 minutes locally; CI job duration spikes noticeably.

## Code Examples

Verified patterns from the codebase:

### Existing: Read parquet and extract unique dates (pattern used in surface_history.py, oi_history.py)

```python
# Source: engine/data/surface_history.py:list_available_dates()
def list_available_dates(ticker: str) -> list[datetime.date]:
    path = _store_path(ticker)
    if not path.exists():
        return []
    try:
        hist = pd.read_parquet(path, columns=["date"])  # read only date column for speed
        dates = pd.to_datetime(hist["date"]).dt.date.unique()  # vectorized
        return sorted(set(dates), reverse=True)
    except Exception as exc:
        print(f"[surface_history] list_available_dates failed for {ticker}: {exc}")
        return []
```

This pattern (read one column → convert to date → unique → sort) is efficient and used throughout. Extend it:

```python
def list_all_dates_in_store(store_path: Path, date_column: str = "date") -> set[datetime.date]:
    """Efficiently extract all unique dates from a parquet store."""
    if not store_path.exists():
        return set()
    try:
        df = pd.read_parquet(store_path, columns=[date_column])
        dates = pd.to_datetime(df[date_column]).dt.date.unique()
        return set(dates)
    except Exception as exc:
        print(f"[health_check] Failed to read dates from {store_path}: {exc}")
        return set()
```

### Existing: NYSE calendar operations (pattern used in health_check.py)

```python
# Source: engine/health_check.py:_last_expected_session()
def _last_expected_session(today: date | None = None) -> date:
    """Most recent NYSE trading day that should have a snapshot by now."""
    today = today or date.today()
    nyse = mcal.get_calendar("NYSE")
    sched = nyse.schedule(
        start_date=(today - timedelta(days=14)).strftime("%Y-%m-%d"),
        end_date=today.strftime("%Y-%m-%d"),
    )
    sessions = [d.date() for d in sched.index]
    if not sessions:
        return today
    # ... (time-of-day logic omitted)
    return sessions[-1]
```

Extend to walk a full date range:

```python
def get_nyse_sessions(start_date: date, end_date: date) -> set[datetime.date]:
    """Get all NYSE trading days between start and end (inclusive)."""
    nyse = mcal.get_calendar("NYSE")
    sched = nyse.schedule(
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
    )
    return set(d.date() for d in sched.index)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tail-only health check (`max(dates) >= expected`) | Full-history gap detection (walk calendar vs. stored dates) | This phase (D-04) | Catches mid-history gaps that tail check misses; more robust for long-running collection |
| Manual rsync up/down from Oracle VM | Automated backup to Oracle Object Storage in CI | This phase (D-06/D-07) | Reduces single point of failure (VM disk) to independent cloud bucket; no manual step |
| No written model-readiness spec | MODEL-READY-DATA-SPEC.md with minimum-depth table per series | This phase (D-09/D-10) | Provides objective gate for when data is sufficient before building a model |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | boto3 with S3-compatible endpoint is the simplest auth approach for Oracle Object Storage from GitHub Actions | Standard Stack (Alternatives) | If OCI SDK or direct OCI CLI is mandated, would add complexity and require different credential setup; decision is slightly uncertain pending user confirmation |
| A2 | GARCH(1,1) minimum ~500–1000 observations applies to this project's eventual modeling work | Model-Ready Depths | If project chooses a different model family (e.g., regime-switching HMM, which has different data needs), targets would shift; contingent on future model spec |
| A3 | NYSE calendar + CBOE holiday cross-reference is sufficient to distinguish "we didn't collect" from "CBOE didn't publish" | Full-History Scan Pattern | If CBOE sometimes publishes on dates we'd classify as "CBOE holidays," this heuristic breaks; requires validation against actual CBOE historical gaps |
| A4 | OCI_NAMESPACE is static per tenancy and can be stored as a GitHub secret safely | Backup Pattern (Pitfall 2) | If Oracle rotates namespaces or if namespace is considered sensitive, the assumption breaks; unlikely but should be verified |

## Open Questions

1. **Exact format of gap report — how detailed?**
   - What we know: D-01 says "surface via health-check output," existing `--strict` already prints human-readable + `--json` support
   - What's unclear: Should full-history gaps be inline with the tail-check summary, or a separate "internal gaps" section? Should the JSON include the full list of gap dates or just counts?
   - Recommendation: Start with a simple counts approach ("5 gaps detected between 2026-06-10 and 2026-06-20") and add detail if the planner/executor wants it. The `--json` output can include a full gap list for downstream automation.

2. **Should full-history scan run on EVERY `--strict` invocation or as a separate periodic/manual command?**
   - What we know: D-04 requires full-history detection; D-07 says extend the existing daily job (no new cron)
   - What's unclear: Runtime cost — full-history scan of 4 stores × 3 tickers from May 2026 to now might be 1–2 seconds (not a blocker) but we don't have exact timing yet
   - Recommendation: Implement as `--full-history` flag (off by default on daily runs, but enabled on `--strict` which already has some slack time). Measure runtime; if < 5 seconds, enable it always.

3. **How deep is "deep enough" for Model-Readiness? Exact session numbers?**
   - What we know: GARCH(1,1) needs 500–2000; percentiles need 30; RV20 needs 252 days of prior history (but we only rank against CBOE vol-index which has decades)
   - What's unclear: Project's actual model plan. If it's GARCH for surface fitting, targets are one thing; if it's Bayesian percentile-ranking (like VRP), targets are another.
   - Recommendation: D-10 explicitly defers this to research/planning with quant rationale. This research provides the literature; the planner/executor should make the final call with the project owner, grounding it in the model idea that's in scope for v5.x.

4. **Restore script — should it be bash or PowerShell?**
   - What we know: Project uses both (scripts/update.sh is bash, scripts/migrate-data.ps1 is PowerShell)
   - What's unclear: Which is "primary" for this phase? GH Actions runner is Linux (ubuntu-latest), so bash is native there; but local developer restore might be on Windows.
   - Recommendation: Write both, or write bash for CI/Oracle server and a separate `.ps1` for local Windows restore. Start with bash since that's what the GH Actions step would call.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| boto3 | Backup step in GitHub Actions | ✓ (add to requirements.txt) | 1.26+ | Use OCI Python SDK instead (more setup, but native) |
| pandas-market-calendars | Full-history gap scan | ✓ (already in requirements.txt) | current | Manual NYSE calendar CSV (not maintained, risky) |
| pandas | All parquet operations | ✓ (already in requirements.txt) | ≥1.5 | None (foundational) |
| OCI Object Storage bucket | Backup storage | ✓ (existing Oracle account, 20 GB free always) | — | AWS S3 or other cloud blob storage (adds vendor, breaks "free" pattern) |
| Oracle SSH credentials | Existing rsync sync | ✓ (secrets.ORACLE_SSH_KEY in use) | — | VPN + direct disk access (complex, risky) |

**Missing dependencies with no fallback:**
- None for Phase 23.

**Missing dependencies with fallback:**
- OCI SDK is optional if using boto3 path (recommended).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | pyproject.toml (or pytest.ini if added) |
| Quick run command | `pytest engine/tests/test_data_health.py -x` |
| Full suite command | `pytest engine/tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01 | Full-history gap scan detects a known gap | unit | `pytest engine/tests/test_data_health.py::TestFullHistoryGapScan::test_detects_known_gap -x` | ❌ Wave 0 |
| DATA-01 | Scan returns clean "no gaps" on complete data | unit | `pytest engine/tests/test_data_health.py::TestFullHistoryGapScan::test_no_false_positives -x` | ❌ Wave 0 |
| DATA-02 | Gap findings appear in health-check `--strict` output | integration | `pytest engine/tests/test_data_health.py::TestHealthCheckStrict -x` | ❌ Wave 0 |
| BACKUP-01 | Backup step uploads files to Object Storage | integration (requires OCI credentials) | Manual or integration env setup | ❌ Wave 0 |
| BACKUP-02 | Restore script downloads and reconstructs `out/` tree | integration (dry-run only in CI) | `./scripts/restore-from-backup.sh --dry-run` | ❌ Wave 0 |
| SCHEMA-01 | Model-ready spec is readable and linked from PROJECT.md | documentation | Manual review | ❌ Wave 0 |
| SCHEMA-02 | Depth audit reports current vs. target per series | unit/integration | `pytest engine/tests/test_data_health.py::TestModelReadinessAudit -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest engine/tests/test_data_health.py -x` (quick run, <30 seconds)
- **Per wave merge:** `pytest engine/tests/ -x` (full suite, includes all data + integration tests)
- **Phase gate:** Full suite green + successful dry-run of restore script before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `engine/tests/test_data_health.py` — extend with `TestFullHistoryGapScan`, `TestHealthCheckStrict`, `TestModelReadinessAudit` classes
- [ ] `.planning/notes/MODEL-READY-DATA-SPEC.md` — new documentation file defining depth targets
- [ ] `engine/backup_to_oci.py` — new module for backup logic (or inline into `health_check.py`'s `main()`)
- [ ] `scripts/restore-from-backup.sh` — new restore script (or `.ps1` variant for Windows)
- [ ] Update `.github/workflows/daily-report.yml` — add backup step after `run_daily`
- [ ] Update `.planning/notes/ORACLE-CLOUD-SETUP.md` — add Object Storage credential setup instructions

*(All gaps are in scope for the planner to break into tasks.)*

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | GitHub secret for OCI credentials; boto3 env-var auth from secrets |
| V3 Session Management | no | No session tokens in scope |
| V4 Access Control | yes | OCI Object Storage bucket IAM policy (restrict to vol-diagnostics backup only, not whole account) |
| V5 Input Validation | yes | Restore script validates downloaded parquet files (check for corruption via `pd.read_parquet()` before using) |
| V6 Cryptography | yes | S3-compatible API uses HTTPS (encrypted in transit); OCI always enforces encryption at rest |

### Known Threat Patterns for {Python data stack + GitHub Actions + Oracle Cloud}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Leaked OCI credentials in logs | Spoofing / Tampering | Use GitHub environment secrets (masked in logs), never print credentials; boto3 respects this |
| Man-in-the-middle on backup upload | Tampering | HTTPS only via boto3 S3 endpoint (enforced); OCI Object Storage always requires HTTPS |
| Compromised VM uploads malicious parquet to backup | Tampering | Backup runs in GitHub Actions (separate environment from VM); if VM is compromised, Actions job still has its own isolated credentials |
| Corrupted parquet during S3 download | Tampering | Restore script validates parquet after download (try `pd.read_parquet()` on each file); fail loudly if any file is unreadable |
| OCI bucket exposed publicly | Information Disclosure | IAM policy must restrict bucket to authenticated requests; verify bucket is NOT set to public-read in OCI console |

## Sources

### Primary (HIGH confidence)
- **Context7 / Codebase Verification:**
  - `engine/health_check.py` — existing tail-freshness check, `_last_expected_session()` logic verified
  - `engine/data/validation.py`, `engine/data/surface_history.py`, `engine/data/vol_index.py`, `engine/data/oi_history.py` — store schemas and date-column handling verified
  - `engine/tests/test_data_health.py` — test pattern verified (mocking, pytest)
  - `.github/workflows/daily-report.yml` — existing rsync + SSH key pattern verified
  - `scripts/migrate-data.ps1`, `scripts/update.sh` — script style and structure verified
  - `engine/config.py` — DEFAULT_VOL_INDICES, TICKER_VOL_INDEX verified

- **Official Documentation:**
  - [Oracle Cloud Object Storage Amazon S3 Compatibility API Support](https://docs.oracle.com/en-us/iaas/Content/Object/Tasks/s3compatibleapi_topic-Amazon_S3_Compatibility_API_Support.htm) — S3-compatible endpoint, boto3 authentication
  - [boto3 documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) — S3 client, authentication, upload/download patterns
  - [pandas-market-calendars documentation](https://github.com/rsheftel/pandas_market_calendars) — NYSE schedule API

### Secondary (MEDIUM confidence)
- **Academic / Practitioner Literature (grounded model-readiness depths):**
  - [ResearchGate: How does Sample Size Affect GARCH Models?](https://www.researchgate.net/publication/221556756_How_does_Sample_Size_Affect_GARCH_Models) — 500–2000 observations for GARCH(1,1)
  - [Ng & Lam (2006) cited in MCP Analytics GARCH guide](https://mcpanalytics.ai/articles/garch-practical-guide-for-data-driven-decisions) — 1000 observations minimum
  - [Statistics By Jim: Percentiles](https://statisticsbyjim.com/basics/percentiles/) — 30 observations for robust 5th/95th percentile estimates
  - [Baruch Volatility Workshop: Session 4 — Fitting SVI](https://mfe.baruch.cuny.edu/wp-content/uploads/2015/06/VW4.pdf) — SVI parameterization (5 parameters per expiry, requires reasonable strike coverage)

- **Practitioner Blogs / Articles:**
  - [Macrosynergy: Six ways to estimate realized volatility](https://macrosynergy.com/research/six-ways-to-estimate-realized-volatility/) — 251 trading days standard for daily RV20 window
  - [Medium: AWS Cloud automation using Python Boto3 via GitHub Actions](https://medium.com/@muralindiablog/aws-automation-using-python-boto3-via-github-actions-with-secure-cloud-access-f82af9fb697b) — GitHub Actions + boto3 pattern

## Metadata

**Confidence breakdown:**
- **Standard Stack (HIGH):** boto3 is production-standard, well-documented, used in thousands of projects. pandas-market-calendars is the standard in quant finance for calendar arithmetic.
- **Architecture (HIGH):** Extended health_check pattern mirrors existing tail-check logic; backup pattern follows boto3 best practices; restore script parallels existing `migrate-data.ps1` structure.
- **Full-History Scan Design (MEDIUM-HIGH):** Algorithm is straightforward (calendar walk + set membership); implementation risk is low. Pitfall #2 (CBOE holiday detection) requires empirical validation against actual CBOE gaps — this should happen during task execution.
- **Model-Ready Depths (MEDIUM):** Literature is solid (GARCH 500–1000, percentiles 30, RV20 251 days). But project's actual model family is not yet decided (v5.0 is data-foundation, model TBD). Recommend treating this research section as a starting point; planner/executor should confirm with project owner before locking numbers.
- **Backup Auth (MEDIUM):** boto3 + S3-compatible API is documented by Oracle and verified to work, but we haven't tested credentials flow in this specific GitHub Actions + OCI context. Should be validated in task execution.

**Research date:** 2026-07-21
**Valid until:** 2026-08-21 (1 month; pandas-market-calendars and boto3 are stable; model-depth assumptions might shift if project scope clarifies)

---

## Appendix: Full Data Store Schemas (Reference)

### gex_snapshots.parquet (Single file, multi-ticker)
```
Columns: date, ticker, spot, net_gex, zero_gamma_level, call_wall, put_wall,
         front_skew, put_25d_iv, call_25d_iv, iv30, strike_slope, term_slope,
         rv20, vrp, coverage_pct, fit_rmse, max_resid, cv_rmse,
         coherence_violations, coherence_calendar, coherence_butterfly
Index: none (date+ticker are data columns)
Idempotency: row is replaced by (date, ticker) on re-run
```

### surface_history/surface_{ticker}.parquet (Per-ticker file)
```
Columns: date, ticker, spot, dte, strike, moneyness, log_moneyness, iv_pct
One row per OTM quote point per day
Idempotency: today's date rows are deleted before re-run
```

### vol_index/{symbol}.parquet (Per-symbol file: VIX, VXN, RVX, VIX9D, VIX3M, VVIX)
```
Columns: symbol, date, open, high, low, close
Source: CBOE historical CSV (full history every fetch)
Idempotency: entire file replaced on each refresh (unconditional overwrite)
```

### oi_history/oi_{ticker}.parquet (Per-ticker file)
```
Columns: date, ticker, expiry, dte, call_oi, put_oi, oi, pct_of_total, put_call_ratio
One row per expiry per day
Idempotency: today's date rows are deleted before re-run
```

---

*Phase 23 Research — Data Completeness, Backup & Model-Readiness Audit*
*Researched: 2026-07-21*

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
**Phase siblings:**
- [[_planning/vol-diagnostics/phases/23-data-completeness-backup-model-readiness/23-CONTEXT|23-CONTEXT]]
- [[_planning/vol-diagnostics/phases/23-data-completeness-backup-model-readiness/23-DISCUSSION-LOG|23-DISCUSSION-LOG]]

<!-- LINKS:END -->
