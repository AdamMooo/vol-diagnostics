# Options Quant — Market Intelligence Dashboard

GEX monitor for SPY, QQQ, IWM — dealer gamma exposure, vanna, charm, and PM flow analytics.

## Running the Dashboard

```powershell
cd C:\dev\options-quant
.venv\Scripts\activate
streamlit run streamlit_app.py
```

Opens at `http://localhost:8501`.

## Using It

- **Sidebar** — select one or more of SPY / QQQ / IWM; hit **Refresh** to re-fetch (clears the 5-min cache)
- **Regime cards** — shows net GEX, VEX, delta-hedge flow ($/1% move), and vs-yesterday direction for each ticker; background colour reflects positive / negative / neutral gamma regime
- **Cross-asset overview** — bar chart comparing net GEX across selected tickers
- **Per-ticker expanders** — click a ticker to see strike GEX chart, gamma profile, and a summary table (Net GEX, VEX, CHEX, zero-gamma level, call wall, put wall)

Live chains fetched from CBOE delayed quotes JSON on first load (CBOE CDN, no auth required). yfinance retained for event study historical price data in `validation.py`. Results cached 5 minutes per ticker.

## Email Pipeline (unchanged)

```powershell
python -m gex.run_daily   # all 3 tickers → HTML email via Outlook COM
```

## Status

Last updated: 2026-05-06 | v3.1 Phase 5 complete (UAT signed off)
Hub: [[options-quant/options-quant]]
