# CLAUDE — Options Quant — Sleeve Allocation Framework
Last updated: 2026-05-04 | Status: active milestone v2.1 — HTML report ready, Bayesian reframe shipped

## Repo Card

- **Runtime:** local Python (venv). Bloomberg/Cron2 is a future swap, not the build environment.
- **Entry points:** `python run.py` (text dashboard to stdout), `python build_report.py` (generates HTML report)
- **Output artifact:** `out/sleeve_report_YYYYMMDD.html` — single self-contained file, charts embedded as base64
- **Data:** free public sources (CBOE + FRED). Bloomberg deferred — one-class swap in `local_data.py` if team greenlights.
- **Workflow:** GSD (`.planning/`)

## What It Does

**v2.1 (current):** Deliver the engine as a quant-readable HTML report. Leads with a conditional summary (today's signal quartiles → historical base rates per sleeve), followed by full signal analysis and statistical context. Ships on free data. Bayesian reframe complete: equity chart removed, Section E carries unconditional bull-market caveat, section order is conditional → A → signal chart → B → C → D → E → G → H.

**v2.0 (closed):** Engine build — signals, sleeve backtest, decision dashboard, statistical rigor (Holm-Bonferroni, block bootstrap, 74 tests). Archived under `.planning/phases-archive/v2.0-engine/`.

**v1.0 (legacy):** Single-fund HMM regime diagnostic in `hmm.ipynb` — preserved untouched.

## Local Setup

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py          # smoke test — should print text dashboard
python build_report.py # generates out/sleeve_report_YYYYMMDD.html
```

`requirements.txt` tracks the stack. Add packages there when needed.

## Constraints

- **No predictive claims:** descriptive of current environment + historical analog only.
- **Interpretability first:** conditional base rates primary, no hidden scoring or weighting.
- **Strategy menu:** covered call, cash-covered put, collar, short straddle. Dispersion out of scope.
- **No new signals:** six signals + fragility composite locked until team validates current set.
- **Windows paths:** use pathlib or `os.path.join` throughout.
- **No PDIV / HMM this phase:** locked per scope cap.

## GEX POC (new direction — dealer gamma exposure)

```
python -m gex.run_gex                # SPY, saves charts to out/
python -m gex.run_gex --ticker QQQ   # different underlying
```

| Module | Purpose |
|--------|---------|
| `gex/data_loader.py` | yfinance chain pull → `ChainSnapshot` |
| `gex/greeks_engine.py` | Black-Scholes gamma vectorised; `add_greeks()` enriches chain df |
| `gex/exposure_engine.py` | GEX = gamma × OI × 100 × S² × 0.01; strike/expiry aggregation; gamma profile curve |
| `gex/analytics.py` | Net GEX, zero-gamma level, call/put walls, regime classification, matplotlib charts |
| `gex/run_gex.py` | Entry point — fetch → compute → print summary → save PNGs to `out/` |
| `gex/validation.py` | Parquet snapshot store + event-study (positive vs negative gamma days vs next-day range) |

Sign convention: calls positive, puts negative. Positive net GEX = dealers net long gamma (stabilising). Zero-gamma level found via linear interpolation of profile sign change.

Bloomberg upgrade path: swap `gex/data_loader.py` only — everything else is data-source-agnostic.

## Key Files (v2.1 — parked)

| File | Purpose |
|------|---------|
| `run.py` | Orchestrator — prints text dashboard to stdout |
| `build_report.py` | HTML report generator — `python build_report.py` → `out/sleeve_report_YYYYMMDD.html` |
| `local_data.py` | Data dispatch (`FreeCon` for CBOE+FRED free data) |
| `data_layer.py` | `build_panels()` → `Panels` dataclass |
| `signals.py` | `build_signals()` → `Signals` dataclass |
| `backtest.py` | `run_backtest()` → `BacktestResults` |
| `dashboard.py` | Section helpers including `section_today_conditional`, `section_a_state`, `section_c_buckets`, etc. |
| `stats_rigor.py` | Holm-Bonferroni, stationary block bootstrap |
| `sensitivity.py` | TC sensitivity + tail risk metrics |
| `WALKTHROUGH.md` | Per-section quant team guide |
| `hmm.ipynb` | v1.0 legacy — DO NOT MODIFY |

## Workflow

Use GSD commands for all phase work:
- `/gsd-quick` for small fixes
- `/gsd-execute-phase` for planned phase work
- `/gsd-debug` for investigation

## Do Not Touch

- `hmm.ipynb` — v1.0 legacy artifact, preserved untouched
- `.planning/phases-archive/` — archived phase history
- `data/` folder contents (source exports)
- `.planning/` docs (GSD-managed)

---

**Hub:** [[options-quant/options-quant|Options Quant]] · **Planning:** [[.planning/planning|.planning/]]
