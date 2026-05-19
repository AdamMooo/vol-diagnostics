# Phase 2: Exposure + PM Flow — Pattern Map

**Mapped:** 2026-05-05
**Files analyzed:** 5 (all modifications to existing files)
**Analogs found:** 5 / 5

## File Classification

| Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---------------|------|-----------|----------------|---------------|
| `gex/exposure_engine.py` | service | transform | `gex/exposure_engine.py` (self — extend existing functions) | exact |
| `gex/analytics.py` | service | transform | `gex/analytics.py` (self — extend `summarise()`) | exact |
| `gex/validation.py` | service | file-I/O | `gex/validation.py` (self — extend `save_snapshot()`, add `load_yesterday()`) | exact |
| `gex/run_daily.py` | orchestrator | request-response | `gex/run_daily.py` (self — extend `process_ticker()`) | exact |
| `gex/report.py` | utility | transform | `gex/report.py` (self — extend `_result_row()` and table header) | exact |

All five targets are modifications of existing files. Pattern source is the file itself in every case.

---

## Pattern Assignments

### `gex/exposure_engine.py` — add `compute_vex()`, `compute_chex()`, `strike_vex()`, `strike_chex()`

**Analog:** `gex/exposure_engine.py` lines 23–43 (existing `compute_gex` / `strike_gex`)

**Imports pattern** (lines 15–20) — no new imports needed:
```python
from __future__ import annotations

import numpy as np
import pandas as pd

MULTIPLIER = 100  # shares per contract
```

**Core pattern — compute_gex (lines 23–31), the direct template:**
```python
def compute_gex(df: pd.DataFrame, spot: float) -> pd.DataFrame:
    df = df.copy()
    sign = np.where(df["type"] == "call", 1.0, -1.0)
    df["gex"] = sign * df["gamma"] * df["oi"] * MULTIPLIER * spot**2 * 0.01
    return df
```

**New functions follow this pattern exactly, with two differences:**
1. Column name: `"vanna"` / `"charm"` instead of `"gamma"`; output column `"vex"` / `"chex"` instead of `"gex"`
2. Spot scaling: `spot * 0.01` (NOT `spot**2 * 0.01`) — vanna/charm are first-order delta derivatives, not position-weighted like gamma

**Core pattern — strike_gex (lines 34–43), the aggregator template:**
```python
def strike_gex(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("strike")["gex"]
        .sum()
        .reset_index()
        .sort_values("strike")
        .reset_index(drop=True)
    )
```

`strike_vex(df)` and `strike_chex(df)` are identical — substitute `"vex"` / `"chex"` for `"gex"`.

---

### `gex/analytics.py` — extend `summarise()` signature and return dict

**Analog:** `gex/analytics.py` lines 25–61 (existing `summarise()`)

**Current signature (line 25–26):**
```python
def summarise(gex_df: pd.DataFrame, profile_df: pd.DataFrame,
              spot: float) -> dict:
```

**New signature — add optional kwargs, positional args unchanged:**
```python
def summarise(gex_df: pd.DataFrame, profile_df: pd.DataFrame,
              spot: float,
              net_vex: float | None = None,
              net_chex: float | None = None,
              delta_hedge_flow: float | None = None) -> dict:
```

**Current return dict (lines 54–61):**
```python
    return {
        "net_gex": net_gex,
        "zero_gamma_level": zero_gamma,
        "call_wall": call_wall,
        "put_wall": put_wall,
        "gamma_regime": regime,
        "spot": spot,
    }
```

**Extended return dict — append new keys, do not remove or reorder existing keys:**
```python
    return {
        "net_gex": net_gex,
        "zero_gamma_level": zero_gamma,
        "call_wall": call_wall,
        "put_wall": put_wall,
        "gamma_regime": regime,
        "spot": spot,
        "net_vex": net_vex,
        "net_chex": net_chex,
        "delta_hedge_flow": delta_hedge_flow,
    }
```

Callers that don't pass the new kwargs get `None` values — backward-compatible.

---

### `gex/validation.py` — extend `save_snapshot()`, add `load_yesterday()`

**Analog:** `gex/validation.py` lines 25–48 (existing `save_snapshot()`)

**Imports pattern (lines 1–22) — add `datetime` is already imported; no new imports for `load_yesterday` except `pandas_market_calendars` (already in `run_daily.py`; import it locally inside `load_yesterday`):**
```python
from __future__ import annotations

import datetime
import pathlib

import numpy as np
import pandas as pd
import yfinance as yf

STORE = pathlib.Path(__file__).resolve().parents[1] / "out" / "gex_snapshots.parquet"
```

**Core pattern — save_snapshot row dict (lines 27–36), extend with one field:**
```python
    row = {
        "date": datetime.date.today(),
        "ticker": ticker,
        "spot": summary["spot"],
        "net_gex": summary["net_gex"],
        "gamma_regime": summary["gamma_regime"],
        "zero_gamma_level": summary.get("zero_gamma_level"),
        "call_wall": summary.get("call_wall"),
        "put_wall": summary.get("put_wall"),
        # Phase 2 addition (EXP-04):
        "vanna_exposure": summary.get("net_vex"),
    }
```

**Idempotency pattern (lines 38–47) — unchanged, copy as-is:**
```python
    if STORE.exists():
        hist = pd.read_parquet(STORE)
        mask = (hist["date"] == row["date"]) & (hist["ticker"] == ticker)
        hist = hist[~mask]
        hist = pd.concat([hist, pd.DataFrame([row])], ignore_index=True)
    else:
        STORE.parent.mkdir(exist_ok=True)
        hist = pd.DataFrame([row])

    hist.to_parquet(STORE, index=False)
```

**New function — `load_yesterday()` — follows the never-raise contract:**
```python
def load_yesterday(ticker: str, today: datetime.date | None = None) -> pd.Series | None:
    if not STORE.exists():
        return None
    try:
        import pandas_market_calendars as mcal
        target = today or datetime.date.today()
        nyse = mcal.get_calendar("NYSE")
        sched = nyse.schedule(
            start_date=(target - datetime.timedelta(days=10)).strftime("%Y-%m-%d"),
            end_date=(target - datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
        )
        if sched.empty:
            return None
        prior_date = sched.index[-1].date()
        hist = pd.read_parquet(STORE)
        hist["date"] = pd.to_datetime(hist["date"]).dt.date  # normalize dtype (Pitfall 4)
        row = hist[(hist["date"] == prior_date) & (hist["ticker"] == ticker)]
        return row.iloc[0] if not row.empty else None
    except Exception:
        return None
```

Return type is `pd.Series | None` — direct attribute access via `row["net_gex"]` matches parquet column names without a translation layer.

**New helper — `_classify_vs_yesterday()` — pure comparison, no I/O:**
```python
def _classify_vs_yesterday(net_gex_today: float, regime_today: str,
                            prior: pd.Series) -> str:
    def _sign(r: str) -> int:
        return 1 if r == "positive" else (-1 if r == "negative" else 0)

    regime_prior = prior["gamma_regime"]
    net_gex_prior = float(prior["net_gex"])

    if _sign(regime_today) != _sign(regime_prior):
        return "FLIPPED"
    if abs(net_gex_prior) == 0:
        return "UNCHANGED"
    ratio = abs(net_gex_today) / abs(net_gex_prior)
    if ratio > 1.05:
        return "INTENSIFIED"
    elif ratio < 0.95:
        return "EASED"
    else:
        return "UNCHANGED"
```

---

### `gex/run_daily.py` — extend `process_ticker()`

**Analog:** `gex/run_daily.py` lines 43–56 (existing `process_ticker()`)

**Import additions needed at top of file:**
```python
from gex.exposure_engine import compute_gex, strike_gex, gamma_profile, compute_vex, compute_chex, strike_vex, strike_chex
from gex.validation import save_snapshot, load_yesterday, _classify_vs_yesterday
```

**Current process_ticker body (lines 43–56) — the full never-raise template:**
```python
def process_ticker(ticker: str) -> dict:
    """Returns summary + raw dataframes. Never raises — errors go in result."""
    try:
        snapshot = load_chain(ticker)
        df = add_greeks(snapshot.chains, spot=snapshot.spot, today=snapshot.as_of)
        df = compute_gex(df, spot=snapshot.spot)
        s_df = strike_gex(df)
        p_df = gamma_profile(df, spot=snapshot.spot)
        summary = summarise(s_df, p_df, spot=snapshot.spot)
        summary["ticker"] = ticker
        return {"summary": summary, "s_df": s_df, "p_df": p_df, "spot": snapshot.spot}
    except Exception as exc:
        print(f"  [WARN] {ticker}: {exc}")
        return {"summary": {"ticker": ticker, "error": str(exc)}}
```

**Extended body — new lines slot in before `summarise()` call:**
```python
def process_ticker(ticker: str) -> dict:
    """Returns summary + raw dataframes. Never raises — errors go in result."""
    try:
        snapshot = load_chain(ticker)
        df = add_greeks(snapshot.chains, spot=snapshot.spot, today=snapshot.as_of)
        df = compute_gex(df, spot=snapshot.spot)
        df = compute_vex(df, spot=snapshot.spot)
        df = compute_chex(df, spot=snapshot.spot)
        s_df = strike_gex(df)
        v_df = strike_vex(df)
        c_df = strike_chex(df)
        p_df = gamma_profile(df, spot=snapshot.spot)

        net_vex = float(v_df["vex"].sum())
        net_chex = float(c_df["chex"].sum())
        net_gex_scalar = float(s_df["gex"].sum())
        delta_hedge_flow = net_gex_scalar / (snapshot.spot * 0.01)

        summary = summarise(s_df, p_df, spot=snapshot.spot,
                            net_vex=net_vex, net_chex=net_chex,
                            delta_hedge_flow=delta_hedge_flow)
        summary["ticker"] = ticker

        prior = load_yesterday(ticker)
        if prior is not None:
            summary["vs_yesterday"] = _classify_vs_yesterday(
                summary["net_gex"], summary["gamma_regime"], prior
            )
        else:
            summary["vs_yesterday"] = None

        return {"summary": summary, "s_df": s_df, "p_df": p_df, "spot": snapshot.spot}
    except Exception as exc:
        print(f"  [WARN] {ticker}: {exc}")
        return {"summary": {"ticker": ticker, "error": str(exc)}}
```

Key: `delta_hedge_flow` is computed from `net_gex_scalar` (pre-summarise sum) to avoid referencing `summary` before assignment (Pitfall 1 from RESEARCH.md).

---

### `gex/report.py` — extend `_result_row()` and table header

**Analog:** `gex/report.py` lines 198–229 (`_result_row()`), lines 232–257 (`_build_table()`), lines 322–334 (table header in `build_email()`)

**Existing formatting helpers pattern (lines 47–72) — new helpers follow this style:**
```python
def _fmt_gex(val: float) -> str:
    b = val / 1e9
    return f"{'+'if b>=0 else ''}{b:.2f}B"

def _fmt_price(val: float | None) -> str:
    return f"{val:.2f}" if val is not None else "—"

def _fmt_distance(spot: float, zero_gamma: float | None) -> tuple[str, str]:
    if zero_gamma is None:
        return "—", "#aaa"
    pct = (spot - zero_gamma) / spot * 100
    color = "#1a7a4a" if pct >= 0 else "#c0392b"
    return f"{'+'if pct>=0 else ''}{pct:.1f}%", color
```

**New formatting helpers — add alongside existing helpers, same style:**
```python
def _fmt_delta_flow(val: float | None) -> str:
    if val is None:
        return "—"
    b = abs(val) / 1e9
    return f"${b:.1f}B/1%"

_VS_YESTERDAY_COLOR = {
    "FLIPPED":    "#c0392b",
    "INTENSIFIED": "#e67e22",
    "EASED":      "#27ae60",
    "UNCHANGED":  "#7f8c8d",
}

def _vs_yesterday_color(label: str | None) -> str:
    return _VS_YESTERDAY_COLOR.get(label or "", "#aaa")
```

**Current _result_row tail — lines 224–229 (the two cells being replaced):**
```python
        f'<td align="right" style="padding:9px 10px;font-size:13px;color:#555;">'
        f'{_fmt_price(r.get("call_wall"))}</td>'
        f'<td align="right" style="padding:9px 10px;font-size:13px;color:#555;">'
        f'{_fmt_price(r.get("put_wall"))}</td>'
        f'</tr>'
```

**Replacement tail — same padding/font-size convention, Call Wall / Put Wall removed:**
```python
        f'<td align="right" style="padding:9px 10px;font-size:13px;color:#555;">'
        f'{_fmt_delta_flow(r.get("delta_hedge_flow"))}</td>'
        f'<td align="center" style="padding:9px 10px;font-size:13px;'
        f'color:{_vs_yesterday_color(r.get("vs_yesterday"))};">'
        f'{r.get("vs_yesterday") or "—"}</td>'
        f'</tr>'
```

**Error row colspan — line 203 (`colspan="6"`) must change to `colspan="6"` — count: 7 cols total, first col is ticker, remaining 6 are data. Unchanged.**

**Group header in _build_table — line 247 (`colspan="7"`) — stays at 7 (same column count after replacing Call Wall / Put Wall):**
```python
        html += (
            f'<tr><td colspan="7" style="background:#2c3e50;color:#ecf0f1;'
            f'padding:5px 10px;font-size:10px;font-weight:bold;letter-spacing:1.5px;">'
            f'{group.upper()}</td></tr>'
        )
```

**Table header in build_email — lines 323–331 (replace last two `<th>` cells):**

Current:
```html
        <th align="right"  style="padding:11px 8px;font-weight:600;">vs Flip</th>
        <th align="right"  style="padding:11px 8px;font-weight:600;">Call Wall</th>
        <th align="right"  style="padding:11px 8px;font-weight:600;">Put Wall</th>
```

New (per D-10 column order: Ticker | Spot | Net GEX | Regime | ZGL | Δ-flow | vs-Yesterday):
```html
        <th align="right"  style="padding:11px 8px;font-weight:600;">ZGL</th>
        <th align="right"  style="padding:11px 8px;font-weight:600;">&#916;-flow</th>
        <th align="center" style="padding:11px 8px;font-weight:600;">vs-Yesterday</th>
```

---

## Shared Patterns

### Never-raise contract
**Source:** `gex/run_daily.py` lines 54–56
**Apply to:** `load_yesterday()` in `validation.py` (inner try/except), `process_ticker()` outer handler
```python
    except Exception as exc:
        print(f"  [WARN] {ticker}: {exc}")
        return {"summary": {"ticker": ticker, "error": str(exc)}}
```
`load_yesterday()` uses a silent `except Exception: return None` variant — no print, no re-raise.

### DataFrame copy-before-mutate
**Source:** `gex/exposure_engine.py` line 28
**Apply to:** `compute_vex()`, `compute_chex()`
```python
    df = df.copy()
```

### `.get()` for optional dict fields
**Source:** `gex/validation.py` lines 33–35, `gex/analytics.py` lines 83–89
**Apply to:** All `summary.get(...)` calls for the new fields in `save_snapshot()` and `report._result_row()`
```python
    "zero_gamma_level": summary.get("zero_gamma_level"),
    "call_wall": summary.get("call_wall"),
    "put_wall": summary.get("put_wall"),
```

### HTML cell padding/font-size convention
**Source:** `gex/report.py` lines 215–228
**Apply to:** Two new `<td>` cells in `_result_row()`
```
padding:9px 10px;font-size:13px
```
Align: `right` for numeric (Δ-flow), `center` for label (vs-Yesterday).

---

## No Analog Found

None — all patterns exist in the codebase. RESEARCH.md patterns are verified against live code and serve as the implementation spec directly.

---

## Critical Pitfalls (from RESEARCH.md — planner must surface in plan actions)

| Pitfall | File | Guard |
|---------|------|-------|
| `spot**2` vs `spot` in VEX/CHEX formula | `exposure_engine.py` | D-01 spec: use `spot * 0.01` |
| `delta_hedge_flow` referencing `summary` before assignment | `run_daily.py` | Compute from `s_df["gex"].sum()` pre-summarise |
| Calendar day minus one for prior trading day | `validation.py` | Use `pandas_market_calendars` schedule |
| Parquet date dtype mismatch | `validation.py` | `pd.to_datetime(hist["date"]).dt.date` before filter |
| colspan mismatch in group headers | `report.py` | Column count stays at 7 (replacing, not adding) |

---

## Metadata

**Analog search scope:** `gex/` directory (all 5 key files read in full)
**Files scanned:** 5
**Pattern extraction date:** 2026-05-05

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/02-exposure-pm-flow/02-01-PLAN|02-01-PLAN]]
- [[_planning/gamma-omm/phases/02-exposure-pm-flow/02-01-SUMMARY|02-01-SUMMARY]]
- [[_planning/gamma-omm/phases/02-exposure-pm-flow/02-02-PLAN|02-02-PLAN]]
- [[_planning/gamma-omm/phases/02-exposure-pm-flow/02-02-SUMMARY|02-02-SUMMARY]]
- [[_planning/gamma-omm/phases/02-exposure-pm-flow/02-03-PLAN|02-03-PLAN]]
- [[_planning/gamma-omm/phases/02-exposure-pm-flow/02-03-SUMMARY|02-03-SUMMARY]]
- [[_planning/gamma-omm/phases/02-exposure-pm-flow/02-04-PLAN|02-04-PLAN]]
- [[_planning/gamma-omm/phases/02-exposure-pm-flow/02-04-SUMMARY|02-04-SUMMARY]]
- [[_planning/gamma-omm/phases/02-exposure-pm-flow/02-CONTEXT|02-CONTEXT]]
- [[_planning/gamma-omm/phases/02-exposure-pm-flow/02-DISCUSSION-LOG|02-DISCUSSION-LOG]]
- [[_planning/gamma-omm/phases/02-exposure-pm-flow/02-RESEARCH|02-RESEARCH]]

<!-- LINKS:END -->
