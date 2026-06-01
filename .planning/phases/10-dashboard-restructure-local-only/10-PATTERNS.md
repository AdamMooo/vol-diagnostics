# Phase 10: Dashboard Restructure (local only) — Pattern Map

**Mapped:** 2026-05-31  
**Files analyzed:** 11 new/modified files  
**Analogs found:** 11 / 11 (100% coverage)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `streamlit_app.py` | UI controller | request-response | self (refactor existing) | exact |
| `gex/analytics.py` | analytics | data-transform | self (refactor existing) | exact |
| `gex/surface_evolution.py` | analytics | data-transform | self (reuse existing) | exact |
| `gex/surface_history.py` | data-access | file-I/O | self (reuse existing) | exact |
| `gex/validation.py` | data-access | file-I/O | self (reuse existing) | exact |
| `gex/vol_metrics.py` | analytics | data-transform | self (reuse existing) | exact |
| `gex/compute.py` | orchestration | CRUD | self (reuse existing) | exact |
| `gex/config.py` | configuration | config | self (add palette tokens) | exact |
| `gex/report.py` | template/builder | data-transform | self (migrate color constants) | exact |

---

## Pattern Assignments

### `streamlit_app.py` (UI controller, request-response)

**Analog:** Self (existing structure, refactor scope)  
**Current structure (lines 247–248):**
```python
tab_surface, tab_skew, tab_term, tab_flow = st.tabs(
    ["Surface", "Skew", "Term Structure", "Flow Context"]
)
```

**Current tab-with-subtabs pattern (Surface, lines 252–253):**
```python
with tab_surface:
    sub_today, sub_change = st.tabs(["Today", "∆ Change"])
    
    with sub_today:
        # content for today's live surface
        for ticker in selected_all:
            # build 3D surface chart
```

**Current Flow tab structure (lines 486–536):**
```python
with tab_flow:
    st.markdown("### Microstructure / Execution Context — model-based, not market prices")
    for ticker in selected_all:
        data = all_data[ticker]
        s = data["summary"]
        spot = data.get("spot")
        c1, c2 = st.columns([3, 2])
        with c1:
            st.plotly_chart(
                plot_strike_gex(data["s_df"], spot, ticker, s),
                use_container_width=True,
            )
```

**History chart pattern (lines 513–536):**
```python
hist30 = _load_history_cached(ticker, days=config.HISTORY_DAYS)
if not hist30.empty:
    chart_df = hist30.sort_values("date")
    zgl_fig = go.Figure()
    zgl_fig.add_trace(go.Scatter(
        x=chart_df["date"],
        y=chart_df["zero_gamma_level"],
        name="γ-flip",
        line=dict(color="#f59e0b", width=1.5),
    ))
    zgl_fig.add_trace(go.Scatter(
        x=chart_df["date"],
        y=chart_df["spot"],
        name="Spot",
        line=dict(color="white", width=1.2, dash="dash"),
    ))
    zgl_fig.update_layout(
        template="plotly_dark",
        title=f"γ-flip vs Spot — {config.HISTORY_DAYS} sessions",
        height=260,
        margin=dict(t=40, b=30, l=60, r=20),
        legend=dict(orientation="h", y=1.15),
    )
```

**Percentile context pattern (lines 350–368):**
```python
hist30 = _load_history_cached(ticker, days=config.HISTORY_DAYS)
skew_series = (
    hist30.dropna(subset=["front_skew"])["front_skew"].tolist()
    if not hist30.empty and "front_skew" in hist30.columns
    else []
)
if front or second:
    m1, m2 = st.columns(2)
    with m1:
        if front:
            st.metric(...)
            if len(skew_series) >= 5:
                pct = int(percentileofscore(skew_series, front["skew"]))
                st.caption(f"{pct}th %ile vs {len(skew_series)}-session history")
```

**Caching pattern (lines 152–165, inferred from imports):**
```python
@st.cache_data(ttl=config.CACHE_TTL_TICKER)
def fetch_ticker(ticker: str) -> dict:
    return compute_ticker(ticker)
```

---

### `gex/analytics.py` (analytics, data-transform)

**Analog:** Self (existing module, repurpose functions)

**Current `plot_strike_gex` signature & structure (lines 66–111):**
```python
def plot_strike_gex(gex_df: pd.DataFrame, spot: float, ticker: str,
                    summary: dict) -> go.Figure:
    """Interactive bar chart of GEX by strike."""
    colors = ["#3b82f6" if v >= 0 else "#ef4444" for v in gex_df["gex"]]
    width = _bar_width(gex_df)
    net_b = summary.get("net_gex", 0) / 1e9

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=gex_df["strike"],
        y=gex_df["gex"] / 1e9,
        marker_color=colors,
        marker_line_width=0,
        width=width,
        hovertemplate="Strike: %{x:.0f}<br>GEX: %{y:.3f}B<extra></extra>",
    ))

    fig.add_vline(x=spot, line_dash="dash", line_color="white", line_width=1.5,
                  annotation_text=f"Spot {spot:.0f}", annotation_position="top right",
                  annotation_font_size=11)
    # ... wall annotations ...
    
    fig.update_layout(
        template="plotly_dark",
        title=dict(text=f"{ticker}  ·  GEX by Strike  ·  Net {net_b:+.2f}B",
                   font_size=13),
        xaxis_title="Strike",
        yaxis_title="GEX ($B)",
        yaxis_ticksuffix="B",
        showlegend=False,
        height=380,
        margin=dict(t=50, b=45, l=65, r=20),
        bargap=0.05,
    )
    return fig
```

**`plot_gamma_profile` demoted-to-expander pattern (lines 114–156):**
```python
def plot_gamma_profile(profile_df: pd.DataFrame, spot: float, ticker: str,
                       summary: dict) -> go.Figure:
    """Interactive line chart of net GEX across spot levels."""
    x = profile_df["spot_level"]
    y = profile_df["net_gex"] / 1e9

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=y.clip(lower=0), fill="tozeroy",
        fillcolor="rgba(59,130,246,0.15)", line_color="rgba(0,0,0,0)",
        showlegend=False, hoverinfo="skip",
    ))
    # ... negative fill, line trace ...
    
    fig.update_layout(
        template="plotly_dark",
        title=dict(text=f"{ticker}  ·  Gamma Profile", font_size=13),
        # ... standard margins/sizing ...
    )
    return fig
```

**Summarise function — already persists walls/zgl (lines 24–47):**
```python
def summarise(gex_df: pd.DataFrame, profile_df: pd.DataFrame,
              spot: float,
              delta_hedge_flow: float | None = None) -> dict:
    """..."""
    net_gex = float(gex_df["gex"].sum())
    zero_gamma = _find_zero_crossing(profile_df)
    
    calls = gex_df[gex_df["gex"] > 0]
    puts = gex_df[gex_df["gex"] < 0]
    call_wall = float(calls.loc[calls["gex"].idxmax(), "strike"]) if not calls.empty else None
    put_wall = float(puts.loc[puts["gex"].idxmin(), "strike"]) if not puts.empty else None
    
    return {
        "net_gex": net_gex,
        "zero_gamma_level": zero_gamma,
        "call_wall": call_wall,
        "put_wall": put_wall,
        "spot": spot,
        "delta_hedge_flow": delta_hedge_flow,
    }
```

**Coverage mask (lines 189–206, used by Evolution):**
```python
def coverage_mask(surface_df, spot, dte_grid, otm_grid, *,
                  dte_floor=5, clip_pct=None):
    """Boolean support mask over the (DTE, %OTM) grid — True where the cell is an
    INTERPOLATION of real quotes, False where it would be EXTRAPOLATION."""
    # ... convex hull logic ...
```

**RBF grid (lines 159–186, shared with Evolution):**
```python
def rbf_grid(surface_df, spot, dte_grid, otm_grid, *,
             dte_floor=5, clip_pct=None):
    """Interpolate the OTM IV scatter onto a (DTE, %OTM) grid via TPS RBF."""
    # ... TPS interpolation with std-normalization ...
```

---

### `gex/surface_evolution.py` (analytics, data-transform)

**Analog:** Self (existing module, reuse load_evolution for Evolution tab)

**`load_evolution` signature (lines 202–223):**
```python
def load_evolution(
    ticker: str,
    horizon: int | None = None,
    days: int = 30,
) -> pd.DataFrame:
    """Load evolution metrics from the store for a single ticker.
    
    Mirrors gex/validation.py load_history pattern.  Optionally filters by horizon.
    Returns an empty DataFrame if the store does not exist or on exception.
    """
    if not STORE.exists():
        return pd.DataFrame()
    try:
        hist = pd.read_parquet(STORE)
        hist["date"] = pd.to_datetime(hist["date"]).dt.date
        hist = hist[hist["ticker"] == ticker].sort_values("date", ascending=False)
        if horizon is not None:
            hist = hist[hist["horizon"] == horizon]
        return hist.head(days).reset_index(drop=True)
    except Exception as exc:
        print(f"[surface_evolution] load_evolution failed for {ticker}: {exc}")
        return pd.DataFrame()
```

**`compute_evolution_scalars` pure function (lines 83–130, for planner to mirror):**
```python
def compute_evolution_scalars(
    IV_diff_masked: np.ndarray,
    otm_grid: np.ndarray,
    dte_grid: np.ndarray,
) -> dict:
    """Decompose a masked ΔIV array into four interpretable scalars.
    
    Pure function — no I/O, no masking.  Receives an already-masked ΔIV array...
    Returns dict with keys: level, rms, skew_change, term_change
    """
    # ... implementation ...
```

**Grid construction (lines 62–76, for consistency across Evolution calls):**
```python
def _construct_grid_axes(surface_df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Build shared DTE and %OTM grid axes from today's surface."""
    dte_max = min(float(surface_df["dte"].max()), float(config.SURFACE_DTE_MAX))
    dte_grid = np.linspace(5.0, dte_max, config.SURFACE_GRID_DTE)
    otm_grid = np.linspace(
        -config.SURFACE_PLOT_OTM_CLIP * 100.0,
        config.SURFACE_PLOT_OTM_CLIP * 100.0,
        config.SURFACE_GRID_LM,
    )
    return dte_grid, otm_grid
```

---

### `gex/surface_history.py` (data-access, file-I/O)

**Analog:** Self (existing module, reuse for Compare dropdown logic)

**`load_surface_snapshot` signature (lines 67–87):**
```python
def load_surface_snapshot(ticker: str, date: datetime.date) -> tuple[pd.DataFrame, float | None]:
    """Load one day's chain points and the spot price recorded that day.
    
    Returns (surface_df, spot). surface_df has columns dte, strike, moneyness,
    log_moneyness, iv_pct. spot is None if the date is not found.
    """
    path = _store_path(ticker)
    if not path.exists():
        return pd.DataFrame(), None
    try:
        hist = pd.read_parquet(path)
        hist["date"] = pd.to_datetime(hist["date"]).dt.date
        rows = hist[hist["date"] == date].reset_index(drop=True)
        if rows.empty:
            return pd.DataFrame(), None
        spot = float(rows["spot"].iloc[0])
        df = rows.drop(columns=["date", "ticker", "spot"])
        return df, spot
    except Exception as exc:
        print(f"[surface_history] load_surface_snapshot failed for {ticker} {date}: {exc}")
        return pd.DataFrame(), None
```

**`list_available_dates` (lines 90–100):**
```python
def list_available_dates(ticker: str) -> list[datetime.date]:
    path = _store_path(ticker)
    if not path.exists():
        return []
    try:
        hist = pd.read_parquet(path, columns=["date"])
        dates = pd.to_datetime(hist["date"]).dt.date.unique()
        return sorted(set(dates), reverse=True)
    except Exception as exc:
        print(f"[surface_history] list_available_dates failed for {ticker}: {exc}")
        return []
```

**`nth_trading_day_back` — for Compare horizon dropdowns (lines 103–121):**
```python
def nth_trading_day_back(
    ticker: str, anchor_date: datetime.date, n: int
) -> datetime.date | None:
    """Find the date that is N trading sessions before anchor_date.
    
    Indexes into the descending list of stored dates — no calendar arithmetic.
    Returns None if anchor_date is not in the store or if fewer than N+1 sessions
    exist after (older than) anchor_date (cold-start case).
    """
    available = list_available_dates(ticker)
    if anchor_date not in available:
        return None
    idx = available.index(anchor_date)
    if idx + n >= len(available):
        return None
    return available[idx + n]
```

---

### `gex/validation.py` (data-access, file-I/O)

**Analog:** Self (existing module, reuse for 2-month price+levels chart)

**`load_history` signature (lines 92–102):**
```python
def load_history(ticker: str, days: int = 30) -> pd.DataFrame:
    """Load rolling history of daily snapshots.
    
    Returns columns: date, ticker, spot, net_gex, zero_gamma_level, call_wall, put_wall,
    front_skew, iv30, rv20, vrp, ... (forward-compatible schema)
    """
    if not STORE.exists():
        return pd.DataFrame()
    try:
        hist = pd.read_parquet(STORE)
        hist["date"] = pd.to_datetime(hist["date"]).dt.date
        hist = hist[hist["ticker"] == ticker].sort_values("date", ascending=False)
        return hist.head(days).reset_index(drop=True)
    except Exception as exc:
        print(f"[validation] load_history failed: {exc}")
        return pd.DataFrame()
```

**Available columns for the 2-month chart (Schema per lines 10–16):**
- `spot` — underlying price (for x-axis)
- `zero_gamma_level` — γ-flip strike
- `call_wall` — call wall strike
- `put_wall` — put wall strike
- `iv30`, `rv20`, `vrp` — for VRP sparkline and percentiles
- `front_skew` — for skew percentile context

---

### `gex/vol_metrics.py` (analytics, data-transform)

**Analog:** Self (existing module, reuse for VRP and scalar strip)

**`compute_rv20` (lines 158–174):**
```python
def compute_rv20(spot_history: pd.Series) -> float | None:
    """20-day realized volatility, annualized.
    
    Expects spot_history sorted oldest-first (ascending date). Does not sort internally.
    Returns None when fewer than 21 prices are available (need 21 prices for 20 returns).
    
    Formula: annualized std of log returns, ddof=1, over the most recent 20 returns.
    """
    if len(spot_history) < 21:
        return None
    prices = spot_history.iloc[-21:].to_numpy(dtype=float)
    if np.any(np.isnan(prices)) or np.any(prices <= 0):
        return None
    log_returns = np.log(prices[1:] / prices[:-1])
    return float(np.sqrt(252) * log_returns.std(ddof=1))
```

**`compute_vrp` (lines 177–190):**
```python
def compute_vrp(iv30: float | None, rv20: float | None) -> float | None:
    """Volatility risk premium: iv30 - rv20.
    
    Both arguments must be decimal fractions (e.g., 0.18 for 18% vol, not 18.0).
    The caller is responsible for normalising iv30 from percentage to decimal before
    calling this function.
    
    Returns None if either input is None.
    Result is in decimal fraction units (e.g., 0.022 for ~2.2 vol points).
    """
    if iv30 is None or rv20 is None:
        return None
    return iv30 - rv20
```

**`compute_skew_25d` (lines 13–67, for skew scalar strip):**
```python
def compute_skew_25d(df: pd.DataFrame, spot: float) -> dict:
    """Per-expiry 25Δ skew bucketed into front_month and second_month.
    
    Returns:
        {
            "front_month": {"put_iv": float, "call_iv": float, "skew": float, "dte": float} | None,
            "second_month": {"put_iv": float, "call_iv": float, "skew": float, "dte": float} | None,
        }
    """
    # ... selection by delta and DTE bucket ...
```

**`compute_term_structure` (lines 70–116, for term spread scalar):**
```python
def compute_term_structure(df: pd.DataFrame, spot: float) -> dict:
    """Build the IV term structure from ATM options and classify the curve shape.
    
    Returns:
        {
            "points": [{"dte": float, "atm_iv": float}, ...],
            "classification": str,
            "front_atm_iv": float | None,
            "back_atm_iv": float | None,
        }
    """
    # ... per-expiry ATM selection + classification ...
```

---

### `gex/compute.py` (orchestration, CRUD)

**Analog:** Self (existing module, keep as single source of truth per D-15)

**`compute_ticker` signature (lines 34–111):**
```python
def compute_ticker(ticker: str) -> dict:
    """Full pipeline for one ticker.
    
    Returns:
        {
          "summary":        dict — net_gex, zero_gamma_level, call/put_wall, iv30, rv20, vrp, ...
          "s_df":           DataFrame — strike-level GEX
          "p_df":           DataFrame — gamma profile
          "spot":           float
          "surface_df":     DataFrame — vol surface
          "skew_df":        DataFrame — per-expiry skew (feeds parquet history columns)
          "skew":           dict | None — 25d skew buckets (front_month, second_month)
          "term_structure": dict | None — classification + ATM IV points
          "rv20":           float | None — 20-day annualized realized vol
          "vrp":            float | None — IV30 − RV20
        }
    """
    snapshot = load_chain(ticker)
    df = add_greeks(snapshot.chains, spot=snapshot.spot, today=snapshot.as_of)
    df = compute_gex(df, spot=snapshot.spot)
    
    s_df = strike_gex(df)
    r = _get_risk_free_rate()
    p_df = gamma_profile(df, spot=snapshot.spot, r=r)
    surface_df = vol_surface_data(df, spot=snapshot.spot)
    # ... rest of pipeline, returns dict ...
```

**Headless design pattern (lines 1–7):**
- No Streamlit calls in `compute_ticker` — pure data pipeline
- Wrapping is done by callers: `run_daily.process_ticker()` adds error handling, `streamlit_app.fetch_ticker()` adds `@st.cache_data`
- This allows Phase 11 email to reuse the same function without Streamlit dependency

---

### `gex/config.py` (configuration, config)

**Analog:** Self (existing module, add palette token section)

**Current structure (lines 1–164):**
```python
"""Central configuration for gamma-omm. Magic numbers gathered here..."""

MIN_OI: int = 100
MIN_DTE: int = 1
MAX_IV: float = 3.0
RISK_FREE_FALLBACK: float = 0.05

# ... domain constants: PROFILE_N_POINTS, SURFACE_* settings, SKEW_*, PLOT_*, CACHE_TTL_* ...

HISTORY_DAYS: int = 30
```

**Where to add palette tokens (new section, after line 163):**
The existing project uses `#f59e0b` (amber), `#16a34a` (green-600), `#dc2626` (red-600), `#64748b` (slate-500) scattered across `streamlit_app.py` and `gex/report.py`. Consolidate these into a shared config dict so Phase 11 email can reference the same values.

---

### `gex/report.py` (template/builder, data-transform)

**Analog:** Self (existing module, migrate REGIME_COLOR to shared config)

**Current REGIME_COLOR (lines 15–20):**
```python
# Sign-of-net-gex visual cue for the accent bar.
REGIME_COLOR = {
    "positive": "#16a34a",  # green-600
    "negative": "#dc2626",  # red-600
    "zero":     "#64748b",  # slate-500 — consistent with analytics._sign_color()
}
```

**Helper colors (lines 22–33):**
```python
TICKER_LABEL = {
    "SPY": "SPY  S&P 500",
    "QQQ": "QQQ  Nasdaq 100",
    "IWM": "IWM  Russell 2000",
}

LABEL_GRAY  = "#94a3b8"
RULE_COLOR  = "#cbd5e1"
POS_GREEN   = "#16a34a"
NEG_RED     = "#dc2626"
```

**`_signed_color` helper (lines 82–85):**
```python
def _signed_color(val: float | None) -> str:
    if val is None or val == 0:
        return LABEL_GRAY
    return POS_GREEN if val >= 0 else NEG_RED
```

---

## Shared Patterns

### Tab & Sub-Tab Construction (Streamlit)

**Source:** `streamlit_app.py` lines 247–253  
**Apply to:** All new tabs (Calculus, Evolution, Positioning sub-tabs within Surface)

```python
# 4-tab layout
tab_surface, tab_calculus, tab_evolution, tab_positioning = st.tabs(
    ["Surface", "Calculus+VRP", "Evolution", "Positioning"]
)

# Sub-tabs within Surface (preserve Today/Compare)
with tab_surface:
    sub_today, sub_compare = st.tabs(["Today", "Compare"])
```

### History Cache Pattern (Streamlit)

**Source:** `streamlit_app.py` lines 152–165 (inferred)  
**Apply to:** All history-driven charts (VRP sparkline, 2-month price+walls, evolution small-multiples)

```python
@st.cache_data(ttl=config.CACHE_TTL_HISTORY)
def _load_history_cached(ticker: str, days: int = config.HISTORY_DAYS) -> pd.DataFrame:
    return load_history(ticker, days=days)

# Usage in chart blocks:
hist = _load_history_cached(ticker)
if not hist.empty:
    # build chart from hist columns
```

### Column/Percentile Context (Streamlit)

**Source:** `streamlit_app.py` lines 350–368  
**Apply to:** VRP headline, skew/term scalars, any metric with historical context

```python
hist = _load_history_cached(ticker, days=config.HISTORY_DAYS)
series = hist.dropna(subset=["column_name"])["column_name"].tolist()
if len(series) >= 5:
    pct = int(percentileofscore(series, current_value))
    st.caption(f"{pct}th %ile vs {len(series)}-session history")
```

### Plotly Chart with Dark Template + Layout

**Source:** `streamlit_app.py` lines 516–536 (ZGL chart); `gex/analytics.py` lines 99–111  
**Apply to:** All new Plotly figures (VRP sparkline, evolution small-multiples, price+walls)

```python
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=chart_df["date"],
    y=chart_df["metric"],
    line=dict(color="#f59e0b", width=1.5),  # accent color (to be moved to config)
    # ... mode, hovertemplate ...
))
fig.add_hline(y=0, line_color="rgba(255,255,255,0.15)", line_width=0.8)
fig.update_layout(
    template="plotly_dark",
    title="...",
    height=260,
    yaxis_title="...",
    margin=dict(t=40, b=30, l=60, r=20),
    showlegend=False,
)
st.plotly_chart(fig, use_container_width=True)
```

### Multi-Ticker Loop Pattern (Streamlit)

**Source:** `streamlit_app.py` lines 496–536  
**Apply to:** Positioning tab per-ticker OI + price+walls charts

```python
for ticker in selected_all:
    if ticker not in all_data:
        continue
    data = all_data[ticker]
    s = data["summary"]
    spot = data.get("spot")
    
    c1, c2 = st.columns([3, 2])  # or proportions per layout
    with c1:
        st.plotly_chart(chart_a, use_container_width=True)
    with c2:
        st.plotly_chart(chart_b, use_container_width=True)
```

### Bar Chart for Strike-Level Data (Plotly)

**Source:** `gex/analytics.py` lines 66–111 (`plot_strike_gex`)  
**Apply to:** OI-by-strike chart (Chart A, Positioning tab)

- **Coloring:** call OI as blue (`#3b82f6`), put OI as red (`#ef4444`)
- **Annotations:** spot (white dash), walls (blue/red dots), γ-flip (amber)
- **Layout:** title includes net value, yaxis suffix ("B" for billions or appropriate units), `bargap=0.05`, `height=380`

```python
colors = ["#3b82f6" if v >= 0 else "#ef4444" for v in oi_data]
fig.add_trace(go.Bar(
    x=oi_data["strike"],
    y=oi_data["oi"] / 1e9,
    marker_color=colors,
    hovertemplate="Strike: %{x:.0f}<br>OI: %{y:.2f}B<extra></extra>",
))
fig.add_vline(x=spot, line_dash="dash", line_color="white", ...)
```

### Line Chart for Time-Series (Plotly, 30–60 day scale)

**Source:** `streamlit_app.py` lines 513–536 (γ-flip vs Spot)  
**Apply to:** 2-month price+walls/flip chart (Chart B, Positioning tab)

- **Traces:** spot (white, dashed), γ-flip (amber, solid), call wall (blue, dotted), put wall (red, dotted)
- **Hovertemplate:** e.g., `"%{x|%b %d}<br>Spot: %{y:,.0f}<extra></extra>"`
- **Layout:** `height=260`, margin consistent, `legend=dict(orientation="h", y=1.15)`

### Small-Multiples Grid (Streamlit + Plotly)

**Source:** (new pattern, inferred from Evolution spec in CONTEXT.md D-10)  
**Apply to:** Evolution tab (5-day, 10-day, 20-day radio → 4 small-multiples stacked)

```python
horizon = st.radio("Horizon (days)", options=[5, 10, 20], horizontal=True, index=0)
evol_data = load_evolution(ticker, horizon=horizon, days=30)

if evol_data.empty:
    st.caption("No evolution data yet — accumulates from `run_daily` runs forward.")
else:
    # Build 4 panels: level, rms, skew_change, term_change
    # Each overlays SPY, QQQ, IWM
    for metric_name in ["level", "rms", "skew_change", "term_change"]:
        fig = go.Figure()
        for ticker_name in ["SPY", "QQQ", "IWM"]:
            ticker_evol = evol_data[evol_data["ticker"] == ticker_name]
            fig.add_trace(go.Scatter(
                x=ticker_evol["date"],
                y=ticker_evol[metric_name],
                name=ticker_name,
            ))
        fig.add_hline(y=0, ...)
        fig.update_layout(template="plotly_dark", yaxis_title=f"{metric_name} (pp)")
        st.plotly_chart(fig, use_container_width=True)
```

### Relative-Horizon Dropdown Pattern (Streamlit, for Compare)

**Source:** `streamlit_app.py` lines 288–293 (current selectbox)  
**Apply to:** Surface → Compare sub-tab for two-date selection

```python
available = list_available_dates(ticker)
if not available:
    st.caption(f"{ticker}: no historical snapshots yet — accumulates from `run_daily` runs forward.")
else:
    prior_date = st.selectbox(
        f"{ticker} — compare against",
        options=available,
        format_func=lambda d: d.strftime("%b %d, %Y"),
        key=f"surface_prior_{ticker}",
    )
    surface_df_prior, spot_prior = load_surface_snapshot(ticker, prior_date)
```

**D-11 expansion (relative horizons via `nth_trading_day_back`):**
```python
horizon_options = {
    "live": None,
    "1d": 1,
    "5d": 5,
    "10d": 10,
    "20d": 20,
    "30d": 30,
    "60d": 60,
}
# Dropdown resolves to actual date via nth_trading_day_back(ticker, today, n)
```

### Expander for Mechanism Details (Streamlit)

**Source:** `streamlit_app.py` lines 539–… (Methodology & Assumptions expander)  
**Apply to:** Gamma profile demoted to expander in Positioning tab

```python
with st.expander("γ-flip & walls — model derivation", expanded=False):
    st.markdown("""
    **Gamma profile.** Beta-gamma sweep across ±15% spot range, BS pricing...
    **Zero-gamma level.** Linear interpolation of the gamma profile...
    **Walls.** Strike-level GEX extrema...
    **Model assumptions.** Dealers net short all options (Garleanu et al. 2009)...
    """)
    st.plotly_chart(plot_gamma_profile(...), use_container_width=True)
```

### Pure Function for Headless Analysis (Python)

**Source:** `gex/vol_metrics.py` (all functions are pure; `gex/compute.py` is orchestration-only)  
**Apply to:** VRP headline builder, evolution 5-day summary, positioning level formatters (per D-15)

**Convention:**
- No I/O (no file reads, no Streamlit calls)
- Return plain Python types (dict, str, float, tuple)
- Accept DataFrame or Series only when absolutely necessary; prefer scalar inputs for composability
- Document input assumptions (e.g., "spot_history must be sorted oldest-first")

```python
def vrp_headline(iv30: float, rv20: float, vrp: float, percentile: int) -> str:
    """Build the plain-read VRP string.
    
    Args:
        iv30: IV30 as percentage (e.g., 18.5)
        rv20: RV20 as percentage
        vrp: IV30 - RV20 in percentage points
        percentile: historical percentile of VRP vs 30-session lookback
    
    Returns:
        Plain-language read, e.g., "vol rich +8.7pp, 82nd %ile — premium-selling favored..."
    """
    # ... pure logic, no side effects ...
```

---

## Accent Color Consolidation (D-14)

**Current scattered colors:**
- Amber (`#f59e0b`) — skew history, γ-flip, accent bars
- Green (`#16a34a` / `#26a34a`) — net GEX positive
- Red (`#dc2626` / `#ef4444`) — net GEX negative, put wall
- Blue (`#3b82f6`) — call wall, positive bar
- Slate (`#64748b`) — zero/neutral

**Consolidation target (to be added to `gex/config.py`):**
```python
# ── Palette tokens (D-14) ────────────────────────────────────────────────────────

PALETTE = {
    "accent": "#f59e0b",      # Bloomberg-like amber
    "positive": "#16a34a",    # Green-600 (net GEX long gamma)
    "negative": "#dc2626",    # Red-600 (net GEX short gamma)
    "neutral": "#64748b",     # Slate-500 (zero/undefined)
    "call": "#3b82f6",        # Blue-500 (call wall, positive OI)
    "put": "#ef4444",         # Red-400 (put wall, negative OI)
}
```

**Usage in Phase 10 code:**
```python
# In streamlit_app.py, gex/analytics.py:
color = config.PALETTE["accent"]  # instead of "#f59e0b"
color = config.PALETTE["positive"]  # instead of "#16a34a"

# In gex/report.py (Phase 11 consumption):
import config
REGIME_COLOR = config.PALETTE  # replaces the inline dict
```

---

## No Analog Found

None — all files have clear analogs in the existing codebase.

---

## Metadata

**Analog search scope:**
- `streamlit_app.py` — 603 lines, existing 4-tab + sub-tab structure
- `gex/analytics.py` — 300+ lines, plotting + summarise functions
- `gex/surface_evolution.py` — 300+ lines, load_evolution + compute_evolution_scalars
- `gex/surface_history.py` — 122 lines, surface snapshot store
- `gex/validation.py` — 103 lines, GEX snapshot history
- `gex/vol_metrics.py` — 191 lines, pure metric functions
- `gex/compute.py` — 112 lines, single source of truth orchestration
- `gex/config.py` — 164 lines, central configuration
- `gex/report.py` — 200+ lines, HTML email builder + color constants

**Files scanned:** 9 core GEX + Streamlit modules  
**Pattern extraction date:** 2026-05-31  

---

## Ready for Planning

Pattern mapping complete. Planner can now:

1. **Tab restructuring** — use existing tab/sub-tab construction from `streamlit_app.py` lines 247–253
2. **Analytics repurposing** — convert `plot_strike_gex` to OI-by-strike by swapping column reference (keep bar-chart signature)
3. **History-driven charts** — extend 30-session ZGL chart to ~42-session price+walls using existing `load_history` columns (spot, call_wall, put_wall, zero_gamma_level, iv30, rv20, vrp)
4. **Evolution small-multiples** — call `load_evolution(ticker, horizon, days)` per horizon radio, build 4 panels overlaying SPY/QQQ/IWM per `compute_evolution_scalars` output
5. **Compare dropdowns** — use `nth_trading_day_back(ticker, anchor_date, n)` to resolve relative horizons to actual dates; default live vs 5d
6. **VRP headline & scalar strip** — build headless functions in new analysis modules, mirroring `compute_vrp` + `compute_skew_25d` + `compute_term_structure` patterns
7. **Shared palette** — add `PALETTE` dict to `config.py`, migrate `REGIME_COLOR` in `report.py` to reference it
8. **Email readiness** — keep all analysis functions pure (no Streamlit), allow Phase 11 to reuse directly


---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/10-dashboard-restructure-local-only/10-CONTEXT|10-CONTEXT]]
- [[_planning/gamma-omm/phases/10-dashboard-restructure-local-only/10-DISCUSSION-LOG|10-DISCUSSION-LOG]]

<!-- LINKS:END -->
