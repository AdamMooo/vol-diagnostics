Real-time options market diagnostic platform on SPY, QQQ and IWM.

Combines four analytical layers into one unified dashboard:

1. VRP (Vol Risk Premium) Percentile: Is IV rich or cheap? Ranks current IV spread against 10+ years of CBOE vol-index history. Tells you sizing, not direction.

2. GEX (Gamma Exposure): How will dealers hedge? Aggregates option gamma by strike and expiry (capped at 90 DTE), shows whether dealers are net long (stabilizing) or short (destabilizing) gamma. Market structure, not a price signal.

3. Arbitrage Constraint Audit: Is the vol surface mathematically consistent? Checks three no-arbitrage axioms on every daily surface - butterfly, calendar, tail stability. Violations auto-repaired via soft constraint mode. Guarantees downstream hedging models work.

4. Vanna and Volga (Second-Order Greeks): How does the surface deform under spot and vol shocks? Vanna shows if spot-vol correlation is priced in. Volga shows if vol-of-vol is expensive or cheap. Surface stability detects regions where fits break down.

Technical Stack: Python 3.11, Streamlit dashboard, Docker on Oracle Cloud. Free CBOE data. Daily refresh weekday mornings via GitHub Actions. 483 unit tests. Live at https://40.233.113.63.nip.io

Design Principles: Descriptive only, no directional forecasts. Evidence-tiered, every metric backed by academic papers. Rigor first, tested four candidate signals and removed them all. Source-agnostic, Bloomberg or OPRA data would be a one-class swap. Constraint-enforced, surfaces audited and auto-repaired daily.

What's NOT Included: No return predictions. No leverage recommendations. No single-name options. No predictive ML. No real-time data.

Built for income-sleeve option writers. Decision framework, not a trading signal.
