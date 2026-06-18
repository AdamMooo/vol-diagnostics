"""
SPIKE: vol-surface "beast" — interactive single-figure 3D surface with live
mouse-driven smile/term slices, de-transformed fit, and an isolated near-expiry layer.

Throwaway exploration (branch spike/vol-surface-beast). Self-contained: reads a saved
surface snapshot, fits the RBF, precomputes every slice, and emits one HTML file with
client-side plotly.js hover callbacks (smooth drag, no server round-trip).

Run:
    .venv/Scripts/python.exe spike/build_surface_beast.py --ticker SPY
    .venv/Scripts/python.exe spike/build_surface_beast.py --ticker SPY --smoothing 0.5 --clip 0.22 --fit-floor 5
    # baseline (current production knobs) for before/after:
    .venv/Scripts/python.exe spike/build_surface_beast.py --ticker SPY --smoothing 1.5 --clip 0.15 --fit-floor 5 --pin-floor

Opens spike/out/surface_beast_<TICKER>.html in a browser.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.interpolate import RBFInterpolator
from scipy.spatial import Delaunay, QhullError

ROOT = Path(__file__).resolve().parent.parent
SNAP_DIR = ROOT / "out" / "surface_history"
OUT_DIR = Path(__file__).resolve().parent / "out"

GRID_DTE = 48
GRID_LM = 40
DTE_MAX = 180


def load_latest(ticker: str) -> tuple[pd.DataFrame, float, str]:
    df = pd.read_parquet(SNAP_DIR / f"surface_{ticker}.parquet")
    latest = df["date"].max()
    d = df[df["date"] == latest].copy()
    spot = float(d["spot"].iloc[0])
    return d, spot, str(latest)


def fit_rbf(dte_v, log_m, iv_v, smoothing):
    pts = np.column_stack([dte_v, log_m])
    std = pts.std(axis=0)
    std[std < 1e-6] = 1.0
    rbf = RBFInterpolator(pts / std, iv_v, kernel="thin_plate_spline", smoothing=smoothing)
    return rbf, std


def hull_mask(dte_v, log_m, DTE, OTM):
    pts = np.column_stack([dte_v, log_m])
    std = pts.std(axis=0)
    std[std < 1e-6] = 1.0
    try:
        hull = Delaunay(pts / std)
    except QhullError:
        return np.zeros(DTE.shape, dtype=bool)
    grid = np.column_stack([DTE.ravel(), OTM.ravel()]) / std
    return (hull.find_simplex(grid) >= 0).reshape(DTE.shape)


def nearest_expiry_points(d_fit, target_dte):
    """Raw (log_m, iv) at the single actual expiry closest to target_dte."""
    expiries = np.sort(d_fit["dte"].unique())
    nearest = expiries[np.argmin(np.abs(expiries - target_dte))]
    sub = d_fit[d_fit["dte"] == nearest].sort_values("log_moneyness")
    return float(nearest), sub["log_moneyness"].tolist(), sub["iv_pct"].tolist()


def term_band_points(d_fit, target_lm, band=0.015):
    """Raw (dte, iv) within +/- band of a moneyness, across all expiries."""
    sub = d_fit[np.abs(d_fit["log_moneyness"] - target_lm) <= band].sort_values("dte")
    return sub["dte"].tolist(), sub["iv_pct"].tolist()


def build(ticker, smoothing, clip, fit_floor, pin_floor, near_max):
    d, spot, date = load_latest(ticker)
    d = d[np.abs(d["log_moneyness"]) <= clip].copy()
    d = d[d["dte"] <= DTE_MAX].copy()

    d_fit = d[d["dte"] >= fit_floor].copy()
    d_near = d[d["dte"] < near_max].copy()  # isolated near-expiry layer (NOT fit)

    if len(d_fit) < 6:
        raise SystemExit(f"{ticker}: only {len(d_fit)} fit points after clip — too sparse.")

    dte_min = float(fit_floor) if pin_floor else float(d_fit["dte"].min())
    dte_max = float(d_fit["dte"].max())
    dte_grid = np.linspace(dte_min, dte_max, GRID_DTE)
    otm_grid = np.linspace(-clip, clip, GRID_LM)

    rbf, std = fit_rbf(d_fit["dte"].to_numpy(), d_fit["log_moneyness"].to_numpy(),
                       d_fit["iv_pct"].to_numpy(), smoothing)
    DTE, OTM = np.meshgrid(dte_grid, otm_grid)  # shape (n_otm, n_dte)
    IV = rbf(np.column_stack([DTE.ravel(), OTM.ravel()]) / std).reshape(DTE.shape)
    IV = np.clip(IV, 0.0, None)

    mask = hull_mask(d_fit["dte"].to_numpy(), d_fit["log_moneyness"].to_numpy(), DTE, OTM)
    IV = np.where(mask, IV, np.nan)
    coverage = 100.0 * float(mask.mean())

    # fit residual RMSE (in-sample)
    fit_pred = rbf(np.column_stack([d_fit["dte"].to_numpy(), d_fit["log_moneyness"].to_numpy()]) / std)
    rmse = float(np.sqrt(np.mean((fit_pred - d_fit["iv_pct"].to_numpy()) ** 2)))

    # Precompute slices indexed by grid position (JS swaps these on hover — instant).
    smile_fit = [np.where(np.isnan(IV[:, i]), None, IV[:, i].round(2)).tolist()
                 for i in range(len(dte_grid))]
    term_fit = [np.where(np.isnan(IV[j, :]), None, IV[j, :].round(2)).tolist()
                for j in range(len(otm_grid))]

    smile_raw = []
    for dg in dte_grid:
        ne, lm, iv = nearest_expiry_points(d_fit, dg)
        smile_raw.append({"dte": round(ne, 0), "x": [round(v, 4) for v in lm],
                          "y": [round(v, 2) for v in iv]})
    term_raw = []
    for og in otm_grid:
        dd, iv = term_band_points(d_fit, og)
        term_raw.append({"x": [round(v, 0) for v in dd], "y": [round(v, 2) for v in iv]})

    # Isolated near-expiry smile (the wild 0-4 DTE the fit excludes), nearest single expiry.
    near_payload = None
    if len(d_near):
        ne, lm, iv = nearest_expiry_points(d_near, d_near["dte"].min())
        near_payload = {"dte": round(ne, 0), "x": [round(v, 4) for v in lm],
                        "y": [round(v, 2) for v in iv]}

    z_cap = float(np.nanpercentile(IV, 99.5))
    z_floor = float(np.nanmin(IV))

    payload = {
        "ticker": ticker, "date": date, "spot": round(spot, 2),
        "smoothing": smoothing, "clip": clip, "fit_floor": fit_floor,
        "pin_floor": pin_floor, "coverage": round(coverage, 0), "rmse": round(rmse, 3),
        "dte_grid": [round(v, 1) for v in dte_grid.tolist()],
        "otm_grid": [round(v, 4) for v in otm_grid.tolist()],
        "ks_grid": [round(float(np.exp(v)), 3) for v in otm_grid.tolist()],
        "IV": [[None if (np.isnan(v)) else round(float(v), 2) for v in row] for row in IV],
        "smile_fit": smile_fit, "term_fit": term_fit,
        "smile_raw": smile_raw, "term_raw": term_raw,
        "near": near_payload,
        "z_cap": round(z_cap, 1), "z_floor": round(max(0.0, z_floor - 2), 1),
    }
    return payload


HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<title>Vol Surface Beast — {ticker}</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  body {{ margin:0; background:#0e1117; color:#e6e6e6; font-family:-apple-system,Segoe UI,sans-serif; }}
  #hdr {{ padding:10px 16px; font-size:13px; border-bottom:1px solid #222; }}
  #hdr b {{ color:#fff; }} .tag {{ color:#8aa; margin-right:14px; }}
  #fig {{ width:100vw; height:calc(100vh - 46px); }}
</style></head>
<body>
<div id="hdr">
  <b>{ticker}</b> {date} &nbsp; spot {spot}
  <span style="float:right">
    <span class="tag">smoothing {smoothing}</span>
    <span class="tag">clip ±{clip}</span>
    <span class="tag">fit floor {fit_floor}{pinned}</span>
    <span class="tag">coverage {coverage}%</span>
    <span class="tag">fit RMSE {rmse}pp</span>
  </span>
  &nbsp; — hover/drag the surface; slices follow live.
</div>
<div id="fig"></div>
<script>
const D = {payload};

const surface = {{
  type:'surface', x:D.dte_grid, y:D.otm_grid, z:D.IV,
  colorscale:'Plasma', cmin:D.z_floor, cmax:D.z_cap,
  colorbar:{{title:'IV %', thickness:12, len:0.55, x:0.58}},
  scene:'scene', showscale:true,
  contours:{{z:{{show:true, usecolormap:true, project_z:true, width:1}}}},
  hovertemplate:'DTE %{{x:.0f}}<br>K/S %{{y:.3f}}<br>IV %{{z:.1f}}%<extra></extra>'
}};

// smile panel (xy2): fitted curve + raw nearest-expiry points + isolated near-expiry
const smileFit = {{type:'scatter', mode:'lines', xaxis:'x2', yaxis:'y2',
  x:D.ks_grid, y:D.smile_fit[0], line:{{color:'#ffd24d', width:3}}, name:'fit'}};
const smileRaw = {{type:'scatter', mode:'markers', xaxis:'x2', yaxis:'y2',
  x:D.smile_raw[0].x.map(Math.exp), y:D.smile_raw[0].y,
  marker:{{color:'#4dd2ff', size:5}}, name:'raw'}};
const nearTrace = {{type:'scatter', mode:'lines+markers', xaxis:'x2', yaxis:'y2',
  x:(D.near?D.near.x.map(Math.exp):[]), y:(D.near?D.near.y:[]),
  line:{{color:'#ff5d5d', width:1, dash:'dot'}}, marker:{{size:3, color:'#ff5d5d'}},
  name:(D.near?('near '+D.near.dte+'DTE (excl.)'):'near (none)')}};

// term panel (xy3): fitted curve + raw band points
const termFit = {{type:'scatter', mode:'lines', xaxis:'x3', yaxis:'y3',
  x:D.dte_grid, y:D.term_fit[Math.floor(D.otm_grid.length/2)],
  line:{{color:'#ffd24d', width:3}}, name:'fit', showlegend:false}};
const termRaw = {{type:'scatter', mode:'markers', xaxis:'x3', yaxis:'y3',
  x:D.term_raw[Math.floor(D.otm_grid.length/2)].x, y:D.term_raw[Math.floor(D.otm_grid.length/2)].y,
  marker:{{color:'#4dd2ff', size:5}}, name:'raw', showlegend:false}};

const layout = {{
  paper_bgcolor:'#0e1117', plot_bgcolor:'#0e1117', font:{{color:'#cfcfcf', size:11}},
  margin:{{t:30,b:40,l:10,r:10}}, showlegend:true,
  legend:{{x:0.62, y:0.50, font:{{size:10}}}},
  scene:{{domain:{{x:[0,0.58], y:[0,1]}},
    xaxis:{{title:'DTE', gridcolor:'#222'}}, yaxis:{{title:'ln(K/S)', gridcolor:'#222'}},
    zaxis:{{title:'IV %', gridcolor:'#222'}},
    camera:{{eye:{{x:1.9,y:-1.3,z:0.7}}}}, aspectmode:'manual', aspectratio:{{x:1.5,y:1.2,z:0.6}}}},
  xaxis2:{{domain:[0.66,1.0], anchor:'y2', title:'K/S', gridcolor:'#222'}},
  yaxis2:{{domain:[0.56,1.0], anchor:'x2', title:'IV % (smile)', gridcolor:'#222'}},
  xaxis3:{{domain:[0.66,1.0], anchor:'y3', title:'DTE', gridcolor:'#222'}},
  yaxis3:{{domain:[0.04,0.46], anchor:'x3', title:'IV % (term)', gridcolor:'#222'}},
  annotations:[
    {{text:'SMILE @ DTE —', x:0.66, y:1.0, xref:'paper', yref:'paper',
      showarrow:false, font:{{color:'#ffd24d', size:11}}, xanchor:'left'}},
    {{text:'TERM @ K/S —', x:0.66, y:0.46, xref:'paper', yref:'paper',
      showarrow:false, font:{{color:'#ffd24d', size:11}}, xanchor:'left'}}
  ]
}};

Plotly.newPlot('fig',
  [surface, smileFit, smileRaw, nearTrace, termFit, termRaw], layout,
  {{responsive:true, displaylogo:false}});

const gd = document.getElementById('fig');
function nearestIdx(arr, v){{ let b=0,bd=1e9; for(let i=0;i<arr.length;i++){{let dd=Math.abs(arr[i]-v); if(dd<bd){{bd=dd;b=i;}}}} return b; }}

gd.on('plotly_hover', function(ev){{
  const p = ev.points[0];
  if(p.data.type !== 'surface') return;
  const di = nearestIdx(D.dte_grid, p.x);   // hovered DTE -> smile
  const oi = nearestIdx(D.otm_grid, p.y);   // hovered ln(K/S) -> term
  const raw = D.smile_raw[di];
  const tr = D.term_raw[oi];
  Plotly.restyle('fig', {{ y:[D.smile_fit[di]] }}, [1]);
  Plotly.restyle('fig', {{ x:[raw.x.map(Math.exp)], y:[raw.y] }}, [2]);
  Plotly.restyle('fig', {{ y:[D.term_fit[oi]] }}, [4]);
  Plotly.restyle('fig', {{ x:[tr.x], y:[tr.y] }}, [5]);
  Plotly.relayout('fig', {{
    'annotations[0].text':'SMILE @ DTE '+Math.round(p.x)+'  (raw @ '+raw.dte+'DTE)',
    'annotations[1].text':'TERM @ K/S '+D.ks_grid[oi].toFixed(3)
  }});
}});
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", default="SPY")
    ap.add_argument("--smoothing", type=float, default=0.5)
    ap.add_argument("--clip", type=float, default=0.20)
    ap.add_argument("--fit-floor", type=float, default=5.0)
    ap.add_argument("--near-max", type=float, default=5.0,
                    help="DTE below this is the isolated near-expiry layer")
    ap.add_argument("--pin-floor", action="store_true",
                    help="pin surface footprint to fit-floor (baseline behaviour)")
    ap.add_argument("--tag", default="", help="filename suffix, e.g. before/after")
    args = ap.parse_args()

    payload = build(args.ticker, args.smoothing, args.clip, args.fit_floor,
                    args.pin_floor, args.near_max)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = f"_{args.tag}" if args.tag else ""
    out = OUT_DIR / f"surface_beast_{args.ticker}{suffix}.html"
    html = HTML.format(
        ticker=payload["ticker"], date=payload["date"], spot=payload["spot"],
        smoothing=payload["smoothing"], clip=payload["clip"], fit_floor=payload["fit_floor"],
        pinned=(" (pinned)" if payload["pin_floor"] else ""),
        coverage=payload["coverage"], rmse=payload["rmse"],
        payload=json.dumps(payload),
    )
    out.write_text(html, encoding="utf-8")
    print(f"[beast] {args.ticker} {payload['date']}  coverage {payload['coverage']}%  "
          f"fit RMSE {payload['rmse']}pp  -> {out}")


if __name__ == "__main__":
    main()
