# HMM lessons from regime-detection (extracted before retiring it)

**Source:** `C:\dev\regime-detection\` (personal project, v1.0 production-ready 2026-04-14, 160+ tests passing). Retired from local disk on 2026-04-29 after this extraction. Live copy on personal GitHub: `AdamMooo/regime-detection`.

**Why these notes:** options-quant and regime-detection both fit HMMs on returns to identify latent market regimes. regime-detection went further (HDP-HMM, GARCH-conditional VaR, validation framework) and uncovered traps that anyone building an HMM on financial data will hit eventually. Capture them here so options-quant doesn't have to rediscover them.

---

## 1. Regime stability is the real problem, not the model

The biggest surprise from regime-detection: **a model that looks great in-sample can fragment OOS**. Original setup found K=3 in-sample but K=10 out-of-sample — regime labels flipping daily, signals worthless. options-quant uses raw benchmark returns (no PCA), so this exact failure mode is less likely, but the diagnostic discipline applies:

- **Always validate OOS regime count.** If K=2 in-sample → 4–5 OOS, the model is overfit to historical noise.
- **Always validate OOS dwell time.** Reasonable financial regimes last weeks/months, not days. If average dwell < 5 days, regimes are noise.
- regime-detection target: dwell ≥ 10 days, OOS K stable.

For options-quant: after fitting the 2-state HMM, before reporting anything to a PM, run a walk-forward split (e.g. fit on first 70%, decode on last 30%) and confirm K=2 still emerges and dwell time on the OOS slice is reasonable.

## 2. Hysteresis filter — apply this from day 1

Even with a good model, daily retraining causes **label flicker**: yesterday's "Risk-Off" becomes today's "Risk-On" and back, just from parameter noise.

Fix: **5-day minimum hold period.** A new regime label has to persist for 5 days before the official label flips. regime-detection used `REGIME_HOLD_DAYS=5` in config and `inference.py::filtered_labels()` applied it.

For options-quant: a 1-line post-processing pass on the Viterbi decode. Without it, regime characterization tables get noisy and the visualization looks chaotic. Easy to add even at MVP — it's literally a smoothing filter.

```python
def apply_hysteresis(labels, hold_days=5):
    out = labels.copy()
    last_change = 0
    for i in range(1, len(labels)):
        if labels[i] != out[last_change] and (i - last_change) >= hold_days:
            last_change = i
        else:
            out[i] = out[last_change]
    return out
```

## 3. Sticky transitions — bake regime persistence into the prior

`hmmlearn` Gaussian HMM has no built-in stickiness. Without it, the model is happy to flip regimes daily because each switch is locally cheap.

Two ways to inject stickiness:
- **Initialize transition matrix biased toward diagonal** (e.g. 0.95 on diagonal, 0.05/(K-1) off-diagonal) and let it train from there. Simplest.
- **Use `hmmlearn.hmm.GaussianHMM(transmat_prior=...)` with a Dirichlet prior favoring self-transitions.** Slightly more principled.

regime-detection went further with HDP-HMM `κ=10.0` sticky parameter. Overkill for options-quant's 2-state benchmark model, but the underlying lesson — **encode "regimes persist" as a model assumption, not a hope** — is universal.

## 4. Picking K (number of regimes): parsimony rule

regime-detection's Phase 2.5.3 finding: **BIC overfits to in-sample data.** It selected K=4 with 3.1% improvement over K=3, but OOS validation showed K=3 was more stable.

Decision rule used: **if BIC improvement < 2%, prefer the simpler model.** And always cross-check with OOS regime count.

options-quant has K=2 locked, but if ever extending to K=3, run walk-forward BIC AND walk-forward OOS K-count. If K=3 in-sample fragments to K=4–5 OOS, K=2 wins.

## 5. Regime naming — absolute thresholds beat rank-based labels

regime-detection initially named regimes by rank ("highest-vol regime", "lowest-vol regime"). This breaks across IS/OOS windows because rank-1 in 2010–2020 is not rank-1 in 2020–2026.

Fix: **name regimes by absolute level.** regime-detection used vol brackets:
- Low-Vol: 0–10% annualized
- Med-Vol: 10–18%
- High-Vol: 18%+

For options-quant with 2 states on benchmark returns, an analogous rule:
- Define "Risk-Off" = annualized vol ≥ Xth percentile of historical benchmark vol (e.g. ≥ 15% for SPY)
- Define "Risk-On" = below that
- Assign regime IDs to labels based on each regime's *realized* vol on the training data, not by ID number.

This makes labels stable across rolling refits.

## 6. VaR: never trust static, always condition on volatility

This was regime-detection's most consequential finding. Static VaR (regime mean ± k×regime_std) **failed Christoffersen independence test** (p=0.0039) — exceedances clustered in time. GARCH-conditional VaR per regime passed both Kupiec and Christoffersen (p=0.95 and p=0.55).

Why: static VaR ignores ARCH effects. During a high-vol regime, vol can still spike *within* the regime; static VaR misses it for 1–3 days, exceedances cluster, independence test fails.

If options-quant ever reports VaR or tail risk numbers to a PM:
- **Don't** quote `regime_mean - 1.65 * regime_std`. It's wrong in a way that gets people fired.
- **Do** fit GARCH(1,1) per regime (`arch` package) and use the conditional 1-day-ahead variance for VaR.
- **Caveat:** GARCH lags 5–20 days during regime *transitions*. Pair with a regime-shift warning.

For pure descriptive characterization (mean, std, max drawdown by regime), static stats are fine — just don't call them risk forecasts.

## 7. Causality discipline

Every feature, every transformation, every fit must be **causal** — no future data leaking into past observations. regime-detection had 10 dedicated causality tests.

The traps (all hit at some point):
- **z-score with full-sample mean/std** → leak. Use **expanding-window** standardization.
- **Winsorizing at the global 99th percentile** → leak. Winsorize on expanding window.
- **PCA fit on all data, applied retroactively** → leak. Fit on training slice, transform out-of-sample.
- **Rolling features that need future data** (e.g. centered moving average) → leak. Always trailing windows.

For options-quant: when doing regime characterization (mean return per regime, sharpe per regime, etc.), make sure the *regime labels* used were inferred causally — e.g. if reporting "fund return in regime 0", the regime decode at time t must use only data ≤ t.

## 8. Reproducibility — pin versions, fix seeds

regime-detection pinned `jax==0.9.1` and `numpyro==0.20.0` because Bayesian samplers are notoriously sensitive to library internals. Also fixed `seed=42` and asserted byte-identical regime label outputs in tests.

For options-quant with `hmmlearn`: less brittle than NumPyro, but still pin `hmmlearn`, `numpy`, and `scipy` versions in `requirements.txt`, and pass `random_state=42` to the HMM constructor. Otherwise notebook reruns produce different regime labels each time → unreproducible research.

## 9. Trust scorecard pattern

regime-detection aggregates 8 validation checks into a single **PASS/WARN/FAIL trust verdict**:
- regime separation (different regimes have different return distributions, Kruskal-Wallis test)
- vol ordering (regime named "high-vol" actually has higher vol than the others)
- persistence (dwell time ≥ N days)
- VaR backtest (Kupiec + Christoffersen)
- OOS agreement (IS and OOS regime sequences correlate)
- OOS separation (regimes still distinguishable OOS)
- calibration (model confidence matches accuracy)
- data freshness (data not stale)

For options-quant, even a smaller scorecard (regime separation + dwell time + OOS K-count match) gives the PM a one-line "is this analysis trustworthy" answer. Far more useful than burying caveats in prose.

## 10. Data-pipeline gotchas worth remembering

From regime-detection's troubleshooting log:
- **`get_adj_nav()` returning DataFrame not Series** — same issue options-quant flagged in its README. Always `.squeeze()` after pandas ops that may return either.
- **Forward-filling weekends/holidays** for daily series. If benchmark and fund have different holiday calendars, joins go sideways without forward-fill.
- **Winsorize before standardize.** If you standardize first, the outliers blow up the std and shrink everything else.

## 11. Architectural decisions worth reusing (or skipping)

**Reuse:**
- Hysteresis filter on labels.
- Sticky transition initialization.
- Absolute (vol-bracket) regime naming over rank-based.
- OOS validation as a release gate, not an afterthought.
- `random_state=42` and version pinning.

**Skip (overkill for options-quant):**
- HDP-HMM / NumPyro stack — 2-state Gaussian HMM via `hmmlearn` is the right level.
- 13-feature engineering pipeline — options-quant's design correctly chose benchmark returns only, regime fits on the benchmark.
- Rolling PCA — not needed for univariate input.
- Walk-forward GARCH-VaR — only if options-quant grows into VaR reporting.

## 12. Files in regime-detection worth re-reading before retiring it

If revisiting any of the above in detail:
- `docs/MODEL_CARD.md` — the canonical "what we built and why"
- `docs/KNOWN_ISSUES.md` — all 8 issues with root cause + mitigation (the most reusable doc)
- `docs/RISK_MODEL_CARD.md` — VaR comparison detail
- `docs/REPRODUCIBILITY.md` — exact pinning and seed protocol
- `src/core/hmm_training.py` — labeling, hysteresis, GARCH per regime
- `src/core/var_backtesting.py` — Kupiec + Christoffersen implementation

All accessible at `https://github.com/AdamMooo/regime-detection` if needed.
