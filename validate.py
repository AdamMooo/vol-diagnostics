"""Walk-forward and out-of-sample validation of signal-to-sleeve rules.

Q: Does *following* the conditional historical patterns we surface in
   Section C actually pay off out-of-sample, or is the in-sample
   apparent edge curve-fitting?

A: Run a true walk-forward where at each roll date t we use only
   information available at t-1 to choose a sleeve, then observe the
   realized return at t+1. Aggregate. Compare to passive baselines
   (always-CC, always-Strangle, equal-weight).

Conclusions of T1a (multiple-comparison) suggest the in-sample edges
won't survive. This module *measures* that prediction.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from backtest import SLEEVE_COLS, BacktestResults
from signals import Signals
from stats_rigor import sharpe_annualized, stationary_block_bootstrap_sharpe

OOS_TRAIN_END = "2017-12-31"  # ≈ 50/50 split: 2010-2017 train / 2018-2026 test


def _bucket_quartile(pct_value: float) -> str:
    if pd.isna(pct_value):
        return "n/a"
    if pct_value < 0.25: return "Q1"
    if pct_value < 0.50: return "Q2"
    if pct_value < 0.75: return "Q3"
    return "Q4"


@dataclass
class WalkForwardResult:
    rule_name: str
    rets: pd.Series  # realized returns following the rule
    sleeve_choice: pd.Series  # which sleeve was chosen at each roll
    summary: dict  # CAGR, Sharpe, SE, etc.


def _summarize(rets: pd.Series, label: str, periods_per_year: int = 12) -> dict:
    r = rets.dropna()
    if len(r) < 5:
        return {"label": label, "n": len(r)}
    growth = (1 + r).prod()
    cagr = growth ** (periods_per_year / len(r)) - 1
    vol = r.std() * np.sqrt(periods_per_year)
    sharpe = sharpe_annualized(r.values, periods_per_year)
    _, lo, hi = stationary_block_bootstrap_sharpe(r.values, expected_block_len=6)
    cum = (1 + r).cumprod()
    max_dd = float((cum / cum.cummax() - 1).min())
    hit = float((r > 0).mean())
    return {
        "label": label, "n": len(r),
        "cagr": cagr, "vol": vol, "sharpe": sharpe,
        "sharpe_block_ci": (lo, hi),
        "max_dd": max_dd, "hit": hit,
    }


def quartile_tilt_rule(
    signal_at_open: pd.Series,
    rolls: pd.DataFrame,
    sleeve_q4: str,
    sleeve_q1: str,
    sleeve_default: str,
) -> tuple[pd.Series, pd.Series]:
    """At each roll, pick sleeve based on signal quartile at OPEN.

    Q4 → sleeve_q4, Q1 → sleeve_q1, else → sleeve_default.
    Returns (realized_returns, chosen_sleeve_per_roll).
    """
    chosen, rets = [], []
    idx = []
    for close_dt, row in rolls.iterrows():
        sig_val = signal_at_open.loc[row["open"]] if row["open"] in signal_at_open.index else np.nan
        q = _bucket_quartile(sig_val)
        if q == "Q4":
            sleeve = sleeve_q4
        elif q == "Q1":
            sleeve = sleeve_q1
        else:
            sleeve = sleeve_default
        chosen.append(sleeve)
        rets.append(row[sleeve])
        idx.append(close_dt)
    return pd.Series(rets, index=idx, name="rule_ret"), pd.Series(chosen, index=idx, name="sleeve")


def oos_split_test(
    sigs: Signals,
    bt: BacktestResults,
    underlying: str,
    signal: str,
    train_end: str = OOS_TRAIN_END,
) -> dict:
    """Train: pick the (q4_sleeve, q1_sleeve, default) by best in-sample mean.
    Test: apply the chosen rule on holdout, compare to passive baselines.
    """
    rolls = bt.rolls[underlying]
    sig_panel = sigs.pct[signal][underlying]

    train_mask = rolls.index <= pd.Timestamp(train_end)
    test_mask = ~train_mask
    train_rolls = rolls.loc[train_mask]
    test_rolls = rolls.loc[test_mask]

    if len(train_rolls) < 30 or len(test_rolls) < 30:
        return {"underlying": underlying, "signal": signal, "skipped": True}

    sig_train_at_open = sig_panel.reindex(train_rolls["open"].values).values
    q1_mask_t = sig_train_at_open < 0.25
    q4_mask_t = sig_train_at_open >= 0.75

    if q1_mask_t.sum() < 5 or q4_mask_t.sum() < 5:
        return {"underlying": underlying, "signal": signal, "skipped": True}

    means_q1 = train_rolls[SLEEVE_COLS].iloc[q1_mask_t].mean()
    means_q4 = train_rolls[SLEEVE_COLS].iloc[q4_mask_t].mean()
    means_mid = train_rolls[SLEEVE_COLS].iloc[~(q1_mask_t | q4_mask_t)].mean()

    sleeve_q4 = means_q4.idxmax()
    sleeve_q1 = means_q1.idxmax()
    sleeve_def = means_mid.idxmax()

    rule_train, _ = quartile_tilt_rule(sig_panel, train_rolls, sleeve_q4, sleeve_q1, sleeve_def)
    rule_test, choice_test = quartile_tilt_rule(sig_panel, test_rolls, sleeve_q4, sleeve_q1, sleeve_def)

    out = {
        "underlying": underlying, "signal": signal,
        "rule": f"Q4→{sleeve_q4}  Q1→{sleeve_q1}  else→{sleeve_def}",
        "train": _summarize(rule_train, "rule (train)"),
        "test":  _summarize(rule_test, "rule (test)"),
        "passive": {
            sleeve: _summarize(test_rolls[sleeve], f"always {sleeve} (test)")
            for sleeve in SLEEVE_COLS
        },
        "n_train": len(train_rolls),
        "n_test": len(test_rolls),
        "skipped": False,
    }
    return out


def run_walk_forward(sigs: Signals, bt: BacktestResults, train_end: str = OOS_TRAIN_END):
    """Run OOS test for each (underlying × signal) and return a tidy DataFrame."""
    rows = []
    for u in bt.rolls:
        for sig in ("vrp", "term", "skew", "fragility", "trend", "dd"):
            res = oos_split_test(sigs, bt, u, sig, train_end)
            if res.get("skipped"):
                continue
            test = res["test"]
            best_passive = max(
                res["passive"].values(),
                key=lambda s: s.get("sharpe", -np.inf),
            )
            rows.append({
                "underlying": u,
                "signal": sig,
                "rule": res["rule"],
                "rule_test_cagr": test["cagr"],
                "rule_test_sharpe": test["sharpe"],
                "rule_test_ci": test["sharpe_block_ci"],
                "best_passive_label": best_passive["label"],
                "best_passive_cagr": best_passive["cagr"],
                "best_passive_sharpe": best_passive["sharpe"],
                "test_n": test["n"],
            })
    return pd.DataFrame(rows)


def format_walk_forward_report(df: pd.DataFrame) -> str:
    if len(df) == 0:
        return "No walk-forward results — insufficient data after split."
    lines = [
        "=" * 72,
        "  WALK-FORWARD VALIDATION  (Train ≤ 2017-12-31, Test 2018-01+)",
        "=" * 72,
        "",
        "Train: pick best sleeve per quartile from in-sample means.",
        "Test:  apply the rule to holdout, compare vs always-best-passive sleeve.",
        "",
        "If 'rule_test_sharpe' beats 'best_passive_sharpe' AND the CI excludes 0,",
        "we have evidence the conditional rule adds value out-of-sample. Otherwise",
        "the in-sample bucket effect was not predictive.",
        "",
    ]
    for _, row in df.iterrows():
        lines.append(f"### {row['underlying']} / {row['signal']}")
        lines.append(f"  Rule:  {row['rule']}")
        lo, hi = row["rule_test_ci"]
        lines.append(
            f"  Test:  Sharpe {row['rule_test_sharpe']:+.2f}  "
            f"CI95 [{lo:+.2f}, {hi:+.2f}]  "
            f"CAGR {row['rule_test_cagr']*100:+.1f}%  n={row['test_n']}"
        )
        lines.append(
            f"  Best passive in test:  {row['best_passive_label']}  "
            f"Sharpe {row['best_passive_sharpe']:+.2f}  CAGR {row['best_passive_cagr']*100:+.1f}%"
        )
        delta_sharpe = row["rule_test_sharpe"] - row["best_passive_sharpe"]
        delta_cagr = (row["rule_test_cagr"] - row["best_passive_cagr"]) * 100
        verdict = "EDGE" if delta_sharpe > 0.10 and lo > 0 else "NO EDGE"
        lines.append(
            f"  Δ vs best passive:  Sharpe {delta_sharpe:+.2f}  "
            f"CAGR {delta_cagr:+.1f}pp   →  {verdict}"
        )
        lines.append("")
    return "\n".join(lines)
