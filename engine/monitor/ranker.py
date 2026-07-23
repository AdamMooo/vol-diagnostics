"""Pure ECDF severity ranker — no I/O.

Mirrors engine/vol/vrp_history.py's percentile pattern exactly: rank today's value
against a history window via scipy's percentileofscore(kind="rank"). Two functions:

compute_level_ranks — dual-lookback (deep + 1yr) level rank, independent windows (D-02).
compute_change_rank — single two-sided k=5 |Δ| rank (D-03).

Never raise. Ranks are always computed and labeled with n, even below the
credibility floor (D-08) — gating on n is the hysteresis layer's job (Plan 02).
"""
from __future__ import annotations

import pandas as pd
from scipy.stats import percentileofscore

from engine import config


def compute_level_ranks(
    history: "pd.Series | None",
    today_value: float | None,
    deep_lookback: int | None = None,
    oneyr_lookback: int = config.MONITOR_ONEYR_LOOKBACK_SESSIONS,
) -> dict:
    """Rank today_value against history on two independent windows: deep (default
    full available history) and the tail oneyr_lookback rows. Never raises."""
    none_dict = {
        "level_rank_deep": None, "n_deep": 0,
        "level_rank_1yr": None, "n_1yr": 0,
    }
    try:
        if history is None or today_value is None:
            return none_dict

        clean = history.dropna()
        if clean.empty:
            return none_dict

        deep_window = clean if deep_lookback is None else clean.iloc[-deep_lookback:]
        n_deep = len(deep_window)
        level_rank_deep = (
            int(percentileofscore(deep_window.to_numpy(), today_value, kind="rank"))
            if n_deep > 0 else None
        )

        oneyr_window = clean.iloc[-oneyr_lookback:]
        n_1yr = len(oneyr_window)
        level_rank_1yr = (
            int(percentileofscore(oneyr_window.to_numpy(), today_value, kind="rank"))
            if n_1yr > 0 else None
        )

        return {
            "level_rank_deep": level_rank_deep, "n_deep": n_deep,
            "level_rank_1yr": level_rank_1yr, "n_1yr": n_1yr,
        }
    except Exception as exc:
        print(f"[ranker] compute_level_ranks failed: {exc}")
        return none_dict


def compute_change_rank(
    history: "pd.Series | None",
    today_value: float | None = None,
    k: int = config.MONITOR_CHANGE_K_SESSIONS,
    lookback: int | None = None,
) -> dict:
    """Two-sided |Δk| severity rank: magnitude only, sign discarded (D-03). Never raises."""
    none_dict = {"change_rank": None, "change_n": 0}
    try:
        if history is None:
            return none_dict

        clean = history.dropna()
        if clean.empty or len(clean) <= k:
            return none_dict

        abs_changes = clean.diff(k).abs().dropna()
        if abs_changes.empty:
            return none_dict

        window = abs_changes if lookback is None else abs_changes.iloc[-lookback:]
        if window.empty:
            return none_dict

        if today_value is None:
            todays_change = float(abs_changes.iloc[-1])
        else:
            prior = clean.iloc[-1 - k] if len(clean) > k else None
            if prior is None:
                return none_dict
            todays_change = abs(float(today_value) - float(prior))

        change_rank = int(percentileofscore(window.to_numpy(), todays_change, kind="rank"))
        return {"change_rank": change_rank, "change_n": len(window)}
    except Exception as exc:
        print(f"[ranker] compute_change_rank failed: {exc}")
        return none_dict
