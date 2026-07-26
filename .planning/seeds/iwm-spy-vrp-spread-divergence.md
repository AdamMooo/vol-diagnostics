---
title: Cross-ticker divergence rows (IWM–SPY VRP spread first)
trigger_condition: monitor v1 shipped; spread series backfilled from stored vol_index/RV histories
planted_date: 2026-07-23
---

Operationalize the repo's cross-ticker thesis (QQQ leads flips, IWM divergence = domestic
stress) as monitor rows. Start with **IWM VRP minus SPY VRP**: build the spread series from
the deep vol-index histories (both legs have real depth), rank it against its own ECDF like
any other metric, alert on band transitions. Later candidates: QQQ–SPY skew spread,
term-ratio divergence — those wait on chain-metric history depth (credibility floors).

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
<!-- LINKS:END -->
