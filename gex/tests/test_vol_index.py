"""Tests for gex/vol_index.py — fetch, store, and load CBOE vol-index data."""
from __future__ import annotations

import datetime
import io
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from gex.vol_index import (
    _fetch_cboe_vol_index,
    load_vol_index,
    save_vol_index_snapshot,
)


# ── Sample CSV data ─────────────────────────────────────────────────────────────

_SAMPLE_CSV = "DATE,OPEN,HIGH,LOW,CLOSE\n2026-01-01,15.5,16.0,14.8,15.2\n2026-01-02,15.2,15.8,14.9,15.6\n2026-01-05,15.6,16.2,15.1,16.0\n"


# ── _fetch_cboe_vol_index ───────────────────────────────────────────────────────


def test_fetch_200_returns_dataframe():
    """200 response with valid CSV returns non-empty DataFrame with columns lowercased."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = _SAMPLE_CSV
    mock_resp.raise_for_status = MagicMock()

    with patch("gex.vol_index.requests.get", return_value=mock_resp):
        df = _fetch_cboe_vol_index("VIX")

    assert df is not None
    assert not df.empty
    assert set(["DATE", "OPEN", "HIGH", "LOW", "CLOSE"]).issubset(set(df.columns))


def test_fetch_200_date_column_is_datetime_date():
    """DATE column is converted to datetime.date objects."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = _SAMPLE_CSV
    mock_resp.raise_for_status = MagicMock()

    with patch("gex.vol_index.requests.get", return_value=mock_resp):
        df = _fetch_cboe_vol_index("VIX")

    assert df is not None
    sample_date = df["DATE"].iloc[0]
    assert isinstance(sample_date, datetime.date)


def test_fetch_403_returns_none():
    """403 response (discontinued symbol) returns None without raising."""
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.raise_for_status = MagicMock()

    with patch("gex.vol_index.requests.get", return_value=mock_resp):
        result = _fetch_cboe_vol_index("VXST")

    assert result is None


def test_fetch_request_exception_returns_none():
    """Network error (RequestException) returns None without raising."""
    import requests as req_lib

    with patch("gex.vol_index.requests.get", side_effect=req_lib.exceptions.RequestException("timeout")):
        result = _fetch_cboe_vol_index("VIX")

    assert result is None


# ── save_vol_index_snapshot ─────────────────────────────────────────────────────


def _make_fetch_df():
    """Return a minimal DataFrame as returned by _fetch_cboe_vol_index."""
    return pd.DataFrame(
        {
            "DATE": [datetime.date(2026, 1, 5)],
            "OPEN": [15.6],
            "HIGH": [16.2],
            "LOW": [15.1],
            "CLOSE": [16.0],
        }
    )


def test_save_creates_parquet(tmp_path, monkeypatch):
    """save_vol_index_snapshot creates a parquet file in STORE_DIR."""
    import gex.vol_index as vi

    monkeypatch.setattr(vi, "STORE_DIR", tmp_path / "vol_index")

    df = _make_fetch_df()
    save_vol_index_snapshot(df, "VIX")

    store_path = tmp_path / "vol_index" / "VIX.parquet"
    assert store_path.exists()


def test_save_idempotent_same_date(tmp_path, monkeypatch):
    """Calling save twice for the same date does not duplicate rows."""
    import gex.vol_index as vi

    monkeypatch.setattr(vi, "STORE_DIR", tmp_path / "vol_index")

    df = _make_fetch_df()
    today = datetime.date(2026, 1, 5)
    save_vol_index_snapshot(df, "VIX", date=today)
    save_vol_index_snapshot(df, "VIX", date=today)

    stored = pd.read_parquet(tmp_path / "vol_index" / "VIX.parquet")
    date_col = pd.to_datetime(stored["date"]).dt.date
    assert (date_col == today).sum() == 1


def test_save_none_df_is_noop(tmp_path, monkeypatch):
    """save_vol_index_snapshot with df=None is a no-op."""
    import gex.vol_index as vi

    monkeypatch.setattr(vi, "STORE_DIR", tmp_path / "vol_index")

    save_vol_index_snapshot(None, "VIX")  # type: ignore[arg-type]

    store_path = tmp_path / "vol_index" / "VIX.parquet"
    assert not store_path.exists()


def test_save_empty_df_is_noop(tmp_path, monkeypatch):
    """save_vol_index_snapshot with empty df is a no-op."""
    import gex.vol_index as vi

    monkeypatch.setattr(vi, "STORE_DIR", tmp_path / "vol_index")

    save_vol_index_snapshot(pd.DataFrame(), "VIX")

    store_path = tmp_path / "vol_index" / "VIX.parquet"
    assert not store_path.exists()


# ── load_vol_index ──────────────────────────────────────────────────────────────


def test_load_returns_empty_when_no_parquet(tmp_path, monkeypatch):
    """load_vol_index returns empty DataFrame when parquet does not exist."""
    import gex.vol_index as vi

    monkeypatch.setattr(vi, "STORE_DIR", tmp_path / "vol_index")

    result = load_vol_index("VIX")
    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_load_returns_columns_and_date_type(tmp_path, monkeypatch):
    """After save, load returns DataFrame with expected columns and datetime.date dates."""
    import gex.vol_index as vi

    monkeypatch.setattr(vi, "STORE_DIR", tmp_path / "vol_index")

    df = _make_fetch_df()
    save_vol_index_snapshot(df, "VIX")

    result = load_vol_index("VIX")

    assert not result.empty
    assert list(result.columns) == ["symbol", "date", "open", "high", "low", "close"]
    assert isinstance(result["date"].iloc[0], datetime.date)


def test_load_sorted_ascending(tmp_path, monkeypatch):
    """load_vol_index returns rows sorted ascending by date."""
    import gex.vol_index as vi

    monkeypatch.setattr(vi, "STORE_DIR", tmp_path / "vol_index")

    # Save multi-row data
    df = pd.DataFrame(
        {
            "DATE": [datetime.date(2026, 1, 5), datetime.date(2026, 1, 2), datetime.date(2026, 1, 1)],
            "OPEN": [15.6, 15.2, 15.5],
            "HIGH": [16.2, 15.8, 16.0],
            "LOW": [15.1, 14.9, 14.8],
            "CLOSE": [16.0, 15.6, 15.2],
        }
    )
    save_vol_index_snapshot(df, "VIX")

    result = load_vol_index("VIX")
    dates = list(result["date"])
    assert dates == sorted(dates)


def test_load_days_limit(tmp_path, monkeypatch):
    """load_vol_index(days=2) returns at most 2 rows — the most recent 2, sorted ascending."""
    import gex.vol_index as vi

    monkeypatch.setattr(vi, "STORE_DIR", tmp_path / "vol_index")

    df = pd.DataFrame(
        {
            "DATE": [datetime.date(2026, 1, 1), datetime.date(2026, 1, 2), datetime.date(2026, 1, 5)],
            "OPEN": [15.5, 15.2, 15.6],
            "HIGH": [16.0, 15.8, 16.2],
            "LOW": [14.8, 14.9, 15.1],
            "CLOSE": [15.2, 15.6, 16.0],
        }
    )
    save_vol_index_snapshot(df, "VIX")

    result = load_vol_index("VIX", days=2)

    assert len(result) == 2
    # Should be the 2 most recent: Jan 2 and Jan 5
    assert result["date"].iloc[0] == datetime.date(2026, 1, 2)
    assert result["date"].iloc[1] == datetime.date(2026, 1, 5)
