# CLAUDE — Gamma OMM — GEX / Vol Diagnostics Dashboard
Last updated: 2026-06-20 | Status: active milestone v3.5 (Index Vol-Context Rebuild)

## Repo Card

- **Runtime:** local Python (venv). Bloomberg/Cron2 is a future swap, not the build environment.
- **Entry points:**
  - `streamlit run app.py` — interactive dashboard (SPY/QQQ/IWM): per-ticker cards + plain-English read, 3D vol surface, surface "video", positioning
  - `python -m gex.run_daily --send` — daily HTML email (scheduled weekdays via Task Scheduler)
  - `python -m gex.run_gex --ticker SPY` — single-ticker CLI (prints summary, saves PNGs)
- **Output:** daily email + `out/` parquet stores (`gex_snapshots`, `surface_history/`, `vol_index/`, `surface_evolution`)
- **Data:** free — CBOE delayed-quote JSON (chains) + CBOE vol-index CSVs + yfinance closes + FRED. No API key. Bloomberg swap = one class in `gex/data_loader.py`.
- **Tests:** `pytest gex/tests` — 246 green.
- **Workflow:** GSD (`.planning/`)

## What It Does

Dealer-gamma + implied-vol diagnostics for an **index income-sleeve PM** (covered calls / cash-secured puts on SPY/QQQ/IWM). Per ticker:
- a plain-English **read** (premium rich/cheap from the VRP percentile, dealer stabilizing/amplifying) sitting on top of the field card, **credibility-gated** — only chips backed by enough history are shown;
- an **interactive 3D vol surface** with mouse-driven smile/term slices, a day-by-day surface **"video"** (Evolution tab, Level ↔ Change), and a two-date ΔIV **compare**;
- OI-led **positioning** — GEX demoted, capped ≤90 DTE, labeled a model construct.

Descriptive only — no predictive/prescriptive claims.

**Cold-start note:** chain-derived metrics (skew, surface, GEX) only accrue from our own daily snapshots (since ~2026-05-06); the VRP percentile is deep (CBOE vol-index 1990/2009 − yfinance RV20 over a 252-session window). The daily scheduler firing is what compounds the value.

**Removed (commit `663f72f`, archive cleanup):** the v2.x sleeve-allocation framework (`run.py`, `build_report.py`, `signals.py`, `backtest.py`, `data_layer.py`, …) and the v1.0 `hmm.ipynb` — hmm was moved to the **marco-quant** repo. All recoverable from git history.

## Local Setup

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py                 # interactive dashboard
python -m gex.run_gex --ticker SPY   # single-ticker smoke test to stdout
pytest gex/tests                     # 246 tests
```

`requirements.txt` tracks the stack. Add packages there when needed.

## Constraints

- **No predictive claims:** descriptive of current environment + historical analog only.
- **Interpretability first:** conditional base rates primary, no hidden scoring or weighting.
- **Strategy menu:** covered call, cash-covered put, collar, short straddle. Dispersion out of scope.
- **No new signals:** six signals + fragility composite locked until team validates current set.
- **Windows paths:** use pathlib or `os.path.join` throughout.
- **No PDIV / HMM this phase:** locked per scope cap.

## GEX Module (active — v3.0)

**Tickers: SPY, QQQ, IWM only.** Full chain pulled per ticker — no moneyness filter, no OI cutoff.

| Ticker | Index | Role |
|--------|-------|------|
| SPY | S&P 500 | Primary benchmark; highest OI → cleanest gamma signal |
| QQQ | Nasdaq-100 | Tech/high-beta; often leads regime flips before SPY |
| IWM | Russell 2000 | Small-cap risk proxy; divergence from SPY = domestic stress signal |

```
python -m gex.run_gex                # SPY, saves charts to out/
python -m gex.run_gex --ticker QQQ   # QQQ or IWM
python -m gex.run_daily              # all 3 tickers → HTML email
```

| Module | Purpose |
|--------|---------|
| `gex/data_loader.py` | CBOE delayed quotes JSON → `ChainSnapshot` (gamma from CBOE) |
| `gex/greeks_engine.py` | `add_greeks()` adds `T_years`; `bs_gamma()` used only by `gamma_profile()` to sweep spot |
| `gex/exposure_engine.py` | GEX = gamma × OI × 100 × S² × 0.01; `strike_gex`, `gamma_profile` |
| `gex/analytics.py` | `summarise()` → net GEX, zero-γ level, call/put walls, δ-flow; plotly charts |
| `gex/compute.py` | Shared pipeline `compute_ticker(ticker)` — single source of truth for daily + streamlit |
| `gex/run_gex.py` | Single-ticker CLI — fetch → compute → print summary → save PNGs |
| `gex/run_daily.py` | Daily orchestrator — SPY/QQQ/IWM, parquet snapshot, HTML email with ΔIV surface PNGs |
| `gex/validation.py` | Parquet snapshot store: `save_snapshot()` + `load_history()` (drives 30-day ZGL chart) |
| `gex/surface_history.py` | Surface snapshot store: per-ticker chain parquet, `list_available_dates`, `nth_trading_day_back` |
| `gex/surface_evolution.py` | ΔIV scalar engine — level, rms, skew_change, term_change vs rolling-mean baseline |
| `gex/report.py` | HTML email builder — cards, ΔIV surface PNG attachments, glossary |
| `gex/card_model.py` | Canonical card: `build_card_fields` (fields) + `build_card_read` (read chips + soft-lean, credibility-gated). Single source for dashboard + email |
| `gex/surface_interactive.py` | Interactive surface engine: `build_surface_payload`/`build_diff_payload`/`build_movie_payload` + `render_*_html` (client-side plotly.js embedded via `components.html`) |
| `gex/vol_index.py` | CBOE vol-index CSV store (VIX/VXN/RVX + VIX9D/VIX3M) — deep daily history |
| `gex/vol_metrics.py` | `compute_rv20`, `compute_vrp`, skew/term helpers |
| `gex/vrp_history.py` | Deep VRP percentile: `vol_index − RV20×100` over a 252-session window (does NOT touch the chain) |
| `app.py` | Browser dashboard (SPY/QQQ/IWM only) — cards+read, interactive surface (Today/Compare), surface video (Evolution), positioning |

Sign convention: calls positive, puts negative. Positive net GEX = dealers net long gamma (stabilising). Zero-gamma level found via linear interpolation of profile sign change. No categorical regime label is produced — the $200M neutral cutoff was hand-tuned and non-stationary; only the sign of net GEX drives the accent color. **GEX/positioning is capped at ≤90 DTE (`config.GEX_MAX_DTE`)** — the dealer-relevant tenor; the long-dated tail is investor-written call flow (mis-signed by the dealer-short convention) and is excluded. The dashboard surface uses its own `SURFACE_INTERACTIVE_*` smoothing/clip, isolated from the email/evolution path.

**Removed for rigor** (do not reintroduce without methodology audit): VEX/CHEX (vanna/charm exposures), wall cluster + concentration, ZGL flow magnitude, vs-yesterday classifier, event study, early-exercise risk flags, categorical "positive/negative/neutral" regime label, vanna/charm BS computations.

Bloomberg upgrade path: swap `gex/data_loader.py` only — everything else is data-source-agnostic.

## v2.x sleeve framework / v1.0 hmm — REMOVED

The sleeve-allocation framework (`run.py`, `build_report.py`, `local_data.py`, `data_layer.py`, `signals.py`, `backtest.py`, `dashboard.py`, `stats_rigor.py`, `sensitivity.py`, `WALKTHROUGH.md`) and `hmm.ipynb` were removed in commit `663f72f` (archive cleanup). `hmm.ipynb` lives in the **marco-quant** repo now. Recover any of these from git history if needed — they are not part of this repo's working tree.

## Workflow

Use GSD commands for all phase work:
- `/gsd-quick` for small fixes
- `/gsd-execute-phase` for planned phase work
- `/gsd-debug` for investigation

## Do Not Touch

- `out/` parquet stores — generated daily snapshots; appended by `run_daily`, not hand-edited
- `.planning/phases-archive/` — archived phase history
- `.planning/` docs (GSD-managed)

---

**Hub:** [[gamma-omm/gamma-omm|Gamma OMM]] · **Planning:** [[_planning/gamma-omm/STATE|.planning/]]
