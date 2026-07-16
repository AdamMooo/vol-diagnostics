"""PNG export from Plotly figures via kaleido. Callers own failure handling — this raises."""
from __future__ import annotations

import datetime
from pathlib import Path

import plotly.graph_objects as go

from engine import config


def export_png(
    fig: go.Figure,
    ticker: str,
    surface_type: str,
    date: datetime.date,
    out_dir: Path | None = None,
) -> Path:
    """Export a Plotly figure to PNG via kaleido.

    Args:
        fig: Plotly Figure object (e.g. from plot_vol_surface or plot_iv_change_surface)
        ticker: ticker symbol ("SPY", "QQQ", "IWM")
        surface_type: short label embedded in filename ("surface", "div_surface")
        date: date embedded in filename
        out_dir: output directory; defaults to repo root / "out"

    Returns:
        Path to saved PNG.

    Raises:
        Whatever kaleido/plotly raises on export failure — callers already wrap
        each export attempt in their own try/except and track failed tickers.
    """
    out_dir = out_dir or (Path(__file__).resolve().parents[2] / "out")
    out_dir.mkdir(parents=True, exist_ok=True)

    fig.update_layout(scene=dict(camera=dict(eye=config.KALEIDO_CAMERA_EYE)))

    filename = f"{ticker.lower()}_{surface_type}_{date.strftime('%Y%m%d')}.png"
    png_path = out_dir / filename

    fig.write_image(str(png_path), format="png", scale=config.KALEIDO_SCALE_FACTOR)
    return png_path
