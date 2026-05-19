# Phase 3: Streamlit Dashboard — Pattern Map

**Mapped:** 2026-05-05
**Files analyzed:** 3 (1 new, 1 modified, 1 test)
**Analogs found:** 3 / 3

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `streamlit_app.py` | orchestrator/app | request-response + CRUD | `gex/run_daily.py` | role-match (same computation sequence, different output layer) |
| `requirements.txt` | config | — | `requirements.txt` (self) | exact |
| `gex/tests/test_streamlit_app.py` | test | — | `gex/tests/test_exposure_flow.py` | exact |

---

## Pattern Assignments

### `streamlit_app.py` (app entry point, request-response + CRUD)

**Analog:** `gex/run_daily.py`

**Imports pattern** (`gex/run_daily.py` lines 10-28):
```python
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")          # MUST precede pyplot import — before any gex import too
import matplotlib.pyplot as plt

from gex.data_loader import load_chain
from gex.greeks_engine import add_greeks
from gex.exposure_engine import compute_gex, strike_gex, gamma_profile, compute_vex, compute_chex, strike_vex, strike_chex
from gex.analytics import summarise, plot_gamma_profile, plot_overview, fig_to_b64
from gex.validation import save_snapshot, load_yesterday, _classify_vs_yesterday
from gex import report as rpt
# from gex import emailer    <-- DO NOT import in streamlit_app.py (win32com crash)
```

**streamlit_app.py import block** — drop `fig_to_b64`, `save_snapshot`, `rpt as module`; add `st`, `pd`, `time`; import color constants directly:
```python
from __future__ import annotations

import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from gex.data_loader import load_chain
from gex.greeks_engine import add_greeks
from gex.exposure_engine import (
    compute_gex, strike_gex, gamma_profile,
    compute_vex, compute_chex, strike_vex, strike_chex,
)
from gex.analytics import summarise, plot_overview, plot_strike_gex, plot_gamma_profile
from gex.validation import load_yesterday, _classify_vs_yesterday
from gex.report import REGIME_COLOR, REGIME_BG
```

**Core computation pattern** (`gex/run_daily.py` lines 43-77) — `process_ticker()` is the direct template for `fetch_ticker()`:
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

**Adaptation for `fetch_ticker()`:** wrap the try/except body in `@st.cache_data(ttl=300, show_spinner=False)`. Remove `save_snapshot()` call (that stays in `run_daily`). Change error return to re-raise (caller uses `st.warning`). Signature: `def fetch_ticker(ticker: str) -> dict` — single string arg keeps cache keying simple.

**Figure lifecycle pattern** (`gex/run_daily.py` lines 106-116):
```python
overview_fig = plot_overview(results)
overview_b64 = fig_to_b64(overview_fig)
plt.close(overview_fig)          # close immediately after use

fig = plot_gamma_profile(d["p_df"], d["spot"], ticker, d["summary"])
fig.set_size_inches(6, 2.8)
charts_b64[ticker] = fig_to_b64(fig)
plt.close(fig)
```

**Adaptation for streamlit:** replace `fig_to_b64(fig)` with `st.pyplot(fig)`, then `plt.close(fig)`. Pattern is identical — create fig, render, close.

**Error handling pattern** (`gex/run_daily.py` lines 75-77, 99-100):
```python
    except Exception as exc:
        print(f"  [WARN] {ticker}: {exc}")
        return {"summary": {"ticker": ticker, "error": str(exc)}}
    # ...
    if not s.get("error"):
        save_snapshot(s, ticker)
```

**Adaptation for streamlit:** replace `print(f"[WARN]...")` with `st.warning(f"{ticker}: {exc}")` inside the fetch loop. Guard chart rendering with `if not s.get("error")`.

**Ticker constant** (`gex/run_daily.py` line 30):
```python
TICKERS = ["SPY", "QQQ", "IWM"]
```
Copy verbatim to `streamlit_app.py`.

**Regime color constants** (`gex/report.py` lines 8-17):
```python
REGIME_COLOR = {
    "positive": "#1a7a4a",
    "negative": "#c0392b",
    "neutral":  "#7f8c8d",
}
REGIME_BG = {
    "positive": "#d5f5e3",
    "negative": "#fadbd8",
    "neutral":  "#ecf0f1",
}
```
Import from `gex.report` — do not copy. Used in `render_regime_card()`.

**HTML inline style pattern** (`gex/report.py` lines 86-91, `_badge()`):
```python
def _badge(regime: str) -> str:
    c  = REGIME_COLOR.get(regime, "#999")
    bg = REGIME_BG.get(regime, "#eee")
    return (
        f'<span style="background:{bg};color:{c};padding:3px 9px;'
        f'border-radius:4px;font-weight:bold;font-size:11px;white-space:nowrap;">'
        f'{regime.upper()}</span>'
    )
```
Extend this pattern for the full regime card div in `streamlit_app.py` — same color lookup, same f-string HTML, `st.markdown(..., unsafe_allow_html=True)`.

**Summary dict keys** (`gex/analytics.py` lines 61-71, `summarise()` return):
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
# run_daily.py adds after summarise():
summary["ticker"] = ticker
summary["vs_yesterday"] = ...
```
`streamlit_app.py` accesses all these keys — match exactly. `ticker` and `vs_yesterday` are added by `fetch_ticker()` post-`summarise()`, same as `process_ticker()`.

**Chart function signatures** (`gex/analytics.py` lines 85-88, 113-116):
```python
def plot_strike_gex(gex_df: pd.DataFrame, spot: float, ticker: str,
                    summary: dict, ax: plt.Axes | None = None) -> plt.Figure:
def plot_gamma_profile(profile_df: pd.DataFrame, spot: float, ticker: str,
                       summary: dict, ax: plt.Axes | None = None) -> plt.Figure:
def plot_overview(results: list[dict]) -> plt.Figure:
```
All three return `plt.Figure`. Call with positional args, pass result to `st.pyplot(fig)`, then `plt.close(fig)`.

---

### `requirements.txt` (config, modify)

**Analog:** `requirements.txt` itself (lines 1-15)

**Current format:**
```
pandas>=2.0,<3.0
numpy>=1.26,<3.0
...
pytest>=8.0
pywin32>=306
python-dotenv>=1.0
```

**Add one line** after `python-dotenv`:
```
streamlit>=1.57,<2.0
```
No other changes. Follow the existing `>=X.Y,<N.0` pin style.

---

### `gex/tests/test_streamlit_app.py` (test, smoke + unit)

**Analog:** `gex/tests/test_exposure_flow.py`

**Test file structure** (`gex/tests/test_exposure_flow.py` lines 1-9):
```python
from __future__ import annotations

import pandas as pd
import pytest

from gex.exposure_engine import compute_vex, compute_chex, strike_vex, strike_chex
from gex.analytics import summarise
from gex.validation import _classify_vs_yesterday, load_yesterday
```

**Helper pattern** (`gex/tests/test_exposure_flow.py` lines 12-34):
```python
def _chain(calls: int = 1, puts: int = 1, spot: float = 500.0) -> pd.DataFrame:
    rows = []
    for _ in range(calls):
        rows.append({"strike": spot, "type": "call", "oi": 100, ...})
    return pd.DataFrame(rows)

def _gex_df(net: float = 1e9) -> pd.DataFrame:
    return pd.DataFrame({"strike": [500.0], "gex": [net]})
```

**Test function pattern** (`gex/tests/test_exposure_flow.py` lines 39-43):
```python
def test_compute_vex_spot_not_squared():
    df = pd.DataFrame({...})
    result = compute_vex(df, spot=500.0)
    assert abs(result["vex"].iloc[0]) != pytest.approx(abs(wrong))
```

**Monkeypatch pattern** (`gex/tests/test_exposure_flow.py` lines 127-130):
```python
def test_load_yesterday_returns_none_when_store_absent(monkeypatch, tmp_path):
    import gex.validation as val
    monkeypatch.setattr(val, "STORE", tmp_path / "nonexistent.parquet")
    assert load_yesterday("SPY") is None
```

**Adaptation for `test_streamlit_app.py`:** The two automatable tests from RESEARCH.md are:

1. **Import smoke test** (DASH-01, DASH-06): `python -c "import streamlit_app"` is the CLI form; in pytest write as:
```python
def test_import_no_emailer_bleed():
    import importlib
    import sys
    # streamlit itself may not be installed during CI — skip if absent
    pytest.importorskip("streamlit")
    mod = importlib.import_module("streamlit_app")
    assert "gex.emailer" not in sys.modules
    assert "gex.run_daily" not in sys.modules
```

2. **Cache clear unit test** (DASH-02): confirm `fetch_ticker.clear` is callable:
```python
def test_fetch_ticker_has_clear():
    pytest.importorskip("streamlit")
    from streamlit_app import fetch_ticker
    assert callable(getattr(fetch_ticker, "clear", None))
```

3. **plot_overview renders** (DASH-04): minimal smoke using synthetic summary dicts:
```python
def test_plot_overview_renders():
    import matplotlib.pyplot as plt
    from gex.analytics import plot_overview
    results = [{"ticker": "SPY", "net_gex": 1e9, "gamma_regime": "positive", "error": None}]
    fig = plot_overview(results)
    assert fig is not None
    plt.close(fig)
```

---

## Shared Patterns

### matplotlib Agg backend
**Source:** `gex/run_daily.py` lines 16-17
**Apply to:** `streamlit_app.py` (first two effective lines after `from __future__`)
```python
import matplotlib
matplotlib.use("Agg")
```
Must appear before any `import matplotlib.pyplot` and before any `gex.*` import that might import pyplot.

### Figure create → render → close cycle
**Source:** `gex/run_daily.py` lines 106-116
**Apply to:** every `st.pyplot()` call in `streamlit_app.py`
```python
fig = plot_overview(results)
# email version:   fig_to_b64(fig)
# streamlit version: st.pyplot(fig)
plt.close(fig)
```

### Error guard on summary dict
**Source:** `gex/run_daily.py` lines 96-100
**Apply to:** all rendering sections in `streamlit_app.py`
```python
if not s.get("error"):
    # render card / charts
```

### `from __future__ import annotations`
**Source:** all `gex/*.py` files, line 1
**Apply to:** `streamlit_app.py` and `gex/tests/test_streamlit_app.py`

---

## No Analog Found

None — all three files have direct analogs in the codebase.

---

## Metadata

**Analog search scope:** `gex/run_daily.py`, `gex/report.py`, `gex/analytics.py`, `gex/tests/test_exposure_flow.py`, `requirements.txt`
**Files read:** 6
**Pattern extraction date:** 2026-05-05

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/03-streamlit-dashboard/03-01-PLAN|03-01-PLAN]]
- [[_planning/gamma-omm/phases/03-streamlit-dashboard/03-01-SUMMARY|03-01-SUMMARY]]
- [[_planning/gamma-omm/phases/03-streamlit-dashboard/03-02-PLAN|03-02-PLAN]]
- [[_planning/gamma-omm/phases/03-streamlit-dashboard/03-02-SUMMARY|03-02-SUMMARY]]
- [[_planning/gamma-omm/phases/03-streamlit-dashboard/03-HUMAN-UAT|03-HUMAN-UAT]]
- [[_planning/gamma-omm/phases/03-streamlit-dashboard/03-RESEARCH|03-RESEARCH]]
- [[_planning/gamma-omm/phases/03-streamlit-dashboard/03-REVIEW|03-REVIEW]]
- [[_planning/gamma-omm/phases/03-streamlit-dashboard/03-VERIFICATION|03-VERIFICATION]]

<!-- LINKS:END -->
