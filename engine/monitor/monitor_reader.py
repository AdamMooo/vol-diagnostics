"""Bulk/trail/event read adapters over the Phase 26 monitor parquet stores.

Pure read/reshape layer -- NO new signal, NO new math. Every value returned here
was already computed and persisted by monitor_store.compute_and_save_monitor_rows;
this module only reshapes it into the bulk/trail/event contracts the distribution
board (Plan 02), evidence panels (Plan 03), and event email (Plan 04) consume.

Cold-start is the primary path: the real out/monitor store holds 0-2 dates today,
so load_all_current_ranks always returns exactly len(METRIC_INVENTORY) rows (one
per pair, placeholder ranks/value=None for pairs with no data) and the event/trail
reads degrade to empty DataFrames -- never None, never an exception. The corrupt-
read guard mirrors monitor_store's [CORRUPT] try/except degrade-to-empty pattern.

Callers in app.py wrap these with @st.cache_data -- no caching here by design.
"""
from __future__ import annotations

import datetime
import pathlib

import pandas as pd

from engine.monitor.monitor_store import RANKS_STORE, ALERT_EVENTS_STORE
from engine.monitor.schema import METRIC_INVENTORY

# Column contracts mirrored from schema.MonitorRow / schema.AlertEvent so the
# placeholder / empty frames carry the same shape as a populated read.
_RANK_COLUMNS = [
    "date", "ticker", "metric", "value",
    "level_rank_deep", "n_deep", "level_rank_1yr", "n_1yr",
    "change_rank", "change_n",
    "band_state_deep", "band_state_1yr", "band_state_change",
]
_N_COLUMNS = ["n_deep", "n_1yr", "change_n"]
_ALERT_COLUMNS = [
    "date", "ticker", "metric", "rank_kind", "alert_type",
    "rank_at_transition", "prior_state",
]


def _inventory_frame() -> pd.DataFrame:
    """One row per (ticker, metric) in METRIC_INVENTORY -- the guaranteed spine."""
    return pd.DataFrame(
        [{"ticker": ticker, "metric": metric} for (metric, ticker) in METRIC_INVENTORY]
    )


def load_all_current_ranks(store: pathlib.Path | None = None) -> pd.DataFrame:
    """Latest MonitorRow per (ticker, metric), guaranteed one row per inventory pair.

    Returns exactly len(METRIC_INVENTORY) rows even when the store is absent, holds
    only 1-2 dates, or is corrupt: pairs with no data get None ranks/value and n=0.
    The returned row for a pair is that pair's OWN latest date (groupby max), not the
    global latest date. Read/reshape only -- no rank is re-derived here.
    """
    path = store if store is not None else RANKS_STORE
    spine = _inventory_frame()

    latest = None
    if path.exists():
        try:
            hist = pd.read_parquet(path)
            hist["date"] = pd.to_datetime(hist["date"]).dt.date
            latest = (
                hist.sort_values("date")
                .groupby(["ticker", "metric"], as_index=False)
                .tail(1)
            )
        except Exception as exc:
            print(f"[CORRUPT] monitor_reader.load_all_current_ranks: {path.name} unreadable ({exc})")
            latest = None

    if latest is None or latest.empty:
        merged = spine.copy()
    else:
        merged = spine.merge(latest, on=["ticker", "metric"], how="left")

    # Ensure every contract column exists (absent store has none from the merge).
    for col in _RANK_COLUMNS:
        if col not in merged.columns:
            merged[col] = None
    # Placeholder pairs (no data) carry n=0 rather than NaN. to_numeric first so an
    # all-None (object) column from an absent store coerces cleanly to a nullable int.
    for col in _N_COLUMNS:
        merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0).astype("Int64")

    return merged[_RANK_COLUMNS].reset_index(drop=True)


def load_rank_trail(
    ticker: str,
    metric: str,
    n: int | None = 10,
    store: pathlib.Path | None = None,
) -> pd.DataFrame:
    """A single pair's MonitorRow history, ascending by date, tail(n).

    n=10 feeds the board sparkline; n=None returns the full history for the evidence
    panel. Returns an EMPTY DataFrame (never None) when the pair has no rows or the
    store is absent/corrupt. Read/reshape only.
    """
    path = store if store is not None else RANKS_STORE
    if not path.exists():
        return pd.DataFrame(columns=_RANK_COLUMNS)
    try:
        hist = pd.read_parquet(path)
        hist["date"] = pd.to_datetime(hist["date"]).dt.date
        subset = hist[(hist["ticker"] == ticker) & (hist["metric"] == metric)]
        subset = subset.sort_values("date").reset_index(drop=True)
        if n is not None:
            subset = subset.tail(n).reset_index(drop=True)
        return subset
    except Exception as exc:
        print(f"[CORRUPT] monitor_reader.load_rank_trail: {path.name} unreadable ({exc})")
        return pd.DataFrame(columns=_RANK_COLUMNS)


def load_recent_alert_events(
    days: int = 1,
    store: pathlib.Path | None = None,
) -> pd.DataFrame:
    """AlertEvent rows within the last `days` calendar days, sorted by date.

    Returns an EMPTY DataFrame (never None, never raises) when alert_events.parquet
    does not exist -- the real current cold-start state, no alert has ever fired.
    Corrupt reads degrade to empty with a [CORRUPT] warning. Read/reshape only.
    """
    path = store if store is not None else ALERT_EVENTS_STORE
    if not path.exists():
        return pd.DataFrame(columns=_ALERT_COLUMNS)
    try:
        hist = pd.read_parquet(path)
        hist["date"] = pd.to_datetime(hist["date"]).dt.date
        cutoff = datetime.date.today() - datetime.timedelta(days=days)
        recent = hist[hist["date"] >= cutoff].sort_values("date").reset_index(drop=True)
        return recent
    except Exception as exc:
        print(f"[CORRUPT] monitor_reader.load_recent_alert_events: {path.name} unreadable ({exc})")
        return pd.DataFrame(columns=_ALERT_COLUMNS)
