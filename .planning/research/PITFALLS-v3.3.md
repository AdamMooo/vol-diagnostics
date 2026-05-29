# Domain Pitfalls — v3.3: Surface Evolution & Daily Intelligence

**Domain:** Building change-over-time vol-surface analytics + a richer daily email on top of an RBF/TPS-interpolated implied-vol surface, for a solo descriptive (non-predictive) options tool
**Researched:** 2026-05-29
**Confidence:** HIGH on the interpolation/delivery mechanics (verified against scipy docs + plotly/Kaleido issue tracker + the actual `analytics.py` / `surface_history.py` code); MEDIUM on PCA/decomposition (small-sample statistics, no project history yet to test against)

---

## The central risk, stated plainly

Everything in v3.3 reads off one object: an RBF thin-plate-spline surface built by `plot_vol_surface()` / `plot_iv_change_surface()` / `_rbf_grid()` in `gex/analytics.py` (scipy `RBFInterpolator`, `kernel="thin_plate_spline"`, `smoothing=1.5`, 40×30 grid, ±15% OTM clip, DTE floor 5). The TPS kernel is biharmonic — its basis function grows like `r²·log r`, i.e. **unbounded away from the data**. There is no convex-hull guard: `RBFInterpolator` happily extrapolates, and the only safety net in the code today is `np.clip(IV, 0.0, None)`, which masks the *symptom* (negative IV) while keeping the *disease* (fabricated structure in unsupported regions). Every derived metric — level/skew/term ΔIV, the merged Skew tab, PCA factors, the email — inherits whatever the surface invents.

**Therefore Phase 8 (validation) must come first and must gate the rest.** The deliverable of Phase 8 is not a prettier surface; it is a *coverage mask* + a *fit-honesty check* that every downstream consumer respects. The single most important rule in this whole document: **never read a metric off a grid cell that has no real quote near it.** Phase 8 builds the mask; Phases 9/10/11 must refuse to compute, display, or email values outside it.

---

## Critical Pitfalls

### Pitfall 1: TPS extrapolating wildly beyond the data, masked by the zero-clip

**What goes wrong:**
The grid (`otm_grid = linspace(-clip_pct, clip_pct, 30)`, `dte_grid = linspace(dte_min, dte_max, 40)`) is a full rectangle. Real quotes are scattered and sparse — especially in the corners (far-OTM × long-DTE, far-OTM × short-DTE). TPS fills those corners by extrapolating a `r²·log r` surface, which curves away steeply once you leave the data. The current code does `IV = np.clip(IV, 0.0, None)` precisely because TPS was producing *negative* IV at boundaries. That clip turns an obviously-wrong value (−4% IV) into a plausible-looking one (0%, or whatever the curvature gives just inside the clip), which is worse: a reviewer sees a smooth surface and trusts it.

**Why it happens:**
TPS is "smooth by construction," so it always *looks* right. The eye reads a continuous coloured surface as data. There is no visual cue distinguishing "interpolated between 8 real strikes" from "extrapolated from the nearest quote 6% of moneyness away."

**How to avoid (Phase 8 — the core deliverable):**
Build a **support/coverage mask** and apply it everywhere. Concretely, in numpy/scipy with no new deps:
1. After building `pts` (the real `[dte, pct_otm]` quote locations, post-clip, post-DTE-floor), compute for each grid cell its distance to the nearest real quote in the **normalized** space (`pts / pts_std`, the same scaling the RBF uses). `scipy.spatial.cKDTree(pts/pts_std).query(grid_pts/pts_std)` gives nearest-neighbour distance per cell in one call.
2. Define a coverage radius (e.g. cells whose nearest real quote is > `COVERAGE_MAX_NN_DIST` in normalized units are "unsupported"). Tune the radius once against a dense day so that the supported region visually matches where quotes actually are.
3. Set unsupported cells to `np.nan` in the `z` array. Plotly `go.Surface` renders NaN as a hole — honest. (The project already accepted "honest holes" — see commit `ad8b017` "honest holes" and `3bed07b`.) Keep that philosophy; v3.3 must not regress it for the sake of a full-looking rectangle.
4. **Do not rely on the zero-clip as a fit check.** Keep `np.clip(IV, 0.0, None)` as a last-resort guard, but log/count how many cells it touches — a high count means the surface is extrapolating into nonsense and the mask should already have removed those cells.

**Warning signs:**
- IV rising toward the OTM corners instead of forming a normal smile/smirk that flattens.
- The clip touching > a handful of cells (instrument it: `(IV_raw < 0).sum()`).
- Surface shape changing dramatically day-to-day in the corners while the ATM region is stable (corners are extrapolation; ATM is interpolation).

**Phase to address:** **Phase 8.** This mask is the reason Phase 8 exists.

---

### Pitfall 2: Inventing a smile from 2–3 strikes at a far DTE

**What goes wrong:**
A back-month expiry (e.g. 150 DTE) may have only 2–3 liquid OTM strikes after `MIN_OI=100` filtering. TPS will still draw a full curved smile across the entire ±15% OTM range at that DTE, because it interpolates a 2D surface, borrowing curvature from *other* DTEs. The result is a confident-looking smile at a DTE where the chain has almost no information. Reading 25Δ skew or ATM term-structure off that slice (Phases 9/10) produces a number with no empirical support.

**Why it happens:**
2D RBF couples the axes: a sparse DTE slice gets its shape "donated" by neighbouring well-populated DTEs. This is desirable for smoothing but dangerous for inference — you cannot tell from the surface alone which slices are real and which are borrowed.

**How to avoid:**
1. **Per-DTE quote-count gate.** Before exposing any DTE slice to skew/term/PCA, require ≥ N real OTM strikes spanning both wings at that expiry (suggest N≥5, with at least one quote on each side of ATM). Expose this as `SURFACE_MIN_STRIKES_PER_EXPIRY` in `config.py`.
2. The skew metric already has `SKEW_MIN_DTE=7` and delta-targeting — keep computing **skew directly from raw quotes**, never from the interpolated grid. (Today `compute_skew_25d` works off the chain, not the surface — preserve that separation in v3.3. The surface is for *visualization*; metrics come from *quotes*.)
3. For the surface plot itself, mask DTE columns that fail the per-expiry count (NaN the whole column) so the viewer doesn't see a fabricated back-month smile.

**Warning signs:**
- A perfectly smooth smile at a DTE where you know only a few strikes trade.
- Skew/term values at long DTE that are suspiciously close to the front-month values (sign of borrowed curvature).

**Phase to address:** **Phase 8** (mask + per-expiry gate); enforced by **Phases 9 & 10** (consumers must check the gate).

---

### Pitfall 3: `smoothing=1.5` is arbitrary and unvalidated

**What goes wrong:**
`smoothing=1.5` was hand-picked. It is applied in **normalized** coordinates (`pts/pts_std`), so its effective strength depends on the spread of that day's quotes — a sparse day and a dense day get different *effective* smoothing from the same constant. This is the same class of error the project already burned on twice: the `$200M` GEX neutral floor and the categorical regime label, both cut for being "hand-tuned and non-stationary."

**Why it happens:**
A smoothing parameter that produces a nice-looking surface on the day you tuned it feels "done." Non-stationarity (different quote density on different days) silently changes its meaning.

**How to avoid:**
1. **Document the choice and its non-stationarity** in the surface docstring and methodology footer, exactly as the project documents other tuned constants. Move it to `config.py` as `SURFACE_RBF_SMOOTHING` so the assumption is visible in one place (consistent with the config.py philosophy already in the file header).
2. **Do not chase a "data-driven" smoothing via naive leave-one-out CV** — see Pitfall 4 for why it misleads on this interpolant.
3. **Validate by held-out *strikes*, not held-out *points*** (Pitfall 4). A defensible smoothing is one where dropping a real strike and predicting it back gives small error *and* the surface doesn't develop oscillations between strikes.
4. Pick smoothing for *robustness*, not minimal in-sample error: prefer slightly more smoothing (flatter, fewer invented wiggles) over less, since the tool is descriptive and over-fit wiggles read as fake structure.

**Warning signs:**
- Surface shape sensitive to adding/removing a single strike.
- Visible oscillation (ringing) between adjacent real strikes at the same DTE.

**Phase to address:** **Phase 8.**

---

### Pitfall 4: Naive cross-validation lies on a smooth-by-construction interpolant

**What goes wrong:**
The obvious validation — leave-one-point-out CV, predict it back, report RMSE — will report a *flattering* error and can pick a *too-low* smoothing. Reason: adjacent strikes at the same expiry are highly correlated (the smile is locally near-linear), so leaving one out and predicting from its immediate neighbours is trivial. Low CV error says nothing about whether the surface fabricates structure in the *gaps and corners* where there are no neighbours — which is exactly where the danger is. You can have near-zero LOO-CV RMSE and a surface that diverges to nonsense 4% OTM further out.

**Why it happens:**
CV measures interpolation quality *near data*. The failure mode here is *extrapolation away from data*. CV by construction never tests the empty regions, so it cannot detect the problem it's being trusted to detect.

**How to avoid:**
1. **Leave-one-*expiry*-out or leave-one-*wing*-out, not leave-one-point-out.** Drop an entire expiry's worth of strikes (or one full wing of a smile), refit, and check how badly the surface reconstructs that held-out structure. This tests the borrowing-from-neighbours behaviour that Pitfall 2 describes.
2. **Separate the two questions:** (a) "Does the surface fit the quotes it has?" — answerable by CV. (b) "Does it invent structure where it has no quotes?" — answerable only by the coverage mask (Pitfall 1) + a monotonicity/shape sanity check, not by CV.
3. **Shape sanity checks** (cheap, numpy-only, run per surface): no-calendar-arbitrage proxy (total variance `IV²·T` non-decreasing in T along an OTM slice — flag violations, don't enforce); smile convexity in the wings (second difference shouldn't flip sign repeatedly between real strikes).
4. Report CV error *only* alongside coverage % — never CV error alone, which would be the "decorating noise" trap from v3.2's Pitfall 1.

**Warning signs:**
- Glowing LOO-CV numbers paired with visibly weird corners — that's the tell that you measured the wrong thing.

**Phase to address:** **Phase 8.**

---

### Pitfall 5: ΔIV comparison differencing interpolated-vs-interpolated nonsense

**What goes wrong:**
`plot_iv_change_surface()` interpolates today and prior *independently* on a shared grid, then subtracts. If the two days have **different real-data support** (e.g. an expiry rolled off, or prior day had a strike today doesn't), large regions of the difference are `interpolated_today − extrapolated_prior` — a difference of two fabrications. The code masks each surface to NaN only when `len(iv_v) < 6` *for the whole day*; it does **not** mask per-cell where one day lacks support. The 97th-percentile colour scaling (`np.nanpercentile(np.abs(IV_diff), 97)`) then keys the entire colourmap off these possibly-fake extremes.

**Why it happens:**
The grid is shared, so the subtraction is mechanically valid (same shape). "Same grid" is mistaken for "same support." The eye sees a clean RdBu_r difference surface and reads the red/blue corners as "vol moved here" when really "the surface guessed differently here on two days with no data."

**How to avoid:**
1. **Intersect the coverage masks.** A ΔIV cell is valid only if *both* days have real-quote support there (reuse the Pitfall-1 cKDTree mask for each day, `mask_today & mask_prior`). NaN everywhere else. The honest ΔIV surface will have holes — that is correct.
2. **Scale the colourmap off masked cells only** (`np.nanpercentile` over the intersected-mask region), so a fabricated corner can't blow out the scale.
3. **The current `abs_max` floor of 0.5pp** is reasonable to keep scale readable, but apply it *after* masking.

**Warning signs:**
- ΔIV showing large moves concentrated in corners (far-OTM × extreme-DTE) rather than near ATM.
- ΔIV regions that flip dramatically when you change which prior date you compare to (sign that you're differencing extrapolations).

**Phase to address:** **Phase 9** (evolution), built on the **Phase 8** mask.

---

### Pitfall 6: DTE-axis misalignment when the front expiry rolls off

**What goes wrong:**
"% OTM × DTE" looks like a stable coordinate system, but **DTE of a fixed expiry decreases by ~1 each day, and expiries roll off entirely.** Comparing today's surface to N-days-ago on the DTE axis silently compares *different contracts*: today's "30 DTE" slice and the prior surface's "30 DTE" slice are different expirations. A vol move attributed to "30 DTE" may just be the calendar rolling. The `dte_min`/`dte_max` intersection in `plot_iv_change_surface` bounds the overlap but does not fix the semantic mismatch — it just trims the axis.

**Why it happens:**
Constant-DTE is the standard surface convention (it *is* the right normalization for a level/skew/term view), but the comparison reads as "same point" when it's "same constant-maturity coordinate, different underlying contracts." Both readings are legitimate; conflating them is the error.

**How to avoid:**
1. **Be explicit about which comparison you're showing.** Constant-maturity ΔIV (what the code does) answers "is the 30-day vol surface higher than it was?" — a valid, standard question. State that in the title/footer: "constant-maturity; not the same contracts."
2. **Do NOT attempt fixed-expiry tracking** unless you store an expiry-date key per quote and match expiries across days — that's more machinery than this descriptive tool needs, and back-months roll out of the window anyway. Constant-maturity is the right default; just label it honestly.
3. **Guard the DTE floor interaction:** with `_DTE_FLOOR=5`, an expiry at 6 DTE today drops below the floor tomorrow. The constant-maturity grid handles this gracefully (it never goes below 5), but the *front* of the surface is where support is thinnest day-to-day — combine with the coverage mask.

**Warning signs:**
- A persistent ΔIV stripe at the short-DTE end that tracks the trading calendar (appears/strengthens as expiries approach the floor).

**Phase to address:** **Phase 9.**

---

### Pitfall 7: "Nth day back" is not N trading sessions

**What goes wrong:**
v3.3 adds 5d/20d evolution horizons. `surface_history.py` stores rows keyed by `datetime.date.today()`. If horizon logic does `today - timedelta(days=5)` or "the row 5 positions back," it breaks: calendar arithmetic lands on weekends/holidays (no data), and "5 positions back in the store" is only 5 sessions if the store has no gaps. A missed run (the machine was off, a holiday, a fetch failure) silently makes "5 days back" actually 7 calendar days or 6 sessions. The project already owns `pandas_market_calendars` — use it.

**Why it happens:**
`date.today()` and naive row-indexing are the path of least resistance. Gaps in the store are invisible until a comparison straddles one.

**How to avoid:**
1. **Resolve horizons against the actual stored dates,** not calendar math. `list_available_dates(ticker)` (already in `surface_history.py`) returns sorted dates; index into *that* for "N sessions back," and assert the gap between consecutive dates is a single trading day using `pandas_market_calendars` (already a dependency).
2. **Surface the real gap to the user:** label the comparison with the *actual* prior date and session count ("today − 2026-05-21, 5 sessions"), which `plot_iv_change_surface` already takes as `label_prior` — feed it the resolved date, never a nominal "5d ago."
3. **Refuse the comparison if the store has a hole** in the requested span, or fall back to the nearest available session *and say so*.

**Warning signs:**
- "5-day" ΔIV that's suspiciously large after a long weekend or a missed run.
- Off-by-one between the label and the true session count.

**Phase to address:** **Phase 9.**

---

### Pitfall 8: Spot-normalization error when spot moves

**What goes wrong:**
The % OTM axis is `(strike/spot − 1)×100`, using *that day's* spot (correctly stored per-row in `surface_history.py`). This is right — but two subtle traps remain: (a) if any code path ever normalizes the prior day's strikes by *today's* spot (or by a scalar-store spot that disagrees with the per-row spot), the % OTM axes misalign and the ΔIV is garbage; (b) a large spot move between the two days means the *same strike* maps to very different % OTM, so a given % OTM cell is supported by different strikes on the two days — compounding Pitfall 5.

**Why it happens:**
There are two spot sources (the per-row spot in `surface_history` and the scalar store in `gex_snapshots.parquet`). Using the wrong one, or mixing them, is an easy silent bug. The code comment in `surface_history.py` explicitly stores spot per-row "so callers never need to look it up elsewhere" — that contract must be honoured.

**How to avoid:**
1. **Always normalize each day's strikes by that day's stored per-row spot.** `load_surface_snapshot` returns `(df, spot)` — use the returned spot, never re-fetch. `_rbf_grid` already takes `spot` as a parameter; ensure callers pass the *snapshot's* spot for the prior day, not today's.
2. **Add a regression test:** a day with a known 3% spot move should still align ATM (% OTM = 0) across both surfaces.
3. On large spot moves, the coverage-mask intersection (Pitfall 5) automatically shrinks the valid region — which is correct behaviour, not a bug to "fix" by widening the band.

**Warning signs:**
- ATM (% OTM ≈ 0) showing a large ΔIV on a day with a big underlying move (ATM vol is usually the *most* stable point; a big ATM ΔIV after a spot jump smells like a normalization bug).

**Phase to address:** **Phase 9.**

---

### Pitfall 9: Small-sample instability of 5d/20d horizons early on

**What goes wrong:**
The surface store starts near-empty. A 20-session horizon needs 20 sessions of stored surfaces per ticker; today there may be only a handful. Same class of error as v3.2 Pitfall 1 (percentile on 9 days). A "20-day surface evolution" computed from 4 stored days is noise dressed as a trend.

**How to avoid:**
1. **Gate each horizon on availability.** If fewer than the required sessions exist, show "Accumulating (N/20 sessions)" — reuse the exact pattern from v3.2's percentile gating. Add `SURFACE_HORIZONS` and require the store depth before rendering each.
2. **Ship the feature, degrade the display.** Same philosophy as v3.2: structural release now, full value after accumulation.

**Warning signs:** A 20d ΔIV that exists when the store is younger than 20 sessions.

**Phase to address:** **Phase 9** (gating); the data accumulates regardless once `run_daily` writes surfaces.

---

### Pitfall 10: PCA over-interpretation on a tiny, non-stationary sample

**What goes wrong:**
Decomposing surface evolution into level/slope/curvature factors (PCA on the time series of surface grids, or on ATM-term / skew-term vectors) is seductive but treacherous here: (a) with < ~30–60 sessions the factor loadings are unstable and will reshuffle as data arrives; (b) PCA assumes a stationary covariance — vol regimes are not stationary, so factors fit across a regime break are meaningless mixtures; (c) **sign is arbitrary** — `np.linalg.svd`/`eig` can flip the sign of any component run-to-run, so "level went up" might be a sign flip, not a market move; (d) feeding PCA the *interpolated grid* re-introduces all of Pitfalls 1–2 (fabricated cells get variance-weighted into factors).

**Why it happens:**
"Level/slope/curvature" is the canonical vol-surface PCA result (it always comes out that way for rates and vol), so it feels validated. But the canonical result is *why you don't need PCA to find it* — and a tiny sample makes the higher factors pure noise.

**How to avoid:**
1. **Strongly consider deferring PCA out of v3.3.** The first three factors of any vol surface are almost always level, term-slope, and skew — which the tool *already measures directly* (ATM term structure, skew term structure). PCA would re-derive what's already shown, at the cost of a non-stationary, sign-ambiguous, small-sample model. This is a textbook "build SVI when TPS + honest flags would do" feature-creep trap (see Pitfall 15).
2. **If PCA ships anyway:** run it on *masked real-quote-derived* vectors (ATM-by-DTE and skew-by-DTE series), never the raw interpolated grid; pin sign conventions (force loading[0] > 0, or anchor the level factor to be positively correlated with ATM IV); require ≥ `PCA_MIN_SESSIONS` (≥40) before display; show only the first 2–3 factors and label them descriptively, never as predictors; report % variance explained so a PM can see when factor 3 is noise.
3. **No reconstruction-for-forecasting.** PCA here is descriptive attribution of *past* moves only — banned-word list from v3.2 Pitfall 4 applies.

**Warning signs:**
- Factor loadings that change shape week to week.
- A "curvature factor" explaining < 5–10% variance being shown as if meaningful.
- Sign flips between runs.

**Phase to address:** **Phase 9** (if built at all) — but the recommendation is **defer / cut** unless the roadmap explicitly justifies it over the existing direct term/skew measures.

---

### Pitfall 11: Kaleido on Windows — hangs, first-call latency, Chromium bundling

**What goes wrong:**
v3.3's richer email embeds surface images. Plotly static export goes through Kaleido, which drives a headless Chromium. On Windows this has a long documented history of: first-call latency (cold Chromium launch, several seconds), outright hangs on `write_image`, and version-coupling pain between `kaleido`, `plotly`, and the bundled Chromium. The legacy `kaleido` (v0.x) is especially flaky on Windows; the re-architected `kaleido` v1 (Choreographer-based, 2024+) is more reliable but is a different install and API surface. 3D `go.Surface` figures are heavier to render than 2D and exacerbate first-call latency.

**Why it happens:**
Headless-browser image export is inherently fragile, and Windows is the worst-supported platform historically. A daily scheduled job that hangs silently produces no email and no error anyone sees until someone notices the email stopped.

**How to avoid:**
1. **Pin versions explicitly** in `requirements.txt` (plotly + kaleido together) and prefer kaleido v1. Re-test export after any plotly bump.
2. **Warm-up call + timeout watchdog.** Do one throwaway `write_image` at process start to absorb first-call latency, and wrap each real export in a timeout (subprocess/thread with a hard kill) so a hang degrades to "email without that image" instead of a stuck job. The project already isolates COM in a subprocess (v3.0 DASH) — same pattern.
3. **Render surfaces as 2D, not 3D, for the email.** A 3D `go.Surface` exported to a static PNG is nearly unreadable (no rotation, perspective ambiguity — see Pitfall 12). A 2D heatmap (`go.Heatmap` of the same masked grid) exports cleanly, renders fast, and is *more* legible in email. This also dovetails with the standing memory note "vol surface should be 2D not 3D."
4. **Always have a fallback:** if export fails/times out, the email sends with a text note ("surface image unavailable today") — never block the whole send. Mirrors v3.2's "fallback gracefully" rule for VRP.

**Warning signs:**
- The daily job occasionally produces no email with no traceback (silent hang).
- First email after a reboot is slow or times out.

**Phase to address:** **Phase 11** (report/email); the 2D-vs-3D decision also touches **Phase 10** (dashboard can keep interactive 3D; email cannot).

---

### Pitfall 12: 3D Plotly surfaces render poorly as static PNG

**What goes wrong:**
The interactive `go.Surface` (rotatable, hover) is genuinely useful in Streamlit. Flattened to a single static camera angle in an email, it loses depth cues, occludes its own back face, and the colourbar + skewed axes become hard to read at email width. The fixed camera (`eye=dict(x=2.0, y=-1.2, z=0.8)`) was tuned for the dashboard, not for a small static raster.

**How to avoid:**
- **Email = 2D heatmap; dashboard = 3D interactive.** Build the email image from the same masked grid as a `go.Heatmap` (% OTM on one axis, DTE on the other, IV as colour). The ΔIV email image is *especially* better as a 2D RdBu_r heatmap — divergence reads instantly in 2D.
- Keep one code path producing the masked grid; two thin renderers (3D for dashboard, 2D for email) consume it. Don't fork the surface-building logic.

**Phase to address:** **Phase 10 / Phase 11.**

---

### Pitfall 13: Parquet schema drift in the surface store

**What goes wrong:**
`surface_history.py` writes columns `date, ticker, spot, dte, strike, moneyness, log_moneyness, iv_pct`. v3.3 may want to add fields (e.g. a coverage flag, expiry date for Pitfall 6/7, a quality tag). If `save_surface_snapshot` adds a column but old parquet files lack it, or column order/dtype drifts, `pd.concat([hist, df])` and downstream reads get silent NaNs or dtype-object columns. The `date` column is stored as Python `date` objects and re-coerced with `pd.to_datetime(...).dt.date` on every read — fragile if a write ever stores a string.

**How to avoid:**
1. **Pin the schema explicitly.** Define the column list + dtypes in one place; on read, reindex to the canonical columns so missing ones become typed NaN (mirror v3.2's `_FLOAT_COLS` approach in `validation.py`).
2. **Additive only** — never rename/reorder existing columns (same rule the GEX store already follows).
3. **Test both a fresh store and the existing populated store** after any schema change.
4. If adding expiry-date tracking for horizon correctness, add it as a new column now (cheap) rather than reconstructing it later from DTE (impossible after the fact).

**Phase to address:** **Phase 8** (decide the schema before accumulating more rows) and **Phase 9**.

---

### Pitfall 14: Non-idempotent re-runs corrupting the store

**What goes wrong:**
`save_surface_snapshot` is idempotent *by design* (drops today's rows before appending). Good. But the richer v3.3 pipeline adds more write steps (evolution metrics, maybe a derived-metrics store). If any new store isn't idempotent, a manual re-run or a dry-run double-appends, inflating "N sessions back" counts (feeding Pitfall 7/9) and skewing any percentile/PCA. Also: idempotency keys on `date.today()` — a run that spans midnight, or a backfill for a *past* date, writes under the wrong key.

**How to avoid:**
1. **Every store write replaces-by-date, not appends.** Copy the existing `hist[hist["date"] != today]` pattern for any new store.
2. **Make the run date explicit and injectable** (don't bury `date.today()` deep in the writer) so backfills and tests can pass a specific date.
3. **Dry-run flag must not write.** v3.3's email work will want a `--no-send` / dry-run; ensure dry-run also skips snapshot writes (or writes to a temp store), so testing the email doesn't pollute history.

**Phase to address:** **Phase 9** (stores) and **Phase 11** (dry-run / send orchestration).

---

## Scope / rigor pitfalls (the solo descriptive-tool guardrails)

### Pitfall 15: Building SVI / parametric fits when TPS + honest coverage flags suffice

**What goes wrong:**
The natural "fix" for sparse-corner extrapolation (Pitfalls 1–2) is to fit a parametric smile (SVI, SABR) per expiry — which guarantees arbitrage-free, well-behaved wings. But SVI is a calibration project: it has its own failure modes (calibration instability with few strikes, butterfly-arbitrage constraints, parameter non-identifiability on sparse chains), adds dependencies, and is exactly the kind of machinery a descriptive solo tool should avoid. `config.py` even notes "SVI would be needed to extrapolate further" beyond 180 DTE — that's an *argument for not extrapolating there*, not for building SVI.

**How to avoid:**
- **Honest holes beat parametric extrapolation.** The coverage mask (Pitfall 1) solves the real problem — don't show what you don't have — without a calibration engine. The project already chose "honest holes" in commits `ad8b017`/`3bed07b`; v3.3 should double down, not reverse it.
- If wings genuinely matter to the PM later, that's a scoped v4.x research item with backtesting, not a v3.3 surface feature.

**Phase to address:** **Phase 8** (decision: mask, don't model) — record it as a strategic decision in PROJECT.md.

---

### Pitfall 16: Evolution / decomposition language that implies prediction

**What goes wrong:**
Surface-evolution analytics ("vol rose 3pp in the 30d wing," "skew steepened over 5 sessions") slide easily into forecasts ("term structure inverting → vol spike ahead," "skew steepening signals downside"). This is the *exact* failure v3.2 Pitfall 4 and the v3.1 regime-label cut were about. ΔIV and PCA factors are descriptive of *what happened*, never *what will happen*.

**How to avoid:**
1. **Reuse the v3.2 banned-words list verbatim:** "expect, likely, should, will, predict, ahead, upcoming." Present-tense / past-tense description only: "skew steepened," "the 30d wing is 3pp higher than 5 sessions ago."
2. **No composite evolution score / traffic light.** Combining ΔIV + skew change + term change into one signal is an untested model — the recurring "compound signal temptation" from v3.2.
3. **Hardcode any narrative text** for the email, review for forward-looking language, freeze — same discipline as the GEX narrative.

**Phase to address:** **Phase 9** (metric labels), **Phase 11** (email copy).

---

### Pitfall 17: Feature creep in the "richer email"

**What goes wrong:**
"Daily intelligence" invites piling every new metric into the email: full surface, ΔIV surface, PCA factors, per-horizon tables, cross-ticker grids. The email becomes a wall the PM stops reading — negating the actionability goal, exactly like v3.2 Pitfall 8 (dashboard clutter).

**How to avoid:**
- **Email carries the *change* story, dashboard carries the *exploration*.** Email: one 2D surface heatmap + one ΔIV heatmap + the existing defensible cards. Anything requiring interaction (rotating 3D, scrubbing horizons) lives in Streamlit only.
- **Hierarchy over count.** Lead with the single most decision-relevant change; relegate detail to the dashboard link.

**Phase to address:** **Phase 11.**

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| `np.clip(IV, 0, None)` as the only fit guard | Hides negative-IV artifacts, surface looks clean | Masks extrapolation nonsense; downstream metrics read fabricated cells | Never as sole guard — must be paired with coverage mask |
| Full rectangular grid with no coverage mask | "Complete-looking" surface, no holes | Every corner is fabricated; ΔIV/skew/PCA inherit it | Never in v3.3 — mask is the milestone's reason for existing |
| `date.today()` row-indexing for "N days back" | Trivial to write | Off-by-N on holidays/missed runs; silent in ΔIV | Never — use stored-date resolution + market calendar |
| LOO-point CV to "validate" smoothing | Easy, gives a number | Flatters interpolation, blind to extrapolation | Only alongside leave-expiry-out + coverage % |
| 3D surface PNG in email | Reuses dashboard figure | Unreadable static; slow/hangs in Kaleido on Windows | Never for email — 2D heatmap instead |
| PCA on interpolated grid | One-liner with sklearn/numpy | Variance-weights fabricated cells; non-stationary; sign-ambiguous | Only on masked real-quote vectors, ≥40 sessions, descriptive-only |
| SVI per-expiry to fix wings | Arbitrage-free smiles | Calibration project, new deps, instability on sparse chains | Defer to v4.x with backtesting |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| scipy `RBFInterpolator` (TPS) | Trusting it inside the convex hull, assuming it's bounded outside | TPS is biharmonic/unbounded away from data; gate output by a cKDTree nearest-neighbour coverage mask |
| Kaleido (Windows) | Calling `write_image` on a 3D fig in a scheduled job, no timeout | Pin kaleido v1, warm-up call, timeout watchdog, 2D heatmap, fallback to text |
| `pandas_market_calendars` (already a dep) | Not using it for horizon arithmetic | Resolve "N sessions back" against actual trading days, not calendar deltas |
| Parquet surface store | Adding columns inconsistently across read/write paths | Canonical schema + reindex-on-read; additive only; test fresh + populated |
| Two spot sources (per-row vs scalar store) | Normalizing prior day by wrong spot | Always use the per-row spot returned by `load_surface_snapshot` |
| Outlook COM (email send) | Attaching/embedding from the main process, blocking on COM | Keep the existing COM isolation; embed images as base64 or attach generated PNGs, fail-soft |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Kaleido cold start | First export slow / hangs after reboot | Warm-up throwaway export at process start | Every fresh process; worst on Windows |
| RBF refit per render | Dashboard sluggish on each interaction | Cache the masked grid (Streamlit `CACHE_TTL_TICKER` already 300s); refit only on new data | When users scrub horizons/tickers rapidly |
| 3D surface export | Multi-second PNG render × 3 tickers × 2 surfaces in daily job | 2D heatmaps for email; 3D only interactive | Daily job over 3 tickers |
| Growing surface parquet | Read-whole-file on every dashboard load | Read with `columns=` projection; only load needed dates | Store grows past months of dense chains |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Full-rectangle surface with no holes | PM trusts fabricated corners as real vol | Honest NaN holes where no quotes support the grid |
| 3D surface in email | Unreadable, ambiguous depth, PM ignores it | 2D heatmap, divergence colourmap for ΔIV |
| "5-day ΔIV" with no real prior-date label | PM thinks it's 5 calendar days / exact contracts | Label actual prior date + session count; "constant-maturity" note |
| Evolution copy with forward-looking words | PM reads a prediction, loses trust when wrong | Banned-words list; past/present-tense description only |
| Email overloaded with every metric | PM stops reading | Email = change story; dashboard = exploration |

## "Looks Done But Isn't" Checklist

- [ ] **Vol surface:** renders a full rectangle — verify it has *honest holes* where no quotes support the grid (coverage mask applied, not just zero-clip).
- [ ] **ΔIV surface:** subtracts two grids — verify cells are NaN unless *both* days have real support there (intersected mask), and colour scale keys off masked cells only.
- [ ] **"N sessions back":** shows a number — verify it resolved against stored trading dates (no holiday/missed-run off-by-N) and labels the *actual* prior date.
- [ ] **Skew / term metrics:** computed — verify they read from *raw quotes*, never from the interpolated grid, and respect per-expiry strike-count gates.
- [ ] **Smoothing=1.5:** surface looks good — verify it's documented as tuned/non-stationary in config.py + footer, and validated by leave-expiry-out (not LOO-point).
- [ ] **Email image:** embeds a figure — verify it's 2D (not 3D), exports under a timeout, and the send proceeds if export fails.
- [ ] **Horizon gating:** shows a 5d/20d view — verify it degrades to "Accumulating (N/M)" when the store is too shallow.
- [ ] **PCA (if built):** shows level/slope/curvature — verify sign convention pinned, ≥40 sessions required, % variance shown, descriptive-only labels.
- [ ] **Re-run safety:** ran the pipeline twice — verify no duplicate rows in any store and dry-run wrote nothing.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Fabricated corners already shipped | MEDIUM | Add coverage mask, re-render; no historical data loss (raw quotes stored) |
| ΔIV differencing nonsense | MEDIUM | Intersect masks, rescale colour; re-render from stored snapshots |
| Off-by-N horizon | LOW | Switch to stored-date resolution; recompute (data intact) |
| Smoothing mis-tuned | LOW | Re-tune via leave-expiry-out; one config constant |
| Duplicate store rows | LOW–MEDIUM | Dedup by (date, ticker, dte, strike); fix writer idempotency |
| Kaleido hang in prod | LOW | Add timeout + fallback; email already has text path |
| PCA factors meaningless | LOW | Cut the feature; direct term/skew metrics already cover it |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| 1. TPS extrapolation masked by clip | **Phase 8** | Coverage mask renders holes; clip touch-count ≈ 0 |
| 2. Invented smile from 2–3 strikes | **Phase 8** (+9/10 consume) | Per-expiry strike gate; back-month columns masked |
| 3. Arbitrary smoothing=1.5 | **Phase 8** | Documented in config + footer; robustness-tuned |
| 4. Naive CV misleads | **Phase 8** | Leave-expiry-out used; CV reported only with coverage % |
| 5. ΔIV differencing fabrications | **Phase 9** | Intersected mask; scale off masked cells |
| 6. DTE-axis roll-off misalignment | **Phase 9** | "Constant-maturity" labeled; DTE floor interaction guarded |
| 7. "Nth day back" ≠ N sessions | **Phase 9** | Resolved via stored dates + market calendar; real date labeled |
| 8. Small-sample horizon instability | **Phase 9** | "Accumulating (N/M)" gate per horizon |
| 9. Spot normalization error | **Phase 9** | Per-row stored spot used; ATM-stability regression test |
| 10. PCA over-interpretation | **Phase 9** (or cut) | Defer unless justified; if built: pinned sign, ≥40 sessions, masked vectors |
| 11. Kaleido on Windows | **Phase 11** (+10) | kaleido v1 pinned, warm-up, timeout, 2D, fallback |
| 12. 3D PNG unreadable | **Phase 10/11** | Email uses 2D heatmap; 3D interactive only |
| 13. Parquet schema drift | **Phase 8/9** | Canonical schema, reindex-on-read, additive-only, dual store test |
| 14. Non-idempotent re-runs | **Phase 9/11** | Replace-by-date writers; injectable run date; dry-run writes nothing |
| 15. Premature SVI | **Phase 8** | Decision recorded: mask, don't model |
| 16. Predictive evolution language | **Phase 9/11** | Banned-words check; no composite score |
| 17. Email feature creep | **Phase 11** | Email = change story; hierarchy over count |

## The Phase 8 validation checklist (implementable, scipy/numpy only, no new deps)

This is the concrete deliverable that justifies Phase 8. Each item is buildable with `numpy`, `scipy.spatial`, `scipy.interpolate` (all already in the stack):

1. **Coverage mask.** Build `pts/pts_std` real-quote locations. `tree = scipy.spatial.cKDTree(pts/pts_std)`; `nn_dist, _ = tree.query(grid_pts/pts_std)`. Mask grid cells where `nn_dist > COVERAGE_MAX_NN_DIST` to NaN. Tune the radius once against a dense SPY day so the supported region matches visible quote density. Add `COVERAGE_MAX_NN_DIST` to config.py.
2. **Per-expiry strike gate.** For each real expiry, count OTM strikes with at least one on each wing; expiries below `SURFACE_MIN_STRIKES_PER_EXPIRY` (≥5) are excluded from skew/term/PCA and their grid columns masked.
3. **Clip instrumentation.** Compute `(IV_raw < 0).sum()` before clipping; log it. A nonzero-and-growing count is the alarm that the mask is letting extrapolation through.
4. **Leave-one-expiry-out check.** Drop each expiry in turn, refit, predict its real strikes back, report per-expiry RMSE. Large errors flag expiries whose shape is "borrowed" (Pitfall 2).
5. **Shape sanity (no-arbitrage proxies).** Total variance `IV²·T` non-decreasing in T along each OTM slice (flag, don't enforce); smile second-difference sign-stability between real strikes (flag ringing → smoothing too low).
6. **Coverage % report.** Fraction of grid cells that are supported. Report alongside any CV number — never CV alone.
7. **Mask reuse contract.** Phases 9/10/11 import the *same* mask function; ΔIV intersects two masks; metrics check the per-expiry gate. One source of truth for "where is the surface real."

---

## Sources

- `gex/analytics.py` (lines 159–436): `plot_vol_surface`, `plot_iv_change_surface`, `_rbf_grid` — RBF/TPS config, zero-clip, independent-interpolate-then-difference, fixed 3D camera (read directly, 2026-05-29)
- `gex/surface_history.py`: per-row spot storage, idempotent replace-by-date, `list_available_dates` (read directly)
- `gex/config.py`: `SURFACE_*` constants, `SKEW_MIN_DTE`, `PLOT_*_ANCHORS`, the "SVI would be needed to extrapolate" note (lines 62–104)
- `.planning/research/PITFALLS-v3.2.md`: percentile-on-9-days, banned-words list, compound-signal temptation, fallback-gracefully, schema-migration patterns — directly reused
- Git history: commits `ad8b017`, `3bed07b`, `569bfe0` — "honest holes," contour/scatter removal (the project's established surface philosophy)
- [scipy.interpolate.RBFInterpolator — SciPy Manual](https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.RBFInterpolator.html) — confirms RBFInterpolator extrapolates beyond the convex hull and "extrapolation is uncertain and should not be relied upon"; TPS is the biharmonic kernel (HIGH)
- [Static image export hangs using kaleido — Plotly Community Forum](https://community.plotly.com/t/static-image-export-hangs-using-kaleido/61519) and [Kaleido issue #110: Image generation hangs on Windows 10](https://github.com/plotly/Kaleido/issues/110) — documented Windows hang/first-call problems (HIGH)
- [Kaleido: The Next Generation](https://plotly.com/blog/kaleido-the-next-generation/) — v1 Choreographer re-architecture motivated specifically by Windows reliability (MEDIUM)
- MEMORY: "vol surface should be 2D not 3D" (project design concern) — corroborates Pitfall 12

---
*Pitfalls research for: v3.3 Surface Evolution & Daily Intelligence*
*Researched: 2026-05-29*

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
