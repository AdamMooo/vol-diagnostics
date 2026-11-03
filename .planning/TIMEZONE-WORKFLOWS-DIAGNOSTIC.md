# Timezone & Workflow Issues — Diagnostic + Terminal SSH Guide

**Date:** 2026-09-11  
**Status:** Active issue in `health_check.py` + workflow coordination mismatch  
**Impact:** Data freshness check may report false STALE or false OK depending on whether collection has completed between 4:35pm ET and 5:00pm ET.

---

## Issue 1: Timezone Cutoff Mismatch in Health Check

### The Problem

**File:** `engine/health_check.py:65`

```python
if sessions[-1] == today and now_et.hour < 17:
    return sessions[-2] if len(sessions) >= 2 else today
```

This checks `hour < 17` (before 5:00pm ET), but the actual data collection cutoff is **4:35pm ET** (16:35):

**File:** `engine/session.py:22`
```python
DATA_CUTOFF_HOUR, DATA_CUTOFF_MIN = 16, 35
```

### Failure Window

Between **4:35pm and 4:59pm ET**, the following race happens:

| Time | What's true | Health check says | Freshness check says | Status |
|------|-----------|------------------|-------------------|--------|
| 4:36pm ET | First collection has fired, data may not be written yet | "Today's session expected" (hour=16 < 17) | "Today's session expected" (correct) | ✓ SYNC |
| 4:50pm ET | Data may still be processing | "Today's session expected" (hour=16 < 17) | "Today's session expected" | ✓ SYNC |
| 5:00pm ET | Data written, collection done | "Yesterday is expected" (hour=17 NOT < 17) | "Today's session expected" | ✗ **MISMATCH** |

**The bug:** After 5:00pm ET, even if today's data was successfully collected at 4:35pm and is fully written, `health_check.py` will report it as STALE (comparing today's data against yesterday's expectation).

### Root Cause

`health_check.py` has its own `_last_expected_session()` function that duplicates the logic from `session.py`, but uses a different cutoff time. This violates the DRY principle stated in the `session.py` docstring:

> "Replaces three drifting copies: run_daily used the raw wall-clock ET date, app.py had a calendar-correct copy, and data_loader computed DTE off the LOCAL date."

The health check should use `latest_session()` from `session.py`, not redefine it.

---

## Issue 2: GitHub Workflow Timing

The three scheduled collection attempts are correctly spaced:

**File:** `.github/workflows/daily-report.yml:15-25`

```yaml
on:
  schedule:
    - cron: "35 20 * * 1-5"  # 20:35 UTC = 4:35pm ET (PRIMARY)
    - cron: "30 22 * * 1-5"  # 22:30 UTC = 6:30pm ET (CATCH-UP if first failed)
    - cron: "30 0 * * 2-6"   # 00:30 UTC = 8:30pm ET previous day (LAST CHANCE)
```

**File:** `.github/workflows/data-freshness-check.yml:10-15`

```yaml
on:
  schedule:
    - cron: "0 1 * * 2-6"    # 01:00 UTC = 9:00pm ET (AFTER all three attempts)
```

✓ Workflows are correctly timed — the freshness check runs AFTER the last collection attempt.

---

## Issue 3: Data Freshness Check Logic

**File:** `.github/workflows/data-freshness-check.yml:62-110`

The inline Python checks are correct and use ET timezone properly:

```python
from pytz import timezone
et = timezone('US/Eastern')
today_et = datetime.now(et).date()
```

✓ Freshness check is correctly gated to ET timezone.

---

## Recommendation & Fix

### Immediate fix: Align health_check.py to use session.py cutoff

**File:** `engine/health_check.py:46-67`

Replace the local `_last_expected_session()` function with an import from `session.py`:

```python
# BEFORE (lines 46-67):
def _last_expected_session(today: date | None = None) -> date:
    """Most recent NYSE trading day that should have a snapshot by now."""
    from datetime import datetime
    import pytz
    now_et = datetime.now(pytz.timezone("America/New_York"))
    today = today or now_et.date()
    # ... custom logic with hour < 17 cutoff ...

# AFTER:
def _last_expected_session(today: date | None = None) -> date:
    """Most recent NYSE trading day that should have a snapshot by now."""
    from datetime import datetime
    return latest_session(
        datetime.datetime.now(ET),
        cutoff_hour=DATA_CUTOFF_HOUR,
        cutoff_min=DATA_CUTOFF_MIN,
    )
```

Then at the top of `health_check.py`, add the imports:

```python
from engine.session import ET, latest_session, DATA_CUTOFF_HOUR, DATA_CUTOFF_MIN
```

This ensures all three code paths (session.py, run_daily.py, health_check.py, freshness_check.yml, app.py) use the SAME cutoff time and ET timezone.

---

## How to Verify the Fix

After applying the change:

```bash
# Test at various times to see the cutoff behavior
python3 << 'EOF'
import datetime
from pytz import timezone
from engine.session import latest_session, DATA_CUTOFF_HOUR, DATA_CUTOFF_MIN

et = timezone('US/Eastern')

# Test just before cutoff (4:34:59pm ET)
before_cutoff = datetime.datetime(2026, 9, 11, 16, 34, 59, tzinfo=et)
print(f"4:34pm ET -> {latest_session(before_cutoff, DATA_CUTOFF_HOUR, DATA_CUTOFF_MIN)}")

# Test right at cutoff (4:35:00pm ET)
at_cutoff = datetime.datetime(2026, 9, 11, 16, 35, 0, tzinfo=et)
print(f"4:35pm ET -> {latest_session(at_cutoff, DATA_CUTOFF_HOUR, DATA_CUTOFF_MIN)}")

# Test after cutoff (5:00:00pm ET)
after_cutoff = datetime.datetime(2026, 9, 11, 17, 0, 0, tzinfo=et)
print(f"5:00pm ET -> {latest_session(after_cutoff, DATA_CUTOFF_HOUR, DATA_CUTOFF_MIN)}")
EOF
```

Expected output:
```
4:34pm ET -> 2026-09-10  (yesterday)
4:35pm ET -> 2026-09-11  (today)
5:00pm ET -> 2026-09-11  (today) ← this ensures consistency after data write
```

---

## Terminal & SSH Documentation

See **[SSH_TERMINAL_GUIDE.md](SSH_TERMINAL_GUIDE.md)** for comprehensive terminal commands, SSH workflows, and the deploy/verify cycle.
