# CLAUDE — Vol Diagnostics Dashboard
Last updated: 2026-08-09 | Status: v5.0 shipped, no active milestone.

## Start Here

| I want to… | Go to |
|---|---|
| Run it locally | [Local Setup](#local-setup) — clone, venv, `streamlit run app.py` |
| Know what it does / why | [What It Does](#what-it-does) |
| Set up a brand-new machine | [New Machine](#new-machine) — 6 steps + a gotchas table |
| Push a change live | [Deploy](#deploy-oracle) — one SSH line, never backgrounded |
| Find a module | [`engine/` map](#engine-package-active--v30) |
| Know what I may not change | [Constraints](#constraints) |

**Any OS.** The setup below is written for Linux/WSL (the live dev setup); every
command has a Windows equivalent noted inline. Nothing here is bound to a
specific machine or user account.

**Current work:** interview/portfolio readiness pass — the dashboard is public-linked.
Phase 27's monitor UI was built, then deleted 2026-07-27 after audit (no defensible
reason to surface raw percentiles without evidence-tier context). `engine/monitor/`
remains as backend-only candidate infra, unused by the UI.

## Repo Card

- **Runtime:** local Python (venv). Bloomberg/Cron2 is a future swap, not the build environment.
- **Entry points:**
  - `streamlit run app.py` — interactive dashboard (SPY/QQQ/IWM): per-ticker cards + plain-English read, 3D vol surface, surface "video", positioning
  - `python -m engine.run_daily --send` — daily HTML email (scheduled weekdays via GitHub Actions `.github/workflows/daily-report.yml` since 2026-07-14 — this is the only scheduler; the old local Windows Task Scheduler job is gone, verified absent 2026-08-06, so the pipeline is machine-independent)
  - `python -m engine.run_gex --ticker SPY` — single-ticker CLI (prints summary, saves PNGs)
- **Output:** daily email + `out/` parquet stores (`gex_snapshots`, `surface_history/`, `vol_index/`, `surface_evolution`)
- **Data:** free — CBOE delayed-quote JSON (chains) + CBOE vol-index CSVs + yfinance closes + FRED. No API key. Bloomberg swap = one class in `engine/data/data_loader.py`.
- **Tests:** `pytest engine/tests` — 483 green.
- **Workflow:** GSD (`.planning/`)

## What It Does

Dealer-gamma + implied-vol diagnostics for an **index income-sleeve PM** (covered calls / cash-secured puts on SPY/QQQ/IWM). Per ticker:
- a plain-English **read** (premium rich/cheap from the VRP percentile, dealer stabilizing/amplifying) sitting on top of the field card, **credibility-gated** — only chips backed by enough history are shown;
- an **interactive 3D vol surface** with mouse-driven smile/term slices, a day-by-day surface **"video"** (Evolution tab, Level ↔ Change), and a two-date ΔIV **compare**;
- OI-led **positioning** — GEX demoted, capped ≤90 DTE, labeled a model construct.

Descriptive only — no predictive/prescriptive claims. An in-app "Methodology & assumptions" popover (sidebar) states the evidence tier behind each read, condensed from `research/methodology-deep-review.md` (fact-checked 2026-07-27).

**Cold-start note:** chain-derived metrics (skew, surface, GEX) only accrue from our own daily snapshots (since ~2026-05-06); the VRP percentile rides the CBOE vol-index's real depth (VIX to 1990, VXN/RVX to 2009), ranked against a genuine ~10-year (2,520-session) window via `config.VRP_DEEP_LOOKBACK_SESSIONS` — not a short recent-regime window, so "cheap"/"rich" can't just mean "cheap relative to an already-elevated past year." The daily scheduler firing is what compounds the value.

**Removed (commit `663f72f`, archive cleanup):** the v2.x sleeve-allocation framework (`run.py`, `build_report.py`, `signals.py`, `backtest.py`, `data_layer.py`, …) and the v1.0 `hmm.ipynb` — hmm was moved to the **purpose-factor-model** repo (formerly marco-quant). All recoverable from git history.

## Local Setup

Already have the repo, `.env`, and `out/`? This is the whole loop:

```bash
python3 -m venv .venv
source .venv/bin/activate               # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py                    # interactive dashboard
python -m engine.run_gex --ticker SPY   # single-ticker smoke test to stdout
pytest engine/tests                     # expect 483 green
```

Starting from nothing on a fresh box? Go to [New Machine](#new-machine) instead —
this block assumes the out-of-band files are already in place.

`requirements.txt` tracks the stack. Add packages there when needed.

## New Machine

**Nothing here is machine-bound.** The daily email runs on GitHub Actions, the
dashboard runs on Oracle, `out/` lives on Oracle's disk plus the OCI backup.
Setting up a new box buys you local dev + manual deploy — nothing else. **The old
machine can be wiped without stopping anything.**

Git carries only code. **Three things are gitignored** and must arrive out-of-band:

| Item | Lives at | Get it from |
|---|---|---|
| `.env` | repo root | KeePassXC vault, or copy from old box, or regenerate (§ Secrets) |
| `vol-diagnostics.key` | `~/.ssh/` | same — needed for deploy + data sync |
| `out/` data | repo root | `scripts/sync-from-oracle.sh` pulls it from Oracle |

**Prerequisites:** Git, Python 3.11+ (dev runs 3.13, CI runs 3.11 — either is fine),
and KeePassXC (`keepassxc.org`) if restoring secrets from the vault.

### The six steps

```bash
# 1. Authenticate FIRST — the repo is private; cloning unauthenticated fails
#    with a confusing "repository not found", not a permission error.
gh auth login

# 2. Clone into the native filesystem (see gotcha #1)
mkdir -p ~/dev && cd ~/dev
git clone https://github.com/AdamMooo/vol-diagnostics
cd vol-diagnostics
git config core.autocrlf input        # repo has no .gitattributes

# 3. Environment
sudo apt install -y python3-venv      # separate package on Debian/Ubuntu
python3 -m venv .venv
source .venv/bin/activate             # Windows: .venv\Scripts\activate
pip install -r requirements.txt       # pywin32 is marker-gated; skipped off Windows

# 4. Drop in the two secrets: .env → repo root, key → ~/.ssh/
chmod 600 ~/.ssh/vol-diagnostics.key  # see gotcha #2

# 5. Pull the data
bash scripts/sync-from-oracle.sh      # Windows: .\scripts\sync-from-oracle.ps1

# 6. Verify before trusting it
pytest engine/tests                                    # expect 483 passed
python -m engine.run_gex --ticker SPY                  # CBOE feed reachable
python -m engine.health_check                          # out/ freshness
ssh -i ~/.ssh/vol-diagnostics.key ubuntu@40.233.113.63 "echo ok"
streamlit run app.py
```

### Gotchas (each one cost a real debugging session)

| # | Trap | Fix |
|---|---|---|
| 1 | **WSL: cloning into `/mnt/c`** — 9p I/O is slow enough to hurt pytest and parquet reads, and the filesystem can't hold Unix permission bits, which breaks the SSH key outright | Clone into the WSL filesystem (`~/dev`) |
| 2 | **SSH key lands as 0644/0777** → `Permissions are too open`. KeePassXC is a Windows app, so its Save dialog writes to the Windows side no matter where you point it | `chmod 600 ~/.ssh/vol-diagnostics.key`. `sync-from-oracle.sh` checks this up front rather than failing inside scp |
| 3 | **Plaintext key left in Windows Downloads** after a vault restore | Delete the Windows-side copy — it's a private key in the most-synced folder on the box |
| 4 | **`run_daily --dry-run` fails on Linux** — kaleido needs a Chrome binary Linux doesn't ship | `python -c "import kaleido; kaleido.get_chrome_sync()"`. Skip unless testing email; the dashboard and test suite never touch kaleido |
| 5 | **`.env` permissions don't survive a copy** — it inherits the new folder's ACL/umask | Don't put it in a synced/shared folder |

**Platform notes.** The codebase is effectively platform-agnostic: no `C:\` paths
and no Windows-only imports in `engine/` or `app.py`. The one deliberate exception
is `engine/report/emailer.py:34`, which branches on `sys.platform` — Outlook COM on
Windows, SMTP everywhere else. Both paths are maintained, and `requirements.txt`
needs no edits (`pywin32` is gated to `sys_platform == "win32"`). It already runs on
Ubuntu daily in two places: the Oracle Docker image (`python:3.11-slim`) and the
GitHub Actions runner. Both `sync-from-oracle.sh` and `.ps1` are maintained twins.

### Secrets — restore or regenerate

Only **two** things can't be reconstructed by a clone: `.env` and `~/.ssh/vol-diagnostics.key`.

**Restore (normal path).** Both live as encrypted attachments in a KeePassXC vault,
`vol-diagnostics-secrets.kdbx`, on Google Drive. Open the `.kdbx` → master
passphrase → for each entry, **Advanced → Attachments → select → Save**. The master
passphrase is the one thing not stored digitally; if it's lost, the vault is
unrecoverable and the regeneration path below is the fallback.

**Regenerate (from scratch).**
- **`.env`** — Gmail App Password (Google Account → Security → App Passwords); OCI Customer Secret Key and API signing key (OCI console → My Profile → generate new, delete old); all OCIDs / namespace / subnet / image / AD are readable from the OCI console any time. `.env.example` lists every key with where-to-find notes.
- **SSH key** — generate a new keypair, add the public key via the OCI console (Instance → Console connection / Cloud Shell), then update the GitHub `ORACLE_SSH_KEY` secret. The `.pub` re-derives: `ssh-keygen -y -f vol-diagnostics.key`.

*(Standing intent: git-crypt would fold the `.env` step into `git clone` + unlock — see auto-memory `git-crypt-all-projects-decision`. Not set up; the KeePassXC vault covers the same need.)*

## Deploy (Oracle)

Pushing to `main` does **not** update the live site — Oracle only updates when you SSH in and pull. Run this after every push you want live:

```
ssh -i ~/.ssh/vol-diagnostics.key ubuntu@40.233.113.63 "cd ~/vol-diagnostics && git pull && docker compose up -d --build"
```

Same command on any machine — only the `-i` key path differs (point it at wherever
the key lives on that box). The IP is Oracle's reserved Always-Free address, stable
unless the instance is recreated.

Three hard rules, each learned the expensive way:

1. **Never background it.** Run the pull+build line on its own, watched in the foreground. Backgrounded, it died mid-`pip install` on the 1 vCPU/1GB box, committed no layer, and left no build cache (2026-08-06).
2. **Never chain `docker compose down` or `systemctl restart docker` into the same SSH call.** That combo hard-locked the box, requiring an OCI console reboot (2026-07-22).
3. **A running site is not evidence your deploy landed.** When the build above died, the old container came back up under its restart policy — the site looked alive while serving stale code. Check the image, not the port.

Rule 3 is now enforced, not remembered. The image carries a `GIT_SHA` build arg
(`Dockerfile`, wired through `docker-compose.yml`), so the commit a container was
built from can be read back out of it:

```bash
bash scripts/verify-deploy.sh    # run from YOUR box, not the server
```

It compares three SHAs — `origin/main`, the server's repo HEAD, the running
container's stamp — and names which hop went stale (pull vs. build), exiting 1 if
any differ. `scripts/update.sh` makes the same assertion inline and now **fails**
instead of printing a cheerful `docker compose ps`. Keep the standalone check
anyway: a deploy killed mid-build can't report its own death, which is exactly how
rule 1 bit in the first place, so the verifier has to be a separate process.

4. **A change to `update.sh` itself takes two runs to land.** The script's own
   `git pull` replaces the file by rename, and the running `bash` holds the old
   inode open to the end — so run N fetches the new script and executes the old
   one. Harmless but confusing: the step counter (`[1/3]` vs `[1/4]`) is how you
   tell which version actually ran. Deploy twice whenever the diff touches
   `scripts/update.sh` (2026-08-09).

Site: https://40.233.113.63.nip.io

## Constraints

- **No predictive claims (current dashboard/email surfaces only):** descriptive of current environment + historical analog only. A predictive/prescriptive modeling track is the intended next milestone (see project hub) — this constraint governs the existing diagnostics surfaces, not that future work.
- **Interpretability first:** conditional base rates primary, no hidden scoring or weighting.
- **Strategy menu:** covered call, cash-covered put, collar, short straddle. Dispersion out of scope.
- **No new signals (dashboard/email surfaces):** six signals + fragility composite locked. Sole-owner project now (no external team gate) — the discipline that stays is self-imposed statistical validation (multiple-testing correction, out-of-sample checks) before any new signal ships, not organizational sign-off.
- **Paths:** use pathlib or `os.path.join` throughout — never hardcode a separator or an absolute path. This is what keeps the repo portable across dev box, Docker image, and CI runner.
- **No PDIV / HMM this phase:** locked per scope cap.
- **CBOE vol-index term siblings (verified 2026-06-23):** CBOE publishes VIX9D and VIX3M (SPY term-structure siblings). No 9D/3M variants exist for VXN (QQQ) or RVX (IWM) — CDN returns 403 for those symbols. Term-structure ratios are SPY-only; QQQ/IWM gracefully degrade.

## `engine/` Package (active — v3.0)

The whole diagnostics engine lives in `engine/`. It was renamed from `gex/`
(2026-06-21) once GEX got demoted to one subdomain — the package now spans data,
greeks/exposure, vol surface, vol metrics, and reporting. **Orchestration +
shared config stay at the package root; everything else is grouped by domain:**

```
engine/
  config.py  compute.py  session.py  run_daily.py  run_gex.py   # root: config + orchestration seam
  health_check.py  backup_to_oci.py  restore_from_oci.py        # root: ops — data freshness + OCI backup/restore (Phase 23)
  data/      data_loader  vol_index  validation  surface_history  oi_history  store
  gex/       greeks_engine  exposure_engine  analytics       # dealer-gamma subdomain
  surface/   surface_interactive  surface_evolution  surface_sweep
  vol/       vol_metrics  vrp_history
  report/    card_model  report  png_export  emailer  observation
  monitor/   schema  ranker  metrics  hysteresis  monitor_store  calibration   # Phase 26 severity-rank + hysteresis alert engine
  tests/     (483 green)
```

**Tickers: SPY, QQQ, IWM only.** Full chain pulled per ticker — no moneyness filter, no OI cutoff.

| Ticker | Index | Role |
|--------|-------|------|
| SPY | S&P 500 | Primary benchmark; highest OI → cleanest gamma signal |
| QQQ | Nasdaq-100 | Tech/high-beta; often leads regime flips before SPY |
| IWM | Russell 2000 | Small-cap risk proxy; divergence from SPY = domestic stress signal |

```
python -m engine.run_gex                # SPY, saves charts to out/
python -m engine.run_gex --ticker QQQ   # QQQ or IWM
python -m engine.run_daily              # all 3 tickers → HTML email
```

| Module | Purpose |
|--------|---------|
| `engine/config.py` | Shared constants (`GEX_MAX_DTE`, surface smoothing/clip, …) |
| `engine/compute.py` | Shared pipeline `compute_ticker(ticker)` — single source of truth for daily + streamlit |
| `engine/run_gex.py` | Single-ticker CLI — fetch → compute → print summary → save PNGs |
| `engine/run_daily.py` | Daily orchestrator — SPY/QQQ/IWM, parquet snapshot, HTML email with ΔIV surface PNGs |
| `engine/session.py` | Shared NYSE trading-session helpers — one source of truth for latest/collection session, DTE, freshness cutoffs (`pandas_market_calendars`) |
| `engine/health_check.py` | Data-pipeline health check — verifies daily snapshots current across tickers + model-ready session-depth targets; `--strict` exits 1 on stale/missing (cron/Docker healthcheck) |
| `engine/backup_to_oci.py` | Backs up `out/` to Oracle Cloud Object Storage via S3-compatible API (BACKUP-01); creds from env only, never logged |
| `engine/restore_from_oci.py` | Restores `out/` from an OCI backup (BACKUP-02); refuses to overwrite populated dest without `--force`, hard-fails on corrupt download |
| `engine/data/data_loader.py` | CBOE delayed quotes JSON → `ChainSnapshot` (gamma from CBOE) |
| `engine/data/vol_index.py` | CBOE vol-index CSV store (VIX/VXN/RVX + VIX9D/VIX3M) — deep daily history |
| `engine/data/validation.py` | Parquet snapshot store: `save_snapshot()` + `load_history()` (drives 30-day ZGL chart) |
| `engine/data/surface_history.py` | Surface snapshot store: per-ticker chain parquet, `list_available_dates`, `nth_trading_day_back` |
| `engine/data/oi_history.py` | Per-expiry OI snapshot store (`out/oi_history/oi_{ticker}.parquet`) — idempotent daily append of call/put OI aggregates |
| `engine/data/store.py` | Shared parquet-store I/O — `atomic_to_parquet` (temp file + `os.replace`) so an interrupted write never truncates accumulated history |
| `engine/gex/greeks_engine.py` | `add_greeks()` adds `T_years`; `bs_gamma()` used only by `gamma_profile()` to sweep spot |
| `engine/gex/exposure_engine.py` | GEX = gamma × OI × 100 × S² × 0.01; `strike_gex`, `gamma_profile` |
| `engine/gex/analytics.py` | `summarise()` → net GEX, zero-γ level, call/put walls, δ-flow; plotly charts |
| `engine/surface/surface_interactive.py` | Interactive surface engine: `build_surface_payload`/`build_diff_payload`/`build_movie_payload` + `render_*_html` (client-side plotly.js embedded via `components.html`) |
| `engine/surface/surface_evolution.py` | ΔIV scalar engine — level, rms, skew_change, term_change vs rolling-mean baseline |
| `engine/surface/surface_sweep.py` | Surface-sweep diagnostic renderer (`python -m engine.surface.surface_sweep`) |
| `engine/vol/vol_metrics.py` | `compute_rv20`, skew/term helpers |
| `engine/vol/vrp_history.py` | Deep VRP percentile: `vol_index − RV20×100` over a 252-session window (does NOT touch the chain) |
| `engine/report/card_model.py` | Canonical card: `build_card_fields` (fields) + `build_card_read` (read chips + soft-lean, credibility-gated). Single source for dashboard + email |
| `engine/report/report.py` | HTML email builder — cards, ΔIV surface PNG attachments, glossary |
| `engine/report/png_export.py` | Plotly → PNG (kaleido) for email attachments |
| `engine/report/emailer.py` | SMTP send |
| `engine/report/observation.py` | Appends a GEX observation block to today's daily note (idempotent) |
| `engine/monitor/schema.py` | Monitor dataclasses (`MonitorRow`, `AlertEvent`) + `METRIC_INVENTORY` — the canonical (metric, ticker) severity-rank set (net GEX excluded per D-10) |
| `engine/monitor/ranker.py` | Pure ECDF severity ranker (no I/O) — dual-lookback deep+1yr level rank + two-sided k=5 change rank via `percentileofscore` |
| `engine/monitor/metrics.py` | Per-metric history loader dispatch — `load_metric_series(ticker, metric)` returns date-indexed series, reusing existing store readers; never raises |
| `engine/monitor/hysteresis.py` | Pure alert state machine — `check_alert_transition` (out → in_entry → in_escalate) with hysteresis on exit; bands passed in from config |
| `engine/monitor/monitor_store.py` | Monitor parquet stores (`ranks.parquet` + `alert_events.parquet`) — `compute_and_save_monitor_rows` orchestration seam `run_daily` calls; idempotent, never raises per metric |
| `engine/monitor/calibration.py` | Calibration CLI — replays ranker + hysteresis over stored history, reports alert episodes/week per band/width grid; prints config-ready snippet, never auto-writes config.py |
| `app.py` | Browser dashboard (SPY/QQQ/IWM only) — cards+read, interactive surface (Today/Compare), surface video (Evolution), positioning |

Sign convention: calls positive, puts negative. Positive net GEX = dealers net long gamma (stabilising). Zero-gamma level found via linear interpolation of profile sign change. No categorical regime label is produced — the $200M neutral cutoff was hand-tuned and non-stationary; only the sign of net GEX drives the accent color. **GEX/positioning is capped at ≤90 DTE (`config.GEX_MAX_DTE`)** — the dealer-relevant tenor; the long-dated tail is investor-written call flow (mis-signed by the dealer-short convention) and is excluded. The dashboard surface uses its own `SURFACE_INTERACTIVE_*` smoothing/clip, isolated from the email/evolution path.

**Removed for rigor** (do not reintroduce without methodology audit): VEX/CHEX (vanna/charm exposures), wall cluster + concentration, ZGL flow magnitude, vs-yesterday classifier, event study, early-exercise risk flags, categorical "positive/negative/neutral" regime label, vanna/charm BS computations.

Bloomberg upgrade path: swap `engine/data/data_loader.py` only — everything else is data-source-agnostic.

## v2.x sleeve framework / v1.0 hmm — REMOVED

The sleeve-allocation framework (`run.py`, `build_report.py`, `local_data.py`, `data_layer.py`, `signals.py`, `backtest.py`, `dashboard.py`, `stats_rigor.py`, `sensitivity.py`, `WALKTHROUGH.md`) and `hmm.ipynb` were removed in commit `663f72f` (archive cleanup). `hmm.ipynb` lives in the **purpose-factor-model** repo (formerly marco-quant) now. Recover any of these from git history if needed — they are not part of this repo's working tree.

## Workflow

Use GSD commands for all phase work:
- `/gsd-quick` for small fixes
- `/gsd-execute-phase` for planned phase work
- `/gsd-debug` for investigation

## Do Not Touch

- `out/` parquet stores — generated daily snapshots; appended by `run_daily`, not hand-edited
- `.planning/phases-archive/` — archived phase history
- `.planning/` docs (GSD-managed)

---

**Hub:** [[vol-diagnostics/vol-diagnostics|Vol Diagnostics]] · **Planning:** [[_planning/vol-diagnostics/STATE|.planning/]]
