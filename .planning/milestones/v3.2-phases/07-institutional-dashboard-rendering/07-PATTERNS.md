# Phase 7: Institutional Dashboard Rendering — Pattern Map

**Mapped:** 2026-05-26
**Files analyzed:** 3 (streamlit_app.py, gex/analytics.py, gex/tests/test_analytics_charts_p7.py)
**Analogs found:** 3 / 3

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `streamlit_app.py` | component (dashboard) | request-response | `streamlit_app.py` (current) | self — restructure |
| `gex/analytics.py` | utility (chart functions) | transform | `gex/analytics.py` (current) | self — additive |
| `gex/tests/test_analytics_charts_p7.py` | test | transform | `gex/tests/test_analytics_summarise.py` | role-match |

---

## Pattern Assignments

### `streamlit_app.py` (restructure — tab layout)

**Analog:** `streamlit_app.py` lines 154–307 (current `render_section()` + boot block)

**Imports pattern** (lines 1–16 — keep as-is, add new chart functions):
```python
from gex.analytics import (
    plot_strike_gex, plot_gamma_profile,
    plot_vol_surface, plot_skew_term_structure,
    # ADD:
    plot_skew_25d_current, plot_term_structure, plot_carry_vrp,
)
```

**Auth/password check** (lines 30–47 — unchanged):
```python
def _check_password() -> bool:
    if st.session_state.get("authenticated"):
        return True
    ...
    if expected and pwd == expected:
        st.session_state.authenticated = True
        st.rerun()
    elif pwd:
        st.error("Incorrect password")
    return False

if not _check_password():
    st.stop()
```

**Regime cards loop pattern** (lines 154–166 — keep, rename `render_section` regime card portion to `render_regime_cards`):
```python
def render_regime_cards(tickers: list[str], all_data: dict[str, dict],
                        n_cols: int = 3) -> None:
    data_list = [all_data[t] for t in tickers if t in all_data
                 and not all_data[t]["summary"].get("error")]
    if not data_list:
        st.info("No data loaded.")
        return
    rows = [data_list[i:i + n_cols] for i in range(0, len(data_list), n_cols)]
    for row in rows:
        cols = st.columns(n_cols)
        for col, data in zip(cols, row):
            render_regime_card(col, data["summary"], spot=data.get("spot"))
```

**Top-level tab structure** (replaces per-ticker expander loop at lines 168–254):
```python
tab_surface, tab_skew, tab_term, tab_carry, tab_flow = st.tabs([
    "Surface", "Skew", "Term Structure", "Carry", "Flow Context"
])

with tab_surface:
    for ticker in selected_all:
        if ticker not in all_data:
            continue
        data = all_data[ticker]
        surface_df = data.get("surface_df")
        spot = data.get("spot")
        if surface_df is not None and not surface_df.empty:
            st.plotly_chart(
                plot_vol_surface(surface_df, ticker, spot=spot),
                use_container_width=True,
            )
        else:
            st.caption(f"{ticker}: insufficient data for surface.")
```
Layout note: Surface tab uses stacked vertical (full width needed for 3D). Skew and Carry use `st.columns(len(selected_all))` for side-by-side 2D charts.

**Per-tab cold-start None guard** (pattern from line 207 and 251):
```python
# Guard before any computation or chart call:
if value is None:
    st.caption("Not yet available — accumulates after 20 daily runs.")
```

**History chart pattern** (ZGL rolling history — lines 210–226 — canonical reference for all rolling charts):
```python
hist30 = _load_history_cached(ticker, days=config.HISTORY_DAYS)
if hist30.empty:
    st.caption("No history yet — daily snapshots accumulate from `gex.run_daily`.")
else:
    chart_df = hist30.sort_values("date")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=chart_df["date"], y=chart_df["zero_gamma_level"],
        name="γ-flip", line=dict(color="#f59e0b", width=1.5),
    ))
    fig.update_layout(
        template="plotly_dark",
        title=f"γ-flip vs Spot — {config.HISTORY_DAYS} sessions",
        height=260,
        margin=dict(t=40, b=30, l=60, r=20),
        legend=dict(orientation="h", y=1.15),
    )
    st.plotly_chart(fig, use_container_width=True)
```

**Skew rolling history pattern** (lines 228–254 — move into Skew tab, keep inline):
```python
if "front_skew" in chart_df.columns and chart_df["front_skew"].notna().any():
    skew_hist = chart_df.dropna(subset=["front_skew"])
    skew_fig = go.Figure()
    skew_fig.add_trace(go.Scatter(
        x=skew_hist["date"], y=skew_hist["front_skew"],
        name="Skew (25Δ)",
        mode="lines+markers",
        line=dict(color="#f59e0b", width=1.5),
        marker=dict(size=5),
        hovertemplate="%{x|%b %d}<br>Skew: %{y:+.2f}pp<extra></extra>",
    ))
    skew_fig.add_hline(y=0, line_color="rgba(255,255,255,0.15)", line_width=0.8)
    skew_fig.update_layout(
        template="plotly_dark",
        title=f"Skew (25Δ put − 50Δ call) — {config.HISTORY_DAYS} sessions",
        height=240,
        yaxis_title="Skew (pp)",
        yaxis_ticksuffix="pp",
        margin=dict(t=40, b=30, l=60, r=20),
        showlegend=False,
    )
    st.plotly_chart(skew_fig, use_container_width=True)
else:
    st.caption(
        "Skew history empty — accumulates from today's `gex.run_daily` run forward."
    )
```

**Carry unit extraction** (new helper, inline in Carry tab or extracted as `_carry_values()`):
```python
def _carry_values(data: dict) -> tuple[float | None, float | None, float | None]:
    summary = data.get("summary", {})
    iv30_pct = summary.get("iv30")            # already percent (e.g. 18.0)
    rv20 = data.get("rv20")                   # decimal fraction (e.g. 0.158)
    vrp = data.get("vrp")                     # decimal fraction (e.g. 0.022)
    rv20_pct = float(rv20 * 100) if rv20 is not None else None
    vrp_pp = float(vrp * 100) if vrp is not None else None
    return iv30_pct, rv20_pct, vrp_pp
```

**Carry rolling VRP history** (new — follows ZGL history pattern, uses parquet `vrp` column):
```python
if "vrp" in chart_df.columns and chart_df["vrp"].notna().any():
    vrp_hist = chart_df.dropna(subset=["vrp"]).copy()
    vrp_hist["vrp_pp"] = vrp_hist["vrp"] * 100   # decimal → vol points
    vrp_fig = go.Figure()
    vrp_fig.add_trace(go.Scatter(
        x=vrp_hist["date"], y=vrp_hist["vrp_pp"],
        mode="lines+markers",
        line=dict(color="#a78bfa", width=1.5),
        marker=dict(size=5),
        hovertemplate="%{x|%b %d}<br>VRP: %{y:+.2f}pp<extra></extra>",
    ))
    vrp_fig.add_hline(y=0, line_color="rgba(255,255,255,0.15)", line_width=0.8)
    vrp_fig.update_layout(
        template="plotly_dark",
        title=f"Vol Carry / VRP — {config.HISTORY_DAYS} sessions",
        height=240,
        yaxis_title="VRP (vol pts)",
        yaxis_ticksuffix="pp",
        margin=dict(t=40, b=30, l=60, r=20),
        showlegend=False,
    )
    st.plotly_chart(vrp_fig, use_container_width=True)
else:
    st.caption("VRP history empty — accumulates from today's `gex.run_daily` run forward.")
```

**Flow Context tab header** (locked text from ROADMAP):
```python
with tab_flow:
    st.markdown(
        "### Microstructure / Execution Context — model-based, not market prices",
        unsafe_allow_html=False,
    )
    st.caption(
        "GEX assumes dealers are net short all options (Garleanu, Pedersen & Poteshman 2009). "
        "Sign and order of magnitude are informative; absolute levels are vendor-dependent."
    )
    for ticker in selected_all:
        if ticker not in all_data:
            continue
        data = all_data[ticker]
        s = data["summary"]
        spot = data.get("spot")
        c1, c2 = st.columns([3, 2])
        with c1:
            st.plotly_chart(plot_strike_gex(data["s_df"], spot, ticker, s),
                            use_container_width=True)
        with c2:
            st.plotly_chart(plot_gamma_profile(data["p_df"], spot, ticker, s),
                            use_container_width=True)
```

**Lines that stay unchanged (do not touch):**
- Lines 30–47: password check
- Lines 49–83: CSS block (`_SIGN_RGBA`, `_CSS`)
- Lines 87–101: `_derive_observations()`
- Lines 104–113: `fetch_ticker()`, `_load_history_cached()` cache functions
- Lines 115–151: `render_regime_card()`
- Lines 259–307: boot, sidebar, ticker fetch, spinner, error display
- Lines 309–373: methodology expander

**Lines to delete:**
- Lines 168–254: entire per-ticker `with st.expander(...)` loop inside `render_section()` (replaces with 5-tab structure)
- Line 306: `render_section(sel_index, all_data, ...)` call (replaces with `render_regime_cards()` + `st.tabs()` block)

---

### `gex/analytics.py` — new function: `plot_skew_25d_current()`

**Analog:** `plot_skew_term_structure()` — lines 278–300 (same file, same role: scatter chart over option metrics)

**Imports** (lines 15–21 — unchanged, already has `go`, `np`, `pd`, `config`):
```python
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from gex import config
```

**Core pattern** (copy structure from `plot_skew_term_structure` lines 278–300):
```python
def plot_skew_25d_current(skew: dict, ticker: str) -> go.Figure:
    """Bar chart of 25Δ put-call skew for front and second month."""
    fig = go.Figure()
    # build from skew["front_month"] and skew["second_month"] dicts
    # each bucket: {"put_iv": float, "call_iv": float, "skew": float, "dte": float} | None
    fig.add_trace(go.Bar(
        x=[...], y=[...],
        ...
        hovertemplate="...<extra></extra>",
    ))
    fig.add_hline(y=0, line_color="rgba(255,255,255,0.2)", line_width=0.8)
    fig.update_layout(
        template="plotly_dark",
        title=dict(text=f"25Δ Put-Call Skew — {ticker}", font_size=13),
        yaxis_title="Skew (pp)",
        yaxis_ticksuffix="pp",
        showlegend=False,
        height=240,
        margin=dict(t=50, b=40, l=65, r=20),
    )
    return fig
```
Empty-data guard: check if both buckets are `None`; return titled empty figure (follow `plot_vol_surface` empty guard at lines 169–177).

---

### `gex/analytics.py` — new function: `plot_term_structure()`

**Analog:** `plot_skew_term_structure()` — lines 278–300 (scatter with lines+markers, same layout conventions)

**Core pattern** (directly follows `plot_skew_term_structure` structure):
```python
def plot_term_structure(ts: dict, ticker: str) -> go.Figure:
    points = ts.get("points", [])
    classification = ts.get("classification", "normal")
    if not points:
        fig = go.Figure()
        fig.update_layout(
            template="plotly_dark",
            title=f"ATM IV Term Structure — {ticker}: no data",
            height=300,
            margin=dict(t=50, b=40, l=65, r=20),
        )
        return fig
    x = [p["dte"] for p in points]
    y = [p["atm_iv"] for p in points]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=y,
        mode="lines+markers",
        line=dict(color="#60a5fa", width=2),
        marker=dict(size=6),
        hovertemplate="DTE: %{x:.0f}<br>ATM IV: %{y:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        template="plotly_dark",
        title=dict(
            text=f"ATM IV Term Structure — {ticker}  ·  {classification}",
            font_size=13,
        ),
        xaxis_title="DTE",
        yaxis_title="ATM IV (%)",
        yaxis_ticksuffix="%",
        height=300,
        margin=dict(t=50, b=40, l=65, r=20),
    )
    return fig
```
Label constraint: `classification` is a descriptor only ("normal", "flat", "inverted", "humped"). No interpretive text.

---

### `gex/analytics.py` — new function: `plot_carry_vrp()`

**Analog:** `plot_strike_gex()` — lines 66–111 (grouped bar with `go.Bar`, same `update_layout` template)

**Core pattern** (follows `plot_strike_gex` bar chart structure, two-trace grouped bar):
```python
def plot_carry_vrp(iv30_pct: float | None, rv20_pct: float | None,
                   vrp_pp: float | None, ticker: str) -> go.Figure:
    fig = go.Figure()
    labels = ["IV30", "RV20"]
    values = [iv30_pct or 0, rv20_pct or 0]
    colors = ["#f59e0b", "#60a5fa"]
    fig.add_trace(go.Bar(
        x=labels, y=values,
        marker_color=colors,
        width=0.5,
        hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
    ))
    vrp_label = f"VRP: {vrp_pp:+.1f}pp" if vrp_pp is not None else "VRP: n/a (cold start)"
    fig.update_layout(
        template="plotly_dark",
        title=dict(
            text=f"Vol Carry / VRP — {ticker}  ·  {vrp_label}",
            font_size=13,
        ),
        yaxis_title="Vol (%)",
        yaxis_ticksuffix="%",
        height=280,
        margin=dict(t=50, b=40, l=65, r=20),
        showlegend=False,
    )
    return fig
```
Unit constraint: `iv30_pct` is percent (18.0), `rv20_pct` is decimal×100 (15.8), `vrp_pp` is decimal×100 (2.2). Caller must convert before passing.

---

### `gex/tests/test_analytics_charts_p7.py` (new smoke test file)

**Analog:** `gex/tests/test_analytics_summarise.py` (same pytest structure: fixtures, class or flat test functions, import from `gex.analytics`)

**Imports pattern** (lines 1–5 of test_analytics_summarise.py):
```python
"""Smoke tests for Phase 7 chart functions — returns go.Figure without error."""
import pandas as pd
import plotly.graph_objects as go
import pytest

from gex.analytics import plot_skew_25d_current, plot_term_structure, plot_carry_vrp
```

**Fixture pattern** (lines 8–18 of test_analytics_summarise.py — minimal synthetic data):
```python
@pytest.fixture
def skew_dict():
    return {
        "front_month": {"put_iv": 22.0, "call_iv": 18.0, "skew": 4.0, "dte": 32.0},
        "second_month": {"put_iv": 21.0, "call_iv": 17.0, "skew": 4.0, "dte": 62.0},
    }

@pytest.fixture
def term_structure_dict():
    return {
        "points": [{"dte": 30.0, "atm_iv": 18.0}, {"dte": 60.0, "atm_iv": 20.0}],
        "classification": "normal",
        "front_atm_iv": 18.0,
        "back_atm_iv": 20.0,
    }
```

**Test structure** (pattern from test_analytics_summarise.py — flat assertions, no mocking):
```python
def test_plot_term_structure_returns_figure(term_structure_dict):
    fig = plot_term_structure(term_structure_dict, "SPY")
    assert isinstance(fig, go.Figure)

def test_plot_term_structure_empty_points():
    fig = plot_term_structure({"points": [], "classification": "normal"}, "SPY")
    assert isinstance(fig, go.Figure)

def test_plot_carry_vrp_returns_figure():
    fig = plot_carry_vrp(18.0, 15.8, 2.2, "SPY")
    assert isinstance(fig, go.Figure)

def test_plot_carry_vrp_cold_start_none():
    # None values must not raise
    fig = plot_carry_vrp(None, None, None, "SPY")
    assert isinstance(fig, go.Figure)

def test_plot_skew_25d_current_returns_figure(skew_dict):
    fig = plot_skew_25d_current(skew_dict, "SPY")
    assert isinstance(fig, go.Figure)

def test_plot_skew_25d_current_none_buckets():
    fig = plot_skew_25d_current({"front_month": None, "second_month": None}, "SPY")
    assert isinstance(fig, go.Figure)
```

---

## Shared Patterns

### Template and layout conventions
**Source:** `gex/analytics.py` — every existing chart function
**Apply to:** All three new chart functions (`plot_skew_25d_current`, `plot_term_structure`, `plot_carry_vrp`)
```python
fig.update_layout(
    template="plotly_dark",
    title=dict(text="...", font_size=13),
    height=280,          # 240–380 depending on chart type
    margin=dict(t=50, b=40, l=65, r=20),
    showlegend=False,
)
```

### Empty-data guard pattern
**Source:** `gex/analytics.py` lines 169–177 (`plot_vol_surface`)
**Apply to:** All new analytics.py chart functions
```python
if not points:   # or if surface_df.empty, or if all buckets are None
    fig = go.Figure()
    fig.update_layout(
        template="plotly_dark",
        title=f"<Chart Name> — {ticker}: no data",
        height=<N>,
        margin=dict(t=50, b=40, l=65, r=20),
    )
    return fig
```

### Cold-start None guard (Streamlit layer)
**Source:** `streamlit_app.py` lines 207, 251
**Apply to:** All tab rendering blocks in `streamlit_app.py` that access `rv20`, `vrp`, `skew` buckets
```python
if value is None:
    st.caption("Not yet available — accumulates after 20 daily runs.")
```

### History load pattern
**Source:** `streamlit_app.py` lines 205–226 (ZGL history chart)
**Apply to:** Skew tab history, Carry tab VRP history
```python
hist30 = _load_history_cached(ticker, days=config.HISTORY_DAYS)
if hist30.empty:
    st.caption("No history yet — daily snapshots accumulate from `gex.run_daily`.")
else:
    chart_df = hist30.sort_values("date")
    # check column exists and has non-NaN rows before building figure
    if "column_name" in chart_df.columns and chart_df["column_name"].notna().any():
        ...
```

### Hovertemplate convention
**Source:** `gex/analytics.py` — all existing traces
**Apply to:** All new chart traces
```python
hovertemplate="%{x|%b %d}<br>Label: %{y:+.2f}pp<extra></extra>",
# <extra></extra> suppresses the default trace name box
```

---

## No Analog Found

No files in this phase are without an analog. All patterns have direct codebase references.

---

## Vol Surface Axis Fix (deferred Phase 6 UAT item)

**What:** Axis labels/symmetry cosmetic issue for IWM specifically.
**Source to inspect:** `gex/analytics.py` lines 211–215 (`PLOT_KS_ANCHORS` usage) and `gex/config.py` (PLOT_KS_ANCHORS definition).
**Likely fix:** Adjust or make `PLOT_KS_ANCHORS` dynamic based on `surface_df["moneyness"]` range.
**When:** During Phase 7 human UAT — inspect IWM surface render. Fix is in `plot_vol_surface()` axis tick generation only.

---

## Metadata

**Analog search scope:** `C:\dev\gamma-omm\streamlit_app.py`, `C:\dev\gamma-omm\gex\analytics.py`, `C:\dev\gamma-omm\gex\validation.py`, `C:\dev\gamma-omm\gex\tests\`
**Files scanned:** 6 (streamlit_app.py, analytics.py, validation.py, test_analytics_summarise.py, test_vol_metrics.py, research.md)
**Pattern extraction date:** 2026-05-26

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/07-institutional-dashboard-rendering/07-RESEARCH|07-RESEARCH]]

<!-- LINKS:END -->
