# Gamma OMM — Market Intelligence Dashboard

GEX monitor for SPY, QQQ, IWM — dealer gamma exposure. Defensible outputs only: net GEX (sign + magnitude), zero-gamma level, single-strike call/put walls, δ-flow, IV30.

## Running the Dashboard

```powershell
cd C:\dev\gamma-omm
.venv\Scripts\activate
streamlit run streamlit_app.py
```

Opens at `http://localhost:8501`.

## Using It

- **Sidebar** — select one or more of SPY / QQQ / IWM; hit **Refresh** to re-fetch (clears the 5-min cache)
- **Cards** — spot, net GEX, δ-flow, zero-γ level, call/put walls, IV30. Accent bar reflects sign of net GEX (no categorical regime label)
- **Cross-asset overview** — bar chart comparing net GEX across selected tickers (color = sign)
- **Per-ticker expanders** — strike GEX bar chart, gamma profile, 30-day ZGL-vs-spot history

Live chains fetched from CBOE delayed quotes JSON on first load (CBOE CDN, no auth required). Results cached 5 minutes per ticker. Parquet snapshot written daily by `run_daily` feeds the 30-day history chart.

## Email Pipeline (unchanged)

```powershell
python -m gex.run_daily   # all 3 tickers → HTML email via Outlook COM
```

## Runners (`runners/`)

Scheduled / repeatable scripts. Edit in place; manage via Windows Task Scheduler.

| File | Purpose | Schedule | Manage |
|------|---------|----------|--------|
| [[runners/gex_daily.ps1\|gex_daily.ps1]] | Registers / inspects the GEX Daily Report task. Runs `python -m gex.run_daily` → SPY/QQQ/IWM chains → HTML email via Outlook COM, parquet snapshot, observation block appended to today's daily note. | Mon–Fri 16:30 local (NYSE trading days only — `is_trading_day()` gates internally) | `gex_daily.ps1 activate \| deactivate \| status` (admin shell required for first registration) |

Project-internal runners only. Cross-project runners live under each project's own `runners/` folder (e.g. `selenium/runners/allocation_report.ps1`). Vault-wide config scripts are in `.config-vault/_meta/`.

**Sanity checks**
- `gex_daily.ps1 status` → `State: Ready`, `Last result: 0` (any non-zero is an error code, e.g. `2147942402` = path not found)
- Manual fire: `Start-ScheduledTask -TaskName "GEX Daily Report"`
- Dry run without scheduler: `python -m gex.run_daily --dry-run` (writes `out/gex_YYYYMMDD.html`, no email sent)

## Status

<!-- GSD-HUB:START -->
> Auto-generated from `.planning/STATE.md` + `ROADMAP.md` · synced 2026-05-11 22:09 UTC

**Milestone:** v3.1 — Hardening & Charm · **Status:** active · **STATE last_updated:** 2026-05-11 (v3.2 scoped via methodology audit)

### Current Position
- **Phase:** 5 — UAT Sign-Off & Cleanup (complete)
- **Plan:** P3 (Wave 3 — docs sweep)
- **Status:** Phase 5 complete — UAT signed off, docs cleaned, ready for Phase 6
- **Last activity:** 2026-05-11 — Out-of-phase work: email rebuild (stacked cards, 720px, theme-adaptive), scheduled task hardening (path fix, weekday trigger, --send guard, Outlook auto-launch), wall cluster + concentration + distance-to-flip + expected-1d-sigma rolled into analytics/report. Audit completed: [[_audits/methodology-review-2026-05-11]]. v3.2 Phase 8 scoped in ROADMAP.

### Pending Todos
- Phase 6: Charm chart — next phase to execute

### Roadmap (current milestone)
- ✅ **Phase 5: UAT Sign-Off & Cleanup** — Complete 4 deferred Streamlit UAT scenarios, commit outstanding code changes, and update stale docs
- ⬜ **Phase 6: Charm by DTE Chart** — Add Charm-by-DTE-bucket bar chart to analytics and surface it in the Streamlit Live tab expander
- ⬜ **Phase 7: Critical-Path Test Coverage** — Add critical-path tests for the 5 previously uncovered modules

_Edit `.planning/STATE.md` or `.planning/ROADMAP.md` to update — this block is regenerated automatically._
<!-- GSD-HUB:END -->

### Operator notes (handwritten — survives hub-sync)

Last hand-updated: 2026-05-10 | **Parked: pre-demo hardening (v3.2) pending — see audit**

**Recent changes (2026-05-10):** Email rebuilt — stacked per-ticker cards in `gex/report.py` (560px width, all dashboard numbers exposed). Scheduled task fixed (path was stale `options-quant` → `gamma-omm`, trigger now Mon–Fri only). Outlook auto-launch shortcut added to Startup. First real fire: Mon 2026-05-11 16:30. Live IWM regime flipped negative on 2026-05-07 — at-ZGL pin.
Hub: [[gamma-omm/gamma-omm]]

## Active workstream — pre-demo hardening (parked, resume in a few days)

Goal: harden GEX POC before showing head of capital markets. Audit completed 2026-05-07.

- **Audit doc:** [[_audits/gex-prep-audit-2026-05-07|GEX POC pre-demo audit]] — section-by-section claims/formulas/risks, Q&A prep, prioritized hardening queue
- **Next action:** `/gsd-plan-phase` for v3.2 with the P0 list (FRED rate, snapshot timestamp + history N display, clustered walls, metadata strip, concession block, NEUTRAL_ABS_FLOOR decision, Task Scheduler daily run)
- **Top 3 things to defend in the meeting:** (1) sign convention for SPY/QQQ/IWM dealer positioning, (2) gamma sourced directly from CBOE (American-model), (3) absolute GEX magnitude is methodology-dependent (sign, ZGL, and wall strikes are the load-bearing outputs)
- **Concede upfront:** 15-min delay, OI is T-1, sample too short for event-study inference. Vanna/charm/VEX/CHEX, vs-yesterday classifier, wall clusters, and the categorical regime label were stripped after the 2026-05-11 methodology audit.
