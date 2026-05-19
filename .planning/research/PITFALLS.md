# Domain Pitfalls — GEX v3.0: Streamlit + Second-Order Greeks

**Domain:** Adding Streamlit dashboard and Vanna/Charm Greeks to a production GEX email system
**Researched:** 2026-05-05
**Scope:** Integration pitfalls specific to this codebase (not generic Streamlit advice)

---

## Quick Reference Table

| # | Pitfall | Severity | Phase | Prevention |
|---|---------|----------|-------|------------|
| 1 | Charm divide-by-T blowup near expiry | **Critical** | 1 (Greeks) | Clamp T to min floor before formula |
| 2 | matplotlib backend conflict (Agg vs Streamlit thread) | **Critical** | 3 (Dashboard) | `matplotlib.use("Agg")` at module top + `plt.close(fig)` always |
| 3 | yfinance 429 on Streamlit cold load (10 tickers) | **High** | 3 (Dashboard) | `@st.cache_data(ttl=300)` per ticker, serial with delay |
| 4 | `@st.cache_data` unhashable args (list of tickers) | **High** | 3 (Dashboard) | Pass `tuple(tickers)`, not list |
| 5 | Parquet schema break when vanna_exposure column added mid-stream | **High** | 2 (VEX) | Read-then-merge pattern; missing columns filled with NaN |
| 6 | win32com COM object in Streamlit process thread | **High** | 3 (Dashboard) | Never import emailer in streamlit_app.py |
| 7 | Vanna sign/scale mismatch vs GEX ($-scaled) | **Medium** | 1 (Greeks) + 2 (VEX) | Unit test: vanna at ATM, 0.20 vol, 30d matches known value |
| 8 | Module-level globals survive Streamlit reruns (stale data) | **Medium** | 3 (Dashboard) | Use `st.session_state` for fetched chain DataFrames |
| 9 | matplotlib figure objects accumulate in Streamlit loop | **Medium** | 3 (Dashboard) | Always `plt.close(fig)` after `st.pyplot(fig)` |
| 10 | Path separators in parquet store break on Windows paths in cache keys | **Low** | 3 (Dashboard) | Use `pathlib.Path.as_posix()` for cache key strings |

---

## Critical Pitfalls

### Pitfall 1: Charm Divide-by-T Blowup Near Expiry

**What goes wrong:**
Charm (∂delta/∂t) in BS contains a `1/T` and `1/sqrt(T)` term. At T → 0 (same-day or next-day expiry — very common in 0DTE SPY chains), the formula returns ±∞ or NaN. Pandas `sum()` on a column with NaN silently propagates NaN into VEX aggregation; with ∞ it corrupts the entire exposure number.

**Why it happens:**
`greeks_engine.py:add_greeks()` already guards against T ≤ 0 with `valid = (T > 0) & ...` for gamma. Charm has the same denominator pattern but is more extreme: the numerator also grows as T → 0 because d1/d2 → ±∞.

The exact Charm formula:
```
charm = -N'(d1) * [2rT - d2*sigma*sqrt(T)] / [2*T*sigma*sqrt(T)]
```
Both `T` and `T*sigma*sqrt(T)` appear in the denominator. At T = 0.001 years (~9 hours), sigma=0.20 → denominator ≈ 6e-5, producing values in the thousands per unit.

**Consequences:**
- VEX sum is meaningless or NaN
- Historical tab comparisons break (NaN rows appear in parquet)
- Chart y-axis range explodes, making all other strikes invisible

**Prevention (Phase 1):**
Apply the same guard pattern already used for gamma, plus a minimum T floor:
```python
T_MIN = 1 / 365  # 1 calendar day — exclude same-day expiry from charm calc
valid = (T > T_MIN) & (iv > 0) & (strike > 0) & (spot > 0)
charm = np.zeros(strike.shape, dtype=float)
# ... only compute for valid[T > T_MIN]
```
This excludes 0DTE and next-morning expiry from charm aggregation. Document in WALKTHROUGH.md that charm figures exclude < 1-day expiry.

**Detection:** A unit test with T=0.0001 (1-hour expiry) should return 0.0, not NaN or inf. Add to Phase 1 test suite.

---

### Pitfall 2: matplotlib Backend Conflict — Agg vs Streamlit Thread

**What goes wrong:**
`run_daily.py` already sets `matplotlib.use("Agg")` at the top. If `streamlit_app.py` imports from `gex.analytics` (which imports `matplotlib.pyplot`), the backend is already set. The problem is not the backend choice — it is that matplotlib is **not thread-safe**. Streamlit runs each session as a separate thread. If two users hit the dashboard simultaneously (or if `st.rerun()` fires mid-render), concurrent `fig, ax = plt.subplots()` calls can race.

**Why it happens:**
The official Streamlit docs state explicitly: "Matplotlib doesn't work well with threads." The fix they recommend is `threading.RLock`. GitHub issue #1227 confirms IndexError/KeyError under concurrent load from shared figure state.

**Consequences:**
- Rare but catastrophic: figures render each other's data (wrong ticker's chart appears)
- More commonly: `IndexError` or blank chart on the second concurrent user

**Prevention (Phase 3):**
Two options, pick one:

Option A (preferred for single-user local tool): Always pass `fig` explicitly to `st.pyplot(fig, clear_figure=True)` rather than relying on `plt.gcf()`. Create figures inside the cached function, not at module level.

Option B (if multi-user ever matters): Wrap all `plt` calls in a module-level RLock:
```python
import threading
_mpl_lock = threading.RLock()
with _mpl_lock:
    fig = plot_strike_gex(...)
    st.pyplot(fig)
    plt.close(fig)
```

For this project (local, single-user), Option A is sufficient. Never use `plt.figure()` at module scope in `streamlit_app.py`.

---

## High Severity Pitfalls

### Pitfall 3: yfinance 429 Rate Limit on Streamlit Cold Load

**What goes wrong:**
`run_daily.py` fetches 10 tickers sequentially with no sleep — acceptable for a once-daily scheduled run. In Streamlit, every page load or refresh triggers a cold cache miss. If a user refreshes twice quickly, or if the `ttl` expires mid-session, all 10 `load_chain()` calls fire in rapid succession. Yahoo Finance enforces rate limits; the community reports hitting 429s after ~950 tickers in a burst (Nov 2024 enforcement tightening).

**Why it happens:**
`@st.cache_data` with a TTL caches per-argument. If `fetch_all_tickers(("SPY","QQQ",...))` is cached as a single call, one miss = 10 simultaneous requests. If cached per-ticker, 10 simultaneous cache misses = 10 simultaneous requests.

**Consequences:**
- Some tickers succeed, some return empty chains — the dashboard shows partial data with no clear error
- The user refreshes, making it worse

**Prevention (Phase 3):**
```python
import time

@st.cache_data(ttl=300)
def fetch_ticker(ticker: str) -> dict:
    return process_ticker(ticker)  # existing function from run_daily.py

def fetch_all(tickers: tuple[str, ...]) -> list[dict]:
    results = []
    for t in tickers:
        results.append(fetch_ticker(t))
        time.sleep(0.3)  # 300ms between calls; 10 tickers = 3s total
    return results
```
Key points:
- Cache per-ticker (not per-list): a single cache miss only re-fetches one ticker
- `time.sleep(0.3)` is enough pacing for yfinance in practice
- On initial load, show `st.spinner("Fetching chains...")` so the user knows 3s is expected
- Never cache the full-list call; that would batch all 10 into a single cache entry

---

### Pitfall 4: `@st.cache_data` Unhashable Argument — List of Tickers

**What goes wrong:**
```python
@st.cache_data
def fetch_all(tickers: list[str]) -> list[dict]:  # WRONG
```
Raises `TypeError: unhashable type: 'list'` at runtime. Streamlit uses the function arguments as cache keys and lists are not hashable.

**Why it happens:**
`@st.cache_data` hashes all arguments to build the cache key. Python lists are mutable and unhashable. This is a silent trap because it only blows up at call time, not at decoration time.

**Prevention (Phase 3):**
Use a tuple constant:
```python
TICKERS = ("SPY", "QQQ", "IWM", "XLF", "EEM", "EFA", "EWJ", "TLT", "HYG", "GLD")
# ...
fetch_all(TICKERS)  # tuple — hashable
```
Or use the underscore-prefix escape hatch (`_tickers`) if dynamic filtering is needed, but that disables cache keying on that argument — risky for a ticker-list that changes.

Also affects DataFrames passed to cached functions: if a function takes a `pd.DataFrame` as an argument, `@st.cache_data` handles DataFrames via content hash (works), but lists-inside-DataFrames (e.g. a column of Python lists) raise `TypeError: unhashable type: 'list'` — seen in Streamlit issue #10957. Check that any DataFrame passed to cached functions has only scalar/numeric/string columns.

---

### Pitfall 5: Parquet Schema Break When Adding vanna_exposure Mid-Stream

**What goes wrong:**
The existing `gex_snapshots.parquet` has columns: `date, ticker, spot, net_gex, gamma_regime, zero_gamma_level, call_wall, put_wall`. Phase 2 adds `vanna_exposure` (and possibly `charm_exposure`). The existing `save_snapshot()` pattern in `validation.py` reads the file, drops today's rows, concatenates a new row, and writes back. If the new row has `vanna_exposure` but old rows don't, `pd.concat()` fills the old rows with NaN — which is correct. But downstream code that does `df["vanna_exposure"].sum()` on history including pre-Phase-2 rows returns NaN unless `skipna=True` is used.

**Why it happens:**
`pd.concat` with columns that only exist in one DataFrame fills the missing side with NaN (correct Parquet behavior; adding nullable columns is a supported schema evolution). The trap is not the write — it is every read-side aggregation thereafter.

**Consequences:**
- Historical tab shows NaN in vanna trend for all pre-v3.0 dates
- `mean()` on regime groups returns NaN if any row is NaN and `skipna` is not explicit

**Prevention (Phase 2):**
1. In `save_snapshot()`, always write all columns explicitly, using `None` for columns not yet computed if called from legacy code path:
```python
row = {
    "date": ...,
    "vanna_exposure": summary.get("vanna_exposure"),  # None if not computed
    ...
}
```
2. On every read, defensively fill missing columns:
```python
df = pd.read_parquet(STORE)
df["vanna_exposure"] = df.get("vanna_exposure", pd.Series(dtype=float))
```
3. All aggregations use explicit `skipna=True`: `df["vanna_exposure"].mean(skipna=True)`.
4. No migration script needed — the NaN-fill approach handles it transparently.

---

### Pitfall 6: win32com COM Object in Streamlit Process Thread

**What goes wrong:**
`gex/emailer.py` uses `win32com.client.Dispatch("Outlook.Application")` to send email. COM objects on Windows are apartment-threaded — the COM object must be used on the same OS thread that created it. Streamlit runs each browser session as a Python thread, not a subprocess. If `streamlit_app.py` ever imports `emailer` (even indirectly via `from gex.run_daily import *`), and a rerun triggers re-execution, the COM client can be initialized on thread A but called on thread B, raising `com_error` or silently doing nothing.

Confirmed by Streamlit issue #6097: win32com API calls work for the first 30 seconds then fail on app update/rerun — exactly the thread-switch timing.

**Consequences:**
- Email pipeline breaks silently (no error visible to the PM desk)
- Worse: if COM is initialized in streamlit_app.py, it may lock the Outlook process

**Prevention (Phase 3):**
Hard rule: `streamlit_app.py` must never import from `gex.emailer` or `gex.run_daily`. The dashboard is read-only — it reads parquet and fetches chains. Email stays in `run_daily.py` only. Enforce this structurally: add a comment at the top of `streamlit_app.py`:
```python
# DO NOT import gex.emailer or gex.run_daily here — COM apartment threading
```
If a "send test email" button is ever requested, implement it as a subprocess call (`subprocess.run(["python", "-m", "gex.run_daily", "--dry-run"])`) so it runs in its own COM apartment.

---

## Medium Severity Pitfalls

### Pitfall 7: Vanna Sign/Scale Mismatch vs GEX

**What goes wrong:**
VEX (Vanna Exposure) is aggregated the same way as GEX: `vanna × OI × 100 × S² × 0.01` (or a variant). If Vanna is computed per-share but GEX uses a different notional scaling, the VEX number is off by a factor of 100 or more — it looks plausible on its own but is wrong in relative terms.

The BS Vanna formula:
```
vanna = -N'(d1) * d2 / (sigma)
```
Note: some sources give Vanna as `-N'(d1) * d2 / (spot * sigma * sqrt(T))` — these are different quantities (sensitivity normalized differently). The correct form for dealer-flow purposes is `∂delta/∂vol`, not `∂delta/∂S ∂vol`.

**Prevention (Phase 1 + 2):**
Write a unit test before `compute_vex()` exists:
```python
# ATM, S=100, K=100, T=30/365, sigma=0.20, r=0.05
# Known vanna ≈ 0.395 (from QuantLib or tabulated values)
assert abs(bs_vanna(100, 100, 0.20, 30/365) - 0.395) < 0.01
```
Pin the formula to the QuantLib convention (∂²C/∂S∂σ). Document in `greeks_engine.py` which partial this is.

---

### Pitfall 8: Module-Level Globals Survive Streamlit Reruns

**What goes wrong:**
```python
# streamlit_app.py — WRONG
_chain_cache = {}

def get_chain(ticker):
    if ticker not in _chain_cache:
        _chain_cache[ticker] = load_chain(ticker)
    return _chain_cache[ticker]
```
`_chain_cache` is module-level. In Streamlit, the module is loaded once per process, not once per session. So `_chain_cache` persists across all reruns and all sessions — stale chains from the morning still appear at 4pm because the dict never expires.

**Why it matters here:** The GEX dashboard is intended to show intraday-fresh data. A chain cached at 9:30am is wrong by 3pm.

**Prevention (Phase 3):**
Use `@st.cache_data(ttl=300)` (5-minute TTL) on all chain-fetching functions instead of hand-rolled module-level dicts. Streamlit's cache handles expiry, invalidation on source-change, and per-session isolation correctly. Never write a `_cache = {}` at module level in `streamlit_app.py`.

---

### Pitfall 9: matplotlib Figure Objects Accumulate in Streamlit Loop

**What goes wrong:**
```python
for ticker in tickers:
    fig = plot_strike_gex(...)  # creates a new figure
    st.pyplot(fig)
    # forgot: plt.close(fig)
```
Each `plt.subplots()` registers the figure with matplotlib's global figure manager. After 10 tickers × N reruns, matplotlib holds hundreds of figure references in memory. Memory grows linearly with reruns. Reported in Streamlit issue #8834 as a real production problem.

**run_daily.py already does this correctly** (`plt.close(fig)` after every `fig_to_b64()`). The risk is that `streamlit_app.py` is written from scratch and the pattern is not copied.

**Prevention (Phase 3):**
Enforce `plt.close(fig)` as a mandatory pattern after every `st.pyplot(fig)`. Better: wrap it:
```python
def render_mpl(fig: plt.Figure, **kwargs) -> None:
    st.pyplot(fig, **kwargs)
    plt.close(fig)
```
Use `render_mpl()` everywhere in `streamlit_app.py`. The existing `analytics.py` functions return the figure rather than calling `plt.show()` — this pattern is already correct and should be preserved.

---

## Low Severity Pitfalls

### Pitfall 10: Windows Path Separators in Cache Keys

**What goes wrong:**
If `STORE` (the parquet path) is ever passed as a string argument to a `@st.cache_data` function, Windows backslash paths (`C:\dev\options-quant\out\gex_snapshots.parquet`) are technically hashable strings, but they create different cache keys than POSIX paths on the same machine if path construction is inconsistent (e.g. one call uses `str(STORE)` and another uses `STORE.as_posix()`).

`validation.py` uses `pathlib.Path` throughout — this is correct. The trap is in `streamlit_app.py` if path strings are passed to cached loader functions.

**Prevention (Phase 3):**
Never pass path objects or path strings as cache arguments. Instead, make the path a module-level constant inside the cached function:
```python
@st.cache_data(ttl=60)
def load_snapshot_history() -> pd.DataFrame:
    return pd.read_parquet(STORE)  # STORE is a module constant, not an arg
```
No path ever appears in a cache key.

---

## Phase Assignment Summary

| Phase | Pitfalls to Address |
|-------|---------------------|
| **Phase 1 — Second-order Greeks** | P1 (charm T-floor guard), P7 (vanna unit test + formula pin) |
| **Phase 2 — VEX + Parquet** | P5 (schema evolution read/write pattern), P7 (VEX scale validation) |
| **Phase 3 — Streamlit Dashboard** | P2 (Agg + figure close), P3 (yfinance TTL + serial), P4 (tuple not list), P6 (no emailer import), P8 (no module globals), P9 (plt.close wrapper), P10 (no path args in cache) |
| **Phase 4 — Historical Tab** | P5 (skipna aggregations on pre-v3.0 NaN rows) |

---

## Sources

- [Streamlit st.pyplot docs — thread safety warning](https://docs.streamlit.io/develop/api-reference/charts/st.pyplot)
- [Streamlit issue #1227 — IndexError/KeyError under concurrent load](https://github.com/streamlit/streamlit/issues/1227)
- [Streamlit issue #8834 — Memory leak updating figures](https://github.com/streamlit/streamlit/issues/8834)
- [Streamlit issue #6097 — win32com com_error after 30s / rerun](https://github.com/streamlit/streamlit/issues/6097)
- [Streamlit issue #10957 — unhashable type: list in DataFrame with cache_data](https://github.com/streamlit/streamlit/issues/10957)
- [yfinance rate limit discussion #2431](https://github.com/ranaroussi/yfinance/discussions/2431)
- [yfinance 429 in Streamlit Community Cloud](https://discuss.streamlit.io/t/yfratelimiterror-too-many-requests-rate-limited-try-after-a-while/111207)
- [Streamlit session state docs](https://docs.streamlit.io/develop/concepts/architecture/session-state)
- [Matplotlib FAQ — thread safety](https://matplotlib.org/stable/users/faq.html)

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
