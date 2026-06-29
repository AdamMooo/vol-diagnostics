# Gamma OMM — Market Intelligence Dashboard

Vol/dealer microstructure dashboard for SPY, QQQ, IWM — index income-sleeve PM diagnostics. Current metrics: VRP percentile (vol-index − RV20 vs 252-session history), IV30, 25Δ skew, 3D implied vol surface (OTM convention, log-moneyness), surface evolution (ΔIV at 5/10/20 horizons), net GEX (≤90 DTE), γ-flip, OI walls. Descriptive only — no trade signals.

## Running the Dashboard

```powershell
cd C:\dev\gamma-omm
.venv\Scripts\activate
streamlit run app.py
```

Opens at `http://localhost:8501`.

## Using It

- **Sidebar** — select one or more of SPY / QQQ / IWM; hit **Refresh** to re-fetch (clears the 5-min cache)
- **Cards** — spot, net GEX, Hedge Sh/$1, γ-flip, skew 25Δ, IV30, VRP percentile. Accent bar reflects sign of net GEX (no categorical regime label). Plain-English read chips shown where credibility-gated history exists.
- **Per-ticker expanders** with **tabs**:
  - **Strikes** — GEX by strike + gamma profile
  - **Vol** — interactive 3D implied vol surface (Today / Compare / Evolution tabs); skew + term structure below
  - **Positioning** — OI-led positioning; GEX (≤90 DTE), call/put walls labeled "(model)" vs "(raw OI)"
- **Bottom expander: Methodology & Assumptions** — full caveat block (free CBOE feed, American greeks model, ^IRX rate, all filters, γ-flip/walls as model constructs, dealer positioning assumption)

Live chains fetched from CBOE delayed quotes JSON on first load (CBOE CDN, no auth required). Results cached 5 minutes per ticker. Parquet snapshot written daily by `run_daily` feeds history charts.

## Email Pipeline

```powershell
python -m engine.run_daily            # all 3 tickers → HTML email via Outlook COM
python -m engine.run_daily --dry-run  # writes out/index-vol-report-YYYY-MM-DD.html, no email
```

## Runners (`runners/`)

Scheduled / repeatable scripts. Edit in place; manage via Windows Task Scheduler.

| File | Purpose | Schedule | Manage |
|------|---------|----------|--------|
| [[runners/gex_daily.ps1\|gex_daily.ps1]] | Registers / inspects the GEX Daily Report task. Runs `python -m engine.run_daily` → SPY/QQQ/IWM chains → HTML email via Outlook COM, parquet snapshot, observation block appended to today's daily note. | Mon–Fri 16:30 local (NYSE trading days only — `is_trading_day()` gates internally) | `gex_daily.ps1 activate \| deactivate \| status` (admin shell required for first registration) |

**Sanity checks**
- `gex_daily.ps1 status` → `State: Ready`, `Last result: 0` (any non-zero is an error code, e.g. `2147942402` = path not found)
- Manual fire: `Start-ScheduledTask -TaskName "GEX Daily Report"`
- Dry run without scheduler: `python -m engine.run_daily --dry-run`

## Status

<!-- GSD-HUB:START -->
> Auto-generated from `.planning/STATE.md` + `ROADMAP.md` · synced 2026-06-22 04:36 UTC

**Milestone:** Phase 16.5 — OI Depth Expansion (next) · **Status:** unknown · **STATE last_updated:** ?

### Current Position
- **Phase:** 16.5
- **Plan:** Not started (next up)
- **Status:** Planning
- **Last activity:** 2026-06-21

_Edit `.planning/STATE.md` or `.planning/ROADMAP.md` to update — this block is regenerated automatically._
<!-- GSD-HUB:END -->

### Operator notes (handwritten — survives hub-sync)

**Re-entry (2026-06-29).** Full codebase review → [[.planning/codebase/REVIEW-2026-06-29]]. **All 6 workstreams addressed · 8 commits · suite GREEN (358).**
- `d7b32f9` **A** atomic parquet writes (`engine/data/store.py`) + vol-index failure isolation + `[CORRUPT]`-loud reads + cross-store check
- `d67f351` **B** shared `engine/session.py` (`latest_session`) — off-by-one `T_years` killed, after-midnight catch-up files under the right session
- `a483977` **D1** dead "what changed today" feature fixed · OI KeyError guard · put/call NaN · γ-flip nearest-spot
- `23cc839` **D2** model-free EM `e^rT` discount · RV20 from adjusted closes · true-5d wall-shift · net-delta doc/dead-branch
- `365ba1c` **E** decluttered dashboard (cut hero narrative + "follow the break" + surface how-to; condensed positioning header; de-conversationalized card lean text; PRESERVED model/raw-OI labels + methodology expander; net −51 lines)
- `9f17ca3` **F** run_gex docstring (`cd gamma-omm`, no "regime" claim) · stale test → green · `io.StringIO` · CLAUDE.md count→358
- `a1419a8` **C** email fails loud (SystemExit 2, scheduler sees failure) · vol-index-feed-down email banner
- `d241c73` review roadmap doc

**D & E changed displayed numbers + copy — validate on the dashboard** (γ-flip, RV20/VRP, expected move, 5d shift; card "read" wording). **Deferred (rationale in commits + review doc):** C-2 resend-without-refetch · W-5 Outlook→SMTP · W-4 fail-open auth (pre-hosting — fail-closed would lock out localhost) · I1 `_classify_term_structure` (tested infra, no user benefit) · I4 skew %ile ≥5-vs-60 (UX call — would hide a daily-visible number). Docker/hosting still parked. gamma-omm.md hub note is uncommitted (mixed with prior WIP).

**Re-entry (2026-06-22).** UI pass-2 polish shipped (quick `260621-v8g`, `ec13dc2`+`c92ddaf`): `ln(K/S)` surface axes, Evolution radio relabel, card γ-flip trim (display-only, email parity intact), `@st.fragment` de-lag. README rewritten to current v3.5 reality. **Phase 16.5 discuss PAUSED** until the `gex/→engine/` migration commits — 16.5 touches the files in flux (another agent owns the migration). The `260621-v8g` commits landed on the pre-migration `gex/analytics.py` path (content also in staged `engine/gex/analytics.py`) — reconcile on migration commit. Then: `/gsd-discuss-phase 16.5`.

**Re-entry (2026-06-21).** Roadmap updated: Phase 16.5 (OI Depth Expansion), Phase 19 (Data Health & Continuity), and v4.0 milestone (Cloud Hosting) added. v3.5 progress: `15 ✅ · 16 ✅ · 16.5 · 17 · 17.1 · 18 · 19`. Freshness banner + email tune shipped 2026-06-20 (`6619308`). Next: `/gsd-discuss-phase 16.5` or `/gsd-plan-phase 16.5`.

**Re-entry (2026-06-16).** Phase 16 (VRP percentile) shipped + verified — `engine/vol/vrp_history.py`, vol-index − RV20 series with VRP-03 isolation, displayed scalar switched to vol-index basis, one CardField → email+dashboard. **`.planning/notes/page-1-card-spec.md`** is the canonical contract 17/17.1/18 implement against. **Landmine:** gsd-planner auto-commit truncated ROADMAP.md — verify roadmap + git status after every plan-phase.

**North star locked (2026-06-12).** gamma-omm is a vol/dealer microstructure dashboard — show what the market is doing and how dealers will behave. No editorial layer, no trade signals. Metrics: VRP rank, term structure, skew, surface evolution, GEX/dealer positioning — observable facts with percentile context.

**Yield-share spun out (2026-06-12).** All 16-name Purpose Yield ETF work moved to `C:\dev\yield-share-strategy`. gamma-omm is now pure SPY/QQQ/IWM index.

## Defensibility status

- ✅ GEX formula (Gatheral/Bergomi derivable; SpotGamma/perfiliev/GEXboard match)
- ✅ Dealer positioning (Garleanu, Pedersen & Poteshman 2009, RFS — empirically confirmed)
- ✅ Hedge Shares/$1 (mechanism well-supported in Egebjerg & Kokholm 2024)
- ✅ IV surface, OTM convention (Gatheral §2.1; log-moneyness per Cont & da Fonseca 2002)
- ✅ IV Skew (Xing, Zhang & Zhao 2010, JFQA)
- ⚠️ ZGL — zero peer-reviewed papers as a price level; defensible only as a model construct
- ⚠️ Walls — trader lore; defensible only as OI concentration, not support/resistance

Hub: [[gamma-omm/gamma-omm]]
