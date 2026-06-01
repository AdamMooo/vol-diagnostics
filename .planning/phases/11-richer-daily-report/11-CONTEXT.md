# Phase 11: Richer Daily Report - Context

**Gathered:** 2026-05-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Upgrade the daily email from plain per-ticker HTML tables into a richer, formal report by:

1. **PNG attachments** — 4 images (3 × vol surface SPY/QQQ/IWM + 1 × SPY ΔIV surface) via `kaleido>=1.0,<2.0`, pinned camera, smoke-test spike first, skip+note fallback if kaleido fails.
2. **Evolution narrative** — a cross-ticker "Surface Evolution (5d)" section at the TOP of the email (above ticker cards), leading the report as a compact table (SPY/QQQ/IWM × level/rms/skew_change/term_change), omitted entirely on cold start.
3. **OI in each card** — "OI Call Wall" and "OI Put Wall" rows (max call-OI / max put-OI strikes) added to each per-ticker card's right column. Text-only, no new PNG pass. Computed from chain data and added to the summary dict in `compute_ticker()`.
4. **Email theme** — explicit white background (#ffffff), current sign colors and amber accent bar retained, no outer wrapper.

No new vol computation, no new signals, no new chart types beyond the existing `plot_vol_surface` / `plot_iv_change_surface`. Phase 11 wires what Phase 10 made headless into the email delivery.

**Email is currently sending.** Every change must preserve the existing email flow — new capabilities are additive.
</domain>

<decisions>
## Implementation Decisions

### Email Theme (RPT-04)
- **D-01:** Set an explicit `background:#ffffff` on the `<body>` tag. The current email inherits the client theme (no body background); adding an explicit white ensures the email is always rendered on a white background regardless of email-client dark-mode settings. Clean business document.
- **D-02:** Keep all current sign colors unchanged — `config.PALETTE["positive"]` (green), `config.PALETTE["negative"]` (red), amber accent bar. Zero code change needed; tokens already shared via `gex/config.py`.
- **D-03:** No outer gray wrapper. Keep the existing centered-720px layout with white body.

### PNG Attachment Scope (RPT-01, RPT-02)
- **D-04:** 4 PNG attachments per email: 3 × 3D vol surface (SPY, QQQ, IWM — `plot_vol_surface()`) + 1 × SPY ΔIV surface (`plot_iv_change_surface()`). Camera angle pinned (Claude's discretion for specific azimuth/elevation — a readable isometric-style 3D view). Phase opens with a kaleido smoke-test spike before embedding is committed.
- **D-05:** kaleido failure fallback: skip all attachments, add a single inline note in the email body ("Surface charts unavailable — kaleido not installed or PNG export failed."). Non-blocking: the email always sends. Logged to stdout.
- **D-06:** ΔIV surface baseline is **live vs 5-day rolling-mean** (same as evolution narrative lead, same as Streamlit dashboard default). 1-day excluded — same hazard as the retired vs-yesterday badge.

### OI in the Report (RPT-03)
- **D-07:** OI represented as two data rows in each per-ticker card: **"OI Call Wall"** (max call-OI strike + % from spot) and **"OI Put Wall"** (max put-OI strike + % from spot). Text-only — no additional kaleido pass, no new attachments. Assumption-free: just the strike with the largest call or put open interest, no dealer model required.
- **D-08:** `oi_call_wall` and `oi_put_wall` computed and added to the summary dict inside `compute_ticker()`. Follows the single-source-of-truth pattern — dashboard and email both read from the same dict.
- **D-09 (Claude's discretion):** OI rows placed **below the GEX-derived Call Wall / Put Wall rows** in the right column. Rationale: keeps both wall types adjacent for direct comparison; honors "OI = highest observable, GEX = highest interpretive" (Phase 10 D-07) without changing the card's overall left/right structure.

### Evolution Narrative (RPT-05)
- **D-10:** Evolution section placed at the **top of the email, before all ticker cards**. Structure: one plain-language cross-ticker lead sentence, then a compact table — rows = SPY/QQQ/IWM, columns = level / rms / skew_change / term_change, all at the 5-day horizon. Units: pp for level/skew/term, pp for rms. Cross-ticker divergence (e.g. IWM moving alone) readable at a glance (EVOL-05).
- **D-11:** Cold-start behavior: if `evolution_5d_summary()` returns all-None for all tickers, **omit the evolution section entirely**. No placeholder, no note. Section appears only once history accumulates from `run_daily`.
- **D-12 (Claude's discretion):** Lead sentence template and exact pp-formatting for the compact table. Generated at runtime from the scalar values. Section header: "Surface Evolution — 5-day".

### Claude's Discretion
- Specific kaleido camera angle (azimuth/elevation for `plot_vol_surface` and `plot_iv_change_surface` PNG exports) — must be readable as a static frame. Suggest: `eye=dict(x=1.5, y=-1.5, z=0.8)` or similar isometric-style.
- Evolution narrative sentence template (based on level/rms/skew/term values — cross-ticker summary).
- Whether `png_export.py` is a new module or a function added to an existing module.
- Whether the OI computation (`oi_call_wall`, `oi_put_wall`) lives in `analytics.py:summarise()` or `exposure_engine.py`.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & requirements
- `.planning/ROADMAP.md` §"Phase 11: Richer Daily Report" — goal + 5 success criteria (RPT-01..05)
- `.planning/REQUIREMENTS.md` §"Richer Daily Report (Phase 11)" — RPT-01..05 full wording

### Code to modify / reuse (the edit surface)
- `gex/report.py` — **main edit surface**: add evolution top section, OI rows to `_ticker_card()`, explicit `#ffffff` body background, PNG-unavailable fallback note. `build_email()` signature gains `attachments_note: str | None` or builds note internally.
- `gex/run_daily.py` — generate PNGs via kaleido before `build_email()`, pass `attachments=[list of Path]` to `emailer.send()`. Evolution section data gathered here (or in a helper) before `build_email()` call.
- `gex/compute.py` — add `oi_call_wall` / `oi_put_wall` to the `compute_ticker()` summary dict. Source: chain strike-level call/put OI (already available in `s_df` / chain DataFrame).
- `gex/vol_metrics.py` — `evolution_5d_summary(evol_df)` (headless, ready); `vrp_headline()` (ready); `positioning_levels()` (ready, Phase 11 email may consume).
- `gex/analytics.py` — `plot_vol_surface()` + `plot_iv_change_surface()` — the two functions kaleido exports. No modification needed; called with `write_image()`.
- `gex/surface_history.py` — `nth_trading_day_back()` + `list_available_dates()` for resolving the 5d baseline date when building the ΔIV PNG.
- `gex/surface_evolution.py` — `load_evolution(ticker, horizon=5, days=30)` → feed into `evolution_5d_summary()`.
- `gex/emailer.py` — `send(attachments: list[Path])` already supports attachments; no changes needed.
- `gex/config.py` — `PALETTE` tokens already shared; no new tokens needed.
- `requirements.txt` — add `kaleido>=1.0,<2.0` (currently absent; `kaleido==0.2.1` hangs on Windows/plotly 6.7 — do NOT use).

### Prior phase context
- `.planning/phases/10-dashboard-restructure-local-only/10-CONTEXT.md` — D-14 (shared palette tokens), D-15 (headless functions built for Phase 11 plug-in), D-07/D-08 (OI-led positioning rationale, "OI = highest observable").
- `.planning/phases/09-surface-evolution-engine/09-02-SUMMARY.md` — evolution engine decisions (rolling-mean baseline, mask-intersection, idempotent parquet writes).

### Codebase conventions
- `.planning/codebase/CONVENTIONS.md` — snake_case, pure-function compute, no mutation of inputs, `df.copy()` pattern, error handling only at boundaries.
- `.planning/codebase/ARCHITECTURE.md` — shared pipeline pattern (`compute_ticker` = single source of truth), output adapters are pure display/delivery wrappers.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `plot_vol_surface()` in `gex/analytics.py` — existing Plotly figure, just call `fig.write_image(path, format="png")` via kaleido. No modification needed.
- `plot_iv_change_surface()` in `gex/analytics.py` — same kaleido export pattern. Accepts two surface snapshots; use live vs 5d-rolling-mean baseline resolved via `nth_trading_day_back`.
- `evolution_5d_summary(evol_df)` in `gex/vol_metrics.py` — returns `{level, rms, skew_change, term_change, as_of}`, None-safe. All-None = cold start → omit section.
- `emailer.send(attachments=list[Path])` — already accepts file path list; calls `mail.Attachments.Add()` per path. Zero wiring needed.
- `_kv_cell()` and `_kv_table()` in `gex/report.py` — OI wall rows use the same helpers as existing card rows.
- `_pct_from_spot()` in `gex/report.py` — reusable for OI wall distance from spot.

### Established Patterns
- `compute_ticker()` result dict is the canonical output for all consumers (email + dashboard). Adding `oi_call_wall`/`oi_put_wall` here follows the established pattern — no split where email has data the dashboard doesn't.
- Error handling: `process_ticker()` in `run_daily.py` never raises (try/except returns error dict). PNG generation should be wrapped the same way — failure = fallback note, never abort.
- Non-blocking evolutions: Phase 9 already uses `try/except` around `update_evolution()` in `run_daily.py`. Same pattern for kaleido PNG generation.
- Shared palette via `config.PALETTE` — REGIME_COLOR already migrated in Phase 10. No new tokens needed for Phase 11.

### Integration Points
- **`run_daily.py:run()`** is the orchestration point: after surface snapshots are saved + evolution is computed, add a "generate PNGs" step, then pass attachments to `emailer.send()` and the PNG-note flag to `build_email()`.
- **`compute_ticker()` → summary dict** gains `oi_call_wall` + `oi_put_wall` — chain data is already available at that point in the pipeline.
- **`build_email()` in `report.py`** gains: (a) optional `evolution_data` parameter for the top section, (b) optional `png_note` string for the fallback message, (c) OI rows in `_ticker_card()`.
</code_context>

<specifics>
## Specific Ideas

- **kaleido smoke-test spike:** Phase opens with `import kaleido; fig.write_image("out/test.png")` using a trivial plotly figure. If this passes, embed PNGs. If it fails, document the fallback path and ship without PNGs. The spike is the first plan in the phase.
- **4 attachment names:** `spy_surface_YYYYMMDD.png`, `qqq_surface_YYYYMMDD.png`, `iwm_surface_YYYYMMDD.png`, `spy_div_surface_YYYYMMDD.png` (or similar deterministic names in `out/`).
- **Evolution section header:** "Surface Evolution — 5-day" (consistent with "5d" terminology throughout Phase 9/10).
- **OI wall glossary entry needed:** add to the methodology footer — distinguish "OI Call/Put Wall (max open interest strike — assumption-free)" from "Call/Put Wall (max GEX strike — dealer positioning model)".
- **PNG fallback note placement:** small inline note just before the methodology footer, same font/color as `LABEL_GRAY` — unobtrusive but honest.
</specifics>

<deferred>
## Deferred Ideas

- **Per-ticker OI-by-strike PNG charts** (3 more kaleido attachments) — deferred in favor of data rows. Could be added in a future phase if more visual OI context is wanted.
- **All-3-tickers ΔIV surfaces** — only SPY ΔIV in Phase 11. Cross-ticker ΔIV comparison is already covered by the evolution compact table.
- **VRP section in the email** — `vrp_headline()` is ready (headless, Phase 10 D-15), but VRP was not part of RPT-01..05. Deferred to a future enhancement.
- **`cid:` inline images** — deferred to v4.x per REQUIREMENTS.md. Plain attachments ship first.

None — discussion stayed within phase scope.
</deferred>

---

*Phase: 11-richer-daily-report*
*Context gathered: 2026-05-31*

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
