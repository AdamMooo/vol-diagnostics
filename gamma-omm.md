# Gamma OMM — Market Intelligence Dashboard

GEX monitor for SPY, QQQ, IWM — dealer gamma exposure. Defensible outputs: net GEX (sign + magnitude), zero-gamma level, single-strike call/put walls, Hedge Shares/$1, IV30, IV skew (25Δ put − 50Δ call), OI×vega-weighted 3D implied vol surface.

## Running the Dashboard

```powershell
cd C:\dev\gamma-omm
.venv\Scripts\activate
streamlit run streamlit_app.py
```

Opens at `http://localhost:8501`.

## Using It

- **Sidebar** — select one or more of SPY / QQQ / IWM; hit **Refresh** to re-fetch (clears the 5-min cache)
- **Cards** — spot, net GEX, Hedge Shares/$1, zero-γ level, skew (25Δ), IV30. Accent bar reflects sign of net GEX (no categorical regime label)
- **Cross-asset overview** — bar chart comparing net GEX across selected tickers (color = sign)
- **Per-ticker expanders** — strike GEX bar chart, gamma profile, 30-day ZGL-vs-spot history, OI×vega-weighted 3D vol surface, IV skew term structure

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
> Auto-generated from `.planning/STATE.md` + `ROADMAP.md` · synced 2026-05-13 20:49 UTC

**Milestone:** v3.1 — SHIPPED · **Status:** shipped · **STATE last_updated:** 2026-05-13 (methodology audit + formula fixes)

### Current Position
- **Phase:** 5 — UAT Sign-Off & Cleanup (complete) + Out-of-Phase Refactor + Methodology Validation (complete)
- **Status:** ✅ v3.1 SHIPPED + methodology validated + 2 new defensible metrics added
- **Last activity:** 2026-05-13 — Two research passes (practitioner audit + peer-reviewed deep review). Three commits: d193b1b (delta-flow fix + live ^IRX rate + caveats), c173c1b (OI×vega 3D vol surface), 83a9ff5 (IV skew 25Δp−50Δc, Xing 2010 JFQA). Charm-by-DTE (Phase 6) intentionally cancelled — adds model assumptions on top of dealer-positioning assumption.

### Pending Todos
- Validate charm calculation methodology for American options
- Propose defensible Greeks/flow metrics with historical backing
- Define new milestone scope based on validated approach

### Roadmap (current milestone)
- ✅ Phase 5: UAT Sign-Off & Cleanup (all 4 scenarios pass, docs updated)
- ✅ Out-of-Phase Refactor (2026-05-11): VEX/CHEX/regime labels removed; expected-1d-sigma added; methodology footer rewritten

_Edit `.planning/STATE.md` or `.planning/ROADMAP.md` to update — this block is regenerated automatically._
<!-- GSD-HUB:END -->

### Operator notes (handwritten — survives hub-sync)

Last hand-updated: 2026-05-13 | **Methodology fully validated + 2 new metrics shipped**

**Recent changes (2026-05-13):** Two research passes followed by three out-of-phase commits.

Research artifacts (in `research/`):
- `methodology-audit.md` — practitioner-source audit (SpotGamma, perfiliev, GEXboard)
- `methodology-deep-review.md` — academic literature review with SSRN/DOI citations

Commits today:
- **`d193b1b`** — Fix Delta-Flow formula bug (was `|GEX|/S/0.01`, algebraically redundant with GEX). Now `Γ_net × OI × 100` = "Hedge Shares/$1" (shares dealers trade per $1 spot move). Live `^IRX` for ZGL risk-free rate (was hardcoded 5%). Methodology caveat added to dashboard + email.
- **`c173c1b`** — 3D OI×vega-weighted implied vol surface (Plotly Surface + scipy cubic griddata; Avellaneda et al. 2020 backs OI×vega over OI-only). Per-ticker expander chart.
- **`83a9ff5`** — IV Skew (25Δ put − 50Δ call). First metric with **direct peer-reviewed predictive validity** — Xing, Zhang & Zhao (2010, JFQA): 10.9% annual alpha. Card row + term-structure chart + email + glossary.

**Defensibility status:**
- ✅ GEX formula (Gatheral/Bergomi derivable; SpotGamma/perfiliev/GEXboard match)
- ✅ Dealer positioning (Garleanu, Pedersen & Poteshman 2009, RFS — empirically confirmed)
- ✅ Hedge Shares/$1 (mechanism well-supported in Egebjerg & Kokholm 2024)
- ✅ OI×vega vol surface (Avellaneda 2020, arXiv)
- ✅ IV Skew (Xing, Zhang & Zhao 2010, JFQA)
- ⚠️ ZGL — zero peer-reviewed papers as a price level; defensible only as a model construct
- ⚠️ Walls — trader lore; defensible only as OI concentration, not support/resistance

**Phases 6–8 status:** Charm-by-DTE (Phase 6) intentionally NOT built — academic literature (DeLorenzo 2023, Flynn 2024) shows charm is real but stacks more model assumptions on top of already-baked-in dealer assumption. Adam's call: don't compound assumption layers. Vega used as a *weight* (vol surface) not as a new exposure metric.

Next:
- Reframe ZGL + wall labels in dashboard ("Gamma Flip Level (model construct)", "Max Call/Put GEX Strike") — 10 min change
- Store `front_skew`, `put_25d_iv`, `call_50d_iv` in daily parquet snapshots → enable 30-day skew history chart
- Email image attachments (full-size JPGs) — defer until charts are visually final

Hub: [[gamma-omm/gamma-omm]]

## Active workstream — methodology layer complete (2026-05-13)

**Status:** Two research passes done, three commits shipped. Dashboard is now mathematically defensible against academic literature. Charm-by-DTE intentionally cancelled (no more stacked assumptions).

**Completed today (out-of-phase, 2026-05-13):**
- Practitioner audit → `research/methodology-audit.md`
- Academic literature deep review → `research/methodology-deep-review.md`
- Commit `d193b1b`: Delta-Flow formula fix → Hedge Shares/$1; live `^IRX` risk-free rate; dealer-positioning caveat
- Commit `c173c1b`: OI×vega-weighted 3D implied vol surface (Avellaneda 2020)
- Commit `83a9ff5`: IV Skew (25Δp − 50Δc), Xing-Zhang-Zhao (2010, JFQA) — first peer-reviewed predictive metric

**Previously completed (out-of-phase, 2026-05-11):**
- VEX/CHEX/regime labels removed; expected-1d-sigma added; methodology footer rewritten
- Task Scheduler hardened (Mon–Fri 16:30 ET, min_dte=1 filter, --send guard, Outlook auto-launch)

**Next immediate actions:**
- Reframe ZGL + wall labels in dashboard ("Gamma Flip Level (model construct)", "Max Call/Put GEX Strike") — 10 min change to make the dashboard honest about what those numbers are
- Store `front_skew`, `put_25d_iv`, `call_50d_iv` in daily parquet snapshots → 30-day skew history chart
- Email image attachments (full-size JPGs via Outlook `Attachments.Add()`) — defer until charts are visually final

**Deferred to v3.2 (Pre-Distribution Hardening):**
- DIST-01: Snapshot timestamp threading (ChainSnapshot.as_of → report.build_email())
- DIST-04: Filter-drop transparency ("Filters removed X% of raw chain OI")

**Cancelled:**
- Phase 6 (Charm-by-DTE chart) — academic backing exists (DeLorenzo 2023, Flynn 2024) but stacks model assumptions on top of dealer-positioning assumption. Vega used as a weight in the vol surface instead.
