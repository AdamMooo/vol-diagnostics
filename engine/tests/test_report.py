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

from engine.report.report import (
    _ticker_card, build_email, evolution_section_html,
    alerts_section_html, _methodology_link, _ordinal,
)
from engine import config


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
    fetched_at: "datetime.datetime | None" = None,
    filter_drop_pct: float | None = None,
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
        "fetched_at": fetched_at,
        "filter_drop_pct": filter_drop_pct,
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


# ── Metrics table: move-size only, no price-level surfacing ───────────────────

def test_metrics_table_shows_expected_move_not_walls():
    # De-directionalized 2026-08-05: γ-flip / call wall / put wall are price levels
    # and are no longer surfaced. Expected move (a move-size stat) stays.
    r = _minimal_result(zero_gamma_level=495.0, call_wall=510.0, put_wall=490.0,
                         expected_move_pct=1.8)
    html = _ticker_card(r)
    assert "Expected move" in html
    assert "±1.8%" in html


def test_metrics_table_omits_wall_and_gamma_flip_levels():
    r = _minimal_result(zero_gamma_level=495.0, call_wall=510.0, put_wall=490.0)
    html = _ticker_card(r)
    assert "γ-flip" not in html
    assert "Call wall" not in html
    assert "Put wall" not in html
    # The level values themselves must not leak into the card either.
    assert "510" not in html and "490" not in html and "495" not in html


# ── Read-block tests: email card shows a single concise "so what" line ───────

def test_read_block_renders_lean_and_regime():
    # vrp_pct low with deep sample → cheap lean; net_gex < 0 → "Dealers amplifying"
    r = _minimal_result(net_gex=-2e9)
    r["vrp_pct"], r["vrp_pct_n"] = 9, 252
    html = _ticker_card(r)
    assert "cheap" in html.lower()  # lean sentence present
    assert "Dealers amplifying" in html  # regime label in the card header


def test_read_block_lean_builds_when_premium_ungated():
    # vrp present but sample below the credibility floor → no rich/cheap read
    r = _minimal_result(net_gex=1e9)
    r["vrp_pct"], r["vrp_pct_n"] = 80, 10
    html = _ticker_card(r)
    assert "premium rich" not in html and "premium cheap" not in html
    assert "history building" in html.lower()  # hedged lean
    assert "Dealers stabilizing" in html  # present-tense regime fact still shows


def test_read_block_has_no_chip_pills():
    # The chip pills were removed to cut color noise / redundancy with the header.
    r = _minimal_result(net_gex=1e9)
    r["vrp_pct"], r["vrp_pct_n"] = 50, 252
    r["read_skew_pct"] = 80
    html = _ticker_card(r)
    assert "skew steep" not in html  # qualitative skew chip gone; number stays in table


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


# ── Header block: end-of-day settled-data line (after-close framing) ─────────

def test_snapshot_timestamp_present_when_fetched_at_set():
    fetched_at = datetime.datetime(2026, 5, 11, 16, 15)
    r = _minimal_result(fetched_at=fetched_at)
    html = build_email([r])
    # After-close framing: settled session, no intraday-staleness language.
    assert "Close of Mon, May 11, 2026" in html
    assert "settled end-of-day data" in html
    assert "OI T-1" not in html
    assert "Greeks 15-min delayed" not in html


def test_snapshot_timestamp_absent_when_fetched_at_missing():
    r = _minimal_result(fetched_at=None)
    html = build_email([r])
    assert "Close of" not in html
    assert "settled end-of-day data" not in html


def test_methodology_caveat_banner_removed():
    # The static methodology banner was removed to cut fixed filler wording.
    html = build_email([_minimal_result(fetched_at=None)])
    assert "Methodology note" not in html
    assert "background:#f1f5f9" not in html


# ── OI-by-expiry section removed 2026-08-05 (too granular for a daily brief) ──

def test_build_email_has_no_oi_by_expiry_section():
    html = build_email([_minimal_result()])
    assert "OI IMPACT BY EXPIRY" not in html


def test_build_email_omits_assumptions_footer():
    html = build_email([_minimal_result()])
    assert "Method assumptions" not in html
    assert "Deep methodology details" not in html


# ── Task 2: mobile-safe width (D-05) + filter-drop footer disclosure (D-07) ───

def test_build_email_uses_mobile_safe_390px_width():
    html = build_email([_minimal_result()])
    assert "max-width:390px" in html
    assert "max-width:720px" not in html


def test_filter_drop_bullet_present_when_pct_set():
    r = _minimal_result(filter_drop_pct=4.2)
    html = build_email([r])
    assert "raw chain OI" not in html


def test_filter_drop_bullet_absent_when_pct_none():
    r = _minimal_result(filter_drop_pct=None)
    html = build_email([r])
    assert "raw chain OI" not in html


def test_gex_magnitude_bullet_not_duplicated_in_footer():
    # Keep the caveat short: only the concise banner copy should appear.
    html = build_email([_minimal_result()])
    assert "Sign &amp; order of magnitude" not in html


def test_evolution_section_includes_largest_move_summary_row():
    evol_data = {
        "SPY": {"level": 0.1, "rms": 0.2, "skew_change": -0.1, "term_change": 0.6, "as_of": datetime.date(2026, 5, 27)},
        "QQQ": {"level": 0.0, "rms": 0.1, "skew_change": 0.0, "term_change": 0.1, "as_of": datetime.date(2026, 5, 27)},
        "IWM": {"level": -0.1, "rms": 0.1, "skew_change": 0.1, "term_change": -0.1, "as_of": datetime.date(2026, 5, 27)},
    }
    html = evolution_section_html(evol_data)
    assert html is not None
    assert "What moved most today" in html


def test_evolution_section_is_movers_strip_only():
    # Per-horizon 5d/10d/30d tables + legend were dropped 2026-08-05; the section
    # is now just the at-a-glance movers strip.
    evol_data = {
        "SPY": {
            "level": 0.1, "rms": 0.2, "skew_change": -0.1, "term_change": 0.6, "as_of": datetime.date(2026, 5, 27),
            "horizons": {
                "5d": {"level": 0.10, "rms": 0.20, "skew_change": -0.10, "term_change": 0.60},
                "30d": {"level": 0.30, "rms": 0.30, "skew_change": 0.00, "term_change": 0.10},
            },
        },
    }
    html = evolution_section_html(evol_data)
    assert html is not None
    assert "What moved most today" in html
    # No per-horizon table scaffolding.
    assert "5-day" not in html and "10-day" not in html and "30-day" not in html


# ── Event-shaped alerts banner (Plan 27-04, hybrid) ──────────────────────────

def _synthetic_alert_df(alert_type: str = "entry", rank: int = 92) -> pd.DataFrame:
    return pd.DataFrame([{
        "date": "2026-07-27", "ticker": "SPY", "metric": "skew_25d",
        "rank_kind": "level_deep", "alert_type": alert_type,
        "rank_at_transition": rank, "prior_state": "out",
    }])


def test_ordinal_suffixes():
    assert _ordinal(1) == "1st"
    assert _ordinal(2) == "2nd"
    assert _ordinal(3) == "3rd"
    assert _ordinal(11) == "11th"
    assert _ordinal(92) == "92nd"
    assert _ordinal(None) == ""


def test_alerts_section_empty_returns_blank():
    # Quiet day (cold-start norm): no banner at all — the rich report is unchanged.
    assert alerts_section_html(None, {}) == ""
    assert alerts_section_html(pd.DataFrame(columns=["ticker"]), {}) == ""


def test_alerts_section_renders_event_row_with_delta():
    df = _synthetic_alert_df(alert_type="entry", rank=92)
    lookup = {("SPY", "skew_25d", "level_deep"): 78}
    html = alerts_section_html(df, lookup)
    assert "SPY" in html
    assert "Skew" in html
    assert "ENTRY" in html
    assert "92nd" in html
    assert "was 78th" in html  # Δ-vs-yesterday fragment


def test_alerts_section_escalation_badge():
    html = alerts_section_html(_synthetic_alert_df(alert_type="escalation"), {})
    assert "ESCALATION" in html


def test_build_email_quiet_day_has_no_alerts_banner():
    # No alert_events → rich descriptive email unchanged, no Alerts header.
    html = build_email([_minimal_result()])
    assert ">Alerts<" not in html


def test_build_email_alerts_banner_suppressed_even_when_events():
    # Suppressed 2026-07-27 (Adam's call): a bare rank-crossing with no mechanism/
    # evidence-tier context read as more meaningful than it is. alerts_section_html()
    # itself stays tested above (test_alerts_section_*) for when it's re-enabled —
    # only build_email's wiring to it is disabled.
    df = _synthetic_alert_df()
    lookup = {("SPY", "skew_25d", "level_deep"): 78}
    html = build_email([_minimal_result()], alert_events=df, prior_rank_lookup=lookup)
    assert ">Alerts<" not in html


def test_build_email_includes_methodology_link_when_url_set():
    html = build_email([_minimal_result()])
    if config.DASHBOARD_METHODOLOGY_URL:
        assert config.DASHBOARD_METHODOLOGY_URL in html
        assert "Methodology" in html


def test_methodology_link_omitted_when_url_blank(monkeypatch):
    monkeypatch.setattr(config, "DASHBOARD_METHODOLOGY_URL", "")
    assert _methodology_link() == ""
