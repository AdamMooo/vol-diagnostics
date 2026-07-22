# Phase 23: Data Completeness, Backup & Model-Readiness Audit - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-21
**Phase:** 23-data-completeness-backup-model-readiness (merged from old Phases 23/24/25 mid-session)
**Areas discussed:** Where gaps get surfaced; backup destination; model-ready spec location

---

## Initial area selection

Presented 4 candidate gray areas: (1) extend `health_check.py` vs. new tool, (2) gap definition — tail vs. full history, (3) where gaps get surfaced, (4) vol_index gap semantics. User selected only "Where gaps get surfaced" and added the free-text note "idk really."

## Where gaps get surfaced

| Option | Description | Selected |
|--------|-------------|----------|
| GH Actions only | Extend the existing daily `--strict` gate; already fails loudly/privately | ✓ |
| Add a dashboard panel, hidden/admin-only | Panel exists but gated so casual visitors don't see it | |
| Add a public dashboard panel | Gap status visible to any visitor as a trust signal | |
| You decide | — | |

**User's choice:** "GH Actions only (Recommended)"
**Notes:** Framed as a recommendation given the dashboard is now public post password-gate-removal — a visible "our scraper missed a day" panel would broadcast internal pipeline health. User agreed with the recommendation without pushback.

---

## Remaining areas (extend vs. new tool, tail vs. full-history gap definition, vol_index semantics)

Asked whether to dig into these individually or defer to Claude's judgment. User selected "Use your judgment (Recommended)."

**Notes:** Resolved via codebase scouting rather than further questions — `engine/health_check.py` already exists, is wired into `.github/workflows/daily-report.yml`'s `--strict` gate, and already covers 2 of the 4 required series but only at the tail (freshness), not full-history. See CONTEXT.md D-02 through D-05 for the resulting decisions and rationale.

## Claude's Discretion

- Extend `engine/health_check.py` rather than build a separate gap-audit script (D-02).
- Extend coverage to all 4 series: `gex_snapshots`, `surface_history`, `vol_index`, `oi_history` (D-03).
- Add full-history gap scanning alongside the existing tail-freshness check (D-04).
- vol_index missing-session semantics — distinguish "CBOE didn't publish" from "our fetch failed," pending verification against `engine/data/vol_index.py` (D-05, explicitly flagged as a starting assumption for the researcher/planner to confirm, not final).
- Exact report format (CLI table / JSON / both) and whether full-history scan runs on every `--strict` invocation vs. a separate command — left open for planning.

## Roadmap restructure (mid-session)

After the gap-monitoring discussion above, Adam asked to understand the shape of the full v5.0 roadmap, then decided to merge old Phases 23 (Data Completeness & Gap Monitoring), 24 (Backup & Restore), and 25 (Model-Ready Data Definition & Depth Audit) into one combined phase. `.planning/ROADMAP.md` was edited directly (the `gsd-sdk query phase.remove` CLI command errored — "Phase 25 not found" — against a phase with no directory yet; rather than debug the bundled CLI further, the removal/renumber/merge was done by hand: old 24 and 25 deleted, old 26→24, old 27→25, and the new merged Phase 23 given all 12 success criteria and 6 requirements). This phase directory was renamed from `23-data-completeness-gap-monitoring` to `23-data-completeness-backup-model-readiness` to match.

## Backup destination

| Option | Description | Selected |
|--------|-------------|----------|
| Oracle Object Storage | Same Oracle account as the VM, Always Free 10GB tier, independent of VM loss | ✓ |
| Private GitHub location (Release asset / separate repo) | Free, but awkward fit for daily-overwrite binary parquet | |
| You decide | — | |

**User's choice:** "Oracle Object Storage (Recommended)"
**Notes:** Matches the project's established pattern of free-tier, no-new-API-key infra (CBOE/FRED/yfinance, and now the existing Oracle account). See CONTEXT.md D-06.

## Model-ready spec location

| Option | Description | Selected |
|--------|-------------|----------|
| New standalone doc linked from PROJECT.md | Keeps PROJECT.md body from growing further; satisfies the "discoverable from PROJECT.md/STATE.md" success criterion via a link | ✓ |
| Directly in PROJECT.md | More visible but PROJECT.md is already large | |
| You decide | — | |

**User's choice:** "New standalone doc, linked from PROJECT.md (Recommended)"
**Notes:** See CONTEXT.md D-09. The actual depth-target numbers (D-10) were explicitly NOT decided here — flagged as a quant/methodology question for research/planning to ground in stated rationale, consistent with Adam's Learning Mode preference for quant work.

## Deferred Ideas

None raised outside phase scope. One todo (`2026-05-11-v3-2-pre-distribution-hardening.md`) surfaced via low-relevance keyword match during todo cross-reference but was not folded — it's dead-code cleanup earmarked for what is now Phase 24 (formerly Phase 26, before the merge renumbered it).

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
**Phase siblings:**
- [[_planning/vol-diagnostics/phases/23-data-completeness-backup-model-readiness/23-CONTEXT|23-CONTEXT]]

<!-- LINKS:END -->
