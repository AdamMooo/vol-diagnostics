# TQ HMM

Regime-aware fund intelligence research notebook. Fits a Hidden Markov Model on benchmark returns to identify latent market regimes, then characterizes how a fund's risk, return, drawdown, and behavior shift across those regimes. Output is structured investment research presentable to a PM or investment committee.

## Status

**Active — 2026-04-22.** Phases 1 + 2 complete, Phase 3 cells written. Notebook at 19 cells. Run cells 16-19 on server to confirm Phase 3, then Phase 4.

**Research question:** Does the fund behave materially differently across identifiable market regimes, and can we characterize those differences in terms of risk-adjusted return, drawdown, beta, and factor/sector exposure?

## Memory

- **Operations:** [[tq-hmm/CLAUDE|CLAUDE.md]] (run commands & constraints)
- **Plan:** `.planning/ROADMAP.md` (open via VS Code — dotfolder, Obsidian can't index)
- **Tasks:** [[../tasks/TQ-HMM-Tasks|Task board]]
- **Auto-memory:** _(none yet — capture as `claude-memory/project_tq_hmm.md` when durable patterns emerge)_
- **Skills:** _(none yet linked)_

## How to Run

- Cron2 Juypter Notebook Server (ONLY)
- Cannot run locally

## Design Decisions

| Date | Decision | Why |
|------|----------|-----|
| 2026-04-22 | 2-state Gaussian HMM on benchmark returns | Interpretable, explainable, aligns with finance intuition; 3-state extension natural if needed |
| 2026-04-22 | Fit regime model on benchmark, not fund | Avoids circularity; regime reflects market conditions, fund behavior analyzed conditionally |
| 2026-04-22 | Internal data only (fund NAV + benchmark return minimum) | Avoids external dependencies; Bloomberg/macro data adds complexity without clear upside at MVP |
| 2026-04-22 | Jupyter Notebook as primary artifact | Research format — presentable to finance team, no deployment overhead |

## Data Requirements

**Minimum viable:**
- `date` — daily or weekly
- `fund_return` / `fund_nav` — total return preferred
- `benchmark_return` — same frequency

**Optional (enables attribution):**
- `portfolio_weights` by sector or factor
- `benchmark_weights` by sector

## Planned Phases

See `.planning/ROADMAP.md` for full phase list.

## Known Issues

- GMM (sklearn) used instead of HMM (hmmlearn) — no temporal transition constraints; may produce noisier regimes. If duration check WARNs, revisit.
- `get_adj_nav()` returns DataFrame, not Series — `.squeeze()` applied in cell 2.

## Skills (relevant)

