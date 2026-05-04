"""Phase 1 — build canonical panels from local_data.con.

Produces the same identifier set as the Cron2 contract so math layers
port back verbatim:

    prices_panel, iv_panel, iv90_panel, iv90mny, skew_panel  (DataFrames)
    vix, rf_rate                                              (Series)

All on NYSE_INDEX, truncated to the shortest IV history per underlying.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import numpy as np
import pandas as pd
import pandas_market_calendars as mcal

from local_data import con

UNDERLYINGS = {
    "SPX": "SPX Index",
    "NDX": "NDX Index",
}

IV_FIELDS = {
    "iv30_atm":   "30DAY_IMPVOL_100.0%MNY_DF",
    "iv30_90mny": "30DAY_IMPVOL_90.0%MNY_DF",
    "iv90_atm":   "90DAY_IMPVOL_100.0%MNY_DF",
}

CROSS_ASSET = {
    "vix":     ("VIX Index",     "PX_LAST"),
    "rf_rate": ("USGG3M Index",  "PX_LAST"),
}


def nyse_index(start: str, end: str) -> pd.DatetimeIndex:
    sched = mcal.get_calendar("NYSE").schedule(start_date=start, end_date=end)
    return pd.DatetimeIndex(sched.index).normalize()


def _to_series(df: pd.DataFrame, name: str) -> pd.Series | None:
    if df is None or len(df) == 0:
        return None
    s = df.squeeze()
    if isinstance(s, pd.DataFrame):
        s = s.iloc[:, 0]
    s.index = pd.DatetimeIndex(s.index).normalize()
    s.name = name
    return s


@dataclass
class Panels:
    nyse_index: pd.DatetimeIndex
    truncate_start: pd.Timestamp
    landed: list[str]
    prices_panel: pd.DataFrame
    iv_panel: pd.DataFrame
    iv90_panel: pd.DataFrame
    iv90mny: pd.DataFrame
    skew_panel: pd.DataFrame
    vix: pd.Series
    rf_rate: pd.Series

    def shape_summary(self) -> pd.DataFrame:
        return pd.DataFrame({
            "prices_panel": self.prices_panel.notna().sum(),
            "iv_panel":     self.iv_panel.reindex(columns=self.prices_panel.columns).notna().sum(),
            "iv90_panel":   self.iv90_panel.reindex(columns=self.prices_panel.columns).notna().sum(),
            "skew_panel":   self.skew_panel.reindex(columns=self.prices_panel.columns).notna().sum(),
        }).T


def build_panels(start: str = "2010-01-01", end: str | None = None) -> Panels:
    if end is None:
        end = dt.date.today().isoformat()

    NYSE = nyse_index(start, end)

    raw_pulls: dict[str, dict[str, pd.DataFrame]] = {u: {} for u in UNDERLYINGS}
    for u, ticker in UNDERLYINGS.items():
        raw_pulls[u]["price"] = con.bdh(ticker, "PX_LAST", start, end)
        for fkey, fname in IV_FIELDS.items():
            raw_pulls[u][fkey] = con.bdh(ticker, fname, start, end)

    raw_cross: dict[str, pd.DataFrame] = {}
    for name, (ticker, field) in CROSS_ASSET.items():
        raw_cross[name] = con.bdh(ticker, field, start, end)

    def _panel(field_key: str, names: list[str]) -> pd.DataFrame:
        cols = {}
        for u in names:
            s = _to_series(raw_pulls[u][field_key], u)
            if s is not None:
                cols[u] = s.reindex(NYSE)
        return pd.DataFrame(cols, index=NYSE)

    landed = [
        u for u in UNDERLYINGS
        if len(raw_pulls[u].get("price", pd.DataFrame())) > 0
        and len(raw_pulls[u].get("iv30_atm", pd.DataFrame())) > 0
        and len(raw_pulls[u].get("iv30_90mny", pd.DataFrame())) > 0
    ]

    prices_full = _panel("price",      list(UNDERLYINGS))
    iv_full     = _panel("iv30_atm",   landed)
    iv90mny_f   = _panel("iv30_90mny", landed)
    iv90_full   = _panel(
        "iv90_atm",
        [u for u in landed if len(raw_pulls[u].get("iv90_atm", pd.DataFrame())) > 0],
    )

    iv_first = []
    for u in landed:
        s = iv_full[u].dropna()
        if len(s):
            iv_first.append(s.index.min())
    truncate_start = max(iv_first) if iv_first else NYSE.min()

    mask = NYSE >= truncate_start
    prices_panel = prices_full.loc[mask].copy()
    iv_panel     = iv_full.loc[mask].copy()
    iv90mny      = iv90mny_f.loc[mask].copy()
    iv90_panel   = iv90_full.loc[mask].copy()

    common = [c for c in iv_panel.columns if c in iv90mny.columns]
    skew_panel = iv90mny[common] - iv_panel[common]

    def _named_series(name: str) -> pd.Series:
        df = raw_cross.get(name, pd.DataFrame())
        if df is None or len(df) == 0:
            s = pd.Series(index=NYSE, dtype="float64", name=name)
        else:
            s = df.squeeze()
            if isinstance(s, pd.DataFrame):
                s = s.iloc[:, 0]
            s.index = pd.DatetimeIndex(s.index).normalize()
            s.name = name
            s = s.reindex(NYSE)
        return s.loc[NYSE >= truncate_start]

    vix     = _named_series("vix")
    rf_rate = _named_series("rf_rate")

    for s in (vix, rf_rate):
        assert s.index.equals(prices_panel.index), f"{s.name} index mismatch"

    return Panels(
        nyse_index=NYSE,
        truncate_start=truncate_start,
        landed=landed,
        prices_panel=prices_panel,
        iv_panel=iv_panel,
        iv90_panel=iv90_panel,
        iv90mny=iv90mny,
        skew_panel=skew_panel,
        vix=vix,
        rf_rate=rf_rate,
    )
