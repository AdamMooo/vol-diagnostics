---
type: hub
project: vol-diagnostics
---
# Vol Diagnostics — Market Intelligence Dashboard

Vol/dealer microstructure dashboard for SPY, QQQ, IWM — index income-sleeve PM diagnostics. Current metrics: VRP percentile (vol-index − RV20 vs 252-session history), IV30, 25Δ skew, 3D implied vol surface (OTM convention, log-moneyness), surface evolution (ΔIV at 5/10/20 horizons), net GEX (≤90 DTE), γ-flip, OI walls. Descriptive only — no trade signals.

## Running the Dashboard

```powershell
cd C:\dev\vol-diagnostics
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

**Primary (since 2026-07-14): GitHub Actions** — `.github/workflows/daily-report.yml` runs on GitHub's runners (schedule: weekdays 20:35 UTC / 4:35pm ET, or manual via `gh workflow run daily-report.yml --repo AdamMooo/vol-diagnostics -f force=true`). Rsyncs `out/` down from the Oracle server before the run and back up after — Oracle's disk stays the one source of truth, history is deliberately not stored in git. Needs 8 repo secrets (`GEX_EMAIL_TO`, `SMTP_HOST/PORT/USER/PASS/FROM`, `ORACLE_HOST`, `ORACLE_SSH_KEY`). Moved off Oracle because the Micro instance's 1 vCPU/1GB couldn't run headless Chromium (kaleido PNG export) reliably — the first live cron fire there hung mid-render.

```powershell
python -m engine.run_daily            # all 3 tickers → HTML email via Outlook COM (local) or SMTP (Linux/CI)
python -m engine.run_daily --dry-run  # writes out/index-vol-report-YYYY-MM-DD.html, no email
```

## Runners (`runners/`)

**Local Windows Task Scheduler job retired (2026-07-14)** — `gex_daily.ps1` still exists for reference but the "GEX Daily Report" task itself was unregistered; GitHub Actions is the sole scheduler now. Data flows one-way: Oracle's disk is the source of truth, `scripts/sync-from-oracle.ps1` pulls a fresh copy down for local dev/viewing on demand (nothing local collects data anymore, so this can go stale — re-run it whenever you want current data locally).

| File | Purpose | Schedule | Manage |
|------|---------|----------|--------|
| [[runners/gex_daily.ps1\|gex_daily.ps1]] | (Retired) Registered/inspected the old local "GEX Daily Report" task. Kept for reference only. | — | `gex_daily.ps1 activate` to re-register if ever needed (admin shell required) |

**Sanity checks**
- Local data freshness: `.\scripts\sync-from-oracle.ps1` then check `out/gex_snapshots.parquet`'s latest date
- Dry run without scheduler: `python -m engine.run_daily --dry-run`
- GitHub Actions status: `gh run list --repo AdamMooo/vol-diagnostics --workflow=daily-report.yml`

## Status

<!-- GSD-HUB:START -->
> Auto-generated from `.planning/STATE.md` + `ROADMAP.md` · synced 2026-07-17 01:58 UTC

**Milestone:** v5.0 · **Status:** planning · **STATE last_updated:** 2026-07-17T00:00:00.000Z

### Current Position
- **Phase:** Not started (roadmap drafted, Phase 23 up first)
- **Plan:** —
- **Status:** Roadmap created, awaiting approval
- **Last activity:** 2026-07-17 — Roadmap extended for v5.0 (Phases 23–27; added 26 Codebase Organization & Dead Code Removal, 27 Existing Computation Rigor Hardening)

### Pending Todos
- None new. 2 stale pre-v4.0 todos acknowledged and deferred at milestone close (see Deferred Items below).

### Blockers
- `engine/report/png_export.py` still swallows any export failure into a `print()` warning and returns None — the same silent-failure shape that hid the plotly/kaleido version mismatch for months. (Partial-failure visibility was fixed one layer up in `run_daily.py`'s PNG attachment builders.)
- `runners/gex_daily.ps1`'s "GEX Daily" naming is stale (script retired, kept for reference only).
- `out/` parquet stores live only on the Oracle server, no backup anywhere — now Phase 24 of v5.0 (no longer just a flagged risk).

_Edit `.planning/STATE.md` or `.planning/ROADMAP.md` to update — this block is regenerated automatically._
<!-- GSD-HUB:END -->

### Operator notes (handwritten — survives hub-sync)

**Re-entry (2026-07-16).** Phase 20.5 (Email Remodel) executed end-to-end — 4 plans, Wave 1 parallel in worktrees, real dry-run email opened in-browser and visually approved. **v4.0 Cloud Hosting is now functionally complete** (19/20/20.5/21/22 all done) but never formally shipped via `/gsd:complete-milestone` — no `MILESTONES.md` entry, phase dirs not archived; open question for next session. Mid-session, a genuine content-clarity catch: "premium cheap" on the VRP chip had no stated comparison basis. Investigation found the claim in this file ("VRP percentile is deep") wasn't actually true — `vrp_history.py`'s RV20 alignment was hardcoded to a 400-day yfinance fetch, capping the usable percentile window to ~1.5yr despite CBOE vol-index data running back to 1990 (VIX) / 2009 (VXN, RVX). Fixed: widened to a real ~10yr window (`config.VRP_DEEP_LOOKBACK_SESSIONS = 2500` + a 40-day fetch buffer to clear RV20 warmup/calendar slack — commit `9f6f920`). Also made the Skew (25Δ) card field state direction explicitly ("puts pricier"/"calls pricier"/"flat") instead of a bare signed number, since `put_iv - call_iv`'s sign isn't self-evident. 7 new tests, suite still green (364). Separately dropped the stale "locked until team validates" governance line from this file's Constraints section (commit `786ce92`) — the dashboard is sole-owner/public now (password gate removed, Oracle-hosted), so there's no team to validate against; kept the actual statistical-validation discipline since that risk doesn't go away with ownership. That conversation escalated into scoping a **v5.0 "Data Foundation" milestone** via `/gsd:new-milestone` (harden data collection/retention — `out/` currently lives ONLY on the Oracle server, no backup — before attempting the options-writing/pricing model Adam actually wants). Scoping confirmed (data-foundation-only, modeling deferred) but paused before writing PROJECT.md/REQUIREMENTS.md/ROADMAP.md at Adam's request. Resume via `.planning/.continue-here.md`.

**Re-entry (2026-07-15).** Ad-hoc low-hanging-fruit pass, punch list from the 2026-07-14 deploy (`7c0c06f`, suite green 358): (1) dashboard auth now fails closed — moved off `st.secrets` to `.env`-sourced `PASSWORD` via `python-dotenv`, blocks access if unset instead of opening it, and swapped `==` for `secrets.compare_digest`; local `.env` needed a `PASSWORD` added or this would've locked out local dev too. (2) `png_export.export_png()` now raises on failure instead of swallowing every exception into a `print()`+`None` — callers (`run_daily.py`'s two PNG builders) already wrap each export in their own try/except and track failed tickers, so the internal swallow was a redundant, less-visible duplicate layer; updated its two tests to assert raise instead of None+stdout. (3) Renamed the retired `gex_daily.ps1` task "GEX Daily Report" → "Index Vol Diagnostics Daily Report" — stale name, script is reference-only now. **Not yet done:** dedicated (non-personal) PASSWORD value on the Oracle server itself — the local `.env` fix doesn't touch that; still needs a `ssh`+`.env` edit on the box next time you're deploying.

**Re-entry (2026-07-14).** Phases 21+22 (v4.0 Cloud Hosting) done, out of sequence ahead of 20.5, via a long ad-hoc session (not a planned/executed GSD phase — see STATE.md decisions). **Dashboard live at https://40.233.113.63.nip.io** (Oracle free E2.1.Micro + Caddy/Let's Encrypt via nip.io, since bare IPs can't get a cert and A1.Flex ARM stayed capacity-constrained in Toronto — retry loop for A1 left running in background). Real bugs found and fixed along the way, all committed: kaleido's PNG export needs a native `chromium` apt package on Linux (Chrome-for-Testing has no linux-arm64 build); 5 dead deps dropped (matplotlib/seaborn/statsmodels/boto3/pandas-datareader — zero imports anywhere). Two measured dashboard perf fixes — deduped a redundant per-ticker risk-free-rate/VVIX fetch, and skipped the never-displayed `cv_rmse` cross-validation on the interactive path — cut a full 3-ticker load from ~36s to ~11s. (Tried parallelizing the ticker loop too; measured it *slower* than sequential on 1 vCPU and reverted.)

**Scheduler architecture changed mid-session**: the daily scheduler container (supercronic) crash-looped on Oracle's kernel, got fixed (`-no-reap`), then its first live cron fire hung mid-PNG-export (1 vCPU/1GB couldn't run headless Chromium reliably) — at that point moved the whole daily job to **GitHub Actions** (`.github/workflows/daily-report.yml`) instead of continuing to fight the underpowered box. Oracle now only runs `dashboard` + `caddy`; the workflow rsyncs `out/` down before each run and back up after, keeping Oracle's disk as the one source of truth (data deliberately not in git). Took 6 test-trigger iterations to get fully green, each surfacing a real bug (rsync missing on both ends, root-owned files unreadable by the sync user, flaky `ssh-keyscan`, an empty `SMTP_PASS` secret from a failed paste) — first green run `29369841431`, verified the data round-tripped back to Oracle correctly. Suite green (359, +1 regression test for a real `UnboundLocalError` caught by timing the deploy, not by tests). Local Windows Task Scheduler job retired afterward (unregistered via admin PowerShell) — GitHub Actions is the sole scheduler now. Added `scripts/sync-from-oracle.ps1` so local dev can pull Oracle's data (the actual source of truth) on demand. **Remaining punch list in STATE.md Blockers** — png_export.py's single-image silent-failure pattern, dashboard password reuse, stale "GEX Daily" naming on the now-retired script. Next: `/gsd:plan-phase 20.5` (context already gathered from 2026-07-13).

**Re-entry (2026-07-13, later same day).** Finished the project rename gamma-omm → vol-diagnostics that the folder move had left half-done: hub file renamed to `vol-diagnostics.md`, `app.py` page_title, docstrings/User-Agent in `engine/config.py`/`vol_index.py`/`run_gex.py`, Oracle deploy scripts (not yet live — Phase 21 hasn't run), wikilinks across all active `.planning/` docs, and `C:\dev\CLAUDE.md`/`INDEX.md`. GitHub repo renamed `AdamMooo/gamma-omm` → `AdamMooo/vol-diagnostics` (owner-only permission — Adam did it directly); local remote updated. **Actual root cause of the 4:30pm failure found:** it was never transient — Windows Task Scheduler's "GEX Daily Report" action still pointed at the dead `C:\dev\gamma-omm\...` path from before the folder move (`LastTaskResult=1`). Re-registered from an elevated PowerShell; confirmed pointing at `vol-diagnostics` and due to fire again today 4:30pm. Also ran `/gsd-discuss-phase 20.5` → [[.planning/phases/20.5-email-remodel/20.5-CONTEXT|20.5-CONTEXT]] (header redesign, mobile width, filter-drop transparency, 3 ship-blocker todos folded in from the 2026-05-11 audit). Next: `/gsd:plan-phase 20.5`.

**Re-entry (2026-07-13).** Two fixes: (1) plotly/kaleido version mismatch (plotly 5.24 + kaleido 1.3) had been silently killing all PNG chart attachments in every daily email for an unknown period — non-blocking try/except hid it. Upgraded venv to plotly 6.9.0, pinned `requirements.txt` to `plotly>=6.1.1,<7.0`. Verified 6/6 PNGs export now. (2) Reweighted the card toward vol surfaces per request: dropped `Net GEX` out of `COMPACT_PRIMARY_LABELS` (card_model.py) — primary row is now pure vol-surface content (Spot, IV30/EM, VRP, Skew, 25Δ Fly); GEX/walls/hedge-shares demoted to the detail column (email) / "More fields" expander (dashboard). Email header retitled "Equity Index Dealer Flow" → "Index Vol Diagnostics". Today's 2026-07-13 report (which failed at the 4:30pm scheduled run — exit 1, all 3 tickers errored transiently, cause not logged since Task Scheduler doesn't capture stdout) was backfilled and sent manually. Suite green (358). **Landmine for next time:** Task Scheduler doesn't capture run_daily's stdout — a future silent-failure investigation needs a log redirect added to the scheduled action, not a manual repro.

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

**North star locked (2026-06-12).** vol-diagnostics is a vol/dealer microstructure dashboard — show what the market is doing and how dealers will behave. No editorial layer, no trade signals. Metrics: VRP rank, term structure, skew, surface evolution, GEX/dealer positioning — observable facts with percentile context.

**Yield-share spun out (2026-06-12).** All 16-name Purpose Yield ETF work moved to `C:\dev\yield-share-strategy`. vol-diagnostics is now pure SPY/QQQ/IWM index.

## Defensibility status

- ✅ GEX formula (Gatheral/Bergomi derivable; SpotGamma/perfiliev/GEXboard match)
- ✅ Dealer positioning (Garleanu, Pedersen & Poteshman 2009, RFS — empirically confirmed)
- ✅ Hedge Shares/$1 (mechanism well-supported in Egebjerg & Kokholm 2024)
- ✅ IV surface, OTM convention (Gatheral §2.1; log-moneyness per Cont & da Fonseca 2002)
- ✅ IV Skew (Xing, Zhang & Zhao 2010, JFQA)
- ⚠️ ZGL — zero peer-reviewed papers as a price level; defensible only as a model construct
- ⚠️ Walls — trader lore; defensible only as OI concentration, not support/resistance

Hub: [[vol-diagnostics/vol-diagnostics]]
