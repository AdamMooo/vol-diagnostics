"""Session-date logic — collection lens vs freshness lens, incl. catch-up.

Locks the behavior that previously drifted across three copies: a normal
scheduled run files under today; a delayed/after-midnight run files under the
session it actually collected; the freshness banner only counts today after
the post-close window.
"""
import datetime

import pytz

from engine.session import (
    latest_session, MARKET_OPEN_HOUR, MARKET_OPEN_MIN, DATA_CUTOFF_HOUR, DATA_CUTOFF_MIN,
)

ET = pytz.timezone("America/New_York")

# 2026-06-26 Fri, -29 Mon, -30 Tue are all NYSE trading days; -27/-28 weekend.
def _et(y, mo, d, h, mi):
    return ET.localize(datetime.datetime(y, mo, d, h, mi))


class TestCollectionLens:
    """Market-open cutoff — the session run_daily is collecting."""

    def test_scheduled_run_files_under_today(self):
        assert latest_session(_et(2026, 6, 30, 16, 30), MARKET_OPEN_HOUR, MARKET_OPEN_MIN) == datetime.date(2026, 6, 30)

    def test_after_midnight_catchup_files_under_prior_session(self):
        assert latest_session(_et(2026, 6, 30, 0, 30), MARKET_OPEN_HOUR, MARKET_OPEN_MIN) == datetime.date(2026, 6, 29)

    def test_weekend_falls_back_to_friday(self):
        assert latest_session(_et(2026, 6, 27, 12, 0), MARKET_OPEN_HOUR, MARKET_OPEN_MIN) == datetime.date(2026, 6, 26)


class TestFreshnessLens:
    """Post-close cutoff — the session we should already have stored."""

    def test_before_cutoff_today_not_yet_expected(self):
        assert latest_session(_et(2026, 6, 30, 16, 30), DATA_CUTOFF_HOUR, DATA_CUTOFF_MIN) == datetime.date(2026, 6, 29)

    def test_after_cutoff_today_expected(self):
        assert latest_session(_et(2026, 6, 30, 16, 40), DATA_CUTOFF_HOUR, DATA_CUTOFF_MIN) == datetime.date(2026, 6, 30)
