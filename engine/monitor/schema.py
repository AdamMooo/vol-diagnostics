"""Monitor schema: dataclasses + the canonical metric inventory.

MonitorRow is one row of severity-rank output per (date, ticker, metric).
AlertEvent is one alert transition (entry/escalation) fired by the hysteresis
layer in Plan 02 — not produced by anything in this plan.

METRIC_INVENTORY enumerates every (metric_name, ticker) pair that gets a
severity rank per D-07. Net GEX is explicitly excluded (D-10) — it gets a
state chip, not a severity rank.
"""
from __future__ import annotations

import dataclasses

_TICKERS = ("SPY", "QQQ", "IWM")
_PER_TICKER_METRICS = ("vrp", "skew_25d", "fly_25d", "surface_level", "surface_rms")

METRIC_INVENTORY: list[tuple[str, str]] = [
    (metric, ticker) for metric in _PER_TICKER_METRICS for ticker in _TICKERS
] + [
    ("term_9d_30", "SPY"),
    ("term_30_3m", "SPY"),
]


@dataclasses.dataclass
class MonitorRow:
    date: object
    ticker: str
    metric: str
    value: float | None
    level_rank_deep: int | None
    n_deep: int
    level_rank_1yr: int | None
    n_1yr: int
    change_rank: int | None
    change_n: int
    band_state_deep: str = "out"
    band_state_1yr: str = "out"
    band_state_change: str = "out"


@dataclasses.dataclass
class AlertEvent:
    date: object
    ticker: str
    metric: str
    rank_kind: str  # "level_deep" | "level_1yr" | "change"
    alert_type: str  # "entry" | "escalation"
    rank_at_transition: int
    prior_state: str
