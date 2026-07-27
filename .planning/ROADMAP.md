# Roadmap: (no active milestone)

**As of 2026-07-27.** Last shipped: v5.0 (see `.planning/MILESTONES.md`).

## v6.0 covered-call tilt-timing — INVESTIGATED & SHELVED 2026-07-27

Opened and dropped the same day, before any build, on evidence. Pre-build tests (SPY, 2016–2026) showed no edge for *timing* a USCC↔VFV tilt on VRP richness:
- forward-return rich-vs-cheap: non-overlapping Welch **p=0.74** (noise)
- forward realized-vol diff: **p=0.074** (marginal, ~35 independent windows, in-sample, before multiple-testing correction or costs)

A *static* covered-call sleeve already harvests VRP structurally; timing it adds nothing demonstrable. Detail: `research/covered-call-spike-findings.md`, memory `v6-covered-call-model-decision`.

The phases that were sketched (proxy data layer / persistence engine / validated backtest / weekly PDF review) are **not being built.**

## Open (not a milestone)
- **OCI restore drill (BACKUP-02)** — verify `restore_from_oci` recovers `out/` (backup live since 2026-07-23).

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
<!-- LINKS:END -->
