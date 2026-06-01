---
phase: 10-dashboard-restructure-local-only
reviewed: 2026-05-31T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - gex/config.py
  - gex/report.py
  - gex/analytics.py
  - gex/vol_metrics.py
  - streamlit_app.py
findings:
  critical: 1
  warning: 3
  info: 4
  total: 8
status: issues_found
---

# Phase 10: Code Review Report

**Reviewed:** 2026-05-31
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Reviewed the Phase 10 dashboard restructure: shared `PALETTE` token dict in `config.py`,
the `plot_oi_by_strike` addition plus 2D-skew/term removals in `analytics.py`, three
headless pure functions in `vol_metrics.py`, and the rewritten 4-tab `streamlit_app.py`.

The new pure functions (`vrp_headline`, `evolution_5d_summary`, `positioning_levels`) are
clean — None/NaN guards, division-by-zero guards, and the descending-sort assumption for
`evolution_5d_summary` all check out against `load_evolution`. The `PALETTE` plumbing through
`report.py` is correct.

The one real correctness defect is in the Positioning tab: `plot_oi_by_strike` is fed
`s_df` (strike-level GEX, columns `strike`/`gex` only), so it never plots open interest at
all — it silently falls through to the `abs(gex)` proxy branch while the chart title, axis,
and Streamlit caption all claim the bars are Call/Put OI. The proxy branch also mislabels its
hover units. Findings below.

## Critical Issues

### CR-01: Positioning tab plots a |GEX| proxy but labels it as "OI by Strike" / "Call OI / Put OI"

**File:** `streamlit_app.py:590`, `gex/analytics.py:490-547,565-567`
**Issue:**
`tab_positioning` calls `plot_oi_by_strike(data["s_df"], spot, ticker, s)`. `s_df` is the
output of `strike_gex(df)` (`gex/exposure_engine.py:36`), which produces exactly two columns:
`strike` and `gex`. It has no `call_oi`, `put_oi`, or `oi` column.

`plot_oi_by_strike` branches on those columns (`analytics.py:503`, `:523`) and, finding none,
always falls into the final `else` branch (`analytics.py:533`) that plots `chain_df["gex"].abs()`
as a "proportional stand-in". So on the live path the chart **never shows open interest** — it
shows a gamma-and-spot²-weighted proxy.

Meanwhile the surrounding UI asserts it *is* OI:
- chart title `"{ticker}  ·  OI by Strike"` (`analytics.py:565`)
- y-axis title `"OI (contracts)"` (`analytics.py:567`)
- Streamlit caption `"Call OI = blue, Put OI = red."` (`streamlit_app.py:594`)

A PM reading "Put OI" bars is actually looking at |GEX| in neutral-gray. The two are not
proportional (GEX folds in gamma and S²), so wall/cluster reads off this chart are wrong. This
is a data-integrity defect on the dashboard's headline "assumption-free observable" panel.

**Fix:** Either pass a frame that actually carries OI, or stop labeling the proxy as OI.
Preferred — thread split OI through the pipeline so the real branch runs:
```python
# gex/exposure_engine.py — emit per-side OI alongside GEX
def strike_oi(df: pd.DataFrame) -> pd.DataFrame:
    piv = (df.pivot_table(index="strike", columns="type", values="oi",
                          aggfunc="sum", fill_value=0)
             .rename(columns={"call": "call_oi", "put": "put_oi"})
             .reset_index())
    return piv.sort_values("strike").reset_index(drop=True)
# compute.py: return "oi_df": strike_oi(df); streamlit: plot_oi_by_strike(data["oi_df"], ...)
```
Stopgap if OI plumbing is deferred — make the chart honest when only `gex` is present
(title `"|GEX| by Strike (OI proxy)"`, y-axis `"|GEX| ($B)"`, divide proxy by 1e9, and drop the
"Call OI = blue, Put OI = red" caption at `streamlit_app.py:594`).

## Warnings

### WR-01: |GEX| proxy hover shows units off by 1e9

**File:** `gex/analytics.py:538,545`
**Issue:**
In the proxy branch `proxy = chain_df["gex"].abs()` is plotted raw (GEX magnitudes are ~1e9 for
index names), but the hovertemplate formats it as billions: `"|GEX| proxy: %{y:.3f}B"`
(`:545`). A bar with GEX of 1.2e9 hovers as `"1200000000.000B"` instead of `"1.200B"`. The other
GEX charts (`plot_strike_gex`, `:80`) correctly divide by 1e9 before plotting. Since CR-01 makes
this branch the live one, the broken hover is what users actually see.
**Fix:** Divide by 1e9 to match the `B` suffix:
```python
proxy = chain_df["gex"].abs() / 1e9
...
hovertemplate="Strike: %{x:.0f}<br>|GEX| proxy: %{y:.3f}B<extra></extra>",
```

### WR-02: ∆IV surface title hardcodes "today" even when Date A is a historical snapshot

**File:** `streamlit_app.py:362-369`, `gex/analytics.py:458`
**Issue:**
The Compare sub-tab lets the user pick **both** dates A and B independently
(`streamlit_app.py:314-327`). The call passes A as `df_today` and B as `df_prior`
(`:363-367`) but only forwards `label_prior=label_b` — `label_a` is dropped. The figure title
is built as `f"∆IV Surface — {ticker}  (today − {label_prior})"` (`analytics.py:458`), so when
the user selects e.g. A=`10d` and B=`live`, the chart computes `IV(10d) − IV(live)` but the
title reads `"today − live"`. The word "today" is wrong (A is 10 sessions back) and the sign
narration is inverted relative to what the label implies. The body caption at
`streamlit_app.py:370-374` does use `label_a`/`label_b` correctly, so the title contradicts the
caption directly beneath it.
**Fix:** Pass `label_a` through and use both labels in the title:
```python
def plot_iv_change_surface(df_today, df_prior, ticker, spot_today, spot_prior,
                           label_today, label_prior):
    ...
    text=f"∆IV Surface — {ticker}  ({label_today} − {label_prior})",
# caller:
plot_iv_change_surface(surface_df_a, surface_df_b, ticker, spot_a, spot_b,
                       label_today=label_a, label_prior=label_b)
```

### WR-03: VRP metric shows a value while its caption says "insufficient history"

**File:** `streamlit_app.py:401-417`
**Issue:**
`vrp_percentile` is only assigned when the history has `>= 5` non-null VRP rows
(`:404`); otherwise it stays `None`. `vrp_headline` returns the cold-start string
`"VRP: insufficient history (accumulates from run_daily)"` whenever `percentile is None`
(`vol_metrics.py:214`). But the `st.metric` directly above (`:412-416`) renders the real
`vrp_display` value regardless. So with 1–4 sessions of history the dashboard shows, e.g.,
`VRP = +2.7pp` in the metric and "insufficient history" in the caption immediately below —
internally contradictory. The headline conflates two distinct conditions (no VRP value vs. no
percentile context).
**Fix:** Decouple the value read from the percentile read in `vrp_headline`, or in the app emit
a value-with-no-percentile caption when `vrp_pp_val is not None and vrp_percentile is None`
(e.g. `f"{vrp_pp_val:+.1f}pp · percentile pending (<5 sessions)"`).

## Info

### IN-01: Unused import inside the proxy branch

**File:** `gex/analytics.py:537`
**Issue:** `from gex.exposure_engine import MULTIPLIER` is imported in the `else` branch but
never referenced — the proxy is `chain_df["gex"].abs()`, no multiplier applied.
**Fix:** Delete the import line.

### IN-02: Dead variable `term_series`

**File:** `streamlit_app.py:450`
**Issue:** `term_series = []` is assigned but never read anywhere (confirmed by grep — only the
assignment exists). Leftover from the removed Term tab.
**Fix:** Delete the line.

### IN-03: Dead defensive branch on `summary.get("error")`

**File:** `streamlit_app.py:188`
**Issue:** `render_regime_cards` filters out tickers where `all_data[t]["summary"].get("error")`
is truthy, but `compute_ticker`/`summarise` never set an `"error"` key — failed tickers raise in
`fetch_ticker` and are caught at `:237`, so they never enter `all_data` at all. The branch can
never be true. Harmless but misleading about where errors are handled.
**Fix:** Drop the `.get("error")` clause, or document that it guards a shape no current caller
produces.

### IN-04: Redundant `result[bucket] = None` re-assignment

**File:** `gex/vol_metrics.py:51`
**Issue:** In `compute_skew_25d`, when a bucket's first qualifying expiry has fewer than 2
puts/calls, the code sets `result[bucket] = None` then `continue`. The bucket is already `None`
from initialization (`:31`) and the guard at `:44` (`if result[bucket] is not None: continue`)
correctly lets a later expiry retry the bucket, so the assignment is a no-op. Not a bug — the
retry semantics are correct — but the line reads as if it finalizes the bucket.
**Fix:** Optional: drop `result[bucket] = None` and keep just `continue`.

---

_Reviewed: 2026-05-31_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/10-dashboard-restructure-local-only/10-01-PLAN|10-01-PLAN]]
- [[_planning/gamma-omm/phases/10-dashboard-restructure-local-only/10-01-SUMMARY|10-01-SUMMARY]]
- [[_planning/gamma-omm/phases/10-dashboard-restructure-local-only/10-02-PLAN|10-02-PLAN]]
- [[_planning/gamma-omm/phases/10-dashboard-restructure-local-only/10-02-SUMMARY|10-02-SUMMARY]]
- [[_planning/gamma-omm/phases/10-dashboard-restructure-local-only/10-CONTEXT|10-CONTEXT]]
- [[_planning/gamma-omm/phases/10-dashboard-restructure-local-only/10-DISCUSSION-LOG|10-DISCUSSION-LOG]]
- [[_planning/gamma-omm/phases/10-dashboard-restructure-local-only/10-PATTERNS|10-PATTERNS]]

<!-- LINKS:END -->
