# Phase 6: Whole-Chain Computation Engine — Pattern Map

**Mapped:** 2026-05-26
**Files analyzed:** 6
**Analogs found:** 6 / 6

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `gex/vol_metrics.py` | utility (pure computation) | transform | `gex/exposure_engine.py` (`compute_skew`, `vol_surface_data`) | role-match |
| `gex/analytics.py` | utility (chart builder) | transform | `gex/analytics.py` (self — signature surgery) | exact |
| `gex/compute.py` | service (pipeline orchestrator) | request-response | `gex/compute.py` (self — key additions + dead-code removal) | exact |
| `gex/validation.py` | service (parquet store) | file-I/O | `gex/validation.py` (self — schema extension) | exact |
| `gex/tests/test_vol_metrics.py` | test | — | `gex/tests/test_exposure_engine.py` + `gex/tests/test_greeks_engine.py` | role-match |
| `streamlit_app.py` | component (rendering) | request-response | `streamlit_app.py` (self — noise cuts) | exact |

---

## Pattern Assignments

### `gex/vol_metrics.py` (utility, transform)

**Analog:** `gex/exposure_engine.py` — `compute_skew()` (lines 96–132) and `vol_surface_data()` (lines 48–93)

**Imports pattern** — copy exactly from `gex/exposure_engine.py` lines 15–20:
```python
from __future__ import annotations

import numpy as np
import pandas as pd

from gex import config
```

**Core pattern — `compute_skew_25d`** derived from `gex/exposure_engine.py` lines 96–132:
```python
def compute_skew(df: pd.DataFrame, min_dte: int = config.SKEW_MIN_DTE) -> pd.DataFrame:
    valid = df[(df["T_years"] > 0) & (df["iv"] > 0) & (df["oi"] > 0)].copy()
    valid["dte"] = valid["T_years"] * 365

    rows = []
    for expiry, grp in valid.groupby("expiry"):      # <-- group by expiry (date), not T_years
        dte = grp["dte"].iloc[0]
        if dte < min_dte:
            continue
        puts = grp[grp["type"] == "put"]
        calls = grp[grp["type"] == "call"]
        if puts.empty or calls.empty:
            continue
        put_idx = (puts["delta"] - config.SKEW_PUT_DELTA).abs().idxmin()   # SKEW_PUT_DELTA = -0.25
        call_idx = (calls["delta"] - config.SKEW_CALL_DELTA).abs().idxmin()
        put_iv = puts.loc[put_idx, "iv"] * 100
        call_iv = calls.loc[call_idx, "iv"] * 100
        rows.append({...})

    return pd.DataFrame(rows).sort_values("dte").reset_index(drop=True)
```

**Adaptation for `compute_skew_25d`:**
- Keep `groupby("expiry")` — NOT `groupby("T_years")` (float equality fragmentation)
- Add K < spot filter for puts, K >= spot for calls (existing function does not filter by moneyness)
- Bucket assignment: `dte <= 45` → `front_month`; `45 < dte <= 90` → `second_month`; else skip
- Skip bucket if already filled (take nearest qualifying expiry per bucket)
- Require `len(puts) >= 2 and len(calls) >= 2` before selecting delta target
- Use `config.SKEW_PUT_DELTA` (-0.25) for the put target delta (same constant as existing function)
- Return dict, not DataFrame: `{"front_month": {put_iv, call_iv, skew, dte} | None, "second_month": ...}`

**OTM filter pattern** — copy from `gex/exposure_engine.py` lines 68–82 (`vol_surface_data`):
```python
valid = df[
    is_otm &
    (df["T_years"] > 0) &
    (df["iv"] > 0) &
    (df["oi"] > 0) &
    ...
].copy()
valid["dte"] = valid["T_years"] * 365
```

**`compute_term_structure` ATM selection** — adapt nearest-strike logic from `idxmin()` pattern:
```python
# ATM per expiry: call side preferred, minimize |K - spot|
atm_calls = grp[grp["type"] == "call"]
if not atm_calls.empty:
    atm_idx = (atm_calls["strike"] - spot).abs().idxmin()
    atm_iv = float(atm_calls.loc[atm_idx, "iv"] * 100)
```

**`compute_rv20` formula** — no existing analog; use research-specified pattern:
```python
def compute_rv20(spot_history: pd.Series) -> float | None:
    # spot_history must arrive sorted oldest-first (ascending date)
    if len(spot_history) < 21:
        return None
    prices = spot_history.iloc[-21:].to_numpy(dtype=float)
    log_returns = np.log(prices[1:] / prices[:-1])   # 20 returns from 21 prices
    return float(np.sqrt(252) * log_returns.std(ddof=1))
```

**`compute_vrp` formula:**
```python
def compute_vrp(iv30: float | None, rv20: float | None) -> float | None:
    if iv30 is None or rv20 is None:
        return None
    return iv30 - rv20
```

**Error handling pattern** — follow `vol_surface_data` / `compute_skew` convention: return empty/None on bad input, no exceptions raised for missing data. No try/except in pure functions — validate at entry with guard clauses.

---

### `gex/analytics.py` — `plot_vol_surface()` (chart builder, transform)

**Analog:** `gex/analytics.py` itself — lines 159–340

**Current signature** (lines 159–163):
```python
def plot_vol_surface(surface_df: pd.DataFrame, ticker: str, spot: float,
                     iv30: float | None = None,
                     gamma_flip: float | None = None,
                     call_wall: float | None = None,
                     put_wall: float | None = None) -> go.Figure:
```

**Target signature after strip** — remove the 4 optional params:
```python
def plot_vol_surface(surface_df: pd.DataFrame, ticker: str, spot: float) -> go.Figure:
```

**Colorscale change** — line 234:
```python
colorscale="Plasma",   # CHANGE TO:
colorscale="Viridis",
```

**Lines to remove inside function body:**
- Line 226: `iv30_label = f" · IV30 {iv30:.1f}%" if iv30 else ""`
- The `iv30_label` usage in the title string (search for `iv30_label` in lines 260–340)
- The `_meridian_iv()` helper function definition (lines 249–254)
- The spot plane `Mesh3d` trace block (lines 257–~290 — starts with `if lm_min <= 0 <= lm_max:`)
- All `fig.add_trace(go.Scatter3d(...))` calls for gamma_flip, call_wall, put_wall meridians

**Empty-df guard pattern** (lines 178–185) — keep unchanged:
```python
if surface_df.empty or len(surface_df) < 6:
    fig = go.Figure()
    fig.update_layout(
        template="plotly_dark",
        title=f"IV Surface — {ticker}: insufficient data",
        height=480,
        margin=dict(t=50, b=10, l=10, r=10),
    )
    return fig
```

---

### `gex/compute.py` (service, request-response)

**Analog:** `gex/compute.py` itself — full file (78 lines)

**Current import block** (lines 13–16) — remove `compute_surface_slopes`:
```python
from gex.exposure_engine import (
    compute_gex, strike_gex, gamma_profile, vol_surface_data, compute_skew,
    compute_surface_slopes,   # REMOVE THIS LINE
)
```

**Add new import** after existing imports:
```python
from gex.vol_metrics import compute_skew_25d, compute_term_structure, compute_rv20, compute_vrp
from gex.validation import load_history
```

**Dead-code removal** — lines 55–56 and 73–74:
```python
slopes = compute_surface_slopes(surface_df)   # REMOVE line 55
# ...
summary["strike_slope"] = slopes.get("strike_slope")  # REMOVE line 73
summary["term_slope"] = slopes.get("term_slope")       # REMOVE line 74
```

**New key additions pattern** — follow the existing pattern at lines 69–74 (add to summary dict after `summary["iv30"] = ...`):
```python
summary["iv30"] = snapshot.iv30                 # existing — iv30 source
summary["price_change_pct"] = snapshot.price_change_pct  # existing
summary["front_skew"] = front_skew              # existing
# --- NEW keys ---
skew = compute_skew_25d(df, spot=snapshot.spot)
term_structure = compute_term_structure(df, spot=snapshot.spot)
hist = load_history(ticker)
if hist.empty or "spot" not in hist.columns:
    rv20, vrp = None, None
else:
    spot_series = hist["spot"].iloc[::-1]   # reverse to oldest-first
    rv20 = compute_rv20(spot_series)
    vrp = compute_vrp(snapshot.iv30, rv20)
```

**Return dict extension** — current line 76–77:
```python
return {"summary": summary, "s_df": s_df, "p_df": p_df,
        "spot": snapshot.spot, "surface_df": surface_df, "skew_df": skew_df}
# ADD new keys:
return {"summary": summary, "s_df": s_df, "p_df": p_df,
        "spot": snapshot.spot, "surface_df": surface_df, "skew_df": skew_df,
        "skew": skew, "term_structure": term_structure,
        "rv20": rv20, "vrp": vrp}
```

---

### `gex/validation.py` (service, file-I/O)

**Analog:** `gex/validation.py` itself — full file (89 lines)

**`_FLOAT_COLS` extension** — current lines 29–33:
```python
_FLOAT_COLS = (
    "zero_gamma_level", "call_wall", "put_wall",
    "front_skew", "put_25d_iv", "call_50d_iv", "iv30",
    "strike_slope", "term_slope",
)
# ADD rv20 and vrp:
_FLOAT_COLS = (
    "zero_gamma_level", "call_wall", "put_wall",
    "front_skew", "put_25d_iv", "call_50d_iv", "iv30",
    "strike_slope", "term_slope",
    "rv20", "vrp",   # NEW
)
```

**`row` dict extension** — current lines 47–61 (`save_snapshot`). Add after `"term_slope"` entry:
```python
"rv20": summary.get("rv20"),    # NEW — float | None
"vrp": summary.get("vrp"),      # NEW — float | None
```

**Forward-compat read pattern** — existing `_FLOAT_COLS` loop at lines 65–67 already handles new columns:
```python
for col in _FLOAT_COLS:
    if col in hist.columns:
        hist[col] = hist[col].astype("float64")
```
No change needed — old parquet rows just won't have rv20/vrp, will load as NaN.

**`load_history` note** — current function (lines 79–88) returns descending date order:
```python
hist = hist[hist["ticker"] == ticker].sort_values("date", ascending=False)
return hist.head(days).reset_index(drop=True)
```
`compute_ticker` must reverse this before passing to `compute_rv20`: `hist["spot"].iloc[::-1]`

---

### `gex/tests/test_vol_metrics.py` (test)

**Analog:** `gex/tests/test_exposure_engine.py` (primary) + `gex/tests/test_greeks_engine.py` (secondary)

**File header and import pattern** — from `gex/tests/test_exposure_engine.py` lines 1–6:
```python
"""Tests for GEX exposure in exposure_engine.py."""
import pandas as pd
import pytest

from gex.exposure_engine import compute_gex, strike_gex
```
Adapt to:
```python
"""Tests for vol_metrics.py — skew, term structure, rv20, vrp."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from gex.vol_metrics import compute_skew_25d, compute_term_structure, compute_rv20, compute_vrp
```

**Fixture pattern** — from `gex/tests/test_exposure_engine.py` lines 8–15 and `gex/tests/test_greeks_engine.py` lines 37–43:
```python
@pytest.fixture
def greek_df():
    return pd.DataFrame({
        "strike": [490.0, 490.0, 500.0, 500.0],
        "type":   ["call", "put", "call", "put"],
        "oi":     [100,    200,   150,    250],
        "gamma":  [0.01,   0.012, 0.015,  0.008],
    })
```
Adapt to a `chain_df` fixture with columns: `strike, type, oi, iv, delta, expiry, T_years`. Construct a synthetic chain where the 25Δ strikes are known (e.g., put at strike 480 with delta=-0.25, call at strike 520 with delta=+0.25).

**Class-based grouping pattern** — from `gex/tests/test_exposure_engine.py` lines 18–51:
```python
class TestComputeGex:
    def test_returns_copy_with_gex_column(self, greek_df):
        ...
    def test_calls_positive(self, greek_df):
        ...
```
Use same class-per-function grouping: `TestComputeSkew25d`, `TestComputeTermStructure`, `TestComputeRv20`, `TestComputeVrp`.

**Scalar assertion pattern** — from `gex/tests/test_analytics_summarise.py` lines 21–27:
```python
def test_summarise_keys_present(gex_df, profile_df):
    r = summarise(gex_df, profile_df, spot=500.0)
    for key in ("net_gex", "zero_gamma_level", ...):
        assert key in r
```

**Numeric precision pattern** — from `gex/tests/test_exposure_engine.py` line 36:
```python
assert abs(result.iloc[0]["gex"] - expected_first_call) < 1e-9
```
Use `pytest.approx()` for RV20 manual calculation test.

**None-propagation pattern** — from `gex/tests/test_analytics_summarise.py` line 30:
```python
assert r["delta_hedge_flow"] is None
```

---

### `streamlit_app.py` — noise cuts (component, request-response)

**Analog:** `streamlit_app.py` itself — three targeted deletion blocks

**Cut 1 — "% vs ZGL" line** at lines 93–95:
```python
# REMOVE THESE 3 LINES:
if zgl is not None and spot:
    pct = (spot - zgl) / zgl * 100
    obs.append(f"{pct:+.1f}% vs ZGL")
```
Keep the surrounding `_derive_observations` function — the Range and % today observations remain.

**Cut 2 — "Hedge Sh / $1" row** at line 156 inside `render_regime_card()`:
```html
<!-- REMOVE THIS LINE: -->
<span class="rc-k">Hedge Sh / $1</span> <span class="rc-v">{df_str}</span>
```
Also remove the `df_val` / `df_str` computation block at lines 134–139:
```python
# REMOVE lines 134-139:
df_val = summary.get("delta_hedge_flow")
if df_val is not None:
    v = abs(df_val)
    df_str = f"{v / 1e6:.1f}M sh/$1" if v >= 1e6 else f"{v / 1e3:.0f}K sh/$1"
else:
    df_str = "—"
```

**Cut 3 — slope display block** at lines 214–254 (entire block):
```python
# REMOVE lines 214-254: the strike_slope/term_slope metric block
strike_slope = s.get("strike_slope")
term_slope = s.get("term_slope")
if strike_slope is not None or term_slope is not None:
    slope_hist = _load_history_cached(ticker, days=90)
    ...
    sm1, sm2, _ = st.columns([1, 1, 2])
    ...
```

**`plot_vol_surface` call site update** — lines 205–213 (must happen alongside `analytics.py` signature change):
```python
# CURRENT (lines 205-213):
st.plotly_chart(
    plot_vol_surface(
        surface_df, ticker, spot=spot, iv30=iv30,
        gamma_flip=s.get("zero_gamma_level"),
        call_wall=s.get("call_wall"),
        put_wall=s.get("put_wall"),
    ),
    use_container_width=True,
)
# REPLACE WITH:
st.plotly_chart(
    plot_vol_surface(surface_df, ticker, spot=spot),
    use_container_width=True,
)
```

---

## Shared Patterns

### Pure function convention
**Source:** `gex/exposure_engine.py` — all top-level functions
**Apply to:** All functions in `gex/vol_metrics.py`
- No side effects, no I/O, no imports of streamlit or validation inside functions
- Return empty/None sentinel on bad input; no raised exceptions for missing data
- Operate on a `.copy()` when mutating the input DataFrame

### Config constant access
**Source:** `gex/exposure_engine.py` line 20 and usage at lines 120–121
```python
from gex import config
# ...
put_idx = (puts["delta"] - config.SKEW_PUT_DELTA).abs().idxmin()
call_idx = (calls["delta"] - config.SKEW_CALL_DELTA).abs().idxmin()
```
**Apply to:** `gex/vol_metrics.py` — use `config.SKEW_PUT_DELTA` (-0.25) rather than hardcoding the literal

### Parquet forward-compat schema
**Source:** `gex/validation.py` lines 29–34 and 65–67
```python
_FLOAT_COLS = ("zero_gamma_level", "call_wall", ...)   # extend, never rename
# read path:
for col in _FLOAT_COLS:
    if col in hist.columns:
        hist[col] = hist[col].astype("float64")
```
**Apply to:** `gex/validation.py` schema extension — add `rv20`, `vrp` to tuple only; never reorder

### `from __future__ import annotations`
**Source:** `gex/compute.py` line 1, `gex/exposure_engine.py` line 15
**Apply to:** `gex/vol_metrics.py` and `gex/tests/test_vol_metrics.py`

---

## No Analog Found

All files have close analogs. No entries.

---

## Metadata

**Analog search scope:** `gex/`, `gex/tests/`, `streamlit_app.py`
**Files read:** `gex/exposure_engine.py`, `gex/compute.py`, `gex/validation.py`, `gex/analytics.py` (lines 1–80, 159–260), `gex/tests/test_exposure_engine.py`, `gex/tests/test_analytics_summarise.py`, `gex/tests/test_greeks_engine.py`, `streamlit_app.py` (lines 80–260)
**Pattern extraction date:** 2026-05-26

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/06-computation-engine/06-CONTEXT|06-CONTEXT]]
- [[_planning/gamma-omm/phases/06-computation-engine/06-RESEARCH|06-RESEARCH]]

<!-- LINKS:END -->
