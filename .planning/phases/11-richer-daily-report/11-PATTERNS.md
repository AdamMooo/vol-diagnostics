# Phase 11: Richer Daily Report - Pattern Map

**Mapped:** 2026-06-01  
**Files analyzed:** 5 new/modified files  
**Analogs found:** 5 / 5 (all matched)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `gex/report.py` | report builder | request-response | `gex/report.py` (existing) | exact (in-place) |
| `gex/run_daily.py` | orchestrator | request-response | `gex/run_daily.py` (existing) | exact (in-place) |
| `gex/compute.py` | compute pipeline | CRUD | `gex/compute.py` (existing) | exact (in-place) |
| `gex/png_export.py` | utility | file-I/O | `gex/emailer.py` (error handling pattern) | utility-match |
| `requirements.txt` | config | N/A | `requirements.txt` (existing) | exact (in-place) |

## Pattern Assignments

### `gex/report.py` (report builder, request-response)

**Analog:** `gex/report.py` (lines 1–115 — existing helpers; lines 156–260 for _ticker_card pattern)

**Imports pattern** (lines 1–15):
```python
from __future__ import annotations

import datetime

from gex import config

# Sign-of-net-gex visual cue — reads from shared palette.
REGIME_COLOR = {
    "positive": config.PALETTE["positive"],
    "negative": config.PALETTE["negative"],
    "zero":     config.PALETTE["neutral"],
}
```

**Existing _kv_cell() pattern** (lines 94–108; reuse for OI rows):
```python
def _kv_cell(label: str, value: str, value_color: str | None = None,
             mono: bool = True) -> str:
    """One label/value row."""
    value_family = _MONO if mono else _SANS
    return (
        f'<tr>'
        f'<td style="{_SANS}padding:7px 12px 7px 0;font-size:12px;color:{LABEL_GRAY};'
        f'letter-spacing:0.5px;text-transform:uppercase;white-space:nowrap;">'
        f'{label}</td>'
        f'<td align="right" style="{value_family}padding:7px 0;font-size:15px;'
        f'font-weight:600;white-space:nowrap;">{value}</td>'
        f'</tr>'
    )
```

**Existing _wall_value() pattern** (lines 120–134; template for OI wall formatting):
```python
def _wall_value(level: float | None, pct_from_spot: float | None) -> str:
    """Format a wall as: '740  +0.3%' (anchor strike, distance from spot)."""
    if level is None:
        return "—"
    parts = [f"{level:,.0f}"]
    if pct_from_spot is not None:
        parts.append(
            f'<span style="font-weight:600;margin-left:10px;font-size:13px;">'
            f'{_fmt_pct(pct_from_spot)}</span>'
        )
    return "".join(parts)
```

**Existing _section_header() pattern** (lines 265–270; for "Surface Evolution — 5-day"):
```python
def _section_header(label: str) -> str:
    return (
        f'<div style="{_SANS}font-size:13px;font-weight:700;letter-spacing:1.6px;'
        f'text-transform:uppercase;color:{LABEL_GRAY};border-bottom:1px solid {RULE_COLOR};'
        f'padding-bottom:7px;margin:8px 0 18px;">{label}</div>'
    )
```

**Build_email() signature pattern** (lines 275–279):
```python
def build_email(
    index_results: list[dict],
    purpose_results: list[dict] | None = None,
    date: datetime.date | None = None,
) -> str:
```
**Modification:** Add parameters `evolution_data: dict | None = None` and `png_note: str | None = None`.

**_ticker_card() right-column insertion point** (lines 220–229):
```python
# Right column: dealer positioning + wall context
right_rows = (
    _kv_cell("Net GEX", _fmt_b(net_gex), value_color=_signed_color(net_gex))
    + _kv_cell("Hedge Shares/$1", _fmt_hedge_shares(r.get("delta_hedge_flow")))
    + _kv_cell("Skew (25Δ)", _fmt_skew(r.get("front_skew")))
    + _kv_cell("Call Wall", _wall_value(cw, cw_pct))
    + _kv_cell("Put Wall",  _wall_value(pw, pw_pct))
    + _kv_cell("Range", ...)
    # ← INSERT OI rows here (below GEX walls per D-09)
)
```

**HTML body with explicit #ffffff background** (line 352):
```python
<body style="{_SANS}margin:0;padding:0;">
# CHANGE TO:
<body style="{_SANS}margin:0;padding:0;background:#ffffff;">
```

---

### `gex/run_daily.py` (orchestrator, request-response)

**Analog:** `gex/run_daily.py` (existing)

**Orchestration pattern** (lines 49–113):
```python
def run(dry_run: bool = False) -> None:
    today = datetime.datetime.now(ET).date()

    if not is_trading_day(today):
        print(f"[gex-daily] {today} is not a NYSE trading day — skipping.")
        return

    print(f"[gex-daily] {today}  tickers: {', '.join(ALL_TICKERS)}")
    OUT_DIR.mkdir(exist_ok=True)

    all_data: list[dict] = []
    for ticker in ALL_TICKERS:
        print(f"  {ticker}...", end=" ", flush=True)
        data = process_ticker(ticker)
        all_data.append(data)
        # ... save snapshots ...

    # Evolution step (lines 73–80) — non-blocking pattern:
    print("\n[run_daily] Computing surface evolution...")
    from gex.surface_evolution import update_evolution
    for ticker in INDEX_TICKERS:
        try:
            rows = update_evolution(ticker, today)
            print(f"  {ticker}: {rows} evolution row(s) written")
        except Exception as exc:
            print(f"  [WARN] {ticker} evolution failed (non-blocking): {exc}")
```

**Email building** (lines 88–93):
```python
subject = f"GEX Report — {today.strftime('%b %d, %Y').replace(' 0', ' ')}"
html = rpt.build_email(
    index_results=index_results,
    purpose_results=[],
    date=today,
)
```

**Modification: Insert PNG generation step** (after evolution, before email build):
```python
# Non-blocking PNG generation (wrap in try/except per Pitfall 2 in RESEARCH.md)
attachments = []
png_note = None
try:
    # Generate 4 PNGs: 3 × surface + 1 × ΔIV (see png_export pattern below)
    # attachments = [Path(...), Path(...), Path(...), Path(...)]
except Exception as exc:
    print(f"[WARN] PNG generation failed (non-blocking): {exc}")
    png_note = "Surface charts unavailable — kaleido not installed or PNG export failed."
```

**Error handling pattern** (lines 101–105; non-blocking, don't abort on failure):
```python
try:
    emailer.send(subject=subject, html_body=html)
    print("[gex-daily] Email sent.")
except Exception as exc:
    print(f"[gex-daily] Email failed: {exc}")
```

**Emailer.send() call signature update** (line 102):
```python
# CURRENT:
emailer.send(subject=subject, html_body=html)

# CHANGE TO:
emailer.send(subject=subject, html_body=html, attachments=attachments)
```

---

### `gex/compute.py` (compute pipeline, CRUD)

**Analog:** `gex/compute.py` (existing)

**Summary dict assembly pattern** (lines 77–92):
```python
summary = summarise(
    s_df, p_df,
    spot=snapshot.spot,
    delta_hedge_flow=delta_hedge_flow,
)
summary["ticker"] = ticker
summary["iv30"] = snapshot.iv30
summary["price_change_pct"] = snapshot.price_change_pct
summary["front_skew"] = front_skew
summary["coverage_pct"] = surface_diag["coverage_pct"]
# ... more additive keys ...
```

**Modification: Add OI walls before return** (insert after line 92, before return statement):
```python
# OI walls — max OI strike, call and put separately
# s_df is already available (created line 56-57)
call_mask = s_df['type'] == 'C'
put_mask = s_df['type'] == 'P'

oi_call_wall = None
oi_put_wall = None
if call_mask.any() and s_df[call_mask]['open_interest'].notna().any():
    oi_call_wall = float(s_df.loc[s_df[call_mask]['open_interest'].idxmax(), 'strike'])
if put_mask.any() and s_df[put_mask]['open_interest'].notna().any():
    oi_put_wall = float(s_df.loc[s_df[put_mask]['open_interest'].idxmax(), 'strike'])

summary["oi_call_wall"] = oi_call_wall
summary["oi_put_wall"] = oi_put_wall
```

---

### `gex/png_export.py` (utility, file-I/O) — OPTIONAL NEW MODULE

**Analog:** `gex/emailer.py` (error handling + win32com pattern; lines 1–48)

**Suggested error-handling wrapper pattern** (from RESEARCH.md Pattern 1 + emailer.py try/except):
```python
"""PNG export from Plotly figures via kaleido. Non-blocking fallback on failure."""
from __future__ import annotations

import datetime
from pathlib import Path

import plotly.graph_objects as go


def export_png(
    fig: go.Figure,
    ticker: str,
    surface_type: str,
    date: datetime.date,
    out_dir: Path | None = None,
) -> Path | None:
    """
    Export a Plotly figure to PNG via kaleido. Returns path on success, None on failure.
    
    Args:
        fig: Plotly Figure object (e.g., from plot_vol_surface or plot_iv_change_surface)
        ticker: "SPY", "QQQ", "IWM", etc.
        surface_type: "surface" or "div_surface" (ΔIV)
        date: datetime.date — embedded in filename
        out_dir: Path to output directory; defaults to repo root / "out"
    
    Returns:
        Path to saved PNG, or None if export failed.
    """
    out_dir = out_dir or (Path(__file__).resolve().parents[1] / "out")
    out_dir.mkdir(exist_ok=True)
    
    # Pinned camera — isometric-style readable 3D (Claude's discretion)
    # eye=dict(x=1.5, y=-1.5, z=0.8) suggested; adjust if needed
    fig.update_layout(
        scene=dict(
            camera=dict(eye=dict(x=1.5, y=-1.5, z=0.8))
        )
    )
    
    filename = f"{ticker.lower()}_{surface_type}_{date.strftime('%Y%m%d')}.png"
    png_path = out_dir / filename
    
    try:
        fig.write_image(str(png_path), format="png")
        return png_path
    except Exception as exc:
        # Non-blocking: log and return None; caller provides fallback note
        print(f"[WARN] PNG export failed ({surface_type}): {exc}")
        return None
```

**Integration in run_daily** (after evolution computation):
```python
from gex.png_export import export_png
from gex.analytics import plot_vol_surface, plot_iv_change_surface
from gex.surface_history import nth_trading_day_back
from gex.surface_evolution import load_evolution

attachments = []
png_note = None

try:
    # 3 × surface (SPY, QQQ, IWM)
    for ticker_idx, ticker in enumerate(INDEX_TICKERS):
        data = all_data[ticker_idx]
        surface_df = data.get("surface_df")
        spot = data["summary"].get("spot")
        if surface_df is not None and spot:
            fig = plot_vol_surface(surface_df, ticker, spot)
            path = export_png(fig, ticker, "surface", today, OUT_DIR)
            if path:
                attachments.append(path)
    
    # 1 × ΔIV (SPY only, vs 5-day rolling mean)
    spy_data = all_data[0]  # SPY is first in INDEX_TICKERS
    spy_surface_df = spy_data.get("surface_df")
    spy_spot = spy_data["summary"].get("spot")
    if spy_surface_df is not None and spy_spot:
        baseline_date = nth_trading_day_back("SPY", today, 5)
        if baseline_date:
            from gex.validation import load_surface_history
            baseline_surface_df = load_surface_history("SPY", baseline_date)
            if baseline_surface_df is not None:
                baseline_spot = ...  # Load from snapshot on baseline_date
                fig = plot_iv_change_surface(
                    spy_surface_df, baseline_surface_df,
                    "SPY", spy_spot, baseline_spot,
                    label_prior=baseline_date.strftime("%b %d")
                )
                path = export_png(fig, "SPY", "div_surface", today, OUT_DIR)
                if path:
                    attachments.append(path)
except Exception as exc:
    print(f"[WARN] PNG generation failed (non-blocking): {exc}")
    png_note = "Surface charts unavailable — kaleido not installed or PNG export failed."
```

---

### `requirements.txt` (config, N/A)

**Analog:** `requirements.txt` (existing; lines 1–15)

**Current format pattern** (lines 1–15):
```
pandas>=2.0,<3.0
numpy>=1.26,<3.0
scipy>=1.13,<2.0
...
plotly>=5.0,<7.0
pywin32>=306; sys_platform == "win32"
```

**Modification: Add kaleido** (insert before plotly or after):
```
kaleido>=1.0,<2.0
```

**Note:** `kaleido==0.2.1` must NOT be used — it hangs indefinitely on Windows with plotly 6.7 (documented in RESEARCH.md Pitfalls, REQUIREMENTS.md).

---

## Shared Patterns

### Error Handling & Non-Blocking Fallbacks
**Source:** `gex/run_daily.py` (lines 40–46, 73–80, 101–105)

Apply to all PNG generation and evolution steps — wrap in try/except, log warning, never abort run_daily:
```python
try:
    # operation that might fail (PNG export, evolution computation, etc.)
except Exception as exc:
    print(f"[WARN] {operation} failed (non-blocking): {exc}")
    # Set fallback flag / note instead of raising
```

### HTML Cell Rendering
**Source:** `gex/report.py` (lines 94–134)

Reuse existing `_kv_cell()` for OI rows and evolution table cells. Pattern: label on left (uppercase, muted gray), value on right (mono font, right-aligned). Use `_wall_value()` template for strike + distance formatting.

### Configuration via config.py
**Source:** `gex/config.py` (lines 168–175 PALETTE tokens)

All color tokens already shared (PALETTE["positive"], PALETTE["negative"], PALETTE["neutral"]). No new tokens needed for Phase 11.

### Datetime & Timezone Handling
**Source:** `gex/run_daily.py` (lines 30–37)
```python
import datetime
import pytz

ET = pytz.timezone("America/New_York")
today = datetime.datetime.now(ET).date()
```
Use same pattern for all date/time operations in Phase 11 code.

---

## Evolution Section Details

### Cold-Start Safe Check
**Source:** `gex/vol_metrics.py` (lines 232–261; `evolution_5d_summary()`)

```python
def evolution_5d_summary(evol_df: pd.DataFrame) -> dict:
    """All values None when evol_df is empty."""
    if evol_df is None or evol_df.empty:
        return {
            "level": None,
            "rms": None,
            "skew_change": None,
            "term_change": None,
            "as_of": None,
        }
    # ... extract row ...
```

**In report.py:** Check if all scalar values are None for all three tickers before rendering section:
```python
def evolution_section_html(evolution_data: dict) -> str | None:
    """evolution_data = {'SPY': {...}, 'QQQ': {...}, 'IWM': {...}}"""
    all_none = all(
        all(v is None for v in ticker_data.values())
        for ticker_data in evolution_data.values()
    )
    if all_none:
        return None  # Omit section entirely on cold start
    # ... render table and lead sentence ...
```

---

## No Analog Found

None — all required patterns exist in the codebase.

---

## Metadata

**Analog search scope:** `gex/` module (9 files scanned)  
**Files with close match:** 5/5 (100%)  
**Pattern extraction date:** 2026-06-01

**Key reusable patterns identified:**
1. **Error handling:** Non-blocking try/except (run_daily.py lines 40–46, 73–80)
2. **HTML cell rendering:** Existing `_kv_cell()`, `_wall_value()`, `_section_header()` (report.py)
3. **Dict-based output:** Summary dict is canonical single source of truth (compute.py, emailer pattern)
4. **Config tokens:** PALETTE shared via config.py (no new tokens needed)
5. **PNG export via kaleido:** Standard Plotly `fig.write_image()` pattern (RESEARCH.md Pattern 1)

---

**Phase:** 11 - Richer Daily Report  
**Status:** Ready for Planning  

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/11-richer-daily-report/11-CONTEXT|11-CONTEXT]]
- [[_planning/gamma-omm/phases/11-richer-daily-report/11-DISCUSSION-LOG|11-DISCUSSION-LOG]]
- [[_planning/gamma-omm/phases/11-richer-daily-report/11-RESEARCH|11-RESEARCH]]

<!-- LINKS:END -->
