# Research Questions

## RQ-001: VRP (IV30 − RV20) as dealer hedging urgency proxy
**Date:** 2026-05-21
**Context:** v3.2 exploration — adding VRP to positioning cards
**Question:** Is IV30 − RV20 a defensible proxy for dealer hedging urgency/aggressiveness?
Carr & Wu (2009) establish VRP as a systematic risk factor. But does the *sign* of VRP
actually predict dealer hedging behavior? Or is it more of a P&L context indicator
(positive VRP = dealers collecting theta, negative = bleeding)?
**Status:** Open — needs lit review before implementation
**Priority:** Medium — can ship VRP display with appropriate caveats even without
peer-reviewed causal backing (it's a descriptive metric either way)

## RQ-002: Realized vol computation methodology
**Date:** 2026-05-21
**Context:** Need RV20 for VRP calculation
**Question:** Close-to-close (Parkinson/Yang-Zhang) or simple log-return std × √252?
For a 20-day window on SPY/QQQ/IWM, the simple estimator is probably fine, but should
verify it doesn't produce misleading VRP readings during gap-heavy regimes.
**Status:** Open
**Priority:** Low — simple estimator is standard; Yang-Zhang is a nice-to-have
