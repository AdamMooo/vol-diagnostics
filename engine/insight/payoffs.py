"""
Conditional strategy payoffs — "the last times it looked like this, what did selling
(or buying) each option structure actually return over the next month?"

Each structure is opened at a session's close on SPX, priced Black-76 with a flat
sigma = VIX (forward = spot, zero carry), strikes placed in sigma units of the 1-month
move, held to expiry `RISK_LENS_HORIZON` sessions later and settled on the realised
close. The return is P&L / capital at risk: max loss for defined-risk structures and for
the short put (cash-secured collateral net of premium), spot notional for the short
straddle (its loss is unbounded). A buyer's return is the seller's sign-flipped P&L.

Known biases, all stated where the table is shown:
- Flat VIX smile. Real ATM implied usually sits below VIX (flattering the straddle
  seller) and real OTM puts above it (understating put credits and put-wing costs).
- Held to expiry: no early management, no fills, no fees.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm

from engine import config
from engine.insight import base_rates as br

# key → (label, capital basis, legs of (type, strike in sigma units, signed qty))
STRUCTURES: dict[str, tuple[str, str, tuple[tuple[str, float, int], ...]]] = {
    "short_straddle": ("Short ATM straddle", "spot", (("put", 0.0, -1), ("call", 0.0, -1))),
    "short_put": ("Short 1σ put (cash-secured)", "max_loss", (("put", -1.0, -1),)),
    "put_spread": ("Put credit spread 1σ/2σ", "max_loss", (("put", -1.0, -1), ("put", -2.0, 1))),
    "iron_condor": ("Iron condor 1σ/2σ", "max_loss",
                    (("put", -1.0, -1), ("put", -2.0, 1), ("call", 1.0, -1), ("call", 2.0, 1))),
    "long_put": ("Long 1σ put (hedge)", "max_loss", (("put", -1.0, 1),)),
}


def _price(spot, strike, sd, kind):
    d1 = np.log(spot / strike) / sd + sd / 2
    call = spot * norm.cdf(d1) - strike * norm.cdf(d1 - sd)
    return call if kind == "call" else call - spot + strike


def _intrinsic(x, strike, kind):
    return np.maximum(x - strike, 0) if kind == "call" else np.maximum(strike - x, 0)


def structure_return(spot, vol, spot_T, key: str, horizon: int | None = None) -> np.ndarray:
    """Return on capital for one structure, vectorised over entry rows.
    `vol` is annualised in vol points (VIX units)."""
    _, basis, legs = STRUCTURES[key]
    spot, spot_T = np.asarray(spot, float), np.asarray(spot_T, float)
    sd = np.asarray(vol, float) / 100 * np.sqrt((horizon or config.RISK_LENS_HORIZON) / 252)
    strikes = [spot * np.exp(z * sd) for _, z, _ in legs]
    cost = sum(q * _price(spot, k, sd, t) for (t, _, q), k in zip(legs, strikes))

    def pnl_at(x):
        return sum(q * _intrinsic(x, k, t) for (t, _, q), k in zip(legs, strikes)) - cost

    if basis == "spot":
        capital = spot
    else:  # piecewise-linear payoff: worst case sits at zero or at a strike
        capital = -np.min([pnl_at(np.zeros_like(spot)), *(pnl_at(k) for k in strikes)], axis=0)
    return pnl_at(spot_T) / capital


def add_payoffs(df: pd.DataFrame, horizon: int | None = None) -> pd.DataFrame:
    """Adds `pnl_<key>` columns (fractional return on capital); NaN where the forward
    window is unfinished or VIX is missing."""
    h = horizon or config.RISK_LENS_HORIZON
    spot_T = df["spx"].shift(-h)
    ok = spot_T.notna() & df["VIX"].notna() & df["spx"].notna()
    for key in STRUCTURES:
        r = np.full(len(df), np.nan)
        r[ok.values] = structure_return(df["spx"][ok], df["VIX"][ok], spot_T[ok], key, h)
        df[f"pnl_{key}"] = r
    return df


def strategy_stats(hist: pd.DataFrame, mask: pd.Series, label: str, split: pd.Timestamp | None,
                   horizon: int | None = None, reps: int | None = None) -> dict:
    """Seller-side return distribution per structure over the cell's rows. Same honesty
    rules as base_rates: effective N, block-bootstrap CI on the mean, early/late split."""
    h = horizon or config.RISK_LENS_HORIZON
    sub = hist[mask.reindex(hist.index, fill_value=False)]
    rows = []
    for key, (name, _, _) in STRUCTURES.items():
        x = sub[f"pnl_{key}"].dropna()
        row = {"key": key, "structure": name, "n": len(x),
               "eff_n": br.effective_n(x.index, hist.index, h)}
        if len(x):
            ci = br.block_bootstrap_ci(x.values, h, reps or config.RISK_LENS_BOOTSTRAP_REPS)
            halves = [x[x.index < split].mean(), x[x.index >= split].mean()] if split is not None else []
            row |= {"mean": float(x.mean()), "median": float(x.median()),
                    "win_rate": float((x > 0).mean()), "worst_5pct": float(x.quantile(0.05)),
                    "mean_ci": list(ci), "ci_excludes_zero": bool(ci[0] > 0 or ci[1] < 0),
                    "early_mean": _f(halves[0]) if halves else None,
                    "late_mean": _f(halves[1]) if halves else None,
                    "stable": bool(np.sign(halves[0]) == np.sign(halves[1]))
                    if halves and all(np.isfinite(halves)) else None}
        rows.append(row)
    return {"label": label, "credible": bool(rows and rows[0]["eff_n"] >= config.RISK_LENS_MIN_EFF_N),
            "rows": rows}


def _f(x) -> float | None:
    return float(x) if np.isfinite(x) else None


def strategy_read(hist: pd.DataFrame, today: pd.Series, cell: str,
                  horizon: int | None = None, reps: int | None = None) -> dict:
    """Payoff tables for the unconditional sample and for `cell` (the base-rate primary),
    so every conditional figure sits next to its 'normal'."""
    hist = hist.dropna(subset=["fwd_rv"])
    masks = br.cell_masks(hist, today)
    keys = dict.fromkeys(["unconditional", cell if cell in masks else "unconditional"])
    return {"cell": cell, "cells": {k: strategy_stats(hist, masks[k][0], masks[k][1], masks[k][2],
                                                      horizon, reps) for k in keys}}
