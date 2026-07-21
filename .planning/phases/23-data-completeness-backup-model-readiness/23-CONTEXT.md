# Phase 23: Data Completeness, Backup & Model-Readiness Audit - Context

**Gathered:** 2026-07-21
**Status:** Ready for planning — all 3 slices (gap-monitoring, backup/restore, model-readiness) discussed. Note D-10: exact depth-target numbers are explicitly deferred to research/planning with stated rationale, not locked here.

<domain>
## Phase Boundary

This phase merges what were three separate v5.0 phases (old 23/24/25) into one integrated data-layer pass:

1. **Gap detection** — an operator (Adam) can see, for each ticker (SPY/QQQ/IWM) × series (`gex_snapshots`, `surface_history`, `vol_index`, `oi_history`), whether data is complete or has gaps — without manually opening parquet files. Detection/reporting only: no backfill, no auto-remediation, no new UI surface beyond what's decided below.
2. **Backup & restore** — `out/` parquet stores survive loss of the single Oracle VM: automated off-VM backup + a documented, tested restore path.
3. **Model-readiness audit** — a written spec defines the minimum depth/schema each series needs before a predictive/prescriptive model could be built on it, and current data is measured against that bar (this slice reuses the gap-detection/session-counting logic from #1).

Merged 2026-07-21 because all three sit on the same "make the data trustworthy before modeling" arc and #3 already depended on #1 — planning/executing as one phase avoids an artificial seam. See `.planning/ROADMAP.md` Phase 23 for the full merged success criteria (12 items, one set per sub-goal above).

</domain>

<decisions>
## Implementation Decisions

### Where gaps surface
- **D-01:** Gap findings surface via the existing GitHub Actions `--strict` gate only (`.github/workflows/daily-report.yml` already runs `python -m engine.health_check --strict` daily). No dashboard panel, hidden or public.
  - Rationale (Adam's call after weighing it): the dashboard is now public (password gate removed, per CLAUDE.md). A visible "our collection has gaps" panel would broadcast internal pipeline health to any visitor. GH Actions failures are already private (visible only in the Actions tab / failure notification to the repo owner) and already fail loudly — reuse that channel instead of building new UI.

### Build approach — extend, don't duplicate (Claude's discretion, confirmed via "use your judgment")
- **D-02:** Extend `engine/health_check.py` rather than write a separate gap-audit script. It already has the NYSE-calendar-aware "expected session" logic (`_last_expected_session()`) and is already wired into the daily `--strict` CI gate — a second parallel tool would duplicate that plumbing and risk drifting out of sync.
- **D-03:** Extend coverage from 2 series (`surface_history`, `gex_snapshots`) to all 4 (`vol_index`, `oi_history` added) across SPY/QQQ/IWM.

### Gap definition — full history, not just tail (Claude's discretion)
- **D-04:** Today's `check_health()` only compares the *latest* available date per series against the expected session — a tail-freshness check. It would NOT catch a session that went silently missing in the middle of history (e.g. a scheduler failure in June that's since self-healed). ROADMAP's Phase 23 success criteria explicitly requires catching "a known historical gap" — this requires a full-history scan (walk the NYSE session calendar across the store's full date range per series/ticker, not just check the max date), in addition to the existing tail check.

### vol_index gap semantics (Claude's discretion)
- **D-05:** `vol_index` (VIX/VXN/RVX/VIX9D/VIX3M/VVIX in `out/vol_index/*.parquet`) is CBOE-published historical CSV data, not driven by our own daily chain-collection run — a missing session there most often means CBOE didn't publish (holiday, data outage) rather than our fetch failing. Treat a missing vol_index session as "no data expected" only when it doesn't correspond to a valid NYSE trading day still expected to have OI/surface data captured that day; otherwise flag it the same as the other 3 series. The researcher/planner should verify this against `engine/data/vol_index.py`'s actual fetch/store logic rather than treating this as final — it's a starting assumption, not a locked spec.

### Backup destination
- **D-06:** Back up `out/` to Oracle Cloud Object Storage (Always Free tier, 10GB), under the same Oracle account already hosting the VM. Chosen over a GitHub-based destination (Release asset / separate repo) because it's independent of the VM (VM loss doesn't lose the bucket), needs no new vendor/API key, and matches the project's established "free tier, no new auth surface" pattern (CBOE, FRED, yfinance are all the same shape).
  - Researcher/planner must confirm exact Object Storage setup (bucket creation, IAM policy, `oci` CLI or `boto3`-compatible S3 API access) against `.planning/notes/ORACLE-CLOUD-SETUP.md` and the existing `${{ secrets.ORACLE_SSH_KEY }}` auth pattern in `.github/workflows/daily-report.yml` — likely a new OCI credential secret, not reusing the SSH key.

### Backup mechanism & restore (Claude's discretion)
- **D-07:** Extend the existing `.github/workflows/daily-report.yml` run rather than add a second scheduled job — it already touches `out/` (rsync down/up) every weekday run, so pushing a copy to Object Storage as one more step in that same job avoids a second cron surface to maintain.
- **D-08:** Restore path must be a runnable script (not just written prose) per ROADMAP success criterion #7 ("a test restore (dry run) successfully reconstructs a working `out/` tree") — e.g. `scripts/restore-from-backup.sh` or `.ps1`, mirroring the existing `scripts/migrate-data.ps1` / `scripts/update.sh` pattern already in the repo.

### Model-ready depth/schema spec
- **D-09:** Spec lives in a new standalone doc (e.g. `.planning/notes/MODEL-READY-DATA-SPEC.md`), linked from PROJECT.md rather than inlined into it — satisfies ROADMAP success criterion #12 ("discoverable from PROJECT.md/STATE.md") without growing the already-long PROJECT.md body.
- **D-10 (flagged for research, not locked):** The actual minimum-depth-per-series numbers are a quant/methodology question, not a UI or infra one — e.g. how many sessions of `surface_history`/`oi_history` are enough depends on what kind of model comes next (a GARCH-style vol model has different minimum-sample-size needs than a percentile-ranking lookup). Per this project's Learning Mode convention, whoever plans/executes this slice should ground each depth target in a stated rationale (a named estimator's typical sample-size requirement, or an explicit "descriptive only, no minimum" call) rather than picking round numbers — Adam has not pre-decided these numbers and expects to be walked through the reasoning, not handed a finished table.

### Claude's Discretion
- Exact report format (CLI table vs. JSON block vs. both) — left to planner/researcher; existing `check_health()` already supports both `--json` and human-readable, extend that pattern rather than inventing a new one.
- Whether full-history scan runs on every `--strict` invocation (adds runtime cost to the daily gate) or as a separate periodic/manual command — left to planner to weigh against the daily gate's runtime budget.
- Backup cadence beyond "runs with the existing daily job" (e.g. retention/pruning policy for the Object Storage bucket) — left to planner.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — DATA-01, DATA-02, BACKUP-01, BACKUP-02, SCHEMA-01, SCHEMA-02 (this phase's requirements, merged)
- `.planning/ROADMAP.md` — Phase 23 section (goal, 12 success criteria, depends-on)

### Existing health-check tool (extend, don't duplicate)
- `engine/health_check.py` — current tail-freshness checker; `check_health()`, `_last_expected_session()` are the extension points
- `engine/tests/test_data_health.py` — existing test coverage for `check_health()`; new tests extend this file
- `.github/workflows/daily-report.yml` (line ~88: `python -m engine.health_check --strict`) — the CI gate this phase extends AND the job the backup step (D-06/D-07) folds into; do not change its invocation surface without checking this still fails the build correctly

### Data stores this phase must cover
- `engine/data/validation.py` — `save_snapshot()`, `load_history()` for `out/gex_snapshots.parquet`
- `engine/data/surface_history.py` — `list_available_dates()`, `nth_trading_day_back()` for `out/surface_history/surface_{ticker}.parquet`
- `engine/data/vol_index.py` — fetch/store logic for `out/vol_index/{VIX,VXN,RVX,VIX9D,VIX3M,VVIX}.parquet` (read this before finalizing D-05 above)
- `engine/data/oi_history.py` — `save_oi_snapshot()` for `out/oi_history/oi_{ticker}.parquet`
- `engine/data/store.py` — `atomic_to_parquet()` shared write helper

### Backup/restore & deployment context
- `.planning/notes/ORACLE-CLOUD-SETUP.md` — current Oracle account/VM setup; read before adding Object Storage (D-06) so the new backup credential follows the same conventions as the existing SSH-key secret
- `scripts/migrate-data.ps1`, `scripts/update.sh` — existing repo scripts; restore script (D-08) should match their style/location
- `docker-compose.yml`, `Dockerfile` — how `out/` is volume-mounted on the Oracle VM today; relevant to how a restore rehydrates it

No other external specs beyond the above — requirements fully captured in `.planning/REQUIREMENTS.md`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `engine/health_check.py:_last_expected_session()` — NYSE-calendar-aware "what session should exist by now" logic; reusable as-is for the tail check, and the pattern (walk `pandas_market_calendars` schedule) is the basis for the new full-history scan.
- `engine/health_check.py` already supports `--json` and `--strict` CLI flags — extend rather than replace this interface so the existing GH Actions step keeps working with minimal changes.

### Established Patterns
- Fail-soft, ticker-independent checks: each ticker/series is checked independently and reported per-ticker (`results[ticker] = {...}`) rather than aborting on first failure — carry this into the 4-series version.
- All persistence is flat parquet files under `out/`, one store per series (some per-ticker like `surface_history`/`oi_history`, some single-file like `gex_snapshots.parquet`, some per-index like `vol_index`) — the gap scanner needs to handle both shapes.

### Integration Points
- `.github/workflows/daily-report.yml` — the single existing invocation point (`--strict` gate); this is the only surface this phase wires into per D-01.
- No dashboard (`app.py`) integration per D-01 — do not add a gap-status panel there.

</code_context>

<specifics>
## Specific Ideas

No specific UI/format requirements from discussion — Adam deferred format/implementation details to planning ("use your judgment"). Hard constraints volunteered directly: keep gap-monitoring off the public dashboard; the model-ready depth numbers must come with stated quant rationale, not be picked arbitrarily (see D-10).

</specifics>

<deferred>
## Deferred Ideas

None raised outside phase scope during this discussion.

### Reviewed Todos (not folded)
- `2026-05-11-v3-2-pre-distribution-hardening.md` — matched at low relevance (score 0.2, keyword "gaps") during todo cross-reference, but its content is dead-code/stale-reference cleanup, earmarked for Phase 24 (CLEAN-01, formerly Phase 26 before the 2026-07-21 renumber) per STATE.md. Not folded here — wrong phase.

</deferred>

---

*Phase: 23-data-completeness-backup-model-readiness*
*Context gathered: 2026-07-21 (gap-monitoring); backup/restore + model-readiness slices added same session*

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
**Phase siblings:**
- [[_planning/vol-diagnostics/phases/23-data-completeness-backup-model-readiness/23-DISCUSSION-LOG|23-DISCUSSION-LOG]]

<!-- LINKS:END -->
