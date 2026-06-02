# Phase 14: Accumulation Gating - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-01
**Phase:** 14-accumulation-gating
**Areas discussed:** Threshold N per element, Caption text and gate posture, Email GATE-02 scope

---

## Threshold N per element

| Option | Description | Selected |
|--------|-------------|----------|
| 5 sessions | Matches existing VRP/skew percentile floor. One week of trading days. | ✓ |
| 10 sessions | Two full trading weeks. More history = less noise on evolution panels. | |
| You decide | Claude picks 5 for consistency with existing floors. | |

**User's choice:** 5 sessions for evolution small-multiples.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, 5 everywhere | One consistent number across all guards. | ✓ |
| No — use element-specific N | E.g. 42-session chart needs 10+, sparkline at 5. | |
| You decide | Claude uses 5 everywhere for simplicity. | |

**User's choice:** Universal N=5 for all remaining guarded elements (VRP sparkline, 42-session chart, VRP/skew percentile captions).

---

## Caption text and gate posture

| Option | Description | Selected |
|--------|-------------|----------|
| Hide entirely, show caption only | Don't render chart at all; single st.caption() in its place. | ✓ |
| Show placeholder, caption below | Render minimal empty frame with caption underneath. | |

**User's choice:** Hide entirely, show caption only.

---

| Option | Description | Selected |
|--------|-------------|----------|
| "Needs ≥5 sessions — accumulates from run_daily" | Explicit count + how to fix it. | ✓ |
| "Insufficient history (≥5 sessions required)" | More formal, reads like an error message. | |
| You decide | Claude uses option 1. | |

**User's choice:** `"Needs ≥5 sessions — accumulates from run_daily runs forward."`

---

## Email GATE-02 scope

| Option | Description | Selected |
|--------|-------------|----------|
| Hardening only — no actual failures seen | Evolution section and ΔIV PNGs already handle cold-start. GATE-02 = tests + regression lock. | ✓ |
| There's a specific failure path to close | Something in the email actually errors on cold start. | |

**User's choice:** Hardening only.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Just add tests — verify None propagation is solid | No new guard logic; existing paths are correct. Tests lock them. | ✓ |
| Add explicit guards + tests | Defensive session-count checks in run_daily.py in addition to tests. | |

**User's choice:** Tests only. No new guard logic in run_daily.py or report.py.

---

## Claude's Discretion

None — all decisions made explicitly by user.

## Deferred Ideas

None — discussion stayed within phase scope.

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/14-accumulation-gating/14-CONTEXT|14-CONTEXT]]

<!-- LINKS:END -->
