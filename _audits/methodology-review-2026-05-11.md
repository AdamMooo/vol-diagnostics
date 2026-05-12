---
type: audit
date: 2026-05-11
status: complete
supersedes: gex-prep-audit-2026-05-07
audience: pre-distribution gate (before sharing GEX email externally)
---

# Methodology & Presentation Review — 2026-05-11

Pre-distribution audit for the GEX daily email + dashboard. Builds on the
[[_audits/gex-prep-audit-2026-05-07|May-7 pre-demo audit]]; folds in changes
made 2026-05-10 → 2026-05-11 (email rebuild, scheduled task hardening, send
guard, and the three enhancement rolls below).

## Scope

- SPY, QQQ, IWM only — the three tickers where the standard dealer-positioning
  convention (long calls, short puts) is empirically defensible.
- Email pipeline (`gex/run_daily.py` → `report.py` → Outlook COM).
- Streamlit dashboard (`streamlit_app.py`).
- Snapshot store + event-study scaffolding (`gex/validation.py`).

## What was implemented this session (2026-05-11)

| Change | File | Status |
|---|---|---|
| Stacked per-ticker email cards (replaced 8-col wide table) | `gex/report.py` | done |
| Removed forced light-mode color scheme; cards now theme-adaptive | `gex/report.py` | done |
| Email width 560 → 720px; padding tuned for Outlook reading pane | `gex/report.py` | done |
| `--send` flag required to send mail; `python -m gex.run_daily` dry-runs without it | `gex/run_daily.py` | done |
| Scheduled task arg updated to `-m gex.run_daily --send` | `runners/gex_daily.ps1` | done |
| Weekly Mon-Fri trigger (was `-Daily`); path `options-quant` → `gamma-omm` | `runners/gex_daily.ps1` | done |
| Outlook auto-launch shortcut in Startup folder | (Windows Startup) | done |
| PSReadLine history scrubbed of unsafe `run_daily` recall lines | (one-shot cleanup) | done |
| Wall cluster (top-3 within ±2% of max, GEX-weighted center) | `gex/analytics.py` | done |
| Wall concentration % (cluster |GEX| / total side |GEX|) | `gex/analytics.py` | done |
| Distance-to-flip % (linear projection from profile slope at spot) | `gex/analytics.py` | done |
| Expected 1-day σ from IV30 alongside IV30 | `gex/report.py` | done |
| Methodology legend in footer (regime, walls, range, dist-to-flip) | `gex/report.py` | done |
| `event_study()` encoding bug fix (Windows cp1252 ≥ char) | `gex/validation.py` | done |

## Methodology — current status

### Solid

- **Sign convention** — calls +1, puts −1, applied consistently in
  `exposure_engine.compute_gex/vex/chex`. Universe gated to SPY/QQQ/IWM where
  the long-call/short-put dealer convention is defensible.
- **ZGL** — first sign change of cumulative profile, linear interpolation
  (`analytics._find_zero_crossing`). Matches commercial-vendor methodology.
- **0DTE exclusion** — `data_loader` locks `min_dte=1`; documented in footer.
  Diverges from full-chain vendors by design (BS singularities + 0DTE
  structural-short-gamma noise per Dim/Eraker/Vilkov 2024). Defensible.
- **Wall identification** — upgraded today from single-max-strike to
  GEX-weighted cluster center of top-3 strikes within ±2% of max. Concentration
  ratio surfaced so reader can tell whether a wall is real or noisy.

### Accepted limitations (footnote, not blocker)

- **Hardcoded `r = 0.05`** in `greeks_engine.py:25,54,76` and
  `exposure_engine.py:58,74`. Real ~4.3%. Vanna/charm at 180+ DTE off by ~15%.
  P0 carryover from May-7. Acceptable as footnote; near-month-dominated chains
  are barely affected.
- **Hardcoded `q = 0`** dividend yield. SPY ~1.2%, QQQ ~0.5%, IWM ~1.4%
  ignored. 5-10% vanna error at 90+ DTE. P1 carryover; low impact.
- **OI is T-1** (CBOE overnight snapshot). Greeks 15-min delayed. Documented.
- **Filter impact unquantified** — `min_oi=100, max_iv=3.0` drop ratio not
  logged or surfaced.

### Open ship-blockers (audit identifies — partially actioned)

- Cluster walls — **done today**.
- **Snapshot timestamp in email header** — still only shows date. CBOE
  response timestamp should appear: `Snapshot 2026-05-11 16:15 ET · OI T-1 ·
  Greeks 15-min delayed`. Needs to thread `snapshot.as_of` through `compute` →
  summary → email header.
- **Methodology caveat above the cards, not just in footer.** Current
  footer is 10px gray; gets skimmed. Should be a one-line banner immediately
  below the date header, plain text, normal-size.

## Presentation — gaps remaining

| Gap | Why it matters | Effort |
|---|---|---|
| Snapshot timestamp in header | "How fresh is this?" is the first question | 30 min |
| Methodology banner above cards | Pre-empts "why doesn't this match Barchart?" | 15 min |
| GEX percentile vs own history | Answers "is +$3B large or normal?" | Blocked on ≥30 days of snapshots |
| Gamma profile slope quantification | "How sharp is this regime?" — currently visual only | 30 min |
| Filter-drop transparency | "What chain did you actually run on?" | 20 min |
| VEX/CHEX one-line legend | Currently shown without interpretation guidance | 5 min (footer-only) |

## Backtest readiness

- **Sample size:** ~5 trading days of snapshots as of 2026-05-11 (parquet store
  started ~2026-05-06). Need ≥30 for any inference.
- **Earliest meaningful backtest:** ~late June 2026.
- **Honest current framing:** "Validation framework ready; results unlock at
  N≈30 (~6 weeks). No event-study output is surfaced anywhere — nothing false
  to retract."
- **No backfill path** without paid feed (ORATS / Polygon). CBOE
  delayed-quotes endpoint serves current snapshot only.
- **Pre-registered metric (recommend):** next-day realized intraday range
  conditional on regime — most direct test of dealer-hedging stabilization
  hypothesis. Hit-rate of ZGL pin is a secondary metric.

## Risk summary

| Risk | Severity | Status | External-share blocker? |
|---|---|---|---|
| Hardcoded `r=0.05` vs actual ~4.3% | Medium | P0 deferred | No (footnote) |
| `q=0` dividend assumption | Low–Medium | P1 deferred | No |
| Single-strike wall | ~~High~~ | **fixed today** | No (resolved) |
| Snapshot timestamp not visible | High | Open | **Yes** |
| Methodology caveat buried in footer | High | Open | **Yes** |
| OI filter impact unquantified | Low | Deferred | No |
| Event-study sample (N≈5) | Low | By design | No (forward-looking) |
| No percentile context | Low | By design | No (early days) |

**Pre-distribution ship-blockers remaining:** 2 (snapshot timestamp + caveat banner). Estimated ~45 min total.

## Recommended next phase

Open as v3.2 — "Pre-Distribution Hardening" (see ROADMAP). Bundle the two
remaining ship-blockers with the two highest-value presentation gaps
(profile-slope quantification, filter-drop transparency) and ship in one PR
before any external send.

## Related

- [[gex-prep-audit-2026-05-07|May-7 pre-demo audit]] (baseline)
- [[gamma-omm/gamma-omm|Gamma OMM hub]]
- [[gamma-omm/.planning/ROADMAP|ROADMAP]]
