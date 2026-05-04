---
phase: 01-extended-data-layer
verified: 2026-04-30T00:00:00Z
status: human_needed
score: 7/7 source-level criteria verified; 5/5 Cron2-run criteria pending operator confirmation
overrides_applied: 0
re_verification: false
human_verification:
  - test: "Run sleeve_alpha.ipynb Section 0 + Section 1 end-to-end on a fresh Cron2 kernel"
    expected: "All 20 cells execute clean; no exceptions; freshness_table and qa_table render at the bottom"
    why_human: "Locked Python env on Cron2 only — no con.bdh, no Bloomberg-flavoured fields, no nbformat module on the local machine"
  - test: "Confirm SPX and QQQ price + iv30_atm + iv30_90mny + iv90_atm landed non-empty"
    expected: "Section 1.2 stdout shows [landed] for SPX/QQQ across price + 3 IV fields; no RuntimeError"
    why_human: "Requires actually calling con.bdh; field availability is server-side"
  - test: "Capture the [landed] vs [deferred] verdict for XIU and XSP"
    expected: "Either [landed] for the same 4 fields or [deferred] with explicit reason — both are acceptable per D-02"
    why_human: "Best-effort field probe — outcome only known after a real con.bdh call"
  - test: "Confirm VIX pull returns non-empty (else cell raises) and capture VVIX / rf_rate landed/empty status"
    expected: "VIX non-empty (else RuntimeError); VVIX optional; rf_rate empty triggers warnings.warn (does not block)"
    why_human: "Cron2-side data availability"
  - test: "Read the printed freshness_table — confirm days_stale values are sane and no stale > 5 warning fires (or, if it does, that force_refresh=True clears it)"
    expected: "Most rows fresh; days_stale ≤ 1 on a normal weekday; status column shows fresh / stale / empty correctly"
    why_human: "Real days_stale depends on the day the cell runs"
---

# Phase 1: Extended Data Layer — Verification Report

**Phase Goal:** Multi-underlying price + ATM IV + 90%-moneyness IV + VIX + risk-free rate are loaded, calendar-aligned, and exposed as canonical panels (`prices_panel`, `iv_panel`, `skew_panel`) ready for downstream signal work.

**Verified:** 2026-04-30
**Status:** `human_needed` — source-level goal achievement confirmed; Cron2-run gate pending operator confirmation
**Re-verification:** No (initial verification)

## Executive Summary

Source-level verification: **PASS**. All seven Phase 1 success-criteria artifacts are present in `sleeve_alpha.ipynb` cell sources, all locked decisions D-01..D-13 are correctly reflected, all 8 plan-level automated `<verify>` checks pass, all DATA-06..12 requirements have implementing cells, `hmm.ipynb` is byte-identical to its pre-Phase-1 state (tree hash `233a9552...`), and zero anti-patterns or scope violations were found.

The Cron2-run gate remains the operator's verification surface — by design, since the locked env on this Windows machine cannot exercise `con.bdh` or load the Cron2-only stack. Status is `human_needed` rather than `passed` because Phase 1's goal includes "data layer runs clean on fresh kernel" (Success Criterion 5), which requires actually running the notebook on Cron2.

## Two-Column Verification Matrix

| Criterion | Local verdict (cell source) | Cron2-run verdict (user's gate) |
|-----------|------------------------------|----------------------------------|
| **SC-1.** SPX/QQQ price + 30D ATM IV + 30D 90%-moneyness IV pulled with documented field names | PASS — `IV_FIELDS` dict defines all three field strings verbatim (`30DAY_IMPVOL_100.0%MNY_DF`, `30DAY_IMPVOL_90.0%MNY_DF`, `90DAY_IMPVOL_100.0%MNY_DF`); Section 1.2 loop calls `bdh_cached` for `PRICE_FIELD` + every `IV_FIELDS` value across SPX/QQQ; `RuntimeError` guards on empty SPX/QQQ price or iv30_atm | pending operator confirmation — actual landing requires a Cron2 `con.bdh` call |
| **SC-2.** XIU/XSP probed; included or explicitly deferred | PASS — `UNDERLYINGS` dict includes XIU and XSP; Section 1.2 loop probes the same 4 fields on each; `_probe` prints `[deferred] {label} / {field}` on empty response and `[landed] {label} / {field}: n=N, first → last` on success; `landed` filter in Section 1.4 drops underlyings missing any required field from panel column membership (D-02) | pending operator confirmation — outcome (landed vs deferred) only known after Cron2 stdout |
| **SC-3.** VIX and risk-free proxy loaded | PASS — `CROSS_ASSET` dict defines `("VIX Index", "PX_LAST")`, `("VVIX Index", "PX_LAST")`, `("USGG3M Index", "PX_LAST")`; Section 1.3 calls `bdh_cached` for each via `_probe`; empty VIX raises `RuntimeError`; empty rf_rate calls `warnings.warn` per D-13 | pending operator confirmation — actual data availability is server-side |
| **SC-4.** All series aligned to a single trading-day index using `pandas_market_calendars` | PASS — `nyse_index(start, end)` defined in cell 5 using `mcal.get_calendar("NYSE").schedule(...)`, normalized to `pd.DatetimeIndex`; `NYSE_INDEX` exposed as module-level scalar; Section 1.4 panels built via `.reindex(NYSE_INDEX)`; Section 1.5 cross-asset Series asserted via `s.index.equals(prices_panel.index)`; D-04 truncation applied uniformly via `truncate_start` mask; D-08 honored — zero `.fillna` calls anywhere in code cells | pending operator confirmation — alignment correctness on real data (e.g. ~5 NaN/yr per Canadian underlying from TSX-only holidays) is observable only at runtime |
| **SC-5.** Freshness check warns on stale data; data layer runs clean on fresh kernel | PASS (authoring side) — Section 1.6 builds `freshness_table` with columns `[underlying, field, last_bar_date, days_stale, status]` exactly per D-13, iterates the 5 panels + 3 cross-asset Series, prints via `to_string(index=False)`; `warnings.warn` fires (does not raise) when any row has `days_stale > 5`; `_trading_days_stale` uses NYSE schedule arithmetic; `raise` absent from cells 17 and 19 | pending operator confirmation — "runs clean on fresh kernel" is the user's gate by phase definition |
| **REQ.** DATA-06..12 covered by plans | PASS — DATA-06/07/08/10 → 01-02-PLAN; DATA-09 → 01-01-PLAN; DATA-11 → 01-04-PLAN; DATA-12 → 01-03-PLAN; zero uncovered, zero orphaned | n/a |
| **INTEGRITY.** `hmm.ipynb` untouched (v1.0 legacy preserved) | PASS — tree hash `233a9552846767e7621880ac12122722a9435628` byte-identical at HEAD vs pre-pivot `89b5c0a` and Phase 1 context capture `c78ce46`; `git log 89b5c0a..HEAD -- hmm.ipynb` returns zero commits | n/a |

## Observable Truths (Source Level)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `sleeve_alpha.ipynb` exists, is valid nbformat v4 (minor 5), 20 cells in expected order | VERIFIED | `json.load` succeeds; cell ordering matches the four plans' `<action>` sequence character-for-character |
| 2 | All Phase 1 identifiers exposed for Phase 2 consumption | VERIFIED | 62/62 source-introspection checks pass: panels (`prices_panel`, `iv_panel`, `iv90_panel`, `iv90mny`, `skew_panel`), Series (`vix`, `vvix`, `rf_rate`), helpers (`bdh_cached`, `_to_series`, `_to_named_series`, `_last_bar`, `_trading_days_stale`), scalars (`NYSE_INDEX`, `truncate_start`, `landed`, `CACHE_DIR`, `UNDERLYINGS`, `CROSS_ASSET`, `IV_FIELDS`, `START_DATE`, `END_DATE`) |
| 3 | All `con.bdh` field-name strings present verbatim | VERIFIED | `30DAY_IMPVOL_100.0%MNY_DF`, `30DAY_IMPVOL_90.0%MNY_DF`, `90DAY_IMPVOL_100.0%MNY_DF`, `USGG3M Index`, `VIX Index`, `VVIX Index`, `PX_LAST` all appear in cell sources |
| 4 | D-13 warn-not-raise discipline holds | VERIFIED | `warnings.warn` present in cells 11 (rf_rate empty) and 17 (stale > 5); `raise` absent from cells 17 and 19; `raise` present in cells 9 (REQUIRED_UNDERLYINGS missing) and 11 (VIX empty) only — exactly the documented exceptions |
| 5 | D-08 no-imputation discipline holds | VERIFIED | Zero `.fillna` calls anywhere in any code cell; cross-asset empty-source path returns `pd.Series(index=NYSE_INDEX, dtype="float64", name=name)` (all-NaN, not zero-filled) |
| 6 | D-09 NYSE-canonical alignment | VERIFIED | `mcal.get_calendar("NYSE").schedule(...)` is the only calendar source; no TSX/XTSE schedule used as canonical; D-04 truncation applied uniformly to all panels and Series |
| 7 | D-11/D-12 cache wrapper correct | VERIFIED | `bdh_cached(ticker, field, start, end, force_refresh=False)`; `_is_stale` uses NYSE-calendar trading-day arithmetic; `pd.read_parquet` on cache hit; `df.to_parquet(path)` on miss; empty response unlinks pre-existing parquet (D-02 deferred-field robustness); `CACHE_DIR = pathlib.Path.home() / "sleeve_alpha_cache"` with `.mkdir(parents=True, exist_ok=True)` — no hardcoded username |

**Score:** 7/7 source-level truths verified.

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `sleeve_alpha.ipynb` | nbformat v4 JSON, 20 cells, kernelspec `python3` | VERIFIED | Cells 0-7 (Plan 01), 8-11 (Plan 02), 12-15 (Plan 03), 16-19 (Plan 04); valid JSON; CRLF line endings; ASCII-encoded with em-dashes as `—` |
| Section 0 — Setup & Config | UNDERLYINGS, IV_FIELDS, PRICE_FIELD, CROSS_ASSET, START_DATE, END_DATE, CACHE_DIR, NYSE_INDEX | VERIFIED | All 8 identifiers in cells 2-5; `nyse_index` helper defined and called |
| Section 1.1 — Cache wrapper | `bdh_cached`, `_cache_path`, `_is_stale` | VERIFIED | Cell 7; force_refresh, parquet read/write, NYSE-calendar mtime, empty-response handling, stale-cache fallback on `con.bdh` exception |
| Section 1.2 — Per-underlying raw pulls | `raw_pulls`, `_probe`, `[landed]/[deferred]` log, REQUIRED_UNDERLYINGS guard | VERIFIED | Cell 9; loops 4 underlyings × 4 fields; raises only on missing required SPX/QQQ price + iv30_atm |
| Section 1.3 — Cross-asset raw pulls | `raw_cross`, VIX raise + rf_rate warn | VERIFIED | Cell 11; raises on empty VIX; warns on empty rf_rate; VVIX silently allowed |
| Section 1.4 — Panel assembly | `prices_panel`, `iv_panel`, `iv90_panel`, `iv90mny`, `skew_panel`; D-04 truncation | VERIFIED | Cell 13; `_to_series` + `_build_panel` helpers; `landed` filter; `truncate_start = max(iv_first_dates)`; `skew_panel = iv90mny[common_skew_cols] - iv_panel[common_skew_cols]` |
| Section 1.5 — Cross-asset Series | `vix`, `vvix`, `rf_rate` as `pd.Series`; assert s.index.equals(prices_panel.index) | VERIFIED | Cell 15; `_to_named_series` empty-source path returns all-NaN Series; alignment assert in place |
| Section 1.6 — Freshness table | `freshness_table` with [underlying, field, last_bar_date, days_stale, status]; warn on > 5 | VERIFIED | Cell 17; column list verbatim; iterates 5 panels + 3 cross-asset; `to_string(index=False)`; warn-not-raise |
| Section 1.7 — Per-panel missingness QA | `qa_table` with [panel, underlying, n, n_valid, miss_pct, first, last] | VERIFIED | Cell 19; column list verbatim; iterates the 5 panels (cross-asset Series intentionally omitted — D-13 already covers them) |

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| Section 0 imports | Section 1 cache wrapper | shared `CACHE_DIR` pathlib.Path | VERIFIED | `CACHE_DIR = pathlib.Path.home() / "sleeve_alpha_cache"` defined in cell 4; `_cache_path` in cell 7 references `CACHE_DIR / f"..."` |
| `bdh_cached` | `con.bdh` | passthrough on cache miss | VERIFIED | `con.bdh(ticker, field, start_date=start, end_date=end)` called inside `bdh_cached` (cell 7); stale-cache fallback wraps the call |
| Data pull cells | `bdh_cached` | function call with ticker + field | VERIFIED | Section 1.2 / 1.3 call `bdh_cached(...)` exclusively via `_probe`; no direct `con.bdh` calls in data-pull cells |
| Deferred-field log | stdout | `print(f"  [deferred] ...")` | VERIFIED | `_probe` in cell 9 prints `[deferred] {label} / {field}: empty response from con.bdh` on empty/None response |
| `raw_pulls` (Plan 02) | `prices_panel` / `iv_panel` / `iv90_panel` | `_build_panel` → `.reindex(NYSE_INDEX)` | VERIFIED | Cell 13 loops `landed`, calls `_build_panel(field_key, landed)` which reindexes each `_to_series(raw_pulls[u][field_key])` onto `NYSE_INDEX` |
| `iv90mny` + `iv_panel` | `skew_panel` | subtraction on column intersection | VERIFIED | `skew_panel = iv90mny[common_skew_cols] - iv_panel[common_skew_cols]` (cell 13) |
| `raw_cross` | `vix` / `vvix` / `rf_rate` Series | `_to_named_series` → `.squeeze().reindex(NYSE_INDEX)` | VERIFIED | Cell 15 calls `_to_named_series("vix")` etc; empty path produces all-NaN Series with same index |
| `freshness_table['days_stale'] > 5` | `warnings.warn` | conditional warning | VERIFIED | Cell 17: `stale_rows = freshness_table[freshness_table["status"] == "stale"]`; if `len(stale_rows) > 0` then `warnings.warn(...)` |

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DATA-06 | 01-02 | SPX, QQQ price + 30d ATM IV + 30d 90%-mny IV via `con.bdh` with documented field names | SATISFIED (source); pending Cron2 run for landing confirmation | `IV_FIELDS` dict + Section 1.2 probe loop |
| DATA-07 | 01-02 | Probe XIU/XSP equivalents; include or document deferred | SATISFIED (source); pending Cron2 run for landed/deferred verdict | `UNDERLYINGS` includes XIU/XSP; `_probe` prints `[deferred]` on empty |
| DATA-08 | 01-02 | VIX (and optional VVIX) via `con.bdh` for fragility composite | SATISFIED (source); pending Cron2 run for landing confirmation | `CROSS_ASSET["vix"]` and `["vvix"]` pulled in Section 1.3 |
| DATA-09 | 01-01 | All series aligned on a common trading-day index via `pandas_market_calendars` | SATISFIED | `NYSE_INDEX` from `mcal.get_calendar("NYSE")`; `.reindex(NYSE_INDEX)` used in panel + Series builders; D-09 NYSE-canonical decision |
| DATA-10 | 01-02 | Risk-free rate proxy (3M T-bill) loaded for option pricing | SATISFIED (source); pending Cron2 run to confirm `USGG3M Index PX_LAST` lands or alternate-field warn fires | `CROSS_ASSET["rf_rate"] = ("USGG3M Index", "PX_LAST")`; warn-not-raise on empty per D-13 |
| DATA-11 | 01-04 | Data freshness check; staleness > 5 trading days = warning | SATISFIED (source); pending Cron2 run for actual `days_stale` values | Section 1.6 `freshness_table` + `warnings.warn` on `> 5` |
| DATA-12 | 01-03 | Data layer cells run cleanly on fresh kernel; produce `prices_panel`, `iv_panel`, `skew_panel` | SATISFIED (source); pending Cron2 run for "runs cleanly" gate | Three canonical panels named per D-05; built via reindex+truncate; cell ordering supports fresh-kernel execution |

**Coverage:** 7/7 phase requirements addressed by exactly one plan each. Zero uncovered. Zero orphaned.

## Anti-Patterns Found

None. Specifically scanned for:

| Anti-pattern | Result |
|--------------|--------|
| TODO / FIXME / placeholder comments | Absent |
| `.fillna` calls (D-08 violation) | Absent across all code cells |
| `pip install` strings | Absent |
| `import hmmlearn` | Absent (locked env constraint honored) |
| `import arch` | Absent (locked env constraint honored) |
| `raise` in cells where D-13 specifies `warn` (cells 17, 19) | Absent — both use `warnings.warn` only |
| Hardcoded username in `CACHE_DIR` | Absent — `pathlib.Path.home()` used |
| Direct `con.bdh` calls in data-pull cells (bypassing cache) | Absent — only inside `bdh_cached` |
| Modification of `hmm.ipynb` | Absent — tree hash byte-identical from `89b5c0a` to HEAD |
| Imputation in cross-asset empty path | Absent — empty path produces all-NaN Series |

## Behavioral Spot-Checks

**SKIPPED (no runnable entry points on this machine).** The notebook is authoring-only by phase design — Cron2 is the only environment that can execute the cells. The local Python env has no `con.bdh`, no Bloomberg-flavoured fields, no Cron2-only stack, and the project explicitly prohibits running the notebook here (`CLAUDE.md`: "Cron2 Jupyter Notebook Server only — cannot run locally").

In lieu of behavioral checks, the source-level verification ran:
- 62/62 identifier-presence greps over concatenated cell sources
- 8/8 plan-level `<verify><automated>` Python checks (verbatim from each plan)
- D-13 warn-not-raise discipline check (cell-by-cell `raise` absence)
- D-08 no-imputation check (`.fillna` absence across all code cells)
- Cell-ordering check against the four plans' `<action>` sequences
- Requirements-coverage cross-reference (plans ↔ phase ↔ REQUIREMENTS.md)
- `hmm.ipynb` tree-hash check across the v2.0 commit range

All source-side checks pass.

## Human Verification Required

These items require running `sleeve_alpha.ipynb` on Cron2. Listed in increasing priority for the operator's first run:

### 1. Fresh-kernel end-to-end run

**Test:** Open `sleeve_alpha.ipynb` on Cron2; run all cells (Section 0 → Section 1.7) in a fresh kernel.
**Expected:** All 20 cells complete without exception. The last two outputs are the printed `freshness_table` and `qa_table`.
**Why human:** Phase Goal Success Criterion 5 explicitly says "data layer runs clean on fresh kernel" — that's a Cron2-only verdict.

### 2. SPX/QQQ landing

**Test:** Read Section 1.2 stdout. Confirm `[landed] SPX / PX_LAST` plus all three IV-field landings; same for QQQ.
**Expected:** Eight `[landed]` lines for SPX + QQQ; zero `RuntimeError`.
**Why human:** Required-underlying landing depends on `con.bdh` returning non-empty data — a server-side fact.

### 3. XIU/XSP landed-or-deferred verdict

**Test:** Read Section 1.2 stdout for XIU and XSP. Capture which fields landed and which printed `[deferred]`. Note the result in `01-04-SUMMARY.md`'s "Pending Cron2 run" section.
**Expected:** Either `[landed]` for the same 4 fields (preferred) or `[deferred] — empty response from con.bdh` (acceptable per D-02).
**Why human:** Best-effort field probe — outcome is part of the documentation D-02 wants captured.

### 4. VIX / VVIX / rf_rate verdict

**Test:** Read Section 1.3 stdout. Confirm VIX landed (else cell raises). Capture VVIX and rf_rate landing status. Note any `warnings.warn` from rf_rate empty.
**Expected:** VIX `[landed]` (else `RuntimeError: VIX pull returned empty`); VVIX optional; rf_rate either landed or warn-fallback.
**Why human:** Server-side data availability.

### 5. Freshness verdict

**Test:** Read the printed `freshness_table` and `qa_table`. Confirm `status` column shows mostly `fresh`. If any `stale` rows or warnings, decide whether to re-run with `force_refresh=True`.
**Expected:** Most rows fresh; days_stale ≤ 1 on a normal weekday; stale > 5 only on long-weekend / holiday lag (in which case the warning text recommends `force_refresh=True`).
**Why human:** Real `days_stale` depends on the day of run.

## Gaps Summary

**No source-level gaps.** Phase 1 ships authoring-only artifacts by phase design (locked-env, Cron2-only runtime). All source artifacts the phase promised are present, all locked decisions are reflected, all plan-level automated checks pass, and `hmm.ipynb` is preserved untouched.

The Cron2-run gate (5 human-verification items above) is the operator's verification surface, not a source-level defect. When the operator runs the notebook on Cron2 and confirms the 5 items, the phase status flips from `human_needed` to `passed`.

---

*Verified: 2026-04-30*
*Verifier: Claude (gsd-verifier)*
*Source-introspection only — Cron2 runtime gate is the user's verification surface*
