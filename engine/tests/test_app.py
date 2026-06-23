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




def _import_app_module():
    pytest.importorskip("streamlit")
    import importlib
    import sys
    import types
    if "pandas_market_calendars" not in sys.modules:
        fake = types.ModuleType("pandas_market_calendars")

        class _Calendar:
            def schedule(self, *args, **kwargs):
                import pandas as pd
                return pd.DataFrame(index=[])

        fake.get_calendar = lambda _name: _Calendar()
        sys.modules["pandas_market_calendars"] = fake
    return importlib.import_module("app")

def _render_regime_card_html(summary_overrides=None, prior_row=None):
    pytest.importorskip("streamlit")
    summary = _minimal_summary(**(summary_overrides or {}))
    col = mock.MagicMock()
    app_mod = _import_app_module()

    with mock.patch.object(app_mod, "load_prior_snapshot", return_value=prior_row):
        app_mod.render_regime_card(col=col, summary=summary, spot=500.0)

    calls = col.markdown.call_args_list
    if not calls:
        return ""
    return calls[-1][0][0] if calls[-1][0] else ""


def test_render_regime_card_uses_build_card_fields():
    """Task 1 RED: render_regime_card must delegate to build_card_fields (imports present)."""
    pytest.importorskip("streamlit")
    app = _import_app_module()
    import inspect
    src = inspect.getsource(app.render_regime_card)
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
        """D-11: secondary wall fields stay out of compact default card."""
        html = _render_regime_card_html()
        assert "Call Wall (model)" not in html
        assert "Put Wall (model)" not in html

    def test_wall_labels_raw_oi(self):
        """D-11: secondary OI wall fields stay out of compact default card."""
        html = _render_regime_card_html()
        assert "OI Call Wall (raw OI)" not in html
        assert "OI Put Wall (raw OI)" not in html

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
    """DASH-01, DASH-06: import app does not pull in emailer or run_daily."""
    import importlib
    import sys
    pytest.importorskip("streamlit")
    # Purge any prior-test pollution so we test a clean import of app,
    # not the accumulated session state (test ordering can load engine.run_daily earlier).
    for mod in list(sys.modules):
        if mod in ("engine.report.emailer", "engine.run_daily", "app"):
            del sys.modules[mod]
    _import_app_module()
    assert "engine.report.emailer" not in sys.modules
    assert "engine.run_daily" not in sys.modules


def test_fetch_ticker_has_clear():
    """DASH-02: @st.cache_data was applied — fetch_ticker.clear() is callable."""
    pytest.importorskip("streamlit")
    fetch_ticker = _import_app_module().fetch_ticker
    assert callable(getattr(fetch_ticker, "clear", None))


def test_trust_readout_strings_formats_values():
    """08-04 VALID-06: raw-number readout, no badge/threshold."""
    pytest.importorskip("streamlit")
    _trust_readout_strings = _import_app_module()._trust_readout_strings
    cov, rms, mx = _trust_readout_strings(
        {"coverage_pct": 87.0, "fit_rmse": 0.9, "max_resid": 2.1})
    assert cov == "Coverage 87%"
    assert rms == "Fit RMS 0.9pp"
    assert mx == "Max 2.1pp"


def test_trust_readout_strings_handles_missing_and_nan():
    pytest.importorskip("streamlit")
    _trust_readout_strings = _import_app_module()._trust_readout_strings
    cov, rms, mx = _trust_readout_strings(
        {"coverage_pct": float("nan"), "fit_rmse": None})
    assert cov == "Coverage —"
    assert rms == "Fit RMS —"
    assert mx == "Max —"
    # entirely missing dict must not raise
    c2, r2, m2 = _trust_readout_strings(None)
    assert (c2, r2, m2) == ("Coverage —", "Fit RMS —", "Max —")



def test_render_regime_card_uses_compact_split_helper():
    """Task 2 RED: dashboard card should consume compact split helper from card_model."""
    pytest.importorskip("streamlit")
    app = _import_app_module()
    import inspect
    src = inspect.getsource(app.render_regime_card)
    assert "split_compact_fields" in src


def test_render_regime_card_renders_trust_tags_from_card_fields():
    html = _render_regime_card_html({"vrp_pct_n": 80})
    assert "rc-tag" in html
    assert "market" in html
    assert "building" in html
    assert "model" in html
    assert "smile" in html




def test_methods_panel_exposes_quick_and_deep_layers():
    app = _import_app_module()
    assert hasattr(app, "_methods_quick_bullets")
    assert hasattr(app, "_methods_deep_markdown")


def test_methods_copy_mentions_quick_and_deep_sections():
    app = _import_app_module()
    quick = app._methods_quick_bullets()
    deep = app._methods_deep_markdown()
    assert any("Quick assumptions" in b for b in quick)
    assert "Deep methodology details" in deep

def test_evolution_summary_picks_largest_dimension_and_direction():
    app = _import_app_module()
    line = app._evolution_largest_move_summary({
        "level": 0.10,
        "rms": -0.25,
        "skew_change": 0.20,
        "term_change": -0.80,
    })
    assert "what changed most today" in line.lower()
    assert "term" in line.lower()
    assert "flattened" in line.lower()
