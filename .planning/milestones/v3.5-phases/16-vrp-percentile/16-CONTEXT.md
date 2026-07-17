# Phase 16: VRP Percentile - Context

**Gathered:** 2026-06-16
**Status:** Ready for planning
**Source:** Discussion during plan-phase (research-informed)

<domain>
## Phase Boundary

Surface today's VRP (vol-index implied vol − RV20 realized) for SPY/QQQ/IWM together
with its percentile rank against its own history, in BOTH the Streamlit dashboard and
the daily email, via the shared canonical card. Descriptive only — raw labeled
percentile, no scoring, no categorical label.
</domain>

<decisions>
## Implementation Decisions (LOCKED)

### VRP basis — single consistent series
- The displayed VRP scalar on the card SWITCHES from `snapshot.iv30 − RV20` to
  `vol_index − RV20`. Card scalar AND its percentile both use the vol-index series
  (VIX/VXN/RVX − RV20) so the two numbers cannot drift. Confirmed with user 2026-06-16.
- This changes a value the daily email already renders (PAR-01 seam) — the email's VRP
  scalar updates to the vol-index basis too. Acceptable and intended.
- The percentile being vol-index-based is non-negotiable per VRP-03; the snapshot-IV30
  path at `compute.py:142` must NEVER feed the percentile history.

### Ticker → vol-index map
- SPY→VIX, QQQ→VXN, IWM→RVX. Add a `TICKER_VOL_INDEX` map to `config.py` (none exists).

### Lookback
- `VRP_PERCENTILE_LOOKBACK = 252` in `config.py` (project's magic-numbers-in-config convention).
- Cold-start (VRP-03): when fewer than the lookback sessions exist, omit the percentile or
  label the actual available count — never silently compute on a thin sample. Reuse the
  existing "needs ≥N sessions" gating pattern.

### Historical VRP series construction
- Historical VRP(date) = historical_vol_index(date) − historical_RV20(date).
- Vol-index history: `gex/vol_index.py` store (full history available — no data blocker).
- RV20 history: widen the yfinance close fetch in `compute.py:_fetch_spot_history_yf`
  from 35 days to ~400d so a 252-point rolling RV20 series can be built. RV20 via existing
  `compute_rv20`.

### Percentile method
- Reuse `scipy.stats.percentileofscore` exactly as `streamlit_app.py:403` already does for skew.
- Label as e.g. "74th percentile, 252-day lookback".

### Surfacing
- Add the percentile as a `CardField` in `build_card_fields()` (gex/card_model.py) so it
  reaches email + dashboard with no per-renderer edit. Value must be PRECOMPUTED in
  `compute_ticker` (no I/O in the pure card builder).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/phases/16-vrp-percentile/16-RESEARCH.md` — minimal file-touch table, VRP-03 trap, verified data paths
- `gex/vol_metrics.py` — existing `compute_rv20`, `compute_vrp`, `vrp_headline` (reuse, do not rebuild)
- `gex/vol_index.py` — `load_vol_index` (VIX/VXN/RVX history store)
- `gex/compute.py` — `compute_ticker`, `_fetch_spot_history_yf` (widen to ~400d), VRP-03 trap at line ~142
- `gex/card_model.py` — `CardField`, `build_card_fields()` (PAR-01 seam)
- `gex/config.py` — add `TICKER_VOL_INDEX`, `VRP_PERCENTILE_LOOKBACK`
- `.planning/REQUIREMENTS.md` — VRP-01/02/03 + out-of-scope "Mixing snapshot IV30 into the percentile series"
</canonical_refs>

<specifics>
## Specific Ideas

- One number, not two: scalar and percentile share the vol-index series.
- percentileofscore usage already proven at streamlit_app.py:403 — mirror it.
</specifics>

<deferred>
## Deferred Ideas

- Full email/dashboard 3-page parity reorg — Phase 18 (only flag the card seam here).
- Term-structure regime — Phase 17.
- Expected-move + 25Δ butterfly axes — separate new phase (added to roadmap after Phase 16 planning).
</deferred>

---

*Phase: 16-vrp-percentile*
*Context gathered: 2026-06-16 during plan-phase*

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/16-vrp-percentile/16-RESEARCH|16-RESEARCH]]

<!-- LINKS:END -->
