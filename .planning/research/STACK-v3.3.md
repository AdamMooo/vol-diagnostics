# Stack Research — v3.3 "Surface Evolution & Daily Intelligence"

**Domain:** Local Python options-analytics app (gamma-omm); subsequent-milestone STACK delta only
**Researched:** 2026-05-29
**Confidence:** HIGH (kaleido × plotly compatibility verified against installed venv + official docs + GitHub issues)

## TL;DR

- **Surface validation (feature 1) and surface evolution (feature 2) need ZERO new dependencies.** Leave-one-out / k-fold CV, residuals, coverage flags, and parameter sensitivity are all hand-rollable on the existing `scipy.interpolate.RBFInterpolator` + `numpy` + `pandas` + `pyarrow` stack already in the repo. Do NOT add scikit-learn.
- **Static image export (feature 3) needs exactly ONE new dependency — but `kaleido==0.2.1` is the WRONG pin for this environment.** The venv runs **plotly 6.7.0**, and `kaleido 0.2.1` + plotly 6.x on Windows is a documented hang/freeze. The correct choice is **`kaleido>=1.0` + a one-time Chrome fetch**, OR pin plotly down to `<6` and use `kaleido==0.2.1`. See the decision box below — this contradicts the greenlit assumption and the roadmapper must resolve it.

## The kaleido Decision (read this first)

The milestone brief greenlit `kaleido==0.2.1`. That pin was correct for the plotly 5.x era but is **unsafe against the plotly version actually installed here.**

Verified facts:

| Fact | Source | Confidence |
|------|--------|------------|
| Installed plotly in `.venv` is **6.7.0** | `python -c "import plotly; print(plotly.__version__)"` | HIGH (direct) |
| kaleido is NOT currently installed | import raised `ModuleNotFoundError` | HIGH (direct) |
| `kaleido 0.2.1` is built for / works with **plotly 5.x** | plotly.py issue #5241, PyPI | HIGH |
| `kaleido 1.0.0+` **requires plotly.py ≥ 6.1.1** | plotly static-image-changes doc, issue #5241 | HIGH |
| `kaleido 0.2.1` + plotly 6.x on Windows → `write_image()` **freezes indefinitely / runs >1hr, no error** | Kaleido issues #402, #300, #322 | MEDIUM (multiple corroborating reports) |
| Pre-v1 kaleido **bundles Chromium**; v1+ does **not** — needs a Chrome/Chromium install (`kaleido.get_chrome()`) | Kaleido README, static-image-changes doc | HIGH |

So with the current `plotly 6.7.0`, two coherent paths exist:

**Path A (recommended) — modern kaleido v1:**
- `pip install "kaleido>=1.0,<2.0"`
- Keep plotly as-is (6.7.0 satisfies the ≥6.1.1 floor).
- One-time, run once per machine: `python -c "import kaleido; kaleido.get_chrome_sync()"` (or CLI `kaleido_get_chrome`). This downloads a pinned Chromium into the kaleido cache. It is NOT a system Chrome install and does not touch the user's browser.
- Export call: `fig.write_image(path)` — do NOT pass `engine="kaleido"` (the `engine` param is deprecated in plotly 6.2 and removed after Sept 2025; default engine is already kaleido).
- Tradeoff: first export per process pays Chromium startup latency (~1–3s); the get_chrome step is a ~150MB one-time download.

**Path B — freeze the old stack:**
- Pin `plotly>=5.22,<6` AND `kaleido==0.2.1` together.
- Pro: kaleido bundles its own Chromium — no separate Chrome fetch, fully offline/self-contained, matches the "single self-contained artifact" ethos.
- Con: downgrades the installed plotly 6.7.0 → a 5.x release, which risks regressions in the existing 3D `go.Surface` charts (lighting/contour kwargs, colorbar API) that were authored and visually signed off against plotly 6.x. This is real rework risk for zero analytical gain.

**Recommendation: Path A.** The repo already runs plotly 6.7.0 and the surface charts are tuned to it; downgrading to chase a kaleido pin that is itself broken on Windows + plotly 6.x is backwards. Use `kaleido>=1.0,<2.0` and document the one-time `get_chrome` step in `CLAUDE.md`. Reserve Path B only if the PM environment cannot run the get_chrome download (locked-down corporate machine with no outbound to the Chromium CDN) — in which case the offline-bundled 0.2.1 + plotly<6 combo is the fallback, accepting the chart-regression test burden.

> The `<7.0` upper bound currently in `requirements.txt` is fine for Path A and should stay. Do NOT pin `kaleido==0.2.1` against it — that is the broken combination.

## Recommended Stack (delta from existing)

### New Dependency — exactly one

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| kaleido | `>=1.0,<2.0` | Static PNG export of plotly figures for email attachment (feature 3) | Only library that renders plotly.js figures to static images headlessly; v1 is the only line compatible with the installed plotly 6.7.0. Path A above. |

That is the **entire** new-dependency footprint for v3.3. Everything else reuses the existing stack.

### Existing Stack — reused for features 1 & 2 (NO new installs)

| Library | Already pinned | Reused for | Why sufficient |
|---------|----------------|------------|----------------|
| scipy | `>=1.13,<2.0` (1.17.1 installed) | LOO/k-fold CV by re-fitting `RBFInterpolator` on held-out subsets; residuals = `rbf(train_pts)` vs raw | The validation IS just refitting the same estimator already in `analytics.py`. No CV framework needed. |
| numpy | `>=1.26,<3.0` (2.4.4 installed) | RMS/level/skew/term decomposition of ΔIV grids, percentile coverage flags, convex-hull / extrapolation masking | All array math; `np.percentile`, `np.linalg`, boolean masks. |
| pandas | `>=2.0,<3.0` | Residual tables, evolution summary frames, snapshot joins on (date, strike, dte) | Already the data spine. |
| pyarrow | `>=15.0` | Persist evolution metrics + per-day surface grids to parquet | `gex/validation.py` already does parquet snapshot save/load — extend the schema, don't add a store. |
| pandas_market_calendars | `>=4.4` | Resolve "1/5/20 trading days back" to actual session dates for snapshot lookup | Already imported elsewhere; trading-day arithmetic is exactly its job. |
| plotly | `>=5.0,<7.0` (6.7.0 installed) | Residual scatter / coverage-overlay charts for the validation report | Existing chart engine; keep the bound. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| pytest | Unit tests for CV-error computation and ΔIV decomposition | Already in the project (24 tests green). Add tests asserting LOO error is finite and decomposition components sum to total ΔIV RMS. |

## Installation

```bash
# Path A (recommended) — modern kaleido against installed plotly 6.7.0
.venv\Scripts\activate
pip install "kaleido>=1.0,<2.0"

# One-time per machine: fetch the Chromium kaleido v1 renders with
python -c "import kaleido; kaleido.get_chrome_sync()"

# Smoke test
python -c "import plotly.graph_objects as go; go.Figure().write_image('out/_kaleido_smoke.png'); print('ok')"
```

requirements.txt addition (Path A):
```
kaleido>=1.0,<2.0
```

Path B fallback (offline / locked-down machine only — NOT recommended):
```
plotly>=5.22,<6
kaleido==0.2.1
```

## Surface Validation — why scipy/numpy is enough (feature 1)

The validation is mechanically just re-running the estimator that already exists in `gex/analytics.py:plot_vol_surface` (`RBFInterpolator(kernel="thin_plate_spline", smoothing=1.5)`):

- **Leave-one-out CV:** for each raw (dte, %OTM, iv) point, fit RBF on the other N−1 points, predict the held-out one, collect residuals. N is small (one option chain, a few hundred points post-clip) → LOO is cheap, no need for batched k-fold. A plain Python loop over `RBFInterpolator` refits is correct and readable.
- **k-fold (optional, faster):** `numpy` random partition into k index groups; same refit pattern. Hand-rolled, ~15 lines.
- **Raw-vs-fitted residuals:** `rbf(raw_pts) - raw_iv` using the already-fitted full-data RBF. Pure numpy.
- **Interpolation vs extrapolation coverage flags:** a grid node is "interpolation" if inside the convex hull of raw points, "extrapolation" otherwise. `scipy.spatial.Delaunay(pts).find_simplex(grid_pts) >= 0` gives the in-hull mask — scipy.spatial is already part of the installed scipy, no new dep. Flag/shade extrapolated nodes in the report.
- **Param sensitivity:** loop over candidate `smoothing` / grid-resolution / clip values, recompute LOO error, tabulate. Just calling the existing builder with different kwargs.

**scikit-learn is NOT needed.** `sklearn.model_selection.KFold` / `cross_val_score` assume an sklearn-style estimator API; `RBFInterpolator` is not one, so you'd be writing an adapter anyway. The hand-rolled loop is fewer lines, has no new dependency, and keeps the CV logic legible for a quant reader — which matches the project's "interpretability first" constraint.

## Surface Evolution — why no new dep (feature 2)

- Snapshots already persist via `gex/validation.py` parquet store; spot is already saved per the memory note on the vol-surface build. Extend the schema with the per-day fitted grid (or recompute on read from stored raw chain) — `pyarrow` handles it.
- Trading-day offsets (1/5/20 back) → resolve to dates with `pandas_market_calendars`, then load those snapshots.
- ΔIV decomposition (level / RMS / skew-change / term-change) is arithmetic on two aligned grids: `level = mean(ΔIV)`, `rms = sqrt(mean(ΔIV²))`, skew-change = change in the %OTM cross-sectional slope, term-change = change in the DTE-axis slope. All `numpy`. The `plot_iv_change_surface` function in `analytics.py` already differences two RBF grids on a shared mesh — the decomposition reuses that exact grid.

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `kaleido==0.2.1` (as greenlit) | Built for plotly 5.x; on the installed **plotly 6.7.0** Windows `write_image()` hangs indefinitely (Kaleido issues #402/#300/#322) | `kaleido>=1.0,<2.0` (Path A), or only if forced offline, downgrade plotly to `<6` (Path B) |
| `engine="kaleido"` kwarg on `write_image` | Deprecated in plotly 6.2, removed after Sept 2025 | Call `fig.write_image(path)` with no engine arg — kaleido is the default engine |
| scikit-learn | Adds a heavy dep for CV/KFold that `RBFInterpolator` can't plug into without an adapter; violates minimal-dependency bias | Hand-rolled LOO/k-fold loop over scipy `RBFInterpolator` (~15–30 lines) |
| scipy.spatial new install | It's already inside the pinned scipy | `from scipy.spatial import Delaunay` for the convex-hull coverage mask |
| orca (legacy plotly image export) | Deprecated, requires a separate Node/Electron binary, removed support after Sept 2025 | kaleido (Path A) |
| matplotlib for the PNGs | Project already renders these as plotly 3D surfaces; re-authoring in matplotlib doubles the charting code | Export the existing plotly figures via kaleido |
| A separate image-cache / asset-pipeline library | Email attachment is a handful of PNGs written to `out/` then attached via the existing `gex/emailer.py` `attachments=[...]` path (already supported, line 45) | Write PNGs to `out/`, pass paths to `send(..., attachments=[...])` |
| Headless-browser libs (selenium/playwright) for rendering | kaleido v1 already manages its own Chromium headlessly | `kaleido.get_chrome_sync()` once, then `write_image` |

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| plotly 6.7.0 (installed) | kaleido `>=1.0` | Requires plotly ≥ 6.1.1; this is the supported pairing. Run `get_chrome` once. |
| plotly 6.x | kaleido `0.2.1` | **BROKEN on Windows** — `write_image` hangs/freezes. Do not pair. |
| plotly 5.x (≤ ~5.24) | kaleido `0.2.1` | The historically-correct pairing; only relevant if Path B (plotly downgrade) is taken. |
| kaleido `>=1.0` | system/bundled Chrome | Does NOT ship Chromium; needs `kaleido.get_chrome()` (downloads a pinned Chromium to kaleido's cache, not a system browser). |
| scipy 1.17.1 (installed) | `scipy.spatial.Delaunay`, `RBFInterpolator` | Both present; no version concern for CV / hull masking. |

## Gotchas for the phase planners

- **First-call latency:** kaleido v1 spins up Chromium on first `write_image` in a process (~1–3s). In `run_daily.py` (one process, 3 tickers, several charts each) this is paid once — acceptable. Don't benchmark it as per-chart cost.
- **One-time machine setup:** the `get_chrome` step must run on the PM/scheduled-task machine before the first emailed report, or `write_image` errors. Add it to `CLAUDE.md` Local Setup and note it in the v3.3 STATE.
- **Headless on Windows scheduled task:** kaleido v1 renders headlessly, so it works under Task Scheduler without an interactive session — but the get_chrome download must have completed under that machine/user profile first.
- **Email path already exists:** `gex/emailer.py:send()` already accepts `attachments: list[Path]` and resolves/attaches them (lines 20, 45). No emailer change needed beyond passing the new PNG paths.
- **Image dimensions:** pass explicit `width`/`height`/`scale` to `write_image` for crisp email rendering; the on-screen `height=540` scene layout is fine but set `scale=2` for retina-sharp attachments.

## Sources

- Installed venv probe — `plotly 6.7.0`, `scipy 1.17.1`, `numpy 2.4.4`, `pandas 2.3.3`, kaleido absent — HIGH (direct)
- https://github.com/plotly/plotly.py/issues/5241 — kaleido 1.0.0 incompatible with plotly 5.x; `kaleido<1.0.0` to stay on 0.2.1; kaleido 1.0 needs plotly ≥6.1.1 — HIGH
- https://plotly.com/python/static-image-generation-changes/ — plotly 6.1 introduces kaleido v1 support; engine param + orca/old-kaleido removed after Sept 2025 — HIGH
- https://github.com/plotly/Kaleido (README) + https://pypi.org/project/kaleido/ — pre-v1 bundles Chromium; v1 needs separate Chrome via `kaleido.get_chrome()`; `write_fig`/`write_fig_sync` added in v1 — HIGH
- https://github.com/plotly/Kaleido/issues/402, /issues/300, /issues/322 — `write_image` hang/freeze on Windows with kaleido 0.2.1 + plotly 6.x (and 6.3+ broadly) — MEDIUM (corroborating user reports, not an official statement)
- `gex/analytics.py` (RBFInterpolator usage, lines 159–430) and `gex/emailer.py` (attachments support) — HIGH (direct read)

---
*Stack research for: gamma-omm v3.3 surface validation + evolution + richer daily email*
*Researched: 2026-05-29*

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
