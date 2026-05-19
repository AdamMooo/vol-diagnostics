# Phase 4: Historical Tab - Pattern Map

**Mapped:** 2026-05-06
**Files analyzed:** 3 (2 modified, 1 new function within existing file)
**Analogs found:** 3 / 3

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `streamlit_app.py` (tab wrap + streak kwarg) | component | request-response | `streamlit_app.py` existing functions | self-analog |
| `gex/validation.py` — `load_history()` | utility | file-I/O | `load_yesterday()` in same file | exact |
| `_compute_streak()` in `streamlit_app.py` | utility | transform | `_classify_vs_yesterday()` in `validation.py` | role-match |

## Pattern Assignments

### `gex/validation.py` — `load_history(ticker, days)` (utility, file-I/O)

**Analog:** `load_yesterday()` in the same file (lines 52–71)

**Imports pattern** (lines 13–23 — already present, no new imports needed):
```python
from __future__ import annotations

import datetime
import pathlib

import numpy as np
import pandas as pd
import yfinance as yf

STORE = pathlib.Path(__file__).resolve().parents[1] / "out" / "gex_snapshots.parquet"
```

**Core pattern — follow `load_yesterday()` exactly** (lines 52–71):
```python
def load_yesterday(ticker: str, today: datetime.date | None = None) -> "pd.Series | None":
    if not STORE.exists():
        return None
    try:
        ...
        hist = pd.read_parquet(STORE)
        hist["date"] = pd.to_datetime(hist["date"]).dt.date
        row = hist[(hist["date"] == prior_date) & (hist["ticker"] == ticker)]
        return row.iloc[0] if not row.empty else None
    except Exception:
        return None
```

**`load_history()` implementation contract** (new function, placed directly below `load_yesterday()`):
```python
def load_history(ticker: str, days: int = 30) -> pd.DataFrame:
    if not STORE.exists():
        return pd.DataFrame()
    try:
        hist = pd.read_parquet(STORE)
        hist["date"] = pd.to_datetime(hist["date"]).dt.date
        hist = hist[hist["ticker"] == ticker].sort_values("date", ascending=False)
        return hist.head(days).reset_index(drop=True)
    except Exception:
        return pd.DataFrame()
```

Key differences from `load_yesterday()`:
- Returns a `pd.DataFrame` (not `pd.Series | None`) — empty DataFrame on miss, never None
- Sorts descending by date, takes `head(days)` — most recent N sessions
- No market-calendar dependency — uses row count as proxy for "trading sessions"

**Error handling pattern** (lines 52–71): bare `except Exception: return <empty>` — same as `load_yesterday()`; no logging, no re-raise.

---

### `streamlit_app.py` — `st.tabs()` wrap (component, request-response)

**Analog:** Existing boot / layout block in `streamlit_app.py` (lines 154–211)

**Tab wrap pattern** — the entire block from the section divider comments downward gets indented one level inside `with tabs[0]:`. Pattern for inserting tabs:
```python
# After sidebar block and st.markdown("## GEX Dashboard") header
tabs = st.tabs(["Live", "Historical"])

with tabs[0]:
    # existing content: fetch loop, regime cards, overview, per-ticker detail
    ...

with tabs[1]:
    # Phase 4 Historical content
    ...
```

**Section header pattern** (lines 193, 204, 214 — reuse verbatim):
```python
st.markdown('<div class="sec">Regime Summary</div>', unsafe_allow_html=True)
```

**`st.info()` gate pattern** (lines 169–171 — reuse for ≥20 session gate):
```python
if not selected:
    st.info("Select at least one ticker in the sidebar.")
    st.stop()
```
For the event study gate: `st.info("Insufficient history — need ≥20 sessions.")` — same call, no `st.stop()` (just skip that section, not the whole tab).

**`st.pyplot()` / `plt.close()` pattern** (lines 209–210, 238–242 — mandatory pair):
```python
fig = plot_overview(clean)
st.pyplot(fig)
plt.close(fig)
```
Every new matplotlib figure in Phase 4 must call `plt.close(fig)` immediately after `st.pyplot(fig)`.

**`st.dataframe` pattern** (lines 234):
```python
st.dataframe(summary_df, hide_index=True, use_container_width=True)
```

---

### `streamlit_app.py` — `render_regime_card()` streak kwarg (component, request-response)

**Analog:** Existing `render_regime_card()` (lines 122–149)

**Function signature extension** (lines 122–123):
```python
# Current:
def render_regime_card(col, summary: dict, spot: float | None = None) -> None:

# Extended (backward-compatible):
def render_regime_card(col, summary: dict, spot: float | None = None, streak: int | None = None) -> None:
```

**HTML card pattern** (lines 136–149 — streak row appended to `.rc-grid`):
```python
col.markdown(f"""
<div class="rc" style="background:{bg};border-left-color:{color};">
  <div class="rc-ticker" style="color:{color};">{ticker}</div>
  <div class="rc-regime" style="color:{color};">{regime}</div>
  <div class="rc-grid">
    <span class="rc-k">Spot</span>       <span class="rc-v">{spot_str}</span>
    <span class="rc-k">Net GEX</span>    <span class="rc-v">{net_gex_b:+.2f}B</span>
    <span class="rc-k">VEX</span>        <span class="rc-v">{net_vex_b:+.2f}B</span>
    <span class="rc-k">&Delta;-flow</span><span class="rc-v">{df_str}</span>
    <span class="rc-k">Zero-&gamma;</span><span class="rc-v">{zgl_str}</span>
    {streak_row}
  </div>
  {_vs_badge(vs)}
</div>
""", unsafe_allow_html=True)
```

Streak row is a conditional — compute before the f-string:
```python
streak_row = (
    f'<span class="rc-k">Streak</span><span class="rc-v">{streak} sessions</span>'
    if streak is not None else ""
)
```

Typography must match existing `.rc-k` / `.rc-v` grid classes. "sessions" matches the decision (D-05: trading sessions, not calendar days).

---

### `streamlit_app.py` — `_compute_streak()` (utility, transform)

**Analog:** `_classify_vs_yesterday()` in `validation.py` (lines 74–92) — same role (derives a scalar from history rows), same leading-underscore private convention.

**Pattern:**
```python
def _compute_streak(hist_df: pd.DataFrame, current_regime: str) -> int | None:
    if hist_df.empty:
        return None
    # hist_df is sorted descending by date (most recent first)
    count = 0
    for regime in hist_df["gamma_regime"]:
        if regime == current_regime:
            count += 1
        else:
            break
    return count if count > 0 else None
```

Note: `hist_df` from `load_history()` is sorted descending (most recent row first), so iterating straight gives trailing streak. Return `None` (not `0`) when streak cannot be computed — matches `render_regime_card()` guard `if streak is not None`.

---

### `streamlit_app.py` — `@st.cache_data` for historical load (utility, file-I/O)

**Analog:** `fetch_ticker` cache (lines 117–119):
```python
@st.cache_data(ttl=300, show_spinner=False)
def fetch_ticker(ticker: str) -> dict:
    return compute_ticker(ticker)
```

**Historical cache pattern** (TTL=1800, separate decorator per D-03):
```python
@st.cache_data(ttl=1800, show_spinner=False)
def _load_history_cached(ticker: str, days: int = 30) -> pd.DataFrame:
    from gex.validation import load_history
    return load_history(ticker, days)
```

Keep the import inside the function to avoid circular issues if `validation.py` is extended later. TTL=1800 (30 min) vs TTL=300 (5 min) for live — they are independent caches.

---

### `streamlit_app.py` — Historical tab ZGL trend chart (component, file-I/O)

**Analog:** `plot_overview()` call block (lines 207–211) — same fig/pyplot/close triple.

**Pattern for new matplotlib chart in Phase 4:**
```python
fig, ax = plt.subplots()  # rcParams apply automatically (transparent bg, light text)
ax.plot(hist_df["date"], hist_df["zero_gamma_level"], label="Zero-γ", linewidth=1.5)
ax.plot(hist_df["date"], hist_df["spot"], label="Spot", linewidth=1.2, linestyle="--")
ax.set_title(f"{ticker} — ZGL vs Spot (30 sessions)")
ax.legend()
fig.autofmt_xdate()
st.pyplot(fig)
plt.close(fig)
```

Single axis — both ZGL and spot are price-level values (D-06). `fig.autofmt_xdate()` handles date label rotation.

---

### `streamlit_app.py` — Regime persistence and event study tables (component, transform)

**Analog:** `summary_df` + `st.dataframe` block (lines 225–234).

**Regime persistence table pattern:**
```python
# hist_df from load_history(ticker, days=20)
counts = hist_df["gamma_regime"].value_counts().reset_index()
counts.columns = ["Regime", "Sessions"]
counts["% Days"] = (counts["Sessions"] / counts["Sessions"].sum() * 100).round(1).astype(str) + "%"
st.dataframe(counts, hide_index=True, use_container_width=True)
```

**Event study table pattern** (gated at ≥20 sessions per D-09):
```python
hist_df = _load_history_cached(ticker, days=30)
if len(hist_df) < 20:
    st.info("Insufficient history — need ≥20 sessions.")
else:
    study = (
        hist_df.groupby("gamma_regime")
        .agg(Sessions=("net_gex", "count"), Avg_Net_GEX=("net_gex", "mean"))
        .reset_index()
    )
    study["% Days"] = (study["Sessions"] / study["Sessions"].sum() * 100).round(1).astype(str) + "%"
    study["Avg Net GEX"] = (study["Avg_Net_GEX"] / 1e9).map("{:+.2f}B".format)
    st.dataframe(study[["gamma_regime", "Sessions", "% Days", "Avg Net GEX"]], hide_index=True, use_container_width=True)
```

---

## Shared Patterns

### Cache decorator
**Source:** `streamlit_app.py` lines 117–119
**Apply to:** All data-loading wrappers in `streamlit_app.py`
```python
@st.cache_data(ttl=300, show_spinner=False)   # live
@st.cache_data(ttl=1800, show_spinner=False)  # historical
```

### plt.close(fig) after every st.pyplot(fig)
**Source:** `streamlit_app.py` lines 209–210
**Apply to:** Every new matplotlib figure in Phase 4
```python
st.pyplot(fig)
plt.close(fig)
```
Failure to close leaks memory. No exceptions.

### st.info() for gates (not st.warning / st.error)
**Source:** `streamlit_app.py` line 170; CONTEXT.md D-09
**Apply to:** ≥20-session event study gate, empty-history guards
```python
st.info("Insufficient history — need ≥20 sessions.")
```

### Empty-return sentinel for data functions
**Source:** `validation.py` lines 53–71 (`load_yesterday` returns `None`; `load_history` returns `pd.DataFrame()`)
**Apply to:** `load_history()`, `_compute_streak()`
- Functions that read parquet return empty container (`pd.DataFrame()`, `None`) on any failure — bare `except Exception`.
- Callers guard with `if df.empty` / `if streak is not None`.

### Parquet read pattern
**Source:** `validation.py` lines 66–68
**Apply to:** `load_history()`
```python
hist = pd.read_parquet(STORE)
hist["date"] = pd.to_datetime(hist["date"]).dt.date
```
Always coerce `date` column after read — parquet may store as datetime64.

### Section header HTML
**Source:** `streamlit_app.py` lines 193, 204, 214
**Apply to:** All new sections in Historical tab
```python
st.markdown('<div class="sec">Section Title</div>', unsafe_allow_html=True)
```

## No Analog Found

None — all Phase 4 patterns have direct analogs in the existing codebase.

## Metadata

**Analog search scope:** `streamlit_app.py`, `gex/validation.py`
**Files scanned:** 2 source files (full read)
**Parquet schema confirmed:** `date, ticker, spot, net_gex, gamma_regime, zero_gamma_level, call_wall, put_wall, vanna_exposure` (from `save_snapshot()` lines 27–37)
**Pattern extraction date:** 2026-05-06

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/04-historical-tab/04-01-PLAN|04-01-PLAN]]
- [[_planning/gamma-omm/phases/04-historical-tab/04-01-SUMMARY|04-01-SUMMARY]]
- [[_planning/gamma-omm/phases/04-historical-tab/04-02-PLAN|04-02-PLAN]]
- [[_planning/gamma-omm/phases/04-historical-tab/04-02-SUMMARY|04-02-SUMMARY]]
- [[_planning/gamma-omm/phases/04-historical-tab/04-CONTEXT|04-CONTEXT]]
- [[_planning/gamma-omm/phases/04-historical-tab/04-DISCUSSION-LOG|04-DISCUSSION-LOG]]
- [[_planning/gamma-omm/phases/04-historical-tab/04-REVIEW|04-REVIEW]]
- [[_planning/gamma-omm/phases/04-historical-tab/04-VERIFICATION|04-VERIFICATION]]

<!-- LINKS:END -->
