"""NOT WIRED UP (unwired 2026-08-20). Kept for the calibration work, not shipping.

Two defects found after it was built, both of which make the alert mislabelled:

1. The quorum is fake. SPY/QQQ/IWM VRP correlate at 0.84-0.94 over 2,514 overlapping
   sessions -- one signal measured on three correlated indices, not three independent
   confirmations. "3 of 5" is really "1 of 3", so the conjunction argument (agreement
   across channels filters idiosyncratic noise) does not hold on this data. Fix: collapse
   correlated series to one rank, and count distinct signals rather than tickers.

2. High VRP is not stress. vrp = vi - rv*100 (implied minus realized), so a high rank
   means options are rich relative to what actually happened -- a calm or
   post-stress-normalisation condition, and the favourable environment for an option
   writer. In a genuine crash realized vol explodes and VRP compresses or goes negative.
   Only term_9d_30 / term_30_3m (VIX9D/VIX and VIX/VIX3M, where high = backwardation)
   are actual stress measures, and with a floor of 3 they can never fire without VRP.

Rebuilding it means using the vol-index family, which has far deeper history than the
chain-derived metrics: VIX from 1990 (9,254 sessions), VVIX from 2006, VIX3M/VXN/RVX
from 2009, VIX9D from 2011. Stress as a LEVEL claim (VIX percentile) and as a SHAPE
claim (term inversion) are different events that fire at different times -- that choice
is still open.

Original design notes follow.

Rare regime alert: email only when the complex is broadly stressed.

Calibrated against 15.9y of replayed history (2010-09-20 -> 2026-08-20): requiring
3 of 5 qualifying metrics to sit in their top decile simultaneously fires ~4.15
times/year. Raising the band instead would hit a similar rate (band 99 gives ~2.2),
but buys rarity from a tail estimated on ~25 observations, so the threshold itself
becomes noisy. Conjunction keeps each metric's threshold estimated on ~250
observations and gets rarity from agreement across metrics instead.

Expressed as a FRACTION of qualifying metrics, never a fixed count: the number
qualifying varies day to day (2-5 in stored history) because a metric with no
reading drops out, and 12 more chain metrics cross the 252-session credibility
floor around 2027-05. A hardcoded 3 would be unfirable on a thin day and trivial
once the inventory grows -- the same class of bug as the hardcoded date window.

Fires on the RISING EDGE only: entering broad stress is the event. A stress
episode lasting three weeks sends one email, not fifteen.
"""
from __future__ import annotations

import argparse
import datetime
import math
import sys
from pathlib import Path

import pandas as pd

from engine import config

ACTIVE_STATES = ("in_entry", "in_escalate")
DEFAULT_STORE = Path(__file__).resolve().parents[1] / "out" / "monitor" / "ranks.parquet"


def _required(qualifying: int, fraction: float, floor: int) -> int:
    return max(floor, math.ceil(fraction * qualifying))


def assess(df: pd.DataFrame, on: datetime.date, fraction: float, floor: int) -> dict:
    day = df[df["date"] == on]
    qualifying = day[day["n_deep"] >= config.MONITOR_CREDIBILITY_FLOOR_SESSIONS]
    active = qualifying[qualifying["band_state_deep"].isin(ACTIVE_STATES)]
    need = _required(len(qualifying), fraction, floor)
    return {
        "date": on,
        "qualifying": len(qualifying),
        "active": len(active),
        "required": need,
        "triggered": len(qualifying) > 0 and len(active) >= need,
        "names": [f"{r.ticker} {r.metric}" for r in active.itertuples()],
    }


def load(store: Path) -> pd.DataFrame:
    df = pd.read_parquet(store)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


def notify(now: dict) -> None:
    from engine.report.emailer import send

    rows = "".join(f"<li>{n}</li>" for n in sorted(now["names"]))
    body = (
        "<div style='font-family:system-ui,sans-serif;font-size:14px'>"
        "<h2 style='margin:0 0 12px'>Broad regime stress</h2>"
        f"<p><b>{now['active']} of {now['qualifying']}</b> tracked metrics are in their "
        f"top decile simultaneously (threshold: {now['required']}).</p>"
        f"<ul>{rows}</ul>"
        "<p style='margin:16px 0 0;color:#666;font-size:12px'>This is a descriptive "
        "reading of option-market conditions, not a directional call or a "
        "recommendation. It reports that several independent measures are "
        "simultaneously extreme relative to their own history — nothing about "
        "what happens next. Calibrated to fire roughly 4 times a year; you get "
        "one email per episode, not one per day.</p></div>"
    )
    send(subject=f"[vol-diagnostics] broad regime stress: {now['active']}/{now['qualifying']} metrics extreme",
         html_body=body)


def main() -> None:
    p = argparse.ArgumentParser(description="Email when the complex enters broad stress.")
    p.add_argument("--store", type=Path, default=DEFAULT_STORE)
    p.add_argument("--fraction", type=float, default=0.6)
    p.add_argument("--min-active", type=int, default=3)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if not args.store.exists():
        print(f"[regime_alert] no monitor store at {args.store} — nothing to assess.")
        return

    df = load(args.store)
    dates = sorted(df["date"].unique())
    if not dates:
        print("[regime_alert] monitor store is empty.")
        return

    now = assess(df, dates[-1], args.fraction, args.min_active)
    prior = assess(df, dates[-2], args.fraction, args.min_active) if len(dates) > 1 else None

    # Rising edge only: already-firing yesterday means this episode was reported.
    rising = now["triggered"] and not (prior and prior["triggered"])
    print(f"[regime_alert] {now['date']}: {now['active']}/{now['qualifying']} active, "
          f"need {now['required']}, triggered={now['triggered']}, rising={rising}")

    if not rising:
        return
    if args.dry_run:
        print(f"[regime_alert] DRY RUN — would email: {', '.join(now['names'])}")
        return
    notify(now)
    print("[regime_alert] regime alert sent.")


if __name__ == "__main__":
    sys.exit(main())
