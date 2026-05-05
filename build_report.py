"""HTML report generator for the Options Quant market intelligence POC.

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
from dashboard import (
    section_environment_context,
    section_short_vol_environment,
    section_analog_periods,
    section_signal_dynamics,
)

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
    "figsize_multi_height": 2.5,
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
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=CHART_STYLE["dpi"], bbox_inches="tight")
    buf.seek(0)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    plt.close(fig)
    return b64


def _add_regime_shading(ax, sigs, fragility_threshold=0.67):
    fragility_ts = sigs.pct.get("fragility")
    if fragility_ts is None:
        return
    if isinstance(fragility_ts, pd.DataFrame):
        fragility_ts = fragility_ts.mean(axis=1)

    high_frag = fragility_ts >= fragility_threshold
    transitions = high_frag != high_frag.shift()
    frag_periods = high_frag[transitions].index

    for i in range(0, len(frag_periods), 2):
        if i + 1 < len(frag_periods):
            start = frag_periods[i]
            end = frag_periods[i + 1]
            ax.axvspan(start, end, alpha=0.1, color="red", label="High fragility" if i == 0 else "")
        elif i == len(frag_periods) - 1 and high_frag.iloc[-1]:
            start = frag_periods[i]
            ax.axvspan(start, fragility_ts.index[-1], alpha=0.1, color="red")


def _signal_chart(sigs) -> str:
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
    axes[-1].xaxis.set_major_locator(mdates.YearLocator())
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    plt.setp(axes[-1].xaxis.get_majorticklabels(), rotation=45, ha="right")
    plt.tight_layout()
    return _fig_to_b64(fig)


def build_html(panels, sigs) -> str:
    parts = []
    parts.append(
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<title>Options Quant — Market Intelligence</title>"
        f"<style>{CSS}</style></head><body>"
    )
    parts.append("<h1>Options Quant — Market Intelligence Dashboard</h1>")
    parts.append(
        f"<p class='meta'>Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC &middot; "
        "Data: CBOE + FRED (free sources) &middot; "
        "90mny IV: synthesized (slope=0.2 approximation &mdash; see WALKTHROUGH.md)</p>"
    )

    # Section 1 — current environment
    parts.append(f"<pre>{section_environment_context(sigs)}</pre>")

    # Signal percentile-rank time-series chart
    sig_b64 = _signal_chart(sigs)
    parts.append(f"<img src='data:image/png;base64,{sig_b64}' alt='Signal percentile ranks'>")

    # Section 2 — short-vol environment historical distributions
    parts.append("<h2>Short-Vol Environment Historical Distributions</h2>")
    parts.append(f"<pre>{section_short_vol_environment(sigs, panels)}</pre>")

    # Section 3 — analog periods
    parts.append("<h2>Past Periods That Looked Like Now</h2>")
    parts.append(f"<pre>{section_analog_periods(sigs, panels)}</pre>")

    # Section 4 — signal dynamics
    parts.append("<h2>Signal Dynamics</h2>")
    parts.append(f"<pre>{section_signal_dynamics(sigs)}</pre>")

    parts.append(
        "<p class='meta'>No score. No recommendation. Market intelligence, not a signal. "
        "Caveats: synthetic 90mny IV (POC; calibrated, not Bloomberg-observed), "
        "0% dividend yield. Historical base rates only; no predictive warrant.</p>"
    )
    parts.append("</body></html>")
    return "\n".join(parts)


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    fname = OUT_DIR / f"sleeve_report_{datetime.utcnow().strftime('%Y%m%d')}.html"

    print("Loading data...")
    panels = build_panels(start="2010-01-01")
    print("Building signals...")
    sigs = build_signals(panels)
    print("Generating HTML report...")
    html = build_html(panels, sigs)

    fname.write_text(html, encoding="utf-8")
    print(f"Report saved: {fname.resolve()}")


if __name__ == "__main__":
    main()
