"""Per-metric history loader dispatch for the severity ranker.

load_metric_series(ticker, metric_name) returns a date-indexed ascending pd.Series
(NaNs dropped) or None -- never raises. One branch per metric_name in
schema.METRIC_INVENTORY's metric-name set. Reuses existing store readers
(validation.py, surface_evolution.py, vol_index.py) and vrp_history.vrp_history_series
-- never re-derives a metric from scratch.
"""
from __future__ import annotations

import pandas as pd

from engine import config
from engine.data.validation import STORE as _GEX_SNAPSHOTS_STORE
from engine.data.vol_index import load_vol_index
from engine.surface.surface_evolution import STORE as _SURFACE_EVOLUTION_STORE
from engine.vol import vrp_history
from engine.vol.vol_metrics import _TERM_SYMBOLS


def _load_gex_snapshots() -> pd.DataFrame:
    if not _GEX_SNAPSHOTS_STORE.exists():
        return pd.DataFrame()
    try:
        return pd.read_parquet(_GEX_SNAPSHOTS_STORE)
    except Exception as exc:
        print(f"[monitor.metrics] _load_gex_snapshots failed: {exc}")
        return pd.DataFrame()


def _load_surface_evolution() -> pd.DataFrame:
    if not _SURFACE_EVOLUTION_STORE.exists():
        return pd.DataFrame()
    try:
        return pd.read_parquet(_SURFACE_EVOLUTION_STORE)
    except Exception as exc:
        print(f"[monitor.metrics] _load_surface_evolution failed: {exc}")
        return pd.DataFrame()


def _gex_snapshot_column(ticker: str, column: str) -> "pd.Series | None":
    try:
        df = _load_gex_snapshots()
        if df.empty or column not in df.columns:
            return None
        df = df[df["ticker"] == ticker].copy()
        if df.empty:
            return None
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df = df.sort_values("date")
        series = df.set_index("date")[column].dropna()
        return series if not series.empty else None
    except Exception as exc:
        print(f"[monitor.metrics] _gex_snapshot_column({ticker}, {column}) failed: {exc}")
        return None


def _evolution_column(ticker: str, column: str, horizon: int) -> "pd.Series | None":
    try:
        df = _load_surface_evolution()
        if df.empty or column not in df.columns:
            return None
        df = df[(df["ticker"] == ticker) & (df["horizon"] == horizon)].copy()
        if df.empty:
            return None
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df = df.sort_values("date")
        series = df.set_index("date")[column].dropna()
        return series if not series.empty else None
    except Exception as exc:
        print(f"[monitor.metrics] _evolution_column({ticker}, {column}) failed: {exc}")
        return None


def _term_ratio_series(ticker: str, leg: str) -> "pd.Series | None":
    try:
        symbols = _TERM_SYMBOLS.get(ticker)
        if symbols is None:
            return None
        sym_9d, sym_30d, sym_3m = symbols

        if leg == "term_9d_30":
            num_sym, den_sym = sym_9d, sym_30d
        else:
            num_sym, den_sym = sym_30d, sym_3m

        num_df = load_vol_index(num_sym)
        den_df = load_vol_index(den_sym)
        if num_df.empty or den_df.empty:
            return None

        num = num_df.set_index("date")["close"]
        den = den_df.set_index("date")["close"]
        aligned = pd.DataFrame({"num": num, "den": den}).dropna()
        if aligned.empty:
            return None

        ratio = (aligned["num"] / aligned["den"]).sort_index()
        return ratio if not ratio.empty else None
    except Exception as exc:
        print(f"[monitor.metrics] _term_ratio_series({ticker}, {leg}) failed: {exc}")
        return None


def load_metric_series(ticker: str, metric_name: str) -> "pd.Series | None":
    """Dispatch on metric_name -> date-indexed ascending pd.Series or None.

    Never raises. Unknown metric_name or any I/O failure returns None.
    """
    try:
        if metric_name == "vrp":
            return vrp_history.vrp_history_series(ticker)
        if metric_name == "skew_25d":
            return _gex_snapshot_column(ticker, "front_skew")
        if metric_name == "fly_25d":
            return _gex_snapshot_column(ticker, "butterfly")
        if metric_name == "surface_level":
            return _evolution_column(ticker, "level", config.MONITOR_CHANGE_K_SESSIONS)
        if metric_name == "surface_rms":
            return _evolution_column(ticker, "rms", config.MONITOR_CHANGE_K_SESSIONS)
        if metric_name in ("term_9d_30", "term_30_3m"):
            return _term_ratio_series(ticker, metric_name)
        return None
    except Exception as exc:
        print(f"[monitor.metrics] load_metric_series({ticker}, {metric_name}) failed: {exc}")
        return None
