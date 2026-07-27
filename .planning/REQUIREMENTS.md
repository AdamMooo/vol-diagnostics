# Requirements: v6.0 — SPY Covered-Call Sleeve Timing

**Defined:** 2026-07-27
**Core Value:** Turn the deep VRP percentile into a *persistent, honestly-validated* read on whether the covered-call sleeve is well-compensated right now — a supporting input to a discretionary USCC↔VFV tilt, never a trigger.

**Decision it supports:** tilt **USCC.TO** (Global X S&P 500 Covered Call ETF) ↔ **VFV** (plain S&P 500), sized by the user on a conviction dial. Beta + unhedged USD/CAD FX net out between the two legs, so the VRP premium-richness signal is the right (and sufficient) input. Sits *under* a future `regime-detection` bull/bear gate (seam designed, gate out of scope).

**Learning Mode:** OFF for this milestone (autonomous incl. core estimators — reconfirmed 2026-07-27).

## v1 Requirements

### Durability leftover (DUR)
- [ ] **DUR-01**: Restore drill — verify `restore_from_oci` actually recovers `out/` from the OCI bucket (closes v5.0's BACKUP-02; backup itself live since 2026-07-23)

### Proxy Data Layer (PROXY)
- [ ] **PROXY-01**: BXM (and BXMD) buy-write index history ingested into the data layer (stored like `vol_index`, Bloomberg-swappable, cold-start-safe) — gives backtest depth to 1986
- [ ] **PROXY-02**: USCC.TO live NAV/price history ingested for cross-check against the BXM proxy

### Persistence Engine (PERSIST)
- [ ] **PERSIST-01**: Hysteresis (Schmitt) regime on the deep VRP percentile — enter/exit bands + minimum-dwell debounce, reusing the Phase-26 hysteresis machinery
- [ ] **PERSIST-02**: Rich-regime half-life estimated two independent ways (AR(1) coefficient + empirical episode-survival) and cross-checked; half-life sets the implied write tenor
- [ ] **PERSIST-03**: Conditional persistence base-rate — empirical P(still favorable in N sessions | top-tercile today), N ∈ {5,10,15,20}

### Validated Backtest (BT) — the ship gate
- [ ] **BT-01**: Regime-conditioned backtest of the USCC↔VFV tilt using **real BXM vs S&P total-return** series (no synthetic Black-Scholes pricing)
- [ ] **BT-02**: True out-of-sample evaluation (walk-forward or held-out split) — no full-sample fit
- [ ] **BT-03**: Multiple-testing correction across the parameter grid (entry/exit bands, dwell, tenor)
- [ ] **BT-04**: Live cross-check vs USCC.TO history; benchmarks = static BXM, static S&P TR, and always-/never-tilt
- [ ] **BT-GATE**: No tilt signal reaches the report unless it beats benchmarks OOS *after* MT-correction

### Weekly Review Report (RPT)
- [ ] **RPT-01**: Weekly PDF generated Sat-AM in CI (weasyprint), iPhone-native, portable (no local-machine dependency; local = HTML preview only)
- [ ] **RPT-02**: Consistent trajectory-first template — skeleton: regime header → cross-index location → SPY CC-environment block → surface/evolution → what-would-have-to-change → methodology link
- [ ] **RPT-03**: Framing = environment + base-rates only (conviction dial, no prescribed structure); metrics = premium/mo, hit-rate + worst-case, half-life, vs-benchmark edge (profit metrics via a labeled BXM/USCC yardstick, explicitly "what the environment paid, not a rec")
- [ ] **RPT-04**: Palette redesigned via the dataviz skill (fix the current confusing colors); 2–3 samples rendered for selection at build
- [ ] **RPT-05**: SPY covered-call analysis + SPY/QQQ/IWM percentile location context; existing daily email + dashboard retained unchanged

## Out of Scope (v6.0)

| Feature | Reason |
|---------|--------|
| HMM regime model | Scope-capped; revisit only if base-rate + hysteresis underperform |
| Chain-derived features | Cold-start too shallow (own snapshots only since 2026-05-06) |
| QQQ/IWM covered-call modeling | SPY-first; QQQ/IWM appear as location context only |
| Bull/bear regime gate | Belongs to the separate `regime-detection` system; v6.0 designs the seam, not the gate |
| FX timing | USD/CAD nets out of the USCC-vs-VFV relative choice; a real-return factor, not a signal |
| Synthetic Black-Scholes backtest | Superseded by the real BXM index (drops the American-option error + haircut fudge) |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DUR-01 | quick task | Pending |
| PROXY-01/02 | Phase 28 | Pending |
| PERSIST-01/02/03 | Phase 29 | Pending |
| BT-01/02/03/04/GATE | Phase 30 | Pending |
| RPT-01/02/03/04/05 | Phase 31 | Pending |

**Coverage:** 16 v1 requirements, all mapped. Prior priors: `research/covered-call-spike-findings.md` (reconstructed). Seed: `.planning/seeds/v6-covered-call-persistence-model.md`.

---
*Requirements defined: 2026-07-27*

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
<!-- LINKS:END -->
