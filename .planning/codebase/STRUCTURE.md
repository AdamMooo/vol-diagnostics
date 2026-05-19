# Codebase Structure

**Analysis Date:** 2026-05-06

## Directory Layout

```
options-quant/
├── gex/                    # Active GEX analysis module
│   ├── __init__.py
│   ├── data_loader.py      # CBOE chain fetch → ChainSnapshot
│   ├── greeks_engine.py    # BS vanna/charm; add_greeks()
│   ├── exposure_engine.py  # GEX/VEX/CHEX compute + aggregation
│   ├── analytics.py        # Regime classification + Plotly charts
│   ├── compute.py          # Shared pipeline: compute_ticker()
│   ├── validation.py       # Parquet snapshot store + event study
│   ├── report.py           # HTML email builder
│   ├── emailer.py          # Outlook COM delivery
│   ├── run_gex.py          # Single-ticker entry point (PNG output)
│   ├── run_daily.py        # Daily orchestrator (all tickers + email)
│   └── tests/              # pytest unit tests
│       ├── test_greeks_engine.py
│       ├── test_exposure_engine.py
│       ├── test_exposure_flow.py
│       ├── test_analytics_summarise.py
│       ├── test_validation_history.py
│       └── test_streamlit_app.py
├── runners/
│   └── gex_daily.ps1       # Windows Task Scheduler registration script
├── assets/
│   └── gamma-icon-lg.png   # Streamlit favicon
├── out/                    # Generated output (not committed)
│   ├── gex_snapshots.parquet
│   ├── gex_YYYYMMDD.html
│   └── gex_strikes_*.png / gex_profile_*.png
├── streamlit_app.py        # Streamlit dashboard entry point
├── .streamlit/
│   └── secrets.toml        # PASSWORD for dashboard auth (gitignored)
├── .env                    # GEX_EMAIL_TO recipients (gitignored)
├── requirements.txt        # pip dependencies
├── .devcontainer/
│   └── devcontainer.json   # Codespaces config (Python 3.11, Streamlit on :8501)
├── .planning/              # GSD-managed planning files
├── .venv/                  # Local virtualenv (not committed)
│
│   — v2.1 sleeve engine (parked) —
├── run.py                  # Text dashboard to stdout
├── build_report.py         # HTML report generator
├── local_data.py           # Data dispatch (FreeCon: CBOE + FRED)
├── data_layer.py           # build_panels() → Panels dataclass
├── signals.py              # build_signals() → Signals dataclass
├── backtest.py             # run_backtest() → BacktestResults
├── dashboard.py            # Section helpers for report
├── stats_rigor.py          # Holm-Bonferroni, block bootstrap
├── sensitivity.py          # TC sensitivity + tail risk
├── hmm.ipynb               # v1.0 legacy — DO NOT MODIFY
└── WALKTHROUGH.md          # Quant team per-section guide
```

## Directory Purposes

**`gex/`:**
- Purpose: All active GEX analysis code
- Contains: pipeline modules, output adapters, tests
- Key files: `compute.py` (pipeline), `data_loader.py` (ingestion), `analytics.py` (charts + regime)

**`gex/tests/`:**
- Purpose: pytest unit tests for GEX module
- Contains: one test file per module being tested
- Co-located with source (inside `gex/`, not a root-level `tests/`)

**`runners/`:**
- Purpose: Operational scripts for scheduling/automation
- Contains: `gex_daily.ps1` — PowerShell Task Scheduler registration

**`assets/`:**
- Purpose: Static assets for Streamlit
- Contains: `gamma-icon-lg.png` (favicon)

**`out/`:**
- Purpose: Generated output; not committed to git
- Contains: parquet snapshots, HTML reports, PNG charts
- Generated: Yes
- Committed: No

**`v2.1 root-level files` (parked):**
- `run.py`, `build_report.py`, `local_data.py`, `data_layer.py`, `signals.py`, `backtest.py`, `dashboard.py`, `stats_rigor.py`, `sensitivity.py`
- Status: Parked — do not modify or add new code here

## Key File Locations

**Entry Points:**
- `streamlit_app.py` — Streamlit dashboard (primary user interface)
- `gex/run_daily.py` — Daily email orchestrator
- `gex/run_gex.py` — Single-ticker debug/POC runner

**Shared Pipeline:**
- `gex/compute.py` — `compute_ticker()`: all callers go through here

**Configuration:**
- `.env` — email recipients (`GEX_EMAIL_TO`)
- `.streamlit/secrets.toml` — dashboard password (`PASSWORD`)
- `requirements.txt` — Python dependencies

**Core Logic:**
- `gex/data_loader.py` — CBOE fetch and OPRA parsing
- `gex/greeks_engine.py` — Black-Scholes vanna/charm formulas
- `gex/exposure_engine.py` — GEX/VEX/CHEX formulas and aggregation
- `gex/analytics.py` — Regime classification, zero-gamma interpolation, Plotly charts
- `gex/validation.py` — Parquet snapshot store

**Email:**
- `gex/report.py` — HTML builder
- `gex/emailer.py` — Outlook COM sender

**Testing:**
- `gex/tests/` — all tests live here

## Naming Conventions

**Files:**
- `snake_case.py` throughout
- Test files: `test_{module_name}.py`
- Output files: `gex_{type}_{TICKER}_{DATE}.{ext}`

**Modules:**
- Verb-noun pairs for action modules: `data_loader`, `greeks_engine`, `exposure_engine`
- Noun for pure data/analytics: `analytics`, `validation`, `report`

## Where to Add New Code

**New GEX metric or exposure type:**
- Formula: `gex/exposure_engine.py` (follow `compute_vex`/`compute_chex` pattern)
- Pipeline integration: `gex/compute.py:compute_ticker()`
- Chart: `gex/analytics.py`
- Tests: `gex/tests/test_exposure_engine.py` or new `test_{metric}.py`

**New dashboard display element:**
- `streamlit_app.py` — add to `render_regime_card()` or `render_section()`

**New email column:**
- `gex/report.py` — add to `_index_row()` or `_purpose_row()`, update `_index_table()`/`_purpose_table()` header

**New ticker list:**
- `gex/run_daily.py`: `INDEX_TICKERS` or `PURPOSE_TICKERS`
- `streamlit_app.py`: `INDEX_TICKERS` or `PURPOSE_TICKERS`
- `gex/report.py`: `TICKER_LABEL` dict

**Utilities or helpers:**
- If GEX-specific: add to the most relevant existing module in `gex/`
- No separate `utils.py` currently exists; avoid creating one unless multiple modules need the same helper

**New snapshot field:**
- `gex/validation.py:save_snapshot()` — add field to `row` dict
- Existing parquet rows will have NaN for new column; handle in consumers

## Special Directories

**`.planning/`:**
- Purpose: GSD workflow planning files
- Generated: Yes (by GSD commands)
- Committed: Yes

**`.claude/`:**
- Purpose: Claude Code agent worktrees and session data
- Generated: Yes
- Committed: Partially (CLAUDE.md yes; worktrees no)

**`out/`:**
- Purpose: All generated artefacts
- Generated: Yes
- Committed: No (in .gitignore)

**`.venv/`:**
- Purpose: Python virtual environment
- Generated: Yes
- Committed: No

---

*Structure analysis: 2026-05-06*

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
