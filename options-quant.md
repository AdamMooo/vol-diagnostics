# Options Quant — Sleeve Allocation Framework

Regime-aware options-overlay sleeve decision dashboard for Purpose. Describes the current options environment (VRP, skew, term structure, trend, drawdown, fragility) and the historical base rates for each sleeve (covered call, cash-covered put, collar, short strangle) in similar environments. **Market-general** — no fund specialization. Ships as a self-contained HTML report on free CBOE+FRED data.

## Status

**Active — 2026-05-04 — milestone v2.1 (POC Delivery & Validation).** Phase 1 complete. Bayesian reframe shipped: conditional summary leads the HTML report, equity chart removed, Section E carries unconditional bull-market caveat. Report is ready to send to quant team.

Open items before sending: UAT the HTML in a browser; NDX skew identity bug (NDX/SPX share the same CBOE SKEW signal).

**v1.0 status:** Closed without ship. `hmm.ipynb` preserved as legacy single-fund diagnostic.

**Research question:** Given today's vol/skew/trend/drawdown readings, what have options sleeves historically returned in similar environments — and what is the honest statistical confidence in that pattern?

## How to Run

```
python run.py           # text dashboard to stdout
python build_report.py  # generates out/sleeve_report_YYYYMMDD.html
```

Open `out/sleeve_report_YYYYMMDD.html` in any browser. No Jupyter needed.

## Memory

- **Operations:** [[options-quant/CLAUDE|CLAUDE.md]] (run commands & constraints)
- **Plan:** `.planning/ROADMAP.md` (open via VS Code — dotfolder, Obsidian can't index)
- **Tasks:** [[../tasks/Options-Quant-Tasks|Task board]]

## Design Decisions

See `.planning/PROJECT.md` for the full table. Key decisions:

| Date | Decision | Why |
|------|----------|-----|
| 2026-05-04 | Bayesian reframe — conditional summary leads report; equity chart removed | Growth-of-$1 chart was a strategy-ranking signal, not a decision-support signal. Conditional base rates are the point. |
| 2026-05-04 | Deliverable is HTML report (`build_report.py`), not a Jupyter notebook | Simpler, no Jupyter dependency, opens in any browser; same content |
| 2026-05-04 | Bloomberg calibration deferred — ship on free data | POC value is the framing and conditional analysis, not absolute IV calibration; Bloomberg is a one-class swap |
| 2026-05-04 | Drop Phase β (PDIV specialization) — α-only scope | Market-general scorecard is more useful than a fund-tuned overlay rule |
| 2026-05-04 | Local POC dev track (CBOE + FRED) | Free official sources; identifier set matches Bloomberg so math is portable |
| 2026-05-04 | yfinance rejected, all-official sources | yfinance is unofficial Yahoo scraper; CBOE/FRED are clean provenance |
| 2026-05-04 | Universe = SPX + NDX index level (POC) | Matches what VIX/VXN actually measure |
| 2026-04-30 | Pivot v1.0 HMM → v2.0 Sleeve Framework | HMM alone cannot answer options sleeve allocation |
| 2026-04-30 | Strategy menu = CC + CSP + Collar + ShortStrangle (drop dispersion) | Dispersion is dealer/HF turf; out of scope for retail AM |

## Data Requirements

**Active — all-official free sources:**
- CBOE: SPX (1975+), VIX (1990+), SKEW (1990+), VIX3M (2009+), VXN (2009+)
- FRED: NASDAQ100 (NDX prices, 2010+), DGS3MO (3M T-bill, rf_rate)
- Synthesized: `iv30_90mny = ATM + (SKEW - 100) * 0.5`; NDX `iv90_atm` via SPX term-ratio scaling

**Bloomberg (deferred — pending team greenlight):**
- `30DAY_IMPVOL_90.0%MNY_DF`, `30DAY_IMPVOL_100.0%MNY_DF`, `90DAY_IMPVOL_100.0%MNY_DF` via `con.bdh`
- VIX (`PX_LAST`), risk-free `USGG3M Index`

## Planned Phases

**v2.1 milestone:**
- Phase 1: COMPLETE — HTML report, Section D reframe, WALKTHROUGH.md
- Post-phase: COMPLETE — Bayesian reframe (conditional summary, equity chart removal, Section E caveat)
- Phase 2+: open, driven by quant-team feedback

**Closed milestones:**
- v2.0 (engine build) — closed 2026-05-04, archived under `.planning/phases-archive/v2.0-engine/`
- v1.0 (HMM diagnostic) — closed 2026-04-30, archived under `.planning/phases-archive/v1.0-hmm/`

## Known Issues

| Issue | Description | Status |
|-------|-------------|--------|
| NDX skew identity | NDX/SPX share the same CBOE SKEW signal — readings always identical | Open — fix before team meeting |
| NDX iv90_atm synthesis | Uses SPX term-structure ratio | Open — same category as skew |
| 90mny IV synthesis | `slope=0.2` approximation; absolute level uncalibrated | Deferred pending Bloomberg greenlight |
| v1.0 GMM mislabeled as HMM | `hmm.ipynb` uses `GaussianMixture`, not HMM | Preserved as-is, legacy artifact |
