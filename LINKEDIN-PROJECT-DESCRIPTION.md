# Vol Diagnostics — LinkedIn Project Description

**Technical project overview for LinkedIn profile**

---

## Headline (120 chars max)

Volatility diagnostics platform: real-time IV surface analysis, dealer positioning, arbitrage-free pricing guarantees

---

## Full Description

### What It Does

Real-time options market diagnostic platform for income-sleeve PMs writing covered calls and cash-secured puts on SPY/QQQ/IWM. Combines four analytical layers into one unified dashboard:

1. **VRP (Vol Risk Premium) Percentile** — Is IV rich or cheap? Ranks current IV spread (realized minus implied) against 10+ years of CBOE vol-index history. Tells you sizing, not direction.

2. **GEX (Gamma Exposure)** — How will dealers hedge? Aggregates option gamma by strike and expiry (capped at 90 DTE), shows whether dealers are net long (stabilizing) or short (destabilizing) gamma. Signs market structure under spot moves; not a price signal.

3. **Arbitrage Constraint Audit** — Is the vol surface mathematically consistent? Checks three no-arbitrage axioms on every daily surface:
   - **Butterfly**: ∂²C/∂K² > 0 (option prices convex in strike)
   - **Calendar**: ∂σ²T/∂T > 0 (total variance increases with time)
   - **Tail stability**: Wing curvature bounded (not oscillating)
   
   Violations auto-repaired via soft constraint mode (reduces smoothing). Guarantees downstream hedging models work.

4. **Vanna/Volga (Second-Order Greeks)** — How does the surface deform under spot/vol shocks?
   - **Vanna** (∂²C/∂S∂σ): Spot-vol correlation pricing. Negative vanna = market prices inverse spot-vol link (healthy).
   - **Volga** (∂²C/∂σ²): Vol-of-vol market pricing. Tells you if volatility straddles are expensive or cheap.
   - **Surface stability**: RMS curvature metric. Detects regions where fits break down.

### Technical Stack

- **Runtime**: Python 3.11+ (venv). Runs daily via GitHub Actions (weekday mornings).
- **Frontend**: Streamlit (interactive 3D vol surface, real-time cards, compare/evolution tabs)
- **Data**: Free CBOE delayed quotes (JSON), CBOE vol-index history (1990+), yfinance closes, FRED rates
- **Pipeline**: 
  - `engine/compute.py` — single source of truth for all daily metrics
  - `engine/surface/arbitrage_constraints.py` — constraint checking (butterfly, calendar, tail)
  - `engine/gex/greeks_second_order.py` — vanna/volga grid computation
  - `engine/surface/surface_constraints_integration.py` — RBF fitting + constraint repair
  - `engine/run_daily.py` — orchestrator; saves parquet snapshots + HTML email
- **Output**: Daily email + parquet stores (gex_snapshots, surface_history, vol_index, surface_evolution)
- **Deployment**: Docker on Oracle Cloud Always-Free (live at https://40.233.113.63.nip.io)

### Key Design Decisions

1. **Descriptive Only** — No predictive claims. Measures current environment + historical context, not market direction. Four candidate signals were tested and removed (returned null on forward tests).

2. **Evidence-Tiered** — Every dashboard metric is labeled with the evidence behind it. Where sample is too thin (e.g., <252 sessions of history), the read is hidden, not shown with an asterisk.

3. **No Predictive Gate** — Tested whether VRP percentile could time a portfolio tilt. It couldn't. Deleted the feature instead of shipping with a caveat. Rigor over false positives.

4. **Constraint Enforcement** — Vol surfaces can violate no-arbitrage axioms if fit poorly. Built constraint checking + auto-repair to catch bad surfaces before they break hedging models.

5. **Free Data, Swappable Source** — Uses free CBOE data. Data loader is one class; Bloomberg/OPRA swap is a one-line change. Everything downstream is source-agnostic, proving methodology holds regardless of feed.

6. **GEX Demoted by Design** — Dealer gamma is included but labeled a model construct, capped at 90 DTE (investor-written calls beyond that), and used only for move-size reads (sign), not price levels. Counter-evidence (Dim, Eraker & Vilkov 2023 on 0DTE) is engaged with, not ignored.

### Academic Backing

- **VRP methodology**: Carr & Wu (2009) "Variance Risk Premiums" (*Review of Financial Studies*)
- **Gamma hedging mechanism**: Baltussen et al. (2021) "Hedging Demand and Market Intraday Momentum" (*JFE*)
- **Dealer positioning (index options)**: Gârleanu, Pedersen & Poteshman (2009) "Demand-Based Option Pricing" (*RFS*)
- **Arbitrage-free surfaces**: Breeden-Litzenberger formula; Gatheral (2006) "The Volatility Surface"; Bergomi (2016) "Stochastic Volatility Modeling"
- **Counter-evidence**: Dim, Eraker & Vilkov (2023) on 0DTE gamma propagation; Muravyev (2016) on dealer positioning in single-name options

### Metrics & Testing

- **Test coverage**: 483 unit tests (pytests across all modules)
- **Daily freshness**: Health check verifies snapshot currency and session-depth targets
- **Surface fit quality**: RMSE, coverage %, max residual logged daily
- **Constraint audit trail**: Butterfly/calendar/tail violations logged per surface
- **Production readiness**: Soft repair mode enabled; strict mode available for fail-fast enforcement

### What's NOT Included

- No directional forecasts or market timing
- No leverage recommendations
- No single-name options (requires dealer-positioning data not available free)
- No predictive ML models (methodology audit stands against that)
- No real-time data (15-minute CBOE delay acceptable for portfolio-level decisions)

### Impact

Reduces surface model risk by catching and fixing arbitrage violations before they break downstream hedging. Adds surface deformation visibility (vanna/volga) for positioning decisions. Provides historical context (VRP percentile, 10yr depth) for sizing option writing programs.

---

## Links

- **Live Dashboard**: https://40.233.113.63.nip.io
- **Methodology**: See `research/methodology-deep-review.md` (peer-review audit trail)
- **Constraint Details**: See `.planning/SURFACE-CONSTRAINTS-IMPLEMENTATION.md`
- **Architecture**: See `CLAUDE.md` (module map + design decisions)
- **Interview Explainer**: See `.planning/INTERVIEW-EXPLAINER.md` (4-layer breakdown for explaining the system)

---

## For Interviews

See `.planning/INTERVIEW-EXPLAINER.md` for:
- 30-second pitch
- 4-layer technical breakdown
- How it all fits together (daily workflow)
- Why each metric matters
- Common misconceptions corrected
- Academic backing
- Honest limitations
- 4 interview scenarios + sample answers
