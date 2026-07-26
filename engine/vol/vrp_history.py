"""VRP-percentile engine — builds one internally-consistent, VRP-03-clean series.

What "VRP" means here (intentional methodology deviation — 25-CONTEXT.md, locked
2026-07-26): this is `vol_index_close − RV20×100`, implied minus realized vol in *points*
— a practitioner vol-risk-premium proxy, NOT the Carr & Wu (2009) variance-swap VRP
(`IV² − RV²`, variance units). The vol-point spread is theoretically aligned for vanilla
covered-call/CSP writing (vanilla premium ≈ linear in IV via vega) and more interpretable
for the income-sleeve PM, so the computation and the "VRP" label are kept as-is by design;
this docstring is the honest first-use definition, not a bug to fix.

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


def _fetch_closes_yf(ticker: str, period: str = "2520d") -> "pd.Series | None":
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


def vrp_history_series(ticker: str) -> "pd.Series | None":
    """Build the full vol-index-based VRP series (date-indexed ascending, vol points).

    Same series vrp_percentile() ranks against internally -- the single source of
    truth so the scalar and its rank (and any other consumer, e.g. engine.monitor.metrics)
    share one definition. Returns None on empty vol-index, yfinance failure, or no date
    alignment. Never raises.
    """
    try:
        sym = config.TICKER_VOL_INDEX[ticker]
        vi = load_vol_index(sym)
        if vi.empty:
            return None

        fetch_days = config.VRP_DEEP_LOOKBACK_SESSIONS + config.VRP_CLOSES_FETCH_BUFFER_DAYS
        closes = _fetch_closes_yf(ticker, period=f"{fetch_days}d")
        if closes is None:
            return None

        vi_close = vi.set_index("date")["close"]  # vol points, date-only index

        # Rolling RV20 aligned to each close date with >=21 prior prices (21 prices -> 20 returns).
        cl = closes.sort_index()
        rv: dict = {}
        for i in range(20, len(cl)):
            window = cl.iloc[i - 20: i + 1].reset_index(drop=True)
            rv[cl.index[i]] = compute_rv20(window)
        if not rv:
            return None
        rv_series = pd.Series(rv)

        aligned = pd.DataFrame({"vi": vi_close, "rv": rv_series}).dropna()
        if aligned.empty:
            return None

        vrp_hist = aligned["vi"] - aligned["rv"] * 100  # both vol points
        if vrp_hist.empty:
            return None

        return vrp_hist
    except Exception as exc:
        print(f"[vrp_history] vrp_history_series failed for {ticker}: {exc}")
        return None


def vrp_percentile(ticker: str, lookback: int | None = None) -> dict:
    """Today's vol-index-based VRP, its percentile rank, and the sample count.

    Ranks today's VRP against ALL available aligned history by default (bounded below by
    a config.VRP_DEEP_LOOKBACK_SESSIONS-session closes fetch, ~10 real trading years) --
    not a short rolling window. A short window can only tell you a value is "cheap"
    relative to a recent, possibly still-elevated regime; ranking against ~10yr instead
    answers the question against the vol-index's actual depth (VIX to 1990, VXN/RVX to
    2009). Pass an explicit `lookback` to rank against a shorter window instead.

    Returns {"vrp": float vol points, "pct": int 0-100, "n": int} when data is sufficient,
    else {"vrp": None, "pct": None, "n": 0} on empty vol-index, yfinance failure, or no
    date alignment. Never raises.
    """
    none_dict = {"vrp": None, "pct": None, "n": 0}

    vrp_hist = vrp_history_series(ticker)
    if vrp_hist is None or vrp_hist.empty:
        return none_dict

    today_vrp = float(vrp_hist.iloc[-1])  # same definition as every history point
    window = vrp_hist if lookback is None else vrp_hist.iloc[-lookback:]
    pct = int(percentileofscore(window.to_numpy(), today_vrp, kind="rank"))
    return {"vrp": today_vrp, "pct": pct, "n": len(window)}
