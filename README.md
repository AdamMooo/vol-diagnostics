# Gamma OMM — GEX Dashboard

Dealer gamma exposure monitor for SPY, QQQ, IWM. Pulls live options chains from CBOE delayed quotes, computes GEX from chain gamma (sourced directly from CBOE's American-model greeks), and surfaces positioning levels in a Streamlit dashboard and an HTML email report.

Defensible outputs only: **Net GEX (sign + magnitude)**, **Zero-γ level**, **Call/Put wall strikes** (single max one-sided GEX), **Δ-flow**, **IV30**. Vanna/charm/VEX/CHEX, wall clusters, vs-yesterday classifier, and the categorical regime label were removed in the 2026-05-11 methodology cleanup — they could not be defended at a quant PM's level of scrutiny.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Running

**Interactive dashboard:**
```powershell
streamlit run streamlit_app.py
```
Opens at `http://localhost:8501`.

**Daily email report (Outlook COM — Windows only):**
```powershell
python -m gex.run_daily --send
python -m gex.run_daily --dry-run   # writes out/gex_YYYYMMDD.html, no email
```

**Single-ticker CLI:**
```powershell
python -m gex.run_gex              # SPY
python -m gex.run_gex --ticker QQQ
python -m gex.run_gex --ticker IWM
```

## Dashboard

| Section | What it shows |
|---------|--------------|
| Cards | Spot, Net GEX, Δ-flow, Zero-γ level, Call/Put walls, IV30. Accent bar = sign of Net GEX |
| Cross-asset overview | Net GEX bar across selected tickers (color = sign) |
| Per-ticker expanders | Strike GEX chart, gamma profile, 30-day ZGL-vs-spot history |

Sidebar lets you filter tickers and refresh the cache (5-min TTL per ticker).

## Key Modules

| Module | Purpose |
|--------|---------|
| `streamlit_app.py` | Interactive dashboard |
| `gex/data_loader.py` | CBOE delayed quotes → `ChainSnapshot` |
| `gex/greeks_engine.py` | `add_greeks()` adds `T_years`; `bs_gamma()` used by `gamma_profile()` |
| `gex/exposure_engine.py` | GEX aggregation + gamma profile sweep |
| `gex/analytics.py` | `summarise()` → net GEX, ZGL, walls, δ-flow + plotly charts |
| `gex/compute.py` | Shared pipeline used by both daily report and streamlit |
| `gex/validation.py` | Parquet snapshot store (history for 30-day ZGL chart) |
| `gex/report.py` | HTML email builder |
| `gex/run_daily.py` | Daily orchestrator (snapshot + email + daily-note observation block) |

## Tests

```powershell
python -m pytest gex/tests/ -q
```
