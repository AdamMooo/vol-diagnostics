"""Tests for engine/data/data_loader.py — fetched_at capture and filter_drop_pct math (20.5-01)."""
from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch

from engine.data.data_loader import load_chain
from engine.session import ET

_TODAY = datetime.date(2024, 6, 17)
_FRONT_EXPIRY = _TODAY + datetime.timedelta(days=5)  # dte=5, passes min_dte=1


def _symbol(ticker: str, expiry: datetime.date, side: str, strike: float) -> str:
    yy = expiry.year - 2000
    letter = "C" if side == "call" else "P"
    strike_int = int(round(strike * 1000))
    return f"{ticker}{yy:02d}{expiry.month:02d}{expiry.day:02d}{letter}{strike_int:08d}"


def _make_option(expiry: datetime.date, side: str, strike: float, oi: int, iv: float) -> dict:
    return {
        "option": _symbol("SPY", expiry, side, strike),
        "open_interest": oi,
        "iv": iv,
        "bid": 1.0,
        "ask": 1.1,
        "gamma": 0.01,
        "delta": 0.25 if side == "call" else -0.25,
        "vega": 0.1,
        "theta": -0.05,
    }


def _make_payload(options: list[dict]) -> dict:
    return {
        "data": {
            "current_price": 500.0,
            "iv30": 20.0,
            "price_change_percent": 0.1,
            "options": options,
        }
    }


def _mock_response(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=payload)
    return resp


class TestFilterDropPct:
    def test_filter_drop_pct_excludes_0dte_from_both_totals(self):
        options = [
            _make_option(_FRONT_EXPIRY, "call", 500.0, oi=200, iv=0.5),   # kept
            _make_option(_FRONT_EXPIRY, "call", 505.0, oi=50, iv=0.5),    # dropped: low OI
            _make_option(_FRONT_EXPIRY, "call", 510.0, oi=200, iv=3.5),   # dropped: IV too high
            _make_option(_TODAY, "call", 495.0, oi=999999, iv=0.5),       # 0DTE — excluded entirely
        ]
        payload = _make_payload(options)

        with patch("engine.data.data_loader.requests.get", return_value=_mock_response(payload)):
            snapshot = load_chain("SPY", today=_TODAY)

        # raw_oi_total = 200 + 50 + 200 = 450 (0DTE's 999999 must not be included)
        # kept_oi_total = 200
        # dropped = 250 -> 250/450*100
        assert snapshot.filter_drop_pct == (250 / 450) * 100

    def test_filter_drop_pct_zero_when_nothing_dropped(self):
        options = [
            _make_option(_FRONT_EXPIRY, "call", 500.0, oi=200, iv=0.5),
            _make_option(_FRONT_EXPIRY, "put", 495.0, oi=150, iv=0.4),
        ]
        payload = _make_payload(options)

        with patch("engine.data.data_loader.requests.get", return_value=_mock_response(payload)):
            snapshot = load_chain("SPY", today=_TODAY)

        assert snapshot.filter_drop_pct == 0.0
        assert snapshot.filter_drop_pct is not None


class TestFetchedAt:
    def test_fetched_at_is_tz_aware_datetime(self):
        options = [
            _make_option(_FRONT_EXPIRY, "call", 500.0, oi=200, iv=0.5),
        ]
        payload = _make_payload(options)

        with patch("engine.data.data_loader.requests.get", return_value=_mock_response(payload)):
            snapshot = load_chain("SPY", today=_TODAY)

        assert isinstance(snapshot.fetched_at, datetime.datetime)
        assert snapshot.fetched_at.tzinfo is not None
        assert snapshot.fetched_at.tzinfo.zone == ET.zone
