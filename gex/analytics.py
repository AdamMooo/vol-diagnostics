"""
Derive analytics from GEX and produce Plotly charts.

Key outputs (only the rigorously defensible ones survive):
    - net_gex: scalar total GEX at current spot
    - zero_gamma_level: spot where cumulative GEX changes sign
    - call_wall: strike with largest positive GEX (single max one-sided)
    - put_wall:  strike with largest negative GEX
    - delta_hedge_flow: |Net GEX| / spot / 0.01

No categorical regime label is produced — the $200M neutral floor was
hand-tuned and non-stationary. Sign of net_gex is the only label used
downstream (drives accent bar color in the report card).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go


def summarise(gex_df: pd.DataFrame, profile_df: pd.DataFrame,
              spot: float,
              delta_hedge_flow: float | None = None) -> dict:
    """
    gex_df: strike-level GEX DataFrame (columns: strike, gex)
    profile_df: gamma profile DataFrame (columns: spot_level, net_gex)
    spot: current underlying price
    """
    net_gex = float(gex_df["gex"].sum())
    zero_gamma = _find_zero_crossing(profile_df)

    calls = gex_df[gex_df["gex"] > 0]
    puts = gex_df[gex_df["gex"] < 0]
    call_wall = float(calls.loc[calls["gex"].idxmax(), "strike"]) if not calls.empty else None
    put_wall = float(puts.loc[puts["gex"].idxmin(), "strike"]) if not puts.empty else None

    return {
        "net_gex": net_gex,
        "zero_gamma_level": zero_gamma,
        "call_wall": call_wall,
        "put_wall": put_wall,
        "spot": spot,
        "delta_hedge_flow": delta_hedge_flow,
    }


def _find_zero_crossing(profile_df: pd.DataFrame) -> float | None:
    signs = np.sign(profile_df["net_gex"].to_numpy())
    for i in range(len(signs) - 1):
        if signs[i] != signs[i + 1]:
            x0, y0 = profile_df["spot_level"].iloc[i], profile_df["net_gex"].iloc[i]
            x1, y1 = profile_df["spot_level"].iloc[i + 1], profile_df["net_gex"].iloc[i + 1]
            return float(x0 - y0 * (x1 - x0) / (y1 - y0))
    return None


def _sign_color(net_gex: float | None) -> str:
    if net_gex is None or net_gex == 0:
        return "#64748b"
    return "#16a34a" if net_gex > 0 else "#dc2626"


def plot_strike_gex(gex_df: pd.DataFrame, spot: float, ticker: str,
                    summary: dict) -> go.Figure:
    """Interactive bar chart of GEX by strike."""
    colors = ["#3b82f6" if v >= 0 else "#ef4444" for v in gex_df["gex"]]
    width = _bar_width(gex_df)
    net_b = summary.get("net_gex", 0) / 1e9

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=gex_df["strike"],
        y=gex_df["gex"] / 1e9,
        marker_color=colors,
        marker_line_width=0,
        width=width,
        hovertemplate="Strike: %{x:.0f}<br>GEX: %{y:.3f}B<extra></extra>",
    ))

    fig.add_vline(x=spot, line_dash="dash", line_color="white", line_width=1.5,
                  annotation_text=f"Spot {spot:.0f}", annotation_position="top right",
                  annotation_font_size=11)
    if summary.get("call_wall"):
        fig.add_vline(x=summary["call_wall"], line_dash="dot", line_color="#3b82f6",
                      line_width=1, annotation_text=f"CW {summary['call_wall']:.0f}",
                      annotation_font_size=10)
    if summary.get("put_wall"):
        fig.add_vline(x=summary["put_wall"], line_dash="dot", line_color="#ef4444",
                      line_width=1, annotation_text=f"PW {summary['put_wall']:.0f}",
                      annotation_font_size=10)
    if summary.get("zero_gamma_level"):
        fig.add_vline(x=summary["zero_gamma_level"], line_color="#f59e0b", line_width=1.5,
                      annotation_text=f"ZGL {summary['zero_gamma_level']:.0f}",
                      annotation_font_size=10)

    fig.update_layout(
        template="plotly_dark",
        title=dict(text=f"{ticker}  ·  GEX by Strike  ·  Net {net_b:+.2f}B",
                   font_size=13),
        xaxis_title="Strike",
        yaxis_title="GEX ($B)",
        yaxis_ticksuffix="B",
        showlegend=False,
        height=380,
        margin=dict(t=50, b=45, l=65, r=20),
        bargap=0.05,
    )
    return fig


def plot_gamma_profile(profile_df: pd.DataFrame, spot: float, ticker: str,
                       summary: dict) -> go.Figure:
    """Interactive line chart of net GEX across spot levels."""
    x = profile_df["spot_level"]
    y = profile_df["net_gex"] / 1e9

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=y.clip(lower=0), fill="tozeroy",
        fillcolor="rgba(59,130,246,0.15)", line_color="rgba(0,0,0,0)",
        showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=y.clip(upper=0), fill="tozeroy",
        fillcolor="rgba(239,68,68,0.15)", line_color="rgba(0,0,0,0)",
        showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=y, line=dict(color="#60a5fa", width=2),
        hovertemplate="Price: %{x:.1f}<br>GEX: %{y:.3f}B<extra></extra>",
        showlegend=False,
    ))

    fig.add_hline(y=0, line_color="rgba(255,255,255,0.3)", line_width=0.8)
    fig.add_vline(x=spot, line_dash="dash", line_color="white", line_width=1.5,
                  annotation_text=f"Spot {spot:.0f}", annotation_position="top right",
                  annotation_font_size=11)
    if summary.get("zero_gamma_level"):
        fig.add_vline(x=summary["zero_gamma_level"], line_color="#f59e0b", line_width=1.5,
                      annotation_text=f"ZGL {summary['zero_gamma_level']:.0f}",
                      annotation_font_size=10)

    fig.update_layout(
        template="plotly_dark",
        title=dict(text=f"{ticker}  ·  Gamma Profile", font_size=13),
        xaxis_title="Underlying Price",
        yaxis_title="Net GEX ($B)",
        yaxis_ticksuffix="B",
        showlegend=False,
        height=300,
        margin=dict(t=50, b=45, l=65, r=20),
    )
    return fig


def plot_overview(results: list[dict]) -> go.Figure:
    """Horizontal bar chart — net GEX for all tickers. Color = sign."""
    from gex.report import TICKER_LABEL

    valid = [r for r in results if not r.get("error")]
    labels = [TICKER_LABEL.get(r["ticker"], r["ticker"]) for r in valid]
    values = [r["net_gex"] / 1e9 for r in valid]
    colors = [_sign_color(r.get("net_gex")) for r in valid]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=values,
        y=labels,
        orientation="h",
        marker_color=colors,
        marker_line_width=0,
        hovertemplate="%{y}: %{x:+.2f}B<extra></extra>",
        text=[f"{v:+.2f}B" for v in values],
        textposition="outside",
        textfont_size=10,
    ))

    fig.add_vline(x=0, line_color="rgba(255,255,255,0.25)", line_width=1)

    fig.update_layout(
        template="plotly_dark",
        title=dict(text="Cross-Asset Gamma Exposure", font_size=13),
        xaxis_title="Net GEX ($B)",
        xaxis_ticksuffix="B",
        yaxis=dict(autorange="reversed"),
        showlegend=False,
        height=max(220, len(valid) * 34 + 80),
        margin=dict(t=50, b=45, l=130, r=70),
    )
    return fig


def _bar_width(gex_df: pd.DataFrame) -> float:
    strikes = sorted(gex_df["strike"].unique())
    if len(strikes) < 2:
        return 1.0
    gaps = [strikes[i + 1] - strikes[i] for i in range(min(10, len(strikes) - 1))]
    return float(np.median(gaps)) * 0.8
