"""
Exception events — the only thing that triggers a Risk Lens email.

Design scars carried over from the unwired engine/regime_alert.py:

* **Distinct signals, not tickers.** SPY/QQQ/IWM vol correlates 0.84–0.94; counting them
  as three votes is one vote counted three times. Every event here is defined on ONE
  series family (SPX vol complex); QQQ/IWM appear only as context in the read.
* **High VRP is not stress.** Implied rich vs realized is the calm state. The stress
  state is the opposite — realized running *above* implied (`carry_flip`).
* **Level and shape are different events.** `vol_elevated` (level) and `curve_inverted`
  (shape) fire independently; both have their own base rates.

Every event is a hysteresis state machine (enter at one threshold, exit at a looser
one) evaluated over the full history, so the state on any day is reproducible from
the stores alone — no persisted state machine to drift. Exits matter as much as
entries for risk-on/off awareness: "stress has cleared" is a decision input too.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd

from engine import config
from engine.insight.exposure import exposure_weight

RISING, EASING = "risk rising", "risk easing"


def _f(row: pd.Series, key: str) -> float:
    v = row.get(key)
    return float(v) if v is not None and np.isfinite(v) else np.nan


@dataclass(frozen=True)
class EventDef:
    key: str
    enter: Callable[[pd.Series], bool]
    exit: Callable[[pd.Series], bool]
    enter_title: str
    exit_title: str | None
    enter_lean: str
    learn: str
    refractory: int = 0  # momentary events: sessions before it may fire again


EVENTS: tuple[EventDef, ...] = (
    EventDef(
        key="vol_extreme",
        enter=lambda r: _f(r, "vix_pct") >= 0.95,
        exit=lambda r: _f(r, "vix_pct") < 0.85,
        enter_title="VIX entered its top 5% of the last 10 years",
        exit_title="VIX left extreme territory (back below its 85th pct)",
        enter_lean=RISING,
        learn=("Forward risk is non-linear in the level: in the top 5% the median next-month "
               "realized vol roughly doubles vs. normal, but median returns are also the highest "
               "of any bucket — panic prices recovery as well as crash. The distribution is "
               "wide, not just shifted."),
    ),
    EventDef(
        key="vol_elevated",
        enter=lambda r: _f(r, "vix_pct") >= 0.80,
        exit=lambda r: _f(r, "vix_pct") < 0.65,
        enter_title="VIX moved into its top 20% of the last 10 years",
        exit_title="VIX normalised (back below its 65th pct)",
        enter_lean=RISING,
        learn=("VIX level is the single strongest predictor of next-month realized vol in the "
               "data (rank-correlation 0.74). Everything else in the system adds a little on top "
               "of it; nothing replaces it. Vol clusters — high now means high next month."),
    ),
    EventDef(
        key="curve_inverted",
        enter=lambda r: _f(r, "term") >= 1.00,
        exit=lambda r: _f(r, "term") < 0.95,
        enter_title="VIX term structure inverted (1-month above 3-month)",
        exit_title="VIX curve back in contango",
        enter_lean=RISING,
        learn=("Normally 3-month vol trades above 1-month (you pay for time). Inversion means the "
               "market prices the next 30 days as riskier than the next 90 — demand for "
               "immediate protection. Holding the VIX level fixed, inversion still adds forward "
               "risk; that is why it's a separate event, not a restatement of level."),
    ),
    EventDef(
        key="carry_flip",
        enter=lambda r: _f(r, "vrp") < -2 and _f(r, "vix_pct") >= 0.5,
        exit=lambda r: _f(r, "vrp") > 1,
        enter_title="Realized vol is running above implied in an elevated tape",
        exit_title="Implied vol is back above realized (carry restored)",
        enter_lean=RISING,
        learn=("Implied vol normally exceeds what's later delivered — that gap is what option "
               "sellers earn. When realized overtakes implied while VIX is already above "
               "median, the market is moving more than options were pricing. Historically the "
               "highest-drawdown state at a given VIX level."),
    ),
    EventDef(
        key="vol_shock",
        enter=lambda r: _f(r, "vix_chg1") >= 0.20 or _f(r, "vix_chg5") >= 0.40,
        exit=lambda r: True,
        enter_title="VIX spiked (≥20% in a day or ≥40% in a week)",
        exit_title=None,
        enter_lean=RISING,
        learn=("A spike is a change, not a level: it can happen from VIX 12. Spikes from low "
               "levels mostly mean-revert; spikes into an already-elevated tape are the "
               "dangerous ones. Compare the two base-rate rows below."),
        refractory=10,
    ),
    EventDef(
        key="vol_calm",
        enter=lambda r: _f(r, "vix_pct") <= 0.10,
        exit=lambda r: _f(r, "vix_pct") > 0.25,
        enter_title="VIX dropped into its bottom 10% — protection is historically cheap",
        exit_title=None,
        enter_lean=EASING,
        learn=("Low vol is the most stable state (next-month drawdown >5% is rare) and the "
               "cheapest time to own convexity. It is not a timing signal for a sell-off — "
               "calm regimes can last years — but it's when hedges cost least per unit of "
               "protection."),
    ),
)
EVENT_BY_KEY = {e.key: e for e in EVENTS}


def detect_events(panel: pd.DataFrame) -> pd.DataFrame:
    """Replay every state machine over the panel. Returns one row per transition:
    date, key, kind ('enter'|'exit'), title, lean."""
    rows: list[dict] = []
    feats = panel.dropna(subset=["VIX"]) if "VIX" in panel else panel.iloc[0:0]
    for ev in EVENTS:
        active, last_fire = False, -10**9
        for i, (dt, r) in enumerate(feats.iterrows()):
            if not active:
                if i - last_fire >= ev.refractory and ev.enter(r):
                    active, last_fire = True, i
                    rows.append({"date": dt, "key": ev.key, "kind": "enter",
                                 "title": ev.enter_title, "lean": ev.enter_lean})
                    if ev.refractory:   # momentary: fire-and-forget
                        active = False
            elif ev.exit(r):
                active = False
                if ev.exit_title:
                    rows.append({"date": dt, "key": ev.key, "kind": "exit",
                                 "title": ev.exit_title, "lean": EASING})
    rows += _exposure_shifts(feats)
    out = pd.DataFrame(rows, columns=["date", "key", "kind", "title", "lean"])
    return out.sort_values(["date", "key"]).reset_index(drop=True)


def _exposure_shifts(feats: pd.DataFrame) -> list[dict]:
    """Anchor-based: fire when the scalar has moved RISK_LENS_EXPOSURE_ALERT_STEP from
    the value at the last alert, then re-anchor. Slow drifts alert once, not daily."""
    if "forecast_vol" not in feats:
        return []
    step = config.RISK_LENS_EXPOSURE_ALERT_STEP
    rows, anchor = [], None
    for dt, fv in feats["forecast_vol"].items():
        w = exposure_weight(fv)
        if w is None:
            continue
        if anchor is None:
            anchor = w
            continue
        if abs(w - anchor) >= step - 1e-9:
            down = w < anchor
            rows.append({"date": dt, "key": "exposure_shift", "kind": "down" if down else "up",
                         "title": (f"Vol-managed exposure {'cut' if down else 'raised'} "
                                   f"from {anchor:.0%} to {w:.0%}"),
                         "lean": RISING if down else EASING})
            anchor = w
    return rows


def event_study(panel: pd.DataFrame, events: pd.DataFrame, hist: pd.DataFrame | None = None) -> pd.DataFrame:
    """What happened over the next horizon after each (key, kind) fired. Every firing is
    one observation; overlapping firings are thinned so effective N is honest."""
    from engine.insight.base_rates import effective_n

    h = config.RISK_LENS_HORIZON
    hist = panel if hist is None else hist
    known = hist.dropna(subset=["fwd_rv"])
    base_rv, base_dd = known["fwd_rv"].median(), (known["fwd_mdd"] < -0.05).mean()
    out = []
    for (key, kind), grp in events.groupby(["key", "kind"]):
        d = known.reindex(grp["date"]).dropna(subset=["fwd_rv"])
        if d.empty:
            continue
        out.append({
            "key": key, "kind": kind, "fires": len(grp), "n": len(d),
            "eff_n": effective_n(d.index, known.index, h),
            "fwd_rv_med": float(d["fwd_rv"].median()),
            "p_dd5": float((d["fwd_mdd"] < -0.05).mean()),
            "p_dd10": float((d["fwd_mdd"] < -0.10).mean()),
            "ret_med": float(d["fwd_ret"].median()),
            "carry_win": float((d["carry_edge"] > 0).mean()) if "carry_edge" in d else None,
            "base_fwd_rv_med": float(base_rv), "base_p_dd5": float(base_dd),
        })
    cols = ["key", "kind", "fires", "n", "eff_n", "fwd_rv_med", "p_dd5", "p_dd10", "ret_med",
            "carry_win", "base_fwd_rv_med", "base_p_dd5"]
    return pd.DataFrame(out, columns=cols)


def fires_per_year(events: pd.DataFrame, panel: pd.DataFrame) -> pd.Series:
    span_years = (panel.index[-1] - panel.index[0]).days / 365.25
    days_with_event = events["date"].nunique() / span_years
    s = events.groupby("key").size() / span_years
    s["ANY (email days)"] = days_with_event
    return s.sort_values(ascending=False)
