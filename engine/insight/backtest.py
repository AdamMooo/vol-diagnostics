"""
Risk Lens evidence — regenerates research/risk-lens-findings.md from the stores.

    python -m engine.insight.backtest                # print markdown
    python -m engine.insight.backtest --write        # also overwrite research/risk-lens-findings.md

Five questions, each answered with the out-of-sample split visible:
  1. Which axes carry information about next-month risk, beyond VIX level?
  2. What do the conditioning cells look like (and do they replicate in both halves)?
  3. How often does each event fire, and what followed it?
  4. Does the vol-managed exposure scalar earn its place? (dashboard context only)
  5. Is the lens itself calibrated? Point-in-time replay: at each monthly as-of date,
     using only history known then, the lens's P(dd>5%) vs what actually happened.
"""
from __future__ import annotations

import argparse
import datetime
import pathlib

import numpy as np
import pandas as pd
from scipy import stats as st

from engine import config
from engine.insight import base_rates as br
from engine.insight import events as ev
from engine.insight.exposure import backtest as exposure_backtest
from engine.insight.panel import known_by, load_panel

FINDINGS = pathlib.Path(__file__).resolve().parents[2] / "research" / "risk-lens-findings.md"


def _md(df: pd.DataFrame, floatfmt: str = "{:.3f}") -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(
            floatfmt.format(v) if isinstance(v, (float, np.floating)) and np.isfinite(v) else str(v)
            for v in r.values) + " |")
    return "\n".join(out)


def axis_information(panel: pd.DataFrame) -> pd.DataFrame:
    d = panel.dropna(subset=["fwd_rv", "VIX"])
    lv = np.log(d["VIX"])
    y = np.log(d["fwd_rv"])

    def resid(a: pd.Series) -> pd.Series:
        m = a.notna()
        coef = np.polyfit(lv[m], a[m], 1)
        return (a - np.polyval(coef, lv)).where(m)

    yr = resid(y)
    rows = [{"axis": "VIX level", "n": len(d), "rho_raw": st.spearmanr(d["VIX"], d["fwd_rv"])[0], "rho_given_VIX": np.nan}]
    for c, name in [("rv20", "realized vol 20d"), ("term", "term VIX/VIX3M"), ("vrp", "VRP (IV−RV)"),
                    ("VVIX", "VVIX"), ("vix_chg5", "VIX 5d change")]:
        if c not in d:
            continue
        x = d[c].astype(float)
        m = x.notna()
        rows.append({"axis": name, "n": int(m.sum()),
                     "rho_raw": st.spearmanr(x[m], d["fwd_rv"][m])[0],
                     "rho_given_VIX": st.spearmanr(resid(x)[m], yr[m])[0]})
    return pd.DataFrame(rows)


def _cell_table(hist: pd.DataFrame, groups: pd.Series, labels: dict, split=None) -> pd.DataFrame:
    rows = []
    for g in sorted(groups.dropna().unique()):
        cs = br.cell_stats(hist, groups == g, labels.get(g, str(g)), split=split, reps=200)
        rows.append({"cell": cs.label, "n": cs.n, "eff_n": cs.eff_n, "fwd_rv_med": cs.fwd_rv_med,
                     "p_dd5": cs.p_dd5, "p_dd5_ci": f"{cs.p_dd5_ci[0]:.2f}–{cs.p_dd5_ci[1]:.2f}" if cs.p_dd5_ci else "",
                     "p_dd10": cs.p_dd10, "carry_win": cs.carry_win,
                     "early_p_dd5": cs.halves.get("early", {}).get("p_dd5"),
                     "late_p_dd5": cs.halves.get("late", {}).get("p_dd5"), "stable": cs.stable})
    return pd.DataFrame(rows)


def _thin(pos: np.ndarray, horizon: int) -> np.ndarray:
    keep, last = [], -10**9
    for i, p in enumerate(np.sort(pos)):
        if p - last >= horizon:
            keep.append(i)
            last = p
    return np.asarray(keep, dtype=int)


def event_significance(events: pd.DataFrame, hist: pd.DataFrame) -> pd.DataFrame:
    """Does each event's P(dd>5%) differ from the base rate, after correcting for testing
    every (event, enter/exit) pair at once?

    Each test uses only non-overlapping firings (thinned to one per 21-session window), so
    the binomial test's independence assumption holds. Two-sided exact binomial vs the
    unconditional rate, then Holm (family-wise) and Benjamini–Hochberg (FDR) at 5%."""
    h = config.RISK_LENS_HORIZON
    known = hist.dropna(subset=["fwd_mdd"])
    base = float((known["fwd_mdd"] < -0.05).mean())
    rows = []
    for (key, kind), grp in events.groupby(["key", "kind"]):
        dates = known.index.intersection(pd.DatetimeIndex(grp["date"]))
        if len(dates) == 0:
            continue
        pos = known.index.get_indexer(dates)
        kept = np.sort(pos)[_thin(pos, h)]
        hits = int((known["fwd_mdd"].iloc[kept] < -0.05).sum())
        n = len(kept)
        rows.append({"event": f"{key}:{kind}", "n_indep": n, "hits": hits,
                     "p_dd5_indep": hits / n, "base_p_dd5": base,
                     "p_value": float(st.binomtest(hits, n, base).pvalue)})
    df = pd.DataFrame(rows).sort_values("p_value").reset_index(drop=True)
    m = len(df)
    if m == 0:
        return df
    p = df["p_value"].to_numpy()
    holm = np.minimum(1, np.maximum.accumulate((m - np.arange(m)) * p))
    bh = np.minimum(1, np.minimum.accumulate(((m / np.arange(1, m + 1)) * p)[::-1])[::-1])
    df["p_holm"], df["p_bh"] = holm, bh
    df["survives_holm"], df["survives_bh"] = holm < 0.05, bh < 0.05
    return df


def calibration_replay(panel: pd.DataFrame, start: str = "2000-01-01", step: int = 21) -> dict:
    """At every `step`-th session, build the conditional read from history known then
    and record the primary cell's P(dd>5%) next to the realized outcome. Non-overlapping
    by construction (step == horizon), so the Brier comparison is on independent draws."""
    d = panel.dropna(subset=["VIX", "vix_pct", "fwd_mdd"])
    dates = d.loc[start:].index[::step]
    recs = []
    for t in dates:
        hist = known_by(panel, t)
        cond = br.conditional_read(hist, panel.loc[t], reps=1)
        p = cond[cond["primary"]].p_dd5
        p0 = cond["unconditional"].p_dd5
        recs.append({"date": t, "p_lens": p, "p_base": p0, "hit": float(panel.loc[t, "fwd_mdd"] < -0.05),
                     "cell": cond["primary"]})
    r = pd.DataFrame(recs).dropna()
    brier = lambda p: float(((r[p] - r["hit"]) ** 2).mean())
    r["bucket"] = pd.cut(r["p_lens"], [0, .1, .2, .3, .45, 1])
    rel = r.groupby("bucket", observed=True).agg(n=("hit", "size"), predicted=("p_lens", "mean"),
                                                 realized=("hit", "mean")).reset_index()
    rel["bucket"] = rel["bucket"].astype(str)
    mid = r["date"].iloc[len(r) // 2]
    halves = {}
    for name, part in (("early", r[r["date"] < mid]), ("late", r[r["date"] >= mid])):
        bl = float(((part["p_lens"] - part["hit"]) ** 2).mean())
        bb = float(((part["p_base"] - part["hit"]) ** 2).mean())
        halves[name] = {"n": len(part), "brier_lens": bl, "brier_base": bb, "skill": 1 - bl / bb}
    return {"n": len(r), "brier_lens": brier("p_lens"), "brier_base": brier("p_base"),
            "skill": 1 - brier("p_lens") / brier("p_base"), "reliability": rel, "halves": halves,
            "cells_used": r["cell"].value_counts().to_dict()}


def build_report(panel: pd.DataFrame) -> str:
    asof = panel.dropna(subset=["VIX"]).index[-1]
    hist = known_by(panel, asof).dropna(subset=["fwd_rv", "vix_pct"])
    out = [
        "# Risk Lens — evidence",
        f"Generated {datetime.date.today()} by `python -m engine.insight.backtest --write` · "
        f"data {hist.index[0].date()} → {asof.date()} · horizon {config.RISK_LENS_HORIZON} sessions · "
        f"SPX (^GSPC) + CBOE vol indices. **Do not hand-edit — regenerate.**",
        "",
        "Outcome definitions: `fwd_rv` = realized vol over the next 21 sessions (annualized %); "
        "`p_dd5` = share of windows whose worst close fell >5% below the start; `carry_win` = "
        "share of windows where VIX exceeded the vol then delivered. `eff_n` = non-overlapping "
        "windows. `early`/`late` = same cell re-estimated on each half of history.",
        "",
        "## 1. Which axes carry information beyond VIX level?",
        "Spearman correlation with next-month realized vol; `rho_given_VIX` partials out log VIX.",
        "",
        _md(axis_information(panel)),
        "",
        "**Read:** VIX level is the dominant axis. Every other layer adds little once level is "
        "known — most of the system's computational surface re-describes one factor. The lens "
        "therefore conditions on level first and only adds term shape / VRP sign where they "
        "carry their own signal (sections 2b, 2c).",
        "",
        "## 2a. Forward risk by VIX level (10y rolling percentile)",
        "",
        _md(_cell_table(hist, hist["vix_pct"].map(br.level_cell), dict(enumerate(br.LEVEL_LABELS)))),
        "",
    ]
    t = hist.dropna(subset=["term"])
    split_t = t.index[len(t) // 2]
    lvl3 = pd.cut(t["vix_pct"], [0, .5, .8, 1], labels=["VIX < median", "VIX 50–80th", "VIX > 80th"])
    tc = t["term"].map(br.term_cell)
    grp = lvl3.astype(str) + " · " + tc.map(dict(enumerate(br.TERM_LABELS))).astype(str)
    out += ["## 2b. Term shape within level (confound check)",
            "If inversion only proxied for level, the term rows inside each level band would match. "
            "They don't at elevated levels — shape carries its own information there.", "",
            _md(_cell_table(t, grp, {}, split=split_t)), ""]
    lvl3h = pd.cut(hist["vix_pct"], [0, .5, .8, 1], labels=["VIX < median", "VIX 50–80th", "VIX > 80th"])
    vs = np.where(hist["vrp"] < 0, "realized > implied", "implied ≥ realized")
    out += ["## 2c. VRP sign within level",
            "High VRP is the *calm* state. Realized overtaking implied inside an elevated tape is the stress state.", "",
            _md(_cell_table(hist, lvl3h.astype(str) + " · " + pd.Series(vs, index=hist.index), {})), ""]

    events = ev.detect_events(panel)
    fpy = ev.fires_per_year(events, panel).rename("per_year").reset_index().rename(columns={"index": "event"})
    study = ev.event_study(panel, events[events["date"] <= hist.index[-1]], hist)
    out += ["## 3. Events — frequency and what followed",
            "Each event is a hysteresis state machine on the SPX vol complex only (QQQ/IWM are "
            "context, never extra votes). 'ANY' = days an email would have gone out.", "",
            _md(fpy, "{:.2f}"), "", _md(study.drop(columns=["base_fwd_rv_med"])), "",
            f"Baseline: median fwd vol {study['base_fwd_rv_med'].iloc[0]:.1f}, p_dd5 {study['base_p_dd5'].iloc[0]:.3f}. "
            "Note exits are not all-clears: several are still followed by above-normal risk, which "
            "is why the email states each event's own history instead of a fixed lean.", ""]

    sig = event_significance(events[events["date"] <= hist.index[-1]], hist)
    n_holm = int(sig["survives_holm"].sum()) if len(sig) else 0
    n_bh = int(sig["survives_bh"].sum()) if len(sig) else 0
    out += ["## 3b. Multiple-testing check on events",
            f"{len(sig)} event comparisons (each enter/exit vs the base rate) are tested at once, so "
            "raw p-values overstate. Each test uses non-overlapping firings only (one per 21-session "
            "window), exact two-sided binomial vs the unconditional P(dd>5%), then Holm (family-wise) "
            "and Benjamini–Hochberg (false-discovery) corrections at 5%.", "",
            _md(sig, "{:.3f}"), "",
            f"**Read:** {n_holm} of {len(sig)} survive Holm, {n_bh} survive BH. Events that do not "
            "survive still email (they mark real state changes), but their 'historically followed by' "
            "read should be treated as suggestive, not established.", ""]

    bt = exposure_backtest(panel)
    rows = []
    for name, p in bt["periods"].items():
        for strat in ("buy_hold", "vol_managed"):
            rows.append({"period": f"{name} ({p['from']}→{p['to']})", "strategy": strat, **p[strat]})
    out += ["## 4. Vol-managed exposure (Moreira–Muir) — dashboard context only",
            f"weight = min({config.RISK_LENS_MAX_WEIGHT:.1f}, {config.RISK_LENS_TARGET_VOL:.0f} / (½·VIX + ½·RV20)), "
            f"weekly rebalance, no costs, no cash yield. Average weight {bt['avg_weight']:.2f}.", "",
            _md(pd.DataFrame(rows)), "",
            "**Read:** a drawdown reducer, not a return engine. Judge it on max_dd / worst_month. "
            "It costs CAGR, the 15% target was chosen with full-sample knowledge, and out-of-sample "
            "studies find vol-managed gains fragile. Decision 2026-11-03: it is a weekly timing rule, "
            "so it appears only as labelled context on the dashboard — never in the email, never as "
            "an event, never in `risk_lens.json`.", ""]

    cal = calibration_replay(panel)
    out += ["## 5. Is the lens calibrated? (point-in-time replay, 2000→)",
            "Every 21st session, the lens is rebuilt from history known *at that date* and its "
            "primary-cell P(dd>5%) is scored against what happened. Brier skill > 0 means the "
            "conditioning beats the unconditional base rate out of sample.", "",
            f"- n = {cal['n']} independent monthly reads; cells used: {cal['cells_used']}",
            f"- Brier: lens {cal['brier_lens']:.4f} vs unconditional {cal['brier_base']:.4f} → "
            f"**skill {cal['skill']:+.1%}**",
            *[f"- {k}: n={v['n']}, skill {v['skill']:+.1%}" for k, v in cal["halves"].items()],
            "",
            "**This skill is an upper bound, not a floor.** Only the probabilities are point-in-time. "
            "The cell boundaries (`RISK_LENS_LEVEL_BINS`, `RISK_LENS_TERM_BINS`), the event thresholds "
            "and the choice of conditioning axes were all designed after looking at the full history, "
            "so some of the measured edge is selection. Expect less live.",
            "", "Reliability (predicted vs realized drawdown frequency):", "",
            _md(cal["reliability"]), "",
            "Tested 2026-11-02 and not adopted: Bühlmann credibility shrinkage of each cell toward the "
            "unconditional rate (k = 5–40 pseudo-observations) left skill unchanged (±0.5pp). The low "
            "bucket stays slightly over-confident (predicts ~4%, realized ~9%) — read calm-state drawdown "
            "odds as a floor, not a point.", ""]
    return "\n".join(out)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--write", action="store_true")
    p.add_argument("--refresh", action="store_true")
    a = p.parse_args()
    import warnings
    warnings.filterwarnings("ignore")
    md = build_report(load_panel(refresh=a.refresh))
    print(md)
    if a.write:
        FINDINGS.write_text(md + "\n", encoding="utf-8")
        print(f"\n[insight] wrote {FINDINGS}")


if __name__ == "__main__":
    main()
