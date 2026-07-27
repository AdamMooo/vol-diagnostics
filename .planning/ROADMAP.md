### Phase 27: Microstructure Monitor UI

**Goal**: The dashboard lands on a distribution board (percentile strip + 10-session trail per metric×ticker, ~15 rows) with per-row evidence panels (metric history with bands + mechanism view: smile / diff surface / implied-vs-realized pair); the daily email becomes event-shaped (band entries + escalations only, near-empty on normal days) with methodology boilerplate cut to a single link. Existing Surfaces/Positioning tabs unchanged as the exploration layer; net-GEX sign shown as a state chip, not a ranked row.
**Requirements**: SC-1..SC-7 (derived success criteria in 27-CONTEXT.md — no formal REQUIREMENTS.md IDs)
**Depends on:** Phase 26 (consumes its severity ranks and alert events)
**Canonical refs:** `.planning/notes/microstructure-monitor-design.md`, `.planning/todos/pending/email-boilerplate-cut.md`
**Plans:** 4 plans

Plans:

**Wave 1**

- [x] 27-01-PLAN.md — Read-side foundation: monitor_reader.py bulk-read adapter (current ranks / N-session trail / recent alert events, cold-start-safe) + vrp_components() VRP-legs exposer + tests (SC-1, SC-5, SC-6)

**Wave 2** *(both depend on 27-01; disjoint files — parallel)*

- [ ] 27-02-PLAN.md — Distribution-board landing in app.py: METRIC_INVENTORY-driven board (rank marks + trail sparklines) + net-GEX chip + risk-bar removal + freshness dot + row-selection state (SC-1, SC-3, SC-5, SC-7)
- [ ] 27-04-PLAN.md — Event-shaped email in report.py/run_daily.py: alerts section (entries/escalations + Δ-vs-yesterday) + nothing-unusual fallback + boilerplate→single Methodology link + OI/key-levels cut + tests (SC-4, SC-6)

**Wave 3** *(depends on 27-01 + 27-02 — shares app.py with the board)*

- [ ] 27-03-PLAN.md — Per-row evidence panels in app.py: rank-history chart with rank-space bands + mechanism-view dispatch (smile overlay / reused diff surface / IV-vs-RV pair / term-ratio history) (SC-2, SC-5, SC-6)

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
<!-- LINKS:END -->
