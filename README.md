# Vol Diagnostics — Vol & Dealer Microstructure Monitor for SPY/QQQ/IWM

Implied-vol and dealer-gamma diagnostics for **SPY, QQQ, IWM** — built for an index income-sleeve PM (covered calls / cash-secured puts). It pulls live CBOE delayed-quote chains plus the free CBOE vol-index history, and surfaces how expensive protection is, where on the surface that expensiveness sits, how the surface is moving, and how dealer positioning is likely to behave.

**Descriptive only — no trade signals, no predictive claims.**

Current metrics: VRP percentile (vol-index − RV20 ranked over a 252-session window), IV30, 25Δ skew, an interactive 3D implied-vol surface (OTM convention, log-moneyness), surface evolution (ΔIV at 5/10/20-day horizons), net GEX (≤90 DTE), γ-flip, and OI walls — each shown as a raw, labeled number with percentile context where enough history exists.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Data is entirely free — CBOE delayed-quote JSON (chains), CBOE vol-index CSVs, yfinance closes, and the FRED `^IRX` risk-free rate. No API key, no vendor feed.

## Running

**Interactive dashboard:**
```powershell
streamlit run app.py
```
Opens at `http://localhost:8501`.

**Daily email report (Outlook COM — Windows only):**
```powershell
python -m engine.run_daily --send
python -m engine.run_daily --dry-run   # writes out/index-vol-report-YYYY-MM-DD.html, no email
```

**Single-ticker CLI:**
```powershell
python -m engine.run_gex              # SPY
python -m engine.run_gex --ticker QQQ
python -m engine.run_gex --ticker IWM
```

## Dashboard

| Section | What it shows |
|---------|--------------|
| **Top bar + freshness banner** | Selected tickers · date · whether the stored snapshots are current through the latest NYSE session (green) or missing sessions (amber) |
| **Cards + read** | Spot, net GEX, γ-flip, 25Δ skew, IV30, VRP percentile. Accent bar = sign of net GEX (no categorical regime label). A plain-English read sits on top, **credibility-gated** — chips only appear when backed by enough history |
| **Vol surface** | Interactive 3D implied-vol surface (OTM convention, log-moneyness) with mouse-driven smile/term slices — **Today**, a two-date ΔIV **Compare**, and a day-by-day surface **Evolution** ("video", Level ↔ Change) |
| **Positioning** | OI-led — GEX is demoted (capped ≤90 DTE, labeled a model construct); call/put walls labeled **(model)** vs **(raw OI)** so the two are never confused |
| **Methodology & Assumptions** | Full caveat block: free CBOE feed (no OPRA), CBOE American option model, live `^IRX` rate, all filters explicit, model-construct tags on γ-flip + walls, dealer-positioning assumption |

Chains are fetched from the CBOE CDN on first load (no auth) and cached 6 hours per ticker (`config.CACHE_TTL_TICKER`). A parquet snapshot written daily by `run_daily` feeds the history and evolution views.

## Severity monitor & alerts

`engine/monitor/` ranks each metric×ticker pair by ECDF percentile — a dual level rank (deep history + trailing 1yr) plus a two-sided k=5 change rank — and drives a hysteresis state machine (entry / escalate / exit at percentile bands 90 / 94 / 85, gap 5) so alerts latch cleanly instead of flickering. Bands are calibrated to a false-alarm budget of ~1 episode/week; re-run the calibration over stored history any time:

```powershell
python -m engine.monitor.calibration
```

Two deliberate design points: metrics only rank once they clear a 252-session credibility floor (today only ~5 of 17 pairs qualify — VRP across the three underlyings plus two SPY term ratios; the chain-derived metrics cold-started ~2026-05 and mature toward ~2027), and **silence is information** — no alert firing is itself a read on the environment. The severity output is computed daily inside `run_daily`; the dedicated monitor UI is Phase 27 (in progress).

## Defensibility

**Peer-reviewed predictive backing:**
- **Skew (25Δ put − 50Δ call)** — Xing, Zhang & Zhao (2010, *JFQA*) — 10.9% annual alpha on skew-sorted portfolios.

**Mechanistic / derivable:**
- **Net GEX** — Gatheral / Bergomi dollar-gamma framework; dealer-net-short positioning empirically confirmed by Garleanu, Pedersen & Poteshman (2009, *RFS*).
- **IV surface** — OTM convention (Gatheral §2.1); log-moneyness axes per Cont & da Fonseca (2002).
- **VRP** — Carr & Wu (2009); implied minus realized variance as a descriptive premium measure.

**Model constructs (descriptive, not predictive):**
- **γ-flip** (the gamma-sign-flip level) — no peer-reviewed paper tests it as a price level. Read it as the model's threshold, not a target.
- **Call/Put wall strikes** — trader lore. Describes where OI gamma is concentrated, not support/resistance.

**Explicitly removed for rigor:** vanna/charm exposures, hand-tuned regime labels, vs-yesterday classifier, wall clusters, OI×vega weighting — each carried more assumption than benefit.

Full research: [`research/methodology-deep-review.md`](research/methodology-deep-review.md) (academic literature with SSRN/DOI citations) and [`research/methodology-audit.md`](research/methodology-audit.md) (practitioner-source audit).

## Layout

The diagnostics engine lives in `engine/`, grouped by domain (orchestration + shared config at the root):

| Path | Purpose |
|------|---------|
| `app.py` | Streamlit dashboard — cards + read, interactive surface, positioning |
| `engine/config.py`, `engine/compute.py` | Shared constants + the `compute_ticker()` pipeline (single source for daily + dashboard) |
| `engine/run_daily.py`, `engine/run_gex.py` | Daily email orchestrator and single-ticker CLI |
| `engine/data/` | `data_loader` (CBOE chains), `vol_index` (CBOE vol-index CSVs), `validation` (parquet snapshots), `surface_history` |
| `engine/gex/` | `greeks_engine`, `exposure_engine`, `analytics` — the dealer-gamma subdomain |
| `engine/surface/` | `surface_interactive`, `surface_evolution`, `surface_sweep` |
| `engine/vol/` | `vol_metrics`, `vrp_history` (deep VRP percentile) |
| `engine/report/` | `card_model` (canonical card shared by email + dashboard), `report`, `png_export`, `emailer`, `observation` |

The data source is isolated to `engine/data/data_loader.py` — a Bloomberg swap is a one-class change.

## Scheduling

The daily report runs on **GitHub Actions** (`.github/workflows/daily-report.yml`), firing weekdays after the NYSE close (trading days gated internally by `is_trading_day()`). The former local Windows Task Scheduler job (`runners/gex_daily.ps1`) was retired 2026-07-14 and removed; to run the report locally, invoke `python -m engine.run_daily --send` directly.

## Tests

```powershell
python -m pytest engine/tests/ -q
```

449 tests covering data loading, GEX aggregation, gamma profile, analytics, the vol surface and its evolution, VRP history, the severity monitor (ranker, hysteresis, calibration), email rendering, the canonical card, the snapshot store, and dashboard boot.
