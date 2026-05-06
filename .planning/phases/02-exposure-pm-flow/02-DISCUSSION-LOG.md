# Phase 2: Exposure + PM Flow - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-05
**Phase:** 02-exposure-pm-flow
**Areas discussed:** vs-yesterday label logic, summarise() architecture, Parquet schema additions, Email table format

---

## vs-yesterday label logic

| Option | Description | Selected |
|--------|-------------|----------|
| Direction of change only | INTENSIFIED if \|gex_today\| > \|gex_yesterday\|, EASED if smaller, UNCHANGED if within ±threshold | ✓ |
| Magnitude + relative threshold | Same but with explicit 20% cutoffs | |
| You decide | Claude picks threshold | |

**User's choice:** Direction of change only — with ±5% UNCHANGED band (tighter than suggested ±10%)

**Follow-up — UNCHANGED band:**

| Option | Description | Selected |
|--------|-------------|----------|
| ±10% | Filters daily noise, recommended | |
| ±5% | Tighter, more sensitive | ✓ |
| ±20% | Loose, UNCHANGED more often | |

**Notes:** User chose ±5% explicitly — more sensitivity to regime shifts desired.

---

## summarise() architecture

| Option | Description | Selected |
|--------|-------------|----------|
| Pass pre-aggregated scalars | Caller computes net_vex, net_chex and passes as optional kwargs | ✓ |
| Pass strike-vex/chex DataFrames | More symmetric with current design, 2 new params | |
| Separate function | compute_flow_analytics() — cleanest separation | |

**User's choice:** Pre-aggregated scalars via optional kwargs — keeps summarise() signature clean.

---

## Parquet schema additions

| Option | Description | Selected |
|--------|-------------|----------|
| vanna_exposure only | Matches EXP-04; charm is transient | ✓ |
| Both vanna_exposure and charm_exposure | Stores more for Phase 4 | |

**User's choice:** vanna_exposure only, as specified in EXP-04.

---

## Email table format

| Option | Description | Selected |
|--------|-------------|----------|
| New columns, compact format | Two new columns: Δ-flow ($X.XB/1%) and vs-Yesterday (label) | ✓ |
| Inline in regime column | vs-yesterday in parentheses after regime | |

**User's choice:** New columns, compact format. Table: Ticker \| Spot \| Net GEX \| Regime \| ZGL \| Δ-flow \| vs-Yesterday.

---

## Claude's Discretion

- HTML styling for new email columns
- `load_yesterday()` return type (dict vs Series)
- Error handling if parquet read fails during vs-yesterday lookup

## Deferred Ideas

None.
