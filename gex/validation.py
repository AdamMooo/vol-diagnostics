"""
Daily snapshot store.

Each day run_daily.py calls `save_snapshot()` to append the day's summary to
the parquet store. `load_history()` reads the store back to drive the 30-day
ZGL-vs-spot chart in the streamlit detail expander.

Vs-yesterday classification and event-study aggregates were removed: the
sample is too short for inference, and vs-yesterday mostly reflected daily
OI roll noise rather than signal.

Store path: out/gex_snapshots.parquet
Columns:    date, ticker, spot, net_gex, zero_gamma_level, call_wall, put_wall,
            front_skew, put_25d_iv, call_50d_iv, iv30, strike_slope, term_slope,
            rv20, vrp

Schema is forward-compatible: older snapshots missing newer columns load as
NaN on read. Don't reorder or rename columns.
"""
from __future__ import annotations

import datetime
import pathlib

import pandas as pd

STORE = pathlib.Path(__file__).resolve().parents[1] / "out" / "gex_snapshots.parquet"


_FLOAT_COLS = (
    "zero_gamma_level", "call_wall", "put_wall",
    "front_skew", "put_25d_iv", "call_50d_iv", "iv30",
    "strike_slope", "term_slope",
    "rv20", "vrp",
)


def save_snapshot(summary: dict, ticker: str, skew_df: pd.DataFrame | None = None) -> None:
    """Append today's summary dict to the parquet store (idempotent on date+ticker).

    skew_df: optional output of compute_skew() — front-row put_25d_iv and
    call_50d_iv are captured for skew history. If omitted, those columns are NaN.
    """
    put_25d = call_50d = None
    if skew_df is not None and not skew_df.empty:
        put_25d = float(skew_df["put_25d_iv"].iloc[0])
        call_50d = float(skew_df["call_50d_iv"].iloc[0])

    row = {
        "date": datetime.date.today(),
        "ticker": ticker,
        "spot": summary["spot"],
        "net_gex": summary["net_gex"],
        "zero_gamma_level": summary.get("zero_gamma_level"),
        "call_wall": summary.get("call_wall"),
        "put_wall": summary.get("put_wall"),
        "front_skew": summary.get("front_skew"),
        "put_25d_iv": put_25d,
        "call_50d_iv": call_50d,
        "iv30": summary.get("iv30"),
        "strike_slope": summary.get("strike_slope"),
        "term_slope": summary.get("term_slope"),
        "rv20": summary.get("rv20"),
        "vrp": summary.get("vrp"),
    }

    if STORE.exists():
        hist = pd.read_parquet(STORE)
        for col in _FLOAT_COLS:
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
