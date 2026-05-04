"""Sensitivity analysis: transaction-cost grid, tail-risk metrics,
parameter sweep. Direct impact estimates the quant team will ask for.

Usage:
    from sensitivity import tc_sensitivity_table, tail_metrics_table
    tc_table = tc_sensitivity_table(bt)
    tail_table = tail_metrics_table(bt)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from backtest import SLEEVE_COLS, BacktestResults
from stats_rigor import sharpe_annualized

# Number of option legs per sleeve (each leg pays round-trip cost).
SLEEVE_LEGS = {
    "spot_ret": 0,
    "cc":       1,
    "csp":      1,
    "collar":   2,
    "strangle": 2,
}


def apply_transaction_cost(rolls: pd.DataFrame, bp_round_trip_per_leg: float) -> pd.DataFrame:
    """Subtract round-trip cost per leg per roll. Returns new rolls DataFrame."""
    out = rolls.copy()
    cost_per_leg = bp_round_trip_per_leg / 10_000.0
    for sleeve, n_legs in SLEEVE_LEGS.items():
        if sleeve in out.columns:
            out[sleeve] = out[sleeve] - n_legs * cost_per_leg
    return out


def tc_sensitivity_table(bt: BacktestResults, bp_grid: tuple[float, ...] = (0, 5, 10, 20)) -> pd.DataFrame:
    """For each (underlying × sleeve), Sharpe and CAGR at each TC level."""
    rows = []
    for u, rolls in bt.rolls.items():
        for bp in bp_grid:
            adj = apply_transaction_cost(rolls, bp)
            for sleeve in SLEEVE_COLS:
                rets = adj[sleeve].dropna().values
                if len(rets) < 5:
                    continue
                cagr = (1 + rets).prod() ** (12 / len(rets)) - 1
                shp = sharpe_annualized(rets, 12)
                rows.append({
                    "underlying": u, "sleeve": sleeve, "bp_round_trip": int(bp),
                    "cagr": cagr, "sharpe": shp,
                })
    return pd.DataFrame(rows)


def format_tc_grid(df: pd.DataFrame) -> str:
    """Pivot the TC table for human reading: Sharpe by sleeve × bp."""
    lines = ["## Section G — Transaction-Cost Sensitivity", ""]
    lines.append("Round-trip cost per option leg, in basis points of underlying notional.")
    lines.append("CC/CSP have 1 leg per roll; Collar/Strangle have 2 legs (so cost doubles).")
    lines.append("")
    for u in df["underlying"].unique():
        sub = df[df["underlying"] == u]
        lines.append(f"### {u} — Sharpe by TC level")
        sharpe_pivot = sub.pivot(index="sleeve", columns="bp_round_trip", values="sharpe").round(3)
        sharpe_pivot.columns = [f"{c}bp" for c in sharpe_pivot.columns]
        lines.append(sharpe_pivot.to_string())
        lines.append("")
        lines.append(f"### {u} — CAGR by TC level (%)")
        cagr_pivot = sub.pivot(index="sleeve", columns="bp_round_trip", values="cagr") * 100
        cagr_pivot = cagr_pivot.round(2)
        cagr_pivot.columns = [f"{c}bp" for c in cagr_pivot.columns]
        lines.append(cagr_pivot.to_string())
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tail-risk metrics
# ---------------------------------------------------------------------------

def tail_metrics(rets: np.ndarray, periods_per_year: int = 12) -> dict:
    r = np.asarray(rets, dtype=float)
    r = r[~np.isnan(r)]
    if len(r) < 5:
        return {}
    cum = np.cumprod(1 + r)
    cagr = cum[-1] ** (periods_per_year / len(r)) - 1
    max_dd = float((cum / np.maximum.accumulate(cum) - 1).min())
    calmar = cagr / abs(max_dd) if max_dd < 0 else float("inf")

    downside = r[r < 0]
    downside_std = downside.std(ddof=1) * np.sqrt(periods_per_year) if len(downside) > 1 else float("nan")
    sortino = (r.mean() * periods_per_year) / downside_std if downside_std and downside_std > 0 else float("nan")

    es5 = float(r[r <= np.quantile(r, 0.05)].mean()) if len(r) >= 20 else float("nan")
    worst_1m = float(r.min())
    # worst trailing 3-month log return
    log_r = np.log1p(r)
    rolling3 = pd.Series(log_r).rolling(3).sum().values
    worst_3m = float(np.expm1(np.nanmin(rolling3)))

    return {
        "calmar": calmar,
        "sortino": sortino,
        "es5%": es5,
        "worst_1m": worst_1m,
        "worst_3m": worst_3m,
    }


def tail_metrics_table(bt: BacktestResults) -> pd.DataFrame:
    rows = []
    for u, rolls in bt.rolls.items():
        for sleeve in SLEEVE_COLS:
            tm = tail_metrics(rolls[sleeve].dropna().values)
            if tm:
                tm["underlying"] = u
                tm["sleeve"] = sleeve
                rows.append(tm)
    df = pd.DataFrame(rows)
    return df.set_index(["underlying", "sleeve"])


def format_tail_metrics(df: pd.DataFrame) -> str:
    lines = ["## Section H — Tail-Risk Metrics", ""]
    lines.append("Calmar = CAGR / |max_dd|. Sortino uses downside-only std.")
    lines.append("ES5% = mean of bottom 5% monthly returns. Worst-Nm = realized worst N-month chunk.")
    lines.append("")
    show = df.copy()
    show["calmar"] = show["calmar"].round(2)
    show["sortino"] = show["sortino"].round(2)
    show["es5%"] = (show["es5%"] * 100).round(2)
    show["worst_1m"] = (show["worst_1m"] * 100).round(2)
    show["worst_3m"] = (show["worst_3m"] * 100).round(2)
    show.columns = ["calmar", "sortino", "ES5%(pp)", "worst_1m%", "worst_3m%"]
    for u in df.index.get_level_values("underlying").unique():
        lines.append(f"### {u}")
        lines.append(show.loc[u].to_string())
        lines.append("")
    return "\n".join(lines)
