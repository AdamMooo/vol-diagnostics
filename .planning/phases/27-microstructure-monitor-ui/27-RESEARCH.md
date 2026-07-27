# Phase 27: Microstructure Monitor UI - Research

**Researched:** 2026-07-26
**Domain:** Streamlit dashboard restructuring + read-layer integration with an already-built severity-rank/alert engine (`engine/monitor/`)
**Confidence:** HIGH (engine internals, current app.py/report.py structure, Streamlit patterns — all read directly from the codebase and the installed `developing-with-streamlit` skill) / MEDIUM (exact layout primitives, since CONTEXT.md leaves those to discretion) / LOW (the "Methodology" link target, an unresearchable product decision)

## Summary

`engine/monitor/` (Phase 26) is a complete, tested (465/465 green) severity-ranking and hysteresis-alerting engine. It computes and persists one `MonitorRow` per (date, ticker, metric) to `out/monitor/ranks.parquet`, and one `AlertEvent` per band transition to `out/monitor/alert_events.parquet`, via `run_daily.py` (already wired, lines 227-239). It is metric-agnostic, pure-Python, well-tested, and requires **zero new signal logic** for this phase.

The gap is entirely on the **read side**. `engine/monitor/monitor_store.py` only exposes a single-row point-read (`load_prior_monitor_row`, one `(ticker, metric)` at a time, requires a full parquet re-read per call) plus the two raw store paths. There is no bulk "latest rank per row" reader, no "N-session trail" reader, and no "today's alert events" reader — all three are required by the distribution board and the event-shaped email. The plan must add a **thin read-adapter module** (new file, e.g. `engine/monitor/monitor_reader.py`) that reshapes the existing persisted structs — this is data plumbing, not a new signal, and is squarely inside the phase boundary.

Second finding: `out/monitor/ranks.parquet` currently holds only **2 calendar dates** (2026-07-22, and a 2026-07-24 row that is all-NaN — a stale/test artifact from Phase 26 development, not a real production day), and `out/monitor/alert_events.parquet` **does not exist yet** (zero alerts have ever fired). The "10-session trail" and the event-shaped email are both correctly built against this reality: they will render as near-empty/sparse for weeks until daily collection accumulates history. This is expected behavior per the design ("silence is information"), not a bug, but the plan should make this explicit in its verification steps so it isn't mistaken for broken wiring.

**Primary recommendation:** Build one new adapter module on top of `engine/monitor/monitor_store.py`'s two parquet stores (no changes to the engine itself), drive the distribution board from `schema.METRIC_INVENTORY` (the canonical 17-row list — already matches the v1 row inventory almost exactly), reuse `st.dataframe(on_select="rerun", selection_mode="single-row")` + sparkline columns for the board (native Streamlit primitives, no custom plotly grid needed for v1), and reuse existing surface/VRP functions for evidence panels with two small named gaps (a value-vs-value VRP leg exposer, and a smile-slice recombination for the skew evidence panel).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Severity rank computation (ECDF, dual lookback, |Δk|) | Backend / engine (`engine/monitor/ranker.py`) | — | Already built, pure functions, no I/O — owns the math |
| Hysteresis alert state transitions | Backend / engine (`engine/monitor/hysteresis.py`) | — | Already built, pure state machine — owns alert semantics |
| Rank/alert persistence | Backend / storage (`engine/monitor/monitor_store.py` → `out/monitor/*.parquet`) | — | Owns the on-disk schema; write path already wired into `run_daily.py` |
| Rank read/reshape for UI consumption | **New: thin adapter layer** (`engine/monitor/monitor_reader.py` or `app.py`-local helpers) | — | Gap — no bulk reader exists today; must sit between storage and UI without touching engine internals |
| Distribution-board rendering (rows, strips, trails, selection) | Frontend (Streamlit `app.py`) | — | Pure presentation over adapter output |
| Evidence-panel mechanism views (smile, diff surface, IV-vs-RV) | Frontend (Streamlit `app.py`) | Backend (`engine/surface/surface_interactive.py`, `engine/vol/vrp_history.py`) | Rendering is frontend; the underlying payload builders already live in the engine and are reused, not duplicated |
| Email event-shaping | Backend / report builder (`engine/report/report.py`) | Storage (`monitor_store.ALERT_EVENTS_STORE`) | Email has no server — it's a static-HTML builder run once/day by `run_daily.py`, same tier as the current report code |
| Net-GEX sign chip | Frontend (Streamlit `app.py`), sourced from `compute_ticker()` summary | — | Explicitly NOT part of `engine/monitor/` (D-10) — stays on the existing dashboard data path, same as today's Positioning tab |

## Standard Stack

No new packages. This phase is 100% internal-module integration.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| streamlit | (repo-pinned; skill files found under `.venv/Lib/site-packages/streamlit/.agents/skills/`) | Dashboard UI | Already the project's only UI framework |
| pandas / pyarrow | (repo-pinned) | Reading `out/monitor/*.parquet` | Already used by every other store reader in the repo (`engine/data/validation.py`, `engine/monitor/monitor_store.py`) |
| plotly | (repo-pinned) | Evidence-panel charts, existing surface/diff/movie renderers | Already the only chart library used for surfaces (`engine/surface/surface_interactive.py`, `engine/gex/analytics.py`) |

### Supporting
None required. No new libraries — the phase reuses existing renderers.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Native `st.dataframe` sparkline columns for the 10-session trail | A hand-built combined-plotly "percentile strip" figure (17 rows in one subplot grid) | Plotly grid gives full control over "today's dot" + deep/1yr tick marks in one visual, but is materially more code to build and maintain for v1. Sparkline columns (`LineChartColumn`/`BarChartColumn`) are a first-class Streamlit primitive purpose-built for exactly this ("evenly-spaced trend data") and ship today — recommend starting there, upgrading to custom plotly only if the built-in column reads too thin once real data fills in. |
| `st.dataframe(on_select="rerun")` for row-click navigation | Manual per-row `st.button` in a loop, or `st.column_config.ButtonColumn` | Native row-selection (`event.selection.rows`) is simpler and is the pattern the skill's `data-display.md` explicitly recommends over `st.data_editor`/manual buttons for "select a row to view detail" use cases. |

**Installation:** N/A — no new packages.

**Version verification:** N/A — no new packages to check against a registry.

## Package Legitimacy Audit

Not applicable — this phase installs no external packages. All work is internal-module composition (a new adapter module + refactors of `app.py`/`report.py`), reusing the existing pinned stack (`streamlit`, `pandas`, `pyarrow`, `plotly`, `scipy`) already present in `requirements.txt`.

## Monitor-Engine Consumption Map

### What `engine/monitor/` exposes today

| Component | File | What it is | UI-usable as-is? |
|---|---|---|---|
| `MonitorRow` dataclass | `schema.py` | One row per (date, ticker, metric): `value`, `level_rank_deep`/`n_deep`, `level_rank_1yr`/`n_1yr`, `change_rank`/`change_n`, `band_state_deep`/`band_state_1yr`/`band_state_change` | Yes — this IS the row shape the board needs, once bulk-read |
| `AlertEvent` dataclass | `schema.py` | One row per fired transition: `date`, `ticker`, `metric`, `rank_kind`, `alert_type` ("entry"/"escalation"), `rank_at_transition`, `prior_state` | Yes — this IS the email's row shape, once bulk-read |
| `METRIC_INVENTORY` | `schema.py` | Canonical list of 17 `(metric, ticker)` pairs: `{vrp, skew_25d, fly_25d, surface_level, surface_rms} × {SPY, QQQ, IWM}` (15) + `{term_9d_30, term_30_3m} × SPY` (2) | Yes — drive the board's row list directly from this constant, do not hand-maintain a second list |
| `ranker.compute_level_ranks` / `compute_change_rank` | `ranker.py` | Pure ECDF percentile functions | Not needed by UI directly — already baked into the persisted `MonitorRow` |
| `hysteresis.check_alert_transition` | `hysteresis.py` | Pure state-transition function | Not needed by UI directly — already baked into `band_state_*` / `AlertEvent` |
| `RANKS_STORE` / `ALERT_EVENTS_STORE` | `monitor_store.py` | `out/monitor/ranks.parquet`, `out/monitor/alert_events.parquet` | Yes, but only via a new bulk reader (see Gap below) |
| `save_monitor_row` / `save_alert_event` | `monitor_store.py` | Write-path, called from `run_daily.py` | Write-only, not for UI |
| `load_prior_monitor_row(ticker, metric, before_date)` | `monitor_store.py` | Single most-recent row before a date, for exactly ONE `(ticker, metric)` pair | Usable but wrong-shaped/wrong-performance for a 17-row board (would mean 17 separate full-parquet reads per page load) |
| `compute_and_save_monitor_rows` | `monitor_store.py` | Orchestrates ranker+hysteresis+persistence for one ticker's metrics | Write-path, called by `run_daily.py` only |
| `MONITOR_ALERT_BAND_ENTRY/ESCALATE/EXIT` | `engine/config.py` (90/94/85, re-calibrated 2026-07-24) | Rank thresholds used for band overlays | Yes — reuse directly for evidence-panel band lines |

### Gap: no bulk-read adapter exists (the riskiest part to plan)

`monitor_store.py` was built Phase 26 purely to support the write path (`compute_and_save_monitor_rows`) plus one narrow read need internal to that write path (yesterday's state for hysteresis). **Nothing reads for display.** Concretely missing, all three required by CONTEXT.md's success criteria:

1. **Latest row per (ticker, metric)** across all 17 `METRIC_INVENTORY` pairs — needed for "today's dot" + deep/1yr rank marks on every board row. `load_prior_monitor_row` does only one pair per call and re-reads the whole parquet file each time; calling it 17× per page load is correct but wasteful (17 full-file reads instead of 1).
2. **N-session trail per (ticker, metric)** — needed for the "10-session trail" (CONTEXT.md calls this load-bearing). No function returns more than one row today.
3. **Recent alert events** — needed both for the email's event-shaped body and (optionally) for any "currently alerting" highlight on the board. `ALERT_EVENTS_STORE` has no reader function at all today (only `save_alert_event`); the file does not currently exist on disk (see Cold-Start Reality below), so any reader must gracefully handle "store absent" the same way `monitor_store.load_prior_monitor_row` already does (`if not path.exists(): return None`).

**Recommended fix (fits the phase boundary — pure read/reshape, no new signal):** add `engine/monitor/monitor_reader.py` with three functions, mirroring the existing store's exception-safety and `store: pathlib.Path | None = None` param-override convention (for testability, matching `test_monitor/test_store.py`'s pattern exactly):

```python
def load_all_current_ranks(store: pathlib.Path | None = None) -> pd.DataFrame:
    """One full parquet read; groupby(['ticker','metric']) + tail(1) per group.
    Iterate schema.METRIC_INVENTORY to guarantee every board row exists even
    if a metric has zero history yet (fill with an all-None placeholder row)."""

def load_rank_trail(ticker: str, metric: str, n: int = 10, store=None) -> pd.DataFrame:
    """Filter to (ticker, metric), sort by date, tail(n). Empty df if absent."""

def load_recent_alert_events(days: int = 1, store=None) -> pd.DataFrame:
    """Filter alert_events.parquet to the last `days` calendar days. Empty df
    (not None) if the store doesn't exist yet -- callers treat empty as
    'nothing unusual', never as an error."""
```

This is one full parquet read (not 17), cacheable with `@st.cache_data(ttl=...)` since the store only changes once/day at `run_daily` time (same TTL tier as `CACHE_TTL_HISTORY` = 21600s already used elsewhere in `app.py`).

### Cold-start reality (verified against `out/monitor/` on disk, 2026-07-26)

```
out/monitor/ranks.parquet:  24 rows, 2 dates only (2026-07-22 full 17-row day;
                             2026-07-24 is a 7-row SPY-only day, ALL VALUES NaN —
                             a stale/dev-run artifact, not real production data)
out/monitor/alert_events.parquet: DOES NOT EXIST — zero alerts fired to date
```

The monitor engine shipped 2026-07-24 (commit `007a544`); `run_daily.py`'s monitor-row wiring (lines 227-239) has run at most a handful of times. **The "10-session trail" will show 1-2 points, not 10, for weeks.** The plan's verification step should explicitly check "renders gracefully with <10 sessions of trail data" rather than assuming a full trail exists — this is a real near-term operating condition, not an edge case to defer.

## Per-Row Data-Source Map (v1 row inventory)

CONTEXT.md says "~15 rows"; `METRIC_INVENTORY` actually enumerates **17** rows. This is a minor, harmless discrepancy (5 metrics × 3 tickers = 15, + 2 SPY-only term-ratio rows = 17) — the plan should drive the board off `METRIC_INVENTORY` directly rather than hand-count a row list, so it never drifts from the engine's own inventory.

| Row (metric, ticker) | Already ranked by engine? | `n_deep` observed (2026-07-22 snapshot) | Credibility status | Data source for evidence-panel history |
|---|---|---|---|---|
| `vrp` × SPY/QQQ/IWM | Yes | 2520 / 2520 / 2515 | Well past `MONITOR_CREDIBILITY_FLOOR_SESSIONS` (252) — full deep-history claims OK | `engine/vol/vrp_history.vrp_history_series(ticker)` |
| `skew_25d` × SPY/QQQ/IWM | Yes | 41 (all three) | Below floor — chain-derived, cold-starting since ~2026-05-06; rank shown labeled with n, but no "historically rare" claim, no alert eligible yet (hysteresis gates on n, not rank display) | `engine.data.validation` gex_snapshots `front_skew` column, via `engine.monitor.metrics._gex_snapshot_column` |
| `fly_25d` × SPY/QQQ/IWM | Yes | 19 (all three) | Below floor, same cold-start reason | gex_snapshots `butterfly` column |
| `surface_level` / `surface_rms` × SPY/QQQ/IWM | Yes | 30 (all) | Below floor, cold-starting since surface snapshots began ~2026-05-06 | `engine.surface.surface_evolution` store, horizon=5 (`config.MONITOR_SURFACE_EVOLUTION_HORIZON`) |
| `term_9d_30` / `term_30_3m` × SPY only | Yes | 3909 / 4235 | Well past floor | `engine.data.vol_index` VIX9D/VIX/VIX3M ratio, via `engine.monitor.metrics._term_ratio_series` |
| `term_9d_30` / `term_30_3m` × QQQ/IWM | **Correctly absent** | — | N/A by design — `vol_metrics._TERM_SYMBOLS["QQQ"] = None`, `["IWM"] = None` (CBOE publishes no 9D/3M for VXN/RVX, verified 2026-06-23 per project CLAUDE.md) | Board must render these two cells as "—" / omitted for QQQ and IWM, not as a missing-data error |
| Net-GEX sign (all 3 tickers) | **Explicitly excluded** (D-10, `schema.py` docstring) | — | N/A — state chip, not a rank | `compute_ticker()` summary `net_gex` field — same value already used in today's Positioning tab (`app.py` lines ~700-711) |
| IWM–SPY VRP spread | Deferred (not in `METRIC_INVENTORY`) | — | Out of scope | N/A — do not wire |

No metric wiring work is needed for any v1 row — `engine/monitor/metrics.load_metric_series(ticker, metric_name)` already dispatches all 17 pairs correctly. The only new engine-adjacent work is the read-adapter above, not new metric plumbing.

## Architecture Patterns

### System Architecture Diagram

```
run_daily.py (already wired, daily cron/GH Actions)
    │
    ├─► compute_ticker() ──► summary dict ──► save_snapshot()/save_surface_snapshot() (existing)
    │                                     └─► update_evolution() (existing)
    │
    └─► monitor_store.compute_and_save_monitor_rows(ticker, summary, today, bands...)
            │  reads: metrics.load_metric_series() (vrp_history / gex_snapshots / evolution / vol_index)
            │  runs:  ranker.compute_level_ranks / compute_change_rank
            │  runs:  hysteresis.check_alert_transition ×3 (deep/1yr/change)
            └─► writes: out/monitor/ranks.parquet (MonitorRow)
                        out/monitor/alert_events.parquet (AlertEvent, append-only)

──────────────────────────── NEW: read side (Phase 27) ────────────────────────────

app.py (Streamlit, on every user page load / rerun)
    │
    ├─► monitor_reader.load_all_current_ranks()  ──► 17-row DataFrame ──► distribution board
    ├─► monitor_reader.load_rank_trail(t, m, 10)  ──► sparkline data (per-row, on demand or precomputed)
    │
    │   [user clicks a row: st.dataframe on_select="rerun" → st.session_state.selected_row = (ticker, metric)]
    │
    └─► evidence panel dispatch on metric type:
            skew_25d / fly_25d  → smile overlay: build_surface_payload(today) + build_surface_payload(5d-ago)
                                    → extract matching smile_fit/smile_raw slice from each, plot 2 lines
            surface_level/rms   → existing build_diff_payload/render_diff_html (reused verbatim,
                                    same call already used by _surface_compare_section)
            vrp                 → NEW: vrp_history "components" (vi, rv legs) — see gap below
            term_9d_30/30_3m    → simple 2-line ratio-history plot from vol_index closes (no new engine code)
          + rank-history line with config.MONITOR_ALERT_BAND_ENTRY/ESCALATE/EXIT as horizontal reference lines

run_daily.py → report.py (email, once/day)
    │
    ├─► monitor_reader.load_recent_alert_events(days=1) ──► [] or [AlertEvent,...]
    └─► build_email(): if [] → "nothing unusual" line; else → one row per event
```

### Recommended Project Structure

```
engine/
  monitor/
    monitor_reader.py     # NEW — thin bulk-read adapter (this phase's only new engine file)
  vol/
    vrp_history.py         # add a components/legs function (see gap below) alongside vrp_history_series
app.py                     # restructured: distribution board replaces _render_environment_hero's risk bar;
                            # evidence-panel dispatch added; Surfaces/Positioning tabs mostly unchanged
engine/report/report.py    # cut caveat banner + glossary + OI table + key-levels; add Alerts section
```

### Pattern 1: Bulk-read adapter with store param-override (testability)
**What:** Mirror `monitor_store.py`'s own convention — every function accepts an optional `store: pathlib.Path | None = None` so tests can point at a `tmp_path` parquet file instead of `out/monitor/*.parquet`.
**When to use:** All three new `monitor_reader.py` functions.
**Example:**
```python
# Source: engine/tests/test_monitor/test_store.py (existing pattern to mirror)
@pytest.fixture
def ranks_store(tmp_path):
    return tmp_path / "ranks.parquet"

def test_load_all_current_ranks_picks_latest_date(ranks_store):
    ...
    result = monitor_reader.load_all_current_ranks(store=ranks_store)
    assert len(result) == len(METRIC_INVENTORY)
```

### Pattern 2: Native row-selection for the distribution board
**What:** `st.dataframe(df, on_select="rerun", selection_mode="single-row")` → `event.selection.rows` → map back to `(ticker, metric)` → store in `st.session_state`.
**When to use:** The board's click-to-evidence-panel navigation.
**Example:**
```python
# Source: developing-with-streamlit skill, references/data-display.md
event = st.dataframe(board_df, on_select="rerun", selection_mode="single-row", hide_index=True)
if event.selection.rows:
    idx = event.selection.rows[0]
    st.session_state.selected_monitor_row = (board_df.iloc[idx]["ticker"], board_df.iloc[idx]["metric"])
```
Do not assign back into the dataframe widget's own `key` after creation (session-state.md's documented `StreamlitAPIException` pitfall) — read the selection event, write to a *separate* session-state key.

### Pattern 3: Sparkline columns for the 10-session trail
**What:** `st.column_config.LineChartColumn` fed by `monitor_reader.load_rank_trail(...)`'s last-N rank values, one column in the same board dataframe.
**When to use:** The trail visual — avoids hand-building 17 individual plotly figures for v1.
**Example:**
```python
# Source: developing-with-streamlit skill, references/data-display.md "Sparklines in metrics"
st.dataframe(board_df, column_config={
    "trail": st.column_config.LineChartColumn("10d trail", width="small"),
    "level_rank_deep": st.column_config.NumberColumn("Deep %ile", format="%d"),
    "level_rank_1yr": st.column_config.NumberColumn("1yr %ile", format="%d"),
}, on_select="rerun", selection_mode="single-row", hide_index=True)
```

### Pattern 4: Fragment isolation for the board + evidence panel
**What:** Wrap the board-render + evidence-panel-render in `@st.fragment` (mirrors the existing `_surface_today_section`/`_surface_compare_section`/`_evolution_section` fragments already in `app.py`).
**When to use:** So a row click reruns only the board+panel, not the whole page (including the ~26s sequential CBOE fetch loop, which is already cached separately but a full-page rerun still re-executes surrounding markdown/layout code).
**Example:**
```python
# Source: app.py's existing pattern (lines 464-486, 489-593, 596-646)
@st.fragment
def _distribution_board_section(all_data: dict) -> None:
    board_df = _load_board_df()  # calls the cached monitor_reader adapter
    event = st.dataframe(board_df, on_select="rerun", selection_mode="single-row", ...)
    ...
    if st.session_state.get("selected_monitor_row"):
        _render_evidence_panel(st.session_state.selected_monitor_row, all_data)
```

### Anti-Patterns to Avoid
- **Calling `load_prior_monitor_row` 17 times to build the board:** each call re-reads the entire parquet file from disk. Use one `load_all_current_ranks()` bulk read instead.
- **Re-deriving band thresholds in value-space per metric:** `MONITOR_ALERT_BAND_ENTRY/ESCALATE/EXIT` are **rank** thresholds (90/94/85), not value thresholds — they only mean something plotted against the rank time series, not against the raw metric value (which has no fixed scale and would require re-computing a rolling percentile-to-value mapping just for display — effectively a second signal). Plot the evidence-panel's "bands drawn" chart in rank-space (`level_rank_deep`/`level_rank_1yr` history from `ranks.parquet`), not raw-value space.
- **Building a second row-inventory list by hand:** drive the board directly off `schema.METRIC_INVENTORY` so the UI never silently drifts out of sync with the engine's canonical list (e.g. if Phase 26 calibration ever adds/removes a metric).
- **Treating `alert_events.parquet` absence as an error:** it legitimately does not exist yet (zero alerts fired). Every reader must return an empty DataFrame/list on `FileNotFoundError`/`.exists() is False`, exactly like `monitor_store.py`'s existing guard clauses.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Percentile/severity computation | A new dashboard-side ranking function | `engine/monitor/ranker.py` (already computed and persisted in `ranks.parquet`) | Phase boundary explicitly forbids new signals — the rank is already sitting in the row |
| Alert transition logic | Dashboard-side "is this abnormal" heuristics | `band_state_*` fields already in `MonitorRow`, or `AlertEvent` rows | Hysteresis state machine is already correct and tested; re-deriving it in the UI would double the logic and could disagree with the email |
| Smile/diff/movie surface rendering | New plotly surface code for evidence panels | `engine/surface/surface_interactive.py`'s `build_surface_payload`/`build_diff_payload`/`build_movie_payload` + their `render_*_html` counterparts | Already handles RBF fitting, coverage masking, near-singular degradation — re-implementing risks silently losing the honest-NaN-hole behavior |
| Row-click state management | Custom URL-param or global-dict hacks | `st.session_state` + `st.dataframe(on_select="rerun")` | Native, documented, avoids the widget-state anti-patterns the skill explicitly warns about |

**Key insight:** every piece of "hard" logic for this phase already exists somewhere in the repo (Phase 26's engine, or the existing surface/VRP renderers). The actual net-new code is a read adapter, some Streamlit layout, and two small exposer functions (VRP legs, skew smile-slice extraction) — resist the temptation to make any of it smarter than "reshape existing data for display."

## Common Pitfalls

### Pitfall 1: Board renders "insufficient history" everywhere and looks broken
**What goes wrong:** With only 2 stored monitor dates (one of them all-NaN), a literal "10-session trail" will show 1 real point for most rows on first ship.
**Why it happens:** The monitor engine is brand new (shipped 2026-07-24); daily accumulation just started.
**How to avoid:** Design the trail/sparkline to degrade gracefully at n<10 (show what's there, maybe a small "n sessions" caption, matching the existing `_fmt_vrp`/`_fmt_butterfly` "building to N" convention already used elsewhere in `card_model.py`). Do not gate the whole board on having 10 sessions.
**Warning signs:** If the plan's verification step expects a "full" 10-point trail, it will fail immediately and for weeks after ship — verification should explicitly test the <10-session case as the primary case, not an edge case.

### Pitfall 2: Treating rank-space and value-space bands as interchangeable
**What goes wrong:** Trying to draw `MONITOR_ALERT_BAND_ENTRY=90` as a horizontal line on a chart of the raw VRP/skew *value* — 90 is a percentile, not a vol-point or pp value, and the value-to-percentile mapping shifts every session (non-stationary ECDF).
**Why it happens:** "Bands drawn" reads naturally as "draw the threshold on the metric chart," but the threshold is only meaningful in rank-space.
**How to avoid:** Plot the evidence panel's history chart from the **rank** columns already in `ranks.parquet` (`level_rank_deep`/`level_rank_1yr`/`change_rank` time series), with the config band constants as flat reference lines on that same 0-100 axis. Show the raw value as a separate line or hover annotation if wanted, not the axis the bands are drawn against.
**Warning signs:** Band lines that appear to "move" session to session, or that don't line up with the displayed `band_state_deep` at all.

### Pitfall 3: Email "Alerts" section silently empty forever, mistaken for a bug
**What goes wrong:** `out/monitor/alert_events.parquet` doesn't exist yet — the very first few weeks of the event-shaped email will show "nothing unusual" every single day, even once wired correctly.
**Why it happens:** Zero alerts have fired since the engine shipped; most chain-derived metrics are also still below the credibility floor (n<252) so hysteresis can't fire on them yet regardless.
**How to avoid:** Verify the email refactor with a **synthetic** `AlertEvent` fixture (unit test), not by waiting for a real alert in production. Document the expected "quiet period" explicitly so it isn't flagged as broken during initial verification.
**Warning signs:** None visible in the running app — this is a documentation/expectation-setting risk, not a code risk.

### Pitfall 4: QQQ/IWM term-ratio cells rendered as errors instead of "N/A by design"
**What goes wrong:** `metrics.load_metric_series("QQQ", "term_9d_30")` returns `None` because `_TERM_SYMBOLS["QQQ"] = None` — this is correct, not a failure, but a naive board renderer might show a red "—" error state identical to a genuine missing-data failure.
**Why it happens:** `METRIC_INVENTORY` only lists `term_9d_30`/`term_30_3m` for SPY in the first place, so if the board is driven off `METRIC_INVENTORY` directly (recommended), this pitfall doesn't even arise — it only bites if someone hand-builds a "SPY/QQQ/IWM × all 7 metrics = 21 rows" grid instead of using the 17-row canonical inventory.
**How to avoid:** Drive row generation off `METRIC_INVENTORY`, not off a cartesian product of tickers × metric names.

## Code Examples

### Bulk rank read (new adapter, sketch)
```python
# Source: pattern mirrors engine/monitor/monitor_store.py's existing read functions
def load_all_current_ranks(store: "pathlib.Path | None" = None) -> pd.DataFrame:
    path = store if store is not None else RANKS_STORE
    if not path.exists():
        return pd.DataFrame(columns=[...])  # empty, same shape as MonitorRow fields
    hist = pd.read_parquet(path)
    hist["date"] = pd.to_datetime(hist["date"]).dt.date
    latest = hist.sort_values("date").groupby(["ticker", "metric"], as_index=False).tail(1)
    return latest
```

### Evidence-panel rank-history + band overlay
```python
# Source: pattern composes ranks.parquet (already stored) + config band constants (already calibrated)
hist = pd.read_parquet(RANKS_STORE)
row_hist = hist[(hist.ticker == ticker) & (hist.metric == metric)].sort_values("date")
fig.add_trace(go.Scatter(x=row_hist.date, y=row_hist.level_rank_deep, mode="lines+markers"))
for y, name in ((config.MONITOR_ALERT_BAND_ENTRY, "entry"),
                (config.MONITOR_ALERT_BAND_ESCALATE, "escalate"),
                (config.MONITOR_ALERT_BAND_EXIT, "exit")):
    fig.add_hline(y=y, line_dash="dot", annotation_text=name)
```

### Reusing the existing diff-surface for the surface-evolution evidence panel
```python
# Source: engine/surface/surface_interactive.py + app.py's existing _surface_compare_section
# (verbatim reuse — same call already used for the "Compare" sub-tab)
diff = build_diff_payload(surface_df_today, spot_today, surface_df_5d, spot_5d,
                           ticker=ticker, label_a="today", label_b="5d")
components.html(render_diff_html(diff), height=640, scrolling=False)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Dashboard leads with an AMPLIFYING/MIXED risk bar computed from net-GEX sign across tickers | Distribution board of ranked severity, net-GEX demoted to a state chip | This phase (CONTEXT.md D-decisions, derived from the 2026-07-22/23 monitor reframe) | Risk bar (`_render_environment_hero`'s `risk-bar` block, `app.py` lines 250-278) and the freshness banner's current full-width treatment (`_render_freshness_banner`, lines 335-364) are both explicitly slated for removal/shrinking |
| Email = always-present descriptive report (every ticker, every field, every day) | Email = event-shaped (band entries/escalations only, near-empty on quiet days) | This phase | `report.py`'s `_methodology_caveat_banner`, `methodology_footer`, `_oi_summary_table`, `_key_levels_block` calls in `build_email()` are all slated for removal per CONTEXT.md + `.planning/todos/pending/email-boilerplate-cut.md` |

**Deprecated/outdated:**
- `_render_environment_hero`'s risk-bar computation (amplifying/stabilizing count across tickers) — superseded by the distribution board; the underlying `net_gex` field itself stays (used for the state chip), only the bar/label goes.
- `report.py`'s `_methodology_caveat_banner()` + the large `methodology_footer` glossary string — superseded by a single "Methodology" link (target URL is an open question, see below).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The "Methodology" link in the remodeled email should point at the dashboard's existing in-app "Methodology & Assumptions" expander (via the Oracle-hosted public URL noted in project memory) rather than a separate hosted doc | Email event-shaping refactor plan | Low — if wrong, it's a one-line URL swap; flagged so the plan doesn't guess a URL that doesn't exist |
| A2 | A single combined plotly figure OR native sparkline columns is an acceptable v1 percentile-strip/trail rendering (CONTEXT.md leaves exact layout primitives to discretion, but this research recommends starting with native `st.dataframe` + sparkline columns over custom plotly for build-cost reasons) | Distribution-board Streamlit architecture | Low — CONTEXT.md explicitly delegates this choice; if the sparkline column reads too thin once real data accumulates, upgrading to a custom plotly strip is a contained follow-up, not a rework |

**If this table is empty:** N/A — two low-risk, discretion-scoped assumptions above; nothing here needs to become a locked decision before planning, but the planner should surface A1 as an explicit question if it isn't already answered by the time email work starts.

## Open Questions

1. **What does the single "Methodology" link in the email point to?**
   - What we know: CONTEXT.md and the email-boilerplate-cut todo both say "replace with one permanent link" but neither specifies the target.
   - What's unclear: Whether it should point at the Oracle-hosted dashboard's Methodology expander, a new standalone doc, or a vault note.
   - Recommendation: Default to the Oracle-hosted dashboard URL (already public per project memory `oracle-deploy-2026-07-14.md`) with a `#methodology`-style anchor or just the root URL — cheapest to build, single source of truth (the expander already exists in `app.py`). Flag for Adam to confirm during planning/execution rather than blocking research.

2. **Should the VRP evidence panel's IV-vs-RV legs live in `vrp_history.py` as a new function, or be recomputed inline in `app.py`?**
   - What we know: `vrp_history.vrp_history_series(ticker)` only returns the already-differenced `vi - rv*100` series; the two legs (`vi`, `rv`) are computed internally but discarded before return.
   - What's unclear: Whether to add a small `vrp_components(ticker) -> pd.DataFrame` (columns `vi`, `rv`, `vrp`) to `vrp_history.py` (single source of truth, testable, mirrors the module's existing docstring philosophy) vs. duplicating the alignment logic in `app.py`.
   - Recommendation: Add it to `vrp_history.py` — it's the same computation already happening inside `vrp_history_series`, just returning more of it. Duplicating in `app.py` would violate the module's own "the single source of truth so the scalar and its rank... share one definition" principle stated in its docstring.

## Environment Availability

Skipped — this phase has no new external dependencies (no new packages, no new services). All work is against the existing local venv, existing parquet stores, and existing Streamlit/plotly stack, already verified present (`pytest engine/tests` → 465 passed against the current `.venv`).

## Validation Architecture

Skipped per `.planning/config.json` (`workflow.nyquist_validation: false`).

## Security Domain

`security_enforcement` is absent from `.planning/config.json` (treated as enabled per protocol), but this phase has essentially no attack surface change to evaluate: it adds no authentication, no new user-writable inputs, and no new network egress — it reads existing local parquet files and renders existing computed values in an already-deployed internal Streamlit app. `st.dataframe`/`st.session_state` row-selection is client-driven UI state only (selecting which row to view), not a trust boundary. No ASVS category meaningfully applies beyond what already applies to the existing dashboard (out of scope for this phase — the dashboard's current lack of authentication on its public Oracle URL, noted only in passing here, predates this phase and is not something this phase's scope touches or should attempt to fix as a drive-by).

## Sources

### Primary (HIGH confidence)
- `engine/monitor/schema.py`, `ranker.py`, `hysteresis.py`, `monitor_store.py`, `metrics.py`, `calibration.py` — read directly, this session
- `engine/config.py` lines 245-336 — monitor constants, calibration provenance comments (dated 2026-07-24, re-run instructions included)
- `engine/tests/test_monitor/*.py` — existing test patterns to mirror (tmp_path + store param-override)
- `app.py`, `engine/report/report.py`, `engine/report/card_model.py`, `engine/surface/surface_interactive.py`, `engine/vol/vrp_history.py`, `engine/compute.py` — read directly, this session
- `out/monitor/ranks.parquet`, `out/monitor/alert_events.parquet` — queried directly on disk, this session, to establish the cold-start reality
- `.venv/Lib/site-packages/streamlit/.agents/skills/developing-with-streamlit/references/{session-state,performance,dashboards,selection-widgets,data-display}.md` — installed skill docs, read directly, this session
- `pytest engine/tests` run against the project's own `.venv/Scripts/python.exe` — confirmed 465 passed (baseline matches CONTEXT.md's stated success criterion #6)

### Secondary (MEDIUM confidence)
- None used — all findings this session were verified directly against the repo or the installed skill docs, not via web search.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Monitor-engine consumption map: HIGH — read every relevant engine file directly, queried the actual parquet stores on disk
- Row-inventory feasibility: HIGH — `METRIC_INVENTORY` and `metrics.load_metric_series` read directly; cross-checked against real stored n_deep values
- Streamlit architecture recommendations: MEDIUM — grounded in the installed skill's documented patterns, but exact layout choice is explicitly Claude's-discretion per CONTEXT.md, so this is a recommendation, not a locked finding
- Evidence-panel reuse map: HIGH for surface-evolution/diff (verbatim existing function reuse); MEDIUM for the VRP-legs and skew-smile-overlay gaps (identified precisely, but the exact function signature is a planning-time design choice)
- Email event-shaping: HIGH for what to cut (explicit in report.py + CONTEXT.md + the boilerplate-cut todo); MEDIUM for the "Methodology" link target (open question, flagged)
- Test surface: HIGH — no existing tests for `report.py`/`card_model.py` confirmed via glob; existing `test_monitor/*` patterns are a clear, directly-reusable template

**Research date:** 2026-07-26
**Valid until:** ~30 days (stable internal codebase; the main time-sensitive fact — sparse `out/monitor/` history — will itself change day by day as `run_daily.py` keeps running, which is expected and doesn't invalidate the architecture recommendations)

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
**Phase siblings:**
- [[_planning/vol-diagnostics/phases/27-microstructure-monitor-ui/27-CONTEXT|27-CONTEXT]]

<!-- LINKS:END -->
