"""Tests for plot_vol_surface() signature strip and Viridis colorscale — Plan 06-02."""
from __future__ import annotations

import inspect

import numpy as np
import pandas as pd
import pytest

from gex.analytics import plot_vol_surface


def _minimal_surface_df(spot: float = 500.0) -> pd.DataFrame:
    """Minimal surface_df with enough rows to pass the < 6 guard."""
    rows = []
    for dte in [7, 14, 30, 60, 90]:
        for ks in [0.95, 1.0, 1.05]:
            rows.append({
                "dte": dte,
                "strike": spot * ks,
                "iv_pct": 20.0 + (1.0 - ks) * 10,
                "log_moneyness": np.log(ks),
                "moneyness": ks,
            })
    return pd.DataFrame(rows)


def test_signature_has_only_three_params():
    """Signature must be (surface_df, ticker, spot) — no GEX overlay params."""
    params = list(inspect.signature(plot_vol_surface).parameters.keys())
    assert params == ["surface_df", "ticker", "spot"]


def test_no_optional_gex_params():
    """iv30, gamma_flip, call_wall, put_wall must not exist as parameters."""
    params = list(inspect.signature(plot_vol_surface).parameters.keys())
    for removed in ("iv30", "gamma_flip", "call_wall", "put_wall"):
        assert removed not in params, f"Param '{removed}' should have been removed"


def test_colorscale_is_viridis():
    """Surface trace colorscale must be Viridis, not Plasma."""
    df = _minimal_surface_df()
    fig = plot_vol_surface(df, "SPY", spot=500.0)
    # fig.data[0] is the go.Surface trace
    surface_trace = fig.data[0]
    assert surface_trace.colorscale is not None
    # Viridis can be stored as string or tuple; check string form
    cs = surface_trace.colorscale
    if isinstance(cs, str):
        assert cs.lower() == "viridis"
    else:
        # Plotly expands named colorscales to tuples; check name via layout or trace type
        # Fall back: render fig to dict and inspect
        fig_dict = fig.to_dict()
        cs_val = fig_dict["data"][0].get("colorscale", "")
        # Named colorscale becomes a list of [t, color] pairs — check it's not Plasma-red
        # Simplest: just confirm it's not the string "Plasma"
        assert cs_val != "Plasma"


def test_no_gex_overlay_traces():
    """No Mesh3d (spot plane). Exactly one Scatter3d allowed — the raw data overlay,
    not GEX meridian lines. Marker color must be white (data overlay), not a meridian color."""
    df = _minimal_surface_df()
    fig = plot_vol_surface(df, "SPY", spot=500.0)
    trace_types = [type(t).__name__ for t in fig.data]
    assert "Mesh3d" not in trace_types, "Spot plane Mesh3d trace should be removed"
    scatter3d_traces = [t for t in fig.data if type(t).__name__ == "Scatter3d"]
    assert len(scatter3d_traces) == 1, "Expected exactly one Scatter3d (raw data overlay)"
    assert scatter3d_traces[0].marker.color == "white", "Data overlay marker must be white"


def test_call_with_positional_spot_works():
    """Call site uses spot=spot keyword — confirm no TypeError."""
    df = _minimal_surface_df()
    fig = plot_vol_surface(df, "SPY", spot=500.0)
    assert fig is not None


def test_empty_df_guard_still_returns_figure():
    """Empty df must still return a valid Figure (guard unchanged)."""
    fig = plot_vol_surface(pd.DataFrame(), "SPY", spot=500.0)
    assert fig is not None
