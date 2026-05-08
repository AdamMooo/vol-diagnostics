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

Last updated: 2026-05-07 | v3.1 Phase 5 complete (UAT signed off) | **Parked: pre-demo hardening (v3.2) pending — see audit**
Hub: [[options-quant/options-quant]]

## Active workstream — pre-demo hardening (parked, resume in a few days)

Goal: harden GEX POC before showing head of capital markets. Audit completed 2026-05-07.

- **Audit doc:** [[_audits/gex-prep-audit-2026-05-07|GEX POC pre-demo audit]] — section-by-section claims/formulas/risks, Q&A prep, prioritized hardening queue
- **Next action:** `/gsd-plan-phase` for v3.2 with the P0 list (FRED rate, snapshot timestamp + history N display, clustered walls, metadata strip, concession block, NEUTRAL_ABS_FLOOR decision, Task Scheduler daily run)
- **Top 3 things to defend in the meeting:** (1) sign convention for SPY/QQQ/IWM dealer positioning, (2) mixed-greek model — CBOE American gamma + BS-European vanna/charm, (3) absolute GEX magnitude is methodology-dependent (sign and ZGL are the load-bearing outputs)
- **Concede upfront:** 15-min delay, OI is T-1, history is N=1 day so no event study yet
