# Covered-Call Spike — Findings (RECONSTRUCTED)

> **⛔ Covered-call TIMING model SHELVED 2026-07-27** — pre-build tests found no timing edge (fwd-return p=0.74; fwd-vol p=0.074 marginal, in-sample, ~35 non-overlapping windows). These priors are retained for the record only; the static-VRP-harvest fact stands, timing does not. See memory `v6-covered-call-model-decision`.

**Status:** ⚠️ Reconstructed from the `.planning/STATE.md` summary on 2026-07-27. The original
`spike_covered_call.py` (v2) is a 0-byte file (never committed, no stash), and no
`spike-findings.md` survived. The numbers below are the *only* surviving record — treat them
as **directional priors to be reproduced and validated** in the v6.0 backtest, not as
established results.

## Question
Is writing a SPY covered call "smart" — and does the edge survive honest, point-in-time testing?

## Findings (directional, unverified)
- **Edge survives point-in-time terciles.** Bucketing dates into VRP terciles using only
  data available *at* each date (no lookahead), the top-tercile ("rich") bucket still showed a
  positive covered-call edge — not a hindsight artifact.
- **~2% OTM sweet spot:** writing ~2% out-of-the-money gave the best risk/reward —
  **+0.49% / month** in the rich regime, **~73% hit rate**.
- **BXM correlation 0.866** (vs the CBOE BuyWrite index) → the synthetic Black-Scholes
  premium overstates realizable premium; **haircut ~30%** to approximate real fills/slippage.

## What v6.0 MUST add (the rigor the spike lacked)
- Significance tests on the **small per-tercile n** (the edge rests on few observations).
- A **true out-of-sample split** (walk-forward or train/test), not full-sample fit.
- **Multiple-testing correction** across the parameter grid (OTM %, DTE, entry/exit
  thresholds) — the project's self-imposed gate before any signal ships.
- The **persistence / half-life** layer (how long the rich regime lasts → sets the DTE to write).

## To upgrade this doc
If the original spike output is recoverable (e.g. Copilot CLI scrollback), paste it and this
file will be replaced with the real numbers + methodology.
