"""Phase 4 — decision dashboard.

State + exposure + conditional historical context. No scoring, no
recommendations. Outputs four sections:

    A. Current market state (signal pct ranks + interpretation)
    B. Sleeve mechanics (static cheat sheet — what each tool does)
    C. Sleeve returns by signal quartile (when VRP was X, sleeve Y returned Z)
    D. Closest regime analogs (K-nearest neighbour on signal vector)

The trader synthesizes. Quant team can audit any number against the
underlying data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from backtest import SLEEVE_COLS, BacktestResults
from signals import Signals
from stats_rigor import sharpe_with_ci, q1_q4_bucket_test

BUCKETED_SIGNALS = ("vrp", "term", "skew", "fragility")
NEIGHBOR_FEATURES = ("vrp", "term", "skew", "trend", "dd", "fragility")
K_NEIGHBORS = 12

INTERPRET = {
    "rv30":      "quiet / normal / turbulent",
    "vrp":       "vol cheap / fair / vol rich",
    "term":      "inversion / flat / strong contango",
    "skew":      "tails cheap / normal / tails expensive",
    "trend":     "downtrend / sideways / uptrend",
    "dd":        "in drawdown / mid / near highs",
    "fragility": "calm / mid / fragile",
}

SLEEVE_DESC = {
    "spot_ret": "Buy & hold the index. Reference benchmark.",
    "cc":       "Long u/l + premium from short ~25Δ call. Capped above strike.",
    "csp":      "Cash earning rf + premium from short ~25Δ put. Loses on sharp drops.",
    "collar":   "Long u/l with floor (long ~25Δ put) + ceiling (short ~25Δ call). Defined-risk.",
    "strangle": "Cash + short ~20Δ call + short ~20Δ put. Vol-selling neutral.",
}


def _interp(pct: float, sig: str) -> str:
    if pd.isna(pct):
        return "n/a"
    low, mid, high = INTERPRET[sig].split(" / ")
    if pct < 0.33:
        return low
    if pct > 0.67:
        return high
    return mid


def section_a_state(sigs: Signals) -> str:
    last_dt = sigs.latest_date()
    underlyings = sigs.pct["vrp"].columns.tolist()
    out = [
        f"## Section A — Current Market State ({last_dt.date()})",
        "",
        "Causal 5y rolling percentile rank. 0 = trailing 5y min, 0.5 = median, 1 = max.",
        "",
    ]
    header = f"  {'signal':10s}"
    for u in underlyings:
        header += f" | {u:>5s} {'reading':<22s}"
    out.append(header)
    out.append("  " + "-" * (len(header) - 2))
    for sig in sigs.pct.keys():
        line = f"  {sig:10s}"
        for u in underlyings:
            v = sigs.pct[sig].loc[last_dt, u]
            line += f" | {v:>5.2f} {_interp(v, sig):<22s}"
        out.append(line)
    return "\n".join(out)


def section_b_mechanics() -> str:
    out = ["## Section B — Sleeve Mechanics", ""]
    out.append("What each sleeve gives you. Not a recommendation — context for choice.")
    out.append("")
    for k, v in SLEEVE_DESC.items():
        out.append(f"  {k:9s}  {v}")
    return "\n".join(out)


_PCT_EDGES = [-np.inf, 0.25, 0.50, 0.75, np.inf]
_PCT_LABELS = ["Q1", "Q2", "Q3", "Q4"]


def _bucket_by_pct(values: np.ndarray) -> pd.Categorical:
    return pd.cut(values, bins=_PCT_EDGES, labels=_PCT_LABELS, include_lowest=True)


def _today_quartile(today_val: float) -> str:
    if pd.isna(today_val):
        return "n/a"
    if today_val < 0.25: return "Q1"
    if today_val < 0.50: return "Q2"
    if today_val < 0.75: return "Q3"
    return "Q4"


def section_c_buckets(sigs: Signals, bt: BacktestResults) -> str:
    last_dt = sigs.latest_date()
    out = [
        "## Section C — Sleeve Returns by Signal Quartile",
        "",
        "Signals are already percentile ranks (0-1). Buckets use fixed edges:",
        "  Q1 = pct rank < 0.25 (signal was in bottom 25% of trailing 5y)",
        "  Q2 = 0.25-0.50      Q3 = 0.50-0.75      Q4 ≥ 0.75",
        "",
        "Mean realized monthly return per sleeve, by quartile of signal AT ROLL OPEN.",
        "Today's bucket marked '*'. Last column 'Δ Q4-Q1' is the mean difference",
        "with Welch's t-test p-value: marks ** for p<0.05, * for p<0.10.",
        "",
    ]
    for u in bt.rolls:
        rolls = bt.rolls[u].copy()
        out.append(f"### {u}  ({len(rolls)} rolls)")
        out.append("")
        for sig in BUCKETED_SIGNALS:
            sig_at_open = sigs.pct[sig].reindex(rolls["open"].values)[u].values
            today_val = sigs.pct[sig].loc[last_dt, u]
            today_q = _today_quartile(today_val)
            rolls["_q"] = _bucket_by_pct(sig_at_open)
            mean_ret = rolls.groupby("_q", observed=False)[SLEEVE_COLS].mean() * 100
            hit_ret  = rolls.groupby("_q", observed=False)[SLEEVE_COLS].apply(lambda x: (x > 0).mean()) * 100
            n_per_q  = rolls.groupby("_q", observed=False)[SLEEVE_COLS[0]].count()

            n_str = "/".join(str(int(n_per_q.get(q, 0))) for q in _PCT_LABELS)
            agg = pd.concat({"mean%": mean_ret.round(2), "hit%": hit_ret.round(0)}, axis=0)
            agg.index = pd.MultiIndex.from_tuples(
                [(stat, f"{q}{'*' if q == today_q else ''}") for stat, q in agg.index]
            )

            test_rows = []
            for sleeve in SLEEVE_COLS:
                t = q1_q4_bucket_test(sig_at_open, rolls[sleeve].values)
                if pd.isna(t["p"]):
                    flag = ""
                elif t["p"] < 0.05:
                    flag = "**"
                elif t["p"] < 0.10:
                    flag = "*"
                else:
                    flag = ""
                test_rows.append({
                    "sleeve": sleeve,
                    "Δ Q4-Q1 (pp)": round(t["diff"] * 100, 2) if not pd.isna(t["diff"]) else float("nan"),
                    "t": round(t["t"], 2) if not pd.isna(t["t"]) else float("nan"),
                    "p": round(t["p"], 3) if not pd.isna(t["p"]) else float("nan"),
                    "sig": flag,
                })
            test_df = pd.DataFrame(test_rows).set_index("sleeve")

            out.append(f"  {sig:9s}  today: {today_val:.2f} → {today_q}   n by Q1/Q2/Q3/Q4: {n_str}")
            out.append(agg.to_string())
            out.append("")
            out.append("    Q4-vs-Q1 difference test (** p<0.05, * p<0.10):")
            out.append("    " + test_df.to_string().replace("\n", "\n    "))
            out.append("")
    return "\n".join(out)


def section_d_analog(sigs: Signals, bt: BacktestResults, k: int = K_NEIGHBORS) -> str:
    last_dt = sigs.latest_date()
    out = [
        "## Section D — Closest Regime Analogs",
        "",
        f"K={k} nearest historical roll-opens, Euclidean distance over signal vector:",
        f"  features: {', '.join(NEIGHBOR_FEATURES)}",
        "Mean and dispersion of realized sleeve returns from those analogs.",
        "",
    ]
    for u in bt.rolls:
        rolls = bt.rolls[u]
        today_vec = np.array([sigs.pct[s].loc[last_dt, u] for s in NEIGHBOR_FEATURES])
        if np.isnan(today_vec).any():
            out.append(f"### {u}: today's vector has NaN — skipping")
            continue

        feat = pd.DataFrame({
            s: sigs.pct[s].reindex(rolls["open"].values)[u].values
            for s in NEIGHBOR_FEATURES
        }, index=rolls.index)
        feat = feat.dropna()
        d = np.linalg.norm(feat.values - today_vec, axis=1)
        feat["_d"] = d
        nn = feat.nsmallest(k, "_d")
        nn_rolls = rolls.loc[nn.index, ["open"] + SLEEVE_COLS]

        out.append(f"### {u}")
        out.append(f"Today's vector: " + ", ".join(
            f"{s}={v:.2f}" for s, v in zip(NEIGHBOR_FEATURES, today_vec)
        ))
        out.append("")
        out.append("Closest analogs:")
        for close_dt, dist in nn["_d"].items():
            open_dt = rolls.loc[close_dt, "open"]
            out.append(f"  open {open_dt.date()}  close {close_dt.date()}  d={dist:.3f}")
        out.append("")
        out.append("Realized sleeve returns from those analogs (% monthly, n=" + str(len(nn)) + "):")
        agg = pd.DataFrame({
            "mean%": nn_rolls[SLEEVE_COLS].mean() * 100,
            "std%":  nn_rolls[SLEEVE_COLS].std() * 100,
            "min%":  nn_rolls[SLEEVE_COLS].min() * 100,
            "max%":  nn_rolls[SLEEVE_COLS].max() * 100,
            "hit%":  (nn_rolls[SLEEVE_COLS] > 0).mean() * 100,
        }).round(2)
        out.append(agg.to_string())
        out.append("")
    return "\n".join(out)


SUBPERIOD_SPLITS = [
    ("2010-02-19", "2015-12-31", "Recovery / bull"),
    ("2016-01-01", "2020-12-31", "Late cycle / COVID"),
    ("2021-01-01", "2026-12-31", "Post-COVID / 2022 bear"),
]


def section_e_subperiod(bt: BacktestResults) -> str:
    out = [
        "## Section E — Subperiod Stability",
        "",
        "Same sleeve stats as Phase 3, computed on three rough 5y windows.",
        "Stability check — does the sleeve's behavior persist across regimes,",
        "or is the full-period number averaging two opposite halves?",
        "",
    ]
    for u in bt.rolls:
        rolls = bt.rolls[u]
        out.append(f"### {u}")
        for start, end, label in SUBPERIOD_SPLITS:
            sub = rolls.loc[start:end]
            if len(sub) == 0:
                continue
            rets = sub[SLEEVE_COLS]
            n_per_year = 12
            stats = pd.DataFrame({
                "cagr":   ((1 + rets).prod() ** (n_per_year / max(len(rets), 1)) - 1),
                "vol":    rets.std() * np.sqrt(n_per_year),
                "sharpe": rets.mean() / rets.std() * np.sqrt(n_per_year),
                "max_dd": ((1 + rets).cumprod() / (1 + rets).cumprod().cummax() - 1).min(),
                "hit":    (rets > 0).mean(),
            })
            out.append(f"  {start[:7]} → {end[:7]}  ({label}, n={len(sub)})")
            out.append(stats.round(3).to_string())
            out.append("")
    return "\n".join(out)


def build_dashboard(sigs: Signals, bt: BacktestResults) -> str:
    bar = "=" * 72
    parts = [
        bar,
        "  OPTIONS QUANT — DECISION DASHBOARD",
        bar,
        "",
        section_a_state(sigs),
        "",
        section_b_mechanics(),
        "",
        section_c_buckets(sigs, bt),
        "",
        section_d_analog(sigs, bt),
        "",
        section_e_subperiod(bt),
        "",
        bar,
        "  No score. No recommendation. Decision input, not the decision.",
        "  Caveats: synthetic 90mny IV (POC; calibrated, not Bloomberg-observed),",
        "  0 transaction costs, 0% dividend yield.",
        bar,
    ]
    return "\n".join(parts)
