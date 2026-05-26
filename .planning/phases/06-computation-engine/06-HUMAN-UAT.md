---
status: partial
phase: 06-computation-engine
source: [06-VERIFICATION.md]
started: 2026-05-26T00:00:00Z
updated: 2026-05-26T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Dashboard VRP Display
expected: IV30 ~18%, RV20 ~15–16%, VRP ~2–3 vol points (not ~17–18). Run `streamlit run streamlit_app.py`, load a ticker with at least 20 days of parquet history, check the Carry / VRP section.
result: [pending]

### 2. Vol Surface Visual
expected: Clean 3D surface with Viridis colorscale; no colored meridian lines for gamma-flip, call wall, put wall; no translucent spot plane.
result: [pending]

### 3. Regime Card Layout
expected: Cards show exactly Spot, Net GEX, gamma-flip, Skew 25d, IV30. No "Hedge Sh / $1" row. Observations show Range and today% only.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/06-computation-engine/06-01-PLAN|06-01-PLAN]]
- [[_planning/gamma-omm/phases/06-computation-engine/06-01-SUMMARY|06-01-SUMMARY]]
- [[_planning/gamma-omm/phases/06-computation-engine/06-02-PLAN|06-02-PLAN]]
- [[_planning/gamma-omm/phases/06-computation-engine/06-02-SUMMARY|06-02-SUMMARY]]
- [[_planning/gamma-omm/phases/06-computation-engine/06-03-PLAN|06-03-PLAN]]
- [[_planning/gamma-omm/phases/06-computation-engine/06-03-SUMMARY|06-03-SUMMARY]]
- [[_planning/gamma-omm/phases/06-computation-engine/06-04-PLAN|06-04-PLAN]]
- [[_planning/gamma-omm/phases/06-computation-engine/06-04-SUMMARY|06-04-SUMMARY]]
- [[_planning/gamma-omm/phases/06-computation-engine/06-CONTEXT|06-CONTEXT]]
- [[_planning/gamma-omm/phases/06-computation-engine/06-PATTERNS|06-PATTERNS]]
- [[_planning/gamma-omm/phases/06-computation-engine/06-RESEARCH|06-RESEARCH]]
- [[_planning/gamma-omm/phases/06-computation-engine/06-REVIEW|06-REVIEW]]
- [[_planning/gamma-omm/phases/06-computation-engine/06-VERIFICATION|06-VERIFICATION]]

<!-- LINKS:END -->
