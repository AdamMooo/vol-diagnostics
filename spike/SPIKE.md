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

## Open / next
- [ ] Tune surface look to taste: final smoothing (0.5 now), 60/40 proportions, near-expiry placement.
- [ ] Wire into streamlit as a components.html block; decide which knob changes graduate to main.
