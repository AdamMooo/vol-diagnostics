# CLAUDE — TQ HMM
Last updated: 2026-04-22 | Status: active (Phases 1–2 complete, Phase 3 cells written, untested)

## Repo Card

- **Open:** Cron2 Jupyter Notebook Server only — cannot run locally
- **Entry point:** `hmm.ipynb`
- **Runtime:** server-side (no local venv, no `requirements.txt` — server provides the stack)
- **Stack:** pandas, numpy, hmmlearn, matplotlib, seaborn, scipy, statsmodels
- **Data:** internal company database (connection config TBD — see notebook Setup cell)
- **Workflow:** GSD (`.planning/`)

## What It Does

A regime-aware fund intelligence research notebook. Fits a Hidden Markov Model on benchmark returns to identify latent market regimes (e.g. Risk-On / Risk-Off), then characterizes how a fund's risk, return, drawdown, and factor/sector behavior change across those regimes. Output is structured investment research — presentable to a PM or investment committee without a quant lecture.

Core value: given fund NAV and benchmark return data, answer "what regime are we in, how stable is it, and how does our fund behave in each regime?"

## Constraints

- **Jupyter only:** all analysis lives in `hmm.ipynb`. No CLI entry points.
- **Interpretability first:** model must be explainable. Max 3 HMM states. No black-box ensembles.
- **Fit regime on benchmark, not fund:** regime reflects market conditions; fund behavior is analyzed conditionally.
- **Internal data preferred:** do not add external market data dependencies unless they provide clear value over what we already have.
- **No predictive claims:** HMM is descriptive/diagnostic. Do not imply forecasting ability.
- **Windows paths:** use pathlib or os.path.join throughout.

## Key Files

| File | Purpose |
|------|---------|
| `hmm.ipynb` | Main research notebook — all analysis, charts, summary |
| `data/` | Local data exports from internal DB (gitignored if sensitive) |

## Notebook Sections (planned)

0. Setup & Data Load
1. Exploratory Data Analysis
2. Regime Model (HMM fit + decode)
3. Regime Characterization
4. Fund Behavior by Regime
5. Attribution by Regime (if holdings available)
6. Regime Stability & Transitions
7. Summary & Interpretation

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

- `data/` folder contents (source exports)
- `.planning/` docs (GSD-managed)

---

**Hub:** [[tq-hmm/tq-hmm|TQ HMM]] · **Planning:** [[.planning/planning|.planning/]]
