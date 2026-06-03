"""
Daily vol diagnostics for Purpose Yield ETF underlyings.

Usage:
    python -m gex.run_daily_yield            # compute + print, saves HTML report to out/
    python -m gex.run_daily_yield --dry-run  # same as above (explicit) — no email
    python -m gex.run_daily_yield --send     # upload to S3, send email (or set GEX_SEND=1)

Workflow:
    1. Compute all 16 tickers, save parquet snapshots.
    2. Build an interactive HTML report (Plotly 3D surfaces, gamma profiles, OI charts).
    3. If --send: upload HTML to S3 (YIELD_S3_BUCKET in .env), send card-based email
       with a presigned link to the hosted report. Recipients tap the link — no download.

.env keys:
    YIELD_S3_BUCKET   S3 bucket name (must exist; upload IAM permissions required)
    YIELD_S3_PREFIX   Optional key prefix, default "yield/" (e.g. "reports/yield/")
    YIELD_S3_EXPIRY   Presigned URL expiry in seconds, default 604800 (7 days)

Scheduled via: runners/yield_daily.ps1 (Task Scheduler, 4:35 PM ET on trading days)

Snapshots accumulate in the same stores as the index pipeline:
    out/gex_snapshots.parquet          — scalar metrics (IV30, skew, RV20, VRP …)
    out/surface_history/surface_*.parquet — raw chain points per ticker

RV20 and VRP require ~20 trading days of spot history before they appear.
"""
from __future__ import annotations

import argparse
import datetime
import math
import pathlib

import pandas_market_calendars as mcal
import pytz

from gex.compute import compute_ticker
from gex.validation import save_snapshot
from gex.surface_history import save_surface_snapshot
from gex import emailer

# CBOE ticker → Purpose ETF display label
YIELD_TICKERS: dict[str, str] = {
    "AMD":   "AMD (AMD) Yield Shares Purpose ETF",
    "META":  "META (META) Yield Shares Purpose ETF",
    "AAPL":  "Apple (AAPL) Yield Shares Purpose ETF",
    "AMZN":  "Amazon (AMZN) Yield Shares Purpose ETF",
    "TSLA":  "Tesla (TSLA) Yield Shares Purpose ETF",
    "BRK.B": "Berkshire Hathaway (BRK.B) Yield Shares Purpose ETF",
    "GOOGL": "Alphabet (GOOGL) Yield Shares Purpose ETF",
    "MSFT":  "Microsoft (MSFT) Yield Shares Purpose ETF",
    "NVDA":  "NVIDIA (NVDA) Yield Shares Purpose ETF",
    "AVGO":  "Broadcom (AVGO) Yield Shares Purpose ETF",
    "COIN":  "Coinbase (COIN) Yield Shares Purpose ETF",
    "COST":  "Costco (COST) Yield Shares Purpose ETF",
    "JPM":   "Yield Shares (JPYS) Purpose ETF",
    "NFLX":  "Netflix (NFLX) Yield Shares Purpose ETF",
    "PLTR":  "Palantir (PLTR) Yield Shares Purpose ETF",
    "UNH":   "UnitedHealth Group (UNH) Yield Shares Purpose ETF",
}

OUT_DIR = pathlib.Path(__file__).resolve().parents[1] / "out" / "yield"
ET = pytz.timezone("America/New_York")

_SANS = "font-family:Arial,Helvetica,sans-serif;"
_MONO = "font-family:Consolas,'SF Mono',Menlo,monospace;"
_GRAY = "#94a3b8"
_RULE = "#cbd5e1"
_GREEN = "#16a34a"
_RED = "#dc2626"
_NEUTRAL = "#64748b"


def is_trading_day(date: datetime.date | None = None) -> bool:
    nyse = mcal.get_calendar("NYSE")
    d = date or datetime.datetime.now(ET).date()
    schedule = nyse.schedule(start_date=d.strftime("%Y-%m-%d"), end_date=d.strftime("%Y-%m-%d"))
    return not schedule.empty


def process_ticker(ticker: str) -> dict:
    try:
        return compute_ticker(ticker)
    except Exception as exc:
        print(f"  [WARN] {ticker}: {exc}")
        return {"summary": {"ticker": ticker, "error": str(exc)}}


# ── S3 upload ─────────────────────────────────────────────────────────────────

_ENV_PATH = pathlib.Path(__file__).resolve().parents[1] / ".env"


def _upload_to_s3(local_path: pathlib.Path, date: datetime.date) -> str | None:
    """Upload HTML report to S3, return a presigned URL (default 7-day expiry) or None."""
    import os
    from dotenv import load_dotenv
    load_dotenv(_ENV_PATH, encoding="utf-8-sig", override=True)
    bucket = os.getenv("YIELD_S3_BUCKET", "").strip()
    if not bucket:
        print("[yield-daily] YIELD_S3_BUCKET not set — skipping S3 upload.")
        return None
    prefix = os.getenv("YIELD_S3_PREFIX", "yield/").strip().rstrip("/") + "/"
    expiry = int(os.getenv("YIELD_S3_EXPIRY", "604800"))  # 7 days
    key = f"{prefix}yield_{date.strftime('%Y%m%d')}.html"
    try:
        import boto3
        s3 = boto3.client("s3")
        s3.upload_file(
            str(local_path),
            bucket,
            key,
            ExtraArgs={"ContentType": "text/html; charset=utf-8"},
        )
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expiry,
        )
        print(f"[yield-daily] S3 upload OK: s3://{bucket}/{key}")
        return url
    except Exception as exc:
        print(f"[yield-daily] S3 upload failed (non-blocking): {exc}")
        return None


# ── Shared formatting helpers ─────────────────────────────────────────────────

def _fmt(v, suffix="", prec=1, prefix="") -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    return f"{prefix}{v:.{prec}f}{suffix}"


def _fmt_signed(v, suffix="pp", prec=1) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.{prec}f}{suffix}"


def _accent_color(price_change_pct: float | None) -> str:
    if price_change_pct is None:
        return _NEUTRAL
    if price_change_pct > 0:
        return _GREEN
    if price_change_pct < 0:
        return _RED
    return _NEUTRAL


def _extract_metrics(data: dict) -> dict:
    s = data["summary"]
    skew = data.get("skew")
    front_rr = (skew.get("front_month") or {}).get("skew") if skew else None
    rv20_decimal = data.get("rv20")
    rv20_pct = rv20_decimal * 100 if rv20_decimal is not None else None
    iv30 = s.get("iv30")
    spot = s.get("spot")
    vrp = data.get("vrp")  # already in pp from compute.py
    iv30_daily_dollar = (iv30 / 100.0 / math.sqrt(252) * spot) if (iv30 and spot) else None
    return {
        "ticker": s["ticker"],
        "label": YIELD_TICKERS.get(s["ticker"], s["ticker"]),
        "spot": spot,
        "price_change_pct": s.get("price_change_pct"),
        "iv30": iv30,
        "iv30_daily_dollar": iv30_daily_dollar,
        "rv20": rv20_pct,
        "vrp": vrp,
        "front_rr": front_rr,
        "coverage_pct": s.get("coverage_pct"),
        "error": s.get("error"),
    }


# ── Email builder ─────────────────────────────────────────────────────────────

def _email_summary_table(metrics_list: list[dict]) -> str:
    th_s = (
        f'font-family:Arial,sans-serif;padding:6px 12px 6px 0;font-size:10px;font-weight:700;'
        f'letter-spacing:0.05em;text-transform:uppercase;color:{_GRAY};'
        f'border-bottom:2px solid #000000;text-align:left;white-space:nowrap;'
    )
    td_s = f'font-family:Consolas,monospace;padding:5px 12px 5px 0;font-size:12px;border-bottom:1px solid {_RULE};white-space:nowrap;'
    td_lbl = f'font-family:Arial,sans-serif;font-weight:700;padding:5px 12px 5px 0;font-size:12px;border-bottom:1px solid {_RULE};white-space:nowrap;color:#111111;'

    header = (
        f'<tr>'
        f'<th style="{th_s}">Underlying</th>'
        f'<th style="{th_s}">Spot</th>'
        f'<th style="{th_s}">Day %</th>'
        f'<th style="{th_s}">IV30</th>'
        f'<th style="{th_s}">RV20</th>'
        f'<th style="{th_s}">VRP</th>'
        f'<th style="{th_s}">25&Delta; RR</th>'
        f'</tr>'
    )

    rows = ""
    for m in metrics_list:
        if m["error"]:
            rows += (
                f'<tr><td style="{td_lbl}">{m["ticker"]}</td>'
                f'<td colspan="6" style="{td_s}color:{_RED};">Load failed</td></tr>'
            )
            continue
        pct = m["price_change_pct"]
        pct_str = f"{pct:+.2f}%" if pct is not None else "—"
        pct_color = _GREEN if (pct is not None and pct > 0) else (_RED if (pct is not None and pct < 0) else "#777777")
        vrp_color = _GREEN if (m["vrp"] is not None and m["vrp"] > 0) else (_RED if (m["vrp"] is not None and m["vrp"] < 0) else "#777777")
        rows += (
            f'<tr>'
            f'<td style="{td_lbl}">{m["ticker"]}</td>'
            f'<td style="{td_s}">{_fmt(m["spot"], prefix="$", prec=2)}</td>'
            f'<td style="{td_s}color:{pct_color};">{pct_str}</td>'
            f'<td style="{td_s}">{_fmt(m["iv30"], suffix="%")}</td>'
            f'<td style="{td_s}">{_fmt(m["rv20"], suffix="%")}</td>'
            f'<td style="{td_s}color:{vrp_color};">{_fmt_signed(m["vrp"])}</td>'
            f'<td style="{td_s}">{_fmt_signed(m["front_rr"])}</td>'
            f'</tr>'
        )

    return (
        f'<div style="overflow-x:auto;">'
        f'<table cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;width:100%;">'
        f'{header}{rows}'
        f'</table></div>'
    )


def build_email(results: list[dict], date: datetime.date,
                report_url: str | None = None) -> str:
    try:
        date_str = f"{date.strftime('%B')} {date.day}, {date.year}"
    except Exception:
        date_str = str(date)

    metrics_list = [_extract_metrics(d) for d in results]
    summary_table = _email_summary_table(metrics_list)

    link_block = ""
    if report_url:
        link_block = (
            f'<table cellpadding="0" cellspacing="0" border="0" style="margin:20px 0 0;">'
            f'<tr><td style="background:#111111;border-radius:4px;">'
            f'<a href="{report_url}" target="_blank" '
            f'style="{_SANS}display:block;padding:9px 20px;color:#ffffff;font-size:13px;'
            f'font-weight:700;text-decoration:none;white-space:nowrap;letter-spacing:0.3px;">'
            f'View Full Interactive Report &rarr;</a>'
            f'</td></tr>'
            f'<tr><td style="{_SANS}font-size:10px;color:{_GRAY};padding-top:5px;">'
            f'Interactive vol surfaces, gamma profiles, and OI charts &mdash; link valid 7 days'
            f'</td></tr>'
            f'</table>'
        )

    disclaimer = (
        f'<div style="{_SANS}font-size:10px;color:{_GRAY};line-height:1.7;'
        f'margin-top:20px;padding-top:10px;border-top:1px solid {_RULE};">'
        f'<b>VRP</b>: IV30 &minus; RV20 (pp). Positive = implied vol priced above realized. &nbsp;'
        f'<b>25&Delta; RR</b>: front-month put IV &minus; call IV. Positive = put skew. &nbsp;'
        f'OI is T&minus;1. Quotes ~15-min delayed.'
        f'</div>'
    )

    logo_email = _logo_tag(height="32px")
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="{_SANS}margin:0;padding:0;background:#ffffff;color:#111111;">
<table width="100%" cellpadding="0" cellspacing="0">
  <tr><td align="center" style="padding:28px 20px;">
    <table width="640" cellpadding="0" cellspacing="0" style="width:640px;max-width:640px;">
      <tr><td>

        <table cellpadding="0" cellspacing="0" border="0" style="width:100%;border-bottom:2px solid #000000;padding-bottom:8px;margin:0 0 6px;">
          <tr>
            <td style="vertical-align:bottom;">
              <div style="{_SANS}font-size:11px;font-weight:700;letter-spacing:1.6px;text-transform:uppercase;color:#000000;">
                Purpose Yield ETF &mdash; Underlying Volatility Diagnostics
              </div>
            </td>
            <td style="text-align:right;vertical-align:bottom;padding-left:12px;">{logo_email}</td>
          </tr>
        </table>
        <div style="{_SANS}font-size:11px;color:{_GRAY};margin:0 0 20px;">{date_str}</div>

        <p style="{_SANS}font-size:12px;color:#333333;margin:0 0 18px;line-height:1.6;">
          The following summarizes implied volatility diagnostics for the underlyings of the
          Purpose Yield ETF suite as of the close of {date_str}. All metrics are derived from
          CBOE delayed options chains. Full interactive charts are available via the attached
          HTML report.
        </p>

        {summary_table}
        {link_block}
        {disclaimer}

      </td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>"""


# ── HTML report builder (interactive Plotly) ──────────────────────────────────

def _logo_tag(height: str = "125px") -> str:
    """Inline the Yield Shares SVG as a base64 img tag. Silent no-op if file missing."""
    import base64
    svg_path = pathlib.Path(__file__).resolve().parents[1] / "assets" / "yieldsharesheadermobile-v1-5.svg"
    if not svg_path.exists():
        return ""
    b64 = base64.b64encode(svg_path.read_bytes()).decode()
    return (
        f'<img src="data:image/svg+xml;base64,{b64}" '
        f'style="height:{height};width:auto;display:block;" '
        f'alt="Yield Shares Purpose ETF">'
    )


def _fig_div(fig) -> str:
    import uuid as _uuid
    div_id = "plt-" + _uuid.uuid4().hex[:8]
    fig_json = fig.to_json()
    return (
        f'<div id="{div_id}" class="lazy-plot plotly-graph-div" style="height:450px;width:100%;"></div>'
        f'<script type="application/json" data-for="{div_id}">{fig_json}</script>'
    )


def _plotly_js_tag() -> str:
    return '<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>'


def _chart_wrap(content: str, wrap_id: str) -> str:
    return (
        f'<div class="cwrap" id="{wrap_id}">'
        f'<button class="fsbtn" onclick="toggleFS(\'{wrap_id}\')" title="Full screen">&#x26F6;</button>'
        f'{content}'
        f'</div>'
    )


def _ticker_section_html(m: dict, surface_div: str, div_iv: str,
                         profile_div: str, oi_div: str,
                         is_first: bool = False) -> str:
    pct = m["price_change_pct"]
    pct_str = f" {pct:+.2f}%" if pct is not None else ""
    accent = _accent_color(pct)
    pct_color = "#22c55e" if (pct or 0) > 0 else "#ef4444"
    tk = m["ticker"].replace(".", "_")
    summary_line = (
        f'<span style="font-weight:700;font-size:15px;color:#e2e2e2;">{m["ticker"]}</span>'
        f'<span style="font-size:13px;color:#888888;margin-left:10px;">{m["label"].split("(")[0].strip()}</span>'
        f'<span style="font-family:Consolas,monospace;margin-left:14px;font-size:13px;color:#cccccc;">'
        f'{_fmt(m["spot"], prefix="$", prec=2)}'
        f'<span style="color:{pct_color};margin-left:8px;">{pct_str}</span>'
        f'</span>'
        f'<span style="font-family:Consolas,monospace;margin-left:14px;font-size:12px;color:#a0a0a0;">'
        f'IV30 {_fmt(m["iv30"], suffix="%")} &nbsp;·&nbsp; '
        f'RV20 {_fmt(m["rv20"], suffix="%")} &nbsp;·&nbsp; '
        f'VRP {_fmt_signed(m["vrp"])} &nbsp;·&nbsp; '
        f'25ΔRR {_fmt_signed(m["front_rr"])}'
        f'</span>'
    )

    open_attr = " open" if is_first else ""
    dv_wrap = _chart_wrap(div_iv, f"cw-{tk}-dv")
    sf_wrap = _chart_wrap(surface_div, f"cw-{tk}-sf")
    pos_wrap = _chart_wrap(
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">'
        f'<div>{profile_div}</div><div>{oi_div}</div></div>',
        f"cw-{tk}-pos",
    )

    return f"""
<details{open_attr} style="margin-bottom:4px;border-left:2px solid {accent};padding-left:12px;">
  <summary style="cursor:pointer;padding:9px 0;list-style:none;outline:none;user-select:none;">
    <span style="display:inline-flex;align-items:center;gap:0;flex-wrap:wrap;">{summary_line}</span>
  </summary>
  <div style="padding:10px 0 18px;">
    <div class="chart-label">&#916;IV &mdash; today vs prior session</div>
    <div style="margin-bottom:16px;">{dv_wrap}</div>
    <div class="chart-label">IV Surface &mdash; today</div>
    <div style="margin-bottom:16px;">{sf_wrap}</div>
    <div class="chart-label">Positioning</div>
    {pos_wrap}
  </div>
</details>"""


def _error_section_html(m: dict) -> str:
    return (
        f'<details style="margin-bottom:4px;border-left:2px solid #333333;padding-left:12px;">'
        f'<summary style="cursor:pointer;padding:9px 0;list-style:none;color:#444444;font-size:14px;">'
        f'{m["ticker"]} — {m["label"].split("(")[0].strip()}'
        f'<span style="color:#ef4444;margin-left:10px;font-size:12px;">Load failed: {m["error"]}</span>'
        f'</summary></details>'
    )


_NO_PRIOR = (
    '<p style="font-family:Arial,sans-serif;font-size:12px;color:#444444;padding:12px 0;">'
    'No prior snapshot — &#916;IV available after the second daily run.</p>'
)


def build_html_report(results: list[dict], date: datetime.date) -> str:
    from gex.analytics import (
        plot_vol_surface, plot_gamma_profile,
        plot_oi_by_strike, plot_iv_change_surface,
    )
    from gex.surface_history import nth_trading_day_back, load_surface_snapshot

    date_str = f"{date.strftime('%B')} {date.day}, {date.year}"
    metrics_list = [_extract_metrics(d) for d in results]

    sections = []
    for i, data in enumerate(results):
        m = metrics_list[i]
        if m["error"]:
            sections.append(_error_section_html(m))
            continue

        ticker = m["ticker"]
        spot = data["spot"]

        try:
            surface_fig = plot_vol_surface(data["surface_df"], ticker, spot)
            surface_div = _fig_div(surface_fig)
        except Exception as exc:
            surface_div = f'<p style="color:#f87171;font-size:12px;">Vol surface failed: {exc}</p>'

        try:
            prior_date = nth_trading_day_back(ticker, date, 1)
            if prior_date is not None:
                prior_df, prior_spot = load_surface_snapshot(ticker, prior_date)
                if not prior_df.empty:
                    div_iv_fig = plot_iv_change_surface(
                        data["surface_df"], prior_df,
                        ticker, spot, prior_spot or spot,
                        label_prior=prior_date.strftime("%b %d"),
                        label_today=date.strftime("%b %d"),
                    )
                    div_iv = _fig_div(div_iv_fig)
                else:
                    div_iv = _NO_PRIOR
            else:
                div_iv = _NO_PRIOR
        except Exception as exc:
            div_iv = f'<p style="color:#f87171;font-size:12px;">&#916;IV failed: {exc}</p>'

        try:
            profile_fig = plot_gamma_profile(data["p_df"], spot, ticker, data["summary"])
            profile_div = _fig_div(profile_fig)
        except Exception as exc:
            profile_div = f'<p style="color:#f87171;font-size:12px;">Gamma profile failed: {exc}</p>'

        try:
            oi_fig = plot_oi_by_strike(data["s_df"], spot, ticker, data["summary"])
            oi_div = _fig_div(oi_fig)
        except Exception as exc:
            oi_div = f'<p style="color:#f87171;font-size:12px;">OI chart failed: {exc}</p>'

        sections.append(_ticker_section_html(
            m, surface_div, div_iv, profile_div, oi_div, is_first=(i == 0),
        ))

    all_sections = "\n".join(sections)

    glossary = (
        '<div style="font-family:Arial,sans-serif;font-size:10px;color:#3a3a3a;line-height:1.8;'
        'margin-top:28px;padding-top:12px;border-top:1px solid #1a1a1a;">'
        '<b>VRP</b>: IV30 &minus; RV20 (pp). Positive = options priced rich vs realized vol.<br>'
        '<b>25&Delta; RR</b>: 25&Delta; put IV &minus; 25&Delta; call IV, front month &le;45 DTE. Positive = put skew.<br>'
        '<b>OI is T&minus;1.</b> CBOE quotes ~15-min delayed. GEX assumes dealers net-short all options '
        '&mdash; holds in aggregate; apply skepticism to single names with heavy institutional flow.'
        '</div>'
    )

    plotly_script = _plotly_js_tag()
    logo = _logo_tag()
    n_ok = len([m for m in metrics_list if not m["error"]])

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Purpose Yield ETF &mdash; Underlying Volatility Diagnostics {date_str}</title>
{plotly_script}
<style>
  * {{ box-sizing: border-box; }}
  body {{
    background: #0d0d0d;
    color: #e2e2e2;
    font-family: 'Segoe UI', system-ui, -apple-system, 'Helvetica Neue', Arial, sans-serif;
    margin: 0;
    padding: 24px 20px;
  }}
  .container {{ max-width: 1200px; margin: 0 auto; }}
  h1 {{ font-size: 20px; font-weight: 600; margin: 0 0 3px; letter-spacing: -0.3px; }}
  .subtitle {{ font-size: 11px; color: #555555; margin: 0 0 22px; }}
  .section-label {{
    font-size: 10px; font-weight: 700; letter-spacing: 1.6px;
    text-transform: uppercase; color: #444444;
    border-bottom: 1px solid #1f1f1f; padding-bottom: 5px; margin: 0 0 14px;
  }}
  .chart-label {{
    font-size: 10px; font-weight: 700; letter-spacing: 1.2px;
    text-transform: uppercase; color: #444444;
    border-bottom: 1px solid #1a1a1a; padding-bottom: 3px; margin-bottom: 8px;
  }}
  details summary::-webkit-details-marker {{ display: none; }}
  details summary::before {{
    content: "\\25B6";
    display: inline-block;
    margin-right: 8px;
    font-size: 9px;
    color: #333333;
    transition: transform 0.15s;
    vertical-align: middle;
  }}
  details[open] summary::before {{ transform: rotate(90deg); }}
  .cwrap {{ position: relative; }}
  .fsbtn {{
    position: absolute; top: 6px; right: 6px; z-index: 20;
    background: rgba(255,255,255,0.05); color: #444444;
    border: 1px solid #222222; border-radius: 3px;
    padding: 3px 7px; cursor: pointer; font-size: 12px; line-height: 1;
    transition: background 0.15s, color 0.15s;
  }}
  .fsbtn:hover {{ background: rgba(255,255,255,0.1); color: #aaaaaa; }}
  .cwrap:fullscreen, .cwrap:-webkit-full-screen {{
    background: #0d0d0d; padding: 32px;
    display: flex; align-items: center; justify-content: center;
  }}
</style>
<script>
function toggleFS(id) {{
  var el = document.getElementById(id);
  var isFS = document.fullscreenElement || document.webkitFullscreenElement;
  if (!isFS) {{
    var fn = el.requestFullscreen || el.webkitRequestFullscreen || el.mozRequestFullScreen;
    if (fn) fn.call(el);
  }} else {{
    var ex = document.exitFullscreen || document.webkitExitFullscreen;
    if (ex) ex.call(document);
  }}
}}
function renderLazyPlots(container) {{
  container.querySelectorAll('.lazy-plot:not([data-rendered])').forEach(function(el) {{
    var s = document.querySelector('script[data-for="' + el.id + '"]');
    if (!s) return;
    var fig = JSON.parse(s.textContent);
    Plotly.newPlot(el, fig.data, fig.layout, {{responsive: true, displayModeBar: true}});
    el.setAttribute('data-rendered', '1');
  }});
}}
document.addEventListener('DOMContentLoaded', function() {{
  document.querySelectorAll('details[open]').forEach(function(d) {{
    renderLazyPlots(d);
  }});
  document.querySelectorAll('details').forEach(function(d) {{
    d.addEventListener('toggle', function() {{
      if (this.open) renderLazyPlots(this);
    }});
  }});
}});
</script>
</head>
<body>
<div class="container">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:20px;">
    <div>
      <h1>Purpose Yield ETF Suite &mdash; Underlying Volatility Diagnostics</h1>
      <p class="subtitle">{date_str} &nbsp;&middot;&nbsp; {n_ok}/{len(metrics_list)} tickers &nbsp;&middot;&nbsp; CBOE delayed</p>
    </div>
    <div style="flex-shrink:0;margin-left:20px;margin-top:2px;">{logo}</div>
  </div>

  <div class="section-label">Charts by Ticker</div>
  {all_sections}

  {glossary}
</div>
</body>
</html>"""


# ── Main ──────────────────────────────────────────────────────────────────────

def run(dry_run: bool = False) -> None:
    today = datetime.datetime.now(ET).date()

    if not is_trading_day(today):
        print(f"[yield-daily] {today} is not a NYSE trading day — skipping.")
        return

    tickers = list(YIELD_TICKERS.keys())
    print(f"[yield-daily] {today}  tickers: {', '.join(tickers)}")
    OUT_DIR.mkdir(exist_ok=True)

    all_data: list[dict] = []
    for ticker in tickers:
        print(f"  {ticker}...", end=" ", flush=True)
        data = process_ticker(ticker)
        all_data.append(data)
        s = data["summary"]
        if not s.get("error"):
            save_snapshot(s, ticker, skew_df=data.get("skew_df"), date=today)
            save_surface_snapshot(data.get("surface_df"), ticker, spot=s["spot"], date=today)
            iv30_str = f"  iv30={s['iv30']:.1f}%" if s.get("iv30") else ""
            print(f"spot={s['spot']:.2f}{iv30_str}")
        else:
            print(f"ERROR: {s['error']}")

    good = [d for d in all_data if not d["summary"].get("error")]
    if not good:
        print("[yield-daily] All tickers failed — skipping output.")
        return

    subject = f"Purpose Yield ETF — Volatility Diagnostics, {today.strftime('%b %d, %Y').replace(' 0', ' ')}"

    # Always save the rich HTML report locally
    html_report = build_html_report(all_data, today)
    out_path = OUT_DIR / f"purpose_yield_vol_report_{today.strftime('%Y%m%d')}.html"
    out_path.write_text(html_report, encoding="utf-8")
    print(f"[yield-daily] HTML report saved: {out_path}")

    if dry_run:
        return

    # Upload to S3 if configured (optional — only fires when YIELD_S3_BUCKET is set)
    report_url = _upload_to_s3(out_path, today)

    html_email = build_email(all_data, today, report_url=report_url)
    try:
        emailer.send(subject=subject, html_body=html_email, attachments=[out_path])
        print("[yield-daily] Email sent.")
    except Exception as exc:
        print(f"[yield-daily] Email failed: {exc}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Save HTML report to out/, do not send email.")
    parser.add_argument("--send", action="store_true",
                        help="Required to actually send the email.")
    args = parser.parse_args()

    import os as _os
    authorized = args.send or _os.getenv("GEX_SEND") == "1"
    if not authorized and not args.dry_run:
        print("[yield-daily] No --send flag. Falling back to --dry-run.")
        args.dry_run = True

    run(dry_run=args.dry_run)
