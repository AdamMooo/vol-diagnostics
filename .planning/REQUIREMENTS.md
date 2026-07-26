# Requirements: Options Quant — GEX Analysis Platform (v5.0 Data Foundation)

**Defined:** 2026-07-17
**Core Value:** How expensive is protection, where on the surface is that expensiveness concentrated, how is the surface moving over time, and what does it imply for portfolio overlays or option-writing sleeves?

## v1 Requirements

Requirements for the v5.0 Data Foundation milestone — hardening data collection and retention *before* building the eventual options-writing/pricing model. Each maps to roadmap phases.

### Data Completeness & Gap Monitoring (DATA)

- [x] **DATA-01**: A report/script identifies missing-session gaps per data series (`gex_snapshots`, `surface_history`, `vol_index`, `oi_history`) per ticker
- [x] **DATA-02**: Gap findings are surfaced somewhere visible (health-check output or a dashboard panel), not just sitting silently in parquet

### Retention & Backup (BACKUP)

- [ ] **BACKUP-01**: `out/` parquet stores are backed up somewhere other than the single Oracle VM
- [ ] **BACKUP-02**: A documented/automated restore path exists — not just a backup existing, but a way to rebuild if the Oracle instance is lost

### Model-Ready Data Definition (SCHEMA)

- [ ] **SCHEMA-01**: A written spec defines, per data series, the minimum depth (sessions) and schema needed before a predictive/prescriptive model could be built on it
- [ ] **SCHEMA-02**: Current actual depth per series is measured against those targets

### Codebase Organization & Dead Code (CLEAN)

- [x] **CLEAN-01**: Dead code, unused imports/functions, and stale references are removed across `engine/` (folds in the stale `260514-fz2-dead-code-stale-ref-sweep` quick-task and backlog item 999.3 Pre-Distribution)
- [x] **CLEAN-02**: Module/package organization is reviewed for consistency; CLAUDE.md orientation docs stay in sync with the actual structure

### Existing Computation Rigor (RIGOR)

- [ ] **RIGOR-01**: Existing statistical/quant computations (VRP, RV20, vol surface fit, skew/term structure) are reviewed for correctness against their documented methodology, with edge cases (thin data, cold-start, missing strikes) checked
- [ ] **RIGOR-02**: Test coverage is expanded for these computations' edge cases, not just the happy path

## v2 Requirements

Deferred beyond v5.0 — the options-writing/pricing model itself, and anything that depends on it.

### Modeling (out of v5.0, future milestone)

- **MODEL-01**: A first predictive/prescriptive options-writing or pricing model
- **MODEL-02**: Backtesting framework for that model

## Out of Scope

| Feature | Reason |
|---------|--------|
| The options-writing/pricing model itself | Explicit v5.0 scope boundary — data robustness first, per user's own sequencing |
| Bloomberg data swap | Still a one-class change deferred from v4.x; not blocking data-foundation work |
| New dashboard-facing signals | Locked per CLAUDE.md — no new signals without statistical validation, unrelated to this milestone's infra focus |
| New predictive/prescriptive model work | RIGOR-01/02 harden the EXISTING descriptive computations (VRP/RV20/surface/skew) — not a new model; the future model is still deferred per MODEL-01/02 above |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 23 (23-01) | Done |
| DATA-02 | Phase 23 (23-01) | Done |
| BACKUP-01 | Phase 24 | Pending |
| BACKUP-02 | Phase 24 | Pending |
| SCHEMA-01 | Phase 25 | Pending |
| SCHEMA-02 | Phase 25 | Pending |
| CLEAN-01 | Phase 24 | Complete |
| CLEAN-02 | Phase 24 | Complete |
| RIGOR-01 | Phase 27 | Pending |
| RIGOR-02 | Phase 27 | Pending |

**Coverage:**
- v1 requirements: 10 total
- Mapped to phases: 10
- Unmapped: 0 ✓

---
*Requirements defined: 2026-07-17*
*Last updated: 2026-07-17 after v5.0 roadmap extension (Phases 26–27 added for CLEAN/RIGOR requirements)*

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
<!-- LINKS:END -->
