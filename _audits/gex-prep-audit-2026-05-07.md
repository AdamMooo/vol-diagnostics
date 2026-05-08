# GEX POC — Pre-Demo Audit & Hardening Plan
Generated: 2026-05-07 | Last self-audit: 2026-05-07 | Status: parked — resume in a few days
Scope: gex/ module + daily HTML report | Goal: defend every number on the page before showing head of capital markets

## Self-audit corrections applied 2026-05-07
- N=1 day of history (was claimed 3) — verified against parquet
- NEUTRAL_ABS_FLOOR is actively binding for IWM (was claimed dead code) — IWM at -$78M < $200M floor
- Vanna T_MIN inconsistency is latent only (was rated High; corrected to Low) — min_dte=1 makes it inert
- Report covers ~20 tickers (SPY/QQQ/IWM index table + Purpose Yield Shares table) — audit reasoning applies primarily to the index table; single-name dealer convention is weaker for Purpose names and should be flagged in conversation

---

## How to use this document

Three columns of work, in priority order:
1. **Defend** — for each claim, know the exact formula + the assumption that could break it. If you can't answer in one sentence, study it before the meeting.
2. **Harden** — code/data fixes that change a number or close an assumption gap. Ranked P0/P1/P2.
3. **Concede** — things you will *say upfront* are limitations rather than try to defend. Pre-empting kills 80% of "gotcha" questions.

Each section: **Claim → Formula → Assumption risks → Hardening → Q&A prep.**

---

## Section 1 — Data layer (`gex/data_loader.py`)

### Claim
"Full-chain GEX for SPY/QQQ/IWM, sourced from CBOE delayed quotes, ≥1 DTE, OI ≥ 100, IV ≤ 300%."

### What's actually happening
- HTTP GET to `cdn.cboe.com/api/global/delayed_quotes/options/{ticker}.json` (no auth, ~15 min lag)
- Parse OPRA symbols → (expiry, side, strike)
- Filter: `dte >= 1`, `oi >= 100`, `0 < iv <= 3.0`
- Returns `ChainSnapshot(ticker, spot, as_of, chains, iv30, price_change_pct)`

### Assumption risks
| Risk | Severity | Why it matters |
|---|---|---|
| OI is **prior session close**, not intraday | High | A loud question: "is this snapshot real-time positioning?" — answer is **no**. OI updates overnight. Greeks/IV are 15-min delayed but OI is T-1. |
| `min_oi=100` filter throws away long-tail | Medium | At deep wings, OI < 100 is common but cumulative GEX can be material. Defensible because retail/illiquid quotes dominate that tail, but be ready. |
| `max_iv=3.0` is a stale-quote filter, not a real filter | Low | Need to verify: does CBOE ever publish IV > 300% on legitimate quotes? Probably no, but check during volatility events. |
| `min_dte=1` excludes 0DTE | High | Significant — 0DTE is ~50% of SPY volume and dominates intraday gamma. Doc says it's excluded to avoid singularities; this is honest but limits intraday relevance. |
| Spot uses CBOE `current_price` — delayed | Medium | A 15-min stale spot at the open or during a fast tape can move ZGL by enough to flip a regime call. |
| No timezone awareness on `as_of` | Low | `datetime.date.today()` uses local Windows clock. Run after 4pm ET = "today's" close; run pre-open = ambiguous. |
| Survivorship: deslisted/expired options | Low | CBOE feed only returns live chains; not a real risk. |

### Hardening
- **P0** Log + display the snapshot timestamp (`as_of`, plus actual response time) in the HTML email header. He will ask "as of when?" — have it visible.
- **P1** Add a "freshness check": if max(quote timestamp) > 30 min old or markets closed, banner the report. CBOE JSON has a timestamp field — wire it through to `ChainSnapshot`.
- **P1** Sanity: count of options pre/post-filter, log it. If filter drops > X% of OI vs. raw, flag it.
- **P2** Add a `--include-0dte` flag and document the singularity workaround (T_MIN floor already exists). Lets you A/B compare numbers with/without 0DTE so you can answer that question quantitatively, not handwavy.
- **P2** Test against a Bloomberg pull for one day to ground-truth net GEX magnitude. You need *one* validation point against an institutional source.

### Q&A prep
- "How fresh is this?" → "OI is T-1 close, greeks are 15-min delayed CBOE. Real-time would need a paid feed."
- "Why exclude 0DTE?" → "BS gamma/charm have singularities at T→0; including them needs ad-hoc floors that don't apply consistently across greeks. SpotGamma includes them; we don't. We can A/B compare if useful."
- "Why min OI 100?" → "Filters retail-noise wings. Cumulative GEX impact below that is typically <1%. Show me a wing you care about and I'll re-run unfiltered."

---

## Section 2 — Greeks (`gex/greeks_engine.py`)

### Claim
"Gamma/delta/vega/theta from CBOE (American model). Vanna and charm computed via Black-Scholes (European, q=0)."

### What's actually happening
- Gamma: **CBOE-published** (American model, accounts for early exercise + dividends). Used directly in `compute_gex`.
- Vanna: BS formula `-N'(d1) * (d2/σ)` — q=0, so **dividend yield ignored**.
- Charm: BS formula `-N'(d1) * (2rT - d2σ√T) / (2Tσ√T)` — q=0.
- T_MIN floor of 1/365 prevents singularity for vanna/charm computation.
- Risk-free rate hardcoded `r=0.05`.

### Assumption risks
| Risk | Severity | Why it matters |
|---|---|---|
| **Mixed greek sources** — CBOE gamma + BS vanna/charm | High | Inconsistent: GEX uses American gamma, but VEX/CHEX use European approximations. Be ready to defend. |
| q=0 dividend assumption for SPY/QQQ/IWM | Medium | SPY div yield ~1.2%, QQQ ~0.5%, IWM ~1.4%. For vanna/charm at long-dated expiries (>180d), this introduces non-trivial error. |
| Hardcoded `r=0.05` | Medium | Currently real risk-free is closer to ~4.3%. Small effect on greeks but it's a "you don't update your discount rate?" question. |
| BS European for American options | Medium-High | Charm and vanna ignore early-exercise boundary. Defensible for puts (rarely exercised early on non-div), weaker for deep ITM calls near ex-div. |
| `T_MIN = 1/365` floor inconsistency | Low (latent) | **Correction:** charm uses `t_guarded = max(t, T_MIN)` AND explicit zero override below T_MIN. Vanna uses raw `t` with no floor at all (greeks_engine.py:68). Different inconsistency than first claimed. **In practice harmless** because `min_dte=1` is locked at data layer (data_loader.py:53), so `t ≥ 1/365` always. Becomes active only if 0DTE ever turned on. Fix when touching that code; not pre-demo critical. |

### Hardening
- **P0** Wire `r` to a live source (FRED 3M T-bill or similar) and display it in the report footer. One line of code, kills a class of question.
- **P0** Document the mixed-source model clearly in the methodology footer (you already mention it; make it more prominent).
- **P1** Add q (dividend yield) as a per-ticker config (SPY 1.2%, QQQ 0.5%, IWM 1.4%) — use forward dividend yield from a public source. Re-derive vanna/charm with q. Numerical impact will be modest but the *answer to "do you account for dividends?"* should be yes.
- **P1** Audit the T_MIN inconsistency in `bs_vanna` — either apply the same explicit zero-override as charm, or document why vanna's behavior at T→0 doesn't need it. Right now this is a latent bug per your project memory (commit 1e02633 fixed a vanna sign issue — this is adjacent territory).
- **P2** Spot-check a handful of CBOE gamma values against your own BS calc. If they diverge significantly on near-expiry ITM/OTM, you've got a story for *why* mixing is fine.

### Q&A prep
- "Why two different greek models?" → "CBOE publishes gamma using their American model — strictly better than my BS. They don't publish vanna/charm, so I compute those with BS-European. Yes, it's mixed; the alternative is ignoring vanna/charm entirely or rolling my own American model."
- "Dividends?" → If P1 done: "Yes, q applied per ticker." If not: "Currently q=0 — material impact is on long-dated vanna/charm only; gamma is from CBOE's model which already handles dividends."
- "Risk-free rate source?" → After P0: "FRED 3M T-bill." Before P0: "Hardcoded 5%, fix in flight."

---

## Section 3 — Exposure (`gex/exposure_engine.py`)

### Claim
"Net GEX = Σ sign × γ × OI × 100 × S² × 0.01. Calls positive, puts negative. Positive net GEX = dealers net long gamma (stabilising)."

### Formula sanity
- `GEX = sign * gamma * OI * 100 * spot² * 0.01`
- `VEX = sign * vanna * OI * 100 * spot * 0.01`
- `CHEX = sign * charm * OI * 100 * spot * 0.01`
- Sign: +1 call, -1 put.

### Assumption risks (the load-bearing one)
| Risk | Severity | Why it matters |
|---|---|---|
| **"Calls long / puts short for dealers"** | Critical | This is the entire interpretation. Empirically true for SPY/QQQ/IWM index options *on average* — institutional flow is heavy in protective puts (dealers short puts) and covered-call programs (dealers long calls). On single names, the convention often inverts. Your scope-lock to SPY/QQQ/IWM is exactly right; **be ready to articulate why this convention holds for indices specifically**. |
| Sign convention literature | Medium | SpotGamma, Squeezemetrics, GS published research all use this. Cite when challenged. |
| The `0.01` factor — "GEX per 1% move" | Low | Standard retail convention. Some sources scale per-point or per-dollar. Be explicit: your numbers are "$ change in dealer delta per 1% move in spot." |
| Net GEX magnitude is **methodology-dependent** | High | Already noted in your footer. Barchart uses 4 nearby expiries, InsiderFinance includes 0DTE — your numbers won't match theirs absolutely. Sign and ZGL are robust; magnitude is not. **Pre-empt this.** |
| Sum across expiries treats all expiries equal | Medium | A $1B GEX position in 2027 LEAPS doesn't hedge the same way as a $1B in 0–7 DTE. No expiry weighting. |

### Hardening
- **P0** In the report header, add one line: "Convention: dealers long calls, short puts. Valid for SPY/QQQ/IWM; inversion possible on single names — out of scope by design."
- **P1** Add a "near-dated GEX" column alongside total — sum of GEX for ≤30 DTE. Gives the reader the "what's actually hedge-active right now" number vs. the structural total.
- **P1** Add an **expiry breakdown** table: GEX by expiry bucket (≤7d, 8–30d, 31–90d, 91+). This is one of the most-asked questions and you don't currently surface it.
- **P2** Sensitivity: report net GEX at spot ±1%, ±2% as a column. Tells you how much hedging flow is "in the room" near current price.

### Q&A prep
- "How do you know dealers are long calls and short puts?" → "It's the standard convention used by every major sell-side gamma desk. Backed by institutional flow data showing protective put dominance and covered-call writer demand. It empirically holds on broad index ETFs; we explicitly scoped to SPY/QQQ/IWM for that reason."
- "What if I'm a single-stock PM?" → "This tool's wrong instrument for that. The sign convention can flip — e.g. heavy retail call buying on memes inverts the dealer position. Single-name GEX needs trade-level data, not just OI."
- "Your number doesn't match Barchart" → "Different methodologies. We use ≥1 DTE full chain, they use 4 nearby expiries. Sign and ZGL agree across sources; absolute magnitudes don't."

---

## Section 4 — Analytics (`gex/analytics.py`)

### Claim
"Zero-gamma level = spot where net GEX flips sign. Call/put walls = strikes with extreme positive/negative GEX. Regime = positive | neutral | negative."

### Formulas
- ZGL: linear interpolation between adjacent grid points where sign of net GEX flips. Grid: 200 points across spot ±15%.
- Call wall: strike with largest positive GEX (single strike, not cluster).
- Put wall: strike with largest negative GEX.
- Regime: `neutral` if `|net_gex| < 200M` OR `|net_gex|/|max_strike_gex| < 0.5%`; otherwise sign of net_gex.

### Assumption risks
| Risk | Severity | Why it matters |
|---|---|---|
| ZGL grid width = ±15% | Medium | If true ZGL is outside ±15% (e.g. deeply negative regime), you return None and the report shows "—". Quietly silent failure. |
| ZGL grid resolution = 200 points | Low | Step size at SPY 600 = ~0.9 / step. Linear interpolation between is fine, but worth noting. |
| Wall = single strike | High | A "wall" in market-speak is usually a *cluster*. Reporting just the max strike misses adjacent strikes that aggregate larger. Easy gotcha. |
| `NEUTRAL_ABS_FLOOR = $200M` | Medium | **Correction (audited 2026-05-07): the floor IS binding for IWM.** 2026-05-06 snapshot: SPY +$3.8B, QQQ +$2.2B, IWM -$78M. IWM falls below the floor and gets pinned to neutral by it. So the floor is not dead code — it's actively driving IWM's regime call. Decide: is that the right call (small-cap genuinely indeterminate?) or should the floor be per-ticker? Calibration source was XLF/EFA/EWJ/TLT noise (~$94M p75), which is closer to IWM's magnitude than to SPY's. |
| `NEUTRAL_BAND_PCT = 0.5%` of |max strike GEX| | Medium | The relative band is the actual binding constraint for SPY/QQQ/IWM. Worth showing the math: if max strike GEX is $5B and net is $20M (0.4%), you flag neutral. That's a defensible heuristic. |
| Wall labeling assumes positive=call wall, negative=put wall | Low | True under your sign convention; circular but consistent. |

### Hardening
- **P0** Display **net GEX, max strike GEX, and the ratio** in the report — exposes the regime calc directly. Reader can see why "neutral" was chosen.
- **P0** When ZGL is None (off-grid), explicitly say "ZGL outside ±15% band (regime is deeply [pos/neg])" rather than just "—".
- **P1** Replace single-strike wall with **clustered wall**: top-3 strikes within ±2% of max, summed. Report both the cluster center and the cluster's GEX. This is what a desk PM expects when they hear "wall."
- **P1** Calibrate `NEUTRAL_ABS_FLOOR` per-ticker. Or, drop it and rely on the relative band. Right now it's dead code for in-scope tickers — explain or remove.
- **P2** Widen grid to ±25% with a fallback, or auto-expand until first sign-change found.

### Q&A prep
- "What is your wall, exactly?" → After P1: "Top-3 strikes within 2% of the max-GEX strike, summed." Before: "Single strike with max GEX. I should cluster — already on the list."
- "Why does this say neutral?" → Show the ratio. "Net is $X, but max strike is $Y. Net/max = 0.3%, below my 0.5% band → neutral."
- "What sets the neutrality threshold?" → Honest answer: "0.5% of max strike GEX. Calibrated against noise on out-of-scope tickers. For SPY/QQQ/IWM the absolute floor is dead — relative band is what binds. Open to better calibration if you have a view."

---

## Section 5 — Validation (`gex/validation.py`)

### Claim
"Daily snapshot saved to parquet; vs-yesterday classification (FLIPPED / INTENSIFIED / EASED / UNCHANGED). Event-study on stored history."

### What's working
- Snapshot append is idempotent on (date, ticker)
- `load_yesterday` uses NYSE calendar — won't crash on Mondays
- `_classify_vs_yesterday` thresholds: ratio > 1.05 = INTENSIFIED, < 0.95 = EASED, else UNCHANGED
- `event_study` joins snapshots with yfinance prices, computes next-N-day return + range, splits by regime

### Assumption risks
| Risk | Severity | Why it matters |
|---|---|---|
| **History is N=1** | Critical | Verified against parquet 2026-05-07: only 2026-05-06 is in the store. Today's run will be the first that produces a non-None vs-Yesterday value. The event study cannot run. **Do not lead with regime-conditional return statistics** — there is no data yet. |
| 5% threshold is arbitrary | Low | INTENSIFIED/EASED at ±5%. Defensible as "noticeable change" but no statistical basis. |
| `event_study` uses yfinance close-to-close | Low | OK for a sanity check. For real validation, intraday data needed. |
| No statistical test on event_study output | High | Just prints means. No t-test, no bootstrap, no multiple-testing correction. He'll ask "is this difference significant?" and the answer is currently "I print the means, you decide." |

### Hardening
- **P0** Be honest about sample size in the report and in the conversation. "We have N days of history" — print N. Don't show event-study output until N ≥ ~30.
- **P0** Set up the daily run on Task Scheduler so the history actually accumulates. Per memory, this was deferred. Now is the time.
- **P1** Backfill: pull historical CBOE snapshots if accessible (they may not be — CBOE delayed-quotes endpoint only serves current). If not, pull from a paid source (ORATS, Polygon) for 1 year of history. Without backfill, the event study is dead until late 2026.
- **P1** When ≥30 days, add a t-test (or Mann-Whitney) on next-day return by regime, with explicit p-value and an N too small/sufficient flag.
- **P2** Replace yfinance with the CBOE snapshot's spot at T+1 — closer to apples-to-apples. yfinance close may differ.

### Q&A prep
- "How long have you been collecting?" → Print N. Be exact.
- "Have you tested whether this works?" → "Not yet — sample size is N=3 as of today. The framework is in place; the validation lags the build by design. If you want me to backfill via a paid feed, that's the unlock."
- "What would significant look like?" → "Next-day return mean by regime, t-test or Mann-Whitney on the difference. With ~50 days per regime I'd expect to detect a 30bp daily-return difference at p<0.05. Currently I have 1 day per regime."

---

## Section 6 — Report (`gex/report.py`)

### Issues
- Methodology footer is good — keep it, **make it more prominent** (not just at the bottom in 10px gray).
- Header doesn't show: snapshot timestamp, risk-free rate, dividend assumptions, history length.
- "Early exercise strikes" column on Purpose table — flag for covered-call writers — sound but undocumented.
- vs-Yesterday color coding is good but won't make sense without calibration history.

### Hardening
- **P0** Add a "Run metadata" strip at the top: as-of date, snapshot timestamp, history length (N days), risk-free, ticker scope. Lets the reader know exactly what they're looking at without scrolling.
- **P0** Add a one-line "Read this first" caveat block above the tables: "Sign and order of magnitude are robust. Absolute GEX magnitude is methodology-dependent. ZGL/walls are load-bearing."
- **P1** Add the expiry-bucket breakdown table mentioned in §3.
- **P2** Add a glossary tooltip/legend at bottom explaining GEX, VEX, CHEX, ZGL, regime — so a reader unfamiliar with the terms doesn't misread.

---

## Concession script (things you SAY upfront, don't wait to be asked)

Practice this as a 60-second opener:

> "Three things to flag before you look at this:
>
> 1. **Data is delayed.** CBOE quotes are 15-min lag, OI is prior-session close. Real-time would need a paid feed.
> 2. **Sign and ZGL are load-bearing; absolute magnitude is not.** Different sources (Barchart, SpotGamma, InsiderFinance) all produce different absolute GEX. The directional read is robust; the dollar number is methodology-specific.
> 3. **Validation is forward-looking.** I started collecting snapshots [X] days ago. The event-study framework is in place but I don't have enough history to claim regime-conditional returns are statistically real yet. That's the next milestone."
>
> "Beyond that — happy to dig into any number on the page. Tell me where you'd want to use this and I'll either tell you it fits or tell you what would have to change."

---

## Priority queue — what to ship before the meeting

**P0 (must-do, ~1 day):**
1. Wire `r` to FRED, display in report
2. Display snapshot timestamp + history length (N days) at top of report
3. Replace single-strike walls with clustered walls (§4 P1) — actually move to P0, this is the most likely immediate gotcha
4. Add concession block above tables
5. Schedule daily run via Task Scheduler so N grows
6. Fix `bs_vanna` T_MIN consistency with `bs_charm`

**P1 (should-do, ~2-3 days):**
7. Per-ticker dividend yield in vanna/charm
8. Expiry-bucket breakdown table
9. Near-dated (≤30 DTE) GEX column
10. Statistical test on event-study output (gated on N ≥ 30)
11. Self-Q&A drill — write 20 questions in his voice, write your answers, identify gaps

**P2 (nice-to-have):**
12. 0DTE A/B toggle
13. Bloomberg ground-truth one-day comparison
14. Backfill historical snapshots via paid feed
15. Glossary in report

**Pre-meeting drill:**
- Run through every section's Q&A prep out loud
- Open the HTML report and click through every cell — for each, can you state in one sentence what it is and what could be wrong with it?
- If any cell stumps you, that's a study item

---

## What to NOT change before the meeting
- Don't add more signals/sleeves/scope
- Don't refactor architecture
- Don't add charts beyond what's there
- Don't write a "v4" plan
- The pitch is "POC + open to direction" — over-polish reads as "already decided"
