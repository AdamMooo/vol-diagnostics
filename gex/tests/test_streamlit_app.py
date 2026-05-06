from __future__ import annotations

import matplotlib.pyplot as plt
import pytest


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


def test_plot_overview_renders():
    """DASH-04: plot_overview() returns a non-None Figure for a minimal result list."""
    from gex.analytics import plot_overview
    results = [{"ticker": "SPY", "net_gex": 1e9, "gamma_regime": "positive", "error": None}]
    fig = plot_overview(results)
    assert fig is not None
    plt.close(fig)
