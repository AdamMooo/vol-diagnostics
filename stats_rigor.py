"""Statistical rigor helpers — bootstrap CIs, t-tests, sample-size honesty.

Why these matter: a Sharpe of 1.22 means nothing without "n=195,
95% CI [0.85, 1.59]". A Q4 minus Q1 bucket-mean difference of 0.6%
means nothing without a p-value to say if 49-vs-49 samples can
distinguish that. The dashboard imports these to wrap any sleeve
stat that's about to influence a decision.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as scs

N_BOOT = 2000
DEFAULT_CI = 0.95


def sharpe_annualized(rets: np.ndarray, periods_per_year: int = 12) -> float:
    if len(rets) < 2:
        return float("nan")
    sd = np.std(rets, ddof=1)
    if sd <= 0:
        return float("nan")
    return float(np.mean(rets) / sd * np.sqrt(periods_per_year))


def bootstrap_ci(
    values: np.ndarray,
    statfn,
    n_boot: int = N_BOOT,
    ci: float = DEFAULT_CI,
    seed: int = 42,
) -> tuple[float, float, float]:
    rng = np.random.default_rng(seed)
    arr = np.asarray(values)
    n = len(arr)
    if n < 5:
        return statfn(arr), float("nan"), float("nan")
    boots = np.empty(n_boot)
    for i in range(n_boot):
        sample = rng.choice(arr, size=n, replace=True)
        boots[i] = statfn(sample)
    lo = float(np.quantile(boots, (1 - ci) / 2))
    hi = float(np.quantile(boots, 1 - (1 - ci) / 2))
    return float(statfn(arr)), lo, hi


def welch_t(a: np.ndarray, b: np.ndarray) -> tuple[float, float, float]:
    """Welch's t-test (unequal variances). Returns (mean_diff, t_stat, p_two_sided)."""
    a, b = np.asarray(a), np.asarray(b)
    if len(a) < 2 or len(b) < 2:
        return float("nan"), float("nan"), float("nan")
    res = scs.ttest_ind(a, b, equal_var=False, nan_policy="omit")
    return float(np.mean(a) - np.mean(b)), float(res.statistic), float(res.pvalue)


def sharpe_with_ci(rets: np.ndarray, periods_per_year: int = 12) -> tuple[float, float, float]:
    return bootstrap_ci(
        np.asarray(rets),
        lambda x: sharpe_annualized(x, periods_per_year),
        n_boot=N_BOOT,
    )


def q1_q4_bucket_test(
    sig_at_open: np.ndarray, returns: np.ndarray
) -> dict[str, float]:
    """Q4-minus-Q1 mean difference and Welch's t-test on a single sleeve."""
    sig = np.asarray(sig_at_open)
    rets = np.asarray(returns)
    valid = ~(np.isnan(sig) | np.isnan(rets))
    sig, rets = sig[valid], rets[valid]
    q1_mask = sig < 0.25
    q4_mask = sig >= 0.75
    if q1_mask.sum() < 5 or q4_mask.sum() < 5:
        return {"diff": float("nan"), "t": float("nan"), "p": float("nan"),
                "n_q1": int(q1_mask.sum()), "n_q4": int(q4_mask.sum())}
    diff, t, p = welch_t(rets[q4_mask], rets[q1_mask])
    return {
        "diff": diff, "t": t, "p": p,
        "n_q1": int(q1_mask.sum()), "n_q4": int(q4_mask.sum()),
    }


def holm_bonferroni(pvals: np.ndarray, alpha: float = 0.05) -> dict[str, np.ndarray]:
    """Holm-Bonferroni step-down family-wise error correction.

    Returns:
        adjusted_p: each raw p multiplied by (m - rank + 1), monotonized
        reject:     boolean array — True if survives FWE at α

    More powerful than naive Bonferroni; controls family-wise Type I.
    """
    p = np.asarray(pvals, dtype=float)
    m = len(p)
    valid = ~np.isnan(p)
    order = np.argsort(np.where(valid, p, np.inf))
    p_sorted = p[order]
    n_valid = int(valid.sum())
    adj = np.full(m, np.nan)
    reject = np.zeros(m, dtype=bool)
    running_max = 0.0
    found_first_fail = False
    for i in range(n_valid):
        # multiplier = m_remaining = (n_valid - i)
        adj_i = min(p_sorted[i] * (n_valid - i), 1.0)
        running_max = max(running_max, adj_i)
        adj[order[i]] = running_max
        if not found_first_fail and adj_i <= alpha:
            reject[order[i]] = True
        else:
            found_first_fail = True
    return {"adj_p": adj, "reject": reject}


def stationary_block_bootstrap_sharpe(
    rets: np.ndarray,
    expected_block_len: int = 6,
    n_boot: int = N_BOOT,
    ci: float = DEFAULT_CI,
    seed: int = 42,
    periods_per_year: int = 12,
) -> tuple[float, float, float]:
    """Politis-Romano stationary block bootstrap for serially-correlated returns.

    Block length is geometrically distributed with mean `expected_block_len`,
    chosen to roughly cover monthly autocorrelation horizons (~6 months).
    Wider CIs than IID bootstrap reflect the true uncertainty for
    autocorrelated series.
    """
    rng = np.random.default_rng(seed)
    arr = np.asarray(rets, dtype=float)
    arr = arr[~np.isnan(arr)]
    n = len(arr)
    if n < 5:
        return float("nan"), float("nan"), float("nan")
    p_continue = 1.0 - 1.0 / max(expected_block_len, 1)
    boots = np.empty(n_boot)
    for b in range(n_boot):
        sample = np.empty(n)
        i = 0
        while i < n:
            start = rng.integers(0, n)
            j = 0
            while i < n and (j == 0 or rng.random() < p_continue):
                sample[i] = arr[(start + j) % n]
                i += 1
                j += 1
        boots[b] = sharpe_annualized(sample, periods_per_year)
    point = sharpe_annualized(arr, periods_per_year)
    lo = float(np.quantile(boots[~np.isnan(boots)], (1 - ci) / 2))
    hi = float(np.quantile(boots[~np.isnan(boots)], 1 - (1 - ci) / 2))
    return point, lo, hi
