# Stack Additions — v3.2 Actionable Positioning Context

**Project:** options-quant / GEX module
**Researched:** 2026-05-22
**Scope:** What's needed for v3.2 NEW features only. Existing stack is validated — not re-researched.
**Confidence:** HIGH — all recommendations use libraries already in requirements.txt

---

## TL;DR: No New Dependencies

Every v3.2 feature is implementable with the current stack. **Do not add libraries.**

| Feature | Implementation | Libraries Used |
|---------|---------------|----------------|
| RV20 (realized vol) | 20-day close-to-close log-return std × √252 | yfinance (price history), numpy |
| GEX percentile rank | `scipy.stats.percentileofscore` on parquet history | scipy, pandas, pyarrow |
| VRP (IV30 − RV20) | Arithmetic difference, already have IV30 from CBOE | numpy |
| OI tilt | `Σ(OI × strike × 100)` grouped by call/put | pandas |
| Skew percentile | Same as GEX percentile, different column | scipy, pandas |
| Positioning narrative | Template strings keyed on GEX sign + magnitude | (none) |

---

## Feature-by-Feature Stack Analysis

### 1. RV20 — Realized Volatility (20-day)

**Source for daily closes:** `yfinance` — already in `requirements.txt` at `>=0.2.40`.

**Why yfinance (not a new source):**
- Already a dependency (used for ^IRX risk-free rate in `gex/compute.py:_get_risk_free_rate()`)
- `yf.download("SPY", period="2mo")` returns adjusted closes — exactly what RV20 needs
- No API key, no auth, free tier sufficient for 3 tickers × 1 call/day
- Alternative considered: storing closes in the parquet snapshot → rejected because
  (a) parquet only has 9 days of history currently, (b) would need bootstrapping,
  (c) yfinance already solves this with zero new code

**Computation (close-to-close, annualized):**
`python
import numpy as np
import yfinance as yf

def compute_rv20(ticker: str) -> float | None:
    """20-day realized volatility, annualized. Close-to-close log returns."""
    try:
        df = yf.download(ticker, period="2mo", progress=False)
        if df is None or len(df) < 21:
            return None
        closes = df["Close"].iloc[-21:]  # 21 prices → 20 returns
        log_returns = np.log(closes / closes.shift(1)).dropna()
        return float(log_returns.std() * np.sqrt(252) * 100)  # annualized, in %
    except Exception:
        return None
`

**Why close-to-close (not Yang-Zhang or Parkinson):**
- SPY/QQQ/IWM are liquid ETFs — overnight gaps are small relative to intraday range
- Close-to-close is the standard VRP convention in practitioner literature (Carr & Wu 2009)
- Yang-Zhang needs OHLC and adds complexity for marginal accuracy gain on liquid ETFs
- VRP is a *context indicator* ("options rich/cheap"), not a trading signal — ±1pp precision is fine
- **Decision:** Use simple estimator. If PM feedback shows gap-regime distortion, upgrade later.

**Integration point:** Add to `compute.py:compute_ticker()` — call `compute_rv20(ticker)`
alongside `_get_risk_free_rate()`, store result in `summary["rv20"]`. VRP = IV30 − RV20.

**Caching:** yfinance fetches are slow (~1-2s each). For 3 tickers, call once and cache
in the pipeline. Don't call per-refresh in Streamlit — use `@st.cache_data(ttl=3600)`.

---

### 2. GEX Percentile Rank (and Skew Percentile)

**Library:** `scipy.stats.percentileofscore` — already in stack (`scipy>=1.13`).

**Why `percentileofscore` (not pandas `rank`):**
- `percentileofscore(history_array, today_value, kind='rank')` returns 0–100 percentile
  of a single new observation against a historical distribution
- `pandas.rank(pct=True)` ranks within the DataFrame — requires appending today's value
  first and then extracting, which is awkward
- scipy's function is purpose-built for this exact use case

**Implementation pattern:**
`python
from scipy.stats import percentileofscore
from gex.validation import load_history

def gex_percentile(ticker: str, today_gex: float, lookback: int = 60) -> float | None:
    """Percentile rank of today's net GEX vs trailing history. Returns 0-100 or None."""
    hist = load_history(ticker, days=lookback)
    if len(hist) < 10:  # minimum sample for meaningful percentile
        return None
    return float(percentileofscore(hist["net_gex"].dropna().values, today_gex, kind='rank'))
`

**Critical constraint: insufficient history.**
- Current parquet store: **9 days** for SPY/QQQ/IWM (2026-05-06 to 2026-05-20)
- Percentile on 9 data points is noisy — e.g., rank 1 of 9 = 11th percentile
- **Minimum viable:** 10 days (returns percentile but with caveat display)
- **Meaningful:** 30+ days
- **Robust:** 60+ days

**UI handling for thin history:**
- < 10 days: show "—" (insufficient data), no percentile displayed
- 10–29 days: show percentile with "~" prefix and "(N days)" qualifier
- 30+ days: show clean percentile

**Parquet store columns needed:** `net_gex` (exists), `front_skew` (exists), `iv30` (exists).
No schema changes required — existing `load_history()` already returns these columns.

**New column to store:** Consider adding `rv20` and `vrp` to the snapshot store for
future percentile ranking of VRP itself. Forward-compatible — older rows get NaN.

---

### 3. OI Tilt

**Library:** pandas only — pure aggregation on existing chain DataFrame.

**Implementation:**
`python
def compute_oi_tilt(chain_df: pd.DataFrame) -> dict:
    """Dollar-weighted OI tilt. Returns call_oi_dollars, put_oi_dollars, tilt_ratio."""
    call_mask = chain_df["type"] == "call"
    put_mask = chain_df["type"] == "put"
    call_oi_$ = (chain_df.loc[call_mask, "oi"] * chain_df.loc[call_mask, "strike"] * 100).sum()
    put_oi_$ = (chain_df.loc[put_mask, "oi"] * chain_df.loc[put_mask, "strike"] * 100).sum()
    total = call_oi_$ + put_oi_$
    tilt = (put_oi_$ - call_oi_$) / total if total > 0 else 0.0
    return {"call_oi_dollars": float(call_oi_$),
            "put_oi_dollars": float(put_oi_$),
            "oi_tilt": float(tilt)}  # negative = call-heavy, positive = put-heavy
`

**Integration point:** Call inside `compute_ticker()` after `compute_gex()`.
The `chain_df` (`df` in compute.py) already has `type`, `oi`, `strike` columns
from `data_loader.load_chain()`.

**No new data needed** — OI and strike are in the CBOE chain snapshot.

---

### 4. Positioning Narrative

**Library:** None — pure string templates.

**Implementation pattern:**
`python
def positioning_narrative(net_gex: float, vrp: float | None, oi_tilt: float | None) -> str:
    """Mechanical explanation of current positioning for PM consumption."""
    if net_gex > 0:
        base = ("Dealers are NET LONG gamma — they sell into rallies and buy dips, "
                "suppressing realized volatility and favoring mean-reversion toward "
                "the gamma-flip level.")
    else:
        base = ("Dealers are NET SHORT gamma — they chase moves in both directions, "
                "amplifying realized volatility and favoring momentum/breakout regimes.")

    parts = [base]
    if vrp is not None:
        if vrp > 3:
            parts.append(f"Options are RICH (VRP {vrp:+.1f}pp) — hedging is expensive relative to realized moves.")
        elif vrp < -3:
            parts.append(f"Options are CHEAP (VRP {vrp:+.1f}pp) — hedging is cheap relative to realized moves.")
        else:
            parts.append(f"Options are FAIR (VRP {vrp:+.1f}pp) — implied and realized vol are aligned.")
    # ... extend with OI tilt context
    return " ".join(parts)
`

**No libraries, no ML, no LLMs.** Mechanical templates keyed on sign/magnitude thresholds.
This is intentional — the narrative should be deterministic and auditable.

---

## What NOT to Add

| Rejected Library | Why Not |
|------------------|---------|
| `arch` (GARCH) | Overkill for RV20. Close-to-close std is the standard VRP convention. GARCH adds model risk for a context metric. |
| `fredapi` / `pandas-datareader` (for rates/prices) | Already have yfinance for prices and ^IRX. pandas-datareader IS in requirements.txt but unused — consider removing it in cleanup. |
| `openai` / any LLM API | Positioning narrative must be deterministic and auditable. Template strings, not generated text. |
| `ta-lib` / `ta` (technical indicators) | RV20 is 5 lines of numpy. No TA library needed. |
| `plotly-resampler` | Not relevant to v3.2 features. |
| `statsmodels` | Already in requirements.txt but not needed for v3.2. RV is simpler than any statsmodels estimator. |

---

## Parquet Schema Evolution

Current snapshot columns (from `validation.py`):
`
date, ticker, spot, net_gex, zero_gamma_level, call_wall, put_wall,
front_skew, put_25d_iv, call_50d_iv, iv30, strike_slope, term_slope
`

**Add for v3.2 (forward-compatible — older rows get NaN):**
`
rv20         float64   — 20-day realized vol at snapshot time
vrp          float64   — IV30 − RV20 at snapshot time
oi_tilt      float64   — put/call dollar-weighted OI tilt
`

**Remove from future snapshots (per CUT-01):**
`
strike_slope  — being cut from display; stop storing
term_slope    — being cut from display; stop storing
`

Don't delete existing columns from the schema — old rows keep their values.
Just stop populating them in `save_snapshot()`.

---

## Integration Map

`
compute_ticker()                          # gex/compute.py
├── load_chain()                          # existing — returns ChainSnapshot with chain_df
├── add_greeks() → compute_gex()          # existing
├── _get_risk_free_rate()                 # existing (yfinance ^IRX)
├── compute_rv20(ticker)                  # NEW — yfinance daily closes → numpy
├── compute_oi_tilt(chain_df)             # NEW — pandas aggregation
├── summarise()                           # existing
├── summary["rv20"] = rv20                # NEW field
├── summary["vrp"] = iv30 - rv20          # NEW field
├── summary["oi_tilt"] = tilt             # NEW field
└── return dict

# In streamlit_app.py / report.py:
gex_percentile(ticker, net_gex)           # NEW — scipy.stats.percentileofscore
skew_percentile(ticker, front_skew)       # NEW — same pattern
positioning_narrative(net_gex, vrp, tilt)  # NEW — template strings
`

---

## Version Pinning

No new packages. Existing pins are sufficient:

| Package | Current Pin | v3.2 Status |
|---------|------------|-------------|
| yfinance | `>=0.2.40` | Used more (daily closes + ^IRX). Pin unchanged. |
| scipy | `>=1.13,<2.0` | `percentileofscore` stable since scipy 0.x. Pin unchanged. |
| numpy | `>=1.26,<3.0` | Log returns, std. Pin unchanged. |
| pandas | `>=2.0,<3.0` | Aggregation. Pin unchanged. |
| pyarrow | `>=15.0` | Parquet read/write. Pin unchanged. |

---

## Risk: yfinance Reliability

yfinance scrapes Yahoo Finance — it breaks occasionally when Yahoo changes HTML/API.
Current usage (^IRX only) already has a fallback (`config.RISK_FREE_FALLBACK`).

**For RV20:** Add the same fallback pattern. If yfinance fails, `rv20 = None`,
`vrp = None`, and the card shows "—" for VRP. The dashboard doesn't break.

**Long-term:** If yfinance becomes unreliable, daily closes for 3 ETFs could be
stored in a local CSV/parquet updated by `run_daily.py`. But don't build this
preemptively — yfinance works today.

---

## Sources

- yfinance API: Context7 /ranaroussi/yfinance — verified download() and history() methods (HIGH confidence)
- scipy.stats.percentileofscore: verified locally via Python import (HIGH confidence)
- VRP convention (IV30 − RV20, close-to-close): Carr & Wu (2009), standard practitioner approach (HIGH confidence)
- Parquet snapshot schema: inspected gex/validation.py and live store (44 rows, 9 days for core tickers) (HIGH confidence)
