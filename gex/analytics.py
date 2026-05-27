"""
Derive analytics from GEX and produce Plotly charts.

Key outputs (only the rigorously defensible ones survive):
    - net_gex: scalar total GEX at current spot
    - zero_gamma_level: spot where cumulative GEX changes sign
    - call_wall: strike with largest positive GEX (single max one-sided)
    - put_wall:  strike with largest negative GEX
    - delta_hedge_flow: shares dealers must trade per $1 spot move (Γ_net × OI × 100)

No categorical regime label is produced — the $200M neutral floor was
hand-tuned and non-stationary. Sign of net_gex is the only label used
downstream (drives accent bar color in the report card).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from gex import config


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


def plot_vol_surface(surface_df: pd.DataFrame, ticker: str, spot: float) -> go.Figure:
    """
    3D implied vol surface from the CBOE chain, OTM convention.

    Coordinate system: x=DTE, y=% OTM (K/S−1)×100, z=IV%.
    Coarse grid (25×20); NaN left as holes where data is absent — no
    nearest-neighbour fill so the surface only exists where real quotes are.
    Raw data points overlaid as white scatter so chain density is visible.
    """
    from scipy.interpolate import griddata

    if surface_df.empty or len(surface_df) < 6:
        fig = go.Figure()
        fig.update_layout(
            template="plotly_dark",
            title=f"IV Surface — {ticker}: insufficient data",
            height=480,
            margin=dict(t=50, b=10, l=10, r=10),
        )
        return fig

    pct_otm = (surface_df["strike"].to_numpy() / spot - 1.0) * 100.0
    dte_vals = surface_df["dte"].to_numpy()
    iv_vals = surface_df["iv_pct"].to_numpy()

    pts = np.column_stack([dte_vals, pct_otm])

    dte_min = max(float(dte_vals.min()), 1.0)
    dte_max = min(float(dte_vals.max()), float(config.SURFACE_DTE_MAX))
    otm_min = float(pct_otm.min())
    otm_max = float(pct_otm.max())

    dte_grid = np.linspace(dte_min, dte_max, config.SURFACE_GRID_DTE)
    otm_grid = np.linspace(otm_min, otm_max, config.SURFACE_GRID_LM)
    DTE, OTM = np.meshgrid(dte_grid, otm_grid)

    # Linear interpolation only — NaN stays NaN where chain data is absent.
    # No nearest-neighbour fill: surface shows honest holes, not extrapolation.
    IV = griddata(pts, iv_vals, (DTE, OTM), method="linear")

    all_nan = np.all(np.isnan(IV))
    iv_floor = float(np.nanmin(IV)) if not all_nan else 0.0
    iv_cap = float(np.nanpercentile(IV, config.SURFACE_Z_CAP_PERCENTILE)) if not all_nan else 100.0

    otm_ticks = [(k - 1.0) * 100.0 for k in config.PLOT_KS_ANCHORS
                 if otm_min <= (k - 1.0) * 100.0 <= otm_max]
    otm_tick_labels = [f"{(k - 1.0) * 100:+.0f}%" for k in config.PLOT_KS_ANCHORS
                       if otm_min <= (k - 1.0) * 100.0 <= otm_max]
    dte_ticks = [d for d in config.PLOT_DTE_ANCHORS if dte_min <= d <= dte_max]

    fig = go.Figure()

    fig.add_trace(go.Surface(
        x=dte_grid,
        y=otm_grid,
        z=IV,
        cmin=iv_floor,
        cmax=iv_cap,
        colorscale="Viridis",
        colorbar=dict(title="IV %", thickness=14, len=0.7, ticksuffix="%"),
        hovertemplate=(
            "DTE: %{x:.0f}<br>"
            "% OTM: %{y:.1f}%<br>"
            "IV: %{z:.1f}%<extra></extra>"
        ),
        showlegend=False,
    ))

    fig.update_layout(
        template="plotly_dark",
        title=dict(
            text=f"IV Surface — {ticker}  (CBOE chain, OTM convention)",
            font_size=13,
        ),
        scene=dict(
            xaxis_title="DTE",
            yaxis_title="% OTM",
            zaxis_title="IV (%)",
            camera=dict(eye=dict(x=-1.7, y=-1.7, z=1.1)),
            aspectmode="manual",
            aspectratio=dict(x=1.4, y=1.4, z=0.7),
            xaxis=dict(
                showgrid=True,
                gridcolor="rgba(255,255,255,0.08)",
                tickmode="array",
                tickvals=dte_ticks,
                ticktext=[str(d) for d in dte_ticks],
                tickfont=dict(size=10),
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor="rgba(255,255,255,0.08)",
                tickmode="array",
                tickvals=otm_ticks,
                ticktext=otm_tick_labels,
            ),
            zaxis=dict(
                showgrid=True,
                gridcolor="rgba(255,255,255,0.08)",
                ticksuffix="%",
                range=[max(0, iv_floor - 2), iv_cap],
            ),
        ),
        height=540,
        margin=dict(t=50, b=10, l=10, r=10),
    )
    return fig


def plot_skew_term_structure(skew_df: pd.DataFrame, ticker: str) -> go.Figure:
    """Term structure of IV skew (25Δ put − 50Δ call) across expirations."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=skew_df["dte"], y=skew_df["skew_pp"],
        mode="lines+markers",
        line=dict(color="#f59e0b", width=2),
        marker=dict(size=6),
        hovertemplate="DTE: %{x:.0f}<br>Skew: %{y:.1f}pp<extra></extra>",
        name="Skew (25Δ put − 50Δ call)",
    ))
    fig.add_hline(y=0, line_color="rgba(255,255,255,0.2)", line_width=0.8)
    fig.update_layout(
        template="plotly_dark",
        title=dict(text=f"IV Skew Term Structure — {ticker}  ·  25Δ put − 50Δ call", font_size=13),
        xaxis_title="DTE",
        yaxis_title="Skew (pp)",
        yaxis_ticksuffix="pp",
        showlegend=False,
        height=240,
        margin=dict(t=50, b=40, l=65, r=20),
    )
    return fig


def plot_skew_25d_current(skew: dict, ticker: str) -> go.Figure:
    """Bar chart of 25Δ put-call skew for front and second month expiries.

    Args:
        skew: dict with keys "front_month" and "second_month", each either None
              or {"put_iv": float, "call_iv": float, "skew": float, "dte": float}
        ticker: underlying ticker symbol
    """
    front = skew.get("front_month")
    second = skew.get("second_month")

    if front is None and second is None:
        fig = go.Figure()
        fig.update_layout(
            template="plotly_dark",
            title=f"25Δ Put-Call Skew — {ticker}: no data",
            height=240,
            margin=dict(t=50, b=40, l=65, r=20),
        )
        return fig

    x_labels = []
    y_values = []
    if front is not None:
        x_labels.append(f"Front ({front['dte']:.0f}d)")
        y_values.append(front["skew"])
    if second is not None:
        x_labels.append(f"2nd ({second['dte']:.0f}d)")
        y_values.append(second["skew"])

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=x_labels,
        y=y_values,
        marker_color="#f59e0b",
        hovertemplate="%{x}<br>Skew: %{y:+.1f}pp<extra></extra>",
    ))
    fig.add_hline(y=0, line_color="rgba(255,255,255,0.2)", line_width=0.8)
    fig.update_layout(
        template="plotly_dark",
        title=dict(text=f"25Δ Put-Call Skew — {ticker}", font_size=13),
        yaxis_title="Skew (pp)",
        yaxis_ticksuffix="pp",
        showlegend=False,
        height=240,
        margin=dict(t=50, b=40, l=65, r=20),
    )
    return fig


def plot_term_structure(ts: dict, ticker: str) -> go.Figure:
    """ATM IV line chart with curve classification in title.

    Args:
        ts: dict with keys "points" (list of {"dte": float, "atm_iv": float})
            and "classification" (str: "normal" | "flat" | "inverted" | "humped")
        ticker: underlying ticker symbol

    CRITICAL label constraint: classification is a descriptor only — no interpretive
    suffix, no trade signals. Injected verbatim from vol_metrics.compute_term_structure().
    """
    points = ts.get("points", [])
    classification = ts.get("classification", "normal")

    if not points:
        fig = go.Figure()
        fig.update_layout(
            template="plotly_dark",
            title=f"ATM IV Term Structure — {ticker}: no data",
            height=300,
            margin=dict(t=50, b=40, l=65, r=20),
        )
        return fig

    x = [p["dte"] for p in points]
    y = [p["atm_iv"] for p in points]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x,
        y=y,
        mode="lines+markers",
        line=dict(color="#60a5fa", width=2),
        marker=dict(size=6),
        hovertemplate="DTE: %{x:.0f}<br>ATM IV: %{y:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        template="plotly_dark",
        title=dict(
            text=f"ATM IV Term Structure — {ticker}  ·  {classification}",
            font_size=13,
        ),
        xaxis_title="DTE",
        yaxis_title="ATM IV (%)",
        yaxis_ticksuffix="%",
        height=300,
        margin=dict(t=50, b=40, l=65, r=20),
    )
    return fig


def plot_carry_vrp(
    iv30_pct: float | None,
    rv20_pct: float | None,
    vrp_pp: float | None,
    ticker: str,
) -> go.Figure:
    """Grouped bar chart of IV30 vs RV20 with VRP spread in title.

    UNIT CONSTRAINT: iv30_pct must already be in percent (e.g. 18.0), rv20_pct must
    already be multiplied by 100 (e.g. 15.8), vrp_pp must already be multiplied by 100
    (e.g. 2.2). The caller (streamlit_app.py) is responsible for the conversion.
    This function does NOT convert — it renders what it receives.
    """
    fig = go.Figure()
    labels = ["IV30", "RV20"]
    values = [iv30_pct or 0.0, rv20_pct or 0.0]
    colors = ["#f59e0b", "#60a5fa"]
    fig.add_trace(go.Bar(
        x=labels,
        y=values,
        marker_color=colors,
        width=0.5,
        hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
    ))
    vrp_label = f"VRP: {vrp_pp:+.1f}pp" if vrp_pp is not None else "VRP: n/a (cold start)"
    fig.update_layout(
        template="plotly_dark",
        title=dict(
            text=f"Vol Carry / VRP — {ticker}  ·  {vrp_label}",
            font_size=13,
        ),
        yaxis_title="Vol (%)",
        yaxis_ticksuffix="%",
        showlegend=False,
        height=280,
        margin=dict(t=50, b=40, l=65, r=20),
    )
    return fig


def _bar_width(gex_df: pd.DataFrame) -> float:
    strikes = sorted(gex_df["strike"].unique())
    if len(strikes) < 2:
        return 1.0
    gaps = [strikes[i + 1] - strikes[i] for i in range(min(10, len(strikes) - 1))]
    return float(np.median(gaps)) * 0.8
