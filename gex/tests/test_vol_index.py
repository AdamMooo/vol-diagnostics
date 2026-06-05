"""Tests for gex/vol_index.py — fetch, store, and load CBOE vol-index data."""
from __future__ import annotations

import datetime
from unittest import mock
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import requests

from gex.vol_index import (
    _fetch_cboe_vol_index,
    load_vol_index,
    refresh_vol_indices,
    save_vol_index_snapshot,
)


_SAMPLE_CSV = (
    "DATE,OPEN,HIGH,LOW,CLOSE\n"
    "2026-01-02,15.0,16.0,14.5,15.5\n"
    "2026-01-03,15.5,16.5,15.0,16.0\n"
    "2026-01-06,16.0,17.0,15.5,16.5\n"
)

_SAMPLE_CSV_WITH_BAD_ROW = (
    "DATE,OPEN,HIGH,LOW,CLOSE\n"
    "2026-01-02,15.0,16.0,14.5,15.5\n"
    "2026-01-03,15.5,16.5,15.0,bad\n"
    "2026-01-06,16.0,17.0,15.5,16.5\n"
)


def _make_fetch_df(nrows: int = 1) -> pd.DataFrame:
    dates = [datetime.date(2026, 1, i + 1) for i in range(nrows)]
    return pd.DataFrame(
        {
            "DATE": dates,
            "OPEN": [15.0 + i for i in range(nrows)],
            "HIGH": [16.0 + i for i in range(nrows)],
            "LOW": [14.5 + i for i in range(nrows)],
            "CLOSE": [15.5 + i for i in range(nrows)],
        }
    )


class TestFetch:
    def test_200_returns_dataframe(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = _SAMPLE_CSV
        mock_resp.raise_for_status = MagicMock()

        with patch("gex.vol_index.requests.get", return_value=mock_resp):
            df = _fetch_cboe_vol_index("VIX")

        assert df is not None
        assert not df.empty
        assert "CLOSE" in df.columns

    def test_200_date_column_is_date_type(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = _SAMPLE_CSV
        mock_resp.raise_for_status = MagicMock()

        with patch("gex.vol_index.requests.get", return_value=mock_resp):
            df = _fetch_cboe_vol_index("VIX")

        assert df is not None
        assert isinstance(df["DATE"].iloc[0], datetime.date)

    def test_403_returns_none(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.raise_for_status = MagicMock()

        with patch("gex.vol_index.requests.get", return_value=mock_resp):
            result = _fetch_cboe_vol_index("VXST")

        assert result is None

    def test_network_error_returns_none(self):
        with patch(
            "gex.vol_index.requests.get",
            side_effect=requests.exceptions.ConnectionError("refused"),
        ):
            result = _fetch_cboe_vol_index("VIX")

        assert result is None

    def test_malformed_rows_dropped(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = _SAMPLE_CSV_WITH_BAD_ROW
        mock_resp.raise_for_status = MagicMock()

        with patch("gex.vol_index.requests.get", return_value=mock_resp):
            df = _fetch_cboe_vol_index("VIX")

        assert df is not None
        assert df["CLOSE"].notna().all()


class TestSave:
    @pytest.fixture
    def sample_df(self):
        return _make_fetch_df(nrows=3)

    def test_creates_parquet(self, tmp_path, sample_df):
        import gex.vol_index as vi

        store = tmp_path / "vol_index"
        with patch("gex.vol_index.STORE_DIR", store):
            save_vol_index_snapshot(sample_df, "VIX")

        assert (store / "VIX.parquet").exists()

    def test_idempotent_same_date(self, tmp_path):
        today = datetime.date(2026, 1, 6)
        # df with a single row dated 'today' — save twice; store must have exactly 1 row
        single_row_df = pd.DataFrame(
            {"DATE": [today], "OPEN": [15.0], "HIGH": [16.0], "LOW": [14.5], "CLOSE": [15.5]}
        )
        store = tmp_path / "vol_index"
        with patch("gex.vol_index.STORE_DIR", store):
            save_vol_index_snapshot(single_row_df, "VIX", date=today)
            save_vol_index_snapshot(single_row_df, "VIX", date=today)

        stored = pd.read_parquet(store / "VIX.parquet")
        date_col = pd.to_datetime(stored["date"]).dt.date
        # The row for 'today' must appear exactly once — idempotency guard works
        assert (date_col == today).sum() == 1

    def test_none_df_is_noop(self, tmp_path):
        store = tmp_path / "vol_index"
        with patch("gex.vol_index.STORE_DIR", store):
            save_vol_index_snapshot(None, "VIX")  # type: ignore[arg-type]

        assert not (store / "VIX.parquet").exists()

    def test_empty_df_is_noop(self, tmp_path):
        store = tmp_path / "vol_index"
        with patch("gex.vol_index.STORE_DIR", store):
            save_vol_index_snapshot(pd.DataFrame(), "VIX")

        assert not (store / "VIX.parquet").exists()

    def test_columns_stored_lowercase(self, tmp_path, sample_df):
        store = tmp_path / "vol_index"
        with patch("gex.vol_index.STORE_DIR", store):
            save_vol_index_snapshot(sample_df, "VIX")

        stored = pd.read_parquet(store / "VIX.parquet")
        assert "close" in stored.columns
        assert "CLOSE" not in stored.columns


class TestLoad:
    @pytest.fixture
    def store_with_data(self, tmp_path):
        df = _make_fetch_df(nrows=10)
        store = tmp_path / "vol_index"
        with patch("gex.vol_index.STORE_DIR", store):
            save_vol_index_snapshot(df, "VIX")
        return store

    def test_no_parquet_returns_empty(self, tmp_path):
        store = tmp_path / "vol_index"
        with patch("gex.vol_index.STORE_DIR", store):
            result = load_vol_index("VIX")

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_returns_sorted_ascending(self, tmp_path):
        df = pd.DataFrame(
            {
                "DATE": [datetime.date(2026, 1, 5), datetime.date(2026, 1, 2), datetime.date(2026, 1, 1)],
                "OPEN": [15.6, 15.2, 15.5],
                "HIGH": [16.2, 15.8, 16.0],
                "LOW": [15.1, 14.9, 14.8],
                "CLOSE": [16.0, 15.6, 15.2],
            }
        )
        store = tmp_path / "vol_index"
        with patch("gex.vol_index.STORE_DIR", store):
            save_vol_index_snapshot(df, "VIX")
            result = load_vol_index("VIX")

        dates = list(result["date"])
        assert dates == sorted(dates)

    def test_days_limit(self, store_with_data):
        with patch("gex.vol_index.STORE_DIR", store_with_data):
            result = load_vol_index("VIX", days=3)

        assert len(result) == 3

    def test_has_close_column(self, store_with_data):
        with patch("gex.vol_index.STORE_DIR", store_with_data):
            result = load_vol_index("VIX")

        assert "close" in result.columns

    def test_date_column_is_date_type(self, store_with_data):
        with patch("gex.vol_index.STORE_DIR", store_with_data):
            result = load_vol_index("VIX")

        assert all(isinstance(d, datetime.date) for d in result["date"])


class TestRefresh:
    def test_skips_403_symbol(self):
        with patch("gex.vol_index._fetch_cboe_vol_index", return_value=None) as mock_fetch, \
             patch("gex.vol_index.save_vol_index_snapshot") as mock_save:
            refresh_vol_indices(["VIX"])

        mock_save.assert_not_called()

    def test_calls_save_on_success(self):
        valid_df = _make_fetch_df()
        with patch("gex.vol_index._fetch_cboe_vol_index", return_value=valid_df) as mock_fetch, \
             patch("gex.vol_index.save_vol_index_snapshot") as mock_save:
            refresh_vol_indices(["VIX"])

        mock_save.assert_called_once()
        _, call_kwargs = mock_save.call_args
        # symbol is passed as positional arg
        call_args = mock_save.call_args[0]
        assert call_args[1] == "VIX"
