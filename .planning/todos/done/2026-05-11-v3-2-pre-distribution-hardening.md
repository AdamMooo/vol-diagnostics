---
created: 2026-05-11T22:30:00Z
title: v3.2 — Pre-Distribution Hardening (audit follow-ups)
area: gamma-omm
status: resolved
resolved: 2026-07-26
resolved_by: Phase 24 (24-02) close-out — backlog 999.3
files:
  - _audits/methodology-review-2026-05-11.md
  - .planning/ROADMAP.md
---

## Resolution (2026-07-26, Phase 24 / backlog 999.3)

Closed as part of the Phase 24 codebase-cleanup pass. Three of four items shipped
out-of-phase (verified in current source); the fourth is formally deferred. No
feature work was re-run in Phase 24 — this is a disposition-only close-out.

| Item | Disposition | Evidence |
|------|-------------|----------|
| (a) Snapshot timestamp in email header | **SHIPPED** | `engine/report/report.py:291-303` renders "Snapshot {ts} ET · OI T-1 · Greeks 15-min delayed"; `snapshot.as_of` threaded through `engine/compute.py:190`. |
| (b) Methodology caveat banner above cards | **SHIPPED** | `engine/report/report.py:307` `_methodology_caveat_banner()`, rendered below header (`report.py:539,570`). |
| (c) Gamma-profile slope steepness / "Regime sharpness" row | **DEFERRED** | Not implemented — no `sharpness`/slope-steepness field anywhere in `engine/`. Counter to current product direction (GEX demoted to a model construct, "no new signals" locked per CLAUDE.md); a new GEX-derived signal would need statistical validation first. |
| (d) Filter-drop transparency | **SHIPPED** | `engine/report/report.py:496` "Filters removed {…} of raw chain OI"; `min_oi`/`max_iv` drop at `engine/data/data_loader.py:111`. |

## Problem

Audit on 2026-05-11 identified two remaining ship-blockers and two
high-value presentation gaps before the GEX daily email can be shared
beyond Adam's own inbox. Scoped as v3.2 Phase 8 in ROADMAP; not yet
planned.

## Solution

Run `/gsd-discuss-phase 8` then `/gsd-plan-phase 8` then `/gsd-execute-phase 8`.
All four items below should ship in one PR.

## Items

### Ship-blockers

- [ ] **Snapshot timestamp in email header.** Thread `ChainSnapshot.as_of`
      through `compute_ticker` -> summary -> `report.build_email()`. Display
      as `Snapshot 2026-05-11 16:15 ET . OI T-1 . Greeks 15-min delayed`
      under the date in the section header.
- [ ] **Methodology caveat banner above cards.** Move the "absolute GEX
      magnitude is methodology-specific" line from the 10px footer to a
      plain-text banner immediately below the date header. Keep the full
      legend in the footer.

### High-value presentation gaps

- [ ] **Gamma profile slope steepness.** Quantify how sharp the regime is
      (e.g. max |dnetGEX/dspot| around current spot, or peak-to-30%-of-peak
      width). Add as new summary field + email row "Regime sharpness".
- [ ] **Filter-drop transparency.** Log `min_oi`/`max_iv` filter drop ratio
      in `data_loader.load_chain`. Surface in email footer line: "Filters
      removed X% of raw chain OI."

## Deferred (footnotes acceptable, separate phases)

- FRED-sourced risk-free rate (carryover P0 from 2026-05-07 audit)
- Per-ticker dividend yield q (carryover P1)
- GEX percentile vs own history (blocked on N>=30 snapshots; ~late June 2026)
- event_study() empirical results (same blocker)

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
<!-- LINKS:END -->
