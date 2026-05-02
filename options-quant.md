# Options Quant — Sleeve Allocation Framework

Regime-aware options-overlay sleeve scorecard for Purpose. Phase α builds an engine that recommends sleeve attractiveness (covered call, cash-covered put, collar, short straddle) across SPX/QQQ and optionally XIU/XSP, driven by a transparent percentile-rank scorecard on VRP / skew / term / trend / drawdown signals. Phase β specializes the engine for PDIV's overlay. Phase γ (optional) adds a Markov-switching fragility flag.

## Status

**Active — 2026-04-30 — milestone v2.0** (pivoted from v1.0 HMM-centric diagnostic on 2026-04-30; project renamed `tq-hmm` → `options-quant` on 2026-05-01). Phase 1 (Extended Data Layer) authored locally; Cron2 run is the gate before Phase 2.

**v1.0 status:** Closed without ship. `hmm.ipynb` preserved as legacy single-fund diagnostic. See `.planning/MILESTONES.md` for closure rationale and `_audits/2026-04-30-sleeve-pivot-audit.md` for the pivot audit.

**Research question:** Given a vol/skew/trend/drawdown panorama on a small set of liquid underlyings, which option-overlay sleeves are attractive right now, and what would historical sleeve P&L have looked like in similar past environments?

## Memory

- **Operations:** [[options-quant/CLAUDE|CLAUDE.md]] (run commands & constraints)
- **Plan:** `.planning/ROADMAP.md` (open via VS Code — dotfolder, Obsidian can't index)
- **Tasks:** [[../tasks/Options-Quant-Tasks|Task board]]
- **Auto-memory:** `claude-memory/project_options_quant.md` (project hub), `project_v2_pivot.md` (v2.0 pivot rationale), `project_execution_split.md` (deck-auto-style local-plan/Cron2-run pattern)
- **Skills:** _(none yet linked)_

## How to Run

- Cron2 Juypter Notebook Server (ONLY)
- Cannot run locally

## Design Decisions

See `.planning/PROJECT.md` Strategic Decisions for the full table. Key recent decisions:

| Date | Decision | Why |
|------|----------|-----|
| 2026-05-01 | Rename `tq-hmm` → `options-quant` | Old name reflected v1.0 HMM diagnostic; v2.0 is an options sleeve allocation framework |
| 2026-04-30 | Pivot v1.0 HMM → v2.0 Sleeve Framework | Stated business goal (options sleeve allocation) cannot be answered by an HMM on benchmark returns alone |
| 2026-04-30 | Scorecard primary, HMM optional | PM-auditable, governance-friendly, robust to data limits |
| 2026-04-30 | Strategy menu = CC + CSP + Collar + ShortStrangle (drop dispersion) | Dispersion is dealer/HF turf, capacity-limited, governance-unfriendly for retail AM |
| 2026-04-30 | Use `statsmodels.MarkovRegression` if HMM ever needed | `hmmlearn` not in locked env; statsmodels gives proper sticky Markov-switching |

## Data Requirements

**v2.0 (Phase α) — confirmed working:**
- Fund NAV via Django ORM (`FundAccount.objects.get(symbol).primary_fund.get_adj_nav()`)
- Price + 30d ATM IV (`30DAY_IMPVOL_100.0%MNY_DF`) via `con.bdh` — confirmed 1,584 days SPX
- 30d 90%-moneyness IV (`30DAY_IMPVOL_90.0%MNY_DF`) via `con.bdh` — confirmed; enables skew
- VIX (`PX_LAST`) via `con.bdh` — confirmed
- Risk-free proxy (3M T-bill or equivalent) — TBD field-name probe in Phase 7

**Phase 1 probes (folded into `sleeve_alpha.ipynb` Section 1.2 — pending Cron2 run):**
- `90DAY_IMPVOL_100.0%MNY_DF` (term structure) — `IV_FIELDS["iv90_atm"]`
- XIU / XSP IV equivalents — probed with `[landed]/[deferred]` log

**Phase β prerequisite (still open):**
- Capture PDIV's current overlay rule (gate for Phase 7)

## Planned Phases

Phases 1-8 (α/β/γ) — renumbered for v2.0. See `.planning/ROADMAP.md`. v1.0 phases archived under `.planning/phases-archive/v1.0-hmm/`. Phase 1: authored local · Cron2 pending.

## Known Issues

- v1.0 `hmm.ipynb` uses GMM, not HMM — preserved as-is per pivot decision
- v1.0 annualization uses `(1+log_mean)^252-1` (technically wrong for log returns); not corrected in legacy notebook
- v1.0 has no causal regime labels (full-sample fit) — diagnostic-only, not for decision support

## Skills (relevant)

