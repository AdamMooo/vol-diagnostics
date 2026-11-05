"""
Conditional forward-risk base rates — "the last times it looked like this, what
happened over the next month?"

Three honesty rules from research/risk-environment-conditioning.md, all enforced here:

1. **Effective N, not day count.** 300 analog days with a 21-session forward window are
   ~15 independent observations, not 300. `eff_n` counts non-overlapping windows and
   the credibility gate uses it.
2. **Overlap corrupts the error bar, not the point estimate.** Point estimates use every
   analog day; the CI on the drawdown probability comes from a moving-block bootstrap
   whose block length equals the horizon.
3. **Out-of-sample split.** Every cell is re-estimated on the first and second half of
   history separately; a cell whose halves disagree is labelled unstable.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from engine import config

LEVEL_LABELS = ["bottom 20%", "20–40th pct", "40–60th pct", "60–80th pct", "80–95th pct", "top 5%"]
TERM_LABELS = ["contango", "flat", "inverted"]


def level_cell(pct: float) -> int | None:
    if pct is None or not np.isfinite(pct):
        return None
    bins = config.RISK_LENS_LEVEL_BINS
    return int(min(np.searchsorted(bins, pct, side="left") - 1, len(bins) - 2)) if pct > 0 else 0


def term_cell(term: float) -> int | None:
    if term is None or not np.isfinite(term):
        return None
    return int(np.searchsorted(config.RISK_LENS_TERM_BINS, term, side="right") - 1)


def effective_n(dates: pd.DatetimeIndex, panel_index: pd.DatetimeIndex, horizon: int) -> int:
    """Greedy count of member days at least `horizon` sessions apart — i.e. how many
    forward windows in this cell don't overlap each other."""
    if len(dates) == 0:
        return 0
    pos = np.sort(panel_index.get_indexer(dates))
    n, last = 0, -10**9
    for p in pos:
        if p - last >= horizon:
            n += 1
            last = p
    return n


def block_bootstrap_ci(x: np.ndarray, block: int, reps: int, seed: int = 7,
                       q: tuple[float, float] = (0.05, 0.95)) -> tuple[float, float]:
    """Moving-block bootstrap CI for the mean of a time-ordered series."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n == 0:
        return (float("nan"), float("nan"))
    if n <= block:
        return (float(x.min()), float(x.max()))
    rng = np.random.default_rng(seed)
    k = int(np.ceil(n / block))
    starts = rng.integers(0, n - block + 1, size=(reps, k))
    idx = (starts[..., None] + np.arange(block)).reshape(reps, -1)[:, :n]
    means = x[idx].mean(axis=1)
    return (float(np.quantile(means, q[0])), float(np.quantile(means, q[1])))


@dataclass
class CellStats:
    label: str
    n: int
    eff_n: int
    fwd_rv_med: float | None = None
    fwd_rv_p10: float | None = None
    fwd_rv_p90: float | None = None
    p_dd5: float | None = None
    p_dd5_ci: tuple[float, float] | None = None
    p_dd10: float | None = None
    carry_win: float | None = None
    carry_edge_med: float | None = None
    ret_med: float | None = None
    halves: dict = field(default_factory=dict)
    stable: bool | None = None
    credible: bool = False

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        d["p_dd5_ci"] = list(self.p_dd5_ci) if self.p_dd5_ci else None
        return {k: (None if isinstance(v, float) and not np.isfinite(v) else v) for k, v in d.items()}


def cell_stats(hist: pd.DataFrame, mask: pd.Series, label: str,
               horizon: int | None = None, split: pd.Timestamp | None = None,
               reps: int | None = None) -> CellStats:
    """Forward-outcome distribution over the rows of `hist` selected by `mask`.
    `hist` must already be restricted to rows whose forward window has closed."""
    h = horizon or config.RISK_LENS_HORIZON
    sub = hist[mask.reindex(hist.index, fill_value=False)].dropna(subset=["fwd_rv", "fwd_mdd"])
    eff = effective_n(sub.index, hist.index, h)
    cs = CellStats(label=label, n=len(sub), eff_n=eff)
    if sub.empty:
        return cs
    dd5 = (sub["fwd_mdd"] < -0.05).astype(float).values
    cs.fwd_rv_med = float(sub["fwd_rv"].median())
    cs.fwd_rv_p10 = float(sub["fwd_rv"].quantile(0.10))
    cs.fwd_rv_p90 = float(sub["fwd_rv"].quantile(0.90))
    cs.p_dd5 = float(dd5.mean())
    cs.p_dd5_ci = block_bootstrap_ci(dd5, h, reps or config.RISK_LENS_BOOTSTRAP_REPS)
    cs.p_dd10 = float((sub["fwd_mdd"] < -0.10).mean())
    cs.ret_med = float(sub["fwd_ret"].median())
    if "carry_edge" in sub and sub["carry_edge"].notna().any():
        cs.carry_win = float((sub["carry_edge"] > 0).mean())
        cs.carry_edge_med = float(sub["carry_edge"].median())
    cs.credible = eff >= config.RISK_LENS_MIN_EFF_N

    if split is None and len(hist):
        split = hist.index[len(hist) // 2]
    if split is not None:
        for name, part in (("early", sub[sub.index < split]), ("late", sub[sub.index >= split])):
            cs.halves[name] = {
                "n": len(part),
                "eff_n": effective_n(part.index, hist.index, h),
                "fwd_rv_med": float(part["fwd_rv"].median()) if len(part) else None,
                "p_dd5": float((part["fwd_mdd"] < -0.05).mean()) if len(part) else None,
            }
        cs.stable = _halves_agree(cs.halves, hist)
    return cs


def _halves_agree(halves: dict, hist: pd.DataFrame) -> bool | None:
    """Stable = both halves have data and sit on the same side of the unconditional
    median forward RV (i.e. the cell's *direction* replicates out of sample)."""
    e, l = halves.get("early", {}), halves.get("late", {})
    if not e.get("n") or not l.get("n") or e["fwd_rv_med"] is None or l["fwd_rv_med"] is None:
        return None
    base = float(hist["fwd_rv"].median())
    return (e["fwd_rv_med"] - base) * (l["fwd_rv_med"] - base) > 0 or \
        abs(e["fwd_rv_med"] - l["fwd_rv_med"]) < 0.15 * base


def cell_masks(hist: pd.DataFrame, today: pd.Series) -> dict[str, tuple[pd.Series, str, pd.Timestamp | None]]:
    """Today's analog cells at increasing specificity: key → (row mask, label, OOS split).
    Shared by the drawdown base rates and the strategy payoffs so both condition on the
    same analogs."""
    split = hist.index[len(hist) // 2] if len(hist) else None
    out = {"unconditional": (pd.Series(True, index=hist.index), "all sessions since 1992", split)}
    lc = level_cell(today.get("vix_pct"))
    if lc is None:
        return out
    lvl = hist["vix_pct"].map(level_cell) == lc
    out["level"] = (lvl, f"VIX in its {LEVEL_LABELS[lc]}", split)

    tc = term_cell(today.get("term"))
    if tc is not None and "term" in hist and hist["term"].notna().any():
        # VIX3M starts 2009: split the OOS halves inside the span the feature exists,
        # or the "early" half is empty by construction.
        has_term = hist.index[hist["term"].notna()]
        out["level_term"] = (lvl & (hist["term"].map(term_cell) == tc),
                             f"VIX in its {LEVEL_LABELS[lc]} + curve {TERM_LABELS[tc]}",
                             has_term[len(has_term) // 2])

    vrp = today.get("vrp")
    if vrp is not None and np.isfinite(vrp):
        neg = vrp < 0
        out["level_vrp"] = (lvl & ((hist["vrp"] < 0) if neg else (hist["vrp"] >= 0)),
                            f"VIX in its {LEVEL_LABELS[lc]} + realized {'above' if neg else 'below'} implied",
                            split)
    return out


def conditional_read(hist: pd.DataFrame, today: pd.Series, horizon: int | None = None,
                     reps: int | None = None) -> dict:
    """Base rates for today's state at increasing specificity.

    Returns {"unconditional", "level", "level_term", "level_vrp", "primary"}; `primary`
    names the most specific credible cell — specificity never buys a thinner sample
    than RISK_LENS_MIN_EFF_N.
    """
    h = horizon or config.RISK_LENS_HORIZON
    hist = hist.dropna(subset=["fwd_rv"])
    out: dict = {k: cell_stats(hist, m, label, horizon=h, split=split, reps=reps)
                 for k, (m, label, split) in cell_masks(hist, today).items()}
    out["primary"] = "unconditional"
    for k in ("level", "level_term"):
        if k in out and out[k].credible:
            out["primary"] = k
    # Negative VRP inside an elevated tape is the one VRP state with its own
    # signal (research: P(dd>5%) 0.46 vs 0.25 at the same level) — let it lead.
    if "level_vrp" in out and today.get("vrp") < 0 and out["level_vrp"].credible \
            and level_cell(today.get("vix_pct")) >= 3:
        out["primary"] = "level_vrp"
    return out
