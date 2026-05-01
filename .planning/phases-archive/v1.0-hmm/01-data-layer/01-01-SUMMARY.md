---
phase: 01-data-layer
plan: 01
subsystem: notebook-setup
tags: [setup, data-load, bloomberg, django-orm]
key-files:
  created: []
  modified:
    - hmm.ipynb
metrics:
  tasks_completed: 2
  tasks_total: 2
---

# Plan 01-01 Summary — Setup & Data Load

## What Was Built

Cleared hmm.ipynb of all prior One-Class SVM analysis and wrote two new foundation cells:

**Cell 1 — Setup (Section 0.1):** All 7 required constants defined (`FUND_SYMBOL='PYF'`, `BENCHMARK_TICKER='SPXT Index'`, `START_DATE`, `END_DATE`, `COLOR_FUND`, `COLOR_BENCH`, `COLOR_DD`). Server context documented — Django ORM and Bloomberg `con` object pre-loaded in shell_plus, no explicit connection setup.

**Cell 2 — Data Load (Section 0.2):** Fund NAV pulled via `fa.primary_fund.get_adj_nav()` (Django ORM, `FundAccount.objects.get(symbol=FUND_SYMBOL)`), filtered to `START_DATE`..`END_DATE`. Benchmark price via `con.bdh(BENCHMARK_TICKER, 'PX_LAST', START_DATE, END_DATE)`, column renamed to `'price'`, extracted as `df_bench_price` Series. Both series print observation count, date range, value range, and `inferred_freq`. Frequency check warns on non-daily (`B`/`D`/`None`) data.

## Commits

| Task | Action |
|------|--------|
| Task 1 | Replaced hmm.ipynb with clean notebook containing Setup cell (no git) |
| Task 2 | Inserted Data Load cell as cell 2 (no git) |

## Deviations

None — executed exactly per plan spec.

## Self-Check: PASSED

- [x] Notebook has exactly 2 cells
- [x] Cell 1 contains all 7 constants (FUND_SYMBOL, BENCHMARK_TICKER, START_DATE, END_DATE, COLOR_FUND, COLOR_BENCH, COLOR_DD)
- [x] Old One-Class SVM code (OneClassSVM, RandomForestClassifier, tickers list) is gone
- [x] Cell 2 contains `FundAccount.objects.get(symbol=FUND_SYMBOL)` and `fa.primary_fund.get_adj_nav()`
- [x] Cell 2 contains `con.bdh(BENCHMARK_TICKER, 'PX_LAST', START_DATE, END_DATE)`
- [x] Cell 2 assigns `df_nav` and `df_bench_price` as named variables
- [x] Cell 2 prints frequency for both series; includes frequency check
- [x] No forward-filling, resampling, or local file path references

## PLAN COMPLETE
