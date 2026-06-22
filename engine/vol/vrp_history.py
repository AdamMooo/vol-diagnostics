"""VRP-percentile engine — builds one internally-consistent, VRP-03-clean series.

The percentile is computed from `vol_index_close − RV20×100` (vol points) at every
aligned historical date. The CBOE-IV30 `vrp` column from the stored options payload is
NEVER read here — mixing it into the history is the VRP-03 violation this module exists
to prevent. Today's value fed to percentileofscore is the last point of that same series,
so the scalar and its rank share one definition and cannot drift.

Composes existing isolated accessors: load_vol_index (CBOE parquet store) and compute_rv20
(pure). The only network I/O is _fetch_closes_yf, isolated like compute._fetch_spot_history_yf.
"""
from __future__ import annotations

import pandas as pd
from scipy.stats import percentileofscore

from engine import config
from engine.data.vol_index import load_vol_index
from engine.vol.vol_metrics import compute_rv20


def _fetch_closes_yf(ticker: str, period: str = "400d") -> "pd.Series | None":
    """Daily closes from yfinance, date-indexed oldest-first. None on any failure; never raises.

    Mirrors compute._fetch_spot_history_yf but returns a date-indexed Series over a wider
    window so a rolling RV20 history can be aligned to the vol-index dates by date.
    """
    try:
        import yfinance as yf
        yf_ticker = ticker.replace(".", "-")
        hist = yf.Ticker(yf_ticker).history(period=period)
        if hist.empty or "Close" not in hist.columns:
            return None
        closes = hist["Close"].dropna()
        if len(closes) < 21:
            return None
        closes.index = pd.to_datetime(closes.index).date
        closes.index.name = "date"
        return closes.sort_index()
    except Exception as exc:
        print(f"[vrp_history] yf history failed for {ticker}: {exc}")
        return None


def vrp_percentile(ticker: str, lookback: int | None = None) -> dict:
    """Today's vol-index-based VRP, its percentile rank, and the sample count.

    Returns {"vrp": float vol points, "pct": int 0-100, "n": int} when data is sufficient,
    else {"vrp": None, "pct": None, "n": 0} on empty vol-index, yfinance failure, or no
    date alignment. Never raises.
    """
    if lookback is None:
        lookback = config.VRP_PERCENTILE_LOOKBACK

    none_dict = {"vrp": None, "pct": None, "n": 0}

    sym = config.TICKER_VOL_INDEX[ticker]
    vi = load_vol_index(sym)
    if vi.empty:
        return none_dict

    closes = _fetch_closes_yf(ticker, period="400d")
    if closes is None:
        return none_dict

    vi_close = vi.set_index("date")["close"]  # vol points, date-only index

    # Rolling RV20 aligned to each close date with >=21 prior prices (21 prices -> 20 returns).
    cl = closes.sort_index()
    rv: dict = {}
    for i in range(20, len(cl)):
        window = cl.iloc[i - 20: i + 1].reset_index(drop=True)
        rv[cl.index[i]] = compute_rv20(window)
    if not rv:
        return none_dict
    rv_series = pd.Series(rv)

    aligned = pd.DataFrame({"vi": vi_close, "rv": rv_series}).dropna()
    if aligned.empty:
        return none_dict

    vrp_hist = aligned["vi"] - aligned["rv"] * 100  # both vol points
    if vrp_hist.empty:
        return none_dict

    today_vrp = float(vrp_hist.iloc[-1])  # same definition as every history point
    window = vrp_hist.iloc[-lookback:]
    pct = int(percentileofscore(window.to_numpy(), today_vrp, kind="rank"))
    return {"vrp": today_vrp, "pct": pct, "n": len(window)}
