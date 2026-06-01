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


def rbf_grid(surface_df, spot, dte_grid, otm_grid, *,
             dte_floor=5, clip_pct=None):
    """Interpolate the OTM IV scatter onto a (DTE, %OTM) grid via TPS RBF.

    Single source of truth for the surface interpolation — consumed by plot_vol_surface,
    plot_iv_change_surface, the fit diagnostics, and (Phase 9) the evolution engine.
    Axes are std-normalized before RBF so DTE (~5-180) doesn't dominate %OTM (~±15).
    Returns IV array shaped (len(otm_grid), len(dte_grid)); NaN-filled when <6 in-band points.
    """
    from scipy.interpolate import RBFInterpolator
    if clip_pct is None:
        clip_pct = config.SURFACE_PLOT_OTM_CLIP * 100.0
    pct_otm = (surface_df["strike"].to_numpy() / spot - 1.0) * 100.0
    dte_v = surface_df["dte"].to_numpy()
    iv_v = surface_df["iv_pct"].to_numpy()
    in_band = (np.abs(pct_otm) <= clip_pct) & (dte_v >= dte_floor)
    pct_otm, dte_v, iv_v = pct_otm[in_band], dte_v[in_band], iv_v[in_band]
    if len(iv_v) < 6:
        return np.full((len(otm_grid), len(dte_grid)), np.nan)
    pts = np.column_stack([dte_v, pct_otm])
    pts_std = pts.std(axis=0)
    pts_std[pts_std < 1e-6] = 1.0
    rbf = RBFInterpolator(pts / pts_std, iv_v, kernel="thin_plate_spline",
                          smoothing=config.SURFACE_SMOOTHING)
    DTE, OTM = np.meshgrid(dte_grid, otm_grid)
    grid_pts = np.column_stack([DTE.ravel(), OTM.ravel()])
    IV = rbf(grid_pts / pts_std).reshape(DTE.shape)
    return np.clip(IV, 0.0, None)


def coverage_mask(surface_df, spot, dte_grid, otm_grid, *,
                  dte_floor=5, clip_pct=None):
    """Boolean support mask over the (DTE, %OTM) grid — True where the cell is an
    INTERPOLATION of real quotes, False where it would be EXTRAPOLATION.

    Support = inside the convex hull of the real quote locations. Interpolating between
    bracketing strikes AND between bracketing expiries is honest; only cells outside the
    quote cloud (the short/long-DTE deep-wing corners beyond the data) are fabricated and
    holed. No tunable radius — the data defines its own support, which fits the project's
    rejection of hand-tuned cutoffs. This is THE exported gate artifact: Phase 9 recomputes
    it per day and intersects two days' masks.

    (Replaced the earlier kNN-radius mask, whose isotropic radius was set by the dense
    strike spacing and so wrongly holed legitimate between-expiry interpolation — ~22%
    coverage vs ~90% here on liquid SPY/QQQ/IWM. See 08-VERIFICATION.md.)
    """
    from scipy.spatial import Delaunay, QhullError
    if clip_pct is None:
        clip_pct = config.SURFACE_PLOT_OTM_CLIP * 100.0
    pct_otm = (surface_df["strike"].to_numpy() / spot - 1.0) * 100.0
    dte_v = surface_df["dte"].to_numpy()
    in_band = (np.abs(pct_otm) <= clip_pct) & (dte_v >= dte_floor)
    pct_otm, dte_v = pct_otm[in_band], dte_v[in_band]
    n_cells = (len(otm_grid), len(dte_grid))
    # need >=6 quotes across >=2 expiries; one expiry is collinear (no 2D hull)
    if len(dte_v) < 6 or len(np.unique(dte_v)) < 2:
        return np.zeros(n_cells, dtype=bool)
    pts = np.column_stack([dte_v, pct_otm])
    pts_std = pts.std(axis=0)
    pts_std[pts_std < 1e-6] = 1.0  # per-axis scaling is affine: hull membership invariant, aids Qhull
    try:
        hull = Delaunay(pts / pts_std)
    except QhullError:
        return np.zeros(n_cells, dtype=bool)
    DTE, OTM = np.meshgrid(dte_grid, otm_grid)
    grid_norm = np.column_stack([DTE.ravel(), OTM.ravel()]) / pts_std
    return (hull.find_simplex(grid_norm) >= 0).reshape(DTE.shape)


def plot_vol_surface(surface_df: pd.DataFrame, ticker: str, spot: float) -> go.Figure:
    """
    3D implied vol surface from the CBOE chain, OTM convention.

    Coordinate system: x=DTE, y=% OTM (K/S−1)×100, z=IV%.
    Grid 40×30; RBF thin-plate-spline interpolation fills the full grid
    without NaN cliffs at convex-hull boundaries. Axes are fixed-range so
    the visual footprint is stable across sessions. DTE floor=5 suppresses
    near-expiry microstructure spikes. Colorscale: Plasma (dark=low IV,
    bright/yellow=high wing vol).
    """
    _DTE_FLOOR = 5

    def _empty(reason: str) -> go.Figure:
        fig = go.Figure()
        fig.update_layout(
            template="plotly_dark",
            title=f"IV Surface — {ticker}: {reason}",
            height=480,
            margin=dict(t=50, b=10, l=10, r=10),
        )
        return fig

    if surface_df.empty or len(surface_df) < 6:
        return _empty("insufficient data")

    clip_pct = config.SURFACE_PLOT_OTM_CLIP * 100.0

    pct_otm = (surface_df["strike"].to_numpy() / spot - 1.0) * 100.0
    dte_vals = surface_df["dte"].to_numpy()
    iv_vals = surface_df["iv_pct"].to_numpy()

    in_band = (np.abs(pct_otm) <= clip_pct) & (dte_vals >= _DTE_FLOOR)
    pct_otm = pct_otm[in_band]
    dte_vals = dte_vals[in_band]
    iv_vals = iv_vals[in_band]

    if len(iv_vals) < 6:
        return _empty("insufficient data after clip")

    dte_min = float(_DTE_FLOOR)  # pin to floor, not data minimum — fixed visual footprint
    dte_max = min(float(dte_vals.max()), float(config.SURFACE_DTE_MAX))
    if dte_max <= dte_min + 1:
        return _empty("single expiry — surface requires ≥2 expirations")

    dte_grid = np.linspace(dte_min, dte_max, config.SURFACE_GRID_DTE)
    otm_grid = np.linspace(-clip_pct, clip_pct, config.SURFACE_GRID_LM)

    # Single shared interpolation (in-band clip + std-normalization live inside rbf_grid).
    IV = rbf_grid(surface_df, spot, dte_grid, otm_grid,
                  dte_floor=_DTE_FLOOR, clip_pct=clip_pct)

    # Coverage gate (VALID-01): NaN out cells with no nearby real quote so Plotly draws
    # honest holes instead of TPS-extrapolated fabrication — the mask is the gate artifact.
    mask = coverage_mask(surface_df, spot, dte_grid, otm_grid,
                         dte_floor=_DTE_FLOOR, clip_pct=clip_pct)
    IV = np.where(mask, IV, np.nan)
    if np.isnan(IV).all():
        return _empty("no supported cells")
    coverage_pct = 100.0 * float(mask.mean())
    n_clipped = int((IV[~np.isnan(IV)] == 0.0).sum())  # supported cells the >=0 clip pinned to 0
    print(f"[surface] {ticker}: coverage {coverage_pct:.0f}%  zero-clipped cells {n_clipped}")

    iv_floor = float(np.nanmin(IV))
    iv_cap = float(np.nanpercentile(IV, config.SURFACE_Z_CAP_PERCENTILE))

    otm_ticks = [(k - 1.0) * 100.0 for k in config.PLOT_KS_ANCHORS
                 if -clip_pct <= (k - 1.0) * 100.0 <= clip_pct]
    otm_tick_labels = [f"{(k - 1.0) * 100:+.0f}%" for k in config.PLOT_KS_ANCHORS
                       if -clip_pct <= (k - 1.0) * 100.0 <= clip_pct]
    dte_ticks = [d for d in config.PLOT_DTE_ANCHORS if dte_min <= d <= dte_max]

    fig = go.Figure()

    fig.add_trace(go.Surface(
        x=dte_grid,
        y=otm_grid,
        z=IV,
        cmin=iv_floor,
        cmax=iv_cap,
        colorscale="Plasma",
        colorbar=dict(title="IV %", thickness=14, len=0.65, ticksuffix="%"),
        lighting=dict(
            ambient=0.7,
            diffuse=0.6,
            specular=0.2,
            roughness=0.45,
            fresnel=0.2,
        ),
        contours=dict(
            z=dict(show=True, usecolormap=True, highlightcolor="white",
                   project_z=True, width=1),
        ),
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
            camera=dict(eye=dict(x=2.0, y=-1.2, z=0.8)),
            aspectmode="manual",
            aspectratio=dict(x=1.5, y=1.2, z=0.6),
            xaxis=dict(
                showgrid=True,
                gridcolor="rgba(255,255,255,0.06)",
                tickmode="array",
                tickvals=dte_ticks,
                ticktext=[str(d) for d in dte_ticks],
                tickfont=dict(size=10),
                range=[dte_min, dte_max],
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor="rgba(255,255,255,0.06)",
                tickmode="array",
                tickvals=otm_ticks,
                ticktext=otm_tick_labels,
                range=[-clip_pct, clip_pct],
            ),
            zaxis=dict(
                showgrid=True,
                gridcolor="rgba(255,255,255,0.06)",
                ticksuffix="%",
                range=[max(0, iv_floor - 2), iv_cap],
            ),
        ),
        height=540,
        margin=dict(t=50, b=10, l=10, r=10),
    )
    return fig


def plot_iv_change_surface(
    df_today: pd.DataFrame,
    df_prior: pd.DataFrame,
    ticker: str,
    spot_today: float,
    spot_prior: float,
    label_prior: str,
) -> go.Figure:
    """
    ∆IV surface: IV_today − IV_prior on a common fixed % OTM / DTE grid.

    Both surfaces are interpolated independently with RBF on the same grid,
    then differenced. Colorscale RdBu_r centred at 0 — red = vol up,
    blue = vol down. Each day's strikes are normalised by that day's spot
    so the % OTM axis is comparable across sessions.
    """
    _DTE_FLOOR = 5

    def _empty(reason: str) -> go.Figure:
        fig = go.Figure()
        fig.update_layout(
            template="plotly_dark",
            title=f"∆IV Surface — {ticker}: {reason}",
            height=480,
            margin=dict(t=50, b=10, l=10, r=10),
        )
        return fig

    if df_today.empty or df_prior.empty:
        return _empty("missing data for one or both dates")

    clip_pct = config.SURFACE_PLOT_OTM_CLIP * 100.0

    # Shared grid bounded by the intersection of both datasets
    dte_min = max(float(df_today["dte"].min()), float(df_prior["dte"].min()), float(_DTE_FLOOR))
    dte_max = min(
        min(float(df_today["dte"].max()), float(df_prior["dte"].max())),
        float(config.SURFACE_DTE_MAX),
    )
    if dte_min >= dte_max:
        return _empty("DTE ranges do not overlap")

    dte_grid = np.linspace(dte_min, dte_max, config.SURFACE_GRID_DTE)
    otm_grid = np.linspace(-clip_pct, clip_pct, config.SURFACE_GRID_LM)

    IV_today = rbf_grid(df_today, spot_today, dte_grid, otm_grid,
                        dte_floor=_DTE_FLOOR, clip_pct=clip_pct)
    IV_prior = rbf_grid(df_prior, spot_prior, dte_grid, otm_grid,
                        dte_floor=_DTE_FLOOR, clip_pct=clip_pct)
    IV_diff = IV_today - IV_prior

    abs_max = float(np.nanpercentile(np.abs(IV_diff), 97)) if not np.all(np.isnan(IV_diff)) else 1.0
    if abs_max < 0.5:
        abs_max = 0.5  # keep scale readable when vol barely moved

    otm_ticks = [(k - 1.0) * 100.0 for k in config.PLOT_KS_ANCHORS
                 if -clip_pct <= (k - 1.0) * 100.0 <= clip_pct]
    otm_tick_labels = [f"{(k - 1.0) * 100:+.0f}%" for k in config.PLOT_KS_ANCHORS
                       if -clip_pct <= (k - 1.0) * 100.0 <= clip_pct]
    dte_ticks = [d for d in config.PLOT_DTE_ANCHORS if dte_min <= d <= dte_max]

    fig = go.Figure()
    fig.add_trace(go.Surface(
        x=dte_grid,
        y=otm_grid,
        z=IV_diff,
        cmin=-abs_max,
        cmax=abs_max,
        colorscale="RdBu_r",
        colorbar=dict(title="∆IV (pp)", thickness=14, len=0.65, ticksuffix="pp"),
        lighting=dict(ambient=0.7, diffuse=0.6, specular=0.2, roughness=0.45, fresnel=0.2),
        contours=dict(
            z=dict(show=True, usecolormap=True, highlightcolor="white",
                   project_z=True, width=1),
        ),
        hovertemplate=(
            "DTE: %{x:.0f}<br>"
            "% OTM: %{y:.1f}%<br>"
            "∆IV: %{z:+.1f}pp<extra></extra>"
        ),
        showlegend=False,
    ))

    fig.update_layout(
        template="plotly_dark",
        title=dict(
            text=f"∆IV Surface — {ticker}  (today − {label_prior})",
            font_size=13,
        ),
        scene=dict(
            xaxis_title="DTE",
            yaxis_title="% OTM",
            zaxis_title="∆IV (pp)",
            camera=dict(eye=dict(x=2.0, y=-1.2, z=0.8)),
            aspectmode="manual",
            aspectratio=dict(x=1.5, y=1.2, z=0.6),
            xaxis=dict(
                showgrid=True, gridcolor="rgba(255,255,255,0.06)",
                tickmode="array", tickvals=dte_ticks,
                ticktext=[str(d) for d in dte_ticks],
                tickfont=dict(size=10), range=[dte_min, dte_max],
            ),
            yaxis=dict(
                showgrid=True, gridcolor="rgba(255,255,255,0.06)",
                tickmode="array", tickvals=otm_ticks, ticktext=otm_tick_labels,
                range=[-clip_pct, clip_pct],
            ),
            zaxis=dict(
                showgrid=True, gridcolor="rgba(255,255,255,0.06)",
                ticksuffix="pp", range=[-abs_max, abs_max],
            ),
        ),
        height=540,
        margin=dict(t=50, b=10, l=10, r=10),
    )
    return fig


def plot_oi_by_strike(chain_df: pd.DataFrame, spot: float, ticker: str,
                      summary: dict) -> go.Figure:
    """Bar chart of open interest by strike — assumption-free observable.

    chain_df: strike-level DataFrame. Preferred columns: call_oi, put_oi (split by
    side). Falls back to total 'oi' column (neutral color). If neither is present,
    uses abs(gex) as a proportional proxy — see comment below.
    summary: dict from summarise() — used for call_wall, put_wall annotations.
    """
    width = _bar_width(chain_df)

    fig = go.Figure()

    if "call_oi" in chain_df.columns and "put_oi" in chain_df.columns:
        fig.add_trace(go.Bar(
            x=chain_df["strike"],
            y=chain_df["call_oi"],
            name="Call OI",
            marker_color=config.PALETTE["call"],
            marker_line_width=0,
            opacity=0.65,
            width=width,
            hovertemplate="Strike: %{x:.0f}<br>Call OI: %{y:,.0f}<extra></extra>",
        ))
        fig.add_trace(go.Bar(
            x=chain_df["strike"],
            y=chain_df["put_oi"],
            name="Put OI",
            marker_color=config.PALETTE["put"],
            marker_line_width=0,
            opacity=0.65,
            width=width,
            hovertemplate="Strike: %{x:.0f}<br>Put OI: %{y:,.0f}<extra></extra>",
        ))
        fig.update_layout(barmode="overlay", showlegend=True)
    elif "oi" in chain_df.columns:
        fig.add_trace(go.Bar(
            x=chain_df["strike"],
            y=chain_df["oi"],
            marker_color=config.PALETTE["neutral"],
            marker_line_width=0,
            width=width,
            hovertemplate="Strike: %{x:.0f}<br>OI: %{y:,.0f}<extra></extra>",
        ))
        fig.update_layout(showlegend=False)
    else:
        # oi column absent — use abs(gex) as a proportional stand-in for OI shape;
        # this is approximate (GEX folds in gamma and spot^2) but preserves the
        # visual pattern until a split-OI column is wired in.
        from gex.exposure_engine import MULTIPLIER
        proxy = chain_df["gex"].abs()
        fig.add_trace(go.Bar(
            x=chain_df["strike"],
            y=proxy,
            marker_color=config.PALETTE["neutral"],
            marker_line_width=0,
            width=width,
            hovertemplate="Strike: %{x:.0f}<br>|GEX| proxy: %{y:.3f}B<extra></extra>",
        ))
        fig.update_layout(showlegend=False)

    fig.add_vline(x=spot, line_dash="dash", line_color="white", line_width=1.5,
                  annotation_text=f"Spot {spot:.0f}", annotation_position="top right",
                  annotation_font_size=11)
    if summary.get("call_wall"):
        fig.add_vline(x=summary["call_wall"], line_dash="dot",
                      line_color=config.PALETTE["call"], line_width=1,
                      annotation_text=f"call wall · model {summary['call_wall']:.0f}",
                      annotation_font_size=10)
    if summary.get("put_wall"):
        fig.add_vline(x=summary["put_wall"], line_dash="dot",
                      line_color=config.PALETTE["put"], line_width=1,
                      annotation_text=f"put wall · model {summary['put_wall']:.0f}",
                      annotation_font_size=10)

    fig.update_layout(
        template="plotly_dark",
        title=dict(text=f"{ticker}  ·  OI by Strike", font_size=13),
        xaxis_title="Strike",
        yaxis_title="OI (contracts)",
        height=380,
        margin=dict(t=50, b=45, l=65, r=20),
        bargap=0.05,
    )
    return fig


def _bar_width(gex_df: pd.DataFrame) -> float:
    strikes = sorted(gex_df["strike"].unique())
    if len(strikes) < 2:
        return 1.0
    gaps = [strikes[i + 1] - strikes[i] for i in range(min(10, len(strikes) - 1))]
    return float(np.median(gaps)) * 0.8
