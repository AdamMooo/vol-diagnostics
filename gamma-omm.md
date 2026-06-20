# Gamma OMM — Market Intelligence Dashboard

GEX monitor for SPY, QQQ, IWM — dealer gamma exposure. Defensible outputs: net GEX (sign + magnitude), γ-flip level, single-strike call/put walls, Hedge Shares/$1, IV30, IV skew (25Δ put − 50Δ call), 3D implied vol surface (OTM convention, log-moneyness) with γ-flip + wall meridian overlays.

## Running the Dashboard

```powershell
cd C:\dev\gamma-omm
.venv\Scripts\activate
streamlit run app.py
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
- Dry run without scheduler: `python -m gex.run_daily --dry-run` (writes `out/index-vol-report-YYYY-MM-DD.html`, no email sent)

## Status

<!-- GSD-HUB:START -->
> Auto-generated from `.planning/STATE.md` + `ROADMAP.md` · synced 2026-06-20 22:48 UTC

**Milestone:** Phase 16 — vrp percentile · **Status:** unknown · **STATE last_updated:** ?

### Current Position
- **Phase:** 16
- **Plan:** 16-02 complete (Phase 16 done)
- **Status:** Executing
- **Last activity:** 2026-06-16

_Edit `.planning/STATE.md` or `.planning/ROADMAP.md` to update — this block is regenerated automatically._
<!-- GSD-HUB:END -->

### Operator notes (handwritten — survives hub-sync)

**Re-entry (2026-06-16).** v3.5 progress: `15 ✅ · 16 ✅ · 17 · 17.1 · 18`. The dead "evolution" tab is being replaced by a page-1 "vol regime" card; Phase 18 does the reorg that kills it. **Phase 16 (VRP percentile) shipped + verified** — `gex/vrp_history.py`, vol-index − RV20 series with VRP-03 isolation, displayed scalar switched to vol-index basis, one CardField → email+dashboard. **New: `.planning/notes/page-1-card-spec.md`** is the canonical contract 17/17.1/18 implement against (frozen field defs/order/units/timescales). **Added Phase 17.1** (25Δ butterfly + front-expiry straddle expected move; macro-event flag folds in here). Cut realized-cone + RND as flashy-breadth. Next: `/gsd:plan-phase 17` or `17.1` (point each CONTEXT at the card spec). Parked in inbox: host static HTML report + slim email (Path A), intraday GEX monitor — both post-v3.5. **Landmine:** gsd-planner auto-commit truncated ROADMAP.md this session — verify roadmap + git status after every plan-phase ([[project-gsd-planner-truncated-roadmap]]).

**North star locked (2026-06-12).** gamma-omm is a vol/dealer microstructure dashboard — show what the market is doing and how dealers will behave. No editorial layer, no trade signals, no "write or wait" synthesis. Metrics: VRP rank, term structure, skew, surface evolution, GEX/dealer positioning — observable facts with percentile context. PMs draw their own conclusions. Build planning deferred to next session.

**Yield-share spun out (2026-06-12).** All 16-name Purpose Yield ETF work moved to its own repo `C:\dev\yield-share-strategy` — `run_daily_yield.py`, `runners/yield_daily.ps1`, the Yield Shares SVG, `YIELD_EMAIL_TO`, and all 16-name `out/` history (142 snapshot rows + per-name surface parquets). The shared vol engine was duplicated, not moved. gamma-omm is now pure SPY/QQQ/IWM index. (GLD/TLT/XLF snapshot rows predate this and stay — they're macro ETFs, not yield names.)

Last hand-updated: 2026-06-03 | **Repo polish (out-of-phase, 2026-06-03).** Professional HTML filenames, thousands separator fix, S3 upload removed. Phase 14 (accumulation gating) is next — context already in `14-CONTEXT.md`.

**Review fixes (2026-06-01, commit `543cfe2`):** Applied all findings from two code reviews (phase-11 standard + deep review). 126/126 tests green after all changes.

- **CR-01 (test fixtures):** `surface_diagnostics`, `compute_skew_25d`, `compute_term_structure` were not mocked in any of the 3 test fixtures — the real implementations ran against minimal fake DataFrames missing required columns, injecting NaN silently into `summary["coverage_pct"]` etc. Tests passed only because nothing asserted those keys. All 3 fixtures now mock all three functions.
- **IN-01 (test fixtures):** `fake_skew_df` used stale column `"call_50d_iv"` — real schema is `"call_25d_iv"` (from `compute_skew()`). Renamed in all 3 fixtures.
- **WR-01 (report.py):** `pct_chg = r.get("price_change_pct") or 0.0` caused a flat day (0.0%) to render as "—". Changed to `is not None` guard.
- **WR-02 (vol_metrics.py):** `evolution_5d_summary` was stringifying `as_of` → `str(date_val)`. The `hasattr(as_of, "strftime")` guard in `report.py` was therefore dead in production. Now returns the date object; formatting lives in the caller as intended.
- **WR-03 (requirements.txt):** `pytz` was used in `run_daily.py` but not pinned — only present as a transitive dep. Added `pytz>=2024.1`.
- **WR-04 (compute.py):** `yf.Ticker("^IRX").fast_info.get("lastPrice")` silently returned None when yfinance changed the key to `"last_price"` (camelCase vs snake_case varies by version). Now tries both; adds a print when falling back silently.
- **IN-02 (exposure_engine.py):** Deleted dead `compute_surface_slopes()` function — no callers.
- **IN-03 (compute.py):** VRP was stored in `summary` as a decimal fraction (e.g. 0.027) while `iv30` is in percentage points (e.g. 18.5). `vrp_headline()` in vol_metrics.py expects pp. Now converts: `vrp = vrp_decimal * 100`.
- **review2-WR-02 (validation.py + run_daily.py):** `save_snapshot` used `datetime.date.today()` (local clock) while `save_surface_snapshot` used the ET-derived `today` date. On any non-ET machine the two parquet stores would land under different dates for the same session. `save_snapshot` now accepts an explicit `date` param; `run_daily` passes `today`.
- **review2-IN-02 (surface_evolution.py):** Added explicit `if front_atm.size > 0` guards before `nanmean` calls for `term_change` front/back slices — avoids relying solely on RuntimeWarning suppression for empty-array edge case.
- **review2-IN-03 (analytics.py):** `_find_zero_crossing` checked `vals[i] == 0.0` before `vals[i] * vals[i+1] < 0`. If the first grid point was exactly zero it returned early without checking for a cleaner sign-change further along. Swapped order: product-sign check first, exact-zero check second.

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
- **v3.2 — Codebase Rigor Sweep (planned 2026-05-14)** — six-item formal phase, see below

---

## v3.2 — Codebase Rigor Sweep (planned 2026-05-14, ready to execute)

**Why:** After 12 commits of out-of-phase methodology + UI + viz work over 2026-05-13/14, the dashboard is *defensible* but the codebase has accumulated loose ends. This phase lifts it from "works and is defensible" to "production-grade." Nothing is broken; this is rigor not repair.

**Scope (6 items, ~3–5 days):**

1. **Test coverage expansion** — target +15–25 tests for currently-uncovered critical paths:
   - `vol_surface_data()` OTM convention (K<S → put, K≥S → call); moneyness band filter; log_moneyness math
   - `compute_skew()` 25Δ put / 50Δ call selection; min_dte=7 filter; pp output
   - `save_snapshot()` schema-additive migration (new cols on old store, NaN backfill)
   - `_get_risk_free_rate()` fallback to 0.05 when yfinance fails
   - `oi_vol_surface_data` (now `vol_surface_data`) → `compute_ticker` → summary roundtrip
   - Hedge Shares/$1 formula `net_gex / (spot**2 × 0.01)` vs known inputs
   - Annotation meridian rendering (γ-flip, walls within range vs outside)

2. **Email pipeline E2E verification** — `python -m gex.run_daily --dry-run`. Open `out/gex_YYYYMMDD.html` in a browser. Confirm every new metric renders (Hedge Shares/$1, Skew 25Δ), glossary entries correct, no `Δ-flow` leakage anywhere. Document any silent breakage.

3. **README.md hand-update** (draft → approve workflow per Adam's preference):
   - Strip "Δ-flow" references; rename to "Hedge Shares/$1"
   - Remove "Cross-asset overview" section (deleted from dashboard)
   - Add Skew (25Δ), IV Surface (OTM convention), Methodology expander references
   - Update dashboard table to mention tabbed expanders

4. **Config consolidation** — pull scattered magic numbers into `gex/config.py`:
   - Surface: grid sizes (50×40), moneyness band (0.22), dte_max (180), z-cap percentile (97)
   - Filters: min OI (100), max IV (3.0), min DTE (1), skew min_dte (7)
   - Caching: TTL (300s, 1800s)
   - Plot anchors: K/S tick values, DTE tick values
   Each constant gets a one-line docstring with rationale + source.

5. **Dead code + stale-ref sweep** — audit run_daily, report.py, validation, tests for unused branches and obsolete imports. Plot_overview was an example; find any others. Confirm no remaining `OI×vega`, `Δ-flow`, `gamma_regime`, `vanna_exposure` references in *active* code (research docs and historical commit logs OK to keep).

6. **DIST-01 + DIST-04 closure** (v3.2 ship-blockers from prior backlog):
   - **DIST-01:** Thread `ChainSnapshot.as_of` through `compute_ticker` → `summary` → `report.build_email()` so the email displays the actual quote timestamp instead of inferring from "today"
   - **DIST-04:** Filter-drop transparency — log/display "filters removed X% of raw chain OI" so opaque exclusions are visible

**README workflow:** I draft the new content → Adam reviews → I commit on approval. Per project rule "READMEs are maintained separately," explicit ask treated as one-time scope, not blanket override.

**Out of scope (deferred):**
- Type hint audit (modern syntax sweep) — distinct workstream
- Email JPG attachments (Inbox item) — separate UX polish, after v3.2 ships
- SVI parametric vol surface fit — only if the linear surface becomes load-bearing for decisions
- Single-name extension (non-SPY/QQQ/IWM) — requires per-ticker positioning assumption review

**Ready to execute via `/gsd-plan-phase` for formal multi-plan breakdown, or `/gsd-quick` item-by-item if Adam prefers tighter cycles.**

### v3.2 — execution progress (2026-05-14 evening)

| # | Item | Status | Commit |
|---|---|---|---|
| 1 | Email pipeline E2E verification | ✅ done — caught real label drift + stale "everything removed" line | `d9b6f91` |
| 2 | README hand-update | ✅ done — draft→approve workflow, defensibility tiers front and centre | `af8cda9` |
| 3 | Config consolidation (`gex/config.py`) | ✅ done — 15+ constants from 5+ files into one module with rationale docstrings | `287e1da` |
| 4 | Test coverage expansion | ⏸ **paused — needs structural plan** | — |
| 5 | Dead code + stale-ref sweep | ✅ done — fixed broken matplotlib/Plotly mismatch in run_gex.py; all stale refs confirmed absent | `22ec33a` |
| 6 | DIST-01 + DIST-04 closure | pending | — |

**Test coverage paused on purpose.** Next: `/gsd-plan-phase --chain` for proper breakdown.

**Out-of-phase additions (same session):**
- Vol surface spike fix: `IV = np.clip(IV, iv_floor, iv_cap)` — surface geometry was not clipped, only the z-axis display range was. Needle spike gone. (`cdc9e90`)
- Strike Slope + Term Slope metrics in Vol tab + parquet snapshots. Shows `value (Nth pctile, Nd)` once N≥10 sessions of history, "Nd, building context" until then. First slope snapshots land tomorrow at 16:30 ET. (`cdc9e90`, `fdfdaff`)

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
