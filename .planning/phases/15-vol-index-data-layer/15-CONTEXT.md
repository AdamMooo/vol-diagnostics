# Phase 15: Vol-Index Data Layer - Context

**Gathered:** 2026-06-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver one isolated, Bloomberg-swappable module that fetches, parses, and caches CBOE vol-index daily history (VIX/VXN/RVX + VIX9D/VIX3M) from the free `cdn.cboe.com` CSV endpoints. Downstream VRP (Phase 16) and term-structure (Phase 17) code calls this module and never touches a data source directly.

**In scope:** fetching, parsing, caching, and a clean `load_vol_index(symbol)` accessor. Realized-vol underlying closes stay on the existing yfinance path (`compute.py` `_fetch_spot_history_yf`) — not this module's job.
**Out of scope:** computing VRP or term ratios (Phases 16/17), any UI, any single-name symbols.

</domain>

<decisions>
## Implementation Decisions

### Symbol Scope
- **D-01:** Default symbol set is exactly the 5 needed: **VIX, VXN, RVX, VIX9D, VIX3M**. Do NOT pull the broader catalog (VIX6M/VIX1Y/SKEW/VVIX) — that's the flashy-breadth trap; add later as config if a decision needs them.
- **D-02:** The fetcher is **symbol-agnostic** — `load_vol_index(symbol)` works for any CBOE vol-index symbol on the `{SYM}_History.csv` pattern. The default set is configuration, not hardcoded logic. (This lets Phase 17 probe VXN/RVX term siblings without new fetch code.)

### Cache Storage + Freshness
- **D-03:** Persist each symbol's history as **parquet under `out/vol_index/{SYM}.parquet`**, mirroring the existing `out/gex_snapshots.parquet` / `out/surface_history/` store pattern. Files have homes; survives restarts; one obvious refresh point.
- **D-04:** **Refresh once per day** (CBOE CSVs update EOD) — aligned with the `run_daily` cadence. Layer `st.cache_data` on top for the live dashboard (mirrors `fetch_ticker` / `CACHE_TTL_*` in `streamlit_app.py`).

### History Depth
- **D-05:** Keep **full CSV history** (VIX → 1990 ~9200 rows; VXN/RVX → 2009 ~4200 rows). Storage is trivial and it lets Phase 16 offer 1yr/3yr/5yr/full percentile lookbacks without re-fetching.

### Claude's Discretion
- Exact module name/location (suggest `gex/vol_index.py` mirroring `data_loader.py`), function signatures, CSV column normalization, the on-disk parquet schema, and error/retry handling — planner/executor decide. One guard worth honoring: a symbol that 403s (e.g. VXST is discontinued) must fail soft, not crash the batch.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & requirements
- `.planning/ROADMAP.md` § "Phase 15: Vol-Index Data Layer" — goal + success criteria
- `.planning/REQUIREMENTS.md` § VIDX-01, VIDX-02 — the two requirements this phase satisfies

### Patterns to mirror (existing code)
- `gex/data_loader.py` — the CBOE-fetch + dataclass-return pattern this module mirrors; Bloomberg-swap path documented in `CLAUDE.md`
- `gex/validation.py` — `save_snapshot()` / `load_history()` parquet store conventions
- `gex/surface_history.py` — per-key parquet store (`out/surface_history/`), the closest analog to `out/vol_index/`
- `gex/config.py` § `CACHE_TTL_*` — TTL constants for the `st.cache_data` layer
- `CLAUDE.md` § "GEX Module" — data-source-agnostic / Bloomberg-swap architecture note

### Verified data endpoints (live 2026-06-04, HTTP 200, no auth)
- Vol indices: `https://cdn.cboe.com/api/global/us_indices/daily_prices/{SYM}_History.csv` (columns: DATE,OPEN,HIGH,LOW,CLOSE)
- Confirmed-existing for the 5: VIX (1990), VXN (2009), RVX (2009), VIX9D (2011), VIX3M (2009). VXST → 403 (discontinued; example of the fail-soft case).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `gex/data_loader.py`: `requests` fetch + `_HEADERS` user-agent + dataclass return — copy the shape for vol-index CSV fetching.
- `gex/surface_history.py`: `_store_path(ticker)` + parquet read/write + `list_available_dates` — direct template for an `out/vol_index/` per-symbol store.
- `streamlit_app.py`: `@st.cache_data(ttl=config.CACHE_TTL_*)` wrappers — the in-memory layer to put over the parquet store for the live app.

### Established Patterns
- Stores live under `out/` as parquet, refreshed by the daily orchestrator (`run_daily`); the app reads through `st.cache_data`. Vol-index store follows this exactly.
- Data-source isolation: everything downstream is source-agnostic so a Bloomberg swap touches one module (`CLAUDE.md`). VIDX-02 extends that contract to vol indices.

### Integration Points
- Phase 16 (VRP) and Phase 17 (term structure) import `load_vol_index(symbol)` — they are the only consumers.
- `run_daily` / `run_daily_yield` gain a daily vol-index refresh call (cheap; 5 small CSVs).

</code_context>

<specifics>
## Specific Ideas

- Constraint that shapes Phase 16 (note for downstream, not this phase's work): VRP percentile must rank the **vol-index series against itself** — never mix the CBOE-snapshot IV30 into the history (VRP-03). The data layer should therefore expose the raw vol-index close series cleanly so Phase 16 can build a self-consistent VRP history.
- Term structure (Phase 17) is SPY-rich (VIX9D/VIX/VIX3M); QQQ/IWM likely only have the 30-day level — the symbol-agnostic fetcher (D-02) lets Phase 17 probe whether VXN/RVX siblings exist without touching this module.

</specifics>

<deferred>
## Deferred Ideas

- **Broader vol-index catalog** (VIX6M, VIX1Y, SKEW, VVIX) — fetchable via the same module by config, but out of scope now (noise until a feature needs them). Re-add when a decision calls for it.
- **Cross-asset vol indices** (OVX/GVZ/VXTLT/etc.) and **put/call ratio archives** — verified-free but out of scope per the v3.5 "index-overlay decision only" boundary.
- **Single-name historical IV** — no free source; blocked, see REQUIREMENTS.md Out of Scope.

None of these belong in Phase 15.

</deferred>

---

*Phase: 15-vol-index-data-layer*
*Context gathered: 2026-06-04*

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
