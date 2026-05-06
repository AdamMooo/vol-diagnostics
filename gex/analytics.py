"""
Derive analytics from GEX and produce matplotlib charts.

Key outputs:
    - net_gex: scalar total GEX at current spot
    - zero_gamma_level: spot where cumulative GEX changes sign
    - call_wall: strike with largest positive GEX (dominant call cluster)
    - put_wall: strike with largest negative GEX (dominant put cluster)
    - gamma_regime: "positive" | "negative" | "neutral"
"""
from __future__ import annotations

import base64
import io

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker


NEUTRAL_BAND_PCT = 0.005  # net GEX within ±0.5% of |max| treated as neutral
# Absolute floor: |net GEX| below this → NEUTRAL regardless of relative magnitude.
# Calibrated 2026-05-05 against post-filter noise tickers (EWJ/EFA/TLT/XLF);
# 75th percentile of that distribution ≈ $94M, rounded to $100M.
NEUTRAL_ABS_FLOOR = 0.2e9  # $200M — calibrated to suppress XLF/EFA/EWJ/TLT noise tier


def summarise(gex_df: pd.DataFrame, profile_df: pd.DataFrame,
              spot: float,
              net_vex: float | None = None,
              net_chex: float | None = None,
              delta_hedge_flow: float | None = None) -> dict:
    """
    gex_df: strike-level GEX DataFrame (columns: strike, gex)
    profile_df: gamma profile DataFrame (columns: spot_level, net_gex)
    spot: current underlying price

    Returns a dict of key analytics.
    """
    net_gex = float(gex_df["gex"].sum())

    # zero-gamma level: first sign change in profile
    zero_gamma = _find_zero_crossing(profile_df)

    calls = gex_df[gex_df["gex"] > 0]
    puts = gex_df[gex_df["gex"] < 0]
    call_wall = float(calls.loc[calls["gex"].idxmax(), "strike"]) if not calls.empty else None
    put_wall = float(puts.loc[puts["gex"].idxmin(), "strike"]) if not puts.empty else None

    abs_max = gex_df["gex"].abs().max()
    if abs_max == 0 or abs(net_gex) < NEUTRAL_ABS_FLOOR:
        regime = "neutral"
    elif abs(net_gex) / abs_max < NEUTRAL_BAND_PCT:
        regime = "neutral"
    elif net_gex > 0:
        regime = "positive"
    else:
        regime = "negative"

    return {
        "net_gex": net_gex,
        "zero_gamma_level": zero_gamma,
        "call_wall": call_wall,
        "put_wall": put_wall,
        "gamma_regime": regime,
        "spot": spot,
        "net_vex": net_vex,
        "net_chex": net_chex,
        "delta_hedge_flow": delta_hedge_flow,
    }


def _find_zero_crossing(profile_df: pd.DataFrame) -> float | None:
    signs = np.sign(profile_df["net_gex"].to_numpy())
    for i in range(len(signs) - 1):
        if signs[i] != signs[i + 1]:
            # linear interpolation between the two points
            x0, y0 = profile_df["spot_level"].iloc[i], profile_df["net_gex"].iloc[i]
            x1, y1 = profile_df["spot_level"].iloc[i + 1], profile_df["net_gex"].iloc[i + 1]
            return float(x0 - y0 * (x1 - x0) / (y1 - y0))
    return None


def plot_strike_gex(gex_df: pd.DataFrame, spot: float, ticker: str,
                    summary: dict, ax: plt.Axes | None = None) -> plt.Figure:
    """Bar chart of GEX by strike."""
    fig, ax = (plt.subplots(figsize=(12, 5)) if ax is None else (ax.figure, ax))

    colors = ["steelblue" if v >= 0 else "firebrick" for v in gex_df["gex"]]
    ax.bar(gex_df["strike"], gex_df["gex"] / 1e9, color=colors, width=_bar_width(gex_df))
    ax.axvline(spot, color="black", lw=1.5, linestyle="--", label=f"Spot {spot:.2f}")
    if summary.get("call_wall"):
        ax.axvline(summary["call_wall"], color="steelblue", lw=1, linestyle=":",
                   label=f"Call wall {summary['call_wall']:.0f}")
    if summary.get("put_wall"):
        ax.axvline(summary["put_wall"], color="firebrick", lw=1, linestyle=":",
                   label=f"Put wall {summary['put_wall']:.0f}")
    if summary.get("zero_gamma_level"):
        ax.axvline(summary["zero_gamma_level"], color="goldenrod", lw=1.5,
                   label=f"Zero-gamma {summary['zero_gamma_level']:.2f}")

    ax.set_xlabel("Strike")
    ax.set_ylabel("GEX ($B)")
    ax.set_title(f"{ticker} — GEX by Strike  |  Net GEX: ${summary['net_gex']/1e9:.2f}B  "
                 f"[{summary['gamma_regime'].upper()} GAMMA]")
    ax.legend(fontsize=8)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1f}B"))
    fig.tight_layout()
    return fig


def plot_gamma_profile(profile_df: pd.DataFrame, spot: float, ticker: str,
                       summary: dict, ax: plt.Axes | None = None) -> plt.Figure:
    """Line chart of net GEX across spot levels."""
    fig, ax = (plt.subplots(figsize=(10, 4)) if ax is None else (ax.figure, ax))

    ax.plot(profile_df["spot_level"], profile_df["net_gex"] / 1e9,
            color="navy", lw=2)
    ax.axhline(0, color="black", lw=0.8, linestyle="-")
    ax.fill_between(profile_df["spot_level"], profile_df["net_gex"] / 1e9, 0,
                    where=(profile_df["net_gex"] >= 0), alpha=0.15, color="steelblue")
    ax.fill_between(profile_df["spot_level"], profile_df["net_gex"] / 1e9, 0,
                    where=(profile_df["net_gex"] < 0), alpha=0.15, color="firebrick")

    ax.axvline(spot, color="black", lw=1.5, linestyle="--", label=f"Spot {spot:.2f}")
    if summary.get("zero_gamma_level"):
        ax.axvline(summary["zero_gamma_level"], color="goldenrod", lw=1.5,
                   label=f"Zero-gamma {summary['zero_gamma_level']:.2f}")

    ax.set_xlabel("Underlying Price")
    ax.set_ylabel("Net GEX ($B)")
    ax.set_title(f"{ticker} — Gamma Profile")
    ax.legend(fontsize=8)
    fig.tight_layout()
    return fig


def fig_to_b64(fig: plt.Figure) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def plot_overview(results: list[dict]) -> plt.Figure:
    """Horizontal bar chart — net GEX for all tickers. For email header."""
    from gex.report import TICKER_LABEL, REGIME_COLOR

    valid = [r for r in results if not r.get("error")]
    labels = [TICKER_LABEL.get(r["ticker"], r["ticker"]) for r in valid]
    values = [r["net_gex"] / 1e9 for r in valid]
    colors = [REGIME_COLOR.get(r["gamma_regime"], "#7f8c8d") for r in valid]

    fig, ax = plt.subplots(figsize=(9, max(2.5, len(valid) * 0.45)))
    bars = ax.barh(labels, values, color=colors, height=0.55)
    ax.axvline(0, color="#2c3e50", lw=1)
    ax.set_xlabel("Net GEX ($B)")
    ax.set_title("Cross-Asset Gamma Exposure", fontsize=13, fontweight="bold", pad=10)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:+.1f}B"))
    ax.invert_yaxis()

    for bar, val in zip(bars, values):
        ax.text(
            val + (0.04 if val >= 0 else -0.04),
            bar.get_y() + bar.get_height() / 2,
            f"{val:+.2f}B",
            va="center", ha="left" if val >= 0 else "right",
            fontsize=9, color="#2c3e50",
        )

    fig.patch.set_facecolor("#f8f9fa")
    ax.set_facecolor("#f8f9fa")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


def _bar_width(gex_df: pd.DataFrame) -> float:
    strikes = sorted(gex_df["strike"].unique())
    if len(strikes) < 2:
        return 1.0
    gaps = [strikes[i + 1] - strikes[i] for i in range(min(10, len(strikes) - 1))]
    return float(np.median(gaps)) * 0.8
