# Options Quant — GEX Dashboard

Dealer gamma exposure monitor for SPY, QQQ, and IWM. Pulls live options chains via CBOE, computes GEX / VEX / CHEX with Black-Scholes Greeks, and surfaces regime signals in an interactive Streamlit dashboard.

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
python -m gex.run_daily
```

**Single-ticker CLI output:**
```powershell
python -m gex.run_gex              # SPY
python -m gex.run_gex --ticker QQQ
python -m gex.run_gex --ticker IWM
```

## Dashboard

| Section | What it shows |
|---------|--------------|
| Regime cards | Net GEX, VEX, delta-hedge flow ($/1% move), vs-yesterday direction |
| Cross-asset overview | Bar chart comparing net GEX across selected tickers |
| Per-ticker expanders | Strike GEX chart, gamma profile, summary table (ZGL, call wall, put wall) |

Sidebar lets you filter tickers and refresh the cache (5-min TTL per ticker).

## Key Modules

| Module | Purpose |
|--------|---------|
| `streamlit_app.py` | Interactive dashboard |
| `gex/data_loader.py` | CBOE chain pull |
| `gex/greeks_engine.py` | Black-Scholes gamma, vanna, charm |
| `gex/exposure_engine.py` | GEX / VEX / CHEX aggregation |
| `gex/analytics.py` | Regime classification, charts |
| `gex/validation.py` | Parquet snapshot store, vs-yesterday |
| `gex/run_daily.py` | Daily email orchestrator |

## Tests

```powershell
python -m pytest gex/tests/ -q
```
