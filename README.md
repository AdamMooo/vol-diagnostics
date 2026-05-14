# Gamma OMM — Dashboard

Dealer gamma exposure + implied vol structure for SPY, QQQ, IWM. Pulls live CBOE delayed-quote chains, computes GEX from CBOE-supplied American-model greeks, and surfaces positioning + vol structure in a Streamlit dashboard and an HTML email report.

## Defensibility

**Peer-reviewed predictive backing:**
- **Skew (25Δ put − 50Δ call)** — Xing, Zhang & Zhao (2010, *JFQA*) — 10.9% annual alpha on skew-sorted portfolios.

**Mechanistic / derivable:**
- **Net GEX** — Gatheral / Bergomi dollar-gamma framework; dealer-net-short positioning empirically confirmed by Garleanu, Pedersen & Poteshman (2009, *RFS*).
- **Hedge Shares/$1** — `Γ_net × OI × 100`; price-impact mechanism in Egebjerg & Kokholm (2024).
- **IV Surface** — OTM convention (Gatheral §2.1); log-moneyness axes per Cont & da Fonseca (2002).

**Model constructs (descriptive, not predictive):**
- **γ-flip** (formerly "Zero-γ Level") — zero peer-reviewed papers test it as a price level. Read as the model's gamma-sign-flip threshold, not a price target.
- **Call/Put Wall strikes** — trader lore. Describes where OI gamma is concentrated, not support/resistance.

**Explicitly removed for rigor:** vanna/charm exposures, hand-tuned regime labels, vs-yesterday classifier, wall clusters, OI×vega weighting — each carried more assumption than benefit.

Full research: [`research/methodology-deep-review.md`](research/methodology-deep-review.md) (academic literature with SSRN/DOI citations) and [`research/methodology-audit.md`](research/methodology-audit.md) (practitioner-source audit).

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
| **Top bar** | Selected tickers · date · data freshness (CBOE delayed, 15-min lag, OI as of prior session) |
| **Cards** | Spot, Net GEX, Hedge Shares/$1, γ-flip, Skew (25Δ), IV30. Accent bar = sign of Net GEX |
| **Per-ticker tabbed expanders** | **Strikes** — GEX by strike + gamma profile. **Vol** — 3D IV surface (OTM convention, log-moneyness) with γ-flip + Call/Put Wall meridians overlaid; skew term structure below. **History** — 30-day γ-flip vs spot + 30-day Skew (25Δ) |
| **Methodology & Assumptions expander** | All caveats consolidated: free CBOE feed (no OPRA), CBOE American option pricing model, live ^IRX risk-free rate, all filters explicit, model-construct tags on γ-flip + walls, dealer positioning assumption |

Sidebar lets you filter tickers and refresh the cache (5-min TTL per ticker).

## Key Modules

| Module | Purpose |
|--------|---------|
| `streamlit_app.py` | Interactive dashboard with tabbed expanders + methodology expander |
| `gex/data_loader.py` | CBOE delayed quotes → `ChainSnapshot` (greeks pre-computed by CBOE's American model) |
| `gex/greeks_engine.py` | `add_greeks()` adds `T_years`; `bs_gamma()` used only by `gamma_profile()` sweep |
| `gex/exposure_engine.py` | GEX aggregation, gamma profile sweep, `vol_surface_data()` (OTM convention), `compute_skew()` (25Δ put − 50Δ call) |
| `gex/analytics.py` | `summarise()` → Net GEX, γ-flip, walls, Hedge Shares/$1; plotly charts: strike GEX, gamma profile, IV surface (with γ-flip + wall meridians), skew term structure |
| `gex/compute.py` | Shared pipeline used by daily report and streamlit. `_get_risk_free_rate()` pulls live `^IRX` 3-month T-bill |
| `gex/validation.py` | Parquet snapshot store: `net_gex`, `zero_gamma_level`, `call_wall`, `put_wall`, `front_skew`, `put_25d_iv`, `call_50d_iv`, `iv30` |
| `gex/report.py` | HTML email builder |
| `gex/run_daily.py` | Daily orchestrator (snapshot + email + daily-note observation block). Scheduled Mon–Fri 16:30 ET via Windows Task Scheduler |

## Tests

```powershell
python -m pytest gex/tests/ -q
```

23 tests covering data loading, GEX aggregation, gamma profile, analytics, email rendering, snapshot store, and streamlit app boot.
