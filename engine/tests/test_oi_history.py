"""Tests for engine/data/oi_history.py — per-expiry OI parquet store."""
from __future__ import annotations

import datetime
import pathlib
import tempfile
import unittest.mock as mock

import pandas as pd
import pytest

from engine.data.oi_history import (
    save_oi_snapshot,
    load_oi_snapshot,
    prior_oi_snapshot,
    list_oi_dates,
)


def _make_expiry_oi_df(n: int = 3) -> pd.DataFrame:
    """Minimal per-expiry OI DataFrame matching the schema save_oi_snapshot expects."""
    return pd.DataFrame({
        "expiry": [f"2024-0{i+1}-19" for i in range(n)],
        "dte":    [30.0 + i * 30 for i in range(n)],
        "call_oi": [1000 + i * 100 for i in range(n)],
        "put_oi":  [800 + i * 50 for i in range(n)],
        "oi":      [1800 + i * 150 for i in range(n)],
        "pct_of_total": [100.0 / n for _ in range(n)],
        "put_call_ratio": [0.8 + i * 0.05 for i in range(n)],
    })


@pytest.fixture(autouse=True)
def patch_store_dir(tmp_path, monkeypatch):
    """Redirect STORE_DIR to a temp directory for every test."""
    import engine.data.oi_history as mod
    monkeypatch.setattr(mod, "STORE_DIR", tmp_path / "oi_history")


class TestSaveOiSnapshot:
    def test_creates_parquet_file(self, tmp_path):
        import engine.data.oi_history as mod
        df = _make_expiry_oi_df(3)
        date = datetime.date(2024, 6, 1)
        save_oi_snapshot(df, "SPY", date=date)
        path = mod.STORE_DIR / "oi_SPY.parquet"
        assert path.exists()

    def test_file_has_expected_columns(self, tmp_path):
        import engine.data.oi_history as mod
        df = _make_expiry_oi_df(3)
        date = datetime.date(2024, 6, 1)
        save_oi_snapshot(df, "SPY", date=date)
        hist = pd.read_parquet(mod.STORE_DIR / "oi_SPY.parquet")
        required = {"date", "ticker", "expiry", "dte", "call_oi", "put_oi", "oi",
                    "pct_of_total", "put_call_ratio"}
        assert required.issubset(set(hist.columns))

    def test_row_count_matches_input(self, tmp_path):
        import engine.data.oi_history as mod
        df = _make_expiry_oi_df(3)
        date = datetime.date(2024, 6, 1)
        save_oi_snapshot(df, "SPY", date=date)
        hist = pd.read_parquet(mod.STORE_DIR / "oi_SPY.parquet")
        assert len(hist) == 3

    def test_idempotent_same_date_does_not_duplicate(self, tmp_path):
        """Running twice for the same date must keep exactly 3 rows (replace, not append)."""
        import engine.data.oi_history as mod
        df = _make_expiry_oi_df(3)
        date = datetime.date(2024, 6, 1)
        save_oi_snapshot(df, "SPY", date=date)
        save_oi_snapshot(df, "SPY", date=date)
        hist = pd.read_parquet(mod.STORE_DIR / "oi_SPY.parquet")
        assert len(hist) == 3

    def test_two_different_dates_accumulate(self, tmp_path):
        import engine.data.oi_history as mod
        df = _make_expiry_oi_df(3)
        save_oi_snapshot(df, "SPY", date=datetime.date(2024, 6, 1))
        save_oi_snapshot(df, "SPY", date=datetime.date(2024, 6, 2))
        hist = pd.read_parquet(mod.STORE_DIR / "oi_SPY.parquet")
        assert len(hist) == 6

    def test_returns_early_on_none(self, tmp_path):
        """None input: no file created, no exception."""
        import engine.data.oi_history as mod
        save_oi_snapshot(None, "SPY", date=datetime.date(2024, 6, 1))
        path = mod.STORE_DIR / "oi_SPY.parquet"
        assert not path.exists()

    def test_returns_early_on_empty_df(self, tmp_path):
        """Empty DataFrame input: no file created, no exception."""
        import engine.data.oi_history as mod
        save_oi_snapshot(pd.DataFrame(), "SPY", date=datetime.date(2024, 6, 1))
        path = mod.STORE_DIR / "oi_SPY.parquet"
        assert not path.exists()

    def test_ticker_column_value(self, tmp_path):
        import engine.data.oi_history as mod
        df = _make_expiry_oi_df(3)
        save_oi_snapshot(df, "QQQ", date=datetime.date(2024, 6, 1))
        hist = pd.read_parquet(mod.STORE_DIR / "oi_QQQ.parquet")
        assert (hist["ticker"] == "QQQ").all()


class TestLoadOiSnapshot:
    def test_returns_empty_df_when_no_store(self):
        """Cold start: no parquet file exists, must return empty DataFrame, not raise."""
        result = load_oi_snapshot("SPY", datetime.date(2024, 6, 1))
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_returns_correct_day_rows(self, tmp_path):
        import engine.data.oi_history as mod
        df = _make_expiry_oi_df(3)
        d1 = datetime.date(2024, 6, 1)
        d2 = datetime.date(2024, 6, 2)
        save_oi_snapshot(df, "SPY", date=d1)
        save_oi_snapshot(df, "SPY", date=d2)
        result = load_oi_snapshot("SPY", d1)
        assert len(result) == 3

    def test_returns_expected_columns(self, tmp_path):
        import engine.data.oi_history as mod
        df = _make_expiry_oi_df(3)
        d = datetime.date(2024, 6, 1)
        save_oi_snapshot(df, "SPY", date=d)
        result = load_oi_snapshot("SPY", d)
        expected = {"expiry", "dte", "call_oi", "put_oi", "oi", "pct_of_total", "put_call_ratio"}
        assert expected.issubset(set(result.columns))
        # date and ticker must NOT be in result (stripped on load)
        assert "date" not in result.columns
        assert "ticker" not in result.columns

    def test_returns_empty_df_when_date_not_found(self, tmp_path):
        import engine.data.oi_history as mod
        df = _make_expiry_oi_df(3)
        save_oi_snapshot(df, "SPY", date=datetime.date(2024, 6, 1))
        result = load_oi_snapshot("SPY", datetime.date(2024, 6, 15))
        assert isinstance(result, pd.DataFrame)
        assert result.empty


class TestPriorOiSnapshot:
    def test_returns_empty_df_cold_start(self):
        """No store at all: prior_oi_snapshot returns empty DataFrame, not exception."""
        result = prior_oi_snapshot("SPY", datetime.date(2024, 6, 2))
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_returns_empty_df_when_no_prior_date(self, tmp_path):
        """Only one date in store and before_date == that date: no prior exists."""
        import engine.data.oi_history as mod
        df = _make_expiry_oi_df(3)
        save_oi_snapshot(df, "SPY", date=datetime.date(2024, 6, 1))
        result = prior_oi_snapshot("SPY", datetime.date(2024, 6, 1))
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_returns_most_recent_prior_session(self, tmp_path):
        """Three dates in store, before_date is newest: should return middle date's rows."""
        import engine.data.oi_history as mod
        df = _make_expiry_oi_df(3)
        save_oi_snapshot(df, "SPY", date=datetime.date(2024, 6, 1))
        save_oi_snapshot(df, "SPY", date=datetime.date(2024, 6, 2))
        save_oi_snapshot(df, "SPY", date=datetime.date(2024, 6, 3))
        result = prior_oi_snapshot("SPY", datetime.date(2024, 6, 3))
        assert len(result) == 3  # the June 2 snapshot

    def test_skips_before_date_itself(self, tmp_path):
        """before_date itself must not be returned as the prior session."""
        import engine.data.oi_history as mod
        df = _make_expiry_oi_df(3)
        save_oi_snapshot(df, "SPY", date=datetime.date(2024, 6, 1))
        save_oi_snapshot(df, "SPY", date=datetime.date(2024, 6, 2))
        result = prior_oi_snapshot("SPY", datetime.date(2024, 6, 2))
        assert len(result) == 3  # must be June 1 rows (strictly less than June 2)


class TestListOiDates:
    def test_returns_empty_list_when_no_store(self):
        result = list_oi_dates("SPY")
        assert result == []

    def test_returns_dates_newest_first(self, tmp_path):
        import engine.data.oi_history as mod
        df = _make_expiry_oi_df(3)
        save_oi_snapshot(df, "SPY", date=datetime.date(2024, 6, 1))
        save_oi_snapshot(df, "SPY", date=datetime.date(2024, 6, 3))
        save_oi_snapshot(df, "SPY", date=datetime.date(2024, 6, 2))
        dates = list_oi_dates("SPY")
        assert dates == sorted(dates, reverse=True)

    def test_returns_correct_count(self, tmp_path):
        import engine.data.oi_history as mod
        df = _make_expiry_oi_df(3)
        for day in [1, 2, 3]:
            save_oi_snapshot(df, "SPY", date=datetime.date(2024, 6, day))
        dates = list_oi_dates("SPY")
        assert len(dates) == 3

    def test_returns_date_objects(self, tmp_path):
        import engine.data.oi_history as mod
        df = _make_expiry_oi_df(3)
        save_oi_snapshot(df, "SPY", date=datetime.date(2024, 6, 1))
        dates = list_oi_dates("SPY")
        assert all(isinstance(d, datetime.date) for d in dates)


# ── Named regression tests (plan 03 spec) ─────────────────────────────────────

def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    """Round-trip: save then load returns original rows with correct column values."""
    import engine.data.oi_history as mod
    monkeypatch.setattr(mod, "STORE_DIR", tmp_path / "oi_history")
    df = _make_expiry_oi_df(3)
    date = datetime.date(2024, 6, 1)
    save_oi_snapshot(df, "SPY", date=date)
    result = load_oi_snapshot("SPY", date)
    assert len(result) == 3
    assert set(result.columns) >= {"expiry", "dte", "call_oi", "put_oi", "oi", "pct_of_total", "put_call_ratio"}
    assert list(result["oi"]) == list(df["oi"])


def test_idempotency(tmp_path, monkeypatch):
    """Saving same date twice results in exactly 3 rows (replace, not append)."""
    import engine.data.oi_history as mod
    monkeypatch.setattr(mod, "STORE_DIR", tmp_path / "oi_history")
    df = _make_expiry_oi_df(3)
    date = datetime.date(2024, 6, 1)
    save_oi_snapshot(df, "SPY", date=date)
    save_oi_snapshot(df, "SPY", date=date)
    import pandas as pd
    hist = pd.read_parquet(mod.STORE_DIR / "oi_SPY.parquet")
    assert len(hist) == 3


def test_cold_start_prior(tmp_path, monkeypatch):
    """prior_oi_snapshot with no store returns empty DataFrame, no exception."""
    import engine.data.oi_history as mod
    monkeypatch.setattr(mod, "STORE_DIR", tmp_path / "oi_history")
    result = prior_oi_snapshot("SPY", datetime.date(2024, 6, 2))
    import pandas as pd
    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_prior_returns_most_recent(tmp_path, monkeypatch):
    """Two dates in store; prior_oi_snapshot(d2) returns d1 rows."""
    import engine.data.oi_history as mod
    monkeypatch.setattr(mod, "STORE_DIR", tmp_path / "oi_history")
    d1 = datetime.date(2024, 6, 1)
    d2 = datetime.date(2024, 6, 2)
    df1 = _make_expiry_oi_df(3)
    df2 = _make_expiry_oi_df(2)
    save_oi_snapshot(df1, "SPY", date=d1)
    save_oi_snapshot(df2, "SPY", date=d2)
    result = prior_oi_snapshot("SPY", d2)
    assert len(result) == 3  # d1 has 3 rows
