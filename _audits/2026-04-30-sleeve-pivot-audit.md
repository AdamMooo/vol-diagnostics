# Sleeve-Pivot Audit — 2026-04-30

Audit performed under the senior-quant-reviewer prompt that drove the v1.0 → v2.0 pivot.

## Audit Verdict

**Pivot, do not extend.** The v1.0 HMM-centric notebook and the stated business goal (options sleeve allocation framework) are different products requiring different inputs. Extending `hmm.ipynb` toward sleeve allocation would have produced a fund-behavior characterization tool wearing a sleeve-allocation label — credibility-risk if shown to a quantitative audience or PM/IC.

## Three load-bearing findings

1. **The notebook does not contain an HMM.** It uses `sklearn.mixture.GaussianMixture` (3 components, `covariance_type='diag'`). GMM has no temporal transition matrix. The post-hoc transition matrix is computed from a sequence the model never enforced was sequential. Naming is dishonest throughout planning docs and code.

2. **There is zero options data anywhere in v1.0.** No IV, no skew, no term, no VIX, no VRP. A regime model on benchmark log returns alone cannot inform options sleeve choice.

3. **Single-fund × single-benchmark scope is too narrow** for the stated audience (Purpose PM/IC, product team).

## Pivot decision

- v1.0 milestone closed without ship. `hmm.ipynb` and `.planning/phases/0[1-3]-*` preserved untouched.
- v2.0 milestone "Sleeve Allocation Framework" started.
- New deliverable: `sleeve_alpha.ipynb` driven primarily by a transparent **scorecard** on options-pricing signals (VRP, skew, term, trend, drawdown), not by a regime model.
- HMM relegated to optional Phase γ "fragility flag" appendix using `statsmodels.tsa.regime_switching.MarkovRegression` (since `hmmlearn` is not in the locked Python env).

## Strategy universe — final

| Sleeve | v2.0? | Reasoning |
|---|---|---|
| Covered call (BXM-style) | YES | Aligns with Purpose ETF/fund DNA; PM-comprehensible |
| Cash-covered put (PUT-style) | YES | Income story, IC-friendly |
| Collar (95/110 monthly) | YES | Skew-driven, downside management |
| Short straddle / strangle | YES | VRP harvest, sized inversely to fragility |
| Dispersion / index-vs-single-name RV | NO | Dealer/HF turf, capacity-limited, governance-unfriendly for retail AM |

## Recommended architecture

- Primary engine: percentile-rank scorecard on a 6-signal panel (RV, VRP, skew, term, trend, drawdown), per underlying.
- Sleeve P&L proxies: synthetic monthly-roll Black-Scholes priced from spot + IV + 90% moneyness IV. No actual option-chain history needed.
- Output: PM-grade dashboard table + auto-generated commentary block + small-multiple charts.
- Optional fragility flag (γ): 2-state `statsmodels.MarkovRegression` on the cross-asset fragility composite, sticky transitions, 5-day hysteresis.

## Data-availability probe results (2026-04-30 server)

| Field | Status | Notes |
|---|---|---|
| `con.bdh('SPX Index', '30DAY_IMPVOL_100.0%MNY_DF', ...)` | OK | 1,584 days, 2020-01-02 → 2026-04-22 |
| `con.bdh('SPX Index', '30DAY_IMPVOL_90.0%MNY_DF', ...)` | OK | Skew computable as IV90 − IV100 |
| `con.bdh('SPX Index', 'IVOL_DELTA_25_PUT', ...)` | FAIL | Field invalid in `emds_client` (not raw Bloomberg) |
| `con.bdh('VIX Index', 'PX_LAST', ...)` | OK | Fragility fallback available |
| `con.bdh('SPX Index', '90DAY_IMPVOL_100.0%MNY_DF', ...)` | Untested | Term structure — assume OK by analogy, verify in Phase 7 |
| XIU / XSP equivalents | Untested | Probe in Phase 7 |

## Open questions still parked (mostly addressed; remaining at milestone start)

| # | Question | Where to resolve |
|---|---|---|
| Q2 | What is PDIV's current overlay rule? | Gate for Phase 13/β; ask PDIV PM |
| Q5 | History depth — internal NAV / IV time depth? | Resolve during Phase 7 data audit |
| Q6 | Compliance constraints on what the framework can recommend? (e.g., short straddle allowed for retail funds?) | Compliance review before β output ships |
| Q7 | Preferred Canadian benchmark — TSX 60, S&P/TSX Composite, capped composite? | Resolve during Phase 7 (XIU vs XSP probe) |

## Items consciously NOT applied from regime-detection lessons

- HDP-HMM / NumPyro stack (overkill, locked env doesn't have them)
- 13-feature engineering pipeline (signal panel deliberately small for interpretability)
- Walk-forward GARCH-VaR (no `arch` package; EWMA suffices for tail-risk reporting)

Items that ARE applied: sticky transitions, 5-day hysteresis, absolute (not rank-based) regime naming, OOS validation as release gate, `random_state=42`, version pinning, causality discipline.

## See also

- `.planning/PROJECT.md` Strategic Decisions
- `.planning/MILESTONES.md` v1.0 closure record
- `.planning/REQUIREMENTS.md` v2.0 active reqs
- `.planning/ROADMAP.md` Phase 7-14 detail
- `NOTES-from-regime-detection.md` (HMM lessons applicable to optional Phase 14/γ)
- [[../options-quant|Options Quant hub]] · [[../../_audits/_audits|Audits hub]]
