---
title: v6.0 Options-Writing Model — SPY covered-call persistence signal
trigger_condition: v5.0 Data Foundation closed (Phases 23–25, 27 complete); Phase 23 model-readiness audit confirms VRP/vol-index depth sufficient to backtest
planted_date: 2026-07-26
---

First prescriptive milestone — the long-deferred MODEL-01/02 track. Answers "is writing a
covered call on SPY smart *and persistent*, not just true for 1–2 days." Scoped by Adam
2026-07-26 as **minimal defensible v1, fully autonomous, Learning Mode OFF for this
milestone**.

**Core thesis:** the "is it smart today" half is ~80% already built — `vol/vrp_history.py`
ranks the deep VRP percentile (vol_index − RV20×100) against a ~10yr window. The net-new work
is the *persistence* layer plus honest validation.

**v1 scope (three pieces, no HMM, no chain history needed):**

1. **Hysteresis (Schmitt trigger)** on the existing deep VRP percentile — enter "write CC"
   regime above ~70, exit only below ~40; the dead band kills daily whipsaw. Pair with a
   minimum-dwell debounce (K consecutive days). Cheapest, highest-leverage piece.
2. **Conditional persistence base rate** — given VRP in top tercile today, empirical P(still
   favorable N=15–20 sessions out). Report the **half-life of mean reversion** of the
   rich-premium regime as the honest trust-horizon. Fits the project's "conditional base
   rates primary, no hidden scoring" DNA. Leans on vol clustering (ARCH autocorrelation).
3. **Synthetic covered-call backtest** — the real work. No historical option chains needed:
   Black-Scholes-price a synthetic ~30-DTE call off each historical date's implied vol, roll
   against the realized path, prove the persistent signal beats always-write / never-write
   out of sample, with multiple-testing discipline (project's self-imposed gate before any
   new signal ships). Deep vol-index history (VIX→1990, VXN/RVX→2009) makes this deeply
   backtestable — the 2026-05-06 chain cold-start does NOT bite here.

**Explicitly out of v1:** HMM regime model (scope-capped; revisit only if base-rate + hysteresis
underperform), chain-derived features (cold-start too shallow), QQQ/IWM (SPY-first).

**Learning-mode note:** normally Adam hand-writes core quant estimators (global CLAUDE.md
Learning Mode). He chose to override that for this milestone — plan + execute autonomously,
including the core. If reopening, confirm that override still holds.

**Related design thinking:** the persistence half-life directly sets the right DTE to write at
(write near/under the half-life so the decision stays valid over the option's life).

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
<!-- LINKS:END -->
