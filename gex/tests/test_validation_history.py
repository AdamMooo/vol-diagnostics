from __future__ import annotations

import datetime
import pathlib

import pandas as pd
import pytest

from gex.validation import load_history


def _make_store(path: pathlib.Path, rows: list[dict]) -> None:
    """Write a minimal parquet store at `path` from a list of row dicts."""
    pd.DataFrame(rows).to_parquet(path, index=False)


def _row(ticker: str, date: datetime.date, spot: float = 500.0, net_gex: float = 1e9,
         regime: str = "positive", zgl: float = 498.0) -> dict:
    return {
        "date": pd.Timestamp(date),
        "ticker": ticker,
        "spot": spot,
        "net_gex": net_gex,
        "gamma_regime": regime,
        "zero_gamma_level": zgl,
        "call_wall": spot + 5,
        "put_wall": spot - 5,
        "vanna_exposure": 0.5e9,
    }


def test_load_history_returns_n_rows(tmp_path, monkeypatch):
    """Returns at most `days` rows for the requested ticker."""
    import gex.validation as val
    store = tmp_path / "snap.parquet"
    rows = [_row("SPY", datetime.date(2025, 1, i + 1)) for i in range(5)]
    _make_store(store, rows)
    monkeypatch.setattr(val, "STORE", store)

    result = load_history("SPY", days=3)
    assert len(result) == 3


def test_load_history_sorted_descending(tmp_path, monkeypatch):
    """Most recent session is at index 0."""
    import gex.validation as val
    store = tmp_path / "snap.parquet"
    rows = [_row("SPY", datetime.date(2025, 1, i + 1)) for i in range(5)]
    _make_store(store, rows)
    monkeypatch.setattr(val, "STORE", store)

    result = load_history("SPY", days=5)
    dates = list(result["date"])
    assert dates == sorted(dates, reverse=True)


def test_load_history_filters_by_ticker(tmp_path, monkeypatch):
    """Only rows for the requested ticker are returned."""
    import gex.validation as val
    store = tmp_path / "snap.parquet"
    rows = [
        _row("SPY", datetime.date(2025, 1, 1)),
        _row("QQQ", datetime.date(2025, 1, 1)),
        _row("SPY", datetime.date(2025, 1, 2)),
    ]
    _make_store(store, rows)
    monkeypatch.setattr(val, "STORE", store)

    result = load_history("SPY", days=30)
    assert len(result) == 2
    assert all(result["ticker"] == "SPY")


def test_load_history_empty_when_no_store(tmp_path, monkeypatch):
    """Returns empty DataFrame when parquet store does not exist."""
    import gex.validation as val
    monkeypatch.setattr(val, "STORE", tmp_path / "nonexistent.parquet")

    result = load_history("SPY")
    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_load_history_empty_when_ticker_missing(tmp_path, monkeypatch):
    """Returns empty DataFrame when ticker has no rows in the store."""
    import gex.validation as val
    store = tmp_path / "snap.parquet"
    _make_store(store, [_row("SPY", datetime.date(2025, 1, 1))])
    monkeypatch.setattr(val, "STORE", store)

    result = load_history("IWM", days=30)
    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_load_history_fewer_rows_than_days(tmp_path, monkeypatch):
    """Returns all available rows when store has fewer than `days` rows for ticker."""
    import gex.validation as val
    store = tmp_path / "snap.parquet"
    rows = [_row("SPY", datetime.date(2025, 1, i + 1)) for i in range(3)]
    _make_store(store, rows)
    monkeypatch.setattr(val, "STORE", store)

    result = load_history("SPY", days=30)
    assert len(result) == 3


def test_load_history_default_days_is_30(tmp_path, monkeypatch):
    """Default days=30 — calling load_history(ticker) without days uses 30."""
    import gex.validation as val
    store = tmp_path / "snap.parquet"
    base = datetime.date(2025, 1, 1)
    rows = [_row("SPY", base + datetime.timedelta(days=i)) for i in range(35)]
    _make_store(store, rows)
    monkeypatch.setattr(val, "STORE", store)

    result = load_history("SPY")
    assert len(result) == 30
