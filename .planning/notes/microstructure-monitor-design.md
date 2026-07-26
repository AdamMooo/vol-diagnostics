---
title: Microstructure monitor — design decisions
date: 2026-07-23
context: /gsd-explore session (2026-07-22/23) reframing the dashboard+email from descriptive report to exception monitor
---

# Microstructure monitor — design decisions

Reframe: the product is a **market microstructure exception monitor**, not a daily report.
Default output is "nothing unusual" — silence is information. Value = firing loudly and
credibly when measured structure hits an extreme or moves abnormally fast.

## Decisions

1. **Severity statistics — empirical percentile ranks (ECDF), nothing else.**
   - Rank both **levels** and **|k-day changes|** against each metric's own history
     (probability integral transform → common [0,1] abnormality scale, no hand weights).
   - No Gaussian z-scores: vol metrics are heavy-tailed/heteroskedastic; a calm-sample z
     over-fires, a crisis-contaminated z never fires. Robust z ((x−median)/MAD) is the
     fallback only if a continuous score is ever needed.
   - **Dual lookback**: deep rank ("historically rare") + 1-yr rank ("locally unusual"),
     both displayed; alert on either. Generalizes the VRP_DEEP_LOOKBACK_SESSIONS call.
   - No composite/anomaly scores — violates the no-hidden-scoring rule.

2. **Alert rule — transitions with hysteresis, budgeted for false alarms.**
   - Fire on band **entry** (e.g. cross 95th), re-fire only on **escalation** (e.g. 99th);
     exit band lower than entry (e.g. 80th) so alerts don't flicker.
   - Band placement derived from a **false-alarm budget**: ~30 daily tests (3 tickers ×
     ~5 metrics × level+change) → at 90th-percentile bands expect ~3 false alarms/day.
     Pick tolerable alarms/week, invert to get the band (≈95th+). Multiple-testing
     discipline (BH/FDR as reference frame; back-of-envelope is sufficient for display).
   - Persistence caveat: metrics are highly autocorrelated → effective sample size ≪ n;
     don't over-read 90th vs 93rd.

3. **Surface split**: **email = event-shaped** (band entries + escalations only; near-empty
   on normal days), **dashboard = state-shaped** (current abnormality of everything).

4. **Dashboard architecture — scan → interrogate → contextualize.**
   - **Landing: distribution board.** One row per metric×ticker (~15 rows): horizontal
     percentile strip, today's dot, deep + 1yr ranks marked, **10-session trail** showing
     the path (motion vs parked is the whole microstructure question; trail is load-bearing).
   - **Click a row → evidence panel**: metric history chart with bands drawn + the
     *mechanism view* (skew row → smile overlay today vs 5d; evolution row → existing diff
     surface; VRP row → implied-vs-realized pair). Existing 3D work re-anchored, not demoted.
   - **Third layer unchanged**: Surfaces/Positioning exploration tabs.
   - Current AMPLIFYING/MIXED risk bar goes (leads with demoted GEX). Freshness banner
     shrinks to a dot unless stale.

5. **Row inventory v1**: VRP (deep+1yr), 25Δ skew, 25Δ fly, term ratios (SPY only),
   5d surface-evolution level & RMS. **Net-GEX sign = state chip only, not a ranked row**
   (GEX-as-candidate decision, 2026-07-22). IWM–SPY VRP spread = candidate row (seed).

6. **Credibility floors per metric depth.** VRP rides ~10yr vol-index history; chain
   metrics (~50 sessions since 2026-05) get percentiles labeled with n and can't fire
   deep-history claims until a few hundred sessions. Order-statistic CIs on percentiles
   are cheap if error bars wanted.

7. **Tier 2 — deferred to v5.0 Data Foundation**: conditional base rates attaching
   measured consequences to alert states ("after skew >90th, 5d RV ran 1.4× baseline,
   n=41"). Detection ships first; consequences only after validation on deep history.
   Keeps the no-predictive-claims constraint intact for tier 1.

## Email cuts (independent of monitor)
Methodology footer/glossary/caveat banner out of the daily (replace with one link);
OI tables and key-levels out of email (dashboard-only); add Δ-vs-yesterday context.

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
<!-- LINKS:END -->
