"""
Interactive vol surface: one 3D surface + live mouse-driven smile/term slices.

Graduated from spike/vol-surface-beast (2026-06-18). Two-canvas design — the 3D
surface and the 2D slice panel are SEPARATE plotly figures so hovering the surface
restyles only the cheap 2D figure (a single linked figure re-renders the WebGL scene
on every mouse move → unusable lag). See spike/SPIKE.md.

Isolated from the email/evolution path on purpose: this uses its OWN smoothing/clip
(SURFACE_INTERACTIVE_*), so tuning the displayed surface never shifts the evolution
baselines or email PNGs that share config.SURFACE_SMOOTHING. coverage_mask (the convex-hull
support gate) is reused from analytics — same honest holes as the static surface.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy.interpolate import RBFInterpolator

from gex import config
from gex.analytics import coverage_mask

GRID_DTE = 36   # mesh density: lower = lighter hover raycast
GRID_LM = 28


def _fit_rbf(dte_v, log_m, iv_v, smoothing):
    pts = np.column_stack([dte_v, log_m])
    std = pts.std(axis=0)
    std[std < 1e-6] = 1.0
    rbf = RBFInterpolator(pts / std, iv_v, kernel="thin_plate_spline", smoothing=smoothing)
    return rbf, std


def _nearest_expiry_points(d_fit, target_dte):
    expiries = np.sort(d_fit["dte"].unique())
    nearest = expiries[np.argmin(np.abs(expiries - target_dte))]
    sub = d_fit[d_fit["dte"] == nearest].sort_values("log_moneyness")
    return float(nearest), sub["log_moneyness"].tolist(), sub["iv_pct"].tolist()


def _term_band_points(d_fit, target_lm, band=0.015):
    sub = d_fit[np.abs(d_fit["log_moneyness"] - target_lm) <= band].sort_values("dte")
    return sub["dte"].tolist(), sub["iv_pct"].tolist()


def build_surface_payload(
    surface_df: pd.DataFrame,
    spot: float,
    ticker: str = "",
    date: str = "",
    *,
    smoothing: float = config.SURFACE_INTERACTIVE_SMOOTHING,
    clip: float = config.SURFACE_INTERACTIVE_CLIP,
    fit_floor: float = 5.0,
    near_max: float = 5.0,
    pin_floor: bool = False,
) -> dict | None:
    """Precompute the surface grid + every smile/term slice (JS swaps them on hover).

    Returns None when too sparse to fit (caller shows a caption instead).
    """
    if surface_df is None or surface_df.empty:
        return None
    d = surface_df.copy()
    d = d[np.abs(d["log_moneyness"]) <= clip]
    d = d[d["dte"] <= config.SURFACE_DTE_MAX]

    d_fit = d[d["dte"] >= fit_floor].copy()
    d_near = d[d["dte"] < near_max].copy()  # isolated near-expiry layer (NOT fit)
    if len(d_fit) < 6 or d_fit["dte"].nunique() < 2:
        return None

    dte_min = float(fit_floor) if pin_floor else float(d_fit["dte"].min())
    dte_max = float(d_fit["dte"].max())
    if dte_max <= dte_min + 1:
        return None
    dte_grid = np.linspace(dte_min, dte_max, GRID_DTE)
    otm_grid = np.linspace(-clip, clip, GRID_LM)

    rbf, std = _fit_rbf(d_fit["dte"].to_numpy(), d_fit["log_moneyness"].to_numpy(),
                        d_fit["iv_pct"].to_numpy(), smoothing)
    DTE, OTM = np.meshgrid(dte_grid, otm_grid)  # (n_otm, n_dte)
    IV = np.clip(rbf(np.column_stack([DTE.ravel(), OTM.ravel()]) / std).reshape(DTE.shape), 0.0, None)

    mask = coverage_mask(d_fit, spot, dte_grid, otm_grid, dte_floor=fit_floor, clip=clip)
    IV = np.where(mask, IV, np.nan)
    if np.isnan(IV).all():
        return None
    coverage = 100.0 * float(mask.mean())

    fit_pred = rbf(np.column_stack([d_fit["dte"].to_numpy(), d_fit["log_moneyness"].to_numpy()]) / std)
    rmse = float(np.sqrt(np.mean((fit_pred - d_fit["iv_pct"].to_numpy()) ** 2)))

    smile_fit = [np.where(np.isnan(IV[:, i]), None, IV[:, i].round(2)).tolist()
                 for i in range(len(dte_grid))]
    term_fit = [np.where(np.isnan(IV[j, :]), None, IV[j, :].round(2)).tolist()
                for j in range(len(otm_grid))]
    smile_raw, term_raw = [], []
    for dg in dte_grid:
        ne, lm, iv = _nearest_expiry_points(d_fit, dg)
        smile_raw.append({"dte": round(ne, 0), "x": [round(v, 4) for v in lm],
                          "y": [round(v, 2) for v in iv]})
    for og in otm_grid:
        dd, iv = _term_band_points(d_fit, og)
        term_raw.append({"x": [round(v, 0) for v in dd], "y": [round(v, 2) for v in iv]})

    near = None
    if len(d_near):
        ne, lm, iv = _nearest_expiry_points(d_near, d_near["dte"].min())
        near = {"dte": round(ne, 0), "x": [round(v, 4) for v in lm], "y": [round(v, 2) for v in iv]}

    return {
        "ticker": ticker, "date": date, "spot": round(float(spot), 2),
        "smoothing": smoothing, "clip": clip, "fit_floor": fit_floor, "pin_floor": pin_floor,
        "coverage": round(coverage, 0), "rmse": round(rmse, 3),
        "dte_grid": [round(v, 1) for v in dte_grid.tolist()],
        "otm_grid": [round(v, 4) for v in otm_grid.tolist()],
        "ks_grid": [round(float(np.exp(v)), 3) for v in otm_grid.tolist()],
        "IV": [[None if np.isnan(v) else round(float(v), 2) for v in row] for row in IV],
        "smile_fit": smile_fit, "term_fit": term_fit,
        "smile_raw": smile_raw, "term_raw": term_raw, "near": near,
        "z_cap": round(float(np.nanpercentile(IV, config.SURFACE_Z_CAP_PERCENTILE)), 1),
        "z_floor": round(max(0.0, float(np.nanmin(IV)) - 2), 1),
    }


_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  body {{ margin:0; background:#0e1117; color:#e6e6e6; font-family:-apple-system,Segoe UI,sans-serif; }}
  #hdr {{ padding:6px 12px; font-size:12px; border-bottom:1px solid #222; }}
  #hdr b {{ color:#fff; }} .tag {{ color:#8aa; margin-right:12px; }}
  #wrap {{ display:flex; width:100%; height:calc(100% - 34px); }}
  #fig3d {{ flex:0 0 60%; height:100%; }}
  #right {{ flex:1; display:flex; flex-direction:column; }}
  .lbl {{ padding:4px 12px; font-size:11px; color:#ffd24d; }}
  #figsl {{ flex:1; }}
  html,body,#wrap {{ height:100%; }}
  #fs {{ cursor:pointer; background:#1b2230; color:#cfcfcf; border:1px solid #333;
        border-radius:4px; padding:1px 8px; font-size:13px; margin-left:10px; }}
</style></head>
<body>
<div id="hdr">
  <b>{ticker}</b> {date} &nbsp; spot {spot}
  <span style="float:right">
    <span class="tag">smoothing {smoothing}</span><span class="tag">clip ±{clip}</span>
    <span class="tag">coverage {coverage}%</span><span class="tag">fit RMSE {rmse}pp</span>
    <button id="fs" title="Fullscreen">⛶</button>
  </span>
</div>
<div id="wrap">
  <div id="fig3d"></div>
  <div id="right"><div class="lbl" id="lbl">smile / term — hover the surface</div><div id="figsl"></div></div>
</div>
<script>
const D = {payload};
const mid = Math.floor(D.otm_grid.length/2);
Plotly.newPlot('fig3d', [{{
  type:'surface', x:D.dte_grid, y:D.otm_grid, z:D.IV, colorscale:'Plasma',
  cmin:D.z_floor, cmax:D.z_cap, colorbar:{{title:'IV %', thickness:12, len:0.6}},
  contours:{{z:{{show:true, usecolormap:true, project_z:false, width:1}}}},
  hovertemplate:'DTE %{{x:.0f}}<br>K/S %{{y:.3f}}<br>IV %{{z:.1f}}%<extra></extra>'
}}], {{paper_bgcolor:'#0e1117', font:{{color:'#cfcfcf', size:11}}, margin:{{t:8,b:8,l:8,r:8}},
  scene:{{xaxis:{{title:'DTE', gridcolor:'#222'}}, yaxis:{{title:'ln(K/S)', gridcolor:'#222'}},
    zaxis:{{title:'IV %', gridcolor:'#222'}}, camera:{{eye:{{x:1.9,y:-1.3,z:0.7}}}},
    aspectmode:'manual', aspectratio:{{x:1.5,y:1.2,z:0.6}}}}}},
  {{responsive:true, displaylogo:false}});
Plotly.newPlot('figsl', [
  {{type:'scatter', mode:'lines', x:D.ks_grid, y:D.smile_fit[0], line:{{color:'#ffd24d', width:3}}, name:'fit'}},
  {{type:'scatter', mode:'markers', x:D.smile_raw[0].x.map(Math.exp), y:D.smile_raw[0].y, marker:{{color:'#4dd2ff', size:5}}, name:'raw'}},
  {{type:'scatter', mode:'lines+markers', x:(D.near?D.near.x.map(Math.exp):[]), y:(D.near?D.near.y:[]),
    line:{{color:'#ff5d5d', width:1, dash:'dot'}}, marker:{{size:3, color:'#ff5d5d'}},
    name:(D.near?('near '+D.near.dte+'DTE (excl.)'):'near (none)')}},
  {{type:'scatter', mode:'lines', xaxis:'x2', yaxis:'y2', x:D.dte_grid, y:D.term_fit[mid], line:{{color:'#ffd24d', width:3}}, showlegend:false}},
  {{type:'scatter', mode:'markers', xaxis:'x2', yaxis:'y2', x:D.term_raw[mid].x, y:D.term_raw[mid].y, marker:{{color:'#4dd2ff', size:5}}, showlegend:false}}
], {{paper_bgcolor:'#0e1117', plot_bgcolor:'#0e1117', font:{{color:'#cfcfcf', size:10}},
  margin:{{t:8,b:46,l:48,r:8}}, showlegend:true, legend:{{x:0, y:1.0, font:{{size:9}}, orientation:'h'}},
  xaxis:{{domain:[0,1], anchor:'y', title:'K/S (smile)', gridcolor:'#222'}},
  yaxis:{{domain:[0.56,1.0], anchor:'x', title:'IV %', gridcolor:'#222'}},
  xaxis2:{{domain:[0,1], anchor:'y2', title:'DTE (term)', gridcolor:'#222'}},
  yaxis2:{{domain:[0.06,0.44], anchor:'x2', title:'IV %', gridcolor:'#222'}}}},
  {{responsive:true, displaylogo:false}});
const lbl = document.getElementById('lbl');
function nIdx(a,v){{let b=0,bd=1e9;for(let i=0;i<a.length;i++){{let d=Math.abs(a[i]-v);if(d<bd){{bd=d;b=i;}}}}return b;}}
let lastDi=-1,lastOi=-1,pending=null,queued=false;
function apply(){{queued=false; if(!pending)return; const {{di,oi}}=pending;
  const raw=D.smile_raw[di], tr=D.term_raw[oi];
  Plotly.restyle('figsl', {{y:[D.smile_fit[di], tr.y], x:[D.ks_grid, tr.x]}}, [0,4]);
  Plotly.restyle('figsl', {{x:[raw.x.map(Math.exp)], y:[raw.y]}}, [1]);
  Plotly.restyle('figsl', {{y:[D.term_fit[oi]]}}, [3]);
  lbl.textContent='smile @ DTE '+D.dte_grid[di]+'  (raw @ '+raw.dte+'DTE)   |   term @ K/S '+D.ks_grid[oi].toFixed(3);}}
document.getElementById('fig3d').on('plotly_hover', function(ev){{
  const p=ev.points[0]; if(!p||p.data.type!=='surface')return;
  const di=nIdx(D.dte_grid,p.x), oi=nIdx(D.otm_grid,p.y);
  if(di===lastDi&&oi===lastOi)return; lastDi=di; lastOi=oi; pending={{di,oi}};
  if(!queued){{queued=true; requestAnimationFrame(apply);}}}});
document.getElementById('fs').onclick=function(){{
  if(document.fullscreenElement){{document.exitFullscreen();}}
  else if(document.documentElement.requestFullscreen){{document.documentElement.requestFullscreen().catch(()=>{{}});}}}};
document.addEventListener('fullscreenchange',function(){{
  setTimeout(function(){{Plotly.Plots.resize('fig3d'); Plotly.Plots.resize('figsl');}}, 80);}});
</script></body></html>"""


def render_surface_html(payload: dict) -> str:
    return _HTML.format(
        ticker=payload["ticker"], date=payload["date"], spot=payload["spot"],
        smoothing=payload["smoothing"], clip=payload["clip"],
        coverage=payload["coverage"], rmse=payload["rmse"], payload=json.dumps(payload),
    )


def _prep(df, clip, fit_floor):
    d = df.copy()
    d = d[np.abs(d["log_moneyness"]) <= clip]
    d = d[(d["dte"] <= config.SURFACE_DTE_MAX) & (d["dte"] >= fit_floor)]
    return d


def build_diff_payload(
    df_a: pd.DataFrame, spot_a: float,
    df_b: pd.DataFrame, spot_b: float,
    ticker: str = "", label_a: str = "A", label_b: str = "B",
    *,
    smoothing: float = config.SURFACE_INTERACTIVE_SMOOTHING,
    clip: float = config.SURFACE_INTERACTIVE_CLIP,
    fit_floor: float = 5.0,
) -> dict | None:
    """ΔIV (A − B) surface + per-slice A/B smile & term overlays. None when too sparse.

    DTE grid = intersection of both dates' ranges (where the diff is defined); coverage
    = both hulls intersected (honest: only cells real in BOTH days)."""
    if df_a is None or df_b is None or df_a.empty or df_b.empty:
        return None
    da, db = _prep(df_a, clip, fit_floor), _prep(df_b, clip, fit_floor)
    if len(da) < 6 or len(db) < 6 or da["dte"].nunique() < 2 or db["dte"].nunique() < 2:
        return None
    dte_min = max(float(da["dte"].min()), float(db["dte"].min()), float(fit_floor))
    dte_max = min(float(da["dte"].max()), float(db["dte"].max()))
    if dte_max <= dte_min + 1:
        return None
    dte_grid = np.linspace(dte_min, dte_max, GRID_DTE)
    otm_grid = np.linspace(-clip, clip, GRID_LM)
    DTE, OTM = np.meshgrid(dte_grid, otm_grid)
    grid = np.column_stack([DTE.ravel(), OTM.ravel()])

    rbf_a, sa = _fit_rbf(da["dte"].to_numpy(), da["log_moneyness"].to_numpy(), da["iv_pct"].to_numpy(), smoothing)
    rbf_b, sb = _fit_rbf(db["dte"].to_numpy(), db["log_moneyness"].to_numpy(), db["iv_pct"].to_numpy(), smoothing)
    IVa = np.clip(rbf_a(grid / sa).reshape(DTE.shape), 0.0, None)
    IVb = np.clip(rbf_b(grid / sb).reshape(DTE.shape), 0.0, None)

    mask = (coverage_mask(da, spot_a, dte_grid, otm_grid, dte_floor=fit_floor, clip=clip) &
            coverage_mask(db, spot_b, dte_grid, otm_grid, dte_floor=fit_floor, clip=clip))
    IVa = np.where(mask, IVa, np.nan)
    IVb = np.where(mask, IVb, np.nan)
    IVd = IVa - IVb
    if np.isnan(IVd).all():
        return None
    cap = float(np.nanpercentile(np.abs(IVd), 99)) or 1.0

    def col(M, i, axis):
        v = M[:, i] if axis == 0 else M[i, :]
        return np.where(np.isnan(v), None, v.round(2)).tolist()

    return {
        "ticker": ticker, "label_a": label_a, "label_b": label_b,
        "coverage": round(100.0 * float(mask.mean()), 0), "cap": round(cap, 2),
        "dte_grid": [round(v, 1) for v in dte_grid.tolist()],
        "otm_grid": [round(v, 4) for v in otm_grid.tolist()],
        "ks_grid": [round(float(np.exp(v)), 3) for v in otm_grid.tolist()],
        "IVd": [[None if np.isnan(v) else round(float(v), 2) for v in row] for row in IVd],
        "smile_a": [col(IVa, i, 0) for i in range(len(dte_grid))],
        "smile_b": [col(IVb, i, 0) for i in range(len(dte_grid))],
        "term_a": [col(IVa, j, 1) for j in range(len(otm_grid))],
        "term_b": [col(IVb, j, 1) for j in range(len(otm_grid))],
    }


_DIFF_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  body {{ margin:0; background:#0e1117; color:#e6e6e6; font-family:-apple-system,Segoe UI,sans-serif; }}
  #hdr {{ padding:6px 12px; font-size:12px; border-bottom:1px solid #222; }}
  #hdr b {{ color:#fff; }} .tag {{ color:#8aa; margin-right:12px; }}
  #wrap {{ display:flex; width:100%; height:calc(100% - 34px); }}
  #fig3d {{ flex:0 0 60%; height:100%; }}
  #right {{ flex:1; display:flex; flex-direction:column; }}
  .lbl {{ padding:4px 12px; font-size:11px; color:#ffd24d; }}
  #figsl {{ flex:1; }} html,body,#wrap {{ height:100%; }}
  #fs {{ cursor:pointer; background:#1b2230; color:#cfcfcf; border:1px solid #333;
        border-radius:4px; padding:1px 8px; font-size:13px; margin-left:10px; }}
</style></head>
<body>
<div id="hdr">
  <b>{ticker} ΔIV</b> &nbsp; {label_a} − {label_b} &nbsp;
  <span style="color:#ff5d5d">red = vol up</span> / <span style="color:#5d9bff">blue = down</span>
  <span style="float:right"><span class="tag">coverage {coverage}%</span>
    <button id="fs" title="Fullscreen">⛶</button></span>
</div>
<div id="wrap">
  <div id="fig3d"></div>
  <div id="right"><div class="lbl" id="lbl">smile / term — hover the surface</div><div id="figsl"></div></div>
</div>
<script>
const D = {payload};
const mid = Math.floor(D.otm_grid.length/2);
Plotly.newPlot('fig3d', [{{
  type:'surface', x:D.dte_grid, y:D.otm_grid, z:D.IVd,
  colorscale:[[0,'#2166ac'],[0.5,'#f7f7f7'],[1,'#b2182b']],
  cmin:-D.cap, cmax:D.cap, colorbar:{{title:'ΔIV', thickness:12, len:0.6}},
  contours:{{z:{{show:true, usecolormap:true, project_z:false, width:1}}}},
  hovertemplate:'DTE %{{x:.0f}}<br>K/S %{{y:.3f}}<br>ΔIV %{{z:.1f}}<extra></extra>'
}}], {{paper_bgcolor:'#0e1117', font:{{color:'#cfcfcf', size:11}}, margin:{{t:8,b:8,l:8,r:8}},
  scene:{{xaxis:{{title:'DTE', gridcolor:'#222'}}, yaxis:{{title:'ln(K/S)', gridcolor:'#222'}},
    zaxis:{{title:'ΔIV', gridcolor:'#222'}}, camera:{{eye:{{x:1.9,y:-1.3,z:0.7}}}},
    aspectmode:'manual', aspectratio:{{x:1.5,y:1.2,z:0.6}}}}}}, {{responsive:true, displaylogo:false}});
Plotly.newPlot('figsl', [
  {{type:'scatter', mode:'lines', x:D.ks_grid, y:D.smile_a[0], line:{{color:'#ffd24d', width:3}}, name:D.label_a}},
  {{type:'scatter', mode:'lines', x:D.ks_grid, y:D.smile_b[0], line:{{color:'#9aa7b8', width:2, dash:'dash'}}, name:D.label_b}},
  {{type:'scatter', mode:'lines', xaxis:'x2', yaxis:'y2', x:D.dte_grid, y:D.term_a[mid], line:{{color:'#ffd24d', width:3}}, showlegend:false}},
  {{type:'scatter', mode:'lines', xaxis:'x2', yaxis:'y2', x:D.dte_grid, y:D.term_b[mid], line:{{color:'#9aa7b8', width:2, dash:'dash'}}, showlegend:false}}
], {{paper_bgcolor:'#0e1117', plot_bgcolor:'#0e1117', font:{{color:'#cfcfcf', size:10}},
  margin:{{t:8,b:46,l:48,r:8}}, showlegend:true, legend:{{x:0, y:1.0, font:{{size:9}}, orientation:'h'}},
  xaxis:{{domain:[0,1], anchor:'y', title:'K/S (smile)', gridcolor:'#222'}},
  yaxis:{{domain:[0.56,1.0], anchor:'x', title:'IV %', gridcolor:'#222'}},
  xaxis2:{{domain:[0,1], anchor:'y2', title:'DTE (term)', gridcolor:'#222'}},
  yaxis2:{{domain:[0.06,0.44], anchor:'x2', title:'IV %', gridcolor:'#222'}}}}, {{responsive:true, displaylogo:false}});
const lbl = document.getElementById('lbl');
function nIdx(a,v){{let b=0,bd=1e9;for(let i=0;i<a.length;i++){{let d=Math.abs(a[i]-v);if(d<bd){{bd=d;b=i;}}}}return b;}}
let lastDi=-1,lastOi=-1,pending=null,queued=false;
function apply(){{queued=false; if(!pending)return; const {{di,oi}}=pending;
  Plotly.restyle('figsl', {{y:[D.smile_a[di], D.smile_b[di]]}}, [0,1]);
  Plotly.restyle('figsl', {{y:[D.term_a[oi], D.term_b[oi]]}}, [2,3]);
  lbl.textContent='smile @ DTE '+D.dte_grid[di]+'   |   term @ K/S '+D.ks_grid[oi].toFixed(3);}}
document.getElementById('fig3d').on('plotly_hover', function(ev){{
  const p=ev.points[0]; if(!p||p.data.type!=='surface')return;
  const di=nIdx(D.dte_grid,p.x), oi=nIdx(D.otm_grid,p.y);
  if(di===lastDi&&oi===lastOi)return; lastDi=di; lastOi=oi; pending={{di,oi}};
  if(!queued){{queued=true; requestAnimationFrame(apply);}}}});
document.getElementById('fs').onclick=function(){{
  if(document.fullscreenElement){{document.exitFullscreen();}}
  else if(document.documentElement.requestFullscreen){{document.documentElement.requestFullscreen().catch(()=>{{}});}}}};
document.addEventListener('fullscreenchange',function(){{
  setTimeout(function(){{Plotly.Plots.resize('fig3d'); Plotly.Plots.resize('figsl');}}, 80);}});
</script></body></html>"""


def render_diff_html(payload: dict) -> str:
    return _DIFF_HTML.format(
        ticker=payload["ticker"], label_a=payload["label_a"], label_b=payload["label_b"],
        coverage=payload["coverage"], payload=json.dumps(payload),
    )
