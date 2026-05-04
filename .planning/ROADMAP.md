# Roadmap: Options Quant — v2.1 POC Delivery & Validation

> **Active milestone v2.1 (started 2026-05-04).** v2.0 engine build is closed and archived under `.planning/phases-archive/v2.0-engine/`. v1.0 HMM is closed and archived under `.planning/phases-archive/v1.0-hmm/`. Phase numbering restarts at 1.

## Overview

v2.1 takes the v2.0 engine (signals, sleeve backtest, decision dashboard, statistical rigor) and prepares it for evaluation by the quant team. Three deliverables, one phase to start; future phases are driven by team feedback.

## Phases

- [x] **Phase 1: POC Delivery & Calibration** — Bloomberg swap, notebook artifact, walkthrough doc, cleanup of forecasting drift. Context locked. **6 plans ready.**
- [ ] **Phase 2+:** Open — driven by quant-team feedback. May include extensions, scope adjustments, or a go/no-go on production-ize.

---

## Phase Details

### Phase 1: POC Delivery & Calibration
**Goal:** Hand a calibrated, quant-readable POC to the quant team for async review followed by a meeting. Notebook + Bloomberg-calibrated data + walkthrough doc.

**Depends on:** v2.0 engine (closed) — `local_data.py`, `data_layer.py`, `signals.py`, `backtest.py`, `dashboard.py`, `stats_rigor.py`, `sensitivity.py`, `run.py`, 74 tests.

**Locked decisions:** `.planning/phases/01-poc-delivery/01-CONTEXT.md` (16 decisions across 4 areas).

**Three deliverables:**
1. **Bloomberg calibration** — replace synthesized 90mny IV with `con.bdh('SPX Index', '30DAY_IMPVOL_90.0%MNY_DF', ...)`. Math layer untouched (identifier set is portable). Add `BloombergCon` class mirroring `FreeCon.bdh` interface; config switch selects which.
2. **Quant-readable notebook (`.ipynb`)** — top-of-page current-state strip, drill-down sections below (A → B → C → D-reframed → E → G → H), embedded charts with regime shading and consistent palette.
3. **Walkthrough doc (`WALKTHROUGH.md`)** — per-section: what it shows, how to read it, what it doesn't show / its limits, how it was built (sample size, statistical method).

**Cleanup:**
- Delete `validate.py` (forecasting drift)
- Reframe Section D — show realized environment after analog match, not realized sleeve P&L
- Keep Section C bucket means + Welch's t-test + Holm-Bonferroni (rigor is the point)

**Hard scope cap (explicitly OUT):** PDIV / fund specialization, Markov-switching/HMM, any new signals.

**Audience & cadence:** Quant team first, weekly Monday review, async handoff then meeting.

**Success criteria:**
1. Notebook compiles top-to-bottom on Bloomberg data; current-state-led layout; chart quality good enough that a quant-team reader gets the regime in 3 seconds.
2. Walkthrough doc covers every dashboard section with read-this-way / its-limits guidance, plus the open question for the team: *"Does the team already have a vol/regime/sleeve-context dashboard we shouldn't duplicate?"*
3. `validate.py` removed; Section D reframed; Section C + Holm rigor preserved verbatim.
4. POC handed to quant team async with the question: *"What would have to be true for this to inform a real decision?"*

**Plans:** 6 plans across 3 waves
- Wave 1 (parallel): 01-01 (BloombergCon class), 01-02 (remove validate.py)
- Wave 2: 01-03 (Section D reframe), 01-04 (notebook builder)
- Wave 3: 01-05 (chart styling), 01-06 (WALKTHROUGH.md)

---

## Progress

| Phase | Plans | Status | Completed |
|-------|-------|--------|-----------|
| 1. POC Delivery & Calibration | 5 plans (01-01 dropped) | In progress — 01-02 done | 01-02 (2026-05-04) |

---

## Closed milestones

### v2.0 — Sleeve Allocation Framework: Engine Build
Closed 2026-05-04. Engine functionally complete on free CBOE+FRED data with statistical rigor (Holm correction, block bootstrap, 74 tests). Mode shift from build → deliver/learn warranted milestone boundary. Phases archived under `.planning/phases-archive/v2.0-engine/`. Original Phase 6 ("Validation Gates") re-scoped and lifted to v2.1 Phase 1.

### v1.0 — Regime-Aware Fund Intelligence Notebook (HMM)
Closed 2026-04-30 without ship. Pivoted to v2.0. `hmm.ipynb` preserved as legacy single-fund diagnostic. Phases archived under `.planning/phases-archive/v1.0-hmm/`. See `.planning/MILESTONES.md` for closure rationale.
