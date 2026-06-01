"""Tests for gex/png_export.py — mocked kaleido, no real disk/rendering."""
from __future__ import annotations

import datetime
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fig() -> MagicMock:
    """Return a minimal mock Plotly Figure."""
    fig = MagicMock()
    fig.write_image = MagicMock()
    fig.update_layout = MagicMock()
    return fig


_DATE = datetime.date(2026, 6, 1)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestExportPng:

    def test_export_png_returns_path_on_success(self, tmp_path: Path) -> None:
        from gex.png_export import export_png

        fig = _make_fig()
        result = export_png(fig, "SPY", "surface", _DATE, out_dir=tmp_path)

        assert isinstance(result, Path)
        assert result.name == "spy_surface_20260601.png"
        assert result.parent == tmp_path

    def test_export_png_returns_none_on_failure(self, tmp_path: Path) -> None:
        from gex.png_export import export_png

        fig = _make_fig()
        fig.write_image.side_effect = RuntimeError("kaleido not available")

        result = export_png(fig, "SPY", "surface", _DATE, out_dir=tmp_path)

        assert result is None

    def test_export_png_logs_warn_on_failure(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        from gex.png_export import export_png

        fig = _make_fig()
        fig.write_image.side_effect = RuntimeError("kaleido not available")

        export_png(fig, "SPY", "surface", _DATE, out_dir=tmp_path)

        captured = capsys.readouterr()
        assert "[WARN]" in captured.out

    def test_export_png_pins_camera(self, tmp_path: Path) -> None:
        from gex import config
        from gex.png_export import export_png

        fig = _make_fig()
        export_png(fig, "SPY", "surface", _DATE, out_dir=tmp_path)

        # update_layout must have been called with scene.camera.eye matching config
        eye = config.KALEIDO_CAMERA_EYE
        fig.update_layout.assert_called_once_with(
            scene=dict(camera=dict(eye=eye))
        )

    def test_export_png_filename_format(self, tmp_path: Path) -> None:
        from gex.png_export import export_png

        # ticker is uppercase input, filename must use lowercase
        result = export_png(_make_fig(), "QQQ", "div_surface", _DATE, out_dir=tmp_path)

        assert result is not None
        assert result.name == "qqq_div_surface_20260601.png"

    def test_export_png_creates_out_dir(self, tmp_path: Path) -> None:
        from gex.png_export import export_png

        new_dir = tmp_path / "subdir" / "output"
        assert not new_dir.exists()

        export_png(_make_fig(), "IWM", "surface", _DATE, out_dir=new_dir)

        assert new_dir.exists()
