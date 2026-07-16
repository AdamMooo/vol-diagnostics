from __future__ import annotations

import pytest


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
    assert "largest move" in line.lower()
    assert "term" in line.lower()
    assert "flattened" in line.lower()

def test_phase18_page_tabs_top_level_labels_and_sections_contract():
    app = _import_app_module()
    import inspect
    src = inspect.getsource(app)
    assert 'tab_regime, tab_surfaces, tab_positioning = st.tabs(' in src
    assert '["Regime", "Surfaces", "Positioning"]' in src
    assert '["Surface", "Evolution", "Positioning"]' not in src
    assert 'sub_today, sub_compare, sub_evolution = st.tabs(["Today", "Compare", "Evolution"])' in src


def test_phase18_page_tabs_routes_evolution_under_surfaces_only():
    app = _import_app_module()
    import inspect
    src = inspect.getsource(app)
    i_surfaces = src.index('with tab_surfaces:')
    i_evo_call = src.index('_evolution_section(selected_all, all_data)')
    assert i_surfaces < i_evo_call

def test_phase18_cross_index_teaser_and_trust_tag_regime_briefing_contract():
    app = _import_app_module()
    import inspect
    src = inspect.getsource(app)
    # Regime tab now uses the unified environment hero
    assert '_render_environment_hero(selected_all, all_data)' in src
    assert 'with tab_regime:' in src


def test_phase18_cross_index_teaser_and_trust_tag_default_cards_and_positioning_split():
    app = _import_app_module()
    import inspect
    src = inspect.getsource(app)
    assert 'st.multiselect(' in src
    assert 'default=INDEX_TICKERS' in src
    assert 'st.dataframe(display_df, use_container_width=True, hide_index=True)' in src
