"""Free-source data loader mirroring the Cron2 `con.bdh` contract.

POC scaffolding so Phase 2+ math can iterate locally without Bloomberg.
Schema parity is the contract: every panel must match the shape produced
by the Cron2/Bloomberg pull so math cells are portable verbatim.

Coverage vs Bloomberg:
    SPX:  prices, iv30_atm (VIX), iv90_atm (VIX3M), iv30_90mny (synth)
    QQQ:  prices, iv30_atm (VXN); 90d ATM and 90mny unavailable -> NaN panel
    XIU:  prices only (yfinance XIU.TO)
    XSP:  prices only (yfinance XSP.TO)
    VIX:  ^VIX
    rf:   FRED DGS3MO

iv30_90mny is synthesized as VIX + (SKEW - 100) * 0.5. Absolute level is
not Bloomberg-calibrated; signals downstream percentile-rank within
sample so monotonic shape is sufficient for POC.
"""
from __future__ import annotations

import datetime as dt
import pathlib
import warnings

import numpy as np
import pandas as pd
import pandas_datareader.data as pdr
import pandas_market_calendars as mcal
import yfinance as yf

CACHE_DIR = pathlib.Path.home() / "sleeve_alpha_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

_YF_PRICE = {
    "SPX Index":     "^GSPC",
    "QQQ US Equity": "QQQ",
    "XIU CN Equity": "XIU.TO",
    "XSP CN Equity": "XSP.TO",
}

_YF_IV = {
    ("SPX Index", "30DAY_IMPVOL_100.0%MNY_DF"): "^VIX",
    ("SPX Index", "90DAY_IMPVOL_100.0%MNY_DF"): "^VIX3M",
    ("QQQ US Equity", "30DAY_IMPVOL_100.0%MNY_DF"): "^VXN",
}

_SKEW_SLOPE = 0.5  # vol pts of OTM-put excess per 1pt of (SKEW - 100), POC calibration

_YF_CROSS = {
    "VIX Index":  "^VIX",
}

_FRED_MAP = {
    "USGG3M Index": "DGS3MO",
}


def _safe(s: str) -> str:
    return s.replace(" ", "_").replace("/", "_").replace("%", "pct").replace(".", "p")


def _cache_path(ticker: str, field: str, start: str, end: str) -> pathlib.Path:
    return CACHE_DIR / f"{_safe(ticker)}__{_safe(field)}__{start}__{end}.parquet"


def _is_stale(path: pathlib.Path, max_age_trading_days: int = 1) -> bool:
    if not path.exists():
        return True
    mtime = dt.datetime.fromtimestamp(path.stat().st_mtime).date()
    today = dt.date.today()
    if mtime >= today:
        return False
    sched = mcal.get_calendar("NYSE").schedule(start_date=mtime, end_date=today)
    return max(0, len(sched) - 1) > max_age_trading_days


def _yf_close(yf_ticker: str, start: str, end: str) -> pd.Series:
    df = yf.download(yf_ticker, start=start, end=end, progress=False, auto_adjust=True)
    if df is None or len(df) == 0:
        return pd.Series(dtype=float)
    close = df["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    close.index = pd.to_datetime(close.index).normalize()
    close.name = yf_ticker
    return close.dropna()


def _fred_series(code: str, start: str, end: str) -> pd.Series:
    df = pdr.DataReader(code, "fred", start, end)
    s = df[code]
    s.index = pd.to_datetime(s.index).normalize()
    s.name = code
    return s.dropna()


def _synth_iv30_90mny(atm_yf: str, start: str, end: str) -> pd.Series:
    """30D 90%-moneyness IV ≈ ATM IV + (SKEW - 100) * slope.

    SPX uses VIX as ATM. QQQ uses VXN as ATM with SPX SKEW reused as the
    skew shape proxy (no public NDX skew index). POC; absolute level is
    not Bloomberg-calibrated but monotonic so percentile ranks survive.
    """
    atm = _yf_close(atm_yf, start, end)
    skew = _yf_close("^SKEW", start, end)
    aligned = pd.concat({"atm": atm, "skew": skew}, axis=1).dropna()
    synth = aligned["atm"] + (aligned["skew"] - 100.0) * _SKEW_SLOPE
    synth.name = f"iv30_90mny_synth({atm_yf})"
    return synth


def _synth_iv90_atm_qqq(start: str, end: str) -> pd.Series:
    """QQQ 90D ATM IV ≈ VXN * (VIX3M / VIX). Term-structure ratio borrowed from SPX."""
    vxn = _yf_close("^VXN", start, end)
    vix = _yf_close("^VIX", start, end)
    vix3m = _yf_close("^VIX3M", start, end)
    aligned = pd.concat({"vxn": vxn, "vix": vix, "vix3m": vix3m}, axis=1).dropna()
    synth = aligned["vxn"] * (aligned["vix3m"] / aligned["vix"])
    synth.name = "iv90_atm_synth(QQQ)"
    return synth


class FreeCon:
    """`con.bdh`-shaped facade backed by free sources.

    Returns DataFrame indexed by date with a single column. Empty DataFrame
    on unsupported (ticker, field) so callers can use the same
    landed-or-deferred branching as on Cron2.
    """

    def bdh(self, ticker: str, field: str, start_date: str, end_date: str) -> pd.DataFrame:
        path = _cache_path(ticker, field, start_date, end_date)
        if not _is_stale(path):
            try:
                return pd.read_parquet(path)
            except Exception:
                pass

        try:
            series = self._dispatch(ticker, field, start_date, end_date)
        except Exception as e:
            if path.exists():
                warnings.warn(f"free source failed for {ticker}/{field} ({e}); serving cached")
                return pd.read_parquet(path)
            raise

        if series is None or len(series) == 0:
            return pd.DataFrame()

        df = series.to_frame(name=field)
        df.to_parquet(path)
        return df

    def _dispatch(self, ticker: str, field: str, start: str, end: str) -> pd.Series:
        if field == "PX_LAST":
            if ticker in _YF_PRICE:
                return _yf_close(_YF_PRICE[ticker], start, end)
            if ticker in _YF_CROSS:
                return _yf_close(_YF_CROSS[ticker], start, end)
            if ticker in _FRED_MAP:
                return _fred_series(_FRED_MAP[ticker], start, end)
            return pd.Series(dtype=float)

        key = (ticker, field)
        if key in _YF_IV:
            return _yf_close(_YF_IV[key], start, end)

        if field == "30DAY_IMPVOL_90.0%MNY_DF":
            if ticker == "SPX Index":
                return _synth_iv30_90mny("^VIX", start, end)
            if ticker == "QQQ US Equity":
                return _synth_iv30_90mny("^VXN", start, end)

        if field == "90DAY_IMPVOL_100.0%MNY_DF" and ticker == "QQQ US Equity":
            return _synth_iv90_atm_qqq(start, end)

        return pd.Series(dtype=float)


con = FreeCon()
