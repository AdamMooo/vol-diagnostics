# Phase 3: Streamlit Dashboard — Research

**Researched:** 2026-05-05
**Domain:** Streamlit 1.x — local single-user quant dashboard over existing GEX pipeline
**Confidence:** HIGH

---

## Summary

Phase 3 wraps the existing GEX pipeline in a Streamlit UI. All data-fetch and computation logic already exists in `gex/`; the dashboard's only job is to call it, cache it, and render outputs. The architecture is a single `streamlit_app.py` at the project root — no new packages beyond `streamlit` itself, no new data paths, no new computation.

The hardest constraint is import isolation: `streamlit_app.py` must never import `gex.emailer` or `gex.run_daily` because those pull in `win32com` which is COM-thread-unsafe from Streamlit's process. The implementation reproduces the computation sequence from `run_daily.process_ticker()` inline (or extracted to a shared helper), stopping short of the email step.

The second constraint is yfinance rate-limiting. On a cold app start with 3 tickers, serial fetching with a 0.3 s inter-ticker sleep avoids 429s. `@st.cache_data(ttl=300)` (5 min) per ticker prevents repeat hits within a session. A sidebar "Refresh" button calls `.clear()` on each cached fetch function then calls `st.rerun()`.

**Primary recommendation:** One file (`streamlit_app.py`), one cached fetch function per ticker (or a single function keyed by ticker string), sidebar for controls, columns for regime cards, `plot_overview()` / `plot_strike_gex()` / `plot_gamma_profile()` reused verbatim via `st.pyplot(fig)`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Data fetch (yfinance chain pull) | streamlit_app.py (cached) | gex/data_loader.py | Cache must live at app layer; data_loader has no cache |
| Greeks + exposure computation | gex/ modules | — | Existing computation pipeline — no changes |
| Regime card rendering | streamlit_app.py | gex/report.py (color constants) | UI rendering belongs in app layer |
| Chart rendering | gex/analytics.py (fig creation) | streamlit_app.py (st.pyplot call) | Figure creation already correct; app just calls st.pyplot |
| vs-yesterday lookup | gex/validation.py | streamlit_app.py (error guard) | load_yesterday() already exists and is safe to call |
| Sidebar controls | streamlit_app.py | — | Pure UI |
| Email pipeline | gex/run_daily.py + gex/emailer.py | — | Must stay separate — never imported by streamlit_app.py |

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DASH-01 | App launches via `streamlit run streamlit_app.py` from project root | Streamlit installed in venv; entry-point pattern is standard |
| DASH-02 | Ticker multi-select sidebar + refresh button clears cache and re-fetches | `st.multiselect` + `st.button` + `fetch_fn.clear()` + `st.rerun()` — all verified |
| DASH-03 | Colored regime cards: regime, net GEX, VEX, delta-flow, vs-yesterday | `st.columns` + inline HTML via `st.markdown(..., unsafe_allow_html=True)` using existing `REGIME_COLOR`/`REGIME_BG` from `gex/report.py` |
| DASH-04 | Cross-asset overview bar chart (reuse `plot_overview()`) | `plot_overview(results)` returns `plt.Figure`; render with `st.pyplot(fig)` |
| DASH-05 | Per-ticker expander with strike GEX, gamma profile, summary table | `st.expander` + `st.pyplot` + `st.dataframe` for summary dict |
| DASH-06 | `import streamlit_app` never transitively imports `gex.emailer` or `gex.run_daily` | Verified: only need `gex.data_loader`, `gex.greeks_engine`, `gex.exposure_engine`, `gex.analytics`, `gex.validation` — emailer and run_daily not in that set |
</phase_requirements>

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| streamlit | 1.57.0 | App framework | Latest stable; pip registry confirmed |
| matplotlib | 3.10.x (already installed) | Chart rendering | Already in stack; `st.pyplot(fig)` is the bridge |
| pandas | 2.3.3 (already installed) | DataFrame display | Already in stack |
| pyarrow | already installed | Parquet read for load_yesterday | Already in stack |

**Version verification:** `pip index versions streamlit` returns `1.57.0` as current. [VERIFIED: pip registry]

All other dependencies (numpy, scipy, yfinance, pandas_market_calendars) are already in `requirements.txt` and the venv.

**Streamlit is NOT currently in the venv.** It must be added to `requirements.txt` and installed. [VERIFIED: pip show streamlit returns "not found"]

**Installation:**
```bash
# Add to requirements.txt: streamlit>=1.57,<2.0
pip install streamlit>=1.57,<2.0
```

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `st.pyplot(fig)` | `st.image(fig_to_b64(fig))` | `st.pyplot` is simpler; `fig_to_b64` exists but is meant for email HTML embedding |
| `st.dataframe` for summary table | `st.table` | `st.dataframe` is interactive (sortable); `st.table` is static. Either works for a 1-row summary — `st.dataframe` preferred |
| inline HTML for regime cards | `st.metric` | `st.metric` has no color control; inline HTML with `unsafe_allow_html=True` lets us reuse `REGIME_COLOR`/`REGIME_BG` directly |

---

## Architecture Patterns

### System Architecture Diagram

```
streamlit_app.py
│
├── SIDEBAR
│   ├── st.multiselect (ticker selection, default=["SPY","QQQ","IWM"])
│   └── st.button("Refresh") → fetch_ticker.clear() → st.rerun()
│
├── FETCH LAYER  (@st.cache_data(ttl=300) per ticker)
│   └── fetch_ticker(ticker: str) → dict
│         ├── data_loader.load_chain(ticker)      # yfinance
│         ├── greeks_engine.add_greeks(...)
│         ├── exposure_engine.compute_gex/vex/chex + aggregators
│         ├── analytics.summarise(...)             # returns summary dict
│         └── validation.load_yesterday(ticker)   # parquet lookup
│
├── OVERVIEW SECTION
│   ├── analytics.plot_overview(results)          # existing fn → plt.Figure
│   └── st.pyplot(fig)
│
├── REGIME CARDS (one st.columns(3) row)
│   └── per ticker: colored card with regime, net GEX, VEX, delta-flow, vs-yesterday
│       (st.markdown with unsafe_allow_html=True using REGIME_COLOR/REGIME_BG)
│
└── PER-TICKER EXPANDERS
    └── st.expander(ticker)
        ├── st.pyplot(plot_strike_gex(...))
        ├── st.pyplot(plot_gamma_profile(...))
        └── st.dataframe(summary_as_df)    # net GEX, VEX, CHEX, ZGL, call wall, put wall
```

### Recommended Project Structure

```
options-quant/
├── streamlit_app.py          # NEW — single-file Streamlit entry point
├── gex/
│   ├── data_loader.py        # unchanged
│   ├── greeks_engine.py      # unchanged
│   ├── exposure_engine.py    # unchanged
│   ├── analytics.py          # unchanged
│   ├── validation.py         # unchanged
│   ├── report.py             # REGIME_COLOR/REGIME_BG imported by streamlit_app
│   ├── run_daily.py          # NEVER imported by streamlit_app
│   └── emailer.py            # NEVER imported by streamlit_app
└── requirements.txt          # add streamlit>=1.57,<2.0
```

### Pattern 1: Per-ticker cache with TTL

```python
# Source: docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_data
import time
import streamlit as st

@st.cache_data(ttl=300, show_spinner=False)
def fetch_ticker(ticker: str) -> dict:
    """Returns dict with keys: summary, s_df, v_df, c_df, p_df, spot"""
    from gex.data_loader import load_chain
    from gex.greeks_engine import add_greeks
    from gex.exposure_engine import (
        compute_gex, strike_gex, gamma_profile,
        compute_vex, compute_chex, strike_vex, strike_chex,
    )
    from gex.analytics import summarise
    from gex.validation import load_yesterday, _classify_vs_yesterday

    snapshot = load_chain(ticker)
    df = add_greeks(snapshot.chains, spot=snapshot.spot, today=snapshot.as_of)
    df = compute_gex(df, spot=snapshot.spot)
    df = compute_vex(df, spot=snapshot.spot)
    df = compute_chex(df, spot=snapshot.spot)
    s_df = strike_gex(df)
    v_df = strike_vex(df)
    c_df = strike_chex(df)
    p_df = gamma_profile(df, spot=snapshot.spot)

    net_vex = float(v_df["vex"].sum())
    net_chex = float(c_df["chex"].sum())
    net_gex_scalar = float(s_df["gex"].sum())
    delta_hedge_flow = net_gex_scalar / (snapshot.spot * 0.01)

    summary = summarise(s_df, p_df, spot=snapshot.spot,
                        net_vex=net_vex, net_chex=net_chex,
                        delta_hedge_flow=delta_hedge_flow)
    summary["ticker"] = ticker

    prior = load_yesterday(ticker)
    summary["vs_yesterday"] = (
        _classify_vs_yesterday(summary["net_gex"], summary["gamma_regime"], prior)
        if prior is not None else None
    )

    return {"summary": summary, "s_df": s_df, "p_df": p_df,
            "v_df": v_df, "c_df": c_df, "spot": snapshot.spot}
```

**Key:** The function signature takes only `ticker: str` — this makes cache keying simple and per-ticker cache clearing straightforward.

### Pattern 2: Serial fetch with rate-limit guard

```python
# Prevents yfinance 429 on cold load
TICKERS = ["SPY", "QQQ", "IWM"]

selected = st.sidebar.multiselect("Tickers", TICKERS, default=TICKERS)

results = []
for i, ticker in enumerate(selected):
    if i > 0:
        time.sleep(0.3)   # inter-ticker delay
    with st.spinner(f"Loading {ticker}..."):
        try:
            data = fetch_ticker(ticker)
            results.append(data)
        except Exception as exc:
            st.warning(f"{ticker}: {exc}")
```

### Pattern 3: Refresh button clears cache

```python
# Source: docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_data#invalidating-the-cache
if st.sidebar.button("Refresh"):
    fetch_ticker.clear()   # clears all per-ticker cache entries
    st.rerun()
```

Alternative: `fetch_ticker.clear(ticker)` to clear only selected tickers. Using `.clear()` (no args) is simpler and correct — TTL=300 prevents stale data anyway.

### Pattern 4: Regime card with color

```python
# Reuse REGIME_COLOR and REGIME_BG from gex.report
from gex.report import REGIME_COLOR, REGIME_BG

def render_regime_card(col, summary: dict) -> None:
    ticker = summary["ticker"]
    regime = summary.get("gamma_regime", "neutral")
    color  = REGIME_COLOR.get(regime, "#999")
    bg     = REGIME_BG.get(regime, "#eee")
    net_gex_b = summary.get("net_gex", 0) / 1e9
    net_vex_b = (summary.get("net_vex") or 0) / 1e9
    df_val    = summary.get("delta_hedge_flow")
    df_str    = f"${abs(df_val)/1e9:.1f}B/1%" if df_val else "—"
    vs_yest   = summary.get("vs_yesterday") or "—"

    col.markdown(f"""
<div style="background:{bg};border-left:4px solid {color};
            border-radius:6px;padding:12px 16px;margin-bottom:8px;">
  <div style="font-weight:bold;font-size:15px;color:{color};">{ticker}</div>
  <div style="font-size:12px;color:{color};font-weight:600;
              text-transform:uppercase;">{regime}</div>
  <div style="font-size:13px;margin-top:6px;">
    GEX: <b>{net_gex_b:+.2f}B</b><br>
    VEX: <b>{net_vex_b:+.2f}B</b><br>
    &Delta;-flow: <b>{df_str}</b><br>
    vs-Yesterday: <b>{vs_yest}</b>
  </div>
</div>
""", unsafe_allow_html=True)
```

### Pattern 5: Per-ticker expander

```python
# Source: docs.streamlit.io/develop/api-reference/layout/st.expander
import matplotlib
matplotlib.use("Agg")   # set at module top — same as run_daily.py

for data in results:
    s = data["summary"]
    ticker = s["ticker"]
    with st.expander(f"{ticker} — detail", expanded=False):
        col_l, col_r = st.columns(2)
        with col_l:
            fig = plot_strike_gex(data["s_df"], data["spot"], ticker, s)
            st.pyplot(fig)
            plt.close(fig)
        with col_r:
            fig = plot_gamma_profile(data["p_df"], data["spot"], ticker, s)
            st.pyplot(fig)
            plt.close(fig)

        # Summary table — one row, formatted
        summary_df = pd.DataFrame([{
            "Net GEX":    f"{s['net_gex']/1e9:+.2f}B",
            "VEX":        f"{(s['net_vex'] or 0)/1e9:+.2f}B",
            "CHEX":       f"{(s['net_chex'] or 0)/1e9:+.2f}B",
            "Zero-Gamma": f"{s['zero_gamma_level']:.2f}" if s['zero_gamma_level'] else "—",
            "Call Wall":  f"{s['call_wall']:.0f}" if s['call_wall'] else "—",
            "Put Wall":   f"{s['put_wall']:.0f}" if s['put_wall'] else "—",
        }])
        st.dataframe(summary_df, hide_index=True)
```

### Anti-Patterns to Avoid

- **Importing `gex.run_daily` or `gex.emailer` anywhere in `streamlit_app.py`:** These pull win32com at import time, which crashes in Streamlit's thread model. The computation sequence from `process_ticker()` must be replicated in `fetch_ticker()` without calling those modules.
- **Using global matplotlib figure (no `fig` arg to `st.pyplot`):** Deprecated. Always pass the Figure object: `st.pyplot(fig)`. Failure to close figures with `plt.close(fig)` leaks memory across reruns.
- **Calling `st.cache_data.clear()` (global) in the refresh path:** This nukes caches for all functions. Use `fetch_ticker.clear()` to target only the fetch cache.
- **Blocking serial fetch without progress indication:** With 3 tickers × ~2 s each, the UI appears frozen. Use `st.spinner(f"Loading {ticker}...")` inside the loop.
- **`time.sleep(0.3)` before the first ticker:** Only sleep between tickers (`if i > 0`). Sleeping before the first fetch adds unnecessary latency.
- **Setting `matplotlib.use("Agg")` after importing `matplotlib.pyplot`:** Must be called before the first `pyplot` import. Put it at the top of `streamlit_app.py`, same as `run_daily.py`.
- **Nesting columns more than one level:** Streamlit docs warn against it. Regime cards in columns, charts in columns inside an expander — but those two column contexts don't nest inside each other, so the layout is safe.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Chart display | Custom base64 embedding | `st.pyplot(fig)` | `fig_to_b64` is for email HTML; Streamlit has native pyplot support |
| Color-coded regime display | Custom HTML component | `st.markdown(..., unsafe_allow_html=True)` + existing `REGIME_COLOR`/`REGIME_BG` | The constants already exist in `gex/report.py`; reuse |
| Data table | Custom HTML table | `st.dataframe` | Built-in, interactive, no extra work |
| Cache invalidation | Custom session state flag | `fetch_ticker.clear()` + `st.rerun()` | Streamlit's built-in cache invalidation API |

---

## Common Pitfalls

### Pitfall 1: win32com Import Bleed

**What goes wrong:** If `streamlit_app.py` imports anything that transitively imports `gex.emailer`, the app crashes on startup with a COM threading error or `ImportError` on machines without pywin32 in the right context.

**Why it happens:** `gex.run_daily` imports `from gex import emailer` at module level. Any import of `run_daily` — even indirect — triggers this.

**How to avoid:** `streamlit_app.py` imports only: `gex.data_loader`, `gex.greeks_engine`, `gex.exposure_engine`, `gex.analytics`, `gex.validation`, `gex.report`. Verify with: `python -c "import streamlit_app"` from a shell where you can confirm no win32com error. DASH-06 success criterion is exactly this check.

**Warning signs:** `ImportError: No module named 'win32com'` or `pywintypes.error` on `streamlit run`.

### Pitfall 2: yfinance 429 on Cold Load

**What goes wrong:** Fetching all 3 tickers concurrently (or in rapid succession) triggers HTTP 429 rate-limit from Yahoo Finance.

**Why it happens:** yfinance does not rate-limit itself; 3 full chain fetches back-to-back hit Yahoo's undocumented rate limit.

**How to avoid:** Serial fetch with `time.sleep(0.3)` between tickers. `@st.cache_data(ttl=300)` ensures warm loads skip yfinance entirely.

**Warning signs:** `yfinance` raises an exception with 429 status or returns empty DataFrames.

### Pitfall 3: matplotlib Figure Leak Across Reruns

**What goes wrong:** Memory grows each time the user triggers a rerun because figures are created but never closed.

**Why it happens:** `plt.close(fig)` is not called after `st.pyplot(fig)`.

**How to avoid:** Always `plt.close(fig)` immediately after `st.pyplot(fig)`. Streamlit has already rendered the PNG before the close call.

**Warning signs:** Browser tab slows down over multiple refreshes; `matplotlib` emits "too many open figures" warning.

### Pitfall 4: matplotlib Backend Not Set to Agg

**What goes wrong:** On Windows without a display, matplotlib may attempt to use an interactive backend (TkAgg, Qt5Agg), which either errors or opens a GUI window.

**Why it happens:** `matplotlib.use("Agg")` must be called before the first `import matplotlib.pyplot`.

**How to avoid:** First two lines of `streamlit_app.py` after `from __future__ import annotations`:
```python
import matplotlib
matplotlib.use("Agg")
```
This mirrors `run_daily.py` line 17-18.

### Pitfall 5: Cache Key Includes Mutable Default

**What goes wrong:** If `fetch_ticker` signature changes to include a mutable default (e.g., a list), Streamlit's cache hashing may behave unexpectedly.

**Why it happens:** `st.cache_data` hashes all function arguments. Mutable defaults are hashed at definition time.

**How to avoid:** Keep `fetch_ticker(ticker: str)` with only the ticker string as argument. Ticker string is trivially hashable.

---

## Code Examples

### Minimal streamlit_app.py skeleton

```python
# Source: verified against Streamlit 1.57.0 docs + existing gex/ module signatures
from __future__ import annotations

import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from gex.data_loader import load_chain
from gex.greeks_engine import add_greeks
from gex.exposure_engine import (
    compute_gex, strike_gex, gamma_profile,
    compute_vex, compute_chex, strike_vex, strike_chex,
)
from gex.analytics import summarise, plot_overview, plot_strike_gex, plot_gamma_profile
from gex.validation import load_yesterday, _classify_vs_yesterday
from gex.report import REGIME_COLOR, REGIME_BG

TICKERS = ["SPY", "QQQ", "IWM"]

st.set_page_config(page_title="GEX Dashboard", layout="wide")

@st.cache_data(ttl=300, show_spinner=False)
def fetch_ticker(ticker: str) -> dict:
    snapshot = load_chain(ticker)
    df = add_greeks(snapshot.chains, spot=snapshot.spot, today=snapshot.as_of)
    df = compute_gex(df, spot=snapshot.spot)
    df = compute_vex(df, spot=snapshot.spot)
    df = compute_chex(df, spot=snapshot.spot)
    s_df = strike_gex(df)
    v_df = strike_vex(df)
    c_df = strike_chex(df)
    p_df = gamma_profile(df, spot=snapshot.spot)
    net_vex  = float(v_df["vex"].sum())
    net_chex = float(c_df["chex"].sum())
    net_gex  = float(s_df["gex"].sum())
    dhf = net_gex / (snapshot.spot * 0.01)
    summary = summarise(s_df, p_df, spot=snapshot.spot,
                        net_vex=net_vex, net_chex=net_chex, delta_hedge_flow=dhf)
    summary["ticker"] = ticker
    prior = load_yesterday(ticker)
    summary["vs_yesterday"] = (
        _classify_vs_yesterday(summary["net_gex"], summary["gamma_regime"], prior)
        if prior is not None else None
    )
    return {"summary": summary, "s_df": s_df, "p_df": p_df, "spot": snapshot.spot}

# Sidebar
with st.sidebar:
    selected = st.multiselect("Tickers", TICKERS, default=TICKERS)
    if st.button("Refresh"):
        fetch_ticker.clear()
        st.rerun()

# Fetch (serial, rate-limit safe)
all_data = []
for i, ticker in enumerate(selected):
    if i > 0:
        time.sleep(0.3)
    with st.spinner(f"Loading {ticker}..."):
        try:
            all_data.append(fetch_ticker(ticker))
        except Exception as exc:
            st.warning(f"{ticker} failed: {exc}")

# Overview chart
results = [d["summary"] for d in all_data]
if results:
    fig = plot_overview(results)
    st.pyplot(fig)
    plt.close(fig)

# Regime cards
cols = st.columns(len(all_data)) if all_data else []
for col, data in zip(cols, all_data):
    s = data["summary"]
    # ... render card (see Pattern 4)

# Per-ticker expanders
for data in all_data:
    s = data["summary"]
    with st.expander(s["ticker"], expanded=False):
        # ... charts + table (see Pattern 5)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@st.cache` (deprecated) | `@st.cache_data` | Streamlit 1.18 (2023) | Use `cache_data` — `cache` raises DeprecationWarning in 1.57 |
| `st.pyplot()` with no fig arg | `st.pyplot(fig)` | Streamlit 1.x | Always pass the fig; global figure is deprecated |
| `use_container_width=True` | `width="stretch"` (default) | Streamlit 1.45 | Both work in 1.57; `width` param is the newer API |

**Deprecated/outdated:**
- `@st.cache`: Replaced by `@st.cache_data` (for serializable data) and `@st.cache_resource` (for connections/models). Using old `@st.cache` will raise `StreamlitDeprecationWarning`.
- `st.pyplot()` with no argument: Renders global matplotlib figure, deprecated. Always pass `fig` explicitly.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `time.sleep(0.3)` between tickers is sufficient to avoid 429 | Common Pitfalls / Pattern 2 | yfinance 429 on cold load; mitigation: increase sleep or add retry logic | [ASSUMED] — no official yfinance rate-limit documentation |
| A2 | `_classify_vs_yesterday` is safe to import directly in streamlit_app.py (it is a private function) | Pattern 1 | Naming convention only; function is already imported in run_daily.py — low risk |

---

## Open Questions

1. **plot_overview() imports from gex.report internally**
   - `analytics.plot_overview()` has `from gex.report import TICKER_LABEL, REGIME_COLOR` inside the function body (line 148 of analytics.py). This is a local import, so `gex.report` is only loaded when `plot_overview()` is called — not at `import gex.analytics` time. `gex.report` does NOT import `gex.emailer`, so this is safe.
   - No action needed — confirmed by reading analytics.py and report.py.

2. **`vs_yesterday` key in summary dict**
   - `process_ticker()` in `run_daily.py` adds `summary["vs_yesterday"]` after the `summarise()` call. `summarise()` itself does NOT add this key. `streamlit_app.py`'s `fetch_ticker()` must also add it after calling `summarise()` — the Pattern 1 skeleton above does this correctly.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python venv | All | Yes | active | — |
| pandas | Data | Yes | 2.3.3 | — |
| numpy | Computation | Yes | 2.4.4 | — |
| matplotlib | Charts | Yes | 3.10.9 | — |
| yfinance | Data fetch | Yes | 1.3.0 | — |
| pyarrow | Parquet read | Yes | installed | — |
| pandas_market_calendars | load_yesterday | Yes | installed | — |
| streamlit | App framework | **NOT INSTALLED** | — | Must install before app can run |

**Missing dependencies with no fallback:**
- `streamlit` — must be added to `requirements.txt` and installed. Blocks DASH-01.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (>=8.0, already in requirements.txt) |
| Config file | none — pytest auto-discovers `gex/tests/` |
| Quick run command | `python -m pytest gex/tests/ -q` |
| Full suite command | `python -m pytest gex/tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DASH-01 | App starts without import error | smoke | `python -c "import streamlit_app"` | ❌ Wave 0 |
| DASH-02 | Refresh clears cache (unit-level: clear() exists on cached fn) | unit | `python -m pytest gex/tests/test_streamlit_app.py::test_fetch_ticker_cache_clear -x` | ❌ Wave 0 |
| DASH-03 | Regime card renders correct color/values | manual | manual inspection | — |
| DASH-04 | plot_overview fig returned and closed | unit | `python -m pytest gex/tests/test_streamlit_app.py::test_plot_overview_renders -x` | ❌ Wave 0 |
| DASH-05 | Per-ticker expander renders (integration) | manual | manual inspection | — |
| DASH-06 | No emailer/run_daily import | smoke | `python -c "import streamlit_app"` (same as DASH-01 — if it passes without win32com error, DASH-06 passes) | ❌ Wave 0 |

**Note:** DASH-01 and DASH-06 share the same smoke test. If `python -c "import streamlit_app"` succeeds in the venv without a COM error, both pass simultaneously.

### Sampling Rate
- **Per task commit:** `python -m pytest gex/tests/ -q`
- **Per wave merge:** `python -m pytest gex/tests/ -v` + `python -c "import streamlit_app"` smoke
- **Phase gate:** Full suite green + smoke test before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `gex/tests/test_streamlit_app.py` — import smoke + cache clear unit test (DASH-01, DASH-02, DASH-06)
- [ ] `streamlit run streamlit_app.py` manual check (DASH-03, DASH-04, DASH-05 — not automatable without a browser)
- [ ] `pip install streamlit>=1.57,<2.0` + add to `requirements.txt`

---

## Security Domain

Security enforcement not applicable — local single-user tool, no auth, no network exposure, no user input stored. [ASSUMED: confirmed by REQUIREMENTS.md "Out of Scope: Multi-user / remote deploy"] [ASSUMED: no `security_enforcement` key in config — treating as disabled for a local tool with no web exposure]

---

## Sources

### Primary (HIGH confidence)
- `docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_data` — ttl, clear(), show_spinner params [VERIFIED: WebFetch]
- `docs.streamlit.io/develop/api-reference/widgets/st.multiselect` — signature, default param [VERIFIED: WebFetch]
- `docs.streamlit.io/develop/api-reference/layout/st.expander` — signature, with-notation [VERIFIED: WebFetch]
- `docs.streamlit.io/develop/api-reference/charts/st.pyplot` — fig param required, clear_figure [VERIFIED: WebFetch]
- `docs.streamlit.io/develop/api-reference/layout/st.columns` — spec, gap, border [VERIFIED: WebFetch]
- `docs.streamlit.io/develop/api-reference/layout/st.sidebar` — object notation vs with notation [VERIFIED: WebFetch]
- `docs.streamlit.io/develop/api-reference/execution-flow/st.rerun` — scope param [VERIFIED: WebFetch]
- `pip index versions streamlit` — 1.57.0 is current [VERIFIED: pip registry]
- Existing venv: pandas 2.3.3, numpy 2.4.4, matplotlib 3.10.9, yfinance 1.3.0 [VERIFIED: pip show]
- `gex/analytics.py`, `gex/report.py`, `gex/run_daily.py`, `gex/validation.py` — function signatures and import structure [VERIFIED: Read tool]

### Secondary (MEDIUM confidence)
- Streamlit version 1.57.0 changelog — `width` param replacing `use_container_width` in 1.45+ [ASSUMED from docs patterns observed]

### Tertiary (LOW confidence)
- 0.3 s inter-ticker sleep sufficient for yfinance rate limiting [ASSUMED — no official rate limit documentation]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — streamlit 1.57.0 verified via pip registry; all other deps confirmed in venv
- Architecture: HIGH — all function signatures verified from source files; Streamlit API verified from official docs
- Pitfalls: HIGH for import isolation and Agg backend (confirmed from codebase); MEDIUM for yfinance rate limit specifics

**Research date:** 2026-05-05
**Valid until:** 2026-06-05 (Streamlit releases frequently; recheck before upgrade)

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/03-streamlit-dashboard/03-01-PLAN|03-01-PLAN]]
- [[_planning/gamma-omm/phases/03-streamlit-dashboard/03-01-SUMMARY|03-01-SUMMARY]]
- [[_planning/gamma-omm/phases/03-streamlit-dashboard/03-02-PLAN|03-02-PLAN]]
- [[_planning/gamma-omm/phases/03-streamlit-dashboard/03-02-SUMMARY|03-02-SUMMARY]]
- [[_planning/gamma-omm/phases/03-streamlit-dashboard/03-HUMAN-UAT|03-HUMAN-UAT]]
- [[_planning/gamma-omm/phases/03-streamlit-dashboard/03-PATTERNS|03-PATTERNS]]
- [[_planning/gamma-omm/phases/03-streamlit-dashboard/03-REVIEW|03-REVIEW]]
- [[_planning/gamma-omm/phases/03-streamlit-dashboard/03-VERIFICATION|03-VERIFICATION]]

<!-- LINKS:END -->
