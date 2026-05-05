"""
Daily snapshot store and simple event-study validation.

Workflow:
    1. Each day run run_gex.py — call `save_snapshot()` to append to the parquet store.
    2. After 20+ trading days, run `event_study()` to check whether positive vs
       negative gamma days differ in next-day realized range or move direction.

Store path: out/gex_snapshots.parquet
Columns:    date, ticker, spot, net_gex, gamma_regime, zero_gamma_level,
            call_wall, put_wall
"""
from __future__ import annotations

import datetime
import pathlib

import numpy as np
import pandas as pd
import yfinance as yf

STORE = pathlib.Path(__file__).resolve().parents[1] / "out" / "gex_snapshots.parquet"


def save_snapshot(summary: dict, ticker: str) -> None:
    """Append today's summary dict to the parquet store (idempotent on date+ticker)."""
    row = {
        "date": datetime.date.today(),
        "ticker": ticker,
        "spot": summary["spot"],
        "net_gex": summary["net_gex"],
        "gamma_regime": summary["gamma_regime"],
        "zero_gamma_level": summary.get("zero_gamma_level"),
        "call_wall": summary.get("call_wall"),
        "put_wall": summary.get("put_wall"),
    }

    if STORE.exists():
        hist = pd.read_parquet(STORE)
        mask = (hist["date"] == row["date"]) & (hist["ticker"] == ticker)
        hist = hist[~mask]
        hist = pd.concat([hist, pd.DataFrame([row])], ignore_index=True)
    else:
        STORE.parent.mkdir(exist_ok=True)
        hist = pd.DataFrame([row])

    hist.to_parquet(STORE, index=False)
    print(f"[gex] Snapshot saved ({len(hist)} rows total): {STORE}")


def event_study(ticker: str = "SPY", lookahead: int = 1) -> pd.DataFrame:
    """
    Join stored GEX snapshots with realised price data.

    For each snapshot, compute:
        - next_{lookahead}d_return: (close_t+n / close_t) - 1
        - next_{lookahead}d_range:  (high - low) / close over t..t+n

    Returns a DataFrame; also prints split means by gamma_regime.
    """
    if not STORE.exists():
        raise FileNotFoundError(f"No snapshot store at {STORE}. Run save_snapshot() first.")

    hist = pd.read_parquet(STORE).query("ticker == @ticker").copy()
    hist["date"] = pd.to_datetime(hist["date"])
    hist = hist.sort_values("date").reset_index(drop=True)
    if len(hist) < 5:
        print("[gex] Not enough history for event study (need ≥5 days).")
        return hist

    start = hist["date"].min() - datetime.timedelta(days=5)
    end = hist["date"].max() + datetime.timedelta(days=lookahead + 5)
    prices = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
    prices.index = pd.to_datetime(prices.index)

    returns: list[float] = []
    ranges: list[float] = []

    for _, row in hist.iterrows():
        date = row["date"]
        future = prices.loc[prices.index > date].head(lookahead)
        if len(future) < lookahead:
            returns.append(float("nan"))
            ranges.append(float("nan"))
            continue

        c0 = prices.loc[prices.index <= date, "Close"].iloc[-1]
        cn = float(future["Close"].iloc[-1])
        hl = float(future["High"].max() - future["Low"].min()) / float(c0)
        returns.append(float(cn / c0 - 1))
        ranges.append(hl)

    hist[f"next_{lookahead}d_return"] = returns
    hist[f"next_{lookahead}d_range"] = ranges

    print(f"\nEvent study — {ticker}  lookahead={lookahead}d  n={len(hist)}")
    for regime in ("positive", "negative", "neutral"):
        sub = hist[hist["gamma_regime"] == regime].dropna(
            subset=[f"next_{lookahead}d_return", f"next_{lookahead}d_range"]
        )
        if sub.empty:
            continue
        ret_mean = sub[f"next_{lookahead}d_return"].mean() * 100
        rng_mean = sub[f"next_{lookahead}d_range"].mean() * 100
        print(f"  {regime:8s}  n={len(sub):3d}  "
              f"avg_return={ret_mean:+.3f}%  avg_range={rng_mean:.3f}%")

    return hist
