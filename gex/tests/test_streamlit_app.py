from __future__ import annotations

import pytest
from unittest import mock


def _minimal_summary(**overrides):
    base = {
        "ticker": "SPY",
        "spot": 500.0,
        "net_gex": 1e9,
        "zero_gamma_level": 495.0,
        "call_wall": 510.0,
        "put_wall": 490.0,
        "oi_call_wall": 512.0,
        "oi_put_wall": 488.0,
        "iv30": 18.0,
        "price_change_pct": 0.5,
        "front_skew": 3.2,
        "delta_hedge_flow": None,
        "rv20": 0.15,
        "vrp": 2.7,
    }
    base.update(overrides)
    return base


def _render_regime_card_html(summary_overrides=None, prior_row=None):
    pytest.importorskip("streamlit")
    summary = _minimal_summary(**(summary_overrides or {}))
    col = mock.MagicMock()

    with mock.patch("streamlit_app.load_prior_snapshot", return_value=prior_row):
        from streamlit_app import render_regime_card
        render_regime_card(col=col, summary=summary, spot=500.0)

    calls = col.markdown.call_args_list
    if not calls:
        return ""
    return calls[-1][0][0] if calls[-1][0] else ""


def test_render_regime_card_uses_build_card_fields():
    """Task 1 RED: render_regime_card must delegate to build_card_fields (imports present)."""
    pytest.importorskip("streamlit")
    import streamlit_app
    import inspect
    src = inspect.getsource(streamlit_app.render_regime_card)
    assert "build_card_fields" in src


class TestRegimeCardCanonical:
    """CARD-01/02/03/04: dashboard regime card parity with email card."""

    def test_vrp_row_present_with_value(self):
        """CARD-02: VRP row rendered when vrp is set."""
        html = _render_regime_card_html()
        assert "VRP" in html
        assert "2.7" in html

    def test_vrp_row_present_when_none(self):
        """CARD-02: VRP row present even when vrp=None, value shown as dash."""
        html = _render_regime_card_html({"vrp": None})
        assert "VRP" in html
        assert "—" in html  # em-dash

    def test_wall_labels_model(self):
        """CARD-04: GEX walls carry '(model)' label."""
        html = _render_regime_card_html()
        assert "(model)" in html
        assert "Call Wall (model)" in html
        assert "Put Wall (model)" in html

    def test_wall_labels_raw_oi(self):
        """CARD-04: OI walls carry '(raw OI)' label."""
        html = _render_regime_card_html()
        assert "(raw OI)" in html
        assert "OI Call Wall (raw OI)" in html
        assert "OI Put Wall (raw OI)" in html

    def test_delta_present_when_prior_row_supplied(self):
        """CARD-03: net_gex delta suffix appears when prior row exists."""
        import pandas as pd
        prior = pd.Series({"net_gex": 1.05e9, "front_skew": 3.0, "iv30": 18.0})
        html = _render_regime_card_html(prior_row=prior)
        assert "(+" in html

    def test_no_delta_when_no_prior_snapshot(self):
        """CARD-03: no '(+nan)', '(+0.0)' when prior_row is None."""
        html = _render_regime_card_html(prior_row=None)
        assert "(+nan)" not in html
        assert "(+0.0)" not in html


def test_import_no_emailer_bleed():
    """DASH-01, DASH-06: import streamlit_app does not pull in emailer or run_daily."""
    import importlib
    import sys
    pytest.importorskip("streamlit")
    importlib.import_module("streamlit_app")
    assert "gex.emailer" not in sys.modules
    assert "gex.run_daily" not in sys.modules


def test_fetch_ticker_has_clear():
    """DASH-02: @st.cache_data was applied — fetch_ticker.clear() is callable."""
    pytest.importorskip("streamlit")
    from streamlit_app import fetch_ticker
    assert callable(getattr(fetch_ticker, "clear", None))


def test_trust_readout_strings_formats_values():
    """08-04 VALID-06: raw-number readout, no badge/threshold."""
    pytest.importorskip("streamlit")
    from streamlit_app import _trust_readout_strings
    cov, rms, mx = _trust_readout_strings(
        {"coverage_pct": 87.0, "fit_rmse": 0.9, "max_resid": 2.1})
    assert cov == "Coverage 87%"
    assert rms == "Fit RMS 0.9pp"
    assert mx == "Max 2.1pp"


def test_trust_readout_strings_handles_missing_and_nan():
    pytest.importorskip("streamlit")
    from streamlit_app import _trust_readout_strings
    cov, rms, mx = _trust_readout_strings(
        {"coverage_pct": float("nan"), "fit_rmse": None})
    assert cov == "Coverage —"
    assert rms == "Fit RMS —"
    assert mx == "Max —"
    # entirely missing dict must not raise
    c2, r2, m2 = _trust_readout_strings(None)
    assert (c2, r2, m2) == ("Coverage —", "Fit RMS —", "Max —")


