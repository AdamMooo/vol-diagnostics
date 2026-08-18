# Data Pipeline Reliability Strategy

**Last updated:** 2026-08-18  
**Status:** Phase 1 implemented — data-driven, no email noise

---

## Problem

Before 2026-08-18:
- Daily email was being sent but rarely read (user prefers the interactive dashboard)
- Email failures (PNG export, SMTP) were silently swallowed — you'd discover data collection broke weeks later
- No monitoring between the data-collection run and when the user noticed staleness

## Solution

**Three-layer approach to ensure data collection never breaks silently:**

### Layer 1: Data Collection (Daily)
**Workflow:** `.github/workflows/daily-report.yml`  
**Schedule:** 20:35 UTC (4:35pm ET) weekdays  
**Does:** 
- Fetch chain data (CBOE)
- Compute all metrics (GEX, surface, vol)
- Save snapshots to parquet (`gex_snapshots.parquet`, `surface_history/`, `oi_history/`)
- Sync to Oracle (`out/`)
- Backup to OCI Object Storage

**Exit code:** 
- `0` = success (data current)
- `1` = failure (exit, don't retry)

**Email:** ❌ Removed. No noise.

### Layer 2: Freshness Monitor (Daily)
**Workflow:** `.github/workflows/data-freshness-check.yml`  
**Schedule:** 21:00 UTC (5:00pm ET) weekdays (25 min after data collection)  
**Does:**
- Pulls latest data from Oracle
- Checks: is today's data (or most recent trading day) current?
- If stale: creates a GitHub Issue automatically with the failure details

**Purpose:** Catch data-collection failures within **~1 hour**, not weeks.

**Alert:** Issues tagged `data-pipeline` — check GitHub Issues daily or set up an alert.

### Layer 3: Health Dashboard (Manual)
**Command:** `python -m engine.health_check --strict`  
**Purpose:** Verbose health report you can run anytime.  
**Output:** 
- Session count per store
- Gap analysis (missing trading days)
- Data freshness per ticker

---

## Guarantees

✅ **If data collection succeeds:** You'll see it in the dashboard within 5-10 min (time for container restart).

✅ **If data collection fails:** 
- GitHub Actions workflow exits with code 1
- Freshness monitor detects it within ~1 hour
- GitHub Issue is created automatically
- You catch it the same day, not weeks later

✅ **If Oracle goes down:** 
- Freshness monitor fails (can't rsync)
- GitHub Issue is created
- No silent data loss

✅ **If freshness monitor breaks:** 
- You'll see it in GitHub Actions logs
- Workflow history is auditable

---

## Monitoring Cadence

| Event | Detection | Action |
|-------|-----------|--------|
| Data collection succeeds | Dashboard updates in ~5 min | None |
| Data collection fails | Workflow exits 1 | Freshness monitor creates issue |
| Freshness monitor detects stale | GitHub Issue auto-created | You investigate & fix |
| Oracle down | Freshness monitor fails | GitHub Issue auto-created |

**Expected pattern:** 
- Normal days: No issues created
- Failure day: Issue created within 1 hour of failure

---

## Future (Phase 2)

**Alert emails** (coming later, phase B):
- Only send email when something significant happens (GEX breach, VRP spike, etc.)
- Not daily noise, only signal

**Workflow:** New `data-alerts.yml` will replace email with purpose-driven alerts.

---

## Manual Checks

**Did today's data collect?**
```bash
python -m engine.health_check --strict
# Look for: SPY/QQQ/IWM latest dates match today (or most recent trading day)
```

**Is the dashboard showing fresh data?**
- Go to https://40.233.113.63.nip.io
- Card should show today's data
- If not, restart the container: `ssh ... "docker compose restart dashboard"`

**Did the freshness monitor run?**
- GitHub Actions → Data Freshness Check → Recent runs
- Should run daily at 21:00 UTC
- Green = data is current
- Red = data is stale, check the issue

---

## Rollback / Manual Override

**To manually re-run data collection (e.g., if workflow hung):**
```bash
gh workflow run daily-report.yml --ref main -f force=true
```

**To force a complete re-sync from Oracle to local:**
```bash
bash scripts/sync-from-oracle.sh
```

---

## Constraints

- **Data is only as fresh as the CBOE chain data.** If CBOE is down, our collection fails.
- **Freshness monitor runs 25 min after data collection.** If both fail in the same 25-min window, we catch it at the next scheduled monitor run (next day).
- **No retroactive backfill.** If a day's data was missed, it stays missed. (Could add backfill logic later.)

---

**Owner:** Data pipeline reliability  
**Last incident:** 2026-08-17 (Oracle unresponsive, fixed with reboot)  
**Next review:** 2026-09-18
