# Phase 4: Historical Tab - Context

**Gathered:** 2026-05-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend `streamlit_app.py` with a Historical tab that reads from `out/gex_snapshots.parquet` to show: zero-gamma level trend chart (30-day with spot overlaid), regime persistence table (20 sessions), "Days in current regime" streak counter on regime cards, and an event study display (gated at ≥20 sessions).

All data comes from the existing parquet store — no new data sources, no new packages. The email pipeline (`run_daily.py`) remains untouched.

</domain>

<decisions>
## Implementation Decisions

### Layout Integration

- **D-01:** Wrap the full app in `st.tabs(["Live", "Historical"])`. Existing Phase 3 content (regime cards, overview chart, per-ticker expanders) moves into `tabs[0]`. Phase 4 Historical content lives in `tabs[1]`. Restructuring is low-risk — existing code is indented one level inside `with tabs[0]:`.

### Historical Data Loading

- **D-02:** Add `load_history(ticker: str, days: int = 30) -> pd.DataFrame` to `gex/validation.py`, alongside `load_yesterday()`. Reads parquet, filters to `ticker` + last `days` trading sessions (sorted descending by date), returns a DataFrame. Keeps all parquet access in one module.
- **D-03:** In `streamlit_app.py`, decorate `load_history` call with `@st.cache_data(ttl=1800)` — 30-min TTL because the parquet store only changes once per daily `run_daily` run. This is a separate cache from `fetch_ticker()` (TTL=300) so live and historical data are not coupled.

### Streak Counter (HIST-03)

- **D-04:** Streak ("Days in current regime") is computed from `load_history()` output, not bundled into `fetch_ticker()`. Keeps the live fetch fast. A helper `_compute_streak(hist_df, current_regime)` in `streamlit_app.py` counts consecutive trailing rows with the same `gamma_regime`. Result is passed to `render_regime_card()` as an optional `streak` kwarg.
- **D-05:** "Days" means trading sessions (parquet rows), not calendar days.

### ZGL Trend Chart (HIST-01)

- **D-06:** Single axis — ZGL and spot are both price-level values, so dual axis is unnecessary. Line chart: `zero_gamma_level` as a line, `spot` as a second line on the same axis. 30-session lookback from `load_history(ticker, days=30)`.

### Regime Persistence Table (HIST-02)

- **D-07:** Built from `load_history(ticker, days=20)`. Counts sessions per regime, computes % of total. `st.dataframe` display with columns: Regime | Sessions | % Days. One table per selected ticker, rendered inside the Historical tab.

### Event Study Display (HIST-04)

- **D-08:** Parquet-only — no live yfinance fetch. Show regime split stats: sessions count, % days in each regime, avg net_gex per regime. Uses `load_history()` output. **No** forward return / range calculation (the existing `event_study()` function in `validation.py` is not called from the dashboard — it's a CLI tool).
- **D-09:** Gated at ≥20 sessions of history per the requirement (HIST-04). If fewer than 20 sessions exist for the ticker, show `st.info("Insufficient history — need ≥20 sessions.")` rather than an error or empty chart.
- **D-10:** Ticker selector: use a `st.selectbox` in the Historical tab to pick which ticker's event study to display (not locked to the sidebar selection — user may want to view history for a different ticker than the live view).

### Claude's Discretion

- Exact formatting of the streak counter within the regime card (e.g., "5 sessions" vs "5d" — keep consistent with existing card typography)
- Column order / styling for the regime persistence `st.dataframe`
- Whether the ZGL trend and regime persistence sections are one section per ticker or laid out in columns

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Code to Extend

- `streamlit_app.py` — Full Phase 3 dashboard; Phase 4 wraps in `st.tabs()`; `render_regime_card()` gains `streak` kwarg
- `gex/validation.py` — `load_yesterday()` pattern; `save_snapshot()` schema; `load_history()` is a new function here
- `out/gex_snapshots.parquet` — Parquet schema: `date, ticker, spot, net_gex, gamma_regime, zero_gamma_level, call_wall, put_wall, vanna_exposure`

### Requirements

- `.planning/REQUIREMENTS.md` — HIST-01 through HIST-04 (all Phase 4)
- `.planning/ROADMAP.md` — Phase 4 success criteria (4 criteria defined)

### Prior Phase Patterns

- `.planning/phases/02-exposure-pm-flow/02-CONTEXT.md` — Parquet schema decisions (D-08: only `vanna_exposure` historicised, not charm)
- `.planning/phases/03-streamlit-dashboard/03-RESEARCH.md` — `@st.cache_data` patterns, `plt.close(fig)` after every `st.pyplot(fig)`, matplotlib Agg backend placement

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `load_yesterday(ticker)` in `validation.py` — pattern to follow for `load_history(ticker, days)`: reads parquet, filters by ticker, sorts by date
- `render_regime_card(col, summary, spot)` in `streamlit_app.py` — extend with optional `streak: int | None = None` kwarg
- `REGIME_COLOR` from `gex/report.py` — already imported in `streamlit_app.py`; reuse for regime persistence table color coding
- `plt.rcParams` block in `streamlit_app.py` lines 26-47 — all new matplotlib charts in Phase 4 inherit these styles automatically (transparent bg, light text)

### Established Patterns

- `@st.cache_data(ttl=300)` for live fetch; use `ttl=1800` for historical data (changes once per day max)
- Always `plt.close(fig)` immediately after `st.pyplot(fig)`
- `matplotlib.use("Agg")` already set at top of `streamlit_app.py` — no change needed
- `st.info()` for informational gates (not `st.warning()` or `st.error()`)

### Integration Points

- `streamlit_app.py` top-level — wrap with `tabs = st.tabs(["Live", "Historical"])`; existing content indents into `with tabs[0]:`
- `gex/validation.py` — add `load_history()` function (no changes to existing functions)
- `render_regime_card()` — add `streak` kwarg (backward-compatible; default `None`)

</code_context>

<specifics>
## Specific Ideas

- Event study table format chosen: `| Regime | Sessions | % Days | Avg Net GEX |` — same column structure as the preview shown during discussion
- Event study ticker selector: `st.selectbox` in the Historical tab, not tied to sidebar multiselect
- ZGL trend: single axis with spot overlaid (both are price levels — no dual axis needed)
- Streak counter counts trading sessions (parquet rows), not calendar days

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-historical-tab*
*Context gathered: 2026-05-06*
