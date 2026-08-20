import datetime
from pathlib import Path

import pandas as pd
import pytest

from engine import watchdog


def test_sessions_behind_counts_only_trading_days():
    # 2026-08-18 -> 2026-08-20 spans 08-19 and 08-20, both weekdays.
    assert watchdog.sessions_behind(datetime.date(2026, 8, 18), datetime.date(2026, 8, 20)) == 2


def test_sessions_behind_skips_the_weekend():
    # Fri 2026-08-21 -> Mon 2026-08-24 is one session, not three calendar days.
    assert watchdog.sessions_behind(datetime.date(2026, 8, 21), datetime.date(2026, 8, 24)) == 1


def test_sessions_behind_is_zero_when_current_or_ahead():
    d = datetime.date(2026, 8, 20)
    assert watchdog.sessions_behind(d, d) == 0
    assert watchdog.sessions_behind(d, datetime.date(2026, 8, 19)) == 0


def test_stored_latest_date_missing_file_is_none(tmp_path):
    assert watchdog.stored_latest_date(tmp_path / "nope.parquet") is None


def test_stored_latest_date_reads_max(tmp_path):
    p = tmp_path / "gex_snapshots.parquet"
    pd.DataFrame({"date": [datetime.date(2026, 8, 18), datetime.date(2026, 8, 20)]}).to_parquet(p)
    assert watchdog.stored_latest_date(p) == datetime.date(2026, 8, 20)


def test_stale_data_notifies_and_exits_nonzero(tmp_path, monkeypatch):
    p = tmp_path / "gex_snapshots.parquet"
    pd.DataFrame({"date": [datetime.date(2026, 8, 10)]}).to_parquet(p)

    sent = {}
    monkeypatch.setattr(watchdog, "notify", lambda s, l: sent.update(subject=s, lines=l))
    monkeypatch.setattr("sys.argv", ["watchdog", "--dest", str(tmp_path), "--skip-restore"])

    with pytest.raises(SystemExit) as exc:
        watchdog.main()
    assert exc.value.code == 1
    assert "trading session" in sent["subject"]


def test_healthy_data_sends_nothing(tmp_path, monkeypatch):
    p = tmp_path / "gex_snapshots.parquet"
    future = datetime.date.today() + datetime.timedelta(days=30)
    pd.DataFrame({"date": [future]}).to_parquet(p)

    sent = []
    monkeypatch.setattr(watchdog, "notify", lambda s, l: sent.append(s))
    monkeypatch.setattr("sys.argv", ["watchdog", "--dest", str(tmp_path), "--skip-restore"])

    watchdog.main()
    assert sent == []
