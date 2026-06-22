"""
Vol surface snapshot store.

run_daily.py calls `save_surface_snapshot()` each trading day to append
the day's raw OTM chain points to a per-ticker parquet store. Spot price
is stored alongside the chain data so the ∆IV comparison view can
normalise strikes correctly without cross-referencing the scalar store.

Store path: out/surface_history/surface_{ticker}.parquet
Columns:    date, ticker, spot, dte, strike, moneyness, log_moneyness, iv_pct

One row per OTM quote point. Idempotent: today's rows are replaced on
re-run so a dry-run or manual rerun doesn't accumulate duplicates.
"""
from __future__ import annotations

import datetime
import pathlib

import pandas as pd

STORE_DIR = pathlib.Path(__file__).resolve().parents[2] / "out" / "surface_history"


def _store_path(ticker: str) -> pathlib.Path:
    return STORE_DIR / f"surface_{ticker}.parquet"


def save_surface_snapshot(
    surface_df: pd.DataFrame,
    ticker: str,
    spot: float,
    date: datetime.date | None = None,
) -> None:
    """Append today's OTM chain points to the per-ticker parquet store.

    spot is saved on every row so callers never need to look it up elsewhere.
    Pass `date` to file the snapshot under the caller's trading date — run_daily
    uses the ET date so the evolution engine looks the surface up under the same
    key. Defaults to the local date for ad-hoc callers.
    """
    if surface_df is None or surface_df.empty:
        return

    today = date if date is not None else datetime.date.today()
    df = surface_df[["dte", "strike", "moneyness", "log_moneyness", "iv_pct"]].copy()
    df.insert(0, "date", today)
    df.insert(1, "ticker", ticker)
    df.insert(2, "spot", float(spot))

    path = _store_path(ticker)
    STORE_DIR.mkdir(parents=True, exist_ok=True)

    if path.exists():
        hist = pd.read_parquet(path)
        hist["date"] = pd.to_datetime(hist["date"]).dt.date
        hist = hist[hist["date"] != today]
        hist = pd.concat([hist, df], ignore_index=True)
    else:
        hist = df

    hist.to_parquet(path, index=False)
    print(f"[surface_history] {ticker}: {len(df)} rows @ spot={spot:.2f} saved for {today} "
          f"({len(hist)} total rows in store)")


def load_surface_snapshot(ticker: str, date: datetime.date) -> tuple[pd.DataFrame, float | None]:
    """Load one day's chain points and the spot price recorded that day.

    Returns (surface_df, spot). surface_df has columns dte, strike, moneyness,
    log_moneyness, iv_pct. spot is None if the date is not found.
    """
    path = _store_path(ticker)
    if not path.exists():
        return pd.DataFrame(), None
    try:
        hist = pd.read_parquet(path)
        hist["date"] = pd.to_datetime(hist["date"]).dt.date
        rows = hist[hist["date"] == date].reset_index(drop=True)
        if rows.empty:
            return pd.DataFrame(), None
        spot = float(rows["spot"].iloc[0])
        df = rows.drop(columns=["date", "ticker", "spot"])
        return df, spot
    except Exception as exc:
        print(f"[surface_history] load_surface_snapshot failed for {ticker} {date}: {exc}")
        return pd.DataFrame(), None


def list_available_dates(ticker: str) -> list[datetime.date]:
    path = _store_path(ticker)
    if not path.exists():
        return []
    try:
        hist = pd.read_parquet(path, columns=["date"])
        dates = pd.to_datetime(hist["date"]).dt.date.unique()
        return sorted(set(dates), reverse=True)
    except Exception as exc:
        print(f"[surface_history] list_available_dates failed for {ticker}: {exc}")
        return []


def nth_trading_day_back(
    ticker: str, anchor_date: datetime.date, n: int
) -> datetime.date | None:
    """Find the date that is N trading sessions before anchor_date.

    Indexes into the descending list of stored dates — no calendar arithmetic.
    Returns None if anchor_date is not in the store or if fewer than N+1 sessions
    exist after (older than) anchor_date (cold-start case).

    Example: stored dates [d5, d4, d3, d2, d1] (newest first), anchor=d5, n=2
    returns d3 (two positions down in the list = two sessions earlier).
    """
    available = list_available_dates(ticker)
    if anchor_date not in available:
        return None
    idx = available.index(anchor_date)
    if idx + n >= len(available):
        return None
    return available[idx + n]
