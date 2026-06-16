---
phase: 16-vrp-percentile
verified: 2026-06-16T00:00:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 16: VRP Percentile Verification Report

**Phase Goal:** The PM sees today's VRP (vol-index implied vol − RV20 realized) for SPY/QQQ/IWM together with its percentile rank against its own history, computed from ONE internally-consistent vol-index series, lookback labeled, in BOTH the Streamlit dashboard and the daily email via the shared canonical card. Descriptive only — raw labeled percentile, no scoring, no categorical label.
**Verified:** 2026-06-16
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | VRP-01 — PM sees today's VRP (vol-index implied − RV20) per index | ✓ VERIFIED | `compute.py:151-153` sets `summary["vrp"]` from `vrp_percentile(ticker)["vrp"]`; surfaced as VRP CardField `card_model.py:268-272`. SPY/QQQ/IWM mapped via `TICKER_VOL_INDEX` `config.py:191`. |
| 2 | VRP-02 — VRP ranked as percentile vs own history, lookback explicitly labeled | ✓ VERIFIED | `vrp_history.py:88` `percentileofscore(window, today, kind="rank")`; `_fmt_vrp` `card_model.py:95-112` renders "Nth %ile · 252-session lookback" reading `config.VRP_PERCENTILE_LOOKBACK`, never hard-coded. |
| 3 | VRP-03 — Percentile from ONE consistent series; snapshot IV30 never mixed; cold-start labeled never silent | ✓ VERIFIED | `vrp_history.py:82` series = `vi_close − rv*100`; today's value `iloc[-1]` of same series (line 86). `snapshot.iv30` only at `compute.py:110` (IV30 card), never feeds VRP. No `compute_vrp` import remains. Cold-start labels actual `n` (`_fmt_vrp:110-111`). |
| 4 | LOCKED — displayed scalar switched to vol_index − RV20 (scalar + percentile one series) | ✓ VERIFIED | Old snapshot-IV30 VRP block removed from `compute.py`; scalar now `vrp_pct_res["vrp"]` (line 152). report.py has zero independent vrp/iv30 logic (grep empty). |
| 5 | PAR-01 seam — single VRP CardField reaches BOTH renderers, no per-renderer edit, no I/O in builder | ✓ VERIFIED | `build_card_fields` called at `report.py:102` AND `streamlit_app.py:159`; VRP field built inside it once. `_fmt_vrp` reads only precomputed values, no I/O. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `gex/vrp_history.py` | VRP-03-clean percentile engine | ✓ VERIFIED | 89 lines; single-series build, isolated yfinance fetch, None-dict failure paths, never raises. |
| `gex/config.py` | TICKER_VOL_INDEX + VRP_PERCENTILE_LOOKBACK | ✓ VERIFIED | `config.py:191` map SPY→VIX/QQQ→VXN/IWM→RVX; `:194` lookback=252. |
| `gex/compute.py` | precompute vrp/vrp_pct/vrp_pct_n, 400d widen | ✓ VERIFIED | `:151-155` precompute; `:23` fetch default widened to 400d. |
| `gex/card_model.py` | `_fmt_vrp` + VRP CardField | ✓ VERIFIED | `:95-112` formatter (no I/O); `:268-272` field at index 8 after Skew. |
| `gex/tests/test_vrp_history.py` | engine tests | ✓ VERIFIED | 6 substantive tests incl. VRP-03 isolation + cold-start + 3 failure paths. |
| `gex/tests/test_card_model.py` | card tests | ✓ VERIFIED | TestVRPCardField: full-lookback, cold-start, fallback, scalar-only, sign. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| compute_ticker | vrp_percentile | direct call | ✓ WIRED | `compute.py:20` import, `:151` call |
| build_card_fields | gex/report.py | import + call | ✓ WIRED | `report.py:17,102` |
| build_card_fields | streamlit_app.py | import + call | ✓ WIRED | `streamlit_app.py:11,159` |
| vrp_percentile | load_vol_index / compute_rv20 | composition | ✓ WIRED | `vrp_history.py:18-19,58,73` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| VRP CardField | summary vrp/vrp_pct/vrp_pct_n | vrp_percentile → load_vol_index (CBOE parquet) + yfinance closes | Yes (real CBOE vol-index store + yfinance) | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase tests pass | `pytest test_vrp_history.py test_card_model.py -q` | 38 passed | ✓ PASS |
| compute imports cleanly | `from gex.compute import compute_ticker` | (covered by suite) | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| VRP-01 | 16-02 | PM sees today's VRP per index | ✓ SATISFIED | Truth 1 |
| VRP-02 | 16-01/02 | VRP percentile vs own history, labeled | ✓ SATISFIED | Truth 2 |
| VRP-03 | 16-01/02 | One consistent series, IV30 never mixed, cold-start labeled | ✓ SATISFIED | Truth 3 |

### Anti-Patterns Found

None in VRP code. No TODO/FIXME/placeholder, no VVIX/categorical/forecast creep, no hard-coded lookback.

### Out-of-Scope Pre-Existing Failures (NOT a phase gap)

6 failures in `gex/tests/test_run_daily_pngs.py` — stale `mock.patch` target `gex.run_daily.plot_iv_change_surface` (attribute removed pre-Phase 16). Touches no VRP code. Recorded per critical-check 5; does not fail this phase. Full suite: 205 passed, 6 failed.

### Gaps Summary

None. All five must-haves verified against the codebase. VRP-03 single-series invariant confirmed at source (series and today's scalar share `vi_close − rv*100`; snapshot.iv30 path isolated to the IV30 card). PAR-01 seam confirmed reaching both renderers through one builder. Cold-start and failure paths return labeled/None values, never NaN, never raise.

---

_Verified: 2026-06-16_
_Verifier: Claude (gsd-verifier)_

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/16-vrp-percentile/16-01-PLAN|16-01-PLAN]]
- [[_planning/gamma-omm/phases/16-vrp-percentile/16-01-SUMMARY|16-01-SUMMARY]]
- [[_planning/gamma-omm/phases/16-vrp-percentile/16-02-PLAN|16-02-PLAN]]
- [[_planning/gamma-omm/phases/16-vrp-percentile/16-02-SUMMARY|16-02-SUMMARY]]
- [[_planning/gamma-omm/phases/16-vrp-percentile/16-CONTEXT|16-CONTEXT]]
- [[_planning/gamma-omm/phases/16-vrp-percentile/16-RESEARCH|16-RESEARCH]]
- [[_planning/gamma-omm/phases/16-vrp-percentile/deferred-items|deferred-items]]

<!-- LINKS:END -->
