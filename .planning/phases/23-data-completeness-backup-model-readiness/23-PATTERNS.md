# Phase 23: Data Completeness, Backup & Model-Readiness Audit - Pattern Map

**Mapped:** 2026-07-21
**Files analyzed:** 6 new/modified files
**Analogs found:** 6 / 6 (100% match)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `engine/health_check.py` | utility/service | CRUD | `engine/data/validation.py` | exact-role |
| `engine/tests/test_data_health.py` | test | CRUD | itself (existing test file) | exact |
| `.github/workflows/daily-report.yml` | config/workflow | CI/CD | itself (existing workflow) | exact |
| `scripts/restore-from-backup.sh` | utility/script | file-I/O | `scripts/migrate-data.ps1` | role-match |
| `.planning/notes/MODEL-READY-DATA-SPEC.md` | documentation/spec | N/A | `.planning/notes/ORACLE-CLOUD-SETUP.md` | role-match |
| `engine/backup_to_oci.py` | service/utility | file-I/O | `engine/data/vol_index.py` | role-match |

## Pattern Assignments

### `engine/health_check.py` (utility/service, CRUD)

**Analog:** `engine/data/validation.py`, `engine/data/surface_history.py`, `engine/data/oi_history.py`

**Imports pattern** (lines 1-21):
```python
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta

import pandas_market_calendars as mcal

from engine.data.surface_history import list_available_dates
from engine.data.validation import load_history

INDEX_TICKERS = ["SPY", "QQQ", "IWM"]
```

**Parquet read pattern** (from `engine/data/surface_history.py:list_available_dates`, lines 92-102):
```python
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

**NYSE calendar operations pattern** (lines 26-43):
```python
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
    # Today's session only counts if market is closed (after 4:35pm ET)
    from datetime import datetime
    import pytz
    now_et = datetime.now(pytz.timezone("America/New_York"))
    if sessions[-1] == today and now_et.hour < 17:
        return sessions[-2] if len(sessions) >= 2 else today
    return sessions[-1]
```

**Result dictionary pattern** (lines 46-100):
```python
def check_health(verbose: bool = True) -> dict:
    """Check all tickers for stale or missing data.

    Returns {"healthy": bool, "tickers": {ticker: {status, latest, expected, gap}}}
    """
    expected = _last_expected_session()
    results = {}
    all_healthy = True

    for ticker in INDEX_TICKERS:
        # Check surface snapshots (daily chain storage)
        available = list(list_available_dates(ticker))
        # Check GEX snapshot store
        hist = load_history(ticker, days=10)

        latest_surface = max(available) if available else None
        latest_snapshot = None
        if not hist.empty and "date" in hist.columns:
            latest_snapshot = hist["date"].max()
            if hasattr(latest_snapshot, "date"):
                latest_snapshot = latest_snapshot.date()

        latest = latest_surface or latest_snapshot
        if latest is None:
            status = "MISSING"
            gap = None
            all_healthy = False
        elif latest < expected:
            nyse = mcal.get_calendar("NYSE")
            sched = nyse.schedule(
                start_date=latest.strftime("%Y-%m-%d"),
                end_date=expected.strftime("%Y-%m-%d"),
            )
            gap = sum(1 for d in sched.index if d.date() > latest)
            status = f"STALE ({gap} session{'s' if gap != 1 else ''} behind)"
            all_healthy = False
        else:
            status = "OK"
            gap = 0

        results[ticker] = {
            "status": status,
            "latest": str(latest) if latest else "none",
            "expected": str(expected),
            "gap": gap,
        }

        if verbose:
            icon = "[OK]" if gap == 0 else "[MISSING]" if gap is None else f"[STALE +{gap}d]"
            print(f"  {ticker}: {icon} latest={latest or 'none'} expected={expected}")

    if verbose:
        print(f"\nOverall: {'HEALTHY' if all_healthy else 'UNHEALTHY'}")

    return {"healthy": all_healthy, "expected": str(expected), "tickers": results}
```

**CLI argument pattern** (lines 103-118):
```python
def main():
    parser = argparse.ArgumentParser(description="Gamma OMM health check")
    parser.add_argument("--strict", action="store_true",
                        help="Exit 1 if any ticker is stale/missing")
    parser.add_argument("--json", action="store_true",
                        help="Output JSON instead of human-readable")
    args = parser.parse_args()

    result = check_health(verbose=not args.json)

    if args.json:
        import json
        print(json.dumps(result, indent=2))

    if args.strict and not result["healthy"]:
        sys.exit(1)
```

**Extension point for full-history scanner:** Extend `check_health()` to add a `--full-history` flag and implement a new function `_full_history_scan(ticker, series_name, store_path)` that walks NYSE calendar from earliest to latest stored date and reports gaps. Pattern: reuse `list_available_dates()` calls, convert dates to a set, get NYSE sessions via `pandas_market_calendars`, then check membership.

---

### `engine/tests/test_data_health.py` (test, CRUD)

**Analog:** itself (existing test file) + `engine/tests/test_data_health.py`

**Existing test structure** (lines 1-137):
```python
"""Tests for the idempotency guard in run_daily and the health_check module."""
from __future__ import annotations

import datetime
import pathlib
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

# Health check tests already follow this pattern:
class TestHealthCheck:
    """Tests for the health_check module."""

    @patch("engine.health_check.list_available_dates", return_value=[])
    @patch("engine.health_check.load_history")
    def test_missing_data_reports_unhealthy(self, mock_hist, mock_dates):
        """No data at all → unhealthy."""
        from engine.health_check import check_health
        mock_hist.return_value = pd.DataFrame()
        result = check_health(verbose=False)
        assert result["healthy"] is False
        for ticker_info in result["tickers"].values():
            assert ticker_info["status"] == "MISSING"

    @patch("engine.health_check._last_expected_session")
    @patch("engine.health_check.list_available_dates")
    @patch("engine.health_check.load_history")
    def test_current_data_reports_healthy(self, mock_hist, mock_dates, mock_expected):
        """Data as of last expected session → healthy."""
        from engine.health_check import check_health
        today = datetime.date(2026, 6, 25)
        mock_expected.return_value = today
        mock_dates.return_value = [today]
        mock_hist.return_value = pd.DataFrame({"date": [today], "ticker": ["SPY"]})
        result = check_health(verbose=False)
        assert result["healthy"] is True

    @patch("engine.health_check._last_expected_session")
    @patch("engine.health_check.list_available_dates")
    @patch("engine.health_check.load_history")
    def test_stale_data_reports_gap(self, mock_hist, mock_dates, mock_expected):
        """Data 2 days old → STALE with gap count."""
        from engine.health_check import check_health
        expected = datetime.date(2026, 6, 25)
        actual = datetime.date(2026, 6, 23)
        mock_expected.return_value = expected
        mock_dates.return_value = [actual]
        mock_hist.return_value = pd.DataFrame({"date": [actual], "ticker": ["SPY"]})
        result = check_health(verbose=False)
        assert result["healthy"] is False
        # At least one ticker should show STALE
        assert any("STALE" in info["status"] for info in result["tickers"].values())
```

**Extension pattern:** Add new test classes for full-history gap scanning, e.g.:
```python
class TestFullHistoryGapScan:
    """Tests for full-history gap detection."""

    @patch("engine.health_check.pandas_market_calendars.get_calendar")
    def test_detects_known_gap_in_middle_of_history(self, mock_calendar):
        """A missing session in the middle should be flagged."""
        # Mock NYSE schedule, parquet read, then assert gap is detected
        pass

    def test_no_false_positives_on_complete_history(self, tmp_path):
        """Complete daily data from May to July should show no gaps."""
        pass
```

Reuse the existing mock pattern (patch data module imports, return known test data, assert on result dict).

---

### `.github/workflows/daily-report.yml` (config/workflow, CI/CD)

**Analog:** itself (existing workflow)

**Existing structure** (lines 1-89):
```yaml
name: Daily Vol Report

on:
  schedule:
    - cron: "35 20 * * 1-5"  # 20:35 UTC = 4:35pm ET, weekdays
  workflow_dispatch:
    inputs:
      force:
        description: "Force re-run even if today's data was already collected"
        type: boolean
        default: false

jobs:
  daily-report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install chromium (for kaleido PNG export) and rsync
        run: |
          sudo apt-get update -qq
          sudo apt-get install -y -qq rsync
          sudo apt-get install -y -qq chromium-browser || sudo apt-get install -y -qq chromium
      - name: Install Python dependencies
        run: pip install -r requirements.txt
      - name: Set up SSH key for Oracle sync
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.ORACLE_SSH_KEY }}" > ~/.ssh/oracle.key
          chmod 600 ~/.ssh/oracle.key
          cat > ~/.ssh/config <<EOF
          Host ${{ secrets.ORACLE_HOST }}
            StrictHostKeyChecking no
            UserKnownHostsFile /dev/null
          EOF
      - name: Pull current history down from Oracle
        run: |
          mkdir -p out
          rsync -avz --rsync-path="sudo rsync" -e "ssh -i ~/.ssh/oracle.key" \
            "ubuntu@${{ secrets.ORACLE_HOST }}:~/vol-diagnostics/out/" ./out/
      - name: Run daily report
        env:
          GEX_EMAIL_TO: ${{ secrets.GEX_EMAIL_TO }}
          SMTP_HOST: ${{ secrets.SMTP_HOST }}
          SMTP_PORT: ${{ secrets.SMTP_PORT }}
          SMTP_USER: ${{ secrets.SMTP_USER }}
          SMTP_PASS: ${{ secrets.SMTP_PASS }}
          SMTP_FROM: ${{ secrets.SMTP_FROM }}
        run: |
          if [ "${{ github.event.inputs.force }}" = "true" ]; then
            python -m engine.run_daily --send --force
          else
            python -m engine.run_daily --send
          fi
      - name: Push updated history back up to Oracle
        if: always()
        run: |
          rsync -avz -e "ssh -i ~/.ssh/oracle.key" \
            ./out/ "ubuntu@${{ secrets.ORACLE_HOST }}:~/vol-diagnostics/out/"
      - name: Health check
        run: python -m engine.health_check --strict
```

**Extension point (new backup step):** Insert a new step after "Run daily report" and before "Push updated history back up to Oracle". Pattern to follow:
```yaml
      - name: Backup out/ to Oracle Object Storage
        if: always()  # run even if earlier steps failed
        env:
          OCI_ACCESS_KEY_ID: ${{ secrets.OCI_ACCESS_KEY_ID }}
          OCI_CUSTOMER_SECRET_KEY: ${{ secrets.OCI_CUSTOMER_SECRET_KEY }}
          OCI_NAMESPACE: ${{ secrets.OCI_NAMESPACE }}
        run: |
          python -m engine.backup_to_oci \
            --bucket vol-diagnostics-backup \
            --region ca-toronto-1 \
            --source ./out
```

**Secrets pattern:** Reuse existing pattern (secrets masked, env-var injection, referenced in step via `${{ secrets.NAME }}`). New secrets: `OCI_ACCESS_KEY_ID`, `OCI_CUSTOMER_SECRET_KEY`, `OCI_NAMESPACE`.

---

### `scripts/restore-from-backup.sh` (utility/script, file-I/O)

**Analog:** `scripts/migrate-data.ps1` (PowerShell equivalent), `scripts/update.sh`, `scripts/deploy.sh`

**migrate-data.ps1 structure** (lines 1-68):
```powershell
# Vol Diagnostics — Migrate parquet data to Oracle Cloud
# Run from your local Windows machine after the remote instance is deployed.
#
# Usage:
#   .\scripts\migrate-data.ps1 -IP "129.xx.xx.xx" -KeyFile "C:\path\to\ssh-key.key"
#
# What it does:
#   1. Copies all out/ parquet files to the server via scp
#   2. Restarts containers to pick up the data
#   3. Runs health-check to verify

param(
    [Parameter(Mandatory=$true)]
    [string]$IP,

    [Parameter(Mandatory=$true)]
    [string]$KeyFile,

    [string]$User = "ubuntu",
    [string]$RemoteDir = "~/vol-diagnostics/out"
)

$ErrorActionPreference = "Stop"
$LocalOut = Join-Path $PSScriptRoot "..\out"

if (-not (Test-Path $LocalOut)) {
    Write-Error "Local out/ directory not found at $LocalOut"
    exit 1
}

if (-not (Test-Path $KeyFile)) {
    Write-Error "SSH key file not found: $KeyFile"
    exit 1
}

Write-Host "=== Vol Diagnostics — Data Migration ===" -ForegroundColor Cyan
Write-Host "Source: $LocalOut"
Write-Host "Target: ${User}@${IP}:${RemoteDir}"
Write-Host ""

# Count files
$files = Get-ChildItem -Recurse -File $LocalOut
Write-Host "Files to transfer: $($files.Count)"
$totalSize = ($files | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Host "Total size: $([math]::Round($totalSize, 1)) MB"
Write-Host ""

# Create remote directories
Write-Host "[1/3] Creating remote directories..."
ssh -i $KeyFile "${User}@${IP}" "mkdir -p ~/vol-diagnostics/out/surface_history ~/vol-diagnostics/out/vol_index ~/vol-diagnostics/out/gex"

# SCP the data
Write-Host "[2/3] Transferring parquet files..."
scp -i $KeyFile -r "${LocalOut}\*" "${User}@${IP}:${RemoteDir}/"

# Restart and verify
Write-Host "[3/3] Restarting containers and verifying..."
ssh -i $KeyFile "${User}@${IP}" "cd ~/vol-diagnostics && docker compose restart && sleep 5 && docker compose exec dashboard python -m engine.health_check"

Write-Host ""
Write-Host "=== Migration Complete ===" -ForegroundColor Green
```

**Pattern to follow for bash restore script:**
- Shebang: `#!/usr/bin/env bash` (POSIX, runs on Linux and macOS; preferred for CI/CD)
- Error handling: `set -euo pipefail`
- Parameter parsing: environment variables (`--dry-run` flag, `OCI_*` env vars)
- Staged output: print what's happening, use colors for emphasis (print `[restore]` prefix like other scripts)
- Main logic: use boto3 (Python one-liner or separate module call, like vol_index.py's fetch pattern)
- Verification: try `pd.read_parquet()` on a test file after download to verify integrity

**Dry-run capability:** Include a `--dry-run` flag that lists objects without downloading, mirroring the safety pattern in existing scripts.

---

### `.planning/notes/MODEL-READY-DATA-SPEC.md` (documentation/spec)

**Analog:** `.planning/notes/ORACLE-CLOUD-SETUP.md`

**ORACLE-CLOUD-SETUP.md structure** (lines 1-507):
```markdown
# Oracle Cloud Free Tier — Vol Diagnostics Setup Guide

Created: 2026-06-24
Updated: 2026-06-25

## What's Free (Always Free Tier — never expires)

| Resource | Free Allowance |
|----------|----------------|
| ARM Compute (VM.Standard.A1.Flex) | 2 OCPUs + 12 GB RAM |
| Boot volume storage | 200 GB total |
| Public IP | 1 reserved public IP |
| Bandwidth | 10 Mbps |
| Object Storage | 20 GB |

---

## Step 1: [Detailed how-to with tables and code blocks]
...
```

**Pattern to follow for MODEL-READY-DATA-SPEC.md:**
- Header: title, date, "Last updated" line
- Section structure: `## Data Series Readiness Targets`
- Primary table: series name → minimum sessions → required columns → model use case
- Sub-sections: one per data series (gex_snapshots, surface_history, vol_index, oi_history)
- For each, include:
  - Column schema (which columns are required; which are optional)
  - Minimum session depth (grounded in literature, e.g., "GARCH(1,1) requires 500–1000 observations")
  - Cold-start considerations (surface_history/oi_history are ~May 2026; vol_index is historical to 1990)
  - Validation rules
- Closing section: how to audit current depth (run `engine.health_check --audit-depth` or similar)
- Footer: related links (ROADMAP, STATE, project hub) following the existing link pattern

**Key difference from ORACLE-CLOUD-SETUP:** This is a *specification*, not a *how-to*, so structure is more like a data-dictionary than a step-by-step guide. Use tables heavily; include rationale citations (e.g., "GARCH: Ng & Lam (2006)").

---

### `engine/backup_to_oci.py` (service/utility, file-I/O)

**Analog:** `engine/data/vol_index.py` (fetch + save pattern), `engine/data/validation.py` (parquet save pattern)

**Data module pattern** (from `engine/data/vol_index.py:_fetch_cboe_vol_index` lines 27-71):
```python
def _fetch_cboe_vol_index(symbol: str) -> pd.DataFrame | None:
    """Fetch CBOE vol-index daily history CSV. Returns None on 403 (discontinued) or network error."""
    try:
        url = _CBOE_VOL_URL.format(SYM=symbol)
        resp = requests.get(url, headers=_HEADERS, timeout=30)
        if resp.status_code == 403:
            print(f"[vol_index] {symbol}: 403 (discontinued), skipping")
            return None
        resp.raise_for_status()

        # CBOE returns full history; no pagination.
        df = pd.read_csv(io.StringIO(resp.text))
        df["DATE"] = pd.to_datetime(df["DATE"]).dt.date

        # Schema normalization...
        if "OPEN" not in df.columns and symbol in df.columns:
            val = pd.to_numeric(df[symbol], errors="coerce")
            df["OPEN"] = val
            # ...
        
        # Validation and cleanup
        clean_df = df.dropna(subset=["OPEN", "HIGH", "LOW", "CLOSE"])
        dropped = len(df) - len(clean_df)
        if dropped > 0:
            print(f"[vol_index] {symbol}: dropped {dropped} malformed rows")

        if clean_df.empty:
            print(f"[vol_index] {symbol}: CSV returned no valid data")
            return None

        return clean_df

    except Exception as exc:
        print(f"[vol_index] {symbol}: fetch/parse failed: {exc}")
        return None
```

**Validation save pattern** (from `engine/data/validation.py:save_snapshot` lines 42-94):
```python
def save_snapshot(summary: dict, ticker: str, skew_df: pd.DataFrame | None = None,
                  date: datetime.date | None = None) -> None:
    """Append today's summary dict to the parquet store (idempotent on date+ticker)."""
    # ... prepare row dict ...
    
    if STORE.exists():
        hist = pd.read_parquet(STORE)
        for col in _FLOAT_COLS:
            if col in hist.columns:
                hist[col] = hist[col].astype("float64")
        mask = (hist["date"] == row["date"]) & (hist["ticker"] == ticker)
        hist = hist[~mask]
        hist = pd.concat([hist, pd.DataFrame([row])], ignore_index=True)
    else:
        STORE.parent.mkdir(exist_ok=True)
        hist = pd.DataFrame([row])

    atomic_to_parquet(hist, STORE)
    print(f"[gex] Snapshot saved ({len(hist)} rows total): {STORE}")
```

**Pattern to follow for backup_to_oci.py:**
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
        OCI_ACCESS_KEY_ID: Customer Access Key
        OCI_CUSTOMER_SECRET_KEY: Customer Secret Key
        OCI_NAMESPACE: Object Storage namespace
    """
    access_key = os.environ['OCI_ACCESS_KEY_ID']
    secret_key = os.environ['OCI_CUSTOMER_SECRET_KEY']
    namespace = os.environ.get('OCI_NAMESPACE')
    
    if not namespace:
        raise ValueError("OCI_NAMESPACE env var not set")
    
    endpoint_url = f"https://{namespace}.compat.objectstorage.{region}.oraclecloud.com"
    
    s3_client = boto3.client(
        's3',
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )
    
    # Recursively upload all files
    for file_path in source_dir.rglob('*'):
        if file_path.is_file():
            key = str(file_path.relative_to(source_dir.parent))
            print(f"[backup] uploading {key} ...")
            try:
                s3_client.upload_file(str(file_path), bucket, key)
            except Exception as exc:
                print(f"[backup] FAILED to upload {key}: {exc}")
                raise
    
    print(f"[backup] complete. {bucket} updated.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--bucket', required=True)
    parser.add_argument('--region', required=True)
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    
    backup_to_oracle(args.bucket, args.region, args.source)
```

Key patterns:
- Module docstring + function docstring (non-obvious why needed)
- Env-var credential reading (no hardcoding)
- Exception handling with informative print() calls (match `[vol_index]` prefix style from data modules)
- CLI entry point with argparse (match health_check.py pattern)

---

## Shared Patterns

### Parquet Date Handling (All Data Modules)

**Source:** `engine/data/surface_history.py:list_available_dates`, `engine/data/validation.py:load_history`, `engine/data/oi_history.py:list_oi_dates`

**Apply to:** All parquet-reading code in `engine/health_check.py` extensions
```python
# Read only the date column for efficiency
df = pd.read_parquet(store_path, columns=["date"])
# Convert to datetime, extract date, unique, vectorized (not a loop)
dates = pd.to_datetime(df["date"]).dt.date.unique()
# Return as a set for O(1) membership testing
return set(dates)
```

### Ticker Iteration Pattern (All Ticker-Based Checks)

**Source:** `engine/health_check.py:check_health` (lines 55-95)

**Apply to:** Full-history gap scanner
```python
INDEX_TICKERS = ["SPY", "QQQ", "IWM"]
results = {}
all_healthy = True

for ticker in INDEX_TICKERS:
    # Check each series independently
    # results[ticker] = {status, details}
    if <problem detected>:
        all_healthy = False

return {"healthy": all_healthy, "tickers": results}
```

### Error Logging Pattern (All Data Access)

**Source:** `engine/data/validation.py:load_history` (lines 122-132), `engine/data/vol_index.py:_fetch_cboe_vol_index` (lines 66-71)

**Apply to:** All new parquet read/write and backup operations
```python
try:
    # Attempt operation
    result = load_parquet_or_fetch_or_upload()
except Exception as exc:
    print(f"[module_name] operation_name failed: {exc}")
    return empty_or_none_sentinel  # Fail soft, don't raise
```

### CLI Argument Pattern (All Executable Modules)

**Source:** `engine/health_check.py:main` (lines 103-118)

**Apply to:** `backup_to_oci.py` main block
```python
parser = argparse.ArgumentParser(description="<Module purpose>")
parser.add_argument("--flag", action="store_true", help="<Description>")
parser.add_argument("--param", type=str, required=True, help="<Description>")
args = parser.parse_args()

# Use args.flag and args.param
# Exit with sys.exit(1) on error
```

### GitHub Actions Secrets Pattern

**Source:** `.github/workflows/daily-report.yml` (lines 41-55)

**Apply to:** New backup step authentication
```yaml
- name: Set up Oracle Object Storage credentials
  run: |
    # Environment variables are already set from secrets via env: block above
    # No secrets should appear in commands or files
    python -m engine.backup_to_oci --bucket ... --region ...
  env:
    OCI_ACCESS_KEY_ID: ${{ secrets.OCI_ACCESS_KEY_ID }}
    OCI_CUSTOMER_SECRET_KEY: ${{ secrets.OCI_CUSTOMER_SECRET_KEY }}
    OCI_NAMESPACE: ${{ secrets.OCI_NAMESPACE }}
```

### Script Template Pattern (Shell Scripts)

**Source:** `scripts/migrate-data.ps1` (PowerShell), implied pattern for bash

**Apply to:** `scripts/restore-from-backup.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail

# Usage documentation at top
# Staged output with color/emoji (use [restore] prefix)
# Parameter validation (env vars, file existence)
# Main logic with progress indication
# Verification step

echo "[restore] complete."
```

---

## No Analog Found

Files with direct analogs already identified above. All 6 files have working analogs in the codebase.

---

## Metadata

**Analog search scope:** `engine/data/`, `engine/`, `.github/workflows/`, `scripts/`, `.planning/notes/`, `engine/tests/`

**Files scanned:** 12 analog files + 3 existing phase files

**Pattern extraction date:** 2026-07-21

**Confidence:** HIGH (all files reuse existing project patterns; no novel architectures required)

---

## Summary of Patterns

1. **Health-check extension:** Reuse existing tail-check structure; add `--full-history` flag and `_full_history_scan()` function following `list_available_dates()` pattern.

2. **Test extension:** Add new test classes (`TestFullHistoryGapScan`, `TestModelReadinessAudit`) using existing mock pattern (patch data module imports, return test data, assert on result dict).

3. **Workflow extension:** Reuse existing job step pattern; add new backup step after `run_daily`, before `rsync push`, using env-var secrets (new: `OCI_ACCESS_KEY_ID`, `OCI_CUSTOMER_SECRET_KEY`, `OCI_NAMESPACE`).

4. **Restore script:** Follow `migrate-data.ps1` structure (parameters, error handling, staged output, progress), implement in bash for CI/CD portability; use boto3 S3-compatible API (same as backup_to_oci.py).

5. **Model-readiness spec:** Follow ORACLE-CLOUD-SETUP structure (sections, tables, citations) but focus on data dictionary / requirements spec (not how-to).

6. **Backup helper module:** Reuse data module pattern (fetch/save) and CLI pattern (argparse); use boto3 for S3-compatible Object Storage access; read credentials from env vars.

All patterns are grounded in existing production code within the vol-diagnostics codebase. No external templates or stylistic departures required.

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
**Phase siblings:**
- [[_planning/vol-diagnostics/phases/23-data-completeness-backup-model-readiness/23-CONTEXT|23-CONTEXT]]
- [[_planning/vol-diagnostics/phases/23-data-completeness-backup-model-readiness/23-DISCUSSION-LOG|23-DISCUSSION-LOG]]
- [[_planning/vol-diagnostics/phases/23-data-completeness-backup-model-readiness/23-RESEARCH|23-RESEARCH]]

<!-- LINKS:END -->
