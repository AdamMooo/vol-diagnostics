# Phase 25 — Methodology Audit Record

**Audited:** 2026-07-26
**Scope:** The four existing descriptive computations (VRP, RV20, vol-surface fit, skew/term-structure) checked against documented/standard methodology. This is the success-criterion-1 "intentional deviation log."
**Source:** 25-RESEARCH.md (yardsticks + citations), 25-CONTEXT.md (locked VRP decision).
**Verdict summary:** RV20, skew(25Δ), term-structure = **VERIFIED CORRECT** (no math change). VRP = **INTENTIONAL DEVIATION** (documented, kept by design). Surface fit = **MATCHES DOCUMENTED INTENT** (descriptive, not arbitrage-free).

---

## Per-Computation Audit Table

| # | Computation | Code location | Yardstick / reference | Verdict | Gap found → resolution |
|---|-------------|---------------|-----------------------|---------|------------------------|
| 1 | **RV20** (realized vol) | `engine/vol/vol_metrics.py:compute_rv20` | Close-to-close historical vol, annualized `√252`, mean-centered, `ddof=1` — Hull, *Options Futures & Other Derivatives*; cross-checked vs macrosynergy.com, flashalpha.com | **VERIFIED CORRECT** — `np.sqrt(252)·log_returns.std(ddof=1)` is the textbook mean-centered, n−1, √252 estimator. No math change. | No formula gap. Untested guards (NaN price→None, ≤0 price→None, 21 identical→0.0) now covered — **25-01 Task 3**. |
| 2 | **VRP** (vol-risk-premium proxy) | `engine/vol/vrp_history.py:vrp_history_series` (`vrp_hist = vi − rv×100`, line 80) | Academic term "VRP" = Carr & Wu (2009) variance risk premium `IV²−RV²` (variance units) | **INTENTIONAL DEVIATION** — code's "VRP" is `vol_index − RV20×100`, an implied-minus-realized vol-**point** spread (a practitioner proxy), NOT the Carr-Wu variance-swap VRP. Kept unchanged by locked decision: vol-point spread is theoretically aligned for vanilla covered-call/CSP writing (premium ≈ linear in IV via vega) and more interpretable for the income-sleeve PM. | Naming/methodology mismatch → **documented at first use in 25-03**: honest docstring in `vrp_history.py` + glossary/email footnote in `report.py` ("practitioner IV−RV proxy, not the Carr-Wu variance-swap VRP"). Computation + "VRP" label unchanged. NaN-mid-series (E7) and n=1 (E8) edges test-covered — **25-03 Task 2**. |
| 3 | **Vol-surface fit** (RBF) | `engine/surface/surface_interactive.py`, `engine/gex/analytics.py:rbf_grid`/`coverage_mask` | Thin-plate-spline RBF over std-normalized `(DTE, ln(K/S))` + convex-hull (Delaunay) coverage mask; industry context = SVI/SABR arbitrage-free fitting | **MATCHES DOCUMENTED INTENT** — a smoothed, honest-about-holes *visualization* of quoted IVs, explicitly "descriptive only" (CLAUDE.md), not a tradeable/arbitrage-free pricing surface. Coverage mask (convex hull) correctly NaN-holes extrapolation. No methodology mismatch for what the code claims to be. | Exception-handling asymmetry (`build_movie_payload` wrapped its RBF fit in try/except; `build_surface_payload`/`build_diff_payload` did not) → **back-ported symmetric try/except in 25-02 Task 1** (near-singular fit degrades to None, not crash). |
| 4 | **Skew (25Δ) + term-structure** | `engine/vol/vol_metrics.py:compute_skew_25d`, `compute_term_structure`, `compute_term_ratios` | 25Δ risk-reversal `IV(25Δ put) − IV(25Δ call)` — Xing, Zhang & Zhao (2010, JFQA), cited in `config.py`; SPY-only term ratio via VIX9D/VIX3M | **VERIFIED CORRECT** — `skew = put_iv − call_iv` (positive = puts pricier, the equity smirk); delta convention symmetric (put −0.25, call +0.25); QQQ/IWM gracefully degrade to None (no CBOE 9D/3M siblings). No formula change. | Two degenerate-case gaps: (a) `_classify_term_structure` returned substantive `"normal"` for <2 points → now `"insufficient_data"` sentinel — **25-01 Task 1**; (b) `_latest_close` (and identical `compute_vvix_level`) returned a truthy NaN float on a NaN last-row close, bypassing `is None` checks → `pd.isna` guard added — **25-01 Task 2**. |

---

## Accepted Limitations (explicitly logged, out-of-scope this phase)

- **RV20 is the least statistically efficient common estimator.** Parkinson (high-low), Garman-Klass (OHLC), and Yang-Zhang (overnight-jump-aware) all have lower estimation variance for the same sample. Switching would require OHLC granularity the spot source (yfinance daily close only, `_fetch_closes_yf`) does not provide — a new data source, not a drop-in fix. Accepted simplification.
- **The RBF vol surface has no arbitrage constraints** (no calendar-spread / butterfly no-arbitrage enforcement, no non-negative risk-neutral density guarantee). This is by design: the surface is a descriptive smoothed visualization, not an arbitrage-free pricing surface. Adding SVI/SABR would be new-model-adjacent work, deferred behind MODEL-01/02.
- **"VRP" naming kept despite the Carr-Wu mismatch.** A full rename to "Vol Premium" / "IV−RV Spread" was rejected as unnecessary churn (practitioners colloquially call IV−RV "the vol risk premium"); the honest first-use definition is the chosen mitigation instead.

---

## Dead Code Retired During Audit

- **`compute_vrp(iv30, rv20)` in `vol_metrics.py`** — superseded by `vrp_history.vrp_percentile()` after the VRP-03 fix (2026-07-16); grep-confirmed zero non-test callers. Deleted cleanly with its `TestComputeVrp` tests and CLAUDE.md engine-table mention — **25-01 Task 3** (no backwards-compat shim, per CLAUDE.md).

---

## Gap-to-Plan Traceability

| Gap (from 25-RESEARCH "Current-Behavior Gap Findings") | Owning plan | Task |
|--------------------------------------------------------|-------------|------|
| VRP naming/methodology mismatch (documented, not renamed) | 25-03 | Task 1 |
| VRP NaN-mid-series (E7) + n=1 (E8) edges untested | 25-03 | Task 2 |
| `build_surface_payload`/`build_diff_payload` missing try/except around RBF fit | 25-02 | Task 1 |
| `_classify_term_structure` returns `"normal"` for <2 points | 25-01 | Task 1 |
| `_latest_close` / `compute_vvix_level` NaN-vs-None contract break | 25-01 | Task 2 |
| `compute_vrp()` dead code | 25-01 | Task 3 |

All four computations certified against their documented methodology: three verified-correct (math unchanged), one intentional-deviation logged honestly at first use.

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
**Phase siblings:**
- [[_planning/vol-diagnostics/phases/25-existing-computation-rigor-hardening/25-01-PLAN|25-01-PLAN]]
- [[_planning/vol-diagnostics/phases/25-existing-computation-rigor-hardening/25-01-SUMMARY|25-01-SUMMARY]]
- [[_planning/vol-diagnostics/phases/25-existing-computation-rigor-hardening/25-02-PLAN|25-02-PLAN]]
- [[_planning/vol-diagnostics/phases/25-existing-computation-rigor-hardening/25-02-SUMMARY|25-02-SUMMARY]]
- [[_planning/vol-diagnostics/phases/25-existing-computation-rigor-hardening/25-03-PLAN|25-03-PLAN]]
- [[_planning/vol-diagnostics/phases/25-existing-computation-rigor-hardening/25-CONTEXT|25-CONTEXT]]
- [[_planning/vol-diagnostics/phases/25-existing-computation-rigor-hardening/25-RESEARCH|25-RESEARCH]]

<!-- LINKS:END -->
