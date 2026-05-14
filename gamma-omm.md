# Gamma OMM — Market Intelligence Dashboard

GEX monitor for SPY, QQQ, IWM — dealer gamma exposure. Defensible outputs: net GEX (sign + magnitude), γ-flip level, single-strike call/put walls, Hedge Shares/$1, IV30, IV skew (25Δ put − 50Δ call), 3D implied vol surface (OTM convention, log-moneyness) with γ-flip + wall meridian overlays.

## Running the Dashboard

```powershell
cd C:\dev\gamma-omm
.venv\Scripts\activate
streamlit run streamlit_app.py
```

Opens at `http://localhost:8501`.

## Using It

- **Sidebar** — select one or more of SPY / QQQ / IWM; hit **Refresh** to re-fetch (clears the 5-min cache)
- **Cards** — spot, net GEX, Hedge Sh/$1, γ-flip, skew 25Δ, IV30. Accent bar reflects sign of net GEX (no categorical regime label)
- **Per-ticker expanders** with **tabs**:
  - **Strikes** — GEX by strike + gamma profile
  - **Vol** — 3D implied vol surface (OTM convention, log-moneyness) with γ-flip + Call/Put Wall meridians overlaid; skew term structure below
  - **History** — 30-day γ-flip vs spot
- **Bottom expander: Methodology & Assumptions** — full caveat block (free CBOE feed, American greeks model, ^IRX rate, all filters, γ-flip/walls as model constructs, dealer positioning assumption)

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
> Auto-generated from `.planning/STATE.md` + `ROADMAP.md` · synced 2026-05-14 15:10 UTC

**Milestone:** v3.1 — SHIPPED · **Status:** shipped · **STATE last_updated:** 2026-05-14 (vol surface OTM convention + GEX overlays)

### Current Position
- **Phase:** 5 — UAT Sign-Off & Cleanup (complete) + Out-of-Phase Refactor + Methodology Validation (complete)
- **Status:** ✅ v3.1 SHIPPED + methodology validated + 2 new defensible metrics added
- **Last activity:** 2026-05-14 — Vol surface rebuilt on OTM convention. Five commits: 6c3dc3d (log-moneyness axis), 70a9021 (skew history snapshots), c914da7 (stale-cache fix + restored top status bar), c16c094 (cubic griddata dropped — was creating artificial wells from undershoot), 0104c29 (OI×vega → OTM convention + GEX overlays: spot plane + γ-flip + Call/Put Wall meridians on the surface). Pending commit: cleanup pass (wider moneyness band ±22%, clean DTE ticks, plot_overview removed, hub doc aligned).

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

Last hand-updated: 2026-05-14 | **Vol surface rebuilt on OTM convention + GEX overlays**

**Recent changes (2026-05-14):** Five commits — carry-over (skew history) + vol surface philosophical refactor (OI×vega → OTM convention) + GEX cross-product overlays + cleanup pass.

- **`6c3dc3d`** — Vol surface in log-moneyness `log(K/S)` (Cont & da Fonseca 2002, Gatheral). Cross-ticker comparable.
- **`70a9021`** — Skew history snapshots: `front_skew`, `put_25d_iv`, `call_50d_iv`, `iv30` added to parquet store. 30-day skew chart in History tab.
- **`c914da7`** — Bug fixes: stale Streamlit cache `KeyError`, restored subtle top status bar after over-correcting on title removal.
- **`c16c094`** — Cubic griddata dropped after Adam spotted "holes" in QQQ surface (cubic was undershooting below local minimum at sparse boundaries → clip-to-zero wells). Linear-only now — no overshoot possible.
- **`0104c29`** — **Vol surface philosophical refactor.** Replaced OI×vega weighting (Avellaneda 2020 framing didn't change the visual — put-call parity meant weighted ≈ unweighted) with **OTM convention** (Gatheral §2.1: put IV for K<S, call IV for K≥S — industry standard, no citation needed). Added **GEX cross-product overlays** on the surface: spot plane + γ-flip meridian + Call/Put Wall meridians. The vol structure can now be read against dealer positioning — the actual novel insight.
- **(this commit pending)** — Cleanup: widened moneyness band to ±22% (far-OTM walls now have rendering headroom), clean DTE tick labels (7/30/60/90/120/180), removed orphan `plot_overview()` + its test (dead after cross-asset bar chart removed), hub doc Defensibility table updated.

**Recent changes (2026-05-13):** Two research passes followed by three out-of-phase commits.

Research artifacts (in `research/`):
- `methodology-audit.md` — practitioner-source audit (SpotGamma, perfiliev, GEXboard)
- `methodology-deep-review.md` — academic literature review with SSRN/DOI citations

Commits today (six total):
- **`d193b1b`** — Fix Delta-Flow formula bug (was `|GEX|/S/0.01`, algebraically redundant with GEX). Now `Γ_net × OI × 100` = "Hedge Shares/$1" (shares dealers trade per $1 spot move). Live `^IRX` for ZGL risk-free rate (was hardcoded 5%). Methodology caveat added to dashboard + email.
- **`c173c1b`** — 3D OI×vega-weighted implied vol surface (Plotly Surface + scipy cubic griddata; Avellaneda et al. 2020 backs OI×vega over OI-only). Per-ticker expander chart.
- **`83a9ff5`** — IV Skew (25Δ put − 50Δ call). First metric with **direct peer-reviewed predictive validity** — Xing, Zhang & Zhao (2010, JFQA): 10.9% annual alpha. Card row + term-structure chart + email + glossary.
- **`dc0919b`** — Hub + STATE.md updated to reflect methodology validation work.
- **`943228d`** — Vol surface viz fix: camera elevated to landscape view, z-axis capped at 97th percentile to clip the deep-OTM corner spike, aspect ratio for landscape proportions, z-contour projection on the floor.
- **`a5e377f`** — Full dashboard UI cleanup. No title, tabbed expanders (Strikes / Vol / History), `Zero-γ` → `γ-flip`, consolidated methodology expander surfacing previously-silent assumptions (free CBOE delayed feed / no OPRA, CBOE American option pricing model for greeks, live ^IRX rate, all filters explicit, γ-flip + walls tagged as model constructs, Hu et al. 2023 caveat).

**Defensibility status:**
- ✅ GEX formula (Gatheral/Bergomi derivable; SpotGamma/perfiliev/GEXboard match)
- ✅ Dealer positioning (Garleanu, Pedersen & Poteshman 2009, RFS — empirically confirmed)
- ✅ Hedge Shares/$1 (mechanism well-supported in Egebjerg & Kokholm 2024)
- ✅ IV surface, OTM convention (Gatheral §2.1; log-moneyness per Cont & da Fonseca 2002)
- ✅ IV Skew (Xing, Zhang & Zhao 2010, JFQA)
- ⚠️ ZGL — zero peer-reviewed papers as a price level; defensible only as a model construct
- ⚠️ Walls — trader lore; defensible only as OI concentration, not support/resistance

**Phases 6–8 status:** Charm-by-DTE (Phase 6) intentionally NOT built — academic literature (DeLorenzo 2023, Flynn 2024) shows charm is real but stacks more model assumptions on top of already-baked-in dealer assumption. Adam's call: don't compound assumption layers. Vega used as a *weight* (vol surface) not as a new exposure metric.

Next:
- ~~Reframe ZGL + wall labels~~ ✅ done as part of `a5e377f` (γ-flip + methodology expander)
- ~~Store `front_skew`, `put_25d_iv`, `call_50d_iv` in daily parquet snapshots~~ ✅ done in `70a9021` (first snapshot lands tomorrow at 16:30 ET)
- README.md hand-update — strip "Δ-flow" / "Cross-asset overview" references, add Skew + IV Surface + OTM convention notes. (Project CLAUDE.md says READMEs are maintained separately, so flagging rather than auto-editing.)
- Email image attachments (full-size JPGs via Outlook `Attachments.Add()`) — finally tackleable now that charts are visually final
- End-to-end sanity pass on the dashboard (tabs, methodology expander, rendered surface)

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
- Store `front_skew`, `put_25d_iv`, `call_50d_iv` in daily parquet snapshots → 30-day skew history chart in the History tab
- Email image attachments (full-size JPGs via Outlook `Attachments.Add()`) — defer until charts are visually final
- End-to-end sanity check on the cleaned dashboard (open each ticker's three tabs, verify methodology expander reads cleanly, confirm rendered surface looks landscape-shaped after z-cap)

**Deferred to v3.2 (Pre-Distribution Hardening):**
- DIST-01: Snapshot timestamp threading (ChainSnapshot.as_of → report.build_email())
- DIST-04: Filter-drop transparency ("Filters removed X% of raw chain OI")

**Cancelled:**
- Phase 6 (Charm-by-DTE chart) — academic backing exists (DeLorenzo 2023, Flynn 2024) but stacks model assumptions on top of dealer-positioning assumption. Vega used as a weight in the vol surface instead.
