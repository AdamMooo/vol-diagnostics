"""HTML report generator for the Options Quant sleeve allocation POC.

Produces a single self-contained HTML file with all sections and charts
embedded as base64 PNG data URIs. No external template engines required.

Usage:
    python build_report.py
Output:
    out/sleeve_report_YYYYMMDD.html
"""
from __future__ import annotations

import io
import base64
import pathlib
import sys
from datetime import datetime

import matplotlib
matplotlib.use("Agg")  # non-interactive backend — must come before pyplot import
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

from data_layer import build_panels
from signals import build_signals
from backtest import run_backtest
from dashboard import (
    section_a_state,
    section_b_mechanics,
    section_c_buckets,
    section_d_analog,
    section_e_subperiod,
)
from sensitivity import format_tc_grid, format_tail_metrics, tc_sensitivity_table, tail_metrics_table

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

OUT_DIR = pathlib.Path("out")

_SIGS_TO_PLOT = ["vrp", "skew", "term", "trend", "dd", "fragility"]

CHART_STYLE = {
    "figsize": (12, 3),
    "dpi": 110,
    "linewidth": 0.9,
    "fontsize_title": 10,
    "fontsize_legend": 8,
    "color_grid": "grey",
    "color_signal": "steelblue",
    "figsize_multi_height": 2.5,  # per-subplot height for stacked charts
}

CSS = """
body { font-family: Georgia, serif; max-width: 1100px; margin: 40px auto; padding: 0 20px; color: #222; }
h1 { border-bottom: 2px solid #333; padding-bottom: 8px; }
h2 { margin-top: 40px; border-bottom: 1px solid #ccc; padding-bottom: 4px; }
pre { background: #f8f8f8; padding: 14px; overflow-x: auto; font-size: 12px; line-height: 1.5; }
img { max-width: 100%; margin: 16px 0; display: block; }
.meta { color: #666; font-size: 13px; margin-bottom: 32px; }
"""


def _fig_to_b64(fig) -> str:
    """Save a matplotlib figure to a base64-encoded PNG string and close it."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=CHART_STYLE["dpi"], bbox_inches="tight")
    buf.seek(0)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    plt.close(fig)
    return b64


def _add_regime_shading(ax, sigs, fragility_threshold=0.67):
    """Add vertical bands to indicate high-fragility periods (background shading).

    Args:
        ax: matplotlib axis to shade
        sigs: Signals object with fragility pct-rank time-series
        fragility_threshold: pct-rank threshold for "high fragility" (default 0.67 = top third)
    """
    fragility_ts = sigs.pct.get("fragility")
    if fragility_ts is None:
        return  # No fragility data; skip shading
    # Collapse DataFrame (one column per underlying) → single Series
    if isinstance(fragility_ts, pd.DataFrame):
        fragility_ts = fragility_ts.mean(axis=1)

    high_frag = fragility_ts >= fragility_threshold
    # Find periods where high_frag changes from False to True (start) and True to False (end)
    transitions = high_frag != high_frag.shift()
    frag_periods = high_frag[transitions].index

    # Shade each high-fragility period
    for i in range(0, len(frag_periods), 2):
        if i + 1 < len(frag_periods):
            start = frag_periods[i]
            end = frag_periods[i + 1]
            ax.axvspan(start, end, alpha=0.1, color="red", label="High fragility" if i == 0 else "")
        elif i == len(frag_periods) - 1 and high_frag.iloc[-1]:
            # Last period is still in high-fragility
            start = frag_periods[i]
            ax.axvspan(start, fragility_ts.index[-1], alpha=0.1, color="red")


def _signal_chart(sigs) -> str:
    """Time-series chart of all signal pct ranks. Returns base64 PNG."""
    n = len(_SIGS_TO_PLOT)
    fig, axes = plt.subplots(n, 1, figsize=(12, CHART_STYLE["figsize_multi_height"] * n), sharex=True)
    for ax, sig in zip(axes, _SIGS_TO_PLOT):
        if sig not in sigs.pct:
            continue
        sigs.pct[sig].plot(ax=ax, lw=CHART_STYLE["linewidth"], color=CHART_STYLE["color_signal"])
        ax.axhline(0.5, color=CHART_STYLE["color_grid"], ls="--", lw=0.5, alpha=0.5)
        _add_regime_shading(ax, sigs, fragility_threshold=0.67)
        ax.set_ylim(0, 1)
        ax.set_ylabel("Pct Rank", fontsize=CHART_STYLE["fontsize_legend"])
        ax.set_title(f"{sig} (causal 5y pct rank)", fontsize=CHART_STYLE["fontsize_title"])
        ax.legend(loc="upper left", fontsize=CHART_STYLE["fontsize_legend"], framealpha=0.9)
        ax.grid(True, alpha=0.3)
    # X-axis formatting on the bottom subplot only
    axes[-1].xaxis.set_major_locator(mdates.YearLocator())
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    plt.setp(axes[-1].xaxis.get_majorticklabels(), rotation=45, ha="right")
    plt.tight_layout()
    return _fig_to_b64(fig)


def _equity_chart(bt, panels) -> str:
    """Sleeve equity curves for all underlyings. Returns base64 PNG."""
    underlyings = list(bt.equity.keys())
    n = len(underlyings)
    fig, axes = plt.subplots(n, 1, figsize=(12, 4 * n), sharex=True)
    if n == 1:
        axes = [axes]
    for ax, u in zip(axes, underlyings):
        bt.equity[u].plot(ax=ax, lw=1.0)
        ax.set_title(f"{u} — sleeve equity curves (monthly roll)")
        ax.set_ylabel("Growth of $1")
        ax.axhline(1, color="grey", lw=0.5)
    plt.tight_layout()
    return _fig_to_b64(fig)


def build_html(panels, sigs, bt) -> str:
    parts = []
    parts.append(
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<title>Options Quant POC</title>"
        f"<style>{CSS}</style></head><body>"
    )
    parts.append("<h1>Options Quant — Sleeve Allocation Framework (α Engine)</h1>")
    parts.append(
        f"<p class='meta'>Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC &middot; "
        "Data: CBOE + FRED (free sources) &middot; "
        "90mny IV: synthesized (slope=0.2 approximation &mdash; see WALKTHROUGH.md)</p>"
    )

    # Section A — leads the report
    parts.append("<h2>Section A &mdash; Current State</h2>")
    parts.append(f"<pre>{section_a_state(sigs)}</pre>")

    # Signal percentile-rank time-series chart
    sig_b64 = _signal_chart(sigs)
    parts.append(f"<img src='data:image/png;base64,{sig_b64}' alt='Signal percentile ranks'>")

    # Section B
    parts.append("<h2>Section B &mdash; Sleeve Mechanics</h2>")
    parts.append(f"<pre>{section_b_mechanics()}</pre>")

    # Section C
    parts.append("<h2>Section C &mdash; Bucket Returns &amp; Holm Correction</h2>")
    parts.append(f"<pre>{section_c_buckets(sigs, bt)}</pre>")

    # Section D
    parts.append("<h2>Section D &mdash; Past Periods That Looked Like Now</h2>")
    parts.append(f"<pre>{section_d_analog(sigs, bt)}</pre>")

    # Section E
    parts.append("<h2>Section E &mdash; Subperiod Stability</h2>")
    parts.append(f"<pre>{section_e_subperiod(bt)}</pre>")

    # Equity curves chart (after Section E, before G)
    eq_b64 = _equity_chart(bt, panels)
    parts.append(f"<img src='data:image/png;base64,{eq_b64}' alt='Sleeve equity curves'>")

    # Section G — TC Sensitivity
    parts.append("<h2>Section G &mdash; Transaction Cost Sensitivity</h2>")
    parts.append(f"<pre>{format_tc_grid(tc_sensitivity_table(bt))}</pre>")

    # Section H — Tail Risk
    parts.append("<h2>Section H &mdash; Tail-Risk Metrics</h2>")
    parts.append(f"<pre>{format_tail_metrics(tail_metrics_table(bt))}</pre>")

    parts.append("</body></html>")
    return "\n".join(parts)


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    fname = OUT_DIR / f"sleeve_report_{datetime.utcnow().strftime('%Y%m%d')}.html"

    print("Loading data...")
    panels = build_panels(start="2010-01-01")
    print("Building signals...")
    sigs = build_signals(panels)
    print("Running backtest...")
    bt = run_backtest(panels)
    print("Generating HTML report...")
    html = build_html(panels, sigs, bt)

    fname.write_text(html, encoding="utf-8")
    print(f"Report saved: {fname.resolve()}")


if __name__ == "__main__":
    main()
