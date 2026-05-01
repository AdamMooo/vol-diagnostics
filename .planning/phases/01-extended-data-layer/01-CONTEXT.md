# Phase 1: Extended Data Layer - Context

**Gathered:** 2026-04-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the v2.0 data foundation in `sleeve_alpha.ipynb`: pull SPX/QQQ (and probe XIU/XSP) prices + 30D ATM IV + 30D 90%-moneyness IV, plus VIX, VVIX, and a 3M risk-free proxy via `con.bdh` (`emds_client`). Reindex everything onto a canonical NYSE trading-day index. Expose three named wide DataFrames — `prices_panel`, `iv_panel`, `skew_panel` — plus standalone `vix`, `vvix`, `rf_rate` Series. Snapshot pulls to a server-side parquet cache so kernel restarts don't re-hit the data server. Print a freshness/QA table; warn (don't raise) on stale data.

Out of phase scope: signals (RV/VRP/skew/term/trend/drawdown — Phase 2), sleeve P&L (Phase 3), scoring (Phase 4). Phase 1 ships only validated, aligned, cached input panels.

</domain>

<decisions>
## Implementation Decisions

### Universe rollout
- **D-01:** Probe all four underlyings (SPX, QQQ, XIU, XSP) in one pull block. SPX and QQQ are required; XIU and XSP are best-effort.
- **D-02:** On `con.bdh` returning empty/sparse data for an optional underlying or field, log the field tried, the row count returned, and a `"deferred — not in panel"` line. Cell stays green; downstream code branches on panel column membership, not on assumptions about which underlyings landed.
- **D-03:** Beyond the locked-in 30D ATM IV + 30D 90%-mny IV + VIX + 3M risk-free, also probe **90D ATM IV** (`90DAY_IMPVOL_100.0%MNY_DF` — pulls forward the term-structure todo from STATE.md) and **VVIX** (cheap one-line addition; optional fragility-composite input). 60D IV and 110%-mny skew leg deferred to Phase 2 unless trivially available.
- **D-04:** History truncated to the shortest IV history per underlying. Loses pre-IV price history; in exchange the panel is dense and signals/sleeves never NaN-fill across an "IV unavailable" boundary. (SIG-04 12m trend will run on the same truncated window — acceptable since sleeve P&L can't price pre-IV anyway.)

### Panel data structure
- **D-05:** Three wide DataFrames per measure — `prices_panel`, `iv_panel`, `skew_panel` — each with the canonical NYSE date index and one column per underlying that landed (SPX, QQQ, and any of XIU/XSP that probed clean). Names match REQUIREMENTS.md verbatim.
- **D-06:** `skew_panel` is computed as `iv90_panel - iv_panel` (90%-mny minus 100%-mny). The intermediate `iv90_panel` is kept as a module-level variable for QA reference but is not one of the three canonical handoff panels.
- **D-07:** Cross-asset / single-series fields live as standalone date-indexed Series alongside the panels: `vix`, `vvix`, `rf_rate`. Not bolted onto `prices_panel` (VIX is not a price) and not wrapped in a fourth panel.
- **D-08:** No imputation. Reindex each pulled series to the canonical NYSE index and leave NaN where the source had no observation. The QA cell prints missingness %; signals/sleeves handle NaN explicitly downstream.

### Multi-calendar alignment
- **D-09:** Canonical index = NYSE trading days (`pandas_market_calendars` NYSE schedule). XIU and XSP get reindexed to NYSE — TSX-only holidays (Family Day, Victoria Day, Canada Day, Civic Holiday) become NaN for those columns; NYSE-only holidays (MLK, Presidents', Thanksgiving Friday) drop entirely from the panel.
- **D-10:** Rationale: the overlay menu (PDIV, SPX/QQQ-anchored sleeves) is US-led; aligning to NYSE keeps signal cadence consistent with the dominant exposure. ~5 NaN days/yr per Canadian underlying is a documented, tolerable cost. If the universe ever flips Canada-led, revisit and consider intersection or union calendars.

### Caching / re-pull
- **D-11:** Parquet cache with freshness toggle. On import, `con.bdh` writes one parquet file per (underlying × field) keyed by date range. On reload, check parquet `mtime`: if older than 1 trading day, re-pull; else load from disk. Explicit `force_refresh=True` argument bypasses the cache.
- **D-12:** Cache lives in a server-side folder **outside the repo** (no GitHub commits). Specific path captured as a top-of-notebook config variable (`CACHE_DIR = pathlib.Path(...)`) so a user can override per-server. Reasonable default: `pathlib.Path.home() / "sleeve_alpha_cache"`. Files are parquet, small, server-local.
- **D-13:** DATA-11 freshness check: print a small DataFrame `[underlying, field, last_bar_date, days_stale, status]` covering every series in the canonical panels. If any `days_stale > 5`, also call `warnings.warn(...)` so it surfaces at the bottom of the Setup section. Do NOT raise — weekend / holiday refresh runs would otherwise block.

### Claude's Discretion
- Exact `con.bdh` field-probe order and the loop / dict-comprehension shape that drives it
- Log message format for deferred fields (just needs to identify the field, the underlying, and the reason)
- Cache key format and parquet schema (per-pull vs concatenated)
- QA cell layout beyond the freshness table — `n` per underlying, missingness %, first/last bar dates per panel, all reasonable
- Cell breaks and markdown headings within Section 1 of `sleeve_alpha.ipynb`
- Colour palette / figure scaffolding (Phase 5 polishes; Phase 1 just needs readable diagnostics)
- Whether risk-free uses `USGG3M Index PX_LAST` or another 3M T-bill proxy field — pick whatever returns clean data via `con.bdh`; document the chosen field in a Setup-cell comment

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project constraints
- `CLAUDE.md` (project root) — Cron2-only runtime, locked Python env (no `hmmlearn`, no `arch`), Windows paths via pathlib, `sleeve_alpha.ipynb` is the v2.0 deliverable, `hmm.ipynb` untouched
- `.planning/PROJECT.md` — v2.0 vision, working `con.bdh` field names (`30DAY_IMPVOL_100.0%MNY_DF`, `30DAY_IMPVOL_90.0%MNY_DF`), strategy menu, out-of-scope list
- `.planning/REQUIREMENTS.md` — DATA-06 through DATA-12 are the acceptance criteria for this phase
- `.planning/STATE.md` — Pending todos: probe XIU/XSP availability, probe 90D IV (both folded into D-03)

### Data pull syntax
- `Data.ipynb` (project root) — Reference for ORM / `emds_client` / `con.bdh` call patterns. **Planner must read this before writing the data-pull cells.** Field-naming convention is Bloomberg-flavoured but not raw Bloomberg.

### Prior-art
- `.planning/phases-archive/v1.0-hmm/01-data-layer/01-CONTEXT.md` — v1.0 data layer (single-fund, Django ORM + S&P 500 benchmark). Inner-join + log-returns pattern superseded by v2.0's NYSE-canonical reindex with NaN. Useful as a syntactic reference for the Django ORM call.
- `NOTES-from-regime-detection.md` §7 (Causality discipline) and §10 (Data-pipeline gotchas) — applicable to QA cell design (`.squeeze()` after pandas ops; expanding-window not full-sample; trailing windows not centred). §12 file list is for Phase γ if it ever runs.

### Field-naming gotcha (memory)
- `IVOL_DELTA_25_PUT` does **not** work on `emds_client`. Skew is computed as `iv90 - iv100`, not via delta-based fields. (Memory: `project_v2_pivot.md`.)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Data.ipynb` — ground truth for `con.bdh` call signature and Django ORM queryset patterns on Cron2. Not imported (notebook), but its cells should be copied/adapted into Section 1 of `sleeve_alpha.ipynb`.
- `pandas_market_calendars` is in the locked env — use `mcal.get_calendar("NYSE").schedule(start, end).index.normalize()` for the canonical date index.
- `numba` and `TA-Lib` are in the locked env. Phase 1 unlikely to need either, but available for Phase 2 signal work.

### Established Patterns
- v1.0 (`hmm.ipynb`): inner-join on dates, log returns, `.squeeze()` defensively after pandas ops that may return Series-or-DataFrame. v2.0 swaps inner-join → NYSE-canonical reindex; `.squeeze()` discipline carries over.
- Project conventions: parquet snapshots per refresh date, `random_state=42` everywhere reproducibility matters, pathlib for all paths.

### Integration Points
- **Output to Phase 2:** Three wide DataFrames (`prices_panel`, `iv_panel`, `skew_panel`) on a NYSE-canonical date index, plus `vix`, `vvix`, `rf_rate` Series. Optional `iv90_panel` available for term-structure work.
- **Output to Phase 3:** Same panels + risk-free Series (BS pricer needs `r`); sleeve P&L uses prices, ATM IV, 90%-mny IV.
- **Output to operators:** Freshness/QA table printed at end of Section 1; parquet cache written to `CACHE_DIR` (server-local, gitignored / outside repo).

</code_context>

<specifics>
## Specific Ideas

- The phase produces **three** named panels by name (`prices_panel`, `iv_panel`, `skew_panel`) — this matches REQUIREMENTS.md DATA-12 exactly. Don't rename.
- VVIX gets pulled in Phase 1 even though SIG-06 doesn't strictly require it — it's free while we're already in `con.bdh`, and Phase γ may want it.
- "Probe and document" (DATA-07) is satisfied by the log-and-defer behavior in D-02 — the deferral message itself is the documentation.
- Cache invalidation rule (mtime > 1 trading day) is deliberately conservative — refreshing once per session during dev is fine; the goal is to avoid hitting `con.bdh` on every kernel restart.
- The QA cell's freshness warning is the single most-PM-relevant Phase 1 output. Make it visible.

</specifics>

<deferred>
## Deferred Ideas

### Out of Phase 1 scope
- **60D ATM IV** — Mid-tenor term-structure. Probe in Phase 2 if 30D vs 90D feels coarse.
- **110%-moneyness skew leg** — Useful for collar pricing in Phase 3 (upside skew). Pull only if trivially available; otherwise Phase 3 prices the upside leg from a parametric skew assumption.
- **TSX-canonical / intersection / union calendar variants** — If the universe ever pivots Canada-led, revisit D-09. Today's US-led overlay menu makes NYSE-canonical the right call.
- **Snapshot-per-refresh-date parquet outputs** (the dated, immutable kind for SLV-07/OUT-05) — distinct from the working cache. Phase 5 owns the dated snapshots. Phase 1 only owns the kernel-restart cache.
- **Risk-free rate by region** (Canadian T-bill for XIU/XSP option pricing) — not on the v2.0 menu. US 3M T-bill is used universally for BS pricing; option price misspecification on XIU/XSP from currency-of-funding mismatch is acknowledged and accepted.

### Reviewed Todos (carried into scope)
- **Probe XIU/XSP IV field availability during Phase 1** (STATE.md) — folded into D-01 / D-02.
- **Probe 90DAY ATM IV for term structure during Phase 1** (STATE.md) — folded into D-03.

### Reviewed Todos (deferred)
- **Capture PDIV's current overlay rule** (STATE.md) — Phase 7/β prerequisite, not Phase 1 work. Stays open.

</deferred>

---

*Phase: 01-extended-data-layer*
*Context gathered: 2026-04-30*
