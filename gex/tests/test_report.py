"""
Behavioral tests for gex/report.py.

Covers:
  - #ffffff body background (D-01)
  - OI Call Wall / OI Put Wall rows in _ticker_card() (D-07, D-09)
  - evolution_section_html() cold-start safety + rendering (D-10, D-11)
  - build_email() signature: evolution_data and png_note params
"""
from __future__ import annotations

import datetime
import re

import pytest

from gex.report import _ticker_card, build_email, evolution_section_html


# ── Shared fixtures ───────────────────────────────────────────────────────────

def _minimal_result(
    ticker: str = "SPY",
    spot: float = 500.0,
    net_gex: float = 1e9,
    call_wall: float | None = 510.0,
    put_wall: float | None = 490.0,
    zero_gamma_level: float | None = 495.0,
    oi_call_wall: float | None = None,
    oi_put_wall: float | None = None,
) -> dict:
    """Minimal result dict sufficient for _ticker_card() to render without KeyError."""
    return {
        "ticker": ticker,
        "spot": spot,
        "net_gex": net_gex,
        "call_wall": call_wall,
        "put_wall": put_wall,
        "zero_gamma_level": zero_gamma_level,
        "oi_call_wall": oi_call_wall,
        "oi_put_wall": oi_put_wall,
        "price_change_pct": 0.5,
        "iv30": 18.0,
        "delta_hedge_flow": None,
        "front_skew": None,
    }


def _all_none_evolution(ticker: str) -> dict:
    return {"level": None, "rms": None, "skew_change": None, "term_change": None, "as_of": None}


# ── Task 1 tests: body background + OI wall rows ──────────────────────────────

def test_body_background_color():
    html = build_email([])
    assert "background:#ffffff" in html, "body tag must include explicit background:#ffffff"


def test_oi_wall_rows_present():
    r = _minimal_result(oi_call_wall=510.0, oi_put_wall=490.0)
    html = _ticker_card(r)
    assert re.search(r"OI CALL WALL", html, re.IGNORECASE), "OI CALL WALL row missing"
    assert re.search(r"OI PUT WALL", html, re.IGNORECASE), "OI PUT WALL row missing"


def test_oi_wall_rows_dash_when_none():
    r = _minimal_result(oi_call_wall=None, oi_put_wall=None)
    html = _ticker_card(r)
    # Both OI rows present but showing the em-dash for None
    assert re.search(r"OI CALL WALL", html, re.IGNORECASE), "OI CALL WALL row missing even when None"
    # Count em-dashes — at least one should appear from OI rows
    assert html.count("—") >= 1, "Expected at least one em-dash for None OI wall"


def test_oi_walls_below_gex_walls():
    r = _minimal_result(oi_call_wall=510.0, oi_put_wall=490.0)
    html = _ticker_card(r)
    # Find positions — GEX CALL WALL must come before OI CALL WALL (D-09)
    gex_pos = html.lower().find("call wall")
    oi_pos = html.lower().find("oi call wall")
    assert gex_pos != -1, "CALL WALL (GEX) row not found"
    assert oi_pos != -1, "OI CALL WALL row not found"
    assert gex_pos < oi_pos, "GEX Call Wall must appear before OI Call Wall in HTML"


# ── Task 2 tests: evolution_section_html() + build_email() new params ─────────

def test_evolution_section_cold_start():
    spy_result = _minimal_result()
    evol_data = {
        "SPY": _all_none_evolution("SPY"),
        "QQQ": _all_none_evolution("QQQ"),
        "IWM": _all_none_evolution("IWM"),
    }
    html = build_email([spy_result], evolution_data=evol_data)
    assert "Surface Evolution" not in html, (
        "Evolution section must be entirely absent on cold start (D-11)"
    )


def test_evolution_section_present_when_data():
    spy_result = _minimal_result()
    evol_data = {
        "SPY": {"level": 0.5, "rms": 0.8, "skew_change": -0.2, "term_change": 0.1,
                "as_of": datetime.date(2026, 5, 27)},
        "QQQ": {"level": 0.3, "rms": 0.5, "skew_change": -0.1, "term_change": 0.05,
                "as_of": datetime.date(2026, 5, 27)},
        "IWM": {"level": 0.1, "rms": 0.3, "skew_change": 0.0, "term_change": -0.05,
                "as_of": datetime.date(2026, 5, 27)},
    }
    html = build_email([spy_result], evolution_data=evol_data)
    assert "Surface Evolution" in html, "Evolution section missing when data is present"


def test_evolution_section_before_cards():
    spy_result = _minimal_result()
    evol_data = {
        "SPY": {"level": 0.5, "rms": 0.8, "skew_change": -0.2, "term_change": 0.1,
                "as_of": datetime.date(2026, 5, 27)},
        "QQQ": {"level": 0.3, "rms": 0.5, "skew_change": -0.1, "term_change": 0.05,
                "as_of": datetime.date(2026, 5, 27)},
        "IWM": {"level": 0.1, "rms": 0.3, "skew_change": 0.0, "term_change": -0.05,
                "as_of": datetime.date(2026, 5, 27)},
    }
    html = build_email([spy_result], evolution_data=evol_data)
    evol_pos = html.find("Surface Evolution")
    # "SPY  S&P 500" is the ticker label in TICKER_LABEL
    card_pos = html.find("SPY  S&amp;P 500")
    if card_pos == -1:
        card_pos = html.find("S&amp;P 500")
    assert evol_pos != -1, "Surface Evolution section not found"
    assert card_pos != -1, "SPY ticker card not found"
    assert evol_pos < card_pos, "Evolution section must appear before ticker cards (D-10)"


def test_evolution_table_has_all_tickers():
    spy_result = _minimal_result()
    evol_data = {
        "SPY": {"level": 0.5, "rms": 0.8, "skew_change": -0.2, "term_change": 0.1,
                "as_of": datetime.date(2026, 5, 27)},
        "QQQ": {"level": 0.3, "rms": 0.5, "skew_change": -0.1, "term_change": 0.05,
                "as_of": datetime.date(2026, 5, 27)},
        "IWM": {"level": 0.1, "rms": 0.3, "skew_change": 0.0, "term_change": -0.05,
                "as_of": datetime.date(2026, 5, 27)},
    }
    section_html = evolution_section_html(evol_data)
    assert section_html is not None
    assert "SPY" in section_html
    assert "QQQ" in section_html
    assert "IWM" in section_html


def test_png_note_present_when_set():
    spy_result = _minimal_result()
    note = "Surface charts unavailable — kaleido not installed or PNG export failed."
    html = build_email([spy_result], png_note=note)
    assert note in html, "PNG fallback note not found in email body"


def test_png_note_absent_when_none():
    spy_result = _minimal_result()
    html = build_email([spy_result])
    assert "Surface charts unavailable" not in html, "PNG note should be absent when png_note=None"


def test_build_email_signature_accepts_new_params():
    # Backward-compatible defaults — must not raise
    html = build_email([], evolution_data=None, png_note=None)
    assert html  # non-empty string
