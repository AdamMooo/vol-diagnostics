"""Behavioral tests for 1-day ΔIV PNG attachment logic in run_daily.py.

Tests target gex.run_daily._build_png_attachments — a private function extracted
from the PNG generation block. All external calls are mocked at the run_daily
module level (from-import creates direct references).
"""
from __future__ import annotations

import datetime
import pathlib
from unittest.mock import MagicMock, call, patch

import pandas as pd
import pytest

# Defined here to avoid importing gex.run_daily at module level (which would bleed
# gex.emailer into sys.modules and break test_import_no_emailer_bleed isolation).
INDEX_TICKERS = ["SPY", "QQQ", "IWM"]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_TODAY = datetime.date(2026, 6, 1)
_PRIOR_SPY = datetime.date(2026, 5, 30)
_PRIOR_QQQ = datetime.date(2026, 5, 30)
_PRIOR_IWM = datetime.date(2026, 5, 30)

_SURFACE_DF = pd.DataFrame({
    "dte": [30.0],
    "strike": [500.0],
    "moneyness": [1.0],
    "log_moneyness": [0.0],
    "iv_pct": [20.0],
})


def _make_all_data() -> list[dict]:
    return [
        {
            "summary": {"ticker": t, "spot": 500.0},
            "surface_df": _SURFACE_DF.copy(),
        }
        for t in INDEX_TICKERS
    ]


def _mock_fig() -> MagicMock:
    fig = MagicMock()
    fig.update_layout = MagicMock()
    fig.write_image = MagicMock()
    return fig


# ---------------------------------------------------------------------------
# TestOneDayDeltaIVPngs
# ---------------------------------------------------------------------------

class TestOneDayDeltaIVPngs:

    def test_three_tickers_attach(self, tmp_path: pathlib.Path) -> None:
        """All 3 tickers produce PNGs when prior snapshots exist."""
        from gex.run_daily import _build_png_attachments

        prior_dates = {t: _PRIOR_SPY for t in INDEX_TICKERS}

        with (
            patch("gex.run_daily.nth_trading_day_back", side_effect=lambda t, d, n: prior_dates[t]),
            patch("gex.run_daily.load_surface_snapshot", return_value=(_SURFACE_DF.copy(), 495.0)),
            patch("gex.run_daily.plot_iv_change_heatmap", return_value=_mock_fig()) as mock_plot,
            patch("gex.run_daily.export_png", return_value=tmp_path / "out.png") as mock_export,
        ):
            attachments = _build_png_attachments(_make_all_data(), _TODAY, tmp_path)

        assert mock_export.call_count == 3
        assert len(attachments) == 3

    def test_missing_prior_snapshot_skips_ticker(self, tmp_path: pathlib.Path) -> None:
        """QQQ skipped when nth_trading_day_back returns None for it."""
        from gex.run_daily import _build_png_attachments

        def _nth(ticker, date, n):
            return None if ticker == "QQQ" else _PRIOR_SPY

        spy_png = tmp_path / "spy.png"
        iwm_png = tmp_path / "iwm.png"

        def _export(fig, ticker, surface_type, date, out_dir=None):
            return spy_png if ticker == "SPY" else iwm_png

        with (
            patch("gex.run_daily.nth_trading_day_back", side_effect=_nth),
            patch("gex.run_daily.load_surface_snapshot", return_value=(_SURFACE_DF.copy(), 495.0)),
            patch("gex.run_daily.plot_iv_change_heatmap", return_value=_mock_fig()),
            patch("gex.run_daily.export_png", side_effect=_export) as mock_export,
        ):
            attachments = _build_png_attachments(_make_all_data(), _TODAY, tmp_path)

        called_tickers = [c.args[1] for c in mock_export.call_args_list]
        assert "SPY" in called_tickers
        assert "IWM" in called_tickers
        assert "QQQ" not in called_tickers
        assert len(attachments) == 2

    def test_empty_prior_df_skips_ticker(self, tmp_path: pathlib.Path) -> None:
        """Ticker skipped when load_surface_snapshot returns empty DataFrame."""
        from gex.run_daily import _build_png_attachments

        def _load(ticker, date):
            if ticker == "IWM":
                return pd.DataFrame(), None
            return _SURFACE_DF.copy(), 495.0

        with (
            patch("gex.run_daily.nth_trading_day_back", return_value=_PRIOR_SPY),
            patch("gex.run_daily.load_surface_snapshot", side_effect=_load),
            patch("gex.run_daily.plot_iv_change_heatmap", return_value=_mock_fig()),
            patch("gex.run_daily.export_png", return_value=tmp_path / "out.png") as mock_export,
        ):
            attachments = _build_png_attachments(_make_all_data(), _TODAY, tmp_path)

        called_tickers = [c.args[1] for c in mock_export.call_args_list]
        assert "IWM" not in called_tickers
        assert mock_export.call_count == 2

    def test_export_png_failure_non_blocking(self, tmp_path: pathlib.Path) -> None:
        """When export_png returns None for one ticker, others still attach."""
        from gex.run_daily import _build_png_attachments

        call_count = {"n": 0}

        def _export(fig, ticker, surface_type, date, out_dir=None):
            call_count["n"] += 1
            return None if ticker == "QQQ" else tmp_path / f"{ticker}.png"

        with (
            patch("gex.run_daily.nth_trading_day_back", return_value=_PRIOR_SPY),
            patch("gex.run_daily.load_surface_snapshot", return_value=(_SURFACE_DF.copy(), 495.0)),
            patch("gex.run_daily.plot_iv_change_heatmap", return_value=_mock_fig()),
            patch("gex.run_daily.export_png", side_effect=_export),
        ):
            attachments = _build_png_attachments(_make_all_data(), _TODAY, tmp_path)

        assert None not in attachments
        assert len(attachments) == 2

    def test_label_prior_format(self, tmp_path: pathlib.Path) -> None:
        """plot_iv_change_heatmap is called with label_prior='May 30'."""
        from gex.run_daily import _build_png_attachments

        prior_date = datetime.date(2026, 5, 30)

        with (
            patch("gex.run_daily.nth_trading_day_back", return_value=prior_date),
            patch("gex.run_daily.load_surface_snapshot", return_value=(_SURFACE_DF.copy(), 495.0)),
            patch("gex.run_daily.plot_iv_change_heatmap", return_value=_mock_fig()) as mock_plot,
            patch("gex.run_daily.export_png", return_value=tmp_path / "out.png"),
        ):
            _build_png_attachments(_make_all_data(), _TODAY, tmp_path)

        for c in mock_plot.call_args_list:
            kwargs = c.kwargs
            label = kwargs.get("label_prior") or (c.args[5] if len(c.args) > 5 else None)
            assert label == "May 30", f"expected 'May 30', got {label!r}"

    def test_surface_type_is_div_surface(self, tmp_path: pathlib.Path) -> None:
        """export_png is called with surface_type='div_surface' for each ticker."""
        from gex.run_daily import _build_png_attachments

        with (
            patch("gex.run_daily.nth_trading_day_back", return_value=_PRIOR_SPY),
            patch("gex.run_daily.load_surface_snapshot", return_value=(_SURFACE_DF.copy(), 495.0)),
            patch("gex.run_daily.plot_iv_change_heatmap", return_value=_mock_fig()),
            patch("gex.run_daily.export_png", return_value=tmp_path / "out.png") as mock_export,
        ):
            _build_png_attachments(_make_all_data(), _TODAY, tmp_path)

        for c in mock_export.call_args_list:
            surface_type = c.args[2] if len(c.args) > 2 else c.kwargs.get("surface_type")
            assert surface_type == "div_surface"

    def test_evolution_store_untouched(self) -> None:
        """The PNG block in run_daily.py must not call update_evolution."""
        src = (pathlib.Path(__file__).resolve().parent.parent / "run_daily.py").read_text(encoding="utf-8")
        # Find the PNG block: from the "Generate PNG attachments" comment to
        # the print statement showing attachment count.
        start = src.find("# Generate PNG attachments")
        end = src.find('print(f"[run_daily]', start)
        assert start != -1, "PNG block start comment not found in run_daily.py"
        assert end != -1, "PNG block end print not found in run_daily.py"
        png_block = src[start:end]
        assert "update_evolution" not in png_block, (
            "PNG block must not call update_evolution — evolution engine must stay untouched"
        )
