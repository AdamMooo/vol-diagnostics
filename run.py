"""End-to-end POC orchestrator. Runs data → signals → backtest, prints
summaries to stdout, saves plots/tables to ./out/.

Usage:
    python run.py
    python run.py --start 2015-01-01
"""
from __future__ import annotations

import argparse
import pathlib
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import matplotlib.pyplot as plt
import pandas as pd

from data_layer import build_panels
from signals import build_signals
from backtest import run_backtest

OUT_DIR = pathlib.Path("out")
PLOT_DIR = OUT_DIR / "plots"


def _section(title: str) -> None:
    bar = "=" * len(title)
    print(f"\n{bar}\n{title}\n{bar}")


def _save(name: str, fig) -> pathlib.Path:
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    path = PLOT_DIR / f"{name}.png"
    fig.savefig(path, dpi=110, bbox_inches="tight")
    plt.close(fig)
    return path


def _save_table(name: str, df: pd.DataFrame) -> pathlib.Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{name}.csv"
    df.to_csv(path)
    return path


def main(start: str = "2010-01-01") -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    _section("Phase 1 — Data Layer")
    panels = build_panels(start=start)
    print(f"NYSE_INDEX: n={len(panels.nyse_index)}  span={panels.nyse_index.min().date()} → {panels.nyse_index.max().date()}")
    print(f"Truncated to: {panels.truncate_start.date()}  (shortest IV history)")
    print(f"Landed underlyings: {panels.landed}")
    print("\nPanel coverage (non-NaN obs):")
    print(panels.shape_summary().to_string())
    _save_table("01_panel_coverage", panels.shape_summary())

    fig, axes = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
    panels.prices_panel.plot(ax=axes[0], title="Price level (index)", lw=1)
    panels.iv_panel.plot(ax=axes[1], title="30D ATM IV", lw=1)
    panels.skew_panel.plot(ax=axes[2], title="30D skew (90mny − ATM)", lw=1)
    plt.tight_layout()
    print(f"  saved → {_save('01_panels', fig)}")

    _section("Phase 2 — Signal Engineering")
    sigs = build_signals(panels)
    latest = sigs.latest()
    print(f"\nLatest signal snapshot — {sigs.latest_date().date()} (causal 5y pct rank, 0=cool / 1=hot):")
    print(latest.round(2).to_string())
    _save_table("02_latest_signals", latest)

    sigs_to_plot = ["vrp", "skew", "term", "trend", "dd", "fragility"]
    fig, axes = plt.subplots(len(sigs_to_plot), 1, figsize=(12, 2 * len(sigs_to_plot)), sharex=True)
    for ax, sig in zip(axes, sigs_to_plot):
        sigs.pct[sig].plot(ax=ax, lw=0.9)
        ax.axhline(0.5, color="grey", ls="--", lw=0.5)
        ax.set_ylim(0, 1)
        ax.set_title(f"{sig} (causal 5y pct rank)", fontsize=10)
        ax.legend(loc="upper left", fontsize=8)
    plt.tight_layout()
    print(f"  saved → {_save('02_signals_timeseries', fig)}")

    _section("Phase 3 — Sleeve Backtest")
    bt = run_backtest(panels)
    for u in panels.iv_panel.columns:
        print(f"\n{u} ({len(bt.rolls[u])} rolls, {bt.rolls[u].index.min().date()} → {bt.rolls[u].index.max().date()}):")
        print(bt.stats[u].round(3).to_string())
        _save_table(f"03_stats_{u}", bt.stats[u])

    fig, axes = plt.subplots(len(panels.iv_panel.columns), 1, figsize=(12, 4 * len(panels.iv_panel.columns)), sharex=True)
    if len(panels.iv_panel.columns) == 1:
        axes = [axes]
    for ax, u in zip(axes, panels.iv_panel.columns):
        bt.equity[u].plot(ax=ax, lw=1.0)
        ax.set_title(f"{u} — sleeve equity curves (monthly roll)")
        ax.set_ylabel("Growth of $1")
        ax.axhline(1, color="grey", lw=0.5)
    plt.tight_layout()
    print(f"\n  saved → {_save('03_equity_curves', fig)}")

    _section("Done")
    print(f"Outputs in {OUT_DIR.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2010-01-01")
    args = parser.parse_args()
    sys.exit(main(start=args.start))
