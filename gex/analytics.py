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


def plot_vol_surface(surface_df: pd.DataFrame, ticker: str, spot: float,
                     iv30: float | None = None,
                     gamma_flip: float | None = None,
                     call_wall: float | None = None,
                     put_wall: float | None = None) -> go.Figure:
    """
    3D implied vol surface from the CBOE chain, OTM convention.

    Annotations overlay the GEX positioning state onto the surface so the smile
    shape can be read against where dealer exposure is concentrated:
      - translucent grey plane at spot (log(K/S) = 0)
      - meridian curves along the surface at γ-flip, call wall, put wall

    Built on linear interpolation onto a 50×40 DTE×log-moneyness grid (cubic
    produced overshoot artifacts at sparse boundaries).
    """
    import numpy as np
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

    # Defensive: compute log_moneyness on the fly if missing (handles stale
    # caches populated by an older schema).
    if "log_moneyness" not in surface_df.columns:
        surface_df = surface_df.copy()
        surface_df["log_moneyness"] = np.log(surface_df["strike"] / spot)
        surface_df["moneyness"] = surface_df["strike"] / spot

    pts = surface_df[["dte", "log_moneyness"]].to_numpy()
    vals = surface_df["iv_pct"].to_numpy()

    dte_min = max(float(surface_df["dte"].min()), 1.0)
    dte_max = min(float(surface_df["dte"].max()), 180.0)
    lm_min = float(surface_df["log_moneyness"].min())
    lm_max = float(surface_df["log_moneyness"].max())

    dte_grid = np.linspace(dte_min, dte_max, 40)
    lm_grid = np.linspace(lm_min, lm_max, 50)
    DTE, LM = np.meshgrid(dte_grid, lm_grid)

    IV = griddata(pts, vals, (DTE, LM), method="linear")
    IV_nn = griddata(pts, vals, (DTE, LM), method="nearest")
    mask = np.isnan(IV)
    IV[mask] = IV_nn[mask]

    iv_floor = float(np.nanmin(IV))
    iv_cap = float(np.nanpercentile(IV, 97))

    KS = np.exp(LM)
    STRIKE_GRID = KS * spot
    customdata = np.dstack([KS, STRIKE_GRID])

    lm_ticks = [round(np.log(k), 4) for k in (0.85, 0.90, 0.95, 1.0, 1.05, 1.10, 1.15)
                if lm_min <= np.log(k) <= lm_max]
    lm_tick_labels = [f"{k:.2f}" for k in (0.85, 0.90, 0.95, 1.0, 1.05, 1.10, 1.15)
                      if lm_min <= np.log(k) <= lm_max]

    iv30_label = f" · IV30 {iv30:.1f}%" if iv30 else ""

    fig = go.Figure(data=[go.Surface(
        x=dte_grid,
        y=lm_grid,
        z=IV,
        cmin=iv_floor,
        cmax=iv_cap,
        colorscale="Plasma",
        colorbar=dict(title="IV %", thickness=14, len=0.7, ticksuffix="%"),
        customdata=customdata,
        hovertemplate=(
            "DTE: %{x:.0f}<br>"
            "K/S: %{customdata[0]:.3f} (strike %{customdata[1]:.0f})<br>"
            "log(K/S): %{y:.3f}<br>"
            "IV: %{z:.1f}%<extra></extra>"
        ),
        contours=dict(z=dict(show=True, usecolormap=True, project_z=True,
                             highlight=False, width=2)),
        showlegend=False,
    )])

    # ── Annotations: spot plane + meridians for γ-flip / call wall / put wall ──
    def _meridian_iv(target_lm: float) -> np.ndarray:
        """IV(target_lm, dte) for each DTE in dte_grid — interpolated from the grid."""
        out = np.empty_like(dte_grid)
        for j in range(len(dte_grid)):
            out[j] = np.interp(target_lm, lm_grid, IV[:, j])
        return out

    # Translucent spot plane at log(K/S) = 0
    if lm_min <= 0 <= lm_max:
        fig.add_trace(go.Mesh3d(
            x=[dte_min, dte_max, dte_max, dte_min],
            y=[0, 0, 0, 0],
            z=[max(0, iv_floor - 2), max(0, iv_floor - 2), iv_cap, iv_cap],
            i=[0, 0],
            j=[1, 2],
            k=[2, 3],
            color="rgba(255,255,255,0.08)",
            hoverinfo="skip",
            showlegend=False,
        ))

    def _add_meridian(level: float | None, name: str, color: str,
                      dash: str | None = None) -> None:
        if level is None or level <= 0:
            return
        target_lm = float(np.log(level / spot))
        if not (lm_min <= target_lm <= lm_max):
            return
        z_vals = _meridian_iv(target_lm)
        # Slight z-offset so the line sits visibly on top of the surface
        z_lifted = np.clip(z_vals, iv_floor, iv_cap)
        fig.add_trace(go.Scatter3d(
            x=dte_grid,
            y=np.full_like(dte_grid, target_lm),
            z=z_lifted,
            mode="lines",
            line=dict(color=color, width=6, dash=dash) if dash
                 else dict(color=color, width=6),
            name=f"{name} {level:.0f}",
            hovertemplate=(
                f"{name} @ K/S=%{{y:.3f}} (strike {level:.0f})<br>"
                "DTE: %{x:.0f}<br>IV at level: %{z:.1f}%<extra></extra>"
            ),
            showlegend=True,
        ))

    _add_meridian(gamma_flip, "γ-flip", "#f59e0b", dash="dash")
    _add_meridian(call_wall, "Call Wall", "#3b82f6")
    _add_meridian(put_wall,  "Put Wall",  "#ef4444")

    fig.update_layout(
        template="plotly_dark",
        title=dict(
            text=(f"IV Surface — {ticker} "
                  f"(CBOE chain, OTM convention, log-moneyness){iv30_label}"),
            font_size=13,
        ),
        scene=dict(
            xaxis_title="DTE",
            yaxis_title="K/S  (log scale)",
            zaxis_title="IV (%)",
            camera=dict(eye=dict(x=-1.7, y=-1.7, z=1.1)),
            aspectmode="manual",
            aspectratio=dict(x=1.4, y=1.4, z=0.7),
            xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.08)"),
            yaxis=dict(
                showgrid=True,
                gridcolor="rgba(255,255,255,0.08)",
                tickmode="array",
                tickvals=lm_ticks,
                ticktext=lm_tick_labels,
            ),
            zaxis=dict(
                showgrid=True,
                gridcolor="rgba(255,255,255,0.08)",
                ticksuffix="%",
                range=[max(0, iv_floor - 2), iv_cap],
            ),
        ),
        legend=dict(orientation="h", y=1.04, x=0.5, xanchor="center",
                    bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
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


def _bar_width(gex_df: pd.DataFrame) -> float:
    strikes = sorted(gex_df["strike"].unique())
    if len(strikes) < 2:
        return 1.0
    gaps = [strikes[i + 1] - strikes[i] for i in range(min(10, len(strikes) - 1))]
    return float(np.median(gaps)) * 0.8
