"""
Vol-managed exposure scalar (Moreira & Muir 2017) and its backtest.

weight = min(MAX_WEIGHT, TARGET_VOL / forecast_vol), forecast = ½·VIX + ½·RV20.

This is the one place the lens produces a number shaped like an action, so the scope is
spelled out: it is a *risk budget read* ("a sleeve targeting 15% vol would hold 80% of
full exposure right now"), handed to portfolio-manager as information. It never moves a
MANDATE weight — governance there decides whether, and how, to use it.

The backtest is deliberately plain — weekly rebalance, no costs, no cash yield — so it
can't flatter itself. The research finding it reproduces: Sharpe up modestly, drawdown
down a lot, CAGR *down*. It is a risk reducer, not a return engine; say so.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine import config


def exposure_weight(forecast_vol: float | None, target: float | None = None,
                    cap: float | None = None) -> float | None:
    if forecast_vol is None or not np.isfinite(forecast_vol) or forecast_vol <= 0:
        return None
    t = target or config.RISK_LENS_TARGET_VOL
    c = cap or config.RISK_LENS_MAX_WEIGHT
    return float(min(c, t / forecast_vol))


def weight_series(panel: pd.DataFrame, target: float | None = None, cap: float | None = None,
                  rebalance: str = "W-FRI") -> pd.Series:
    """Weight in force on each session: set at the last rebalance close, applied from
    the next session (shifted, so no look-ahead)."""
    t = target or config.RISK_LENS_TARGET_VOL
    c = cap or config.RISK_LENS_MAX_WEIGHT
    w = (t / panel["forecast_vol"]).clip(upper=c)
    w = w.resample(rebalance).last().reindex(panel.index, method="ffill")
    return w.shift(1)


def _stats(r: pd.Series) -> dict:
    r = r.dropna()
    if r.empty:
        return {}
    eq = (1 + r).cumprod()
    vol = r.std() * np.sqrt(252)
    return {
        "cagr": float(eq.iloc[-1] ** (252 / len(r)) - 1),
        "vol": float(vol),
        "sharpe": float(r.mean() * 252 / vol) if vol > 0 else None,
        "max_dd": float((eq / eq.cummax() - 1).min()),
        "worst_month": float(r.resample("ME").apply(lambda x: (1 + x).prod() - 1).min()),
    }


def backtest(panel: pd.DataFrame, start: str = "1992-01-01", target: float | None = None) -> dict:
    """Buy-and-hold SPX vs the vol-managed sleeve, full sample + both halves (the
    halves are the out-of-sample check: the effect must show up in each)."""
    w = weight_series(panel, target)
    df = pd.DataFrame({"bh": panel["ret1"], "vm": w * panel["ret1"], "w": w}).loc[start:].dropna()
    mid = df.index[len(df) // 2]
    out = {"start": str(df.index[0].date()), "end": str(df.index[-1].date()),
           "avg_weight": float(df["w"].mean()), "periods": {}}
    for name, part in (("full", df), ("early", df[df.index < mid]), ("late", df[df.index >= mid])):
        out["periods"][name] = {"from": str(part.index[0].date()), "to": str(part.index[-1].date()),
                                "buy_hold": _stats(part["bh"]), "vol_managed": _stats(part["vm"])}
    return out
