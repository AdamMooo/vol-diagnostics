# Phase 1: Data Layer - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Load fund NAV and benchmark returns from two server-side data sources (Django ORM + Bloomberg API), compute log returns, align on a common date index, and produce an EDA section. No HMM work here — output is a validated, aligned return series pair that downstream phases can trust.

</domain>

<decisions>
## Implementation Decisions

### Server architecture
- **D-01:** Notebook runs server-side (same pattern as deck-auto). No local code execution. `data.ipynb` will be provided as reference context showing the exact data pull patterns — the planner should treat it as the primary reference for connection and query syntax.
- **D-02:** The Setup cell documents parameters (fund identifier, benchmark ticker, date range) and the two connection patterns, but does not require reader intervention to run on the server.

### Data sources
- **D-03:** Fund data via Django ORM (shell_plus context). Load NAV or price series for the target fund.
- **D-04:** Benchmark via Bloomberg API (`con.bdh()`). Use S&P 500 as a universal benchmark regardless of fund-specific mandate — avoids the complexity of fund-matched benchmarks for an internal research tool.
- **D-05:** Both data pulls documented clearly in the Setup cell so a reader on the same server can reproduce them.

### Return computation
- **D-06:** Log returns: `np.log(price_t / price_{t-1})` applied to both fund NAV and benchmark price series after loading. Log returns are preferred over simple returns for the Gaussian HMM (better approximation of normality).
- **D-07:** Daily frequency. No resampling to weekly or monthly.

### Date alignment
- **D-08:** Inner join — keep only dates where both fund and benchmark have a valid observation. No forward-filling. Missing dates are dropped, not imputed. Any unexplained gaps are flagged visually in EDA.

### EDA charts and stats
- **D-09:** Light visual structure set up in Phase 1: consistent figure sizes (e.g. `figsize=(12, 4)`) and a basic color scheme (fund vs benchmark color constants). Phase 5 handles full polish — Phase 1 charts should be readable but not presentation-quality.
- **D-10:** Summary statistics table covers the full history (unconditional): annualized mean return, annualized volatility, Sharpe ratio, max drawdown. This serves as the baseline against which Phase 3's regime-conditional table is compared.
- **D-11:** Required EDA charts: cumulative return (fund vs benchmark), rolling 21-day volatility (fund vs benchmark), drawdown chart (fund). All on a shared date axis.

### Claude's Discretion
- Exact figure sizes and baseline color constants (fund/benchmark colors — Phase 5 will refine)
- Drawdown computation method (e.g. rolling max approach)
- Cell organization and markdown headers within the notebook
- How to annualize vol and Sharpe (assume 252 trading days — standard for daily equity data)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Data pull patterns
- `data.ipynb` — Primary reference for Django ORM queryset syntax (fund NAV) and Bloomberg `con.bdh()` call signature (benchmark). **This file will be provided by the user — the planner must wait for it or ask before writing Plan 01-01.**

### Project constraints
- `CLAUDE.md` (project root) — Notebook-only constraint, Windows paths (pathlib), interpretability-first rules
- `.planning/REQUIREMENTS.md` — DATA-01 through DATA-05 define the acceptance criteria for this phase

No ADRs or external design specs — this is an internal research project. Requirements are fully captured in decisions above and REQUIREMENTS.md.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- The existing `hmm.ipynb` contains a prior analysis (One-Class SVM on yield shares) that is unrelated to this project. Treat the notebook as a blank slate — clear all existing cells before implementing Phase 1.
- Bloomberg `con.bdh()` call pattern is visible in the existing notebook (fields list, date range args) — use as syntax reference only.

### Established Patterns
- Django ORM / shell_plus: same server environment as deck-auto. No explicit connection setup in the notebook — Django context is pre-loaded.
- pathlib for any file paths (Windows server).

### Integration Points
- Phase 1 output: two date-indexed pandas Series (fund log returns, benchmark log returns) sharing a common index after inner join. These are the inputs to Phase 2 (HMM fit on benchmark) and Phase 3 (fund analysis).

</code_context>

<specifics>
## Specific Ideas

- S&P 500 chosen as universal benchmark to avoid fund-specific benchmark matching complexity — this is a deliberate simplification for an internal research tool
- `data.ipynb` is the canonical reference for data pull syntax; the planner should read it before writing Plan 01-01

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-data-layer*
*Context gathered: 2026-04-22*
