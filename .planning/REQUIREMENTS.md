# Requirements — v3.3 Surface Evolution & Daily Intelligence

*Last updated: 2026-05-29 — milestone v3.3 defined*

## Milestone Goal

Turn the vol surface into an accumulating, trustworthy daily diagnostic: prove the interpolated surface isn't overfit, build the "calculus" of how it moves over time, surface that change in a restructured local dashboard, and deliver it in a clean, formal daily report. Streamlit is LOCAL-only (removed from the live server).

**Foundation-first gate:** every downstream metric reads off the RBF/TPS surface. Phase 8 produces a coverage mask + fit-honesty layer that becomes the single source of truth for "where the surface is real." Phases 9–11 may not compute, display, or email a value in an uncovered grid cell.

---

## Requirements

### Surface Validation (Phase 8 — the gate)

- [x] **VALID-01** — A coverage mask flags every interpolated grid cell that has no nearby real quote (convex-hull / kNN over actual quote locations); unsupported cells render as honest NaN holes, not fabricated IV. The mask is exported as the single source of truth consumed by all downstream phases.
- [x] **VALID-02** — Surface fit quality is reported per ticker: RMSE and max residual (pp) of the RBF fit against the input quotes, persisted daily to the snapshot store.
- [x] **VALID-03** — The `smoothing` parameter is moved out of inline code into `config.py` with a documented sensitivity sweep justifying the chosen value (no unexplained magic number).
- [x] **VALID-04** — Surface-coherence checks (calendar total-variance monotonicity + butterfly convexity) report PASS/FAIL and violation locations as fit-quality QA, computed headless and persisted to the snapshot. They are never a trading signal (on delayed CBOE quotes any arbitrage is untradable) and never auto-repair the surface. No dashboard UI in Phase 8.
- [x] **VALID-05** — The RBF interpolation logic exists as one shared helper (`rbf_grid`) consumed by the surface render, the diagnostics, and the evolution engine — no duplicated interpolation definitions.
- [x] **VALID-06** — Surface coverage % and fit RMS are visible in the Streamlit dashboard so the user can see at a glance whether today's surface is trustworthy.

### Surface Evolution Engine (Phase 9)

- [x] **EVOL-01** — A `surface_evolution` module computes the change between today's surface and a prior baseline, decomposed into four scalars on the masked grid: level (mean ΔIV), rms (total movement), skew-change (put-wing vs call-wing ΔIV), term-change (front vs back ΔIV). The headline baseline is the **N-day rolling mean** of the masked daily surfaces (`IV_today − nanmean_k(masked grids)`), with the comparison mask = today ∩ all N baseline-day masks so no extrapolated cell enters the diff. Point-to-point (today vs a single stored snapshot) is retained for the 3D Δ-surface render and the two-date comparator (VIEW-03).
- [x] **EVOL-02** — The comparison runs at multiple horizons — **5, 10, and 20 trading days back** — with each horizon resolved against actually-stored trading sessions (not calendar arithmetic) and labelled with the real prior date. 1-day is intentionally excluded (mostly expiry-roll + quote noise).
- [ ] **EVOL-03** — Evolution metrics persist to `out/surface_evolution.parquet`, idempotent on (date, ticker, horizon), accumulating forward.
- [ ] **EVOL-04** — Evolution is computed automatically as a non-blocking pass inside `run_daily` after the day's snapshot is saved; a failure here never blocks the email.
- [x] **EVOL-05** — Surface-change is comparable across SPY / QQQ / IWM (cross-ticker view), so divergence (e.g. IWM moving alone) is visible.
- [ ] **EVOL-06** — A backfill routine retro-computes evolution from existing `surface_history` so the dashboard is not empty on first use.

### Dashboard Restructure (Phase 10 — local only)

- [ ] **VIEW-01** — Tabs collapse from 5 to 4; Skew and Term Structure merge into a single tab reframed around the surface calculus.
- [ ] **VIEW-02** — The carry/VRP block, the 25Δ risk-reversal history chart, and the strike-GEX bar charts are removed (data over bar charts).
- [ ] **VIEW-03** — The surface comparison view can compare two stored dates (not only today-live vs a stored date), so the dashboard is useful on accumulated history without a live fetch.
- [ ] **VIEW-04** — A surface-evolution view charts level / rms / skew-change / term-change over time, selectable by horizon.
- [ ] **VIEW-05** — The dashboard uses a restrained, professional palette (no garish colours); coverage holes are shown honestly; the interactive 3D surface is retained here.

### Richer Daily Report (Phase 11)

- [ ] **RPT-01** — PNG export works on the target Windows machine via `kaleido>=1.0,<2.0` + a one-time Chrome fetch; Phase 11 opens with a smoke-test spike before PNG embedding is committed (HTML-artifact attachment is the documented fallback if the spike fails).
- [ ] **RPT-02** — The daily email attaches the surface and ΔIV-surface images as 3D renders consistent with the Streamlit views, using a pinned camera angle so the static frame is readable.
- [ ] **RPT-03** — Report content is prioritised surfaces > put/call walls > OI > gamma; open interest is surfaced as data (currently absent from the email).
- [ ] **RPT-04** — The report reads as a clean, formal business document: restrained palette consistent with the dashboard, no crazy colours, no decorative noise.
- [ ] **RPT-05** — Evolution scalars appear in the report and the narrative leads with the 5-day rolling read (today vs the 5-day mean surface); 1-day is excluded as mostly expiry-roll + quote noise — the same hazard that retired the v3.1 vs-yesterday badge.

---

## Future Requirements (deferred)

- Inline-embedded (`cid:`) email images instead of attachments — requires Outlook COM PropertyAccessor plumbing; plain attachment ships first.
- Bloomberg data swap — one-class change in `data_loader.py`, v4.x.
- Live intraday refresh — CBOE CDN is delayed; real-time needs a paid feed.

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| PCA / factor decomposition of surface change | First 3 factors are exactly the level/skew/term scalars already measured directly; tiny non-stationary sample is noisy + sign-ambiguous. Cut, not deferred. |
| SVI / SSVI / SABR calibration | Fragile per-slice calibration engine for a tradable book; this is a free-data descriptive tool. Verify the surface (no-arb checks), don't re-calibrate it. v4.x at earliest. |
| `kaleido==0.2.1` | Hangs indefinitely on Windows against the installed plotly 6.7. |
| Downgrading plotly to 5.x | Would regress the signed-off 3D surface charts to keep an old kaleido. |
| scikit-learn for cross-validation | RBFInterpolator isn't an sklearn estimator; hand-rolled leave-one-expiry-out is fewer lines. |
| Predictive / "fair value" surface forecasting | Descriptive-only constraint stands. |
| New tickers beyond SPY/QQQ/IWM | Dealer-positioning convention is only defensible for these. |

---

## Traceability

All 22 v1 requirements mapped to exactly one phase. No orphans, no duplicates.

| REQ-ID | Phase | Status |
|--------|-------|--------|
| VALID-01 | Phase 8 | Complete |
| VALID-02 | Phase 8 | Complete |
| VALID-03 | Phase 8 | Complete |
| VALID-04 | Phase 8 | Complete |
| VALID-05 | Phase 8 | Complete |
| VALID-06 | Phase 8 | Complete |
| EVOL-01 | Phase 9 | Complete |
| EVOL-02 | Phase 9 | Complete |
| EVOL-03 | Phase 9 | Pending |
| EVOL-04 | Phase 9 | Pending |
| EVOL-05 | Phase 9 | Complete |
| EVOL-06 | Phase 9 | Pending |
| VIEW-01 | Phase 10 | Pending |
| VIEW-02 | Phase 10 | Pending |
| VIEW-03 | Phase 10 | Pending |
| VIEW-04 | Phase 10 | Pending |
| VIEW-05 | Phase 10 | Pending |
| RPT-01 | Phase 11 | Pending |
| RPT-02 | Phase 11 | Pending |
| RPT-03 | Phase 11 | Pending |
| RPT-04 | Phase 11 | Pending |
| RPT-05 | Phase 11 | Pending |

**Coverage:** 22/22 mapped ✓

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
