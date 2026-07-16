"""
Behavioral tests for engine/report/report.py.

Covers:
  - #ffffff body background (D-01)
  - viewport meta tag + single-column card (mobile-safe rewrite, 2026-07-16)
  - Key Levels block: gamma-flip / call wall / put wall / expected move
  - evolution_section_html() cold-start safety + rendering (D-10, D-11)
  - build_email() signature: evolution_data and png_note params
  - read-block chips + lean (CARD-02, CARD-03, CARD-04 lineage)
"""
from __future__ import annotations

import datetime
import re

import pandas as pd
import pytest

from engine.report.report import _ticker_card, build_email, evolution_section_html, _oi_summary_table


# ── Shared fixtures ───────────────────────────────────────────────────────────

def _minimal_result(
    ticker: str = "SPY",
    spot: float = 500.0,
    net_gex: float = 1e9,
    call_wall: float | None = 510.0,
    put_wall: float | None = 490.0,
    zero_gamma_level: float | None = 495.0,
    expected_move_pct: float | None = None,
    zgl_5d_shift: float | None = None,
    call_wall_5d_shift: float | None = None,
    put_wall_5d_shift: float | None = None,
    vrp: float | None = None,
    rv20: float | None = None,
) -> dict:
    """Minimal result dict sufficient for _ticker_card() to render without KeyError."""
    return {
        "ticker": ticker,
        "spot": spot,
        "net_gex": net_gex,
        "call_wall": call_wall,
        "put_wall": put_wall,
        "zero_gamma_level": zero_gamma_level,
        "expected_move_pct": expected_move_pct,
        "zgl_5d_shift": zgl_5d_shift,
        "call_wall_5d_shift": call_wall_5d_shift,
        "put_wall_5d_shift": put_wall_5d_shift,
        "price_change_pct": 0.5,
        "iv30": 18.0,
        "delta_hedge_flow": None,
        "front_skew": None,
        "vrp": vrp,
        "rv20": rv20,
    }


def _all_none_evolution(ticker: str) -> dict:
    return {"level": None, "rms": None, "skew_change": None, "term_change": None, "as_of": None}


# ── Mobile-safety: viewport meta + single-column card ─────────────────────────

def test_body_background_color():
    html = build_email([])
    assert "background:#ffffff" in html, "body tag must include explicit background:#ffffff"


def test_build_email_has_viewport_meta():
    html = build_email([])
    assert 'name="viewport"' in html, "missing viewport meta tag — breaks mobile mail rendering"


def test_ticker_card_has_no_side_by_side_split():
    # Regression guard: the old card split fields into two width="50%" columns,
    # which is what broke on phones. The rewritten card is single-column.
    r = _minimal_result()
    html = _ticker_card(r)
    assert 'width="50%"' not in html


def test_ticker_card_shows_spot_in_header():
    r = _minimal_result(spot=512.34)
    html = _ticker_card(r)
    assert "512" in html


# ── Key Levels block: gamma-flip / call wall / put wall / expected move ───────

def test_key_levels_shows_zgl_call_put_and_expected_move():
    r = _minimal_result(zero_gamma_level=495.0, call_wall=510.0, put_wall=490.0,
                         expected_move_pct=1.8)
    html = _ticker_card(r)
    assert "γ-flip" in html
    assert "Call wall" in html
    assert "Put wall" in html
    assert "Expected move" in html
    assert "495" in html and "510" in html and "490" in html
    assert "±1.8%" in html


def test_key_levels_includes_pct_from_spot():
    r = _minimal_result(spot=500.0, call_wall=510.0)
    html = _ticker_card(r)
    assert "+2.0%" in html  # (510-500)/500*100


def test_key_levels_includes_5d_shift_when_present():
    r = _minimal_result(call_wall=510.0, call_wall_5d_shift=1.5)
    html = _ticker_card(r)
    assert "+1.5% 5d" in html


def test_key_levels_omits_5d_shift_when_absent():
    r = _minimal_result(call_wall=510.0, call_wall_5d_shift=None)
    html = _ticker_card(r)
    assert "5d)" not in html


def test_key_levels_omits_row_when_level_missing():
    r = _minimal_result(zero_gamma_level=None)
    html = _ticker_card(r)
    assert "γ-flip" not in html


# ── Read-block tests: email card shows the same read as the dashboard ─────────

def test_read_block_renders_gated_chips_and_lean():
    # vrp_pct low with deep sample → "premium cheap"; net_gex < 0 → "dealers amplifying"
    r = _minimal_result(net_gex=-2e9)
    r["vrp_pct"], r["vrp_pct_n"] = 9, 252
    html = _ticker_card(r)
    assert "premium cheap" in html
    assert "dealers amplifying" in html
    assert "cheap" in html.lower()  # lean sentence present


def test_read_block_omits_ungated_premium_chip():
    # vrp present but sample below the credibility floor → no premium chip
    r = _minimal_result(net_gex=1e9)
    r["vrp_pct"], r["vrp_pct_n"] = 80, 10
    html = _ticker_card(r)
    assert "premium rich" not in html and "premium cheap" not in html
    assert "dealers stabilizing" in html  # present-tense fact still shows


def test_read_block_shows_skew_chip_when_seam_provides_it():
    # read_skew_pct on the summary (the canonical seam) flows into the chip set
    r = _minimal_result(net_gex=1e9)
    r["vrp_pct"], r["vrp_pct_n"] = 50, 252
    r["read_skew_pct"] = 80
    html = _ticker_card(r)
    assert "skew steep" in html


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
    # TICKER_LABEL["SPY"] = "SPY  S&P 500" — appears literally in HTML (not entity-escaped)
    card_pos = html.find("SPY  S&P 500")
    if card_pos == -1:
        card_pos = html.find("S&P 500")
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


# ── OI summary table tests ─────────────────────────────────────────────────

def _make_expiry_oi_df(n: int = 5) -> pd.DataFrame:
    """Build a minimal expiry_oi_df with the columns _oi_summary_table expects."""
    import datetime
    base = datetime.date(2024, 1, 19)
    return pd.DataFrame({
        "expiry": [(base + datetime.timedelta(days=i * 30)).strftime("%Y-%m-%d") for i in range(n)],
        "dte":    [30.0 + i * 30 for i in range(n)],
        "call_oi": [5000 - i * 200 for i in range(n)],
        "put_oi":  [4000 - i * 150 for i in range(n)],
        "oi":      [9000 - i * 350 for i in range(n)],
        "pct_of_total": [20.0 for _ in range(n)],
        "put_call_ratio": [0.80 + i * 0.05 for i in range(n)],
    })


def test_oi_summary_table_none_input():
    assert _oi_summary_table(None) is None


def test_oi_summary_table_empty_df():
    assert _oi_summary_table(pd.DataFrame()) is None


def test_oi_summary_table_renders_top3():
    import datetime
    df = _make_expiry_oi_df(5)
    result = _oi_summary_table(df)
    assert result is not None
    assert isinstance(result, str)
    # Only the first 3 expiry dates should appear (rows 0, 1, 2)
    dates_in_df = [
        (datetime.date(2024, 1, 19) + datetime.timedelta(days=i * 30)).strftime("%b %d")
        for i in range(5)
    ]
    for d in dates_in_df[:3]:
        assert d in result, f"Expected expiry {d} in top-3 OI table"
    for d in dates_in_df[3:]:
        assert d not in result, f"Expiry {d} (row {dates_in_df.index(d)+1}) must not appear in top-3"


def test_oi_summary_table_contains_section_label():
    df = _make_expiry_oi_df(3)
    result = _oi_summary_table(df)
    assert result is not None
    assert "OI IMPACT BY EXPIRY" in result


def test_build_email_oi_data_omitted():
    """build_email without oi_data must not include OI BY EXPIRY section."""
    html = build_email([_minimal_result()])
    assert "OI IMPACT BY EXPIRY" not in html


def test_build_email_oi_data_included():
    """build_email with oi_data containing a valid expiry_oi_df includes OI table."""
    df = _make_expiry_oi_df(5)
    oi_data = {"SPY": df}
    html = build_email([_minimal_result()], oi_data=oi_data)
    assert "OI IMPACT BY EXPIRY" in html


def test_oi_summary_table_contains_mobile_safe_columns():
    """Trimmed to 5 columns (from 8) so the table fits a phone-width email."""
    df = _make_expiry_oi_df(3)
    result = _oi_summary_table(df)
    assert result is not None
    for hdr in ("Expiry", "DTE", "OI Share", "P:C Ratio", "Impact"):
        assert hdr in result
    assert "5d Avg Share" not in result
    assert "vs 5d Avg" not in result


def test_oi_summary_table_impact_language_from_concentration():
    df = _make_expiry_oi_df(3)
    df.loc[0, "pct_of_total"] = 45.0
    result = _oi_summary_table(df)
    assert result is not None
    assert "high concentration" in result.lower()


def test_oi_summary_table_mentions_primary_14dte_lens():
    result = _oi_summary_table(_make_expiry_oi_df(3))
    assert result is not None
    assert "14 DTE primary" in result


def test_build_email_includes_quick_and_deep_method_sections():
    html = build_email([_minimal_result()])
    assert "Quick assumptions" in html
    assert "Deep methodology details" in html


def test_evolution_section_includes_largest_move_summary_row():
    evol_data = {
        "SPY": {"level": 0.1, "rms": 0.2, "skew_change": -0.1, "term_change": 0.6, "as_of": datetime.date(2026, 5, 27)},
        "QQQ": {"level": 0.0, "rms": 0.1, "skew_change": 0.0, "term_change": 0.1, "as_of": datetime.date(2026, 5, 27)},
        "IWM": {"level": -0.1, "rms": 0.1, "skew_change": 0.1, "term_change": -0.1, "as_of": datetime.date(2026, 5, 27)},
    }
    html = evolution_section_html(evol_data)
    assert html is not None
    assert "What changed most today" in html
