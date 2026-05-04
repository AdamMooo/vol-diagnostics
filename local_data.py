"""Free-source data loader mirroring the Cron2 `con.bdh` contract.

POC scaffolding so Phase 2+ math can iterate locally without Bloomberg.
Schema parity is the contract: every panel must match the shape produced
by the Cron2/Bloomberg pull so math cells are portable verbatim.

Data sources — all official primary publishers, no scrapers:
    CBOE: SPX, VIX, VIX3M, VIX9D, SKEW, VXN, RUT (cdn.cboe.com)
    FRED: NASDAQ100, DGS3MO, DGS10 (St. Louis Fed)

Coverage vs Bloomberg:
    SPX:  prices, iv30_atm (VIX), iv90_atm (VIX3M), iv30_90mny (synth)
    NDX:  prices, iv30_atm (VXN); iv30_90mny synth from VXN+SKEW;
          iv90_atm synth via SPX term ratio
    VIX:  ^VIX
    rf:   FRED DGS3MO

iv30_90mny is synthesized as ATM + (SKEW - 100) * 0.5. Absolute level is
not Bloomberg-calibrated; signals downstream percentile-rank within
sample so monotonic shape is sufficient for POC.

XIU/XSP (Canadian) and VVIX deferred — no free official source. Add
back with Bloomberg or licensed feed.
"""
from __future__ import annotations

import datetime as dt
import io
import pathlib
import urllib.request
import warnings

import numpy as np
import pandas as pd
import pandas_datareader.data as pdr
import pandas_market_calendars as mcal

CACHE_DIR = pathlib.Path.home() / "sleeve_alpha_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

_CBOE_BASE = "https://cdn.cboe.com/api/global/us_indices/daily_prices/{}_History.csv"

_CBOE_SYMBOLS = {"SPX", "VIX", "VIX3M", "VIX9D", "SKEW", "VXN", "RUT"}

_PRICE_MAP = {
    "SPX Index":     ("CBOE", "SPX"),
    "NDX Index":     ("FRED", "NASDAQ100"),
}

_IV_MAP = {
    ("SPX Index", "30DAY_IMPVOL_100.0%MNY_DF"): ("CBOE", "VIX"),
    ("SPX Index", "90DAY_IMPVOL_100.0%MNY_DF"): ("CBOE", "VIX3M"),
    ("NDX Index", "30DAY_IMPVOL_100.0%MNY_DF"): ("CBOE", "VXN"),
}

_CROSS_MAP = {
    "VIX Index":   ("CBOE", "VIX"),
    "USGG3M Index": ("FRED", "DGS3MO"),
}

_SKEW_SLOPE = 0.5


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


def _fetch_cboe(symbol: str) -> pd.Series:
    url = _CBOE_BASE.format(symbol)
    req = urllib.request.Request(url, headers={"User-Agent": "options-quant-poc/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        text = resp.read().decode("utf-8", errors="replace")
    df = pd.read_csv(io.StringIO(text))
    df.columns = [c.upper().strip() for c in df.columns]
    date_col = df.columns[0]
    if "CLOSE" in df.columns:
        val = df["CLOSE"]
    elif symbol.upper() in df.columns:
        val = df[symbol.upper()]
    else:
        val = df.iloc[:, -1]
    s = pd.Series(val.values, index=pd.to_datetime(df[date_col]).values, name=symbol)
    s.index = pd.DatetimeIndex(s.index).normalize()
    return s.sort_index().dropna()


def _fetch_fred(code: str, start: str, end: str) -> pd.Series:
    df = pdr.DataReader(code, "fred", start, end)
    s = df[code]
    s.index = pd.DatetimeIndex(s.index).normalize()
    s.name = code
    return s.dropna()


def _series(provider: str, symbol: str, start: str, end: str) -> pd.Series:
    if provider == "CBOE":
        s = _fetch_cboe(symbol)
        return s.loc[(s.index >= pd.Timestamp(start)) & (s.index <= pd.Timestamp(end))]
    if provider == "FRED":
        return _fetch_fred(symbol, start, end)
    raise ValueError(f"unknown provider {provider}")


def _synth_iv30_90mny(atm_provider: str, atm_symbol: str, start: str, end: str) -> pd.Series:
    atm = _series(atm_provider, atm_symbol, start, end)
    skew = _series("CBOE", "SKEW", start, end)
    aligned = pd.concat({"atm": atm, "skew": skew}, axis=1).dropna()
    synth = aligned["atm"] + (aligned["skew"] - 100.0) * _SKEW_SLOPE
    synth.name = f"iv30_90mny_synth({atm_symbol})"
    return synth


def _synth_iv90_atm_ndx(start: str, end: str) -> pd.Series:
    vxn = _series("CBOE", "VXN", start, end)
    vix = _series("CBOE", "VIX", start, end)
    vix3m = _series("CBOE", "VIX3M", start, end)
    aligned = pd.concat({"vxn": vxn, "vix": vix, "vix3m": vix3m}, axis=1).dropna()
    synth = aligned["vxn"] * (aligned["vix3m"] / aligned["vix"])
    synth.name = "iv90_atm_synth(NDX)"
    return synth


class FreeCon:
    """`con.bdh`-shaped facade backed by free, official sources.

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
                warnings.warn(f"source failed for {ticker}/{field} ({e}); serving cached")
                return pd.read_parquet(path)
            raise

        if series is None or len(series) == 0:
            return pd.DataFrame()

        df = series.to_frame(name=field)
        df.to_parquet(path)
        return df

    def _dispatch(self, ticker: str, field: str, start: str, end: str) -> pd.Series:
        if field == "PX_LAST":
            if ticker in _PRICE_MAP:
                p, sym = _PRICE_MAP[ticker]
                return _series(p, sym, start, end)
            if ticker in _CROSS_MAP:
                p, sym = _CROSS_MAP[ticker]
                return _series(p, sym, start, end)
            return pd.Series(dtype=float)

        key = (ticker, field)
        if key in _IV_MAP:
            p, sym = _IV_MAP[key]
            return _series(p, sym, start, end)

        if field == "30DAY_IMPVOL_90.0%MNY_DF":
            if ticker == "SPX Index":
                return _synth_iv30_90mny("CBOE", "VIX", start, end)
            if ticker == "NDX Index":
                return _synth_iv30_90mny("CBOE", "VXN", start, end)

        if field == "90DAY_IMPVOL_100.0%MNY_DF" and ticker == "NDX Index":
            return _synth_iv90_atm_ndx(start, end)

        return pd.Series(dtype=float)


con = FreeCon()
