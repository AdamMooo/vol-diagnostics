"""Phase 2 — signal engineering.

Six raw signals per underlying, then causal 5y rolling percentile rank:

    rv30   30D realized vol (annualized, vol pts)
    vrp    iv30_atm - rv30
    term   iv90_atm - iv30_atm
    skew   iv30_90mny - iv30_atm  (already a panel from data_layer)
    trend  log(spot / SMA200)
    dd     spot / rolling-max(252) - 1

Plus a fragility composite: mean(vrp_pct, skew_pct, 1-trend_pct, 1-dd_pct)
— high when vol expensive, skew steep, trend weak, drawdown deep.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from data_layer import Panels

PCT_WINDOW  = 1260   # ~5y trading days
PCT_MIN_OBS = 252    # 1y warmup


@dataclass
class Signals:
    log_ret: pd.DataFrame
    raw: dict[str, pd.DataFrame]
    pct: dict[str, pd.DataFrame]
    fragility: pd.DataFrame

    def latest(self) -> pd.DataFrame:
        """Last row for which every signal has data (avoids T-0 publish lag)."""
        all_pct = pd.concat(self.pct, axis=1)
        last_full = all_pct.dropna(how="any").index.max()
        return pd.DataFrame({sig: panel.loc[last_full] for sig, panel in self.pct.items()}).T

    def latest_date(self) -> pd.Timestamp:
        all_pct = pd.concat(self.pct, axis=1)
        return all_pct.dropna(how="any").index.max()


def causal_pct_rank(panel: pd.DataFrame) -> pd.DataFrame:
    return panel.rolling(window=PCT_WINDOW, min_periods=PCT_MIN_OBS).rank(pct=True)


def build_signals(p: Panels) -> Signals:
    log_ret = np.log(p.prices_panel / p.prices_panel.shift(1))
    rv30 = log_ret.rolling(window=21, min_periods=15).std() * np.sqrt(252) * 100

    raw = {
        "rv30":  rv30,
        "vrp":   p.iv_panel - rv30,
        "term":  p.iv90_panel - p.iv_panel,
        "skew":  p.skew_panel.copy(),
        "trend": np.log(p.prices_panel / p.prices_panel.rolling(200, min_periods=100).mean()),
        "dd":    p.prices_panel / p.prices_panel.rolling(252, min_periods=100).max() - 1.0,
    }

    pct = {k: causal_pct_rank(v) for k, v in raw.items()}

    fragility = (
        pct["vrp"] + pct["skew"] + (1.0 - pct["trend"]) + (1.0 - pct["dd"])
    ) / 4.0
    pct["fragility"] = fragility

    return Signals(log_ret=log_ret, raw=raw, pct=pct, fragility=fragility)
