# Phase 7: Institutional Dashboard Rendering — Research

**Researched:** 2026-05-26
**Domain:** Streamlit dashboard restructure — Plotly charting, tab layout, vol diagnostics UI
**Confidence:** HIGH (all findings verified against live codebase)

---

## Summary

Phase 7 is a pure rendering phase. Every metric it needs to display is already computed and available on the `compute_ticker()` return dict. The work is: (1) restructure `streamlit_app.py` from a per-ticker expander model to a 5-tab top-level layout, (2) write three new Plotly chart functions in `analytics.py` for skew history, term structure, and carry/VRP, (3) move GEX content to a clearly-labeled Flow Context tab, and (4) enforce label precision throughout.

The key insight is that the current architecture puts the vol surface, GEX strikes, and history all inside per-ticker expanders with nested sub-tabs. Phase 7 inverts this: the top-level navigation becomes the 5 module tabs (Surface, Skew, Term Structure, Carry, Flow Context), and each tab renders all three tickers side-by-side (or stacked) rather than requiring the user to expand per-ticker panels.

The `compute_ticker()` return dict already has `skew` (dict with front_month/second_month buckets), `term_structure` (dict with points and classification), `rv20`, and `vrp` — all Phase 6 deliverables. The rolling history for skew is already in the parquet store as `front_skew` column; rolling history for VRP/carry requires `rv20` and `vrp` columns that were added in Phase 6.

There is one cosmetic issue deferred from Phase 6 UAT: vol surface axis labels/symmetry. This is in scope for Phase 7 to close.

There is also a label discrepancy to note: `plot_skew_term_structure()` in `analytics.py` currently exists and produces a per-expiry skew-vs-DTE line chart. This is NOT the same as the Phase 7 Skew tab (which shows front-month and second-month 25Δ skew + rolling history). The existing function may be reused for a term structure sub-view, but Phase 7 needs to clearly separate "25Δ skew" from "ATM IV term structure."

**Primary recommendation:** Restructure tab layout first (top-level 5 tabs replacing per-ticker expanders), then add chart functions one module at a time, then move GEX content last.

---

## User Constraints (from CONTEXT.md — Phase 6 locked decisions, inherited)

### Locked Decisions

- Observable prices first; GEX is secondary and clearly labeled
- No "positioning narrative", no GEX percentile rank as primary metric
- All labels must be precise: "25Δ put-call skew", "IV30 − RV20", not "fear gauge"
- Surface: Viridis, no GEX overlays — `plot_vol_surface(surface_df, ticker, spot)` signature is final
- GEX stays in the pipeline but is demoted to Flow Context tab only
- Metric labels: "25Δ put-call skew", "vol carry / VRP", "Microstructure / Execution Context — model-based, not market prices"

### Deferred to v3.3+

- OI tilt (TILT-01)
- Front skew gauge (SKEW-01)
- Vol surface shape change metrics
- z-scores and percentile ranks for skew/term structure
- Email template updates

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| COV-01 | `tests/test_data_loader.py`: happy-path CBOE JSON parse, filter tests, malformed symbol skip | REQUIREMENTS.md traceability maps COV-01/05 to "Phase 7" but these are test coverage requirements, not rendering requirements. See scope clarification below. |
| COV-02 | `tests/test_report.py`: build_email() non-empty HTML, ticker headers, accent bar colors | Same — test coverage, Phase 7 scope per REQUIREMENTS.md traceability |
| COV-03 | `tests/test_emailer.py`: ValueError on no recipients, Outlook COM mocked | Same |
| COV-04 | `tests/test_run_daily.py`: orchestration happy path, 3 tickers mocked, parquet written | Same |
| COV-05 | `tests/test_analytics_charts.py`: chart functions return Figure without error, zero-exposure edge | Same |

**Scope clarification — COV-01 through COV-05 vs v3.2 roadmap:**

REQUIREMENTS.md traceability maps COV-01/05 to "Phase 7" but ROADMAP.md moved these to "Backlog (999.2)" after the v3.2 strategic reframe. The ROADMAP explicitly states:

> 999.2: Critical-Path Test Coverage — Status: BACKLOG — Deferred pending 999.1 outcome

This creates a traceability mismatch. REQUIREMENTS.md was last updated 2026-05-12 (pre-reframe); the ROADMAP is authoritative for v3.2 scope.

**Recommendation for planner:** Phase 7 success criteria (from ROADMAP) define 5 rendering outcomes, not test coverage. COV-01/05 should be treated as out-of-scope for Phase 7 execution plans. The planner should note this mismatch but follow ROADMAP Phase 7 success criteria as the definitive scope.

COV-05 (test_analytics_charts.py covering chart functions without error) is the one exception — the new Phase 7 chart functions should have basic smoke tests added to an existing or new test file. This is prudent but is a bonus, not a gate.
</phase_requirements>

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Top-level tab structure | `streamlit_app.py` | — | Layout is pure rendering, no compute |
| Surface tab rendering | `streamlit_app.py` | `gex/analytics.py` (chart function already exists) | Reuse `plot_vol_surface()` — already correct |
| Skew tab — current values | `streamlit_app.py` | `gex/analytics.py` (new chart function needed) | `compute_ticker()["skew"]` has the data; need a display function |
| Skew tab — rolling history chart | `streamlit_app.py` | `gex/validation.py` (parquet source, `front_skew` column) | History tab already does this — reuse pattern |
| Term Structure tab — line chart | `streamlit_app.py` | `gex/analytics.py` (new chart function needed) | `compute_ticker()["term_structure"]` has points + classification |
| Carry tab — IV30/RV20/VRP | `streamlit_app.py` | `gex/analytics.py` (new chart function needed) | `compute_ticker()["rv20"]`, `["vrp"]`, `summary["iv30"]` |
| Carry tab — rolling history | `streamlit_app.py` | `gex/validation.py` (`rv20`, `vrp` columns added Phase 6) | Load history, filter columns — same pattern as ZGL history |
| Flow Context tab (GEX) | `streamlit_app.py` | `gex/analytics.py` (existing `plot_strike_gex`, `plot_gamma_profile`) | Move existing GEX charts here with clear header |
| Regime summary cards | `streamlit_app.py` | — | Stays — header row of cards for at-a-glance |
| Label precision enforcement | `streamlit_app.py` | `gex/analytics.py` (chart titles) | No deterministic language in any rendered text |

---

## Standard Stack

### Core (all already installed — no new dependencies)

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| streamlit | existing | Tab layout, `st.tabs()`, columns, expanders | [VERIFIED: requirements.txt] |
| plotly | existing | All charts (`go.Figure`, `go.Scatter`, `go.Surface`, `go.Bar`) | [VERIFIED: analytics.py imports] |
| pandas | existing | History DataFrame, parquet I/O | [VERIFIED: validation.py] |
| numpy | existing | Any numeric formatting | [VERIFIED: analytics.py imports] |

**No new dependencies required for Phase 7.** All chart infrastructure is Plotly. The `st.tabs()` API has been available since Streamlit 1.x.

**Version verification:** [ASSUMED — Streamlit version not pinned in requirements.txt; `st.tabs()` has been available since early Streamlit 1.x and is safe to use]

---

## Architecture Patterns

### System Architecture Diagram

```
User opens browser
        |
  streamlit_app.py
        |
   [Regime Cards — top row, all tickers, always visible]
        |
   st.tabs(["Surface", "Skew", "Term Structure", "Carry", "Flow Context"])
        |
        +──── Surface tab
        |         all_data[ticker]["surface_df"]
        |         → plot_vol_surface() [existing, analytics.py]
        |         → rendered per-ticker (columns or expander)
        |
        +──── Skew tab
        |         all_data[ticker]["skew"]  {front_month, second_month}
        |         → plot_skew_25d_current() [NEW, analytics.py]
        |         _load_history_cached(ticker)["front_skew"]
        |         → rolling history Scatter [inline in streamlit_app.py or extracted]
        |
        +──── Term Structure tab
        |         all_data[ticker]["term_structure"]  {points, classification}
        |         → plot_term_structure() [NEW, analytics.py]
        |
        +──── Carry tab
        |         all_data[ticker]["rv20"], ["vrp"], summary["iv30"]
        |         → plot_carry_vrp() [NEW, analytics.py]
        |         _load_history_cached(ticker)["rv20"], ["vrp"]
        |         → rolling VRP history Scatter [inline or extracted]
        |
        +──── Flow Context tab
                  all_data[ticker]["s_df"], ["p_df"], summary
                  → plot_strike_gex() [existing, analytics.py]
                  → plot_gamma_profile() [existing, analytics.py]
                  [Header: "Microstructure / Execution Context — model-based, not market prices"]
```

### Recommended Project Structure (changes only)

```
gex/
└── analytics.py        # ADD: plot_skew_25d_current(), plot_term_structure(), plot_carry_vrp()
streamlit_app.py        # RESTRUCTURE: tab layout, move GEX to Flow Context, add new tab renderers
gex/tests/
└── test_analytics_charts.py  # NEW (or extend existing) — smoke tests for new chart functions
```

### Pattern 1: Top-level st.tabs() replacing per-ticker expanders

**What:** `st.tabs()` creates persistent tab navigation at the top of the page. Each tab contains a full-width rendering loop over all selected tickers.

**When to use:** Module-first navigation — user selects what diagnostic to examine, then sees it for all tickers.

**Example:**
```python
# Source: [VERIFIED: streamlit_app.py — current structure uses st.tabs() inside expanders]
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

**Layout decision (Claude's discretion):** Three tickers in one tab can be arranged as:
- Stacked vertically (simple, works at any window width)
- Three columns (compact, but 3D surfaces may be cramped at `width/3`)

Recommended: **stacked vertically** for Surface (3D surface needs full width), **columns** for Skew and Carry (2D charts are narrower).

### Pattern 2: Extracting current skew values from compute_ticker()["skew"]

**What:** `compute_ticker()["skew"]` returns:
```python
{
    "front_month": {"put_iv": float, "call_iv": float, "skew": float, "dte": float} | None,
    "second_month": {"put_iv": float, "call_iv": float, "skew": float, "dte": float} | None,
}
```

**Display format:** Show front and second month as a small metric table or two `st.metric()` calls. Rolling 30-day history from parquet `front_skew` column.

**Example (current values display):**
```python
# Source: [VERIFIED: vol_metrics.py — confirmed return structure]
skew_data = data.get("skew") or {}
front = skew_data.get("front_month")
second = skew_data.get("second_month")

col1, col2 = st.columns(2)
with col1:
    if front:
        st.metric(f"Front month ({front['dte']:.0f} DTE)", f"{front['skew']:+.1f}pp",
                  help="25Δ put IV − 25Δ call IV")
    else:
        st.caption("Front month: insufficient chain data")
with col2:
    if second:
        st.metric(f"Second month ({second['dte']:.0f} DTE)", f"{second['skew']:+.1f}pp",
                  help="25Δ put IV − 25Δ call IV")
    else:
        st.caption("Second month: insufficient chain data")
```

### Pattern 3: Rolling history from parquet for skew

**What:** `_load_history_cached(ticker)` returns a DataFrame with `date`, `front_skew` columns. The skew history chart is already prototyped in the existing History tab (lines 228–254 of `streamlit_app.py`). Phase 7 moves/reuses this logic in the Skew tab.

**Current location in streamlit_app.py:**
```python
# Lines 228–254 — skew history chart (currently inside History sub-tab inside expander)
if "front_skew" in chart_df.columns and chart_df["front_skew"].notna().any():
    skew_hist = chart_df.dropna(subset=["front_skew"])
    skew_fig = go.Figure()
    skew_fig.add_trace(go.Scatter(
        x=skew_hist["date"], y=skew_hist["front_skew"],
        name="Skew (25Δ)",
        mode="lines+markers",
        ...
    ))
```

This code can be extracted to `plot_skew_history()` in `analytics.py` or kept inline in `streamlit_app.py`. Given the existing pattern (ZGL history is inline), keeping it inline in `streamlit_app.py` is consistent.

### Pattern 4: Term structure line chart

**What:** `compute_ticker()["term_structure"]` returns:
```python
{
    "points": [{"dte": float, "atm_iv": float}, ...],  # sorted by DTE
    "classification": "normal" | "flat" | "inverted" | "humped",
    "front_atm_iv": float | None,
    "back_atm_iv": float | None,
}
```

**New function needed:** `plot_term_structure(term_structure_dict, ticker)` in `analytics.py`.

```python
# Source: [ASSUMED — pattern follows existing plot_skew_term_structure style]
def plot_term_structure(ts: dict, ticker: str) -> go.Figure:
    points = ts.get("points", [])
    classification = ts.get("classification", "normal")
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

**Label constraint:** Classification label in chart title must be restrained. "normal", "flat", "inverted", "humped" are acceptable — no "bullish" / "fearful" / "stressed" interpretations.

### Pattern 5: Carry / VRP display

**What:** Three items to display per ticker:
1. Current IV30 (from `summary["iv30"]` — percentage, e.g. 18.0)
2. Current RV20 (from `data["rv20"]` — decimal fraction, e.g. 0.158; must be displayed as % so multiply by 100)
3. Current VRP (from `data["vrp"]` — decimal fraction, e.g. 0.022; display as vol points, multiply by 100)
4. Rolling VRP history from parquet `vrp` column

**Unit handling (CRITICAL):** `iv30` in summary is in percentage units (18.0). `rv20` and `vrp` from `compute_ticker()` are in decimal fraction units (0.158, 0.022). Display layer must normalize for consistent labeling.

```python
# Source: [VERIFIED: compute.py:88-89 — iv30_decimal = snapshot.iv30 / 100.0 before compute_vrp]
# iv30 in summary is percentage; rv20 and vrp returned by compute_ticker() are decimal fractions
iv30_pct = summary.get("iv30")          # e.g. 18.0 (percent)
rv20 = data.get("rv20")                 # e.g. 0.158 (decimal)
vrp = data.get("vrp")                   # e.g. 0.022 (decimal)

rv20_pct = rv20 * 100 if rv20 is not None else None      # → 15.8
vrp_pp = vrp * 100 if vrp is not None else None          # → 2.2 vol points
```

**New function needed:** `plot_carry_vrp(iv30_pct, rv20_pct, vrp_pp, ticker)` in `analytics.py` — a grouped bar chart showing IV30 vs RV20, with a separate VRP spread indicator.

### Pattern 6: Flow Context tab — move existing GEX content

**What:** The existing `tab_strikes` content (strike GEX bar chart + gamma profile) moves here verbatim. The tab gets a prominent header.

**Required header text (locked):** "Microstructure / Execution Context — model-based, not market prices"

**What moves:**
- `plot_strike_gex(data["s_df"], spot, ticker, s)` — unchanged
- `plot_gamma_profile(data["p_df"], spot, ticker, s)` — unchanged
- ZGL rolling history chart (currently in History sub-tab) — can stay here or in a sub-expander

**What does NOT move to Flow Context:**
- The regime summary cards (these stay at top of page — they show spot, net GEX, γ-flip, Skew 25Δ, IV30 concisely)

### Pattern 7: Cold-start None handling in all tabs

**What:** On cold start (no parquet history, or first run before 20 sessions), `rv20`, `vrp`, and some `skew` buckets will be `None`. Each tab must gracefully handle missing data without crashing.

**Standard pattern (already used throughout streamlit_app.py):**
```python
if value is None:
    st.caption("Not yet available — accumulates from daily runs.")
```

**Source:** `streamlit_app.py:207` — `if hist30.empty: st.caption("No history yet...")` — same idiom.

### Anti-Patterns to Avoid

- **Rendering GEX in any tab other than Flow Context:** The entire point of Phase 7 is demoting GEX. No GEX bar charts, no gamma profiles, no zero-gamma level annotations appear outside the Flow Context tab.
- **Deterministic language in labels:** "vol is high" or "protection is expensive" are editorial. Use: "IV30 18.0%" not "expensive protection". Use "vol carry / VRP" not "value trade".
- **Displaying classification labels as trade signals:** "inverted" term structure is a descriptor, not an action. Label must be restrained (e.g., "Term structure: inverted" not "Sell the back").
- **Unit inconsistency in Carry tab:** rv20 and vrp come out of compute_ticker() as decimal fractions. If rendered directly as numbers they appear as 0.022 instead of 2.2pp. Must multiply by 100 at the display layer.
- **Keeping per-ticker expander as the primary navigation paradigm:** The old structure (cards → expanders → sub-tabs) must be replaced. Regime cards stay as a header row. The 5 module tabs become the primary navigation.
- **Assuming skew history column is named `skew_25d`:** The parquet column is `front_skew` (added by `compute_skew()` output, not `compute_skew_25d()`). The rolling history shows `front_skew` (25Δ put − 50Δ ATM call convention). This is a known approximation — it reflects the old `compute_skew()` formula. Phase 7 should note this in chart annotation rather than recomputing. [ASSUMED: acceptable to use `front_skew` as proxy for rolling history until Phase 8+]

---

## What `compute_ticker()` Returns — Verified Inventory

**Source:** [VERIFIED: gex/compute.py lines 33-98]

```python
{
    "summary": {
        "net_gex": float,
        "zero_gamma_level": float | None,
        "call_wall": float | None,
        "put_wall": float | None,
        "spot": float,
        "delta_hedge_flow": float,
        "ticker": str,
        "iv30": float | None,          # percentage units (e.g. 18.0)
        "price_change_pct": float | None,
        "front_skew": float | None,    # from old compute_skew() — pp
        "rv20": float | None,          # decimal fraction
        "vrp": float | None,           # decimal fraction
    },
    "s_df": DataFrame,                 # strike-level GEX (columns: strike, gex)
    "p_df": DataFrame,                 # gamma profile (columns: spot_level, net_gex)
    "spot": float,
    "surface_df": DataFrame,           # vol surface (columns: dte, strike, moneyness, log_moneyness, iv_pct)
    "skew_df": DataFrame,              # legacy per-expiry skew from compute_skew()
    "skew": {                          # NEW Phase 6 — symmetric 25Δ convention
        "front_month": {"put_iv": float, "call_iv": float, "skew": float, "dte": float} | None,
        "second_month": {"put_iv": float, "call_iv": float, "skew": float, "dte": float} | None,
    },
    "term_structure": {                # NEW Phase 6
        "points": [{"dte": float, "atm_iv": float}, ...],
        "classification": "normal" | "flat" | "inverted" | "humped",
        "front_atm_iv": float | None,
        "back_atm_iv": float | None,
    },
    "rv20": float | None,              # decimal fraction
    "vrp": float | None,               # decimal fraction
}
```

**Note:** `rv20` and `vrp` appear in both `summary` (lines 90-91) and as top-level keys (lines 97-98). Either access path works. Top-level keys are cleaner for the render layer.

---

## Existing Chart Functions in analytics.py — Reuse vs New

**Source:** [VERIFIED: gex/analytics.py]

| Function | Status | Phase 7 Use |
|----------|--------|-------------|
| `plot_strike_gex(gex_df, spot, ticker, summary)` | Existing — unchanged | Flow Context tab only |
| `plot_gamma_profile(profile_df, spot, ticker, summary)` | Existing — unchanged | Flow Context tab only |
| `plot_vol_surface(surface_df, ticker, spot)` | Existing — stripped Phase 6 | Surface tab |
| `plot_skew_term_structure(skew_df, ticker)` | Existing — renders `skew_df` (legacy per-expiry skew by DTE) | Can be repurposed for a "skew across expirations" view in Skew tab, but NOT the primary 25Δ display |
| `plot_skew_25d_current()` | **NEEDS CREATION** | Skew tab — current front/second month values |
| `plot_term_structure()` | **NEEDS CREATION** | Term Structure tab — ATM IV line chart with classification |
| `plot_carry_vrp()` | **NEEDS CREATION** | Carry tab — IV30 vs RV20 bar + VRP spread |

**Note on `plot_skew_term_structure()`:** This function plots skew (pp) on the y-axis vs DTE on the x-axis from the `skew_df` DataFrame. This is a "skew curve across expirations" view — potentially useful in the Skew tab as a secondary chart. It does NOT replace the primary 25Δ front/second month display.

---

## Current streamlit_app.py Structure — What Changes

**Source:** [VERIFIED: streamlit_app.py — full read]

### Current structure (to be replaced):
```
[Regime cards — top row]
[Per-ticker expander loop]
  └── [sub-tabs: Strikes | Vol | History]
        Strikes:  plot_strike_gex, plot_gamma_profile
        Vol:      plot_vol_surface, plot_skew_term_structure
        History:  ZGL history chart, skew history chart
[Methodology expander]
```

### Phase 7 target structure:
```
[Regime cards — top row, unchanged]
[Top-level st.tabs: Surface | Skew | Term Structure | Carry | Flow Context]
  Surface tab:
    for each ticker: plot_vol_surface (stacked vertically)
  Skew tab:
    for each ticker: current 25Δ values (front/second month), rolling skew history
  Term Structure tab:
    for each ticker: ATM IV line chart + classification label
  Carry tab:
    for each ticker: IV30 / RV20 / VRP current + rolling VRP history
  Flow Context tab:
    [header: "Microstructure / Execution Context — model-based, not market prices"]
    for each ticker: plot_strike_gex, plot_gamma_profile
[Methodology expander — unchanged]
```

### Lines that change or disappear:
- Lines 178–254 (`render_section()` inner expander and sub-tabs): **replace** with 5-tab top-level structure
- The `render_section()` function call at line 306: **replace** with module tab rendering
- `plot_skew_term_structure` import at line 14: **keep** (still used in Skew tab as secondary view)

### Lines that stay unchanged:
- Lines 30–47: password check
- Lines 49–83: CSS
- Lines 87–101: `_derive_observations()`
- Lines 104–113: `fetch_ticker()`, `_load_history_cached()` cache functions
- Lines 115–151: `render_regime_card()`
- Lines 154–167: `render_section()` regime card loop (refactor to `render_regime_cards()`)
- Lines 259–307: boot, sidebar, ticker fetch
- Lines 309–373: methodology expander

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tab navigation | Custom session-state tab toggle | `st.tabs()` | Built-in, zero state management needed |
| Rolling history charts | Custom matplotlib | Plotly `go.Scatter` — already established pattern | ZGL history chart is the reference implementation |
| Metric display with label | Custom HTML cards | `st.metric()` for current values | Clean, no unsafe HTML needed for scalar display |
| Side-by-side chart columns | Manual HTML layout | `st.columns(n)` | Already used throughout codebase |
| Grouped bar chart for IV30 vs RV20 | Custom | `go.Bar` with two traces | Already used in `plot_strike_gex` |

---

## Common Pitfalls

### Pitfall 1: Unit inconsistency in Carry tab
**What goes wrong:** Displaying `rv20` and `vrp` as raw values (decimal fractions like 0.158, 0.022) instead of converting to percentage/pp (15.8%, 2.2pp).
**Why it happens:** `iv30` in `summary` is in percentage units (18.0) but `rv20` and `vrp` from `compute_ticker()` are decimal fractions. Mixed display makes all three look wrong.
**How to avoid:** Explicitly multiply `rv20 * 100` and `vrp * 100` at the render layer. Verify by checking: IV30 ~18%, RV20 ~15-16%, VRP ~2-3pp.
**Warning signs:** VRP reads as ~0.02 or IV30 reads as ~0.18 — unit mismatch.

### Pitfall 2: Rendering skew history from wrong column
**What goes wrong:** Using `front_skew` column from parquet as "25Δ put-call skew" history when it actually represents IV(25Δ put) − IV(50Δ ATM call) from the legacy `compute_skew()`.
**Why it happens:** Two skew conventions coexist: old `compute_skew()` uses 50Δ call; new `compute_skew_25d()` uses 25Δ call. The parquet column `front_skew` records the old convention.
**How to avoid:** Label the rolling history chart accurately: "Skew (25Δ put − 50Δ call) — 30 sessions" or add a note that the convention predates Phase 6. Do NOT label it "25Δ put-call skew" if it's actually the 50Δ call convention. [See Assumptions Log A1]
**Warning signs:** Chart title says "25Δ put-call skew" but values match the old `front_skew` column.

### Pitfall 3: GEX metrics leaking outside Flow Context tab
**What goes wrong:** Net GEX / γ-flip / call wall remain visible outside the Flow Context tab (e.g., in a regime card that's rendered above all tabs, or as an annotation on the vol surface).
**Why it happens:** The regime cards currently show "Net GEX", "γ-flip", "Skew 25Δ", "IV30" — these are rendered outside the tab structure.
**How to avoid:** The regime cards are intentionally in the header row (always visible) — this is acceptable per Phase 7 success criteria (Flow Context tab contains GEX, cards are a summary widget). Do NOT add GEX charts or GEX-derived annotations to Surface, Skew, Term Structure, or Carry tabs.

### Pitfall 4: Classification label as editorial language
**What goes wrong:** Adding interpretive text next to term structure classification — e.g., "inverted: protective positioning building" or "normal: calm market conditions".
**Why it happens:** Natural impulse to make the metric "actionable" for the PM.
**How to avoid:** Classification is a descriptor only. Show "Term structure: inverted" and let the PM draw conclusions. No deterministic language anywhere.

### Pitfall 5: Cold-start crash on None values
**What goes wrong:** `rv20 * 100` raises TypeError when `rv20 is None` (first 20 sessions before history accumulates).
**Why it happens:** Cold-start guard in `compute_rv20()` returns None when insufficient history.
**How to avoid:** Pattern from current streamlit_app.py:
```python
rv20 = data.get("rv20")
rv20_pct = rv20 * 100 if rv20 is not None else None
```
Then show `st.caption("Not yet available — accumulates after 20 daily runs.")` when None.

### Pitfall 6: Vol surface labels/symmetry (deferred from Phase 6 UAT)
**What goes wrong:** Phase 6 UAT noted a cosmetic issue with vol surface axis labels/symmetry (deferred to Phase 7). The y-axis labels show K/S values from PLOT_KS_ANCHORS but may not be symmetric or well-spaced for all tickers.
**Why it happens:** PLOT_KS_ANCHORS = (0.80...1.20) are fixed; IWM's moneyness band may differ from SPY's.
**How to avoid:** Review the rendered surface for IWM specifically during Phase 7 human UAT. The fix, if needed, is to adjust `PLOT_KS_ANCHORS` in `config.py` or make them dynamic based on `SURFACE_MONEYNESS_BAND`.

---

## Code Examples

### Carry tab — unit-safe value extraction
```python
# Source: [VERIFIED: compute.py return dict structure + vol_metrics.py return conventions]
def _carry_values(data: dict) -> tuple[float | None, float | None, float | None]:
    """Return (iv30_pct, rv20_pct, vrp_pp) all in display units (percent / vol points)."""
    summary = data.get("summary", {})
    iv30_pct = summary.get("iv30")                    # already percent
    rv20 = data.get("rv20")
    vrp = data.get("vrp")
    rv20_pct = float(rv20 * 100) if rv20 is not None else None
    vrp_pp = float(vrp * 100) if vrp is not None else None
    return iv30_pct, rv20_pct, vrp_pp
```

### Flow Context tab header
```python
# Source: ROADMAP.md — locked header text
st.markdown(
    "### Microstructure / Execution Context — model-based, not market prices",
    unsafe_allow_html=False,
)
st.caption(
    "GEX assumes dealers are net short all options (Garleanu, Pedersen & Poteshman 2009). "
    "Sign and order of magnitude are informative; absolute levels are vendor-dependent."
)
```

### Term structure chart — minimal defensible implementation
```python
# Source: [ASSUMED — pattern follows plot_skew_term_structure style in analytics.py]
def plot_term_structure(ts: dict, ticker: str) -> go.Figure:
    points = ts.get("points", [])
    classification = ts.get("classification", "normal")
    if not points:
        fig = go.Figure()
        fig.update_layout(template="plotly_dark",
                          title=f"ATM IV Term Structure — {ticker}: no data",
                          height=300, margin=dict(t=50, b=40, l=65, r=20))
        return fig
    x = [p["dte"] for p in points]
    y = [p["atm_iv"] for p in points]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=y, mode="lines+markers",
        line=dict(color="#60a5fa", width=2), marker=dict(size=6),
        hovertemplate="DTE: %{x:.0f}<br>ATM IV: %{y:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        template="plotly_dark",
        title=dict(text=f"ATM IV Term Structure — {ticker}  ·  {classification}", font_size=13),
        xaxis_title="DTE", yaxis_title="ATM IV (%)", yaxis_ticksuffix="%",
        height=300, margin=dict(t=50, b=40, l=65, r=20),
    )
    return fig
```

### Carry VRP chart — grouped bar + spread line
```python
# Source: [ASSUMED — Plotly grouped bar pattern, no existing reference in codebase]
def plot_carry_vrp(iv30_pct: float | None, rv20_pct: float | None,
                   vrp_pp: float | None, ticker: str) -> go.Figure:
    fig = go.Figure()
    labels = ["IV30", "RV20"]
    values = [iv30_pct or 0, rv20_pct or 0]
    colors = ["#f59e0b", "#60a5fa"]
    fig.add_trace(go.Bar(
        x=labels, y=values, marker_color=colors, width=0.5,
        hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
    ))
    vrp_label = f"VRP: {vrp_pp:+.1f}pp" if vrp_pp is not None else "VRP: n/a (cold start)"
    fig.update_layout(
        template="plotly_dark",
        title=dict(text=f"Vol Carry / VRP — {ticker}  ·  {vrp_label}", font_size=13),
        yaxis_title="Vol (%)", yaxis_ticksuffix="%",
        height=280, margin=dict(t=50, b=40, l=65, r=20),
        showlegend=False,
    )
    return fig
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Per-ticker expanders as primary nav | 5-module top-level tabs | Phase 7 (now) | PM sees all tickers per diagnostic vs. drilling into each ticker |
| GEX as primary diagnostic | GEX as "Flow Context" | Phase 7 (now) | Observable prices (IV surface, skew, VRP) lead |
| Skew = 25Δ put − 50Δ ATM call | Skew = 25Δ put − 25Δ call | Phase 6 (computation); Phase 7 (display) | More symmetric convention; historic parquet still uses old convention |
| No VRP display | VRP = IV30 − RV20 displayed in Carry tab | Phase 7 (now) | Answers "is vol carry attractive?" directly |

**Deprecated/outdated:**
- Per-ticker expanders with sub-tabs (Strikes / Vol / History): replaced by module tabs. GEX content survives in Flow Context; History charts are distributed into their respective module tabs.
- `render_section()` function: will be refactored or split — the regime card rendering loop is kept, the expander loop is removed.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Rolling skew history from `front_skew` parquet column is acceptable to display as skew history even though it uses 25Δ put − 50Δ ATM call convention, not symmetric 25Δ convention | Pitfall 2, Pattern 3 | Minor label inaccuracy — history labeled correctly mitigates this |
| A2 | Tickers displayed stacked vertically in Surface tab is the right layout (vs. 3 columns) | Pattern 1 | Cosmetic — 3D surface would be cramped in 1/3 width |
| A3 | `st.tabs()` API is available in the installed Streamlit version | Standard Stack | Low risk — st.tabs() available since Streamlit 1.x; app already uses st.tabs() inside expanders |
| A4 | `plot_skew_term_structure()` (existing function) can serve as a secondary "skew across expirations" view in Skew tab | Existing Chart Functions table | Low risk — function exists and works; just needs correct placement |
| A5 | COV-01/05 test coverage requirements are out of scope for Phase 7 per ROADMAP.md v3.2 reframe | Phase Requirements section | Medium risk if wrong — planner needs to check with project owner |

---

## Open Questions

1. **COV-01/05 scope disambiguation**
   - What we know: REQUIREMENTS.md traceability maps COV-01/05 to Phase 7. ROADMAP.md moves them to Backlog 999.2.
   - What's unclear: Is the planner expected to write COV-01/05 tests in Phase 7 plans?
   - Recommendation: Follow ROADMAP.md Phase 7 success criteria (5 rendering outcomes). COV-01/05 are deferred. If the project owner wants them in Phase 7, this must be explicitly confirmed — they are a distinct workstream from rendering.

2. **Layout decision: per-module or per-ticker?**
   - What we know: ROADMAP says "5-module tab structure." This implies module-first navigation (top tab = module, then all tickers visible in that module).
   - What's unclear: Should each module tab show all 3 tickers stacked, or should there be a ticker selector within each tab?
   - Recommendation: All 3 tickers stacked in each module tab, with ticker as a section header. Consistent with the existing regime cards approach. Avoids adding state management.

3. **Whether to add a basic smoke test for new chart functions**
   - What we know: 60 tests pass. `test_analytics_charts.py` does not yet exist (COV-05 would create it, but that's deferred).
   - What's unclear: Phase 7 adds 3 new chart functions. Should the phase include basic smoke tests?
   - Recommendation: Yes — add a minimal test file `test_analytics_charts_p7.py` covering the 3 new functions return a `go.Figure` without error given minimal valid input. This is fast (<30s) and prevents silent regressions. It is NOT the full COV-05 scope.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 7 has no new external dependencies. All libraries (Streamlit, Plotly, pandas) are already installed and have been verified working throughout Phases 1–6. No new tools required.

---

## Sources

### Primary (HIGH confidence — verified against live codebase)

- `gex/compute.py:33-98` — `compute_ticker()` full return dict structure including all Phase 6 additions [VERIFIED]
- `gex/vol_metrics.py:1-189` — all 4 pure functions, return types, None conventions [VERIFIED]
- `gex/analytics.py:1-309` — all existing chart functions, signatures, existing `plot_skew_term_structure` [VERIFIED]
- `streamlit_app.py:1-373` — full current layout, `render_regime_card()`, `render_section()`, tab sub-structure, history charts at lines 228-254 [VERIFIED]
- `gex/validation.py:30-35` — `_FLOAT_COLS` confirms `rv20` and `vrp` are in parquet schema [VERIFIED]
- `gex/config.py:84-89` — SKEW_PUT_DELTA, SKEW_CALL_DELTA, HISTORY_DAYS constants [VERIFIED]
- `.planning/phases/06-computation-engine/06-VERIFICATION.md` — Phase 6 completion confirmed, 60/60 tests, all keys wired [VERIFIED]
- `.planning/ROADMAP.md` — Phase 7 success criteria (5 rendering outcomes), COV-01/05 in Backlog 999.2 [VERIFIED]
- `.planning/REQUIREMENTS.md` — COV-01/05 traceability maps to "Phase 7" (mismatch with ROADMAP noted) [VERIFIED]
- `.planning/config.json` — `nyquist_validation: false` confirmed [VERIFIED]

### Secondary (MEDIUM confidence)

- Phase 6 CONTEXT.md deferred items — explicit list of what Phase 7 must render [VERIFIED against live CONTEXT.md]

---

## Metadata

**Confidence breakdown:**
- compute_ticker() return dict: HIGH — verified against live source
- Existing chart function signatures: HIGH — verified against live analytics.py
- Current streamlit_app.py layout: HIGH — full file read
- Phase 7 new chart function implementations: MEDIUM — structure clear from existing patterns, exact implementation is Claude's discretion
- COV-01/05 scope: MEDIUM — mismatch between REQUIREMENTS.md and ROADMAP.md; ROADMAP is authoritative but project owner should confirm

**Research date:** 2026-05-26
**Valid until:** Stable — no external dependencies; valid until streamlit_app.py or analytics.py are modified

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
