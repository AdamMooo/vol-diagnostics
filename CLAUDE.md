# CLAUDE — Gamma OMM — Vol Diagnostics Dashboard
Last updated: 2026-07-27 | Status: v5.0 shipped. No active milestone — current work is an interview/portfolio readiness pass (public dashboard link). Phase 27's monitor UI (raw percentile board + evidence panel) was built, then deleted from the dashboard 2026-07-27 after audit — no defensible reason to surface it without evidence-tier context; `engine/monitor/` backend stays as candidate infra, unused by the UI for now.

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

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py                    # interactive dashboard
python -m engine.run_gex --ticker SPY   # single-ticker smoke test to stdout
pytest engine/tests                     # 483 tests
```

`requirements.txt` tracks the stack. Add packages there when needed.

## Moving to a New Dev Machine

Git carries only code. Three things are gitignored and must ride along out-of-band:

1. **`.env`** — secrets (SMTP, both OCI credential families, OCI private key). Copy the file directly from the old machine. `.env.example` lists every key with a "where to find it" note if you'd rather regenerate from scratch.
2. **SSH key** `vol-diagnostics.key` (+ `.pub`) — needed for deploy and data sync. Copy into `~/.ssh/` (any path is fine; pass `-KeyFile` to the sync script / `-i` to `ssh` if it lives elsewhere).
3. **`out/` data** — lives only on Oracle's disk, never in git. Pull it down after cloning.

**Nothing about the running service is machine-bound** (verified 2026-08-06). The daily email runs on GitHub Actions with its own copy of all 18 secrets; the dashboard runs on Oracle; `out/` lives on Oracle's disk plus the OCI backup. There is **no local Windows Task Scheduler job** — confirmed absent. Moving machines costs you local dev + manual-deploy access only. **The old machine can be wiped without stopping anything.**

Prerequisites on the new box: Git, Python 3.11+ (local dev runs 3.13, CI runs 3.11 — either is fine), and **KeePassXC** (`keepassxc.org`) if you're restoring secrets from the vault rather than copying them across — the `.kdbx` is just an encrypted file and nothing else can open it.

**The repo is private**, so a fresh machine must authenticate to GitHub as `AdamMooo` *before* the clone will work — `gh auth login` (GitHub CLI, easiest) or a PAT / SSH key. A bare `git clone` on an unauthenticated box fails with a confusing "repository not found", not a permission error.

Turnkey on the new box:

```powershell
git clone https://github.com/AdamMooo/vol-diagnostics
cd vol-diagnostics
python -m venv .venv; .venv\Scripts\activate; pip install -r requirements.txt
# then: drop .env into the repo root, and vol-diagnostics.key(.pub) into ~\.ssh\
#   (copy from old machine, or export both from the KeePassXC vault — see below)
.\scripts\sync-from-oracle.ps1     # pulls Oracle's out/ down (needs the SSH key)
streamlit run app.py
```

Verify the move before trusting it — all four should pass:

```powershell
pytest engine/tests                      # expect 483 passed
python -m engine.run_gex --ticker SPY    # network + CBOE feed reachable
python -m engine.run_daily --dry-run     # full pipeline, writes HTML, sends nothing
python -m engine.health_check            # out/ freshness after the Oracle sync
```

Then confirm SSH works (`ssh -i <key> ubuntu@40.233.113.63 "echo ok"`) — that is the one credential the clone can't prove on its own. Deploying from the new box is identical to the Deploy section below; only the `-i` key path is machine-specific.

Note `.env` permissions do not carry over a copy — on Windows it inherits the new folder's ACL. Nothing reads it but you, but don't drop it in a synced/shared folder.

(Standing intent: git-crypt would fold the `.env` step into `git clone` + unlock — see auto-memory `git-crypt-all-projects-decision`; not set up, and the KeePassXC vault now covers the same need.)

### If this machine is gone (nothing to copy from)

Only **two** things live outside git and cannot be reconstructed by a clone: `.env` and `~/.ssh/vol-diagnostics.key`.

**Current backup (2026-08-04):** both live inside a **KeePassXC vault** — `vol-diagnostics-secrets.kdbx` — stored on Adam's personal **Google Drive**. It holds two entries (`.env` and the SSH key) as encrypted attachments. **Restore on a new machine:** install KeePassXC (free, `keepassxc.org`) → open the `.kdbx` from Drive → master passphrase → export the `.env` attachment to the repo root and the key to `~/.ssh/vol-diagnostics.key`. The vault's master passphrase is the one thing NOT stored digitally — if it's lost, the vault is unrecoverable, so the regeneration paths below are the fallback.

If instead you're starting from scratch (no vault, no copies), regenerate them:

1. **`.env`** (secrets). Regenerable if lost, one by one: Gmail **App Password** (Google Account → Security → App Passwords); OCI **Customer Secret Key** and **API signing key** (OCI console → My Profile → Customer Secret Keys / API Keys → generate new, delete old); all OCIDs / namespace / subnet / image / AD are readable from the OCI console any time. `.env.example` lists every key with where-to-find notes.
2. **`~/.ssh/vol-diagnostics.key`** (Oracle SSH). If lost you're locked out of the running instance over SSH — generate a new keypair, add the public key via the OCI console (Instance → Console connection / Cloud Shell), then update the GitHub `ORACLE_SSH_KEY` secret. The `.pub` re-derives from the private key: `ssh-keygen -y -f vol-diagnostics.key`.

**Resilience note:** losing this laptop does **not** stop the product. The daily email pipeline runs on GitHub Actions with its own copy of all 18 secrets, and `out/` lives on Oracle's disk plus the OCI backup. A dead laptop costs you local dev + manual-deploy access, not the running service or the data.

## Deploy (Oracle)

Pushing to `main` does **not** update the live site — Oracle only updates when you SSH in and pull. Run this after every push you want live:

```
ssh -i C:\Users\AdamMorris\.ssh\vol-diagnostics.key ubuntu@40.233.113.63 "cd ~/vol-diagnostics && git pull && docker compose up -d --build"
```

Same command on any machine — only the `-i` key path is machine-specific (copy the key there, or point at wherever it lives on that box). IP is Oracle's reserved Always-Free address for this instance, stable unless the instance itself is recreated.

**Never** chain this with `docker compose down` or `systemctl restart docker` in the same SSH call — that combo hard-locked the 1-vCPU/1GB box once (2026-07-22), requiring an OCI console reboot. Run the pull+build line on its own, watched in the foreground.

Site: https://40.233.113.63.nip.io

## Constraints

- **No predictive claims (current dashboard/email surfaces only):** descriptive of current environment + historical analog only. A predictive/prescriptive modeling track is the intended next milestone (see project hub) — this constraint governs the existing diagnostics surfaces, not that future work.
- **Interpretability first:** conditional base rates primary, no hidden scoring or weighting.
- **Strategy menu:** covered call, cash-covered put, collar, short straddle. Dispersion out of scope.
- **No new signals (dashboard/email surfaces):** six signals + fragility composite locked. Sole-owner project now (no external team gate) — the discipline that stays is self-imposed statistical validation (multiple-testing correction, out-of-sample checks) before any new signal ships, not organizational sign-off.
- **Windows paths:** use pathlib or `os.path.join` throughout.
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
