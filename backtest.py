"""Phase 3 — sleeve backtest engine.

Black-Scholes monthly-roll P&L for four sleeves, per underlying:

    cc       long u/l + short ~0.25Δ call
    csp      cash + short ~0.25Δ put
    collar   long u/l + short 0.25Δ call - long 0.25Δ put
    strangle cash + short 0.20Δ call + short 0.20Δ put

Per-roll P&L in fraction-of-spot units → comparable across sleeves.
Strikes set at trade open via BS analytical delta-inversion. Held to
next roll, settled vs. realized spot. Cash legs earn rf_rate * T.

POC simplifications (refine in Phase 6):
- Flat ATM vol pricing (skew differential not priced in P&L)
- 0% dividend yield
- 0 transaction costs / bid-ask
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import norm

from data_layer import Panels

DELTA_TARGET   = 0.25
STRANGLE_DELTA = 0.20

SLEEVE_COLS = ["spot_ret", "cc", "csp", "collar", "strangle"]


def bs_price(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0, kind: str = "call") -> float:
    if T <= 0 or sigma <= 0:
        return max(0.0, S - K) if kind == "call" else max(0.0, K - S)
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    if kind == "call":
        return S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    return K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)


def bs_strike_from_delta(S: float, T: float, r: float, sigma: float, target_delta: float, q: float = 0.0, kind: str = "call") -> float:
    if kind == "call":
        d1 = norm.ppf(target_delta * np.exp(q * T))
    else:
        d1 = -norm.ppf(-target_delta * np.exp(q * T))
    return S * np.exp(-(d1 * sigma * np.sqrt(T)) + (r - q + 0.5 * sigma ** 2) * T)


def iv_at_strike(S: float, K: float, iv_atm_pts: float, iv_90mny_pts: float) -> float:
    """Linear-in-moneyness IV interpolation between ATM (m=1) and 90% mny (m=0.9).

    For m >= 1: flat at ATM (we lack upside skew data freely).
    For m in [0.9, 1.0]: linear interp.
    For m < 0.9: capped at iv_90mny.

    POC: the 90mny IV input itself is synthesized from VIX+SKEW; using
    it for pricing approximates the real put-skew premium. With actual
    Bloomberg 30D_IMPVOL_90mny this becomes properly calibrated.
    """
    if pd.isna(iv_90mny_pts):
        return iv_atm_pts / 100.0
    m = K / S
    if m >= 1.0:
        return iv_atm_pts / 100.0
    if m <= 0.9:
        return iv_90mny_pts / 100.0
    w = (1.0 - m) / 0.1
    return (iv_atm_pts + w * (iv_90mny_pts - iv_atm_pts)) / 100.0


def third_fridays(start: pd.Timestamp, end: pd.Timestamp) -> pd.DatetimeIndex:
    out = []
    cur = pd.Timestamp(start).to_period("M").to_timestamp()
    while cur <= pd.Timestamp(end):
        first = cur.replace(day=1)
        offset = (4 - first.weekday()) % 7  # Friday = 4
        third = first + pd.Timedelta(days=offset + 14)
        if pd.Timestamp(start) <= third <= pd.Timestamp(end):
            out.append(third.normalize())
        cur = cur + pd.offsets.MonthBegin(1)
    return pd.DatetimeIndex(out)


def snap_to_trading(dates: pd.DatetimeIndex, trading_idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    snapped = []
    for d in dates:
        if d in trading_idx:
            snapped.append(d)
        else:
            loc = trading_idx.searchsorted(d) - 1
            if loc >= 0:
                snapped.append(trading_idx[loc])
    return pd.DatetimeIndex(snapped).unique()


def backtest_sleeves(panels: Panels, underlying: str, roll_dates: pd.DatetimeIndex) -> pd.DataFrame:
    S = panels.prices_panel[underlying]
    iv = panels.iv_panel[underlying]
    iv90mny = panels.iv90mny[underlying] if underlying in panels.iv90mny.columns else None
    rf = panels.rf_rate

    rolls = []
    for i, t0 in enumerate(roll_dates[:-1]):
        t1 = roll_dates[i + 1]
        S0, S1 = S.loc[t0], S.loc[t1]
        iv_atm_pts = iv.loc[t0]
        iv_90mny_pts = iv90mny.loc[t0] if iv90mny is not None else np.nan
        sig = iv_atm_pts / 100.0
        rate_pct = rf.loc[t0]
        r = (rate_pct / 100.0) if not pd.isna(rate_pct) else 0.04

        if pd.isna(S0) or pd.isna(S1) or pd.isna(sig) or sig <= 0:
            continue
        T = max((t1 - t0).days / 365.0, 1 / 365)

        K_call_25 = bs_strike_from_delta(S0, T, r, sig, +DELTA_TARGET, kind="call")
        K_put_25  = bs_strike_from_delta(S0, T, r, sig, -DELTA_TARGET, kind="put")
        K_call_20 = bs_strike_from_delta(S0, T, r, sig, +STRANGLE_DELTA, kind="call")
        K_put_20  = bs_strike_from_delta(S0, T, r, sig, -STRANGLE_DELTA, kind="put")

        sig_put_25 = iv_at_strike(S0, K_put_25, iv_atm_pts, iv_90mny_pts)
        sig_put_20 = iv_at_strike(S0, K_put_20, iv_atm_pts, iv_90mny_pts)

        P_call_25 = bs_price(S0, K_call_25, T, r, sig,        kind="call")
        P_put_25  = bs_price(S0, K_put_25,  T, r, sig_put_25, kind="put")
        P_call_20 = bs_price(S0, K_call_20, T, r, sig,        kind="call")
        P_put_20  = bs_price(S0, K_put_20,  T, r, sig_put_20, kind="put")

        spot_ret = (S1 - S0) / S0
        rf_ret   = r * T

        cc_ret       = spot_ret + (P_call_25 - max(S1 - K_call_25, 0)) / S0
        csp_ret      = rf_ret   + (P_put_25  - max(K_put_25  - S1, 0)) / S0
        collar_ret   = (
            spot_ret
            + (P_call_25 - max(S1 - K_call_25, 0)) / S0
            + (-P_put_25 + max(K_put_25  - S1, 0)) / S0
        )
        strangle_ret = (
            rf_ret
            + (P_call_20 - max(S1 - K_call_20, 0)) / S0
            + (P_put_20  - max(K_put_20  - S1, 0)) / S0
        )

        rolls.append({
            "open": t0, "close": t1, "S0": S0, "S1": S1,
            "sigma": sig, "rate": r, "T_days": (t1 - t0).days,
            "spot_ret": spot_ret,
            "cc": cc_ret, "csp": csp_ret, "collar": collar_ret, "strangle": strangle_ret,
        })

    return pd.DataFrame(rolls).set_index("close")


@dataclass
class BacktestResults:
    rolls: dict[str, pd.DataFrame]
    equity: dict[str, pd.DataFrame]
    stats: dict[str, pd.DataFrame]


def equity_and_stats(rolls: pd.DataFrame, n_per_year: int = 12) -> tuple[pd.DataFrame, pd.DataFrame]:
    rets = rolls[SLEEVE_COLS]
    eq = (1 + rets).cumprod()
    stats = pd.DataFrame({
        "cagr":   (eq.iloc[-1] ** (n_per_year / len(rets)) - 1),
        "vol":    rets.std() * np.sqrt(n_per_year),
        "sharpe": rets.mean() / rets.std() * np.sqrt(n_per_year),
        "max_dd": (eq / eq.cummax() - 1).min(),
        "hit":    (rets > 0).mean(),
    })
    return eq, stats


def run_backtest(panels: Panels) -> BacktestResults:
    raw_rolls = third_fridays(panels.prices_panel.index.min(), panels.prices_panel.index.max())
    roll_dates = snap_to_trading(raw_rolls, panels.prices_panel.index)

    rolls = {}
    equity = {}
    stats = {}
    for u in panels.iv_panel.columns:
        rolls[u] = backtest_sleeves(panels, u, roll_dates)
        eq, st = equity_and_stats(rolls[u])
        equity[u] = eq
        stats[u] = st

    return BacktestResults(rolls=rolls, equity=equity, stats=stats)
