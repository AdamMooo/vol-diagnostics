# Risk Lens — evidence
Generated 2026-11-03 by `python -m engine.insight.backtest --write` · data 1991-12-30 → 2026-11-02 · horizon 21 sessions · SPX (^GSPC) + CBOE vol indices. **Do not hand-edit — regenerate.**

Outcome definitions: `fwd_rv` = realized vol over the next 21 sessions (annualized %); `p_dd5` = share of windows whose worst close fell >5% below the start; `carry_win` = share of windows where VIX exceeded the vol then delivered. `eff_n` = non-overlapping windows. `early`/`late` = same cell re-estimated on each half of history.

## 1. Which axes carry information beyond VIX level?
Spearman correlation with next-month realized vol; `rho_given_VIX` partials out log VIX.

| axis | n | rho_raw | rho_given_VIX |
|---|---|---|---|
| VIX level | 9252 | 0.731 | nan |
| realized vol 20d | 9232 | 0.626 | 0.094 |
| term VIX/VIX3M | 4286 | 0.451 | 0.093 |
| VRP (IV−RV) | 9232 | 0.051 | -0.087 |
| VVIX | 5117 | 0.198 | -0.139 |
| VIX 5d change | 9243 | 0.115 | -0.005 |

**Read:** VIX level is the dominant axis. Every other layer adds little once level is known — most of the system's computational surface re-describes one factor. The lens therefore conditions on level first and only adds term shape / VRP sign where they carry their own signal (sections 2b, 2c).

## 2a. Forward risk by VIX level (10y rolling percentile)

| cell | n | eff_n | fwd_rv_med | p_dd5 | p_dd5_ci | p_dd10 | carry_win | early_p_dd5 | late_p_dd5 | stable |
|---|---|---|---|---|---|---|---|---|---|---|
| bottom 20% | 2014 | 139 | 8.926 | 0.046 | 0.02–0.07 | 0.005 | 0.866 | 0.025 | 0.085 | True |
| 20–40th pct | 1677 | 170 | 10.683 | 0.098 | 0.07–0.13 | 0.013 | 0.864 | 0.069 | 0.114 | True |
| 40–60th pct | 1453 | 167 | 12.484 | 0.171 | 0.13–0.22 | 0.033 | 0.851 | 0.256 | 0.129 | True |
| 60–80th pct | 1494 | 164 | 15.665 | 0.236 | 0.19–0.30 | 0.048 | 0.833 | 0.311 | 0.175 | True |
| 80–95th pct | 1581 | 138 | 19.657 | 0.248 | 0.20–0.29 | 0.055 | 0.850 | 0.220 | 0.288 | True |
| top 5% | 530 | 52 | 29.989 | 0.379 | 0.27–0.49 | 0.223 | 0.785 | 0.447 | 0.200 | True |

## 2b. Term shape within level (confound check)
If inversion only proxied for level, the term rows inside each level band would match. They don't at elevated levels — shape carries its own information there.

| cell | n | eff_n | fwd_rv_med | p_dd5 | p_dd5_ci | p_dd10 | carry_win | early_p_dd5 | late_p_dd5 | stable |
|---|---|---|---|---|---|---|---|---|---|---|
| VIX 50–80th · contango | 888 | 93 | 13.310 | 0.148 | 0.10–0.21 | 0.018 | 0.912 | 0.153 | 0.145 | True |
| VIX 50–80th · flat | 248 | 52 | 15.634 | 0.210 | 0.12–0.30 | 0.093 | 0.730 | 0.175 | 0.232 | True |
| VIX 50–80th · inverted | 103 | 33 | 15.210 | 0.204 | 0.11–0.25 | 0.107 | 0.738 | 0.172 | 0.256 | True |
| VIX < median · contango | 2231 | 138 | 10.287 | 0.108 | 0.08–0.14 | 0.019 | 0.830 | 0.108 | 0.108 | True |
| VIX < median · flat | 59 | 20 | 10.308 | 0.119 | 0.00–0.10 | 0.017 | 0.881 | 0.071 | 1.000 | False |
| VIX < median · inverted | 6 | 4 | 7.824 | 0.000 | 0.00–0.00 | 0.000 | 1.000 | 0.000 | nan | None |
| VIX > 80th · contango | 343 | 31 | 19.095 | 0.248 | 0.15–0.39 | 0.067 | 0.793 | 0.182 | 0.252 | True |
| VIX > 80th · flat | 192 | 33 | 22.617 | 0.286 | 0.17–0.40 | 0.005 | 0.896 | 0.453 | 0.223 | True |
| VIX > 80th · inverted | 216 | 39 | 26.736 | 0.306 | 0.20–0.42 | 0.097 | 0.856 | 0.318 | 0.298 | True |

## 2c. VRP sign within level
High VRP is the *calm* state. Realized overtaking implied inside an elevated tape is the stress state.

| cell | n | eff_n | fwd_rv_med | p_dd5 | p_dd5_ci | p_dd10 | carry_win | early_p_dd5 | late_p_dd5 | stable |
|---|---|---|---|---|---|---|---|---|---|---|
| VIX 50–80th · implied ≥ realized | 1878 | 189 | 14.254 | 0.202 | 0.16–0.25 | 0.043 | 0.851 | 0.300 | 0.130 | True |
| VIX 50–80th · realized > implied | 335 | 51 | 16.794 | 0.328 | 0.25–0.42 | 0.060 | 0.752 | 0.351 | 0.314 | True |
| VIX < median · implied ≥ realized | 4093 | 243 | 10.062 | 0.083 | 0.06–0.10 | 0.011 | 0.864 | 0.051 | 0.114 | True |
| VIX < median · realized > implied | 332 | 48 | 9.727 | 0.087 | 0.04–0.14 | 0.018 | 0.864 | 0.178 | 0.048 | True |
| VIX > 80th · implied ≥ realized | 1676 | 141 | 20.087 | 0.258 | 0.21–0.32 | 0.084 | 0.842 | 0.254 | 0.265 | True |
| VIX > 80th · realized > implied | 435 | 47 | 26.489 | 0.368 | 0.28–0.48 | 0.149 | 0.802 | 0.415 | 0.297 | True |

## 3. Events — frequency and what followed
Each event is a hysteresis state machine on the SPX vol complex only (QQQ/IWM are context, never extra votes). 'ANY' = days an email would have gone out.

| key | per_year |
|---|---|
| ANY (email days) | 14.28 |
| curve_inverted | 4.02 |
| vol_elevated | 3.64 |
| carry_flip | 3.20 |
| vol_shock | 3.04 |
| vol_extreme | 1.52 |
| vol_calm | 1.25 |

| key | kind | fires | n | eff_n | fwd_rv_med | p_dd5 | p_dd10 | ret_med | carry_win | base_p_dd5 |
|---|---|---|---|---|---|---|---|---|---|---|
| carry_flip | enter | 59 | 59 | 42 | 22.397 | 0.373 | 0.136 | 0.013 | 0.729 | 0.166 |
| carry_flip | exit | 59 | 59 | 46 | 23.055 | 0.407 | 0.136 | 0.010 | 0.763 | 0.166 |
| curve_inverted | enter | 74 | 74 | 50 | 17.633 | 0.243 | 0.054 | 0.026 | 0.851 | 0.166 |
| curve_inverted | exit | 74 | 74 | 52 | 15.177 | 0.257 | 0.068 | 0.028 | 0.743 | 0.166 |
| vol_calm | enter | 46 | 46 | 34 | 8.822 | 0.022 | 0.000 | 0.017 | 0.913 | 0.166 |
| vol_elevated | enter | 67 | 67 | 55 | 19.201 | 0.254 | 0.075 | 0.021 | 0.806 | 0.166 |
| vol_elevated | exit | 67 | 67 | 55 | 14.204 | 0.179 | 0.030 | 0.019 | 0.836 | 0.166 |
| vol_extreme | enter | 28 | 28 | 26 | 25.854 | 0.321 | 0.179 | 0.022 | 0.786 | 0.166 |
| vol_extreme | exit | 28 | 28 | 28 | 19.019 | 0.214 | 0.036 | 0.016 | 0.821 | 0.166 |
| vol_shock | enter | 111 | 105 | 86 | 16.905 | 0.210 | 0.057 | 0.017 | 0.810 | 0.166 |

Baseline: median fwd vol 12.9, p_dd5 0.166. Note exits are not all-clears: several are still followed by above-normal risk, which is why the email states each event's own history instead of a fixed lean.

## 3b. Multiple-testing check on events
10 event comparisons (each enter/exit vs the base rate) are tested at once, so raw p-values overstate. Each test uses non-overlapping firings only (one per 21-session window), exact two-sided binomial vs the unconditional P(dd>5%), then Holm (family-wise) and Benjamini–Hochberg (false-discovery) corrections at 5%.

| event | n_indep | hits | p_dd5_indep | base_p_dd5 | p_value | p_holm | p_bh | survives_holm | survives_bh |
|---|---|---|---|---|---|---|---|---|---|
| carry_flip:exit | 46 | 18 | 0.391 | 0.166 | 0.000 | 0.002 | 0.002 | True | True |
| carry_flip:enter | 42 | 14 | 0.333 | 0.166 | 0.007 | 0.059 | 0.033 | False | True |
| vol_elevated:enter | 55 | 16 | 0.291 | 0.166 | 0.018 | 0.142 | 0.059 | False | False |
| vol_calm:enter | 34 | 1 | 0.029 | 0.166 | 0.034 | 0.240 | 0.086 | False | False |
| vol_extreme:enter | 26 | 8 | 0.308 | 0.166 | 0.063 | 0.378 | 0.126 | False | False |
| curve_inverted:exit | 52 | 13 | 0.250 | 0.166 | 0.132 | 0.661 | 0.220 | False | False |
| vol_shock:enter | 86 | 18 | 0.209 | 0.166 | 0.308 | 1.000 | 0.440 | False | False |
| vol_extreme:exit | 28 | 6 | 0.214 | 0.166 | 0.449 | 1.000 | 0.562 | False | False |
| curve_inverted:enter | 50 | 10 | 0.200 | 0.166 | 0.567 | 1.000 | 0.630 | False | False |
| vol_elevated:exit | 55 | 10 | 0.182 | 0.166 | 0.717 | 1.000 | 0.717 | False | False |

**Read:** 1 of 10 survive Holm, 2 survive BH. Events that do not survive still email (they mark real state changes), but their 'historically followed by' read should be treated as suggestive, not established.

## 4. Vol-managed exposure (Moreira–Muir) — dashboard context only
weight = min(1.0, 15 / (½·VIX + ½·RV20)), weekly rebalance, no costs, no cash yield. Average weight 0.86.

| period | strategy | cagr | vol | sharpe | max_dd | worst_month |
|---|---|---|---|---|---|---|
| full (1992-01-02→2026-11-02) | buy_hold | 0.087 | 0.181 | 0.550 | -0.568 | -0.169 |
| full (1992-01-02→2026-11-02) | vol_managed | 0.071 | 0.123 | 0.617 | -0.424 | -0.083 |
| early (1992-01-02→2009-05-27) | buy_hold | 0.045 | 0.190 | 0.325 | -0.568 | -0.169 |
| early (1992-01-02→2009-05-27) | vol_managed | 0.044 | 0.123 | 0.412 | -0.424 | -0.083 |
| late (2009-05-28→2026-11-02) | buy_hold | 0.130 | 0.172 | 0.801 | -0.339 | -0.125 |
| late (2009-05-28→2026-11-02) | vol_managed | 0.098 | 0.124 | 0.820 | -0.190 | -0.081 |

**Read:** a drawdown reducer, not a return engine. Judge it on max_dd / worst_month. It costs CAGR, the 15% target was chosen with full-sample knowledge, and out-of-sample studies find vol-managed gains fragile. Decision 2026-11-03: it is a weekly timing rule, so it appears only as labelled context on the dashboard — never in the email, never as an event, never in `risk_lens.json`.

## 5. Is the lens calibrated? (point-in-time replay, 2000→)
Every 21st session, the lens is rebuilt from history known *at that date* and its primary-cell P(dd>5%) is scored against what happened. Brier skill > 0 means the conditioning beats the unconditional base rate out of sample.

- n = 321 independent monthly reads; cells used: {'level': 187, 'level_term': 117, 'level_vrp': 10, 'unconditional': 7}
- Brier: lens 0.1505 vs unconditional 0.1591 → **skill +5.4%**
- early: n=160, skill +6.9%
- late: n=161, skill +3.1%

**This skill is an upper bound, not a floor.** Only the probabilities are point-in-time. The cell boundaries (`RISK_LENS_LEVEL_BINS`, `RISK_LENS_TERM_BINS`), the event thresholds and the choice of conditioning axes were all designed after looking at the full history, so some of the measured edge is selection. Expect less live.

Reliability (predicted vs realized drawdown frequency):

| bucket | n | predicted | realized |
|---|---|---|---|
| (0.0, 0.1] | 97 | 0.042 | 0.093 |
| (0.1, 0.2] | 113 | 0.145 | 0.186 |
| (0.2, 0.3] | 84 | 0.247 | 0.274 |
| (0.3, 0.45] | 25 | 0.357 | 0.360 |
| (0.45, 1.0] | 2 | 0.455 | 0.000 |

Tested 2026-11-02 and not adopted: Bühlmann credibility shrinkage of each cell toward the unconditional rate (k = 5–40 pseudo-observations) left skill unchanged (±0.5pp). The low bucket stays slightly over-confident (predicts ~4%, realized ~9%) — read calm-state drawdown odds as a floor, not a point.

