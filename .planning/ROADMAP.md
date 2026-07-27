# Roadmap: v6.0 — SPY Covered-Call Sleeve Timing

**Opened:** 2026-07-27 · First prescriptive milestone (the long-deferred MODEL-01/02 track). Learning Mode OFF.
**Prior milestones:** see `.planning/MILESTONES.md` (v1.0–v5.0). Phase numbering continues from 27.

**North star:** a weekly, iPhone-friendly PDF *review* that says where S&P premium sits vs ~10yr, whether the covered-call environment is favorable *and persistent*, and how it's evolving — as a supporting input to a discretionary **USCC↔VFV** tilt, backed by an honestly-validated model. Portability is a hard constraint (production is 100% cloud; report generated in CI).

**Critical path:** 28 → 29 → 30 (gate) → 31. The restore drill and Phase 28 are independent and can go anytime.

---

### Quick task: Restore drill (DUR-01)

**Goal:** Confirm `restore_from_oci` actually recovers `out/` from the OCI bucket into a clean location. Backup itself is live (2026-07-23); this closes the one untested half (v5.0 BACKUP-02). Not a phase — a one-off verification.

---

### Phase 28: Proxy Data Layer

**Goal:** Ingest the buy-write index history that the backtest needs. BXM (S&P 500 BuyWrite, ATM/monthly/100%-cover — the deep proxy for USCC, to 1986) and BXMD (OTM variant) stored like `vol_index` (Bloomberg-swappable, cold-start-safe); plus USCC.TO live NAV/price for cross-check.
**Requirements:** PROXY-01, PROXY-02
**Depends on:** — (data-layer pattern mirrors `engine/data/vol_index.py`)
**Plans:** TBD (`/gsd-plan-phase 28`)

### Phase 29: Persistence Engine

**Goal:** The net-new statistical layer. Hysteresis (Schmitt) regime on the deep VRP percentile (reusing the Phase-26 machinery), rich-regime half-life (AR(1) + survival, cross-checked), and conditional persistence base-rates P(still favorable in N | top-tercile today). Pure/testable, no I/O in the estimators.
**Requirements:** PERSIST-01, PERSIST-02, PERSIST-03
**Depends on:** Phase 28 (needs the aligned VRP/proxy series)
**Plans:** TBD

### Phase 30: Validated Backtest — the gate

**Goal:** Prove the tilt. Regime-conditioned USCC↔VFV backtest on real BXM vs S&P total-return, true OOS split, multiple-testing correction across the parameter grid, cross-checked vs USCC live, benchmarked against static BXM / static S&P TR / always-never-tilt. **BT-GATE:** no signal ships to the report unless it beats benchmarks OOS after MT-correction.
**Requirements:** BT-01, BT-02, BT-03, BT-04, BT-GATE
**Depends on:** Phase 29
**Plans:** TBD

### Phase 31: Weekly PDF Review

**Goal:** The deliverable, built around *validated* numbers only. Weekly Sat-AM PDF (weasyprint in CI, iPhone-native, portable), trajectory-first, consistent template; environment + base-rates framing with a conviction dial (no prescribed structure); metrics via a labeled BXM/USCC yardstick; palette redesigned via the dataviz skill; SPY CC analysis + SPY/QQQ/IWM location. Daily email + dashboard retained.
**Requirements:** RPT-01, RPT-02, RPT-03, RPT-04, RPT-05
**Depends on:** Phase 30 (ships only after the gate clears)
**Plans:** TBD

---

**Future seam (out of v6.0):** a bull/bear gate from the separate `regime-detection` system sits *above* the tilt (bear → neither USCC nor VFV). v6.0 designs a clean "risk-on assumed" boundary; it does not build the gate.

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
<!-- LINKS:END -->
