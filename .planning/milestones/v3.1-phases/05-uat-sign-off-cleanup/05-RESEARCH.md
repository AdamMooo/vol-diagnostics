# Phase 5: UAT Sign-Off & Cleanup — Research

**Researched:** 2026-05-06
**Domain:** Streamlit UAT execution, git commit hygiene, stale-doc inventory
**Confidence:** HIGH (all findings verified against actual codebase and git diff)

---

## Summary

Phase 5 has no new feature code. The work is: (1) live interactive UAT of `streamlit_app.py` across 4 scenarios, (2) atomic commit of 3 known-clean diffs, (3) grep-driven docs sweep. All 3 outstanding diffs are verified and understood. The Streamlit app imports cleanly, tests pass, and the infrastructure for UAT is in place.

Two significant discrepancies exist between the UAT doc (`03-HUMAN-UAT.md`) and the current live app. The app has evolved since the UAT doc was written — it now has a password gate, 20 tickers across two sections (not 3), and 7 columns in the expander summary table (not 6). The UAT doc scenarios must be updated in the plan to reflect the actual app, not the v3.0 spec. Alternatively, the UAT pass/fail criteria should be matched against observed reality rather than the stale doc text.

The yfinance docs-sweep is nuanced: yfinance remains a real dependency (`validation.py:event_study()` calls `yf.download()`; it is in `requirements.txt`). What needs cleaning is only the CLAUDE.md claim that `gex/data_loader.py` uses yfinance for chain pulls — that module was rewritten to CBOE JSON. Do not remove all yfinance references; remove only the inaccurate ones.

**Primary recommendation:** Run UAT against the actual app behavior (not the stale 3-ticker spec). Update pass criteria as you record results. Commit the 3 diffs atomically first — they are already in the working tree and confirmed clean.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- D-01: Live walkthrough mode — Adam runs `streamlit run streamlit_app.py` and walks through each of the 4 scenarios while Claude guides step-by-step. Results recorded in `03-HUMAN-UAT.md` as we go (pass/fail per scenario).
- D-02: UAT scenarios are exactly the 4 defined in `03-HUMAN-UAT.md`: (1) app launch, (2) regime cards, (3) per-ticker expander, (4) refresh button.
- D-03: If any scenario fails, the plan must include a fix cycle before marking UAT complete.
- D-04: Brief summary → confirm → single atomic commit for all 3 outstanding files together.
- D-05: The 3 diffs are clean fixes (not in-progress work) — commit message documents what each changes.
- D-06: Full stale-doc sweep — not just CLAUDE.md. Targets: CLAUDE.md, 03-HUMAN-UAT.md, 03-VERIFICATION.md, options-quant.md, any file found via grep.
- D-07: Docs sweep happens AFTER UAT sign-off, not before.

### Claude's Discretion

- Exact commit message wording for the outstanding 3-file fix commit
- Order of UAT scenario walkthrough steps within each scenario
- Whether options-quant.md needs content changes beyond yfinance cleanup (leave other content alone unless clearly wrong)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UAT-01 | Streamlit app launch — no import/COM/matplotlib errors | App imports cleanly (verified); password gate present; matplotlib.use("Agg") not in current app — see pitfall |
| UAT-02 | Regime cards render with correct colors and all fields | `render_regime_card()` fully implemented; app now has 20 tickers across two sections, not 3 |
| UAT-03 | Per-ticker expander shows charts + summary table | Implementation at lines 247-293; table has 7 cols (Spot added), not 6 as in UAT doc |
| UAT-04 | Refresh button clears cache and re-fetches | `fetch_ticker.clear()` + `st.rerun()` at lines 309-310; confirmed callable via pytest |
</phase_requirements>

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| UAT execution | Human interaction | Claude guidance | Interactive UI cannot be automated without a running Streamlit server |
| Code fix commit | git working tree | — | 3 diffs already staged as modifications; single `git commit` |
| Docs sweep | Filesystem grep | git commit | Find-then-edit; grep first to avoid guessing |
| UAT result recording | `03-HUMAN-UAT.md` | `03-VERIFICATION.md` | Existing files with pass/fail/pending format to update in-place |

---

## Section 1: Outstanding Diffs — Exact State

All 3 files are modified in the working tree (`git status`: ` M` = modified, unstaged). `git diff HEAD` confirms the exact changes. No partial or in-progress work — all 3 diffs are complete and self-contained. [VERIFIED: git diff HEAD]

### emailer.py — DispatchEx → Dispatch

**File:** `gex/emailer.py:32`
**Change:** One line. `DispatchEx` replaced with `Dispatch` in the Outlook COM fallback path.

```python
# Before (in git HEAD)
outlook = win32com.client.DispatchEx("Outlook.Application")

# After (working tree)
outlook = win32com.client.Dispatch("Outlook.Application")
```

**Why:** `DispatchEx` always creates a new COM instance — under some Outlook configs this causes errors when Outlook is already running. `Dispatch` reuses the existing COM server when possible. The surrounding `GetActiveObject` → fallback to `Dispatch` pattern is the canonical approach. [VERIFIED: gex/emailer.py lines 29-34]

### report.py — Nested-table email layout

**File:** `gex/report.py:236-256`
**Change:** `build_email()` return value. The wrapping `<div>` is replaced with a two-level table structure (outer full-width table → inner 820px centered table).

```
# Before: div-based, max-width via CSS
<html><body style="...padding:20px;margin:0;">
<div style="max-width:820px;margin:0 auto;">
  {content}
</div>

# After: table-based centering
<html><body style="...margin:0;padding:0;">
<table width="100%" ...>
  <tr><td align="center" style="padding:20px;">
    <table width="820" ... style="width:820px;max-width:820px;">
      <tr><td>
        {content}
      </td></tr>
    </table>
  </td></tr>
</table>
```

**Why:** Email clients (Outlook, Apple Mail) ignore CSS `max-width` on `<div>` elements but do respect table `width` attributes. This makes the email render at the intended width across clients. [VERIFIED: gex/report.py diff]

### validation.py — dtype coercion guard on parquet load

**File:** `gex/validation.py:41-43` (within `save_snapshot()`)
**Change:** After reading the existing parquet store, cast 4 nullable float columns to `float64` before the concat.

```python
# Added block (3 lines):
for col in ("zero_gamma_level", "call_wall", "put_wall", "vanna_exposure"):
    if col in hist.columns:
        hist[col] = hist[col].astype("float64")
```

**Why:** When a column's first snapshot row has `NaN`, pyarrow may infer it as `object` or `float32`. Subsequent rows with real values create a dtype mismatch at `pd.concat`. The cast ensures consistent `float64` before merge. [VERIFIED: gex/validation.py lines 39-43]

---

## Section 2: Streamlit App State — UAT Scenario Analysis

### Critical: App Has Evolved Beyond UAT Doc Spec

The UAT doc was written against v3.0 (3-ticker, single-section app). The current `streamlit_app.py` is a materially different app. The plan must acknowledge this and adjust pass criteria accordingly. [VERIFIED: streamlit_app.py full read]

**Key differences between UAT doc expectations and current app:**

| UAT Doc Says | Actual App (current) |
|---|---|
| "Three colored regime cards (SPY, QQQ, IWM)" | 20 tickers: 6 Index (SPY, QQQ, IWM, XLF, GLD, TLT) + 14 Purpose tickers; each gets a regime card |
| "Single multi-select with SPY, QQQ, IWM" | Two multi-selects: "Index" (6) and "Purpose Yield Shares" (14) in sidebar |
| "Sidebar shows Refresh button" | Sidebar has "Refresh data" button (`use_container_width=True`) — confirmed present at line 308 |
| Summary table: "Net GEX, VEX, CHEX, Zero-Gamma, Call Wall, Put Wall" (6 cols) | Summary table: "Spot, Net GEX, VEX, CHEX, Zero-γ, Call Wall, Put Wall" (7 cols); optionally "IV30" (8 cols) |
| "Two charts (strike GEX, gamma profile)" | Two charts + ZGL-vs-Spot 30-session line chart + regime distribution table (when parquet history exists) |
| No password | `_check_password()` runs at startup; password stored in `.streamlit/secrets.toml` |

**UAT walkthroughs must use the actual observed behavior as the pass criterion**, not the stale doc text. The plan should note updated expected values per scenario before Adam runs each test.

### Scenario 1: App Launch (UAT-01)

**What should happen:** `streamlit run streamlit_app.py` from project root starts the dev server, prints a localhost URL, and the browser page loads.

**Potential blockers:**
- Password gate (`_check_password()`) runs first. Browser will show a password prompt, not the dashboard. Adam must enter the password from `.streamlit/secrets.toml` to proceed. This is not an error — it is expected behavior.
- `matplotlib.use("Agg")` was verified present at line 6 in the v3.0 app (Phase 3 verification). The current app does NOT have this line — it uses Plotly (not matplotlib) for the main charts, and imports matplotlib only indirectly via `gex.analytics`. This needs to be verified live; if matplotlib backend is invoked at import time in a non-interactive context, there may be a warning but it should not crash. [VERIFIED: current streamlit_app.py has no `matplotlib.use("Agg")` call; Plotly is the primary charting lib]
- `page_icon="assets/gamma-icon-lg.png"` — file confirmed present at `assets/gamma-icon-lg.png`. [VERIFIED: ls assets/]
- `gex/compute.py` imports cleanly (confirmed: `python -c "from gex.compute import compute_ticker"` exits 0). [VERIFIED: Bash]

**Success criterion (updated):** Browser loads, password prompt appears, after entering password the GEX Dashboard title is visible with Index and Purpose Yield Shares multi-selects in the sidebar.

### Scenario 2: Regime Cards (UAT-02)

**What should happen:** After data loads (~20 tickers via CBOE), colored cards appear for each selected ticker.

**Potential blockers:**
- CBOE fetch for 20 tickers will be slow on first load (no cache). Cache TTL is 5 minutes. The spinner "Loading chains from CBOE..." covers this.
- `time.sleep(0.15)` between tickers — 20 tickers = ~3 seconds of intentional sleep during fetch.
- `_load_history_cached()` called per card to compute streak. On first run (no parquet or parquet with no history for some tickers), returns empty DataFrame — `_compute_streak()` returns `None`, which is handled gracefully.
- vs-yesterday label: depends on `load_yesterday()` which requires parquet history. `out/gex_snapshots.parquet` exists [VERIFIED: ls out/], so vs-yesterday may show for tickers with prior snapshots.

**Success criterion (updated):** Cards render for all selected tickers (not just SPY/QQQ/IWM). Colors match regime. All 5 core fields visible (ticker, regime, GEX, VEX, delta-flow). ZGL and streak/observations are bonus fields.

### Scenario 3: Per-Ticker Expander (UAT-03)

**What should happen:** Clicking a ticker expander reveals a summary table, two Plotly charts, and (if parquet history exists) a ZGL-vs-Spot chart and regime distribution table.

**Actual table columns (7):** Spot, Net GEX, VEX, CHEX, Zero-γ, Call Wall, Put Wall. The UAT doc says 6 columns (omits Spot). [VERIFIED: streamlit_app.py lines 248-256]

**Actual chart count:** 2 Plotly charts (`plot_strike_gex`, `plot_gamma_profile`) plus optionally a ZGL history chart and regime counts table. UAT doc says "two charts" — the additional ZGL chart is conditional on history existing. Since parquet exists, UAT will likely see 3 charts + 2 tables per expander.

**Success criterion (updated):** Summary table renders with at minimum 7 columns. Two main Plotly charts render. No Python traceback. ZGL history chart is a bonus.

### Scenario 4: Refresh Button (UAT-04)

**What should happen:** Clicking "Refresh data" calls `fetch_ticker.clear()` then `st.rerun()`, forcing a cold re-fetch.

**Mechanism confirmed:** Lines 308-310 in streamlit_app.py. The button label is "Refresh data" (not "Refresh"). [VERIFIED: streamlit_app.py:308]

**Behavior:** On click, cache is cleared and page re-runs. Because CBOE fetch takes 1-3 seconds per ticker, the spinner "Loading chains from CBOE..." reappears. This is the expected visual confirmation of re-fetch.

**Success criterion:** "Refresh data" button click causes spinners to reappear and data re-loads without error.

---

## Section 3: yfinance/v2.1 Reference Inventory

**Grep results (verified):** [VERIFIED: Grep tool — *.py and *.md scanned]

### Python files

| File | Line | Content | Action |
|------|------|---------|--------|
| `gex/validation.py` | 20 | `import yfinance as yf` | **KEEP** — used by `event_study()` which calls `yf.download()`. Active dependency. |

### Markdown files

| File | Line | Content | Action |
|------|------|---------|--------|
| `CLAUDE.md` | ~59 | `gex/data_loader.py` — "yfinance chain pull → ChainSnapshot" | **UPDATE** — data_loader.py now uses CBOE JSON, not yfinance. Change description. |
| `CLAUDE.md` | ~14 | v2.1 section header and description | **ASSESS** — this is a historical milestone note, not an operational instruction. Could be left or removed as a milestone summary. |
| `CLAUDE.md` | ~72 | `## Key Files (v2.1 — parked)` section | **ASSESS** — clearly labeled parked; probably fine to leave; may confuse new readers. |
| `options-quant.md` | 22 | "Data is pulled live from yfinance on first load..." | **UPDATE** — data now comes from CBOE. Rewrite sentence. |
| `options-quant.md` | ~32 | "Last updated: 2026-05-05 | v3.0 Phase 3 complete" | **UPDATE** — stale; should reflect v3.1 Phase 5 completion after UAT. |
| `README.md` | 3, 48 | yfinance references in public README | **ASSESS** — README is maintained separately per CLAUDE.md global instructions. Do not edit unless explicitly in scope. Not listed in D-06 targets. |

### Important: yfinance is still a real dependency

`requirements.txt:9` has `yfinance>=0.2.40`. `gex/validation.py:event_study()` uses `yf.download()`. The docs sweep must not imply yfinance has been fully removed — only that it is no longer used for chain pulls. The accurate statement is: "CBOE JSON for live chains; yfinance retained for event study historical price data."

---

## Section 4: Commit Strategy

### Commit 1 — 3 outstanding fixes (before UAT, per D-07 reversal note)

**Files:** `gex/emailer.py`, `gex/report.py`, `gex/validation.py`

**Status:** All 3 are clean modifications in the working tree (`git status` shows ` M`). No staging required — `git add` will pick them up. No other files are modified in these paths.

**Recommended commit message:**
```
fix(gex): emailer Dispatch, report nested-table layout, validation dtype guard

emailer.py: DispatchEx → Dispatch in COM fallback (more reliable when Outlook
already running; DispatchEx always spawns new instance)

report.py: wrap build_email() content in nested table structure (width=820,
max-width enforced via table attributes for Outlook/Apple Mail compatibility)

validation.py: cast nullable float cols to float64 before pd.concat in
save_snapshot() to prevent dtype merge errors on parquet round-trip
```

**Git command:**
```powershell
git add gex/emailer.py gex/report.py gex/validation.py
git commit -m "..."
```

**Note on D-07 ordering:** D-07 says docs sweep AFTER UAT. The outstanding code commits are not docs — they should happen before or during UAT (not after). Plan should commit the 3 fixes first (Wave 0 or Wave 1), then run UAT, then do docs sweep.

### Commit 2 — UAT results + docs sweep (after UAT)

**Files:** `03-HUMAN-UAT.md`, `03-VERIFICATION.md`, `CLAUDE.md`, `options-quant.md`

**Recommended commit message structure:**
```
docs(phase-5): UAT sign-off + stale-doc sweep

Mark 4 UAT scenarios pass/fail, update 03-VERIFICATION.md status to complete,
remove stale yfinance/data_loader description from CLAUDE.md, update
options-quant.md data source sentence and status line.
```

---

## Section 5: Edge Cases and Fix-Cycle Planning

### Edge Case A: CBOE fetch fails during UAT

`fetch_ticker()` wraps `compute_ticker()` in a try/except (lines 329-332). Errors are collected and displayed via `st.error()` — the app does not crash. If CBOE CDN is unreachable, some tickers will show error messages rather than cards. This is not a UAT failure for scenarios 2-4 if at least one ticker loads.

**Fix-cycle trigger:** App crashes (unhandled exception, not per-ticker error). That would indicate an import or startup issue, not a data issue.

### Edge Case B: Password gate blocks UAT-01

The `_check_password()` function at startup is not documented in the UAT scenarios at all. Adam will see a password prompt, not the dashboard. This is expected behavior — not a failure. Plan must include "enter password from `.streamlit/secrets.toml`" as a UAT-01 step.

**Password:** Available in `.streamlit/secrets.toml` (not reproduced here for security).

### Edge Case C: matplotlib backend issue

The v3.0 app had `matplotlib.use("Agg")` at line 6. The current app imports `gex.analytics` which may import matplotlib at module level. If matplotlib tries to display a GUI, it would error in a headless-style context — but on Windows with a browser session active, this is unlikely to manifest. Plotly handles all visible charts; matplotlib is only used inside `gex.analytics` chart functions.

**Fix-cycle trigger:** Terminal shows `matplotlib backend` error or the app hangs on import. Fix: add `import matplotlib; matplotlib.use("Agg")` before the `gex.analytics` import in `streamlit_app.py`.

### Edge Case D: UAT-03 column count mismatch

The UAT doc says 6 columns; the app has 7 (Spot is included). This is not a failure — it is a documentation drift. Record the actual columns seen and mark pass if all 7 are present.

### Edge Case E: No parquet history for some tickers

The extended ticker list (XLF, GLD, TLT, NVDA, etc.) was likely never snapshotted. `_load_history_cached()` will return empty DataFrame for these. ZGL history chart and regime distribution table will not render for those tickers. Streak will be `None`. These are expected behaviors — not failures.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | `pytest.ini` or default discovery |
| Quick run command | `cd C:/dev/options-quant && .venv/Scripts/pytest gex/tests/test_streamlit_app.py -q` |
| Full suite command | `cd C:/dev/options-quant && .venv/Scripts/pytest gex/tests/ -q` |

### Success Criteria → Verification Map

| Criterion | Verification Method | Command / Check |
|-----------|---------------------|-----------------|
| SC-1: App starts without errors | Human + automated smoke | `pytest gex/tests/test_streamlit_app.py -q` (3 tests) + live `streamlit run` |
| SC-2: Three+ regime cards render correctly | Human visual inspection | No automated equivalent — requires running server |
| SC-3: Per-ticker expander shows charts + table with ≥6 cols | Human visual inspection | No automated equivalent |
| SC-4: Refresh button triggers re-fetch | Human interaction | No automated equivalent |
| SC-5: 3 files committed; CLAUDE.md no longer has stale yfinance/data_loader text | Grep verification | `git log --oneline -5` + `grep "yfinance" CLAUDE.md` |

### Grep-Verifiable Checks (post-phase)

```powershell
# SC-5a: Confirm 3 files committed (no outstanding modifications)
git status gex/emailer.py gex/report.py gex/validation.py
# Expected: nothing shown (clean working tree for these files)

# SC-5b: Confirm CLAUDE.md no longer references yfinance for data_loader
Select-String -Path CLAUDE.md -Pattern "yfinance"
# Expected: zero matches (or only the event-study note if retained)

# SC-5c: Confirm options-quant.md data source sentence updated
Select-String -Path options-quant.md -Pattern "yfinance"
# Expected: zero matches

# SC-5d: Confirm UAT doc marked complete
Select-String -Path .planning/phases/03-streamlit-dashboard/03-HUMAN-UAT.md -Pattern "\[pending\]"
# Expected: zero matches

# SC-5e: Full test suite still green after commits
cd C:/dev/options-quant && .venv/Scripts/pytest gex/tests/ -q
# Expected: all pass (baseline: 77 tests pass as of Phase 4 completion; current baseline 3 streamlit tests pass)
```

### Wave 0 Gaps

None — existing test infrastructure covers automated checks. Human walkthrough is the primary validation mechanism for UAT-01 through UAT-04.

---

## Common Pitfalls

### Pitfall 1: Treating UAT doc expected values as ground truth

**What goes wrong:** Plan checks for "3 regime cards" but app shows 20. Confusion about whether this is a pass or fail.
**Why it happens:** UAT doc was written when the app had 3 tickers. App expanded significantly.
**How to avoid:** Plan must update the expected values per scenario before Adam runs. The criteria should be behavioral ("cards render for each selected ticker") not count-specific ("3 cards").

### Pitfall 2: Removing all yfinance references from docs

**What goes wrong:** Docs claim "yfinance removed" but `validation.py` still imports it for `event_study()`. False statement creates confusion later.
**Why it happens:** The CBOE migration story is "we replaced yfinance for chain pulls" — people assume yfinance is gone entirely.
**How to avoid:** Be precise. CLAUDE.md change is: "yfinance chain pull" → "CBOE delayed quotes JSON" in the data_loader row only. Add a note that yfinance is retained for `event_study()` if helpful.

### Pitfall 3: Forgetting the password gate in UAT-01

**What goes wrong:** UAT script says "app loads showing GEX Dashboard" but Adam sees a password prompt and thinks something is wrong.
**Why it happens:** `_check_password()` was added after the UAT doc was written.
**How to avoid:** First UAT step for SC-1: "browser shows password prompt → enter password → dashboard appears."

### Pitfall 4: Committing docs before UAT (violating D-07)

**What goes wrong:** Docs marked complete before UAT reveals a failure; fix cycle makes docs stale again.
**How to avoid:** Commit the 3 code fixes first (clean, no UAT dependency). Do docs sweep only after UAT scenarios are all marked pass.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python venv | All | Yes | 3.x | — |
| streamlit | UAT | Yes | 1.57.0 | — |
| Plotly | streamlit_app charts | Yes (implied by app running) | — | — |
| gex.compute | fetch_ticker | Yes (import confirmed) | — | — |
| .streamlit/secrets.toml | Password gate at UAT start | Yes | — | — |
| out/gex_snapshots.parquet | vs-yesterday, streak, ZGL history | Yes | — | First-run graceful (empty DataFrame returned) |
| assets/gamma-icon-lg.png | page_icon in set_page_config | Yes | — | — |
| yfinance | event_study() in validation.py | Yes | 1.3.0 | — |

No missing dependencies.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The current `streamlit_app.py` runs without errors in a live Streamlit server | Section 2 UAT-01 | Startup error would trigger fix cycle; matplotlib backend is the most likely culprit |
| A2 | CBOE CDN is reachable from the dev machine during UAT | Section 2 UAT-02 | Tickers will fail to load; not a UAT-01 failure but would affect 02/03 scenarios |

All other claims are VERIFIED against codebase.

---

## Sources

### Primary (HIGH confidence)
- `gex/emailer.py` — read directly, diff confirmed [VERIFIED]
- `gex/report.py` — read directly, diff confirmed [VERIFIED]
- `gex/validation.py` — read directly, diff confirmed [VERIFIED]
- `streamlit_app.py` — read directly, 351 lines [VERIFIED]
- `.planning/phases/03-streamlit-dashboard/03-HUMAN-UAT.md` — read directly [VERIFIED]
- `.planning/phases/03-streamlit-dashboard/03-VERIFICATION.md` — read directly [VERIFIED]
- `git diff HEAD` — exact diff output for all 3 files [VERIFIED]
- `Grep` tool — yfinance/v2.1 sweep across all .py and .md files [VERIFIED]
- `.venv/Scripts/python.exe -c "import streamlit; print(streamlit.__version__)"` — 1.57.0 [VERIFIED]
- `.venv/Scripts/pytest gex/tests/test_streamlit_app.py -q` — 3 passed [VERIFIED]

---

## Metadata

**Confidence breakdown:**
- Outstanding diffs: HIGH — exact line-level diff confirmed
- App UAT readiness: HIGH — imports clean, tests pass; live run is human-only
- yfinance/v2.1 inventory: HIGH — grep-verified across all files
- Commit strategy: HIGH — standard git workflow, no complexity

**Research date:** 2026-05-06
**Valid until:** 2026-05-13 (7 days — fast-moving active phase)

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/05-uat-sign-off-cleanup/05-CONTEXT|05-CONTEXT]]
- [[_planning/gamma-omm/phases/05-uat-sign-off-cleanup/05-DISCUSSION-LOG|05-DISCUSSION-LOG]]
- [[_planning/gamma-omm/phases/05-uat-sign-off-cleanup/05-P1-PLAN|05-P1-PLAN]]
- [[_planning/gamma-omm/phases/05-uat-sign-off-cleanup/05-P1-SUMMARY|05-P1-SUMMARY]]
- [[_planning/gamma-omm/phases/05-uat-sign-off-cleanup/05-P2-PLAN|05-P2-PLAN]]
- [[_planning/gamma-omm/phases/05-uat-sign-off-cleanup/05-P2-SUMMARY|05-P2-SUMMARY]]
- [[_planning/gamma-omm/phases/05-uat-sign-off-cleanup/05-P3-PLAN|05-P3-PLAN]]
- [[_planning/gamma-omm/phases/05-uat-sign-off-cleanup/05-P3-SUMMARY|05-P3-SUMMARY]]

<!-- LINKS:END -->
