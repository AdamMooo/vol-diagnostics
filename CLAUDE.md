# CLAUDE — Options Quant — Sleeve Allocation Framework
Last updated: 2026-05-04 | Status: active milestone v2.1 — local-first POC build

## Repo Card

- **Runtime:** local Python (venv). Cron2/Jupyter is a future migration target, not the build environment.
- **Entry points:** `python run.py` (text dashboard to stdout), `python build_report.py` (generates HTML report)
- **Output artifact:** `out/sleeve_report_YYYYMMDD.html` — single self-contained file, charts embedded as base64
- **Data:** free public sources (CBOE + FRED via `pandas-datareader`). Bloomberg/emds_client deferred — add if team greenlights the POC.
- **Workflow:** GSD (`.planning/`)

## What It Does

**v2.1 (current):** Polish, calibrate, and deliver the engine as a quant-readable POC. Three deliverables: (1) HTML report (`out/sleeve_report_YYYYMMDD.html`) with top-of-page current state + embedded charts, (2) WALKTHROUGH.md for async team handoff, (3) cleanup of forecasting drift. Ship on free data; if the team sees value, Bloomberg calibration is a one-class swap.

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
- **Interpretability first:** scorecard primary, weights printed, no hidden coefficients.
- **Strategy menu:** covered call, cash-covered put, collar, short straddle. Dispersion out of scope.
- **No new signals this phase:** six signals + fragility composite. Locked until team validates.
- **Windows paths:** use pathlib or `os.path.join` throughout.
- **No PDIV / HMM this phase:** locked out per D-16 in `01-CONTEXT.md`.

## Key Files

| File | Purpose |
|------|---------|
| `run.py` | Orchestrator — prints text dashboard to stdout |
| `build_report.py` | HTML report generator — `python build_report.py` → `out/sleeve_report_YYYYMMDD.html` |
| `local_data.py` | Data dispatch (`FreeCon` for CBOE+FRED free data) |
| `data_layer.py` | `build_panels()` → `Panels` dataclass |
| `signals.py` | `build_signals()` → `Signals` dataclass |
| `backtest.py` | `run_backtest()` → `BacktestResults` |
| `dashboard.py` | Section helpers (`section_a_state`, `section_c_buckets`, etc.) |
| `stats_rigor.py` | Holm-Bonferroni, stationary block bootstrap |
| `sensitivity.py` | TC sensitivity + tail risk metrics |
| `WALKTHROUGH.md` | Per-section quant team guide (generated this phase) |
| `hmm.ipynb` | v1.0 legacy — DO NOT MODIFY |
| `Data.ipynb` | Reference for data access patterns |

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
