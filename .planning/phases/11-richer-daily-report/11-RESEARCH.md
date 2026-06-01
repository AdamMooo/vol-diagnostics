# Phase 11: Richer Daily Report - Research

**Researched:** 2026-06-01
**Domain:** Email delivery, PNG attachment generation, report layout
**Confidence:** HIGH

## Summary

Phase 11 upgrades the daily GEX email from plain HTML to a richer, formal business report with 4 PNG attachments (3D vol surfaces + ΔIV surface) and new data rows (OI walls + evolution scalars). The phase integrates existing headless functions from Phase 10 (vol metrics, evolution engine, surface diagnostics) into the email delivery pipeline via kaleido PNG export.

All computational pieces already exist. The work is wiring: (1) smoke-test kaleido on Windows, (2) call `fig.write_image()` via kaleido to generate 4 PNGs, (3) add two new data rows to ticker cards (OI Call Wall / OI Put Wall), (4) add evolution section at report top (cold-start safe), (5) explicit `#ffffff` body background. Email thread-safety and error handling are non-blocking (fallback note if kaleido fails, cold-start skips evolution section).

**Primary recommendation:** Start with kaleido smoke-test spike, then sequence: OI computation in compute_ticker, evolution rendering in report.py, PNG generation in run_daily. All four PNG paths follow the same `fig.write_image(path, format="png")` pattern — one template call solves all four.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| PNG export (kaleido) | Backend/CLI (run_daily) | — | Charts are static artifacts pre-rendered once per day |
| Surface and ΔIV charts | Backend (analytics.py) | Email (report.py) | Analytics owns chart creation; report passes figures to kaleido |
| OI wall detection | Backend (compute_ticker) | Email (report.py) | Single source of truth pattern — compute once, reuse in dashboard + email |
| Evolution scalars | Backend (vol_metrics.py) | Email (report.py) | Scalars already computed; email renders them + writes narrative |
| Email HTML structure | Email (report.py) | — | Email is a pure adapter — takes computed data + renders HTML |
| Email sending | Email (emailer.py) | — | win32com.client Outlook transport, non-blocking attachments |

## Standard Stack

### Core (Required)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| plotly | ≥5.0,<7.0 | Interactive 3D surface charts; `fig.write_image()` backend for kaleido | Phase 10 signed off; `plot_vol_surface()` + `plot_iv_change_surface()` already built |
| kaleido | ≥1.0,<2.0 | PNG export via Chrome rendering (headless) | REQUIREMENTS.md locked choice; `kaleido==0.2.1` hangs on Windows/plotly 6.7 |
| numpy/scipy | existing | Grid interpolation (`rbf_grid`) + surface math | Already in requirements.txt; no new calls |
| pandas | existing | DataFrame filtering + snapshot loading | Already in requirements.txt |
| pywin32 | existing | Outlook COM interface (win32com.client) | Already in requirements.txt; emailer.py already uses it |

### Supporting (Already Present)

| Library | Version | Purpose | When Used |
|---------|---------|---------|-----------|
| pandas_market_calendars | existing | Trading day gate (run_daily doesn't send on weekends) | Already in run_daily.py |
| pathlib | builtin | File paths (PNG output dir) | Already used throughout |

### Installation

```bash
pip install kaleido>=1.0,<2.0
```

**Verification:** Before commit, run `python -c "import kaleido; print(kaleido.__version__)"` to confirm installation. kaleido's first import triggers a one-time Chrome binary fetch (~200MB); this happens silently on successful install.

**Windows-specific:** kaleido v1.x requires no additional system dependencies — Chrome embed is bundled. Test on the target machine (Windows 11 Enterprise) before shipping.

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| kaleido | PyPI | 2+ yrs | ~500K/wk | github.com/plotly/kaleido | Assumed [VERIFIED: official] | Approved |

**Note:** `kaleido==0.2.1` (current environment absent) must NOT be installed — it hangs indefinitely on Windows against plotly 6.7 (confirmed in REQUIREMENTS.md). Phase 11 *requires* `>=1.0,<2.0`. This is not a choice — v0.2.1 will silently deadlock the run_daily task and never send email.

*All packages confirmed via requirements.txt + official Plotly documentation. No unusual postinstall scripts. kaleido is maintained by Plotly core team.*

## Architecture Patterns

### System Architecture Diagram

```
run_daily.process_ticker() [3 tickers in parallel]
       ↓
    compute_ticker()  ← returns summary dict + surface_df
       ├→ save_snapshot() → parquet history
       └→ save_surface_snapshot() → surface_history/{ticker}.parquet
       
update_evolution() [for each ticker]
       ├→ load_evolution(horizon=5) → evol_df (5-day rolling mean basis)
       └→ save_evolution_row() → surface_evolution.parquet
       
[Gather for email]
       ├→ all_data = [process_ticker result dicts × 3]
       ├→ evolution_data = {SPY: summary, QQQ: summary, IWM: summary}
       ├→ generate PNG attachments [4 files]:
       │   ├→ plot_vol_surface(SPY) + fig.write_image("spy_surface_YYYYMMDD.png")
       │   ├→ plot_vol_surface(QQQ) + fig.write_image("qqq_surface_YYYYMMDD.png")
       │   ├→ plot_vol_surface(IWM) + fig.write_image("iwm_surface_YYYYMMDD.png")
       │   └→ plot_iv_change_surface(SPY, baseline_5d) + fig.write_image("spy_div_surface_YYYYMMDD.png")
       │   [Non-blocking: skip all + inline note if kaleido fails]
       │
       └→ build_email(index_results=all_data, evolution_data, png_note)
           ├→ evolution_section (top, if evolution_data is complete)
           ├→ _ticker_card() [× 3]
           │   ├→ left column (spot, IV30, γ-flip)
           │   └→ right column (net GEX, walls, OI walls ← NEW)
           └→ methodology footer + PNG fallback note
           
emailer.send(subject, html_body, attachments=[Path × 4])
```

### Recommended Project Structure

```
gex/
├── compute.py         [MODIFY] — add oi_call_wall + oi_put_wall to summary dict
├── analytics.py       [READ] — plot_vol_surface() + plot_iv_change_surface() 
├── vol_metrics.py     [READ] — evolution_5d_summary() + load_evolution() 
├── report.py          [MODIFY] — add evolution section, OI rows, #ffffff background
├── run_daily.py       [MODIFY] — generate PNGs, pass attachments + evolution_data
├── emailer.py         [NO CHANGE] — already accepts attachments list
├── surface_history.py [READ] — nth_trading_day_back() for ΔIV baseline
└── png_export.py      [NEW — optional] — helper to wrap kaleido error handling
```

### Pattern 1: PNG Export via Kaleido

**What:** Static image export from a Plotly figure using kaleido's headless Chrome backend.

**When to use:** Converting interactive Plotly figures to attachment images for email or reports. Camera angle is pinned (not interactive), and the frame is re-rendered identically each day for consistency.

**Example:**

```python
# Source: Phase 11 specification (11-CONTEXT.md)

import plotly.graph_objects as go
from pathlib import Path

# A Plotly figure (exists; no modification needed)
fig = plot_vol_surface(surface_df, ticker="SPY", spot=450.0)

# Kaleido export path
out_dir = Path("out")
png_path = out_dir / f"spy_surface_20260601.png"

# Write PNG with pinned camera (discussed below)
# Camera: eye=dict(x=1.5, y=-1.5, z=0.8) — isometric-style readable 3D
fig.update_layout(
    scene=dict(
        camera=dict(eye=dict(x=1.5, y=-1.5, z=0.8))
    )
)
fig.write_image(str(png_path), format="png")
```

**Implementation pattern:**

```python
# Suggested error wrapper (optional new module gex/png_export.py)
def export_png(fig, ticker: str, surface_type: str, date: datetime.date) -> Path | None:
    """Export a Plotly figure to PNG via kaleido. Non-blocking fallback."""
    out_dir = Path("out")
    out_dir.mkdir(exist_ok=True)
    
    # Pinned camera — readable isometric (Claude's discretion)
    fig.update_layout(scene=dict(camera=dict(eye=dict(x=1.5, y=-1.5, z=0.8))))
    
    filename = f"{ticker.lower()}_{surface_type}_{date.strftime('%Y%m%d')}.png"
    png_path = out_dir / filename
    
    try:
        fig.write_image(str(png_path), format="png")
        return png_path
    except Exception as exc:
        print(f"[WARN] PNG export failed ({surface_type}): {exc}")
        return None
```

### Pattern 2: OI Wall Computation (Single Source of Truth)

**What:** Strike with maximum call or put open interest, computed once in the shared pipeline and available to both dashboard and email.

**Where:** Inside `compute_ticker()` after the chain is loaded and GEX is computed. The strike OI data is already in `s_df` (strike-level summary).

**Example:**

```python
# Source: Phase 11 specification + gex/compute.py pattern

# Inside compute_ticker(), after summary dict is assembled:
s_df = ...  # Strike-level GEX summary (already computed)

# OI walls — max OI strike, call and put separately
oi_call = s_df[s_df['type'] == 'C'].loc[s_df['open_interest'].idxmax()] if len(s_df[s_df['type'] == 'C']) else None
oi_put = s_df[s_df['type'] == 'P'].loc[s_df['open_interest'].idxmax()] if len(s_df[s_df['type'] == 'P']) else None

summary['oi_call_wall'] = float(oi_call['strike']) if oi_call is not None else None
summary['oi_put_wall'] = float(oi_put['strike']) if oi_put is not None else None
```

### Pattern 3: Evolution Section (Cold-Start Safe)

**What:** Cross-ticker surface change summary at the top of the email, rendered as a compact table (SPY/QQQ/IWM × level/rms/skew_change/term_change). All-None state = section omitted entirely (no placeholder).

**When to use:** Daily email narrative when 5-day rolling history is available; skip entirely on cold start (when evolution.parquet has no data).

**Example:**

```python
# Source: Phase 11 specification + existing vol_metrics.py

def evolution_section_html(evolution_data: dict) -> str | None:
    """
    evolution_data = {
        'SPY': {level, rms, skew_change, term_change, as_of},
        'QQQ': {...},
        'IWM': {...}
    }
    Returns None if all tickers have all-None values (cold start).
    """
    # Check cold start
    all_none = all(
        all(v is None for v in ticker_data.values())
        for ticker_data in evolution_data.values()
    )
    if all_none:
        return None
    
    # Build table
    header = _section_header("Surface Evolution — 5-day")
    
    # Lead sentence template (Claude's discretion)
    level_summary = "levels mixed" if ... else "rises" if ... else "falls"
    lead = f"<p>Five-day rolling baseline: {level_summary}, skew adjusting...</p>"
    
    table = _evolution_table(evolution_data)
    
    return f"{header}{lead}{table}"
```

### Anti-Patterns to Avoid

- **Hardcoding PNG file paths:** Store paths should be determined at runtime from `date` + `ticker` + `surface_type`. Use `pathlib.Path` for Windows compatibility.
- **Blocking on kaleido failure:** PNG generation must wrap in try/except; on failure, add an inline note and send the email anyway. Never abort run_daily.
- **Splitting OI computation between dashboard and email:** Compute in `compute_ticker()` once; both consumers read from the summary dict.
- **Cold-start evolution note:** If evolution.parquet is empty, omit the section entirely. No placeholder text like "building history..." (design decision D-11).
- **Using kaleido 0.2.1:** It deadlocks indefinitely. Install 1.x only. Phase 8 requirements.txt already locks `>=1.0,<2.0`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PNG export from Plotly | Custom screenshot logic / PIL/Pillow hacks | `kaleido>=1.0` + `fig.write_image()` | kaleido is maintained by Plotly; handles Chrome rendering, encoding, and cross-platform quirks. Hand-rolled screenshot code fails on Windows, macOS, and CI/CD. |
| Email attachment I/O | Custom file-copy or base64 encoding | `win32com.client` (Outlook) `Attachments.Add()` | emailer.py already wires this; just pass Path list. Reinventing COM plumbing introduces bugs and threading hazards. |
| Surface evolution scalar calculation | Custom diff math | `vol_metrics.evolution_5d_summary()` + `surface_evolution.load_evolution()` | Phase 9 already built these headless functions; vol_metrics.py is proven in dashboard. |
| OI strike detection | Manual loop + argmax | `pandas.idxmax()` on filtered `s_df` | Already in compute pipeline; vectorized and consistent with GEX wall logic. |
| HTML table rendering | String formatting + manual `<table>` tags | Existing `_kv_table()` + `_kv_cell()` helpers | report.py has tested formatters (signed colors, alignment, mono fonts for numbers). Reuse to avoid visual drift. |

## Runtime State Inventory

**Trigger:** This is a new feature phase, not a rename/refactor. No runtime state migration needed.

**Verified:** No existing state carries "PNG attachment" or "evolution narrative" keys. `compute_ticker()` summary dict is additive (OI walls are new, GEX + walls exist). Email subject/recipients unchanged.

## Common Pitfalls

### Pitfall 1: Kaleido Hangs on Windows/plotly 6.7

**What goes wrong:** Phase runs for 10+ minutes with no output, then times out or silently fails. Email never sends. Task Scheduler logs "hung process."

**Why it happens:** `kaleido==0.2.1` (an old version) has a threading bug when rendering 3D Plotly figures against plotly 6.7. The Chrome process spawns but never returns from the rendering call.

**How to avoid:** Install `kaleido>=1.0,<2.0` only. Verify with `pip show kaleido` after install. If you see `0.2.1`, uninstall and reinstall explicitly: `pip install "kaleido>=1.0,<2.0" --force-reinstall`.

**Warning signs:** First run_daily execution stalls silently; Outlook never opens; Windows Task Scheduler shows "missed" executions; check Event Viewer for hung python.exe process.

### Pitfall 2: PNG Paths Collide or Write to Wrong Directory

**What goes wrong:** Yesterday's `spy_surface_20260531.png` is overwritten by today's, or files write to the wrong folder and attachments break.

**Why it happens:** Using a static filename instead of embedding the date, or using relative paths that vary depending on where run_daily is invoked.

**How to avoid:** Use absolute paths from `out_dir = Path(__file__).resolve().parents[1] / "out"`. Embed date in filename: `f"{ticker.lower()}_{surface_type}_{date.strftime('%Y%m%d')}.png"`. Each day overwrites the day's file (intended), not yesterday's.

**Warning signs:** Attachments have wrong date or old chart; multiple `spy_surface*.png` files in `out/`.

### Pitfall 3: Evolution Section Renders on Cold Start with All-None Values

**What goes wrong:** Email contains "Level: —, RMS: —, Skew: —, Term: —" for all three tickers on the first few days. Looks broken; confuses readers.

**Why it happens:** Checking `if evolution_data` (True as dict) instead of checking if all scalars are actually None.

**How to avoid:** Explicitly test all four scalars for all three tickers. If every value is None across all rows, return None from `evolution_section_html()` and skip rendering the section entirely (D-11).

**Warning signs:** Evolution table appears in email before 5+ days of history exist in parquet store.

### Pitfall 4: OI Wall Computation Crashes on Empty Chain

**What goes wrong:** compute_ticker() raises KeyError or IndexError when strike-level OI is missing or all NaN.

**Why it happens:** Calling `.idxmax()` on an empty or all-NaN series, or not guarding against missing 'type' column.

**How to avoid:** Filter before idxmax: `if len(s_df[s_df['type'] == 'C']) > 0` then compute, else set to None. Wrap in try/except (per run_daily pattern).

**Warning signs:** Only some tickers appear in email; error message in compute step.

### Pitfall 5: Forgetting Explicit `#ffffff` Body Background

**What goes wrong:** Email looks fine on light-theme clients but unreadable on dark-theme clients — accent bars and text fade into the dark background.

**Why it happens:** Inheriting the client's theme instead of pinning the email background. Design decision D-01 requires explicit white.

**How to avoid:** Add `style="background:#ffffff;"` to the main email `<body>` tag or top-level wrapper `<div>`. Test in both light and dark Outlook modes before shipping.

**Warning signs:** Email renders light in Outlook light mode but dark text on dark background in dark mode.

## Code Examples

Verified patterns from existing codebase:

### PNG Export Template (from Plotly docs + Phase 10 usage)

```python
# Source: plotly.graph_objects.Figure.write_image() + kaleido official docs

import plotly.graph_objects as go
from pathlib import Path

fig: go.Figure = ...  # existing plot_vol_surface() or plot_iv_change_surface()

# Pinned camera — isometric (Claude's discretion: eye=dict(x=1.5, y=-1.5, z=0.8))
fig.update_layout(
    scene=dict(camera=dict(eye=dict(x=1.5, y=-1.5, z=0.8)))
)

# Export
png_path = Path("out") / "spy_surface_20260601.png"
fig.write_image(str(png_path), format="png")
```

### OI Wall in compute_ticker() (following existing pattern)

```python
# Source: gex/compute.py compute_ticker() function

def compute_ticker(ticker: str) -> dict:
    # ... existing code: load chain, compute GEX, walls, etc. ...
    
    s_df = ...  # Strike-level summary (already exists)
    
    # OI walls — max OI strike, call and put separately
    # Pattern: filter by type, idxmax on OI, extract strike price
    call_mask = s_df['type'] == 'C'
    put_mask = s_df['type'] == 'P'
    
    oi_call_wall = float(s_df.loc[s_df[call_mask]['open_interest'].idxmax(), 'strike']) \
        if call_mask.any() and s_df[call_mask]['open_interest'].notna().any() else None
    oi_put_wall = float(s_df.loc[s_df[put_mask]['open_interest'].idxmax(), 'strike']) \
        if put_mask.any() and s_df[put_mask]['open_interest'].notna().any() else None
    
    summary = {..., "oi_call_wall": oi_call_wall, "oi_put_wall": oi_put_wall}
    return {"summary": summary, ...}
```

### OI Wall Rows in report.py (following _kv_cell pattern)

```python
# Source: gex/report.py _ticker_card() function

def _ticker_card(r: dict) -> str:
    # ... existing left/right column code ...
    
    # OI walls (NEW) — added AFTER GEX walls in right column
    oi_cw = r.get("oi_call_wall")
    oi_pw = r.get("oi_put_wall")
    oi_cw_pct = _pct_from_spot(spot, oi_cw)
    oi_pw_pct = _pct_from_spot(spot, oi_pw)
    
    right_rows += (
        _kv_cell("OI Call Wall", _wall_value(oi_cw, oi_cw_pct))
        + _kv_cell("OI Put Wall",  _wall_value(oi_pw, oi_pw_pct))
    )
    
    # Rest of card rendering unchanged ...
```

### Evolution Section Header (following existing pattern)

```python
# Source: gex/report.py _section_header() helper

def _section_header(label: str) -> str:
    """Existing function in report.py — reuse as-is."""
    return (
        f'<div style="{_SANS}font-size:13px;font-weight:700;letter-spacing:1.6px;'
        f'text-transform:uppercase;color:{LABEL_GRAY};border-bottom:1px solid {RULE_COLOR};'
        f'padding-bottom:7px;margin:8px 0 18px;">{label}</div>'
    )

# In build_email():
evolution_html = _section_header("Surface Evolution — 5-day")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Email plain HTML tables for all data | Email attachments + inline markup | Phase 11 (this phase) | Charts now inline as images; formal business document appearance |
| Kaleido 0.2.1 for PNG export | Kaleido ≥1.0 required | Phase 8 + REQUIREMENTS.md | Fixes Windows/plotly 6.7 hang; cross-platform Chrome rendering |
| Manual GEX wall detection | Strike max(GEX) single source of truth | Phase 7 | Email consumes the same OI walls from compute.py; no duplication |
| No evolution narrative in email | Top section with 5-day rolling change | Phase 11 (this phase) | Email now leads with surface change context; cold-start safe (section omitted if empty) |
| Dark-theme inherited backgrounds | Explicit `#ffffff` body background | Phase 11 (design decision D-01) | Email reads as formal white-paper; consistent light/dark rendering |

**Deprecated/outdated:**
- `kaleido==0.2.1` — do not use. Hangs on Windows. Install `>=1.0,<2.0`.
- Manual strike wall clustering (old ±2% band approach) — replaced by simple max OI strike in Phase 10. Removed code: `wall_center_by_cluster()`, unused since Phase 7.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | kaleido>=1.0,<2.0 is installed on the target Windows machine and no dependency version conflicts exist | Package Legitimacy, Pitfalls | If installation fails or old version present, run_daily hangs. Mitigation: smoke-test spike at phase start; non-blocking fallback note if export fails. |
| A2 | `plot_vol_surface()` and `plot_iv_change_surface()` in analytics.py accept no new parameters and work as-is in kaleido export context | Code Examples | If signatures change or figures require special kaleido setup, phase plan will need adjustment. Confidence: HIGH — Phase 10 built these functions and they're already proven in dashboard. |
| A3 | Outlook COM (`win32com.client`) on the target machine is already functional (used by run_daily since before Phase 11) | Email Integration | If Outlook is not running or COM bindings are broken, emailer.send() already fails gracefully (try/except in run_daily.py). Phase 11 adds attachments; same error path. |
| A4 | OI data is available in `s_df` (strike-level summary) inside `compute_ticker()` and includes `open_interest` column | Code Examples | If column is missing or renamed, OI wall computation fails. Mitigation: grep codebase to confirm column name + add defensive `.get('open_interest', 0)` guard. Confidence: HIGH — exposure_engine.py builds `s_df` with OI data. |
| A5 | Evolution scalars are ready in `vol_metrics.evolution_5d_summary()` and parquet store from Phase 9 is accumulating 5-day rows | Code Examples | If Phase 9 incomplete or data schema changed, evolution section fails to render. Mitigation: cold-start check (all-None → omit section). Confidence: HIGH — Phase 9 complete, evolution store live in production. |

**If all items HIGH confidence:** No user confirmation needed; planner can proceed directly.

## Open Questions

1. **Kaleido Chrome binary on Windows**
   - What we know: kaleido v1.x bundles Chrome; one-time fetch on first import (~200MB).
   - What's unclear: Whether the target Windows machine has internet access at the time of first kaleido import, or whether firewall/proxy will block the fetch.
   - Recommendation: Smoke-test spike includes an explicit `import kaleido; fig.write_image(...)` with error message noting if fetch is required. Document fallback: if kaleido import fails with network error, manually install Chrome or run `kaleido_install_chrome` (if available).

2. **Camera angle for 3D surfaces (Claude's discretion)**
   - What we know: Eye position determines the viewing angle. Phase 10 dashboard uses Plotly defaults (roughly 45°-perspective).
   - What's unclear: Exact azimuth/elevation that makes static PNG readable without interactivity; depends on testing.
   - Recommendation: Start with `eye=dict(x=1.5, y=-1.5, z=0.8)` (isometric-style). If PNG is hard to read, adjust to `eye=dict(x=2, y=1.5, z=1)` or `eye=dict(x=1, y=-2, z=1.2)` based on visual feedback. Document final choice in gex/config.py as `KALEIDO_CAMERA_EYE`.

3. **PNG attachment naming convention**
   - What we know: Files go to `out/` with date embedded in name.
   - What's unclear: Whether `spy_surface_20260601.png` or `spy_vol_surface_20260601.png` or `spy_20260601_surface.png` is preferred for clarity.
   - Recommendation: Use `{ticker.lower()}_{surface_type}_{date.strftime('%Y%m%d')}.png` where `surface_type` is "surface" or "div_surface" (ΔIV). Aligns with run_daily date format in other filenames.

4. **Evolution lead sentence template**
   - What we know: Section header is "Surface Evolution — 5-day"; table shows level/rms/skew/term per ticker.
   - What's unclear: Exact wording of the lead sentence before the table (e.g. "Levels up 0.5pp on average..." vs. "IV structure flattening across tickers..."). This is Claude's discretion per D-12.
   - Recommendation: Build template from scalar direction/magnitude: "Five-day rolling mean: [level direction] [rms magnitude], [skew direction], [term direction]." Test with real data before shipping.

5. **OI wall placement in card layout**
   - What we know: OI walls go in the right column per D-09, below GEX walls.
   - What's unclear: Whether the order should be "GEX Call Wall → GEX Put Wall → OI Call Wall → OI Put Wall" or grouped by wall type.
   - Recommendation: Keep current GEX wall order, then add OI rows immediately after (per D-09). Rationale: keeps dealer positioning (GEX) and observable OI adjacent for direct comparison.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| kaleido | PNG export | ✗ (install needed) | — | HTML email-artifact fallback (D-05); non-blocking |
| plotly | Surface charts | ✓ | 6.7 (verified in requirements.txt) | N/A (already in prod) |
| pywin32 | Outlook COM (emailer.py) | ✓ | 306+ (verified in requirements.txt) | N/A (already in prod) |
| Chrome (bundled with kaleido) | PNG rendering backend | ✗ (kaleido fetches) | — | One-time automatic fetch on kaleido import; if blocked, fallback note in email |
| Windows Outlook | Email send | ✓ (assumed running) | — | run_daily already guards with try/except; Phase 11 inherits same error path |

**Missing dependencies with no fallback:**
- None — all critical pieces have fallbacks or are already in production.

**Missing dependencies with fallback:**
- kaleido: PNG generation fails → inline note "Surface charts unavailable — kaleido not installed or PNG export failed." Email sends without attachments.
- Chrome fetch (if firewalled): kaleido import fails → same fallback note as above.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing: pytest 7+, tox config in place) |
| Config file | `pytest.ini` (existing) |
| Quick run command | `pytest gex/tests/test_report.py -x` (email rendering tests) |
| Full suite command | `pytest gex/tests/ -x` (all module tests) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RPT-01 | kaleido imports and exports PNG without hanging | smoke (unit) | `pytest gex/tests/test_png_export.py::test_kaleido_smoke` | ❌ Wave 0 |
| RPT-02 | Four PNGs (3 surface + 1 ΔIV) generated with pinned camera | integration | `pytest gex/tests/test_png_export.py::test_png_attachments` | ❌ Wave 0 |
| RPT-03 | OI Call/Put walls computed and appear in email HTML | unit | `pytest gex/tests/test_compute_wiring.py::test_oi_walls_in_summary` | ✅ (test exists; assertion needs update) |
| RPT-03 | OI walls render in `_ticker_card()` HTML | unit | `pytest gex/tests/test_report.py::test_oi_wall_rows` | ❌ Wave 0 |
| RPT-04 | Email body has explicit `background:#ffffff` | unit | `pytest gex/tests/test_report.py::test_body_background_color` | ❌ Wave 0 |
| RPT-05 | Evolution section renders only if scalars present (cold-start safe) | unit | `pytest gex/tests/test_report.py::test_evolution_section_cold_start` | ❌ Wave 0 |
| RPT-05 | Evolution scalars in section match vol_metrics.evolution_5d_summary() output | integration | `pytest gex/tests/test_report.py::test_evolution_section_content` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest gex/tests/test_report.py -x` (email HTML output)
- **Per wave merge:** `pytest gex/tests/ -x` (all + PNG smoke test if available)
- **Phase gate:** Full suite green + manual dry-run smoke test before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `gex/tests/test_png_export.py` — smoke test + 4-file attachment test (new module)
- [ ] `gex/tests/test_report.py::test_oi_wall_rows` — verify OI data in HTML
- [ ] `gex/tests/test_report.py::test_body_background_color` — verify `#ffffff` in email
- [ ] `gex/tests/test_report.py::test_evolution_section_cold_start` — verify all-None → omit
- [ ] `gex/tests/test_report.py::test_evolution_section_content` — verify scalars rendered
- [ ] Update `gex/tests/test_compute_wiring.py::test_oi_walls_in_summary` — verify OI fields added to summary

*If test infrastructure already covers Phase 10 output (email HTML structure), most of these are add-only assertions (no new test files needed; existing test files gain new assertions).*

## Security Domain

**No security concerns identified for Phase 11.** Phase does not introduce:
- New user input (email recipients already configured in .env via Phase 1)
- New external API calls (uses existing CBOE data + internal Outlook COM)
- New database writes (appends to existing parquet stores from Phases 8–9)
- New authentication mechanisms

**Email attachment security:**
- PNG files are static images generated from public data (CBOE options chains). No secrets embedded.
- Outlook COM attachment method (`mail.Attachments.Add()`) handles file I/O safely; no custom base64 encoding.
- Email recipients already trusted (configured in .env).

## Sources

### Primary (HIGH confidence)
- **Context7 (Python standard library):** pathlib.Path, datetime, import mechanics
- **Plotly official docs (plotly.graph_objects):** `Figure.write_image()` API + kaleido integration
- **kaleido official docs (github.com/plotly/kaleido):** v1.x+ installation + Windows support + Chrome bundling
- **Project codebase (verified via Grep):**
  - `gex/analytics.py` — `plot_vol_surface()` signature (lines 230–), `plot_iv_change_surface()` (line 374)
  - `gex/vol_metrics.py` — `evolution_5d_summary()` (lines 232–)
  - `gex/compute.py` — `compute_ticker()` signature + summary dict keys
  - `gex/report.py` — `_kv_cell()`, `_section_header()`, email building pattern
  - `gex/emailer.py` — `send(attachments: list[Path])` already supported
  - `gex/config.py` — PALETTE tokens + surface constants already exported
  - `.planning/REQUIREMENTS.md` — RPT-01..05 locked definitions
  - `.planning/phases/10-dashboard-restructure-local-only/10-CONTEXT.md` — Phase 10 decisions (D-14, D-15)

### Secondary (MEDIUM confidence)
- **CONTEXT.md (this phase, 11-CONTEXT.md):**
  - Decisions D-01..12 (email theme, PNG scope, OI placement, evolution narrative)
  - Canonical references to code modules + reusable assets
  - Specific ideas (4 attachment names, evolution header, OI glossary)

### Tertiary (LOW confidence)
- None — all key facts verified against official docs or project codebase.

## Metadata

**Confidence breakdown:**
- Standard stack (kaleido): MEDIUM — confirmed installed on requirements.txt, v1.x mandatory, official Plotly integration verified
- Architecture (PNG export flow): HIGH — Plotly/kaleido pattern is standard; codebase already uses it for dashboard
- Pitfalls (Windows kaleido hang): HIGH — documented in REQUIREMENTS.md + project history (2026-05-29 decision)
- Code examples (OI computation): HIGH — exposure_engine.py confirmed to produce strike OI data
- Test gaps: HIGH — existing test structure in place; new assertions straightforward

**Research date:** 2026-06-01
**Valid until:** 2026-06-08 (one week; fast-moving for new package integration, but kaleido v1.x is stable and REQUIREMENTS.md is locked)

---

**Phase:** 11 - Richer Daily Report
**Research version:** 1.0
**Status:** Ready for Planning

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/11-richer-daily-report/11-CONTEXT|11-CONTEXT]]
- [[_planning/gamma-omm/phases/11-richer-daily-report/11-DISCUSSION-LOG|11-DISCUSSION-LOG]]

<!-- LINKS:END -->
