### Phase 16: VRP Percentile

**Goal**: The PM can see today's VRP (vol-index implied vol minus RV20 realized vol) for each index together with its percentile rank against its own history, computed from one internally-consistent series and labeled with the lookback window.
**Depends on**: Phase 15
**Requirements**: VRP-01, VRP-02, VRP-03
**Success Criteria** (what must be TRUE):

  1. The dashboard and email display today's VRP scalar for SPY, QQQ, and IWM (vol-index minus RV20).
  2. Each VRP value is accompanied by its percentile rank (e.g. "74th percentile, 252-day lookback") with the lookback window explicitly labeled.
  3. The percentile is computed using only the vol-index series for both the current reading and its history — snapshot IV30 is never mixed into the VRP history (verifiable by reading the computation path).
  4. When fewer sessions exist than the lookback window, the percentile is either omitted or labeled with the actual available count — never silently computed on a thin sample without disclosure.

**Plans**: 2 plans

Plans:
**Wave 1**

- [ ] 16-01-PLAN.md — gex/vrp_history.py vrp_percentile() engine (vol-index − RV20 series, isolated yf fetch) + TICKER_VOL_INDEX/VRP_PERCENTILE_LOOKBACK in config.py

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 16-02-PLAN.md — Wire into compute_ticker (vol-index VRP scalar + precomputed percentile, widen yf to 400d) + VRP CardField (email + dashboard parity)

---

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
