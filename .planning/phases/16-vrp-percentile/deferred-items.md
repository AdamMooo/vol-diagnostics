# Deferred Items — Phase 16

Out-of-scope discoveries logged during execution. Not fixed (SCOPE BOUNDARY).

## Pre-existing test failures in gex/tests/test_run_daily_pngs.py (7 tests)

**Found during:** 16-02 full-suite verification.
**Status:** Pre-existing, unrelated to Phase 16. NOT caused by this plan's changes.

The `TestOneDayDeltaIVPngs` suite patches `gex.run_daily.plot_iv_change_surface`,
but `run_daily.py` no longer exposes that attribute (grep: no match). The test was
last touched in Phase 13 (commit 27807f3); `run_daily.py` last in Phase 15 (2f27341).
The surface-PNG plotting was evidently renamed/relocated after the test was written.

Failing tests:
- test_three_tickers_attach
- test_missing_prior_snapshot_skips_ticker
- test_empty_prior_df_skips_ticker
- test_export_png_failure_non_blocking
- test_label_prior_format
- test_surface_type_is_div_surface

Error: `AttributeError: module 'gex.run_daily' has no attribute 'plot_iv_change_surface'`

**Recommendation:** Re-point the patch target to the current plotting function
(likely in gex/surface_evolution.py or wherever ΔIV surface PNGs are built) in a
dedicated test-maintenance fix. Out of scope for Phase 16 (VRP percentile).

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/16-vrp-percentile/16-01-PLAN|16-01-PLAN]]
- [[_planning/gamma-omm/phases/16-vrp-percentile/16-01-SUMMARY|16-01-SUMMARY]]
- [[_planning/gamma-omm/phases/16-vrp-percentile/16-02-PLAN|16-02-PLAN]]
- [[_planning/gamma-omm/phases/16-vrp-percentile/16-CONTEXT|16-CONTEXT]]
- [[_planning/gamma-omm/phases/16-vrp-percentile/16-RESEARCH|16-RESEARCH]]

<!-- LINKS:END -->
