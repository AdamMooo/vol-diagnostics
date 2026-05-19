# Architecture

**Analysis Date:** 2026-05-06

## Pattern Overview

**Overall:** Shared pipeline with thin output adapters

The GEX module is structured as a single linear compute pipeline (`gex/compute.py:compute_ticker()`) that produces a canonical result dict. Two output adapters — the daily email orchestrator and the Streamlit dashboard — both call this same pipeline. Neither adapter contains any computation logic.

**Key Characteristics:**
- All business logic lives in `gex/compute.py` and the modules it calls
- Output adapters (`gex/run_daily.py`, `streamlit_app.py`) are pure display/delivery wrappers
- DataFrames are passed between pipeline stages; no shared mutable state
- Each pipeline stage returns a copy (never mutates inputs)

## Layers

**Data Ingestion:**
- Purpose: Fetch raw options chains from CBOE and parse OPRA symbols
- Location: `gex/data_loader.py`
- Contains: `load_chain()`, `ChainSnapshot` dataclass, OPRA symbol parser
- Depends on: `requests`, stdlib `datetime`
- Used by: `gex/compute.py`

**Greeks Computation:**
- Purpose: Compute vanna and charm via Black-Scholes; note CBOE-sourced gamma/delta/vega/theta are passed through unchanged
- Location: `gex/greeks_engine.py`
- Contains: `bs_gamma()`, `bs_vanna()`, `bs_charm()`, `add_greeks()`
- Depends on: `numpy`, `scipy.stats.norm`
- Used by: `gex/compute.py`, `gex/exposure_engine.py` (gamma profile recompute)

**Exposure Engine:**
- Purpose: Convert per-option greeks into dollar-denominated exposures (GEX, VEX, CHEX)
- Location: `gex/exposure_engine.py`
- Contains: `compute_gex()`, `compute_vex()`, `compute_chex()`, strike aggregators, `gamma_profile()`
- Formula: `GEX = sign × gamma × OI × 100 × spot² × 0.01`
- Depends on: `numpy`, `pandas`, `gex/greeks_engine.py` (gamma_profile only)
- Used by: `gex/compute.py`

**Analytics:**
- Purpose: Derive regime classification, key levels (ZGL, walls), and produce Plotly charts
- Location: `gex/analytics.py`
- Contains: `summarise()`, `_find_zero_crossing()`, `plot_strike_gex()`, `plot_gamma_profile()`, `plot_overview()`
- Depends on: `numpy`, `pandas`, `plotly`
- Used by: `gex/compute.py` (summarise), `streamlit_app.py` (charts), `gex/analytics.py` imports `gex/report.py` constants in `plot_overview()`

**Shared Pipeline:**
- Purpose: Single-function orchestration of all pipeline stages for one ticker
- Location: `gex/compute.py`
- Contains: `compute_ticker()` — fetch → greeks → GEX/VEX/CHEX → summarise → vs_yesterday → early exercise
- Returns: `{"summary": dict, "s_df": DataFrame, "p_df": DataFrame, "spot": float}`
- Depends on: all four layers above plus `gex/validation.py`
- Used by: `gex/run_daily.py`, `streamlit_app.py`

**Validation / Snapshot Store:**
- Purpose: Persist daily summaries as parquet, load prior-day data for change classification
- Location: `gex/validation.py`
- Contains: `save_snapshot()`, `load_yesterday()`, `load_history()`, `_classify_vs_yesterday()`, `event_study()`
- Store: `out/gex_snapshots.parquet`
- Depends on: `pandas`, `pyarrow`, `yfinance`, `pandas_market_calendars`
- Used by: `gex/compute.py` (load_yesterday), `gex/run_daily.py` (save_snapshot), `streamlit_app.py` (load_history)

**Output Adapters:**
- `gex/run_daily.py` — loops ALL_TICKERS, calls `compute_ticker()`, saves snapshots, builds HTML email, sends via Outlook
- `streamlit_app.py` — interactive dashboard; wraps `compute_ticker()` with `@st.cache_data(ttl=300)`; renders regime cards + Plotly charts

**Email Report:**
- Purpose: Build inline-CSS HTML email body from summary dicts
- Location: `gex/report.py`
- Contains: `build_email()`, `_index_table()`, `_purpose_table()`, formatting helpers, `TICKER_LABEL`, `REGIME_COLOR` constants
- Used by: `gex/run_daily.py`, `gex/analytics.py:plot_overview()` (imports constants only)

**Email Sender:**
- Purpose: Deliver HTML email via Outlook COM automation
- Location: `gex/emailer.py`
- Contains: `send()`, `_recipients()`
- Depends on: `win32com.client`, `python-dotenv`
- Used by: `gex/run_daily.py`

## Data Flow

**Daily Email Flow:**

1. `gex/run_daily.py:run()` checks NYSE trading day via `pandas_market_calendars`
2. Loops `ALL_TICKERS` (6 index + 14 equity); calls `process_ticker()` (error-wrapped `compute_ticker()`)
3. `compute_ticker()` fetches CBOE chain → computes greeks → computes GEX/VEX/CHEX → summarises → loads prior snapshot for vs_yesterday
4. `save_snapshot()` appends summary to `out/gex_snapshots.parquet`
5. `rpt.build_email()` renders inline-CSS HTML tables
6. `emailer.send()` dispatches via Outlook COM

**Streamlit Dashboard Flow:**

1. User loads `streamlit_app.py`; password gate checks `.streamlit/secrets.toml`
2. Selected tickers fetched via `fetch_ticker()` (5-min Streamlit cache wrapping `compute_ticker()`)
3. `render_section()` renders regime cards + Plotly charts per ticker
4. Historical data loaded from parquet via `_load_history_cached()` (30-min cache)

**State Management:**
- No global mutable state in pipeline
- Streamlit session state: `authenticated` bool only
- Snapshots persist in `out/gex_snapshots.parquet` across runs

## Key Abstractions

**ChainSnapshot:**
- Purpose: Typed container for raw CBOE fetch output
- Location: `gex/data_loader.py`
- Fields: `ticker`, `spot`, `as_of`, `chains` (DataFrame), `iv30`, `price_change_pct`

**compute_ticker() result dict:**
- Purpose: Canonical pipeline output; passed to both email and dashboard adapters
- Keys: `summary` (analytics dict), `s_df` (strike GEX DataFrame), `p_df` (gamma profile DataFrame), `spot`
- The `summary` dict contains: `net_gex`, `zero_gamma_level`, `call_wall`, `put_wall`, `gamma_regime`, `spot`, `net_vex`, `net_chex`, `delta_hedge_flow`, `ticker`, `iv30`, `price_change_pct`, `early_exercise_strikes`, `early_exercise_oi`, `vs_yesterday`

**Regime Classification:**
- `"positive"` — net GEX > 0 and above neutral thresholds (dealers net long gamma; stabilising)
- `"negative"` — net GEX < 0 and below neutral thresholds (dealers net short gamma; destabilising)
- `"neutral"` — |net GEX| < $200M floor OR within ±0.5% of max absolute GEX
- Constants in `gex/analytics.py`: `NEUTRAL_ABS_FLOOR = 0.2e9`, `NEUTRAL_BAND_PCT = 0.005`

## Entry Points

**Single-ticker GEX (POC/debug):**
- Location: `gex/run_gex.py`
- Invocation: `python -m gex.run_gex [--ticker QQQ] [--no-save]`
- Uses older direct pipeline (not via `compute.py`); saves static PNGs via matplotlib

**Daily orchestrator:**
- Location: `gex/run_daily.py`
- Invocation: `python -m gex.run_daily [--dry-run]`
- Scheduled via `runners/gex_daily.ps1` at 16:30 ET

**Streamlit dashboard:**
- Location: `streamlit_app.py`
- Invocation: `streamlit run streamlit_app.py`
- Port: 8501

## Error Handling

**Strategy:** Fail-soft at the ticker level; never abort the full run

**Patterns:**
- `gex/run_daily.py:process_ticker()` wraps `compute_ticker()` in try/except; returns `{"summary": {"ticker": ..., "error": str(exc)}}`
- Error tickers are included in email with "Load failed" row
- `gex/validation.py:load_yesterday()` catches all exceptions and returns `None`; pipeline continues without prior-day comparison
- `gex/emailer.py:send()` raises `RuntimeError` with actionable message if Outlook unavailable

## Cross-Cutting Concerns

**Logging:** `print()` to stdout only; no logging framework
**Validation:** At data boundaries only (`load_chain()` filters OI, IV, DTE; `summarise()` handles empty DataFrames)
**Authentication:** Dashboard password gate in `streamlit_app.py`; email has no auth (Outlook COM)
**Immutability:** All DataFrame-transforming functions return copies; inputs never mutated
**Sign Convention:** Calls positive, puts negative throughout — enforced in `compute_gex()`, `compute_vex()`, `compute_chex()` via `np.where(df["type"] == "call", 1.0, -1.0)`

---

*Architecture analysis: 2026-05-06*

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
