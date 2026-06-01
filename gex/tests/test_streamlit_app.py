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
    import streamlit
    summary = _minimal_summary(**(summary_overrides or {}))
    captured = {}

    def _capture_markdown(html, **kwargs):
        captured["html"] = html

    with mock.patch.object(streamlit, "markdown", side_effect=_capture_markdown):
        with mock.patch("gex.validation.load_prior_snapshot", return_value=prior_row):
            from streamlit_app import render_regime_card
            render_regime_card(col=mock.MagicMock(), summary=summary, spot=500.0)

    return captured.get("html", "")


def test_render_regime_card_uses_build_card_fields():
    """Task 1 RED: render_regime_card must delegate to build_card_fields (imports present)."""
    pytest.importorskip("streamlit")
    import streamlit_app
    import inspect
    src = inspect.getsource(streamlit_app.render_regime_card)
    assert "build_card_fields" in src


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


