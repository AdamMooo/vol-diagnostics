# Options Quant — Sleeve Allocation Framework (formerly tq-hmm)

## What This Is

A research notebook that recommends, on a regular cadence, which options-overlay sleeves (covered call, cash-covered put, collar, short-strangle) are attractive in the current market environment. Universe: SPX and NDX index level (POC) — extends to ETFs/Canadian once on Bloomberg. **Market-general scorecard, no fund-specific specialization** — pivoted away from PDIV (Phase β) on 2026-05-04 to keep scope tight and broadly useful for the quant team.

The original v1.0 HMM-only fund-intelligence notebook (`hmm.ipynb`) is preserved as a legacy single-fund diagnostic. The HMM/Markov-switching layer is demoted to an optional "fragility flag" appendix in v2.0 — not the spine.

## Core Value

Given a vol/skew/trend/drawdown panorama on a few liquid underlyings, output a PM-readable scorecard of which option-overlay sleeves are attractive right now, why (which signals are loaded), and what the historical sleeve P&L looked like in similar past environments. Bridges the gap between "intellectually interesting regime model" and "decision a PM can act on tomorrow."

## Current Milestone: v2.1 — POC Delivery & Validation

> v1.0 (HMM) closed/archived. **v2.0 (Sleeve Allocation Framework — Engine Build) closed 2026-05-04** — local POC complete, archived under `.planning/phases-archive/v2.0-engine/`. v2.1 is the only active milestone.

**Goal:** Deliver the v2.0 engine to the quant team for evaluation. Calibrate against Bloomberg (replace synthetic 90mny IV), package as a Jupyter notebook with quality charts, write a walkthrough doc, and surface the question *"What would have to be true for this to inform a real decision?"*

**Audience:** Quant team first. Weekly Monday review cadence. Async handoff (notebook + walkthrough doc) followed by a focused meeting.

**Phase 1 — POC Delivery & Calibration (active):** Bloomberg swap + notebook artifact + walkthrough doc + cleanup. Locked decisions in `.planning/phases/01-poc-delivery/01-CONTEXT.md`.

**Future phases (open):** driven by team feedback. May include extensions, scope changes, or a go/no-go decision after the team reviews. Not pre-defined.

**Hard scope cap (locked):** No PDIV / fund specialization. No Markov-switching/HMM. No new signals beyond the six + fragility composite already shipped in v2.0.

**Insight framing (locked from v2.0):**
- **Market-general** — applicable to the quant team's broader trading view, not fund-specific
- **State + exposure + history**, never prescriptive — no scoring, no buy-this recommendations
- **Statistical rigor over predictive claims** — Holm correction, block bootstrap, honest reporting of negative results

**Local engine assets (from v2.0, untouched):**
- `local_data.py`, `data_layer.py`, `signals.py`, `backtest.py`, `dashboard.py`, `stats_rigor.py`, `sensitivity.py`, `run.py`
- 74 tests (math + pipeline + property-based)
- Math layer is portable to Cron2/Bloomberg verbatim — only the data dispatch in `local_data.py` changes

## Constraints

- **Format**: Jupyter Notebook only. New work in `sleeve_alpha.ipynb`. `hmm.ipynb` preserved untouched.
- **Runtime**: Cron2 Jupyter server only. Cannot run locally.
- **Locked Python env**: no `pip install`. Must work with installed: pandas 1.5.2, numpy 1.23.5, scipy 1.13.0, scikit-learn 1.1.1, statsmodels 0.14.2, matplotlib 3.9.0, seaborn 0.8.1, ffn 0.4.19, TA-Lib 0.4.29, pandas_market_calendars, exchange_calendars, numba. **No `hmmlearn`. No `arch`.**
- **Data**: internal Django ORM (fund NAVs) + `emds_client` `con.bdh` (Bloomberg-flavored fields, **not** raw Bloomberg — field naming convention differs). Confirmed working fields: `30DAY_IMPVOL_100.0%MNY_DF`, `30DAY_IMPVOL_90.0%MNY_DF`, `PX_LAST` on VIX/SPX/etc.
- **Audience**: PM-readable. Output must be presentable without verbal explanation, including auto-commentary block.
- **No predictive claims**: all output framed as descriptive of current environment + historical analog, not as forecasts.
- **Strategy menu**: covered call, cash-covered put, collar, short-strangle. Dispersion explicitly out of scope (dealer/HF turf, capacity-limited, governance-unfriendly for retail AM).
- **Windows paths**: pathlib or os.path.join.

## Key Files

| File | Purpose |
|------|---------|
| `sleeve_alpha.ipynb` | NEW — primary deliverable for Phase α/β |
| `hmm.ipynb` | LEGACY — v1.0 single-fund diagnostic, preserved as-is |
| `Data.ipynb` | Reference for ORM/Bloomberg/emds_client syntax |
| `NOTES-from-regime-detection.md` | HMM lessons; applicable to optional Phase γ fragility flag |
| `_audits/` | Audit reports (e.g., the 2026-04-30 sleeve-pivot audit) |
| `data/` | Local data exports — sensitive, gitignored |

## Conventions

- Notebook cells are the unit of work — section-headered, short, focused
- All signals percentile-ranked on expanding window (default 252d) for PM readability
- Sleeve scores in [-1, +1]; sleeve weights normalized within an overlay budget
- Every output table includes n, date range, and any signal capping flags
- Reproducibility: `random_state=42` everywhere; results saved as parquet snapshots per refresh date

## Workflow

GSD-managed. Major commands:
- `/gsd-discuss-phase [N]` then `/gsd-plan-phase [N]` for new phase work
- `/gsd-quick` for one-cell additions
- `/gsd-debug` for investigation

Do not edit `hmm.ipynb`. Do not modify Phase 1-3 planning artifacts in `.planning/phases/0[1-3]-*`.

## Strategic Decisions

| Date | Decision | Why |
|------|----------|-----|
| 2026-04-22 | (v1.0) 2-state Gaussian HMM on benchmark, fund-conditional analysis | Original framing — interpretable single-fund diagnostic |
| 2026-04-30 | (v1.0 → v2.0 pivot) Drop HMM as spine; build sleeve allocation framework | Stated goal is options sleeve allocation; HMM-only design cannot inform sleeve choice without options-pricing data |
| 2026-04-30 | (v2.0) Scorecard primary, HMM/MarkovRegression optional fragility flag | Scorecard is PM-auditable, robust to data limits, governance-friendly. HMM is a "cool plus" not a load-bearing tool |
| 2026-04-30 | (v2.0) Strategy menu = CC + CSP + Collar + ShortStrangle. Drop dispersion | Dispersion is dealer/HF turf, capacity-limited, governance-unfriendly for retail AM |
| 2026-04-30 | (v2.0) Confirm IV data via `emds_client` is buildable | `30DAY_IMPVOL_100.0%MNY_DF` + `30DAY_IMPVOL_90.0%MNY_DF` work — VRP and skew are computable |
| 2026-04-30 | (v2.0) Engine first (Phase α — SPX/QQQ generic), then specialize (Phase β — PDIV) | β is ~1 cell-block on top of α once PDIV's rule is known. α generates the artifacts every other audience needs |
| 2026-04-30 | (v2.0) Use `statsmodels.tsa.regime_switching.MarkovRegression` if HMM ever needed | `hmmlearn` not in locked env; statsmodels gives proper sticky Markov-switching mean/variance |

## Out of Scope

| Feature | Reason |
|---------|--------|
| Dispersion / implied-correlation sleeve | Dealer/HF turf, capacity-limited, governance-unfriendly for retail AM, distribution mismatch |
| Real-time / intraday refresh | Notebook is research/decision-support, weekly cadence sufficient |
| External data subscriptions beyond `emds_client` | Locked environment; license risk |
| `hmm.ipynb` modification | Preserved as legacy v1.0 diagnostic |
| Single-name option strategies | Dispersion-adjacent, capacity-limited |
| Predictive / forecasting language | Framework is descriptive of current environment + historical analog |
| Live execution / order routing | Research notebook only |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition:**
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Mark in REQUIREMENTS.md with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Strategic Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone:**
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-30 — milestone v2.0 started after sleeve-pivot audit*
