# Technology Stack

**Analysis Date:** 2026-05-06

## Languages

**Primary:**
- Python 3.13.13 — all application code

## Runtime

**Environment:**
- CPython 3.13.13 (local Windows, `C:\Users\AdamMorris\AppData\Local\Programs\Python\Python313`)

**Package Manager:**
- pip with `requirements.txt`
- Lockfile: not present (ranges only in requirements.txt)
- venv at `options-quant/.venv`

## Frameworks

**Web/Dashboard:**
- Streamlit >=1.57,<2.0 — interactive GEX dashboard (`streamlit_app.py`)

**Numerical:**
- NumPy >=1.26,<3.0 — vectorised array operations throughout `gex/`
- SciPy >=1.13,<2.0 — `scipy.stats.norm` for Black-Scholes PDF in `gex/greeks_engine.py`
- pandas >=2.0,<3.0 — DataFrame pipeline; all inter-module data exchange

**Statistics (v2.1 sleeve engine — parked):**
- statsmodels >=0.14,<1.0 — Holm-Bonferroni, block bootstrap in `stats_rigor.py`

**Visualisation:**
- Plotly >=5.0,<7.0 — interactive charts in `gex/analytics.py` and `streamlit_app.py`
- Matplotlib >=3.9,<4.0 — static PNG output in `gex/run_gex.py` (Agg backend)
- Seaborn >=0.13,<1.0 — available; not actively used in GEX module

**Testing:**
- pytest — test runner (no version pinned in requirements.txt; present in `.venv`)

**Build/Dev:**
- python-dotenv >=1.0 — loads `.env` for `GEX_EMAIL_TO` in `gex/emailer.py`

## Key Dependencies

**Critical:**
- yfinance >=0.2.40 — historical price download in `gex/validation.py` (`event_study()`)
- requests >=2.31 — CBOE chain fetch in `gex/data_loader.py`
- pyarrow >=15.0 — parquet read/write for snapshot store (`out/gex_snapshots.parquet`)
- pandas_market_calendars >=4.4 — NYSE trading day checks in `gex/validation.py` and `gex/run_daily.py`
- pytz — Eastern timezone handling in `gex/run_daily.py`

**Infrastructure:**
- win32com.client (pywin32) — Outlook COM automation for email send in `gex/emailer.py`; Windows-only; not in requirements.txt (assumed installed system-wide or separately)

**Data (v2.1 sleeve engine — parked):**
- pandas-datareader >=0.10.0 — FRED data fetch in `local_data.py`

## Configuration

**Environment:**
- `.env` file at project root — read only by `gex/emailer.py`
- Required key: `GEX_EMAIL_TO` (comma-separated recipient list)
- `.streamlit/secrets.toml` — `PASSWORD` key for Streamlit dashboard auth gate

**Build:**
- No build config; pure Python package
- `.devcontainer/devcontainer.json` — Codespaces/devcontainer config targets Python 3.11 image, auto-runs Streamlit on port 8501

## Platform Requirements

**Development:**
- Windows (primary) — email send via `win32com`/Outlook; Task Scheduler via `runners/gex_daily.ps1`
- Codespaces-compatible for Streamlit-only use (devcontainer config present)

**Production:**
- Local Windows machine running Outlook
- Windows Task Scheduler triggers `gex.run_daily` at 16:30 ET on trading days

---

*Stack analysis: 2026-05-06*

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
