"""Smoke tests for Phase 7 chart functions — verify each returns go.Figure without error."""
import plotly.graph_objects as go
import pytest

from gex.analytics import plot_carry_vrp, plot_skew_25d_current, plot_term_structure


@pytest.fixture
def skew_dict():
    return {
        "front_month": {"put_iv": 22.0, "call_iv": 18.0, "skew": 4.0, "dte": 32.0},
        "second_month": {"put_iv": 21.0, "call_iv": 17.0, "skew": 4.0, "dte": 62.0},
    }


@pytest.fixture
def term_structure_dict():
    return {
        "points": [{"dte": 30.0, "atm_iv": 18.0}, {"dte": 60.0, "atm_iv": 20.0}],
        "classification": "normal",
        "front_atm_iv": 18.0,
        "back_atm_iv": 20.0,
    }


def test_plot_skew_25d_current_returns_figure(skew_dict):
    fig = plot_skew_25d_current(skew_dict, "SPY")
    assert isinstance(fig, go.Figure)


def test_plot_skew_25d_current_none_buckets():
    fig = plot_skew_25d_current({"front_month": None, "second_month": None}, "SPY")
    assert isinstance(fig, go.Figure)


def test_plot_term_structure_returns_figure(term_structure_dict):
    fig = plot_term_structure(term_structure_dict, "SPY")
    assert isinstance(fig, go.Figure)


def test_plot_term_structure_empty_points():
    fig = plot_term_structure({"points": [], "classification": "normal"}, "SPY")
    assert isinstance(fig, go.Figure)


def test_plot_carry_vrp_returns_figure():
    fig = plot_carry_vrp(18.0, 15.8, 2.2, "SPY")
    assert isinstance(fig, go.Figure)


def test_plot_carry_vrp_cold_start_none():
    fig = plot_carry_vrp(None, None, None, "SPY")
    assert isinstance(fig, go.Figure)
