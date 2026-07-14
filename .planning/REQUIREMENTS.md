# Requirements — v3.5 Index Vol-Context Rebuild

*Last updated: 2026-06-04 — roadmap phases 15–18 assigned*

## Milestone Goal

Re-aim the dashboard at the index income-sleeve PM (covered-call / put-write overlays on SPY/QQQ/IWM). Lead with the two metrics that change an option-writing decision — VRP percentile and VIX term-structure regime — and reorganize surfaces + GEX beneath them. All data is free (CBOE vol-index CSVs + yfinance closes). Trustworthy for index overlays only; deliberately not extended to single-name writing (no free historical IV).

**Interpretability note:** percentiles and term ratios are shown as raw, labeled numbers — no hidden scoring, weighting, or categorical regime label (the non-stationary-floor trap that retired the GEX regime badge).

**Consistency note:** the page-1 snapshot must render numbers identical to the daily email via the shared canonical card — the email and dashboard cannot drift.

---

## Requirements

### Vol-Index Data Layer (VIDX)

- [x] **VIDX-01** — System fetches and caches the CBOE vol-index daily history (VIX/VXN/RVX, plus the VIX9D/VIX3M term siblings that exist) from the free `cdn.cboe.com` CSV endpoints. Underlying closes for realized vol continue to come from the existing yfinance path.
- [x] **VIDX-02** — Vol-index access is isolated in one module mirroring the `data_loader.py` pattern, so the source is Bloomberg-swappable without touching downstream metric code.

### VRP Percentile (VRP)

- [x] **VRP-01** — PM sees today's VRP (vol-index implied vol − RV20 realized) for each index.
- [x] **VRP-02** — PM sees today's VRP ranked as a percentile against its own history, with the lookback window explicitly labeled.
- [x] **VRP-03** — The percentile is computed from one internally-consistent series (the vol index for both today's reading and the history), never mixing the vol index with the live snapshot IV30.

### Term-Structure Regime (TERM)

- [x] **TERM-01** — PM sees the SPY term-structure state from VIX9D / VIX / VIX3M as a raw ratio (contango vs backwardation), with no hidden scoring or categorical label.
- [x] **TERM-02** — QQQ/IWM display whichever term points CBOE publishes for them, degrading gracefully to the 30-day level (VXN/RVX) when short/long-dated siblings are absent — no fabricated term structure.

### Convexity & Expected Move (EM / SHAPE)

- [x] **EM-01** — PM sees the front-expiry implied expected move as a ±% (and/or ± price) range, computed from the ATM straddle, with the expiry/DTE explicitly labeled. Descriptive only — no trade prescription.
- [x] **SHAPE-01** — PM sees the front-month 25Δ butterfly — ½(25Δput_iv + 25Δcall_iv) − ATM_iv — beside the existing 25Δ risk reversal, labeled, with percentile context vs its own history where enough sessions exist (reusing the Phase 16 percentile + cold-start gating). No realized cone, RND, put/call ratio, or VVIX.

### Dashboard Reorg (VIEW — continues VIEW-05)

- [x] **VIEW-06** — The dashboard is organized into three pages: (1) VRP + term structure + snapshot, (2) surfaces, (3) GEX. Surfaces and GEX are retained, only demoted.
- [ ] **VIEW-07** — The page-1 snapshot is simplified for at-a-glance readability (the lead PM-facing view).
- [x] **CUT-02** — (absorbed from v3.2 backlog) The 3D vol surface is demoted off page 1 into the surfaces page.

### Email Parity (PAR)

- [ ] **PAR-01** — The page-1 snapshot renders numbers identical to the daily email by extending the shared canonical card (Phase 12), so the two surfaces cannot drift.

### Accumulation Gating (GATE — carried forward from v3.4 Phase 14)

- [ ] **GATE-01** — Dashboard UI elements that require accumulated history (percentiles, evolution small-multiples, sparklines, multi-session charts) are hidden behind an explicit "needs ≥N sessions" guard with a clear caption until enough stored sessions exist. Engines and stores untouched — only the display is gated.
- [ ] **GATE-02** — The email is cold-start clean: history-dependent content is omitted rather than rendered empty/NaN when its required history does not yet exist, and the send never fails on missing history.

---

## Future Requirements (deferred)

- **Conditional base-rate framework (v2.x track)** — environment → historical outcome per strategy; pairs with VRP as the "what do I do" layer. Lives on the separate sleeve-allocation track, surfaced here as the natural next companion to VRP.
- **Single-name VRP/percentile** — blocked on free historical single-name IV (none exists); revisit only with a vendor (ORATS/IVolatility) or ~1yr of accumulated snapshots.
- **Bloomberg data swap** — one-class change; v4.x.

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Single-name vol context | No free historical IV → no trustworthy percentile; PMs use Bloomberg live. Index-overlay decision only. |
| Put/call ratios, VVIX, cross-asset vol indices | Free and available, but noise for an index-writing PM — adding them repeats the flashy-breadth mistake. |
| Categorical regime / contango label with thresholds | Hidden scoring violates the interpretability rule; show raw ratios + percentiles, let the PM judge. |
| New tickers beyond SPY/QQQ/IWM | Vol-index history (VIX/VXN/RVX) only exists for these; dealer convention defensible only here. |
| Predictive / fair-value forecasting | Descriptive-only constraint stands. |
| Mixing snapshot IV30 into the percentile series | Biases the percentile (VIX ≠ SPY-snapshot IV30); ruled out in VRP-03. |

---

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| VIDX-01 | Phase 15 | Complete |
| VIDX-02 | Phase 15 | Complete |
| VRP-01 | Phase 16 | Complete |
| VRP-02 | Phase 16 | Complete |
| VRP-03 | Phase 16 | Complete |
| TERM-01 | Phase 17 | Pending |
| TERM-02 | Phase 17 | Pending |
| EM-01 | Phase 17.1 | Complete |
| SHAPE-01 | Phase 17.1 | Complete |
| VIEW-06 | Phase 18 | Complete |
| VIEW-07 | Phase 18 | Pending |
| CUT-02 | Phase 18 | Complete |
| PAR-01 | Phase 18 | Pending |
| GATE-01 | Phase 18 | Pending |
| GATE-02 | Phase 18 | Pending |

---
---
---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
<!-- LINKS:END -->
