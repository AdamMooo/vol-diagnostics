# Vol Diagnostics — Launch Post & Reply Bank

Companion to [`INTERVIEW-PREP.md`](INTERVIEW-PREP.md). Same positioning: descriptive,
non-directional, built for an option-writing desk. Nothing here claims direction, and
nothing cites a specific market move — public posts age badly when they do.

Last updated: 2026-08-09

---

## Primary post (recommended)

> I built a volatility diagnostics platform that refuses to tell you where the market is going.
>
> That sounds like a missing feature. It's the entire design.
>
> An option-writing desk doesn't get paid for direction. It gets paid for carrying risk — implied volatility trades above realized on average, and selling options harvests that spread. The edge is structural. What varies is how well you're compensated for it on any given day.
>
> So that's what the tool measures:
>
> - Is premium rich or cheap, ranked against a decade of CBOE volatility history
> - Where on the surface the richness sits — skew says which side to sell, term structure says which tenor
> - How large moves tend to run in the current dealer-positioning regime, which sets sizing, not direction
>
> Every read maps to a decision a systematic overwriter already makes on every roll. None of them require a view.
>
> The part I'm most pleased with is what isn't in it. I tested whether the premium signal could time a portfolio tilt. It couldn't — the forward-return test came back null. So I removed the feature instead of shipping it with a caveat. Four other metrics went the same way, for the same reason.
>
> Every claim on the dashboard is tiered to the evidence behind it, with citations. Where the sample is too thin to support a read, the read is hidden rather than shown with an asterisk.
>
> Built on free data — no vendor feed. Runs itself daily.
>
> Live dashboard: https://40.233.113.63.nip.io

**Length:** ~260 words. Reads in about 45 seconds.

---

## Short variant (if you want it tighter)

> I built a volatility diagnostics platform that won't tell you where the market is going.
>
> That's the design, not a gap. An option-writing desk isn't paid for direction — it's paid for carrying risk. Implied vol trades above realized, and selling options harvests that spread. What varies is how well you're compensated for it today.
>
> So the tool measures that: whether premium is rich or cheap against a decade of history, where on the volatility surface the richness sits, and how large moves tend to run in the current regime.
>
> The part I'm proudest of is what I took out. I tested whether the premium signal could time a tilt. It came back null, so I deleted the feature rather than ship it with a caveat.
>
> Live: https://40.233.113.63.nip.io

**Length:** ~130 words.

---

## Reply bank

Prepared answers for the comments this will actually draw. Keep them short — these are
replies, not essays.

**"Isn't this just GEX / SpotGamma stuff?"**
> Dealer gamma is in there, but demoted on purpose — capped at 90 DTE, labeled a model construct, and I use only its sign for a move-size read, never as a price level. It sits below the volatility-surface reads because the evidence behind it is weaker. There's also good counter-evidence I engage with rather than ignore: Dim, Eraker and Vilkov (2023) find 0DTE gamma doesn't propagate to future volatility.

**"How is this different from just watching VIX?"**
> VIX is the level. This is the level relative to what's actually being realized, ranked against its own decade of history, and decomposed across strike and tenor so you know which option to sell — not just whether vol is high.

**"Does it make money / what's the backtest?"**
> It isn't a strategy, so there's nothing to backtest as one. It's a conditioning layer on a writing program that already has a structural edge. The one timing claim I did test — using the premium signal to time a tilt — failed, and I removed it.

**"Why free data instead of a real feed?"**
> Because the data source is one class and swapping it is a one-class change. Everything downstream is source-agnostic. Free CBOE data was enough to prove the methodology; a Bloomberg or OPRA drop-in doesn't change a line of the surface fit or the ranking logic.

**"Can I see the code?"**
> Happy to walk through it — the repo's private, but I'll screen-share the architecture and the methodology doc any time.

---

## Posting notes

- **No emojis, no hashtag spam.** Two or three at most if any: `#volatility` `#quantfinance` `#optionstrading`.
- **Best window:** Tuesday–Thursday morning. Avoid Friday and weekends.
- **Cold start is now 5-7s** — but load the dashboard once yourself before posting so the container is warm for the first wave of clicks.
- **Do not** add a specific market move or performance number to the public post. Keep the worked example in `INTERVIEW-PREP.md` for conversations where you can give it full context and answer follow-ups.
- If it gets traction, the natural follow-up post is the methodology tiering — "how I decided what was allowed on the dashboard" — which is the most distinctive thing here.
