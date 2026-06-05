---
plan: 01-01
phase: 01-greeks-engine
status: complete
completed: 2026-05-05
commit: a7526b2
---

# Summary: 01-01 — Add bs_vanna, bs_charm, T_MIN

## What Was Built

Added `bs_vanna()` and `bs_charm()` to `gex/greeks_engine.py` following the existing `bs_gamma()` pattern. Added `T_MIN = 1.0 / 365.0` as a module-level constant. Extended `add_greeks()` to compute vanna and charm columns on every chain DataFrame.

## Key Files

- `gex/greeks_engine.py` — bs_vanna(), bs_charm(), T_MIN added; add_greeks() extended

## Verification

- `bs_vanna(100, 100, 0.20, 0.25)` → 0.147330 (finite, positive ATM)
- `bs_charm(100, 100, 0.20, 0.25)` → -0.137508 (finite)
- `bs_charm(100, 100, 0.20, 0.0001)` → 0.0 (0DTE guard confirmed)
- `add_greeks()` returns DataFrame with gamma, vanna, charm columns — all finite

## Self-Check: PASSED

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/01-greeks-engine/01-01-PLAN|01-01-PLAN]]
- [[_planning/gamma-omm/phases/01-greeks-engine/01-02-PLAN|01-02-PLAN]]
- [[_planning/gamma-omm/phases/01-greeks-engine/01-02-SUMMARY|01-02-SUMMARY]]
- [[_planning/gamma-omm/phases/01-greeks-engine/01-RESEARCH|01-RESEARCH]]
- [[_planning/gamma-omm/phases/01-greeks-engine/01-VERIFICATION|01-VERIFICATION]]

<!-- LINKS:END -->
