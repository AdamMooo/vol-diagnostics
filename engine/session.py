"""
Shared NYSE trading-session helpers — one source of truth for "what session
are we in / should we have data for."

Replaces three drifting copies: run_daily used the raw wall-clock ET date,
app.py had a calendar-correct copy, and data_loader computed DTE off the LOCAL
date. They could disagree by a day on a delayed/after-midnight run or a box
whose local date != ET, silently mis-filing snapshots and skewing T_years.
"""
from __future__ import annotations

import datetime

import pandas_market_calendars as mcal
import pytz

ET = pytz.timezone("America/New_York")

# Freshness lens: today's session counts as "should already be collected" only
# after the post-close collection window (gives the 16:30 daily run time to fetch
# and write). Used by the dashboard freshness banner.
DATA_CUTOFF_HOUR, DATA_CUTOFF_MIN = 16, 35

# Collection lens: today's session is the one being collected once the regular
# session has opened. Used by run_daily so a normal 16:30 run files under today,
# while an after-midnight catch-up (now < open) files under the prior session.
MARKET_OPEN_HOUR, MARKET_OPEN_MIN = 9, 30


def is_trading_day(d: datetime.date | None = None) -> bool:
    d = d or datetime.datetime.now(ET).date()
    sched = mcal.get_calendar("NYSE").schedule(
        start_date=d.strftime("%Y-%m-%d"), end_date=d.strftime("%Y-%m-%d")
    )
    return not sched.empty


def latest_session(
    now_et: datetime.datetime | None = None,
    cutoff_hour: int = DATA_CUTOFF_HOUR,
    cutoff_min: int = DATA_CUTOFF_MIN,
) -> datetime.date:
    """Most recent NYSE session as of now_et, calendar-derived (never the raw
    wall-clock date).

    Today's session counts only once now_et is at/after the ET cutoff; before
    that — or on a non-trading day — the latest session is the prior trading day.
    Pass the market-open cutoff for the "session being collected" sense, or the
    post-close cutoff for the "session we should already have" sense.
    """
    now_et = now_et or datetime.datetime.now(ET)
    today = now_et.date()
    sched = mcal.get_calendar("NYSE").schedule(
        start_date=(today - datetime.timedelta(days=12)).strftime("%Y-%m-%d"),
        end_date=today.strftime("%Y-%m-%d"),
    )
    sessions = [d.date() for d in sched.index]
    if not sessions:
        return today
    cutoff = now_et.replace(hour=cutoff_hour, minute=cutoff_min, second=0, microsecond=0)
    if sessions[-1] == today and now_et < cutoff:
        return sessions[-2] if len(sessions) >= 2 else today
    return sessions[-1]
