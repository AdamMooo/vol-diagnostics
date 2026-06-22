"""
Per-expiry OI snapshot store.

run_daily.py calls save_oi_snapshot() each trading day to append the day's
per-expiry aggregates to a per-ticker parquet store. Store path:
out/oi_history/oi_{ticker}.parquet. Columns: date, ticker, expiry, dte,
call_oi, put_oi, oi, pct_of_total, put_call_ratio. One row per expiry per
session. Idempotent: today's rows are replaced on re-run.
"""
from __future__ import annotations

import datetime
import pathlib

import pandas as pd

STORE_DIR = pathlib.Path(__file__).resolve().parents[2] / "out" / "oi_history"


def _store_path(ticker: str) -> pathlib.Path:
    return STORE_DIR / f"oi_{ticker}.parquet"


def save_oi_snapshot(
    expiry_oi_df: pd.DataFrame | None,
    ticker: str,
    date: datetime.date | None = None,
) -> None:
    """Append today's per-expiry OI rows to the per-ticker parquet store.

    Idempotent: today's rows are deleted before concat so re-runs replace rather
    than accumulate. Returns early on None or empty input (T-16.5-02 mitigate).
    """
    if expiry_oi_df is None or expiry_oi_df.empty:
        return

    today = date if date is not None else datetime.date.today()

    cols = ["expiry", "dte", "call_oi", "put_oi", "oi", "pct_of_total", "put_call_ratio"]
    df = expiry_oi_df[cols].copy()
    df.insert(0, "date", today)
    df.insert(1, "ticker", ticker)

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
    print(f"[oi_history] {ticker}: {len(df)} rows saved for {today} "
          f"({len(hist)} total rows in store)")


def load_oi_snapshot(ticker: str, date: datetime.date) -> pd.DataFrame:
    """Load one day's per-expiry rows for ticker.

    Returns DataFrame with columns expiry, dte, call_oi, put_oi, oi,
    pct_of_total, put_call_ratio. Returns empty DataFrame (never raises) when
    store absent or date not found.
    """
    path = _store_path(ticker)
    if not path.exists():
        return pd.DataFrame()
    try:
        hist = pd.read_parquet(path)
        hist["date"] = pd.to_datetime(hist["date"]).dt.date
        rows = hist[hist["date"] == date].reset_index(drop=True)
        if rows.empty:
            return pd.DataFrame()
        return rows.drop(columns=["date", "ticker"])
    except Exception as exc:
        print(f"[oi_history] load_oi_snapshot failed for {ticker} {date}: {exc}")
        return pd.DataFrame()


def prior_oi_snapshot(ticker: str, before_date: datetime.date) -> pd.DataFrame:
    """Return the most recent snapshot strictly before before_date.

    Calls list_oi_dates to find available dates newest-first, then picks the
    first date that is strictly less than before_date. Returns empty DataFrame
    on cold start (no prior session exists) — never raises.
    """
    dates = list_oi_dates(ticker)
    prior = [d for d in dates if d < before_date]
    if not prior:
        return pd.DataFrame()
    return load_oi_snapshot(ticker, prior[0])


def list_oi_dates(ticker: str) -> list[datetime.date]:
    """Return sorted list of available dates (newest first).

    Returns [] when store absent or on any exception.
    """
    path = _store_path(ticker)
    if not path.exists():
        return []
    try:
        hist = pd.read_parquet(path, columns=["date"])
        dates = pd.to_datetime(hist["date"]).dt.date.unique()
        return sorted(set(dates), reverse=True)
    except Exception as exc:
        print(f"[oi_history] list_oi_dates failed for {ticker}: {exc}")
        return []
