# Architecture Research — v3.3 "Surface Evolution & Daily Intelligence"

**Domain:** integration architecture for an existing local-Python vol-diagnostics tool (gamma-omm)
**Researched:** 2026-05-29
**Confidence:** HIGH (codebase read directly; one external dependency risk verified via web)

This is an *integration* architecture doc, not a greenfield one. The codebase exists and is
clean; v3.3 must slot into it with minimal-diff respect for the established seams. Every
recommendation below names a concrete `file:function` integration point and marks **NEW** vs
**MODIFIED**.

---

## Standard Architecture (current, as read)

```
┌──────────────────────────────────────────────────────────────────────────┐
│  ENTRY POINTS                                                              │
│  run.py (legacy text)   gex.run_daily (orchestrator)   streamlit_app.py   │
└───────────────┬──────────────────────┬──────────────────────┬────────────┘
                │                       │                      │
                ▼                       ▼                      ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  SHARED COMPUTE  —  gex/compute.py :: compute_ticker(ticker) -> dict       │
│  single source of truth: summary, s_df, p_df, spot, surface_df, skew_df,   │
│  skew, term_structure, rv20, vrp                                           │
└───────────────┬──────────────────────────────────────────────────────────┘
                │ pulls from
                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  ENGINE LAYER (pure, no I/O)                                               │
│  data_loader → greeks_engine → exposure_engine → analytics(summarise)      │
│  vol_metrics (skew_25d, term_structure, rv20, vrp)                         │
└───────────────┬──────────────────────────────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  RENDER LAYER          │  PERSISTENCE LAYER       │  DELIVERY LAYER        │
│  analytics.plot_*      │  validation.py (scalar)  │  report.build_email    │
│  (plotly figures)      │  surface_history.py      │  emailer.send(         │
│                        │  (raw OTM chain parquet) │    attachments=[...])  │
└────────────────────────┴──────────────────────────┴────────────────────────┘
```

### Component Responsibilities (current + where v3.3 lands)

| Component | Responsibility | v3.3 change |
|-----------|----------------|-------------|
| `compute.py::compute_ticker` | live pipeline per ticker → dict | **MODIFIED** (Phase 8): add `surface_diag` key |
| `exposure_engine.py` | pure GEX/surface/skew math | **MODIFIED** (Phase 8): host `surface_diagnostics()` |
| `analytics.py::_rbf_grid` | (currently nested in `plot_iv_change_surface`) | **MODIFIED** (Phase 8): promote to module-level shared helper |
| `surface_history.py` | raw OTM chain parquet store + lookups | **MODIFIED** (Phase 9): add `nth_trading_day_back()` helper |
| `surface_evolution.py` | — | **NEW** (Phase 9): compute + parquet store for day-over-day deltas |
| `validation.py` | scalar snapshot store (the idempotent pattern to copy) | unchanged (reference template) |
| `run_daily.py::run` | orchestrate, persist, email | **MODIFIED** (Phase 9 + 11): evolution trigger, PNG export, attachments |
| `streamlit_app.py` | 5-tab dashboard | **MODIFIED** (Phase 10): 5→4 tabs, two new views |
| `report.py::build_email` | HTML email body | **MODIFIED** (Phase 11): richer copy, image-ref blocks |
| `emailer.py::send` | Outlook COM send, already `attachments=` capable | unchanged (already supports it) |

---

## Question-by-question integration design

### 1. Where do surface-validation diagnostics live?

**Recommendation: a pure function `surface_diagnostics()` in `exposure_engine.py`, called from
`compute.py::compute_ticker`, computed daily and persisted into the existing scalar store.**

Rationale grounded in the existing seams:

- `exposure_engine.py` already owns the comparable pure metric `compute_surface_slopes(surface_df)`
  (lines 140–180) — diagnostics are the same shape (DataFrame in, scalar dict out, no I/O). Put it
  next to its sibling, not in a new module. A new module is only warranted when there is state or
  I/O; diagnostics are stateless.
- It must be inside `compute_ticker` (not on-demand) because **both** callers need it and
  `compute_ticker` is explicitly the single source of truth (`compute.py:1-7`). Computing it there
  means Streamlit and the email get identical numbers for free.
- **Store it daily** rather than recompute on-demand. The scalar store (`validation.py`) already
  carries `strike_slope`, `term_slope` — diagnostics are the same kind of per-day scalar and belong
  in the same row. Persisting them buys you a history series (e.g. "RMS-of-fit percentile vs 30
  sessions") at zero extra cost and matches what the Skew/Term tabs already do with `front_skew`/`iv30`.

**Concrete diagnostic metrics** (cheap, defensible, computed from `surface_df` + the RBF fit):
- `surface_coverage` — fraction of the fixed grid cells backed by a real quote inside the convex
  hull (honest-holes metric; pairs with the "honest holes" decision in recent commits).
- `surface_rms` — RMS residual of the RBF fit at the raw quote points (interpolation trust metric).
- `n_expiries`, `n_points` — raw density.
- `dte_min_used`, `dte_max_used` — actual rendered range after the DTE floor/cap.

Integration points:
- **NEW** `exposure_engine.py::surface_diagnostics(surface_df, spot) -> dict` (sits beside
  `compute_surface_slopes`, line ~181).
- **MODIFIED** `compute.py::compute_ticker` — after `surface_df = vol_surface_data(...)` (line 59),
  add `surface_diag = surface_diagnostics(surface_df, snapshot.spot)`; merge into the returned dict
  and into `summary` (so it flows to `save_snapshot`).
- **MODIFIED** `validation.py::save_snapshot` + `_FLOAT_COLS` — append `surface_coverage`,
  `surface_rms` columns (forward-compatible: the header comment at lines 16–18 already guarantees
  old rows load as NaN).

> Do **not** compute diagnostics inside the plot functions. Diagnostics must exist headless (for the
> email and for the daily store) where no figure is rendered.

---

### 2. `surface_evolution.py` design

**Recommendation: NEW module that depends on `surface_history.load_surface_snapshot` for *both*
sides, reuses the promoted `analytics._rbf_grid`, is triggered inside `run_daily.run` after
`save_surface_snapshot`, and gets its "Nth trading day back" via a new helper in `surface_history.py`.**

#### Dependencies / interpolation reuse
- Today's side and the prior side both come from `load_surface_snapshot(ticker, date)` →
  `(surface_df, spot)`. **Use the stored snapshot for today too**, not the live `compute_ticker`
  result, so the evolution number is reproducible from disk and a re-run is deterministic. (Caveat:
  this requires `save_surface_snapshot` to have already run for today — hence ordering in §2 trigger.)
- **Reuse the RBF grid via the promoted shared helper** (see "_rbf_grid decision" below). Both
  `plot_vol_surface` (analytics.py:201-220) and `plot_iv_change_surface` (analytics.py:338-354)
  contain near-identical RBF-on-normalized-axes code — `surface_evolution.py` would be the *third*
  copy if not factored out. Factor it out **first** (Phase 8), depend on it here (Phase 9).

#### What the evolution engine computes
For a pair (today, prior) it interpolates both onto the shared fixed grid (intersection DTE range,
±15% OTM) and emits scalar deltas:
- `level` — mean ∆IV across the grid (parallel shift).
- `rms` — RMS of ∆IV (total surface movement magnitude).
- `skew_change` — change in the OTM-put-minus-OTM-call wing gap (front slice).
- `term_change` — change in the ATM front-minus-back spread.
- `coverage` — fraction of grid cells where *both* days had hull support (honest-holes for the diff).

These are exactly the scalars the new Streamlit "evolution time-series" view plots, and they map 1:1
to the proposed parquet schema (§3).

#### Trigger location — inside `run_daily.run`, after the persist loop
Place it as a **second pass after the ticker loop** in `run_daily.run` (after line 71, before the
email build at line 77), not inside `process_ticker`:

```python
# run_daily.run — NEW second pass, after save_snapshot/save_surface_snapshot loop
from gex.surface_evolution import update_evolution
for ticker in INDEX_TICKERS:
    if any(d["summary"]["ticker"] == ticker and not d["summary"].get("error") for d in all_data):
        update_evolution(ticker, today)   # reads today + 1d/5d/21d-back from the store, appends rows
```

Why a separate pass, not inside `process_ticker`:
- `update_evolution` depends on `save_surface_snapshot` having committed *today's* rows first. A
  separate pass after the loop guarantees the whole store is current.
- `process_ticker` is wrapped in "never raises" error handling (run_daily.py:40-46). Evolution is a
  derived, non-blocking step — wrap its own pass in the same try/except-and-print idiom used for the
  observation log (run_daily.py:96-101) so a parquet hiccup never blocks the email.

#### "Nth trading day back" lookup
`list_available_dates(ticker)` already returns dates **descending** (surface_history.py:82-92). The
horizon lookup is "walk N positions down the available-dates list" — *not* calendar arithmetic —
because the store only contains trading days that actually ran. Add a small helper:

- **NEW** `surface_history.py::nth_trading_day_back(ticker, anchor_date, n) -> date | None`
  — find `anchor_date` in `list_available_dates`, return the date `n` positions later in the
  descending list (i.e. `n` snapshots earlier in time). Returns `None` if fewer than `n+1` snapshots
  exist (cold-start safe).

Horizons to compute: 1 (prior session), 5 (~1 week), 21 (~1 month). Store missing horizons as absent
rows, not NaN rows — keeps the store honest about what was actually computable.

---

### 3. New parquet store: `out/surface_evolution.parquet`

**Recommendation: copy `validation.py`'s exact idempotent pattern, not `surface_history.py`'s.**
The two stores differ: `surface_history` replaces *all of today's rows*; `validation` replaces a
single `(date, ticker)` row. Evolution wants per-`(date, ticker, horizon)` idempotency, which is the
`validation` pattern with one extra key.

Schema (one row per `date × ticker × horizon`):

| Column | Type | Meaning |
|--------|------|---------|
| `date` | date | the "today" anchor of the comparison |
| `ticker` | str | SPY/QQQ/IWM |
| `horizon` | int | trading-days-back (1, 5, 21) |
| `prior_date` | date | the resolved snapshot date `horizon` sessions back |
| `level` | float | mean ∆IV (pp) |
| `rms` | float | RMS ∆IV (pp) |
| `skew_change` | float | change in wing gap (pp) |
| `term_change` | float | change in front-minus-back ATM spread (pp) |
| `coverage` | float | fraction of grid cells with both-day hull support |

Idempotent write (mirrors `validation.save_snapshot:67-79`, with a 3-key mask):

```python
mask = (hist["date"] == row["date"]) & (hist["ticker"] == ticker) & (hist["horizon"] == horizon)
hist = hist[~mask]
hist = pd.concat([hist, pd.DataFrame([row])], ignore_index=True)
```

- Single flat parquet at `out/surface_evolution.parquet` (matches `gex_snapshots.parquet`), **not**
  per-ticker files (that pattern is `surface_history`'s, justified there only by row volume — raw
  chain points. Evolution is ~3 rows/day/ticker, trivially small).
- Keep a `_FLOAT_COLS` cast block (validation.py:69-71) so re-reads coerce dtypes and old rows with
  missing future columns load as NaN.
- Provide `load_evolution(ticker, horizon=None, days=...)` mirroring `load_history` for the dashboard.

---

### 4. PNG export flow for the email

**Recommendation: render the per-ticker surface figures to `out/` PNGs via kaleido inside
`run_daily.run`, just before the email build, and pass the paths to `emailer.send(attachments=...)`.
`emailer.send` already accepts `attachments: list[Path]` (emailer.py:20, 45-47) — zero change there.**

⚠️ **Dependency risk — verify in Phase 11 before committing to embedding.** This venv runs
**plotly 6.7.0 with no kaleido installed.** Kaleido v1 (the version pip will pull for plotly 6.x)
**no longer bundles Chrome** — it requires a system Chrome/Chromium — and there are open reports of
`write_image` failing on Windows 10 with plotly 6.3+ regardless of kaleido version. This is the single
highest-risk integration point in v3.3. Mitigations, in order of preference:
1. Install kaleido, confirm a system Chrome is present, smoke-test `fig.write_image()` on one surface
   on this exact machine **first** (spike at the top of Phase 11).
2. If kaleido export is flaky, fall back to **attaching the existing self-contained HTML**
   (`run_daily` already writes `gex_{date}.html` on dry-run, lines 84-85) rather than inline PNGs —
   the email already renders cards as HTML; surfaces can be a linked/attached HTML artifact.
3. Pin `kaleido` and `plotly` together in `requirements.txt` once a working pair is confirmed.

Integration points (assuming the spike passes):
- **NEW** `analytics.py::save_fig_png(fig, path, scale=2)` — thin wrapper over `fig.write_image`
  (or the kaleido-v1 `write_fig`) so the API choice lives in one place and the rest of the codebase
  is export-API-agnostic (same philosophy as the Bloomberg swap isolation in `data_loader`).
- **MODIFIED** `run_daily.run` — after the persist loop, before `rpt.build_email` (between lines 71
  and 77): for each good ticker, build the surface fig (`plot_vol_surface`) and the ∆IV fig
  (`plot_iv_change_surface` vs 1-day-back), save to `OUT_DIR / f"surface_{ticker}_{date}.png"`,
  collect paths.
- **MODIFIED** `emailer.send` call (run_daily.py:90) — pass `attachments=png_paths`. Optionally embed
  with `cid:` references in `report.build_email` (requires setting `Attachment.PropertyAccessor`
  content-id on the COM attachment — defer to a stretch goal; plain attachments work day one).
- Guard the whole PNG block in try/except-and-print (non-blocking, like the observation log) so an
  export failure never stops the email from sending the HTML cards.

---

### 5. Streamlit restructure — minimal-diff path

Current tabs (streamlit_app.py:227-229): `Surface | Skew | Term Structure | Flow Context`.
Target: `Surface | Skew & Term | Evolution | Flow Context` (merge Skew+Term, drop Carry — note:
"Carry" content currently lives *inside* the Term Structure tab as `plot_carry_vrp`, lines 449-462,
there is no standalone Carry tab. Confirm intent with the milestone owner: the minimal read is "remove
the VRP/carry chart block from the merged tab.")

Minimal-diff sequence:
1. **Tab declaration (line 227-229):** change to four tabs:
   `tab_surface, tab_skew_term, tab_evolution, tab_flow = st.tabs(["Surface", "Skew & Term", "Surface Evolution", "Flow Context"])`.
2. **Merge Skew+Term:** move the body of `with tab_term:` (lines 400-462) to run *below* the existing
   `with tab_skew:` body inside the renamed `with tab_skew_term:`. Both already iterate
   `loaded_tickers` in per-ticker columns — keep them as two stacked `st.divider()`-separated
   sections rather than re-weaving the column loops (smaller diff, no logic churn).
3. **Remove Carry:** delete the `plot_carry_vrp` block (lines 449-462) and its import
   (analytics import list, line 16). `plot_carry_vrp` in analytics.py can stay defined but unused, or
   be deleted in the same commit (per global prefs: delete cleanly, no dead re-exports).
4. **NEW Evolution tab** (`with tab_evolution:`): two views.
   - **Stored-vs-stored compare:** generalize the existing `sub_change` block (lines 250-291). Today
     it compares *live today* vs a stored prior. The new view adds a **second selectbox for the
     "today" side**, both sourced from `load_surface_snapshot`, so any two stored dates can be
     differenced. This reuses `plot_iv_change_surface` verbatim — no new chart needed.
   - **Evolution time-series:** read `out/surface_evolution.parquet` via the new
     `load_evolution(ticker, horizon=1)` and plot `level`/`rms`/`skew_change` as a line series
     (same `go.Scatter` + `plotly_dark` idiom as the skew-history chart at lines 374-395). Add a
     horizon selectbox (1/5/21).
5. **Caching:** wrap `load_evolution` in an `@st.cache_data(ttl=config.CACHE_TTL_HISTORY)` helper
   beside `_load_history_cached` (lines 116-119) — same pattern, parquet is append-once-daily.

---

## The `_rbf_grid` shared-helper decision (quality-gate item)

**Verdict: factor it out. This is a real smell and v3.3 makes it worse if ignored.**

There are currently **two** copies of "RBF thin-plate-spline on std-normalized (DTE, %OTM) axes,
clipped ≥0":
- `analytics.plot_vol_surface` lines 201–220 (inline).
- `analytics.plot_iv_change_surface` lines 338–354 (nested function literally named `_rbf_grid`).

`surface_evolution.py` (Phase 9) needs the identical computation. Without extraction it becomes the
**third** copy — and the three would silently drift (one uses `smoothing=1.5`, another could be
tweaked during tuning, and the surface and the evolution number would then disagree).

**Extraction:**
- **NEW** module-level `analytics.py::rbf_grid(surface_df, spot, dte_grid, otm_grid, *, dte_floor=5, clip_pct=...)` — the body of the existing nested `_rbf_grid` (analytics.py:338-354), promoted and
  parameterized. Returns the interpolated `IV` array (NaN-filled when <6 points).
- **MODIFIED** `plot_vol_surface` and `plot_iv_change_surface` both call `rbf_grid`. This shrinks
  `plot_vol_surface` by ~20 lines and removes the duplication.
- Do this in **Phase 8** (validation foundation) so the diagnostics RMS metric and the evolution
  engine both build on one interpolation definition. This is the single most leveraged refactor in
  v3.3 — it touches three consumers and prevents a class of drift bugs.

> Constraint check against global prefs ("small diffs, no pre-emptive abstraction"): this abstraction
> is *not* pre-emptive — it has three concrete consumers the moment v3.3 lands, and one already
> exists. Extraction is the smaller long-term diff. Approved.

---

## Data Flow (v3.3)

### Daily run (`run_daily.run`)
```
for ticker:
  compute_ticker(ticker)                # now includes surface_diag
    → save_snapshot(summary)            # now writes surface_coverage, surface_rms
    → save_surface_snapshot(surface_df) # unchanged
─── second pass (NEW) ───
for ticker:
  update_evolution(ticker, today)       # reads store: today + nth_trading_day_back(1,5,21)
    → reuse analytics.rbf_grid on both sides
    → append rows to out/surface_evolution.parquet  (idempotent on date×ticker×horizon)
─── render (NEW) ───
for ticker: save_fig_png(plot_vol_surface / plot_iv_change_surface) → out/*.png
build_email(...)  → emailer.send(attachments=png_paths)
```

### Streamlit (`compute_ticker` live + parquet reads)
```
fetch_ticker(ticker)  → surface_df, skew, term_structure, surface_diag (live)
load_surface_snapshot(ticker, date) ×2  → stored-vs-stored ∆IV compare (rbf_grid)
load_evolution(ticker, horizon)         → evolution time-series chart
load_history(ticker)                    → unchanged (skew/iv30/zgl history)
```

---

## Anti-Patterns to avoid (v3.3-specific)

### Anti-Pattern 1: computing diagnostics inside plot functions
**Mistake:** putting `surface_rms`/`coverage` logic inside `plot_vol_surface`.
**Why wrong:** the email and the daily store need these headless, with no figure rendered.
**Instead:** pure `exposure_engine.surface_diagnostics()`, called in `compute_ticker`.

### Anti-Pattern 2: a third copy of the RBF code
**Mistake:** copy-pasting the RBF block into `surface_evolution.py`.
**Why wrong:** three definitions drift; surface render and evolution number disagree.
**Instead:** one `analytics.rbf_grid`, three consumers.

### Anti-Pattern 3: calendar arithmetic for "N days back"
**Mistake:** `today - timedelta(days=N)` to find the prior snapshot.
**Why wrong:** the store only holds trading days that actually ran (holidays, missed runs, cold
start). Calendar math will miss or mis-key snapshots.
**Instead:** index into the descending `list_available_dates` via `nth_trading_day_back`.

### Anti-Pattern 4: blocking the email on a derived step
**Mistake:** letting `update_evolution` or PNG export raise and abort `run_daily.run`.
**Why wrong:** the email (the actual deliverable) is gated on a non-essential parquet/Chrome step.
**Instead:** wrap each derived pass in try/except-and-print, matching the observation-log idiom
(run_daily.py:96-101).

### Anti-Pattern 5: live-today vs stored-prior asymmetry in the evolution store
**Mistake:** computing the stored evolution number from live `compute_ticker` for the "today" side.
**Why wrong:** the daily-stored number won't reproduce on a re-run (live quotes drift intraday).
**Instead:** evolution engine reads *both* sides from `surface_history` after today's snapshot is
committed — deterministic and reproducible. (The Streamlit "Today (live)" compare view may still use
live today; that's a UI convenience, kept out of the persisted store.)

---

## Integration Points summary table

| Boundary | NEW / MODIFIED | File:function |
|----------|----------------|---------------|
| diagnostics math | NEW | `exposure_engine.py::surface_diagnostics` |
| diagnostics into pipeline | MODIFIED | `compute.py::compute_ticker` (after line 59) |
| diagnostics persisted | MODIFIED | `validation.py::save_snapshot` + `_FLOAT_COLS` |
| RBF shared helper | NEW (extract) | `analytics.py::rbf_grid` (from lines 338-354) |
| RBF consumers updated | MODIFIED | `analytics.py::plot_vol_surface`, `plot_iv_change_surface` |
| Nth-day lookup | NEW | `surface_history.py::nth_trading_day_back` |
| evolution engine | NEW module | `surface_evolution.py::update_evolution`, `load_evolution` |
| evolution store | NEW | `out/surface_evolution.parquet` (validation.py idempotent pattern) |
| evolution trigger | MODIFIED | `run_daily.py::run` (NEW second pass after line 71) |
| PNG export wrapper | NEW | `analytics.py::save_fig_png` |
| PNG export call | MODIFIED | `run_daily.py::run` (before line 77) |
| email attachments | MODIFIED (call only) | `run_daily.py::run` line 90 — `emailer.send` already supports it |
| dashboard restructure | MODIFIED | `streamlit_app.py:227-462` |
| evolution cache helper | NEW | `streamlit_app.py` (beside `_load_history_cached`, line 116) |
| dependency | NEW | `requirements.txt` — `kaleido` (pin after Phase 11 spike) |

---

## Build order (dependency-ordered, maps to phases 8–11)

The foundation-first gate holds: nothing downstream can compute a trustworthy delta until the
interpolation is unified and diagnostics exist.

### Phase 8 — Validation foundation
1. **Extract `analytics.rbf_grid`** (the leverage move — unblocks everything that interpolates).
   Update both existing plot consumers; visual output must be unchanged (regression check the surface
   renders identically).
2. **`exposure_engine.surface_diagnostics`** + wire into `compute_ticker` + persist via
   `save_snapshot` (new columns).
3. Surface a diagnostics readout in Streamlit (small — a caption/metric under the surface) so the
   foundation is observable before evolution depends on it.

*Gate: rbf_grid is the single interpolation definition; diagnostics flow to the store. Only then →*

### Phase 9 — Evolution engine
4. **`surface_history.nth_trading_day_back`** (pure lookup, unit-testable in isolation).
5. **`surface_evolution.py`** — `update_evolution` (reads store both sides, uses `rbf_grid`,
   writes idempotent rows) + `load_evolution`.
6. **Wire trigger** into `run_daily.run` as a non-blocking second pass.

*Gate: a few days of `run_daily` (or backfilled from existing `surface_history`) populate the
evolution parquet. Only then does the dashboard have a time-series to plot →*

### Phase 10 — Dashboard restructure
7. 5→4 tabs; merge Skew+Term; remove Carry.
8. Stored-vs-stored compare (generalize `sub_change`).
9. Evolution time-series view (reads `load_evolution`).

### Phase 11 — Richer report
10. **Spike first:** confirm kaleido + system Chrome `write_image` works on this Windows machine.
    Decide PNG-embed vs HTML-attach based on the result.
11. `analytics.save_fig_png`; PNG render loop in `run_daily.run`; attachments wired into
    `emailer.send`; richer `report.build_email` copy (evolution callouts, diagnostics footnote).

> Why this order respects dependencies: Phase 9 reuses Phase 8's `rbf_grid`; Phase 10 reads Phase 9's
> store; Phase 11's report can surface diagnostics (Phase 8) and evolution (Phase 9). A `Backfill`
> sub-task can be slotted at the start of Phase 9/10 to retro-compute evolution from the existing
> `surface_history` parquet, so the dashboard isn't empty on day one (cold-start mitigation).

---

## Sources

- Codebase (read directly, 2026-05-29): `gex/compute.py`, `gex/run_daily.py`,
  `gex/surface_history.py`, `gex/validation.py`, `gex/analytics.py`, `gex/exposure_engine.py`,
  `gex/vol_metrics.py`, `gex/report.py`, `gex/emailer.py`, `gex/config.py`, `streamlit_app.py`,
  `requirements.txt` — HIGH confidence (primary source).
- Local env probe: `plotly 6.7.0`, `kaleido` not installed — HIGH confidence (direct).
- [Static image generation changes in plotly.py 6.1](https://plotly.com/python/static-image-generation-changes/) — kaleido v1 API, Chrome dependency — MEDIUM.
- [plotly/Kaleido issue #402 — write_image fails on Windows 10, plotly 6.3+](https://github.com/plotly/Kaleido/issues/402) — Windows export risk — MEDIUM (single-issue, but corroborated by #443).
- [kaleido on PyPI](https://pypi.org/project/kaleido/) — version landscape — MEDIUM.

---
*Architecture research for: gamma-omm v3.3 integration*
*Researched: 2026-05-29*

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
