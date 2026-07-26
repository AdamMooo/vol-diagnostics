---
quick_id: 260514-fz2
slug: dead-code-stale-ref-sweep
status: complete
commit: 22ec33a
---

# Summary: v3.2 item 5 — dead code + stale-ref sweep

## What was done

Removed the broken matplotlib save/show path from `gex/run_gex.py`. The file previously imported `matplotlib` and `matplotlib.pyplot` solely for `fig.savefig()`, `plt.close()`, and `plt.show()` calls on Plotly `go.Figure` objects — all of which would raise `AttributeError` at runtime. Replaced with `fig.write_html()` in the save branch and `fig.show()` in the interactive branch. Removed all three matplotlib imports and the stray `matplotlib.use("TkAgg")` call.

Audit confirmed all other flagged stale-ref terms (`plot_overview`, `expected_1d_sigma`, `OI×vega`, `vanna_exposure`, `vex`, `chex`) are already absent from active source files. Tombstone guard tests in `test_analytics_summarise.py` for `gamma_regime`, `net_vex`, `net_chex` are correct and were left untouched.

## Outcome

- 23 tests passed, 0 failed (`pytest gex/tests/ -x -q`)
- Smoke test (`python -m gex.run_gex --ticker SPY`) completed without error, writing `out/gex_strikes_SPY_2026-05-14.html` and `out/gex_profile_SPY_2026-05-14.html`

## Files changed

- `gex/run_gex.py` — removed matplotlib imports, replaced savefig/plt.close/plt.show with write_html/fig.show

## Verified resolved in Phase 24 (2026-07-26)

Confirmed complete during the Phase 24 (24-02) close-out — STATE.md's stale "missing"
flag was corrected to "resolved". No re-work; the 2026-05-14 fix (commit 22ec33a) stands.

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
<!-- LINKS:END -->
