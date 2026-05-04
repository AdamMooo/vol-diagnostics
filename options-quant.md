# Options Quant — Sleeve Allocation Framework

Regime-aware options-overlay sleeve scorecard for Purpose. Phase α (the POC) builds an engine that recommends sleeve attractiveness (covered call, cash-covered put, collar, short strangle) on SPX + NDX, driven by a transparent percentile-rank scorecard on VRP / skew / term / trend / drawdown signals. **Market-general** — no fund specialization (Phase β dropped 2026-05-04). Phase γ (optional) adds a Markov-switching fragility flag.

## Status

**Active — 2026-05-04 — milestone v2.0** (pivoted from v1.0 HMM on 2026-04-30; renamed `tq-hmm` → `options-quant` 2026-05-01; **scope simplified to α-only / market-general 2026-05-04**, β/PDIV dropped). Phase 1 done on the local POC track (`sleeve_alpha_dev.ipynb` + `local_data.py` against CBOE+FRED). Phase 2 next.

**v1.0 status:** Closed without ship. `hmm.ipynb` preserved as legacy single-fund diagnostic. See `.planning/MILESTONES.md` for closure rationale and `_audits/2026-04-30-sleeve-pivot-audit.md` for the pivot audit.

**Research question:** Given a vol/skew/trend/drawdown panorama on a small set of liquid underlyings, which option-overlay sleeves are attractive right now, and what would historical sleeve P&L have looked like in similar past environments?

## Memory

- **Operations:** [[options-quant/CLAUDE|CLAUDE.md]] (run commands & constraints)
- **Plan:** `.planning/ROADMAP.md` (open via VS Code — dotfolder, Obsidian can't index)
- **Tasks:** [[../tasks/Options-Quant-Tasks|Task board]]
- **Auto-memory:** `claude-memory/project_options_quant.md` (project hub), `project_v2_pivot.md` (v2.0 pivot rationale), `project_execution_split.md` (deck-auto-style local-plan/Cron2-run pattern)
- **Skills:** _(none yet linked)_

## How to Run

- **Local POC (active dev path):** `.venv/Scripts/python.exe -m jupyter lab` → open `sleeve_alpha_dev.ipynb`. Data via CBOE + FRED, no auth needed. Math layer ports back to Cron2 verbatim.
- **Cron2 / Bloomberg (production):** open `sleeve_alpha.ipynb` on the Cron2 server. Run All on a fresh kernel. Same identifier set as the local notebook so math cells transplant unchanged.

## Design Decisions

See `.planning/PROJECT.md` Strategic Decisions for the full table. Key recent decisions:

| Date | Decision | Why |
|------|----------|-----|
| 2026-05-04 | Drop Phase β (PDIV specialization) — α-only scope | Quant-team usefulness comes from a market-general scorecard, not a fund-tuned overlay rule. Keeps POC tight. |
| 2026-05-04 | Local POC dev track (CBOE + FRED) | Cron2 latency was blocking iteration. Free official sources let math iterate locally; identifier set matches Cron2 so math is portable. |
| 2026-05-04 | yfinance rejected, all-official sources | yfinance is unofficial Yahoo scraper; CBOE publishes its own indices and FRED is government — cleanest data provenance for the quant team's review. |
| 2026-05-04 | Universe = SPX + NDX index level (POC) | Matches what VIX/VXN actually measure (index options). ETFs and Canadian tickers add back when on Bloomberg. |
| 2026-05-01 | Rename `tq-hmm` → `options-quant` | Old name reflected v1.0 HMM diagnostic; v2.0 is an options sleeve allocation framework |
| 2026-04-30 | Pivot v1.0 HMM → v2.0 Sleeve Framework | Stated business goal (options sleeve allocation) cannot be answered by an HMM on benchmark returns alone |
| 2026-04-30 | Scorecard primary, HMM optional | PM-auditable, governance-friendly, robust to data limits |
| 2026-04-30 | Strategy menu = CC + CSP + Collar + ShortStrangle (drop dispersion) | Dispersion is dealer/HF turf, capacity-limited, governance-unfriendly for retail AM |
| 2026-04-30 | Use `statsmodels.MarkovRegression` if HMM ever needed | `hmmlearn` not in locked env; statsmodels gives proper sticky Markov-switching |

## Data Requirements

**Local POC (active) — all-official free sources:**
- CBOE: SPX (1975+), VIX (1990+), SKEW (1990+), VIX3M (2009+), VXN (2009+) via `cdn.cboe.com/api/global/us_indices/daily_prices/{IDX}_History.csv`
- FRED: NASDAQ100 (NDX prices, 2010+), DGS3MO (3M T-bill, rf_rate)
- Synthesized: `iv30_90mny = ATM + (SKEW - 100) * 0.5`; NDX `iv90_atm` via SPX term-ratio scaling

**Cron2 / Bloomberg (production target) — confirmed working:**
- Price + 30d ATM IV (`30DAY_IMPVOL_100.0%MNY_DF`) via `con.bdh`
- 30d 90%-moneyness IV (`30DAY_IMPVOL_90.0%MNY_DF`) via `con.bdh`
- 90d ATM IV (`90DAY_IMPVOL_100.0%MNY_DF`) — probed in Phase 1 Plan 01
- VIX (`PX_LAST`) via `con.bdh`
- Risk-free `USGG3M Index` `PX_LAST`

**Deferred (revisit on Bloomberg):**
- VVIX — no free historical
- XIU / XSP (Canadian) — no free official source

## Planned Phases

POC scope: Phases 1-6 (α engine). Phase γ (HMM fragility flag) optional appendix. Phase β (PDIV) dropped 2026-05-04. See `.planning/ROADMAP.md`. v1.0 phases archived under `.planning/phases-archive/v1.0-hmm/`. Phase 1 done on the local POC track.

## Known Issues

- v1.0 `hmm.ipynb` uses GMM, not HMM — preserved as-is per pivot decision
- v1.0 annualization uses `(1+log_mean)^252-1` (technically wrong for log returns); not corrected in legacy notebook
- v1.0 has no causal regime labels (full-sample fit) — diagnostic-only, not for decision support

## Skills (relevant)

