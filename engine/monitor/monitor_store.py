"""Monitor parquet stores: ranks.parquet + alert_events.parquet.

Mirrors engine/data/validation.py's idempotent read-mask-concat-atomic pattern
exactly. compute_and_save_monitor_rows is the per-ticker orchestration seam
run_daily.py calls after the existing snapshot/evolution saves: for every
(metric, ticker) in METRIC_INVENTORY matching this ticker, it loads history,
computes level+change ranks, reads yesterday's band_state via
load_prior_monitor_row, runs the hysteresis transition three times (deep/1yr/
change), and persists a MonitorRow + any fired AlertEvents. Never raises per
metric -- one metric's failure does not block the others.
"""
from __future__ import annotations

import datetime
import pathlib

import pandas as pd

from engine.data.store import atomic_to_parquet
from engine.monitor import ranker, metrics, hysteresis
from engine.monitor.schema import METRIC_INVENTORY

RANKS_STORE = pathlib.Path(__file__).resolve().parents[2] / "out" / "monitor" / "ranks.parquet"
ALERT_EVENTS_STORE = pathlib.Path(__file__).resolve().parents[2] / "out" / "monitor" / "alert_events.parquet"


def save_monitor_row(row: dict, store: pathlib.Path | None = None) -> None:
    """Append/replace one MonitorRow, idempotent on (date, ticker, metric)."""
    path = store if store is not None else RANKS_STORE
    if path.exists():
        hist = pd.read_parquet(path)
        mask = (
            (hist["date"] == row["date"])
            & (hist["ticker"] == row["ticker"])
            & (hist["metric"] == row["metric"])
        )
        hist = hist[~mask]
        hist = pd.concat([hist, pd.DataFrame([row])], ignore_index=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        hist = pd.DataFrame([row])

    atomic_to_parquet(hist, path)
    print(f"[monitor] Rank row saved ({len(hist)} rows total): {path}")


def save_alert_event(event: dict, store: pathlib.Path | None = None) -> None:
    """Append-only write of one AlertEvent -- every transition is a distinct fact."""
    path = store if store is not None else ALERT_EVENTS_STORE
    if path.exists():
        hist = pd.read_parquet(path)
        hist = pd.concat([hist, pd.DataFrame([event])], ignore_index=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        hist = pd.DataFrame([event])

    atomic_to_parquet(hist, path)
    print(f"[monitor] Alert event saved ({len(hist)} rows total): {path}")


def load_prior_monitor_row(
    ticker: str,
    metric: str,
    before_date: datetime.date,
    store: pathlib.Path | None = None,
) -> dict | None:
    """Return the most-recent monitor row strictly before before_date, or None."""
    path = store if store is not None else RANKS_STORE
    if not path.exists():
        return None
    try:
        hist = pd.read_parquet(path)
        hist["date"] = pd.to_datetime(hist["date"]).dt.date
        mask = (hist["ticker"] == ticker) & (hist["metric"] == metric) & (hist["date"] < before_date)
        subset = hist[mask].sort_values("date", ascending=False)
        if subset.empty:
            return None
        return subset.iloc[0].to_dict()
    except Exception as exc:
        print(f"[CORRUPT] monitor_store.load_prior_monitor_row: {path.name} unreadable ({exc})")
        return None


def compute_and_save_monitor_rows(
    ticker: str,
    summary: dict,
    today: datetime.date,
    band_entry: int,
    band_escalate: int,
    band_exit: int,
) -> int:
    """Compute + persist a MonitorRow (and any fired AlertEvents) for every metric
    belonging to this ticker in METRIC_INVENTORY. Never raises -- one metric's
    failure is caught and skipped, others still get saved. Returns rows written."""
    written = 0
    for metric_name, inv_ticker in METRIC_INVENTORY:
        if inv_ticker != ticker:
            continue
        try:
            history = metrics.load_metric_series(ticker, metric_name)
            today_value = summary.get(metric_name)
            if today_value is None and history is not None and not history.empty:
                last_date = history.index[-1]
                if last_date == today:
                    today_value = float(history.iloc[-1])
                else:
                    print(f"[monitor] {ticker}/{metric_name}: history stale (last={last_date}); skipping value")

            level_res = ranker.compute_level_ranks(history, today_value)
            change_res = ranker.compute_change_rank(history, today_value)

            prior = load_prior_monitor_row(ticker, metric_name, today) or {}
            prior_deep = prior.get("band_state_deep", "out")
            prior_1yr = prior.get("band_state_1yr", "out")
            prior_change = prior.get("band_state_change", "out")

            alert_deep, state_deep = hysteresis.check_alert_transition(
                level_res["level_rank_deep"], level_res["n_deep"], prior_deep,
                band_entry, band_escalate, band_exit,
            )
            alert_1yr, state_1yr = hysteresis.check_alert_transition(
                level_res["level_rank_1yr"], level_res["n_1yr"], prior_1yr,
                band_entry, band_escalate, band_exit,
            )
            alert_change, state_change = hysteresis.check_alert_transition(
                change_res["change_rank"], change_res["change_n"], prior_change,
                band_entry, band_escalate, band_exit,
            )

            row = {
                "date": today,
                "ticker": ticker,
                "metric": metric_name,
                "value": today_value,
                "level_rank_deep": level_res["level_rank_deep"],
                "n_deep": level_res["n_deep"],
                "level_rank_1yr": level_res["level_rank_1yr"],
                "n_1yr": level_res["n_1yr"],
                "change_rank": change_res["change_rank"],
                "change_n": change_res["change_n"],
                "band_state_deep": state_deep,
                "band_state_1yr": state_1yr,
                "band_state_change": state_change,
            }
            save_monitor_row(row)
            written += 1

            for rank_kind, alert_type, rank_value, prior_state in (
                ("level_deep", alert_deep, level_res["level_rank_deep"], prior_deep),
                ("level_1yr", alert_1yr, level_res["level_rank_1yr"], prior_1yr),
                ("change", alert_change, change_res["change_rank"], prior_change),
            ):
                if alert_type is not None:
                    save_alert_event({
                        "date": today,
                        "ticker": ticker,
                        "metric": metric_name,
                        "rank_kind": rank_kind,
                        "alert_type": alert_type,
                        "rank_at_transition": rank_value,
                        "prior_state": prior_state,
                    })
        except Exception as exc:
            print(f"[monitor] {ticker}/{metric_name} failed (non-blocking): {exc}")
            continue

    return written
