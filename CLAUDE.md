# CLAUDE — TQ Sleeve Allocation Framework (formerly TQ HMM)
Last updated: 2026-04-30 | Status: active milestone v2.0 (pivoted from v1.0 HMM on 2026-04-30); Phase 7 next

## Repo Card

- **Open:** Cron2 Jupyter Notebook Server only — cannot run locally
- **Entry point:** `hmm.ipynb`
- **Runtime:** server-side (no local venv, no `requirements.txt` — server provides the stack)
- **Stack:** pandas, numpy, hmmlearn, matplotlib, seaborn, scipy, statsmodels
- **Data:** internal company database (connection config TBD — see notebook Setup cell)
- **Workflow:** GSD (`.planning/`)

## What It Does

**v2.0 (current):** A regime-aware options-overlay sleeve scorecard for Purpose. Builds an engine (Phase α) that recommends sleeve attractiveness — covered call, cash-covered put, collar, short straddle — across SPX/QQQ (and optionally XIU/XSP), driven by a transparent percentile-rank scorecard on VRP / skew / term / trend / drawdown signals + sleeve P&L backtests. Specializes for PDIV (Phase β). Optional Markov-switching fragility flag (Phase γ).

Core value: given a vol/skew/trend/drawdown panorama on a small set of liquid underlyings, output a PM-readable scorecard of which option-overlay sleeves are attractive right now, why, and what historical sleeve P&L looked like in similar past environments.

**v1.0 (legacy):** Single-fund regime diagnostic in `hmm.ipynb` — preserved untouched. See `.planning/MILESTONES.md` for pivot rationale.

## Constraints

- **Jupyter only:** v2.0 work in `sleeve_alpha.ipynb` (new); `hmm.ipynb` preserved as v1.0 legacy. No CLI entry points.
- **Locked Python env:** no pip install. Available: pandas 1.5.2, numpy 1.23.5, scipy 1.13.0, scikit-learn 1.1.1, statsmodels 0.14.2, matplotlib 3.9.0, ffn 0.4.19, TA-Lib 0.4.29, pandas_market_calendars, exchange_calendars, numba. **No `hmmlearn`. No `arch`.**
- **Interpretability first:** scorecard primary, weights printed, no hidden coefficients. HMM optional (Phase γ via `statsmodels.MarkovRegression`).
- **PM-readable output:** dashboard table + auto-commentary. Output must be presentable without verbal explanation.
- **Strategy menu:** covered call, cash-covered put, collar, short straddle. Dispersion explicitly out of scope.
- **Internal data:** Django ORM (fund NAVs) + `emds_client` `con.bdh` (Bloomberg-flavored fields, NOT raw Bloomberg).
- **No predictive claims:** descriptive of current environment + historical analog only.
- **Windows paths:** use pathlib or os.path.join throughout.

## Key Files

| File | Purpose |
|------|---------|
| `sleeve_alpha.ipynb` | **v2.0 primary deliverable** — sleeve scorecard, signals, backtests, PM output |
| `hmm.ipynb` | v1.0 legacy diagnostic — DO NOT MODIFY |
| `Data.ipynb` | Reference for ORM/Bloomberg/emds_client syntax |
| `NOTES-from-regime-detection.md` | HMM lessons; applicable to optional Phase γ |
| `_audits/` | Audit reports (sleeve-pivot 2026-04-30) |
| `data/` | Local data exports (gitignored if sensitive) |

## Notebook Sections (v2.0 — `sleeve_alpha.ipynb`)

0. Setup & Config (universe, sleeves, dates, palette)
1. Data Layer (prices, IV panels, skew panels, VIX, risk-free) — Phase 7
2. Signal Engineering (RV, VRP, skew, term, trend, drawdown, fragility composite) — Phase 8
3. Sleeve Backtest Engine (BS pricing + monthly-roll P&L for CC, CSP, Collar, Short Straddle) — Phase 9
4. Sleeve Scorecard (transparent linear rules, normalized weights) — Phase 10
5. PM-Grade Output (dashboard table + auto-commentary + small-multiples) — Phase 11
6. Validation Gates (causality, sleeve-sign, turnover, tail-risk, robustness, trust verdict) — Phase 12
7. PDIV Specialization (Phase β) — Phase 13
8. Optional: Markov-Switching Fragility Flag (Phase γ) — Phase 14

## Conventions

- Notebook cells are the unit of work — keep cells short and focused
- No inline comments unless the statistical reasoning is non-obvious
- Chart style: consistent palette, regime shading on all time-series plots
- All statistics reported with regime label, sample size (n), and date range
- Regime labels are human-assigned after reviewing model output (not auto-named)

## Workflow

Use GSD commands for all phase work:
- `/gsd-quick` for small fixes or single-cell additions
- `/gsd-execute-phase` for planned phase work
- `/gsd-debug` for investigation

Do not make notebook edits outside GSD unless user explicitly bypasses.

## Do Not Touch

- `hmm.ipynb` — v1.0 legacy artifact, preserved untouched
- `.planning/phases/01-data-layer/`, `02-regime-model/`, `03-fund-analysis/` — v1.0 phase planning, archived in place
- `data/` folder contents (source exports)
- `.planning/` docs (GSD-managed)

---

**Hub:** [[tq-hmm/tq-hmm|TQ HMM]] · **Planning:** [[.planning/planning|.planning/]]
