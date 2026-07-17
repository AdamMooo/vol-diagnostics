# Phase 16: VRP Percentile - Research

**Researched:** 2026-06-16
**Domain:** Quant vol metrics — historical VRP percentile from internally-consistent vol-index series
**Confidence:** HIGH (all claims verified against the live codebase and stored data)

## Summary

The phase is well-scoped and **fully achievable today with no data blocker**. The hard part — VRP-03's "one internally-consistent series" — turns out to be cheap because the heavy lifting already exists: the CBOE vol-index parquet store (`gex/vol_index.py` → `out/vol_index/*.parquet`) holds **full history** (VIX back to 1990 / 9206 rows, VXN & RVX back to 2009 / ~4200 rows each), and `compute_rv20()` in `gex/vol_metrics.py` is a pure function that takes any close series. A 252-day VRP percentile is buildable on day one — cold-start labeling will essentially never trigger for the standard lookback.

The single highest-risk design point is a **trap that already exists in the codebase**: `gex/compute.py:142` builds today's VRP from `snapshot.iv30` (CBOE-computed 30-day constant-maturity IV from the delayed options payload). That on-card scalar is fine to keep AS-IS for VRP-01's "today's number," but it **must not** be the basis for the percentile. The percentile series must be built from `vol_index − RV20` at every historical date, where `vol_index` is VIX/VXN/RVX (per ticker) and `RV20` is recomputed from yfinance closes at each date. Mixing the two series — e.g. ranking today's `snapshot.iv30 − RV20` against a history made of `VIX − RV20`, or worse, against the thin 25-row `vrp` column in `gex_snapshots.parquet` — is exactly the VRP-03 violation called out in REQUIREMENTS.md's out-of-scope table.

**Primary recommendation:** Add a new pure function `vrp_percentile_series(ticker)` (or a small module `gex/vrp_history.py`) that (1) maps ticker → vol-index symbol, (2) loads the full vol-index close history via `load_vol_index()`, (3) fetches ~400d of yfinance closes once, (4) computes a rolling RV20 aligned to vol-index dates, (5) forms `vrp_hist = vol_index_close − RV20×100` (both in vol points), (6) ranks today's **vol-index-based** VRP with `scipy.stats.percentileofscore(..., kind="rank")`, labeled with the actual sample count. Surface it as a new card field and an email/dashboard line. Keep the existing `snapshot.iv30`-based VRP scalar untouched as the "today" number, but compute the **percentile** from the vol-index series and label it accordingly.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Vol-index history load | Data layer (`gex/vol_index.py`) | — | Already isolated, Bloomberg-swappable (VIDX-02). Do not touch. |
| RV20 from closes | Pure compute (`gex/vol_metrics.py:compute_rv20`) | — | Already exists; reuse, do not rebuild. |
| Historical VRP series + percentile | Pure compute (new fn in `vol_metrics.py` or new `gex/vrp_history.py`) | — | New logic; must be I/O-light pure where possible, yfinance fetch isolated like `_fetch_spot_history_yf`. |
| Ticker → vol-index map | Config (`gex/config.py`) | — | New constant `TICKER_VOL_INDEX`; one source of truth per D-02 convention. |
| Percentile into card | Card model (`gex/card_model.py:build_card_fields`) | — | Single source for both surfaces (PAR-01 seam). |
| Render | Email (`gex/report.py`) + Dashboard (`streamlit_app.py`) | — | Both consume `build_card_fields()` — no per-renderer duplication. |

## User Constraints (from project — no CONTEXT.md exists; sourced from CLAUDE.md + REQUIREMENTS.md)

> No `/gsd:discuss-phase` was run for this phase — no CONTEXT.md present. These constraints are
> drawn from project CLAUDE.md and REQUIREMENTS.md and carry the same authority as locked decisions.

### Locked Decisions (project constraints)
- **Descriptive only** — no predictive / fair-value / forecasting claims. VRP and percentile are descriptive of the current environment + historical rank only.
- **Interpretability first** — raw labeled percentile only. **No hidden scoring, no weighting, no categorical regime label** (the non-stationary-floor trap that retired the GEX regime badge).
- **Free data only** — CBOE vol-index CSVs (already cached) + yfinance closes. No Bloomberg.
- **SPY/QQQ/IWM only** — vol-index history (VIX/VXN/RVX) exists only for these.
- **Small diffs** — leverage existing `vol_metrics.py` / `vol_index.py`; do NOT rebuild what exists.
- **Windows paths** — pathlib throughout (existing stores already use `pathlib.Path(...).resolve().parents[1]`).
- **Canonical card consistency** — the page-1 snapshot must render numbers identical to the daily email via the shared card (`gex/card_model.py`); the two surfaces cannot drift.

### Deferred Ideas (OUT OF SCOPE — do NOT propose)
- Mixing snapshot IV30 into the percentile series (the VRP-03 crux — see out-of-scope table).
- Put/call ratios, VVIX, cross-asset vol indices.
- Categorical regime / contango labels with thresholds.
- New tickers beyond SPY/QQQ/IWM.
- Single-name VRP/percentile (no free historical single-name IV).
- GARCH / vol forecasting.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VRP-01 | PM sees today's VRP (vol-index implied − RV20) per index. | Today's VRP already computed in `compute.py` (uses `snapshot.iv30`). For the **headline number** the vol-index value (VIX/VXN/RVX latest close − RV20) is the internally-consistent choice; reuse `compute_vrp()` with vol-index close as the IV input. See "Critical Question 4" resolution. |
| VRP-02 | VRP ranked as a percentile vs its own history, lookback labeled. | `scipy.stats.percentileofscore` already imported in `streamlit_app.py:19` and used for skew (`:403`). Same pattern. Label `"{n}th %ile, {len}-session lookback"` (target 252). |
| VRP-03 | Percentile from ONE internally-consistent series; snapshot IV30 NEVER mixed into VRP history; cold-start omits or labels actual count. | Vol-index store has full history (VIX→1990). Build `vol_index − RV20` at every date. Never read the `vrp` column from `gex_snapshots.parquet` (it is IV30-based AND thin). Cold-start guard mirrors `streamlit_app.py:402` (`len(series) >= N`). |

## Standard Stack

### Core (all already present — nothing new to install)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | (installed) | Date alignment of vol-index closes ↔ yfinance closes, rolling RV20 | Already the project's data backbone |
| numpy | (installed) | Log-return std for RV20 (inside existing `compute_rv20`) | Already used by `compute_rv20` |
| scipy | >=1.13,<2.0 `[VERIFIED: requirements.txt]` | `scipy.stats.percentileofscore` | Already imported + used for skew percentile (`streamlit_app.py:19,403`) |
| yfinance | >=0.2.40 `[VERIFIED: requirements.txt]` | Underlying daily closes for the RV20 history | Existing close-history path per VIDX-01 |

**Installation:** None. No new dependencies. (Package Legitimacy Audit therefore N/A — no external package installs in this phase.)

### `scipy.stats.percentileofscore` method note
`[CITED: docs.scipy.org/doc/scipy/reference/generated/scipy.stats.percentileofscore.html]`
- Signature: `percentileofscore(a, score, kind='rank')`.
- `kind` options: `'rank'` (default, averages ties), `'weak'`, `'strict'`, `'mean'`.
- The existing skew code uses the default (`kind='rank'`) and casts to `int`. **Use the same default for consistency** — a PM reading "74th %ile" expects the conventional rank definition. Do not introduce a different `kind` without a reason; uniformity with the skew percentile is the right call here.

## Architecture Patterns

### Data flow (the historical-VRP-series construction path — the load-bearing diagram)

```
                          ┌─────────────────────────────────────────────┐
   ticker (SPY/QQQ/IWM) ──┤ TICKER_VOL_INDEX  (new const in config.py)   │
                          │   SPY→VIX  QQQ→VXN  IWM→RVX                   │
                          └───────────────┬─────────────────────────────┘
                                          │ vol-index symbol
                                          ▼
              load_vol_index(sym)  ── out/vol_index/{SYM}.parquet
              (FULL history: VIX→1990, VXN/RVX→2009)
                  │  columns: date, close   (close = vol points, e.g. 14.2)
                  ▼
        vix_close_series  ──────────────┐
                                         │
   yfinance closes (~400d, one fetch) ──┤  align on date
   (existing _fetch_spot_history_yf      │
    path, but fetch ~400d not 35d)       ▼
                            ┌────────────────────────────────────────┐
                            │ for each date d in vol-index history:   │
                            │   rv20_d = compute_rv20(closes[..d])    │  ← reuse pure fn
                            │   vrp_d  = vix_close[d] − rv20_d*100     │  ← both in vol points
                            └───────────────┬────────────────────────┘
                                            │ vrp_hist  (series, len up to ~252)
                                            ▼
            today_vrp = latest_vix_close − today_rv20*100   ← SAME series definition
                                            │
                                            ▼
            pct = percentileofscore(vrp_hist[-252:], today_vrp, kind='rank')
            label = f"{int(pct)}th %ile · {len(window)}-session lookback"
            (cold-start: if len(window) < target → label actual count or omit)
```

### Pattern 1: Reuse the existing yfinance isolation pattern, just widen the window
**What:** `compute.py:_fetch_spot_history_yf(ticker, days=35)` already isolates the yfinance call and never raises. The historical-RV20 series needs ~273 trading days (252 lookback + 21 for the first RV20 window) + slack.
**When to use:** Building the VRP history series.
**Verified:** `yf.Ticker('SPY').history(period='400d')` returns 400 calendar-day rows (~273 trading days) covering 2024-11 → 2026-06 `[VERIFIED: live yfinance call this session]`. 400d is comfortably enough; use `period='400d'` (or `'2y'` for headroom).
```python
# Mirror the existing helper; do not raise, return None on failure.
# Fetch ONCE per ticker, reuse for the whole rolling RV20 series.
closes = yf.Ticker(ticker.replace(".", "-")).history(period="400d")["Close"].dropna()
```

### Pattern 2: Rolling RV20 over closes, aligned to vol-index dates
**What:** `compute_rv20()` takes oldest-first closes and returns the RV20 of the **last 20 returns**. To build a *series*, slide a window: for each target date `d`, call `compute_rv20(closes.loc[:d])` (oldest-first up to and including d). Vectorize with `closes.rolling(21).apply(...)` or a simple loop over the vol-index dates (≤252 iterations — cheap).
**When to use:** Producing one RV20 per historical date so it can be subtracted from the vol-index close on that date.
**Note on alignment:** vol-index dates and yfinance trading days are both NYSE sessions and should align cleanly, but use an inner join / `reindex` on date to be gap-safe (holidays, missing rows). Drop dates where either side is NaN before forming the VRP series.

### Pattern 3: Card-field addition via `build_card_fields` (single source — PAR-01 seam)
**What:** Add the VRP percentile as a `CardField` in `gex/card_model.py:build_card_fields()`. Both `report.py:_ticker_card()` (`:102`) and the dashboard's `render_regime_card()` consume this list, so adding one field surfaces it in **both** the email and the dashboard with no per-renderer edit — this is exactly the PAR-01 mechanism.
**Caveat:** `report.py:_ticker_card` splits fields `[:5]` left / `[5:]` right (`:104-105`). Adding a field shifts the split; verify the layout still reads well (or place VRP intentionally). The dashboard renderer iterates the full list, so it is unaffected by the split index.
**Where the percentile value comes from:** `build_card_fields` currently takes `today_summary` + `prior_summary`. The percentile needs the historical series, which is an I/O operation (yfinance + parquet). **Do not** put I/O inside `build_card_fields` (it is pure). Compute the percentile upstream in `compute.py:compute_ticker()` (alongside the existing `rv20`/`vrp`), stash it in `summary` (e.g. `summary["vrp_pct"]`, `summary["vrp_pct_n"]`), and let `build_card_fields` read it from `today_summary` like every other field.

### Anti-Patterns to Avoid
- **Mixing IV sources in one percentile** (VRP-03 violation): ranking a `snapshot.iv30`-based VRP against a `VIX`-based history, or vice versa. The "today" value fed to `percentileofscore` MUST be `vol_index_latest − RV20`, identical in definition to every point in the history series.
- **Reusing the `vrp` column from `gex_snapshots.parquet`**: it is (a) only 25 sessions deep `[VERIFIED: parquet has 25 SPY rows, 2026-05-06→2026-06-15]` and (b) built from `snapshot.iv30`. Double-disqualified for the percentile.
- **Putting yfinance/parquet I/O inside `build_card_fields` or `compute_vrp`**: keep the pure functions pure; do I/O in `compute_ticker` or a dedicated `gex/vrp_history.py`.
- **Categorical labeling** ("VRP rich/cheap regime"): the `vrp_headline()` helper already emits soft language ("premium-selling favored") — acceptable as plain read, but do NOT add threshold-based regime badges. Show the raw percentile.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Percentile rank | Custom sort-and-count | `scipy.stats.percentileofscore` (already imported) | Handles ties via `kind`; matches the skew percentile already in the app |
| RV20 | New realized-vol calc | `gex/vol_metrics.py:compute_rv20` | Already exists, tested, ddof=1, √252 annualized, 21-price guard |
| VRP subtraction | New function | `gex/vol_metrics.py:compute_vrp` | Exists; just feed it vol-index close (as decimal) instead of `snapshot.iv30` |
| Vol-index history | New CBOE fetch | `gex/vol_index.py:load_vol_index(sym)` | Full history already cached; Bloomberg-swappable per VIDX-02 |
| Cold-start guard | New gating scheme | Mirror `streamlit_app.py:402` (`len(series) >= N`) pattern | Consistent with existing skew percentile gate and GATE-01 intent |

**Key insight:** This phase is ~90% wiring of existing pure functions. The only genuinely new code is (1) the ticker→index map constant, (2) the rolling-RV20-over-history loop, and (3) one card field. Resist building a vol-stats subsystem.

## Common Pitfalls

### Pitfall 1: Unit mismatch (vol points vs decimal)
**What goes wrong:** `compute_rv20` returns a **decimal** (e.g. `0.158`); vol-index `close` is in **vol points** (e.g. `14.2`); `compute_vrp` docstring requires **both args in decimal** and returns decimal; the card/email displays **vol points (pp)**.
**Why it happens:** Three unit conventions in one calculation path. The existing `compute.py:142-144` already normalizes (`iv30/100`, then `*100` on the result).
**How to avoid:** Pick ONE convention for the series and be explicit. Cleanest: convert vol-index close to decimal (`/100`), call `compute_vrp(vix_close/100, rv20)`, then `*100` for display — mirroring the existing IV30 path exactly. Apply the SAME transform to both today's value and every history point.
**Warning sign:** A VRP percentile that looks sensible but a VRP scalar 100× off, or vice versa.

### Pitfall 2: Date misalignment between vol-index and yfinance
**What goes wrong:** Subtracting `VIX[date]` from an RV20 computed on a slightly different trading-day index produces silently-wrong VRP points.
**Why it happens:** Holiday gaps, yfinance vs CBOE row differences, timezone-stamped yfinance index vs CBOE `date` (date-only).
**How to avoid:** Normalize both to date-only (`.dt.date`), inner-join on date, drop NaN rows before forming the series. `load_vol_index` already returns `date` as `.dt.date`.
**Warning sign:** Series length noticeably shorter than expected, or off-by-one VRP spikes.

### Pitfall 3: Recomputing the RV20 history naively (O(n²) but harmless)
**What goes wrong:** Looping `compute_rv20(closes[:d])` for every date re-slices the full series each time. For ≤252 dates × 21-point windows this is trivially fast — not a real performance issue, just don't over-engineer a vectorized version unless profiling says so.
**How to avoid:** A simple loop or `rolling(21).apply` is fine. Cache the result behind `@st.cache_data` in streamlit (like `_load_history_cached`) so it isn't recomputed every rerun.

### Pitfall 4: The card-field split index in report.py
**What goes wrong:** `_ticker_card` hard-splits `fields[:5]` / `fields[5:]`. Inserting a VRP field shifts the column balance.
**How to avoid:** Decide placement deliberately (likely near IV30, since VRP is IV-vs-RV). Eyeball the rendered email after.

## Runtime State Inventory

> This is an additive-feature phase, not a rename/refactor — included for completeness.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Vol-index parquet (`out/vol_index/*.parquet`) — full history, read-only here. `gex_snapshots.parquet` `vrp` column exists but MUST NOT feed the percentile. | None (read vol-index); explicitly avoid snapshot `vrp` for percentile |
| Live service config | None | None — verified: no external service holds VRP config |
| OS-registered state | None | None |
| Secrets/env vars | None | None — CBOE/yfinance are unauthenticated free endpoints |
| Build artifacts | None | None |

## Critical Question Resolutions

**Q1 — Historical VRP series & close source (the crux):** RESOLVED, no blocker. Vol-index history is full (VIX 9206 rows to 1990; VXN/RVX ~4200 to 2009) `[VERIFIED: read out/vol_index/*.parquet this session]`. Historical RV20 comes from yfinance closes via the existing isolated path (currently `days=35`; widen to ~400d). `yf SPY history(period='400d')` → 400 rows ≈ 273 trading days `[VERIFIED]`. **A 252-day lookback is achievable today.** Cold-start will not trigger for the standard window — but still implement the guard for robustness and per VRP-03/GATE intent.

**Q2 — Ticker → vol-index map:** SPY→VIX, QQQ→VXN, IWM→RVX. All three symbols verified present in `out/vol_index/` `[VERIFIED]`. **No mapping constant exists yet** `[VERIFIED: grep found none]` — add `TICKER_VOL_INDEX = {"SPY":"VIX","QQQ":"VXN","IWM":"RVX"}` to `config.py` (per the D-02 "add symbols in config, not the module" convention already noted at `config.py:187`).

**Q3 — Percentile method:** `scipy.stats.percentileofscore(series, value, kind='rank')` — already imported (`streamlit_app.py:19`) and used identically for skew (`:403`). Use default `kind='rank'`, cast `int`. Label: `f"{pct}th %ile · {len(window)}-session lookback"`. Cold-start clause: if `len(window) < target_lookback`, either omit the percentile or label with the actual count (`f"{pct}th %ile · {n} sessions (building to 252)"`) — never silently rank on a thin sample. Mirror the existing `len(series) >= 5` guard pattern (`:402`).

**Q4 — Where VRP lives vs. must appear (highest-risk):** RESOLVED.
- `compute.py:142` builds VRP from `snapshot.iv30` and stores `summary["vrp"]`. This is the **today scalar** for the card.
- **Decision for the percentile:** the percentile MUST be computed from a vol-index-based series. The cleanest VRP-03-clean design is to make the **headline VRP itself** vol-index-based too (latest VIX close − RV20), so the displayed number and the percentile share one definition. That is the most internally-consistent reading of VRP-01+VRP-03 ("the vol index for both today's reading and the history").
- **Open design choice for the planner / discuss-phase:** keep the existing `snapshot.iv30`-based VRP scalar on the card AND add a separate vol-index-based VRP+percentile, OR replace the scalar's IV input with the vol-index value so there is one VRP. `[ASSUMED]` The latter (one vol-index-based VRP) is simpler and avoids two confusingly-similar "VRP" numbers — but it changes the existing card number, which touches PAR-01 parity. **Recommend confirming with the user** before changing the existing scalar. Either way, the **percentile** is vol-index-based, non-negotiable per VRP-03.

**Q5 — Canonical card + email parity:** Add the percentile as a `CardField` in `build_card_fields()` (`card_model.py:154`). Both renderers consume it (`report.py:102`; dashboard `render_regime_card`). Value must be precomputed upstream in `compute_ticker` and stashed in `summary` (don't do I/O in the pure card builder). Mind the `fields[:5]/[5:]` split in `_ticker_card`. Full 3-page parity is Phase 18 — this phase only needs the field present in both surfaces.

**Q6 — Cold-start / gating:** Stored snapshot history is thin (25 sessions) but **irrelevant** — the percentile draws on vol-index full history + yfinance, not the snapshot store. So the percentile is NOT cold-start-limited. The guard still belongs in code (VRP-03 cold-start clause) and should mirror `streamlit_app.py:402`. Full GATE-01/02 display gating is Phase 18; this phase implements the per-metric guard inline.

## Code Examples

### Ticker→index map (config.py)
```python
# Per the D-02 convention: vol-index symbols live in config, not the modules.
TICKER_VOL_INDEX: dict[str, str] = {"SPY": "VIX", "QQQ": "VXN", "IWM": "RVX"}
"""Index ETF → CBOE vol-index used as the implied-vol leg of VRP.
SPY→VIX, QQQ→VXN, IWM→RVX. Only these three have free vol-index history."""
```

### Historical VRP series + percentile (new pure-ish fn; isolate the yf fetch)
```python
# gex/vrp_history.py  (or a function in vol_metrics.py with the fetch passed in)
# Source pattern: mirrors compute._fetch_spot_history_yf + vol_metrics.compute_rv20
import pandas as pd
from scipy.stats import percentileofscore
from gex.vol_index import load_vol_index
from gex.vol_metrics import compute_rv20
from gex import config

def vrp_percentile(ticker: str, lookback: int = 252) -> dict:
    sym = config.TICKER_VOL_INDEX[ticker]
    vi = load_vol_index(sym)                      # full history, date+close
    if vi.empty:
        return {"vrp": None, "pct": None, "n": 0}

    closes = _fetch_closes_yf(ticker, period="400d")  # oldest-first Series, date-indexed
    if closes is None:
        return {"vrp": None, "pct": None, "n": 0}

    vi = vi.set_index("date")["close"]            # vol points
    # rolling RV20 aligned to each date that has >=21 prior closes
    rv = {}
    cl = closes.sort_index()
    for i in range(20, len(cl)):
        window = cl.iloc[i-20:i+1]                # 21 prices -> 20 returns
        rv[cl.index[i]] = compute_rv20(window.reset_index(drop=True))
    rv = pd.Series(rv)

    df = pd.DataFrame({"vi": vi, "rv": rv}).dropna()
    vrp_hist = df["vi"] - df["rv"] * 100          # both in vol points
    if vrp_hist.empty:
        return {"vrp": None, "pct": None, "n": 0}

    today_vrp = float(vrp_hist.iloc[-1])          # SAME definition as the series
    window = vrp_hist.iloc[-lookback:]
    pct = int(percentileofscore(window.to_numpy(), today_vrp, kind="rank"))
    return {"vrp": today_vrp, "pct": pct, "n": len(window)}
```

### Cold-start-safe label (mirror existing skew gate)
```python
res = vrp_percentile(ticker)
if res["pct"] is None:
    label = "VRP %ile: insufficient history"
elif res["n"] < 252:
    label = f"{res['pct']}th %ile · {res['n']} sessions (building to 252)"
else:
    label = f"{res['pct']}th %ile · 252-session lookback"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| VRP from `snapshot.iv30 − RV20`, stored in thin snapshot parquet | VRP **percentile** from `vol_index − RV20` over full CBOE history | This phase (16) | Removes the IV30/VIX inconsistency; makes a 252d percentile possible day one |

**Deprecated/outdated for the percentile:**
- `gex_snapshots.parquet:vrp` column — keep writing it (forward-compatible schema), but do not read it for the percentile.

## Files to Touch (minimal set)

| File | Change | Risk |
|------|--------|------|
| `gex/config.py` | Add `TICKER_VOL_INDEX` constant | trivial |
| `gex/vrp_history.py` (new) **or** `gex/vol_metrics.py` | `vrp_percentile(ticker)` + isolated `_fetch_closes_yf` | low — reuses pure fns |
| `gex/compute.py` | Call `vrp_percentile()` in `compute_ticker`, stash `summary["vrp_pct"]`/`["vrp_pct_n"]`; decide whether headline VRP becomes vol-index-based (Q4 — confirm w/ user) | medium — touches existing VRP path |
| `gex/card_model.py` | Add VRP %ile `CardField` in `build_card_fields` (read precomputed values from `today_summary`) | low — single source |
| `gex/report.py` | None required if field added to card; verify `fields[:5]/[5:]` split still reads | low |
| `streamlit_app.py` | None required if via card; optionally surface explicitly on page-1 (Phase 18 territory) | low |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Whether to replace the existing `snapshot.iv30`-based headline VRP with a vol-index-based VRP, or keep both, is a user/design decision. Recommend one vol-index VRP. | Q4 | If the existing card number changes unexpectedly, PAR-01 parity expectations and prior daily emails shift. Confirm before changing the displayed scalar. |
| A2 | `kind='rank'` is the intended percentile convention (chosen for uniformity with the existing skew percentile). | scipy note / Q3 | Different `kind` would shift reported percentiles by a few points; low impact, but lock it deliberately. |

## Open Questions

1. **Headline VRP definition (A1).** Should today's displayed VRP scalar switch from `snapshot.iv30 − RV20` to `vol_index − RV20` so it matches the percentile's series exactly? Recommend yes (one consistent number), but it changes an existing card value — surface to the user in discuss/plan.
   - What we know: percentile MUST be vol-index-based (VRP-03).
   - What's unclear: whether to keep the IV30-based scalar alongside.
   - Recommendation: single vol-index-based VRP; confirm with user.

2. **Lookback constant home.** Add a `VRP_PERCENTILE_LOOKBACK = 252` to `config.py` (consistent with the "magic numbers in config" convention) vs. a function default. Recommend config constant with a one-line rationale, matching the file's existing style.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| CBOE vol-index parquet | VRP percentile history | ✓ | VIX→1990, VXN/RVX→2009 | — (already cached; refresh via `refresh_vol_indices`) |
| yfinance | RV20 close history | ✓ | >=0.2.40 | falls back to snapshot `spot` history (thin) per existing `compute.py` logic, but that caps the lookback |
| scipy | percentile | ✓ | >=1.13,<2.0 | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** yfinance failure → percentile returns None (cold-start label), email/dashboard degrade gracefully — never error (matches GATE-02 intent).

## Sources

### Primary (HIGH confidence)
- Live codebase reads: `gex/vol_metrics.py`, `gex/vol_index.py`, `gex/compute.py`, `gex/config.py`, `gex/card_model.py`, `gex/validation.py`, `gex/report.py`, `streamlit_app.py`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`
- Live data inspection: `out/vol_index/{VIX,VXN,RVX}.parquet` (row counts + date ranges), `out/gex_snapshots.parquet` (columns, depth, vrp null count)
- Live yfinance call: `SPY history(period='400d')` → 400 rows
- `requirements.txt` — scipy/yfinance pins

### Secondary (MEDIUM confidence)
- scipy docs — `percentileofscore` `kind` semantics `[CITED: docs.scipy.org]`

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — everything already installed and in use
- Architecture / data path: HIGH — verified against live stores and functions
- Pitfalls: HIGH — unit/alignment issues confirmed by reading existing `compute.py:142-144`
- Q4 design choice: MEDIUM — a genuine product decision (A1), not a technical unknown

**Research date:** 2026-06-16
**Valid until:** ~2026-07-16 (stable; vol-index store is full history, yfinance path is mature)

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
