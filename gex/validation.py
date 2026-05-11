"""
Daily snapshot store.

Workflow: each day run_daily.py calls `save_snapshot()` to append the day's
summary to the parquet store. The store backs future research (e.g. a proper
event study, once we have 3+ years of clean history and a controlled design).

The previous in-process `event_study()` and `_classify_vs_yesterday()` helpers
were removed: the sample is too short for inference (n~60 per regime per ticker,
no multiple-testing correction, no vol-clustering controls), and the
vs-yesterday classifier mostly reflected daily OI roll noise rather than signal.

Store path: out/gex_snapshots.parquet
Columns:    date, ticker, spot, net_gex, gamma_regime, zero_gamma_level,
            call_wall, put_wall, vanna_exposure
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
        "gamma_regime": summary["gamma_regime"],
        "zero_gamma_level": summary.get("zero_gamma_level"),
        "call_wall": summary.get("call_wall"),
        "put_wall": summary.get("put_wall"),
        "vanna_exposure": summary.get("net_vex"),
    }

    if STORE.exists():
        hist = pd.read_parquet(STORE)
        for col in ("zero_gamma_level", "call_wall", "put_wall", "vanna_exposure"):
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


def load_yesterday(ticker: str, today: datetime.date | None = None) -> "pd.Series | None":
    if not STORE.exists():
        return None
    try:
        import pandas_market_calendars as mcal
        target = today or datetime.date.today()
        nyse = mcal.get_calendar("NYSE")
        sched = nyse.schedule(
            start_date=(target - datetime.timedelta(days=10)).strftime("%Y-%m-%d"),
            end_date=(target - datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
        )
        if sched.empty:
            return None
        prior_date = sched.index[-1].date()
        hist = pd.read_parquet(STORE)
        hist["date"] = pd.to_datetime(hist["date"]).dt.date
        row = hist[(hist["date"] == prior_date) & (hist["ticker"] == ticker)]
        return row.iloc[0] if not row.empty else None
    except Exception:
        return None


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


