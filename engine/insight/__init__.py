"""Risk Lens — turns the vol stores into conditional, decision-shaped insight.

Every other module in engine/ describes *today*. This package answers the question a
description can't: "the last times it looked like this, what happened over the next
month?" — with effective sample sizes, bootstrap error bars and an out-of-sample split
shown next to every number.

    panel       daily feature + forward-outcome panel (SPX from 1990, vol indices)
    base_rates  conditional forward-risk distributions per state cell
    exposure    vol-managed exposure scalar + its backtest
    events      hysteresis state machines → exception events (the email trigger)
    lens        assembles the read (one JSON dict, schema vol-risk-lens-v1)
    render      exception email HTML + terminal text
    run         daily CLI — `python -m engine.insight.run --send`
    backtest    evidence CLI — regenerates research/risk-lens-findings.md
"""
