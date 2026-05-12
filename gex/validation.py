"""
Daily snapshot store.

Each day run_daily.py calls `save_snapshot()` to append the day's summary to
the parquet store. `load_history()` reads the store back to drive the 30-day
ZGL-vs-spot chart in the streamlit detail expander.

Vs-yesterday classification and event-study aggregates were removed: the
sample is too short for inference, and vs-yesterday mostly reflected daily
OI roll noise rather than signal.

Store path: out/gex_snapshots.parquet
Columns:    date, ticker, spot, net_gex, zero_gamma_level, call_wall, put_wall
"""
from __future__ import annotations

import datetime
import pathlib

import pandas as pd

STORE = pathlib.Path(__file__).resolve().parents[1] / "out" / "gex_snapshots.parquet"


def save_snapshot(summary: dict, ticker: str) -> None:
    """Append today's summary dict to the parquet store (idempotent on date+ticker)."""
    row = {
        "date": datetime.date.today(),
        "ticker": ticker,
        "spot": summary["spot"],
        "net_gex": summary["net_gex"],
        "zero_gamma_level": summary.get("zero_gamma_level"),
        "call_wall": summary.get("call_wall"),
        "put_wall": summary.get("put_wall"),
    }

    if STORE.exists():
        hist = pd.read_parquet(STORE)
        for col in ("zero_gamma_level", "call_wall", "put_wall"):
            if col in hist.columns:
                hist[col] = hist[col].astype("float64")
        mask = (hist["date"] == row["date"]) & (hist["ticker"] == ticker)
        hist = hist[~mask]
        hist = pd.concat([hist, pd.DataFrame([row])], ignore_index=True)
    else:
        STORE.parent.mkdir(exist_ok=True)
        hist = pd.DataFrame([row])

    hist.to_parquet(STORE, index=False)
    print(f"[gex] Snapshot saved ({len(hist)} rows total): {STORE}")


def load_history(ticker: str, days: int = 30) -> pd.DataFrame:
    if not STORE.exists():
        return pd.DataFrame()
    try:
        hist = pd.read_parquet(STORE)
        hist["date"] = pd.to_datetime(hist["date"]).dt.date
        hist = hist[hist["ticker"] == ticker].sort_values("date", ascending=False)
        return hist.head(days).reset_index(drop=True)
    except Exception:
        return pd.DataFrame()
