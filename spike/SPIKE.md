# SPIKE: Vol Surface → Beast

Branch: `spike/vol-surface-beast` | Started 2026-06-18 | throwaway exploration, nothing merges to main until blessed

## Goal
Make the vol surface **true, stable, and legible** + a single interactive figure where dragging the
mouse over the 3D surface drives live smile/term slices. (Over-time "moving surface" + predictive
power = explicitly future, out of this spike.)

## Decisions locked with user (2026-06-18)
- Output: experiment branch, before/after renders, keep/discard at end.
- Near-expiry (0–4 DTE): **separate isolated view**, NOT fed into the main RBF fit (they blow up — SPY
  1DTE has 138% IV at the wings on 2026-06-17).
- Visual: **one figure**, 3D hero + slice panels that follow the mouse (NOT two static charts).

## Knobs (gex/config.py + gex/analytics.py) and findings
| Knob | Production | "Feels like" | Spike finding |
|---|---|---|---|
| `SURFACE_SMOOTHING` | 1.5 | "transformed/aggressive" | CV (leave-one-expiry-out) best at ~0; monotonically worse as smoothing rises. 1.5 over-smooths. Recommend ~0.3–0.5. |
| `dte_min` pin (analytics.py:217) | pinned to floor=5 | "fixed footprint" | Un-pin to real data min → natural footprint. |
| `SURFACE_PLOT_OTM_CLIP` | 0.15 (±16%) | wings cut | Raw data reaches ±24%; widening to ±0.20 holds 95% coverage on SPY. |
| `dte_floor=5` (×8 sites) | drops 0–4 DTE | "hiding true options" | Keep out of *fit*, show as isolated near-expiry layer. |

CV sweep (SPY 2026-06-17): cv_rmse 0.0→0.31, 0.5→0.63, 1.5→0.79, 5.0→0.99.

## Artifacts
- `spike/build_surface_beast.py` — self-contained: snapshot → RBF → precomputed slices → one HTML
  with client-side plotly.js hover callbacks. CLI: `--smoothing --clip --fit-floor --near-max --pin-floor --tag`.
- `spike/out/surface_beast_SPY_before.html` — production knobs (1.5 / ±0.15 / pinned)
- `spike/out/surface_beast_{SPY,QQQ,IWM}_after.html` — de-transformed (0.5 / ±0.20 / unpinned)

## Interaction architecture (RESOLVED 2026-06-18) ✅
User verdict: "so fucking good, much better, so informative."
- **LANDMINE:** 3D surface + frequently-restyled 2D traces in ONE plotly figure → every hover
  re-renders the heavy WebGL scene → unusable lag. First attempt failed exactly here.
- **FIX (proven smooth):** two separate canvases — `#fig3d` (surface) and `#figsl` (2D slices).
  `plotly_hover` on the 3D div restyles ONLY the cheap 2D div. Plus: changed-grid-cell guard +
  `requestAnimationFrame` throttle + label via `textContent` (never `Plotly.relayout`).
- Production path: client-side plotly.js embedded via `st.components.v1.html` (NOT
  `streamlit-plotly-events` — that round-trips per hover, the lag we just escaped).

## Streamlit integration (PROVEN 2026-06-18) ✅
`spike/surface_app_demo.py` — `streamlit run spike/surface_app_demo.py`. The production shape:
streamlit owns controls + server-side RBF fit (`@st.cache_data`); `build()`→`render_html()`→
`components.html()`. Server-side fit, client-side hover — drag stays smooth. This is the drop-in
for `app.py`'s Surface tab.
- **Productionization to-do:** `st.components.v1.html` is deprecated → swap to `st.iframe` before main.

## GRADUATED TO MAIN (2026-06-18) ✅
Smoothing locked **0.5**, clip **0.20**, mesh thinned 48×40→36×28 + floor-projected contour off (lag fix).
- `gex/surface_interactive.py` — `build_surface_payload()` + `render_surface_html()` (reuses
  `analytics.coverage_mask`; local TPS fit so it's isolated from email/evolution).
- `gex/config.py` — new `SURFACE_INTERACTIVE_SMOOTHING=0.5` / `SURFACE_INTERACTIVE_CLIP=0.20`
  (kept SEPARATE from `SURFACE_SMOOTHING=1.5` so email PNGs + evolution baselines are untouched).
- `app.py` — Surface→Today tab renders the interactive component; static `plot_vol_surface` kept
  as the fallback when payload is None.
- Verified: module smoke test + main app boots clean on :8503.

## Shipped since graduation (all committed on this branch)
- Compare → interactive ΔIV; **daily surface video** (Evolution tab) w/ Level↔Change toggle + fullscreen.
- Lighter plotly **gl3d** bundle; per-frame fit guards.
- Card **"read" layer** (`build_card_read`, card_model.py): chips + soft-lean, **credibility-gated** via `config.CARD_READ_MIN_SESSIONS=60` (only defensible chips; today = Premium + Dealers).
- **GEX tenor cap** `config.GEX_MAX_DTE=90` + demoted (LEAPS call tail mis-signed; flipped QQQ +0.57→−0.26B). Lean on OI.

## NEXT — resume here (2026-06-19)
1. **UI audit** — launch `gsd-ui-auditor` agent on app.py + gex/surface_interactive.py + card_model.py → spike/UI-REVIEW.md. (Prompt was drafted; user paused before launch — this was the immediate next action.)
2. **`@st.fragment` de-lag** — wrap surface/video/cards so ticker/mode switch reruns only that region, not full script + iframe remount. Reference: the `ui-skill` (streamlit architecture).
3. **Close the spike**: merge `spike/vol-surface-beast` → main, `components.html`→`st.iframe`, delete throwaway `spike/` files.
4. **The "where"** — resume Phase 17 (term) → 17.1 (expected-move **cone**, not full RND).
5. Wire the card read into the **email** (report.py) via the canonical-card seam — the 7am glance.

Why-notes in memory: [[project_dashboard_read_and_gex_tenor]], [[project_interactive_surface_pattern]].
