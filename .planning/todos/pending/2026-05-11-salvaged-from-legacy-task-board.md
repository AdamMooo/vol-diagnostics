---
created: 2026-05-11T21:51:28Z
title: Salvaged todos from legacy task board
area: planning
files:
  - _archive/tasks-pre-live-planning-mirror/Gamma-OMM-Tasks.md
---

## Problem

The pre-live-planning task board at `C:\dev\tasks\Gamma-OMM-Tasks.md` was archived on 2026-05-11 (now redundant — planning docs are visible directly in Obsidian via `_planning/` hard-link mirror). These items were unresolved at archive time and may still need action. The board referenced v2.1 (Bayesian reframe / sleeve report) work that predates the current v3.1 (GEX dashboard) milestone — many items below may now be obsolete.

## Solution

Review each item against the current v3.1 STATE; promote to a phase or close as obsolete.

## Items

- [ ] NDX skew identity bug — NDX/SPX currently share `sigs.pct["skew"]` (same series). NDX should use VXN-based term structure or CBOE NDX SKEW if available. (Was tagged "fix before sending to team" under v2.1.)
- [ ] NDX iv90_atm synthesis — uses SPX term-structure ratio to scale. Same data-accuracy category as the skew bug.
- [ ] Send async to quant team — `out/sleeve_report_YYYYMMDD.html` + `WALKTHROUGH.md`. (Possibly obsolete now that v3.1 GEX dashboard supersedes the sleeve report — verify before sending.)
- [ ] **Backlog — Bloomberg calibration:** replace synthesized `iv30_90mny` with `con.bdh('SPX Index', '30DAY_IMPVOL_90.0%MNY_DF', ...)`. One-class swap in `local_data.py`. Gate: team greenlights POC.
- [ ] **Backlog — GEX/dealer gamma signal:** Bloomberg field probe needed. `SPX Index` + `OPEN_INT`, `OPEN_INT_TOTAL_CALL/PUT`, `PUT_CALL_RATIO`; also `PCUSEQTR Index PX_LAST`. (Probably handled by current v3.1 milestone — verify.)
- [ ] **Backlog — CFTC COT positioning:** `IMM0COMM Index`, `IMM0NCOM Index`, `IMM0SPEC Index` for weekly speculator/commercial net.
- [ ] **Backlog — walk-forward OOS validation:** regime-conditioned walk-forward for signal↔return stability.
- [ ] **Backlog — automated weekly schedule:** manual for POC; revisit if team adopts weekly cadence.

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
