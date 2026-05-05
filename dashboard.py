"""Market intelligence dashboard — signal environment + market outcomes.

No sleeve P&L. Four sections:

    Environment  — current signal readings with cross-signal interpretation
    Market       — SPX returns + IV changes by signal quartile (historical base rates)
    Analogs      — K-nearest historical periods; realized market outcomes after each
    Dynamics     — signal trends, extremes, cross-signal divergences
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from data_layer import Panels
from signals import Signals

NEIGHBOR_FEATURES = ("vrp", "term", "skew", "trend", "dd", "fragility")
BUCKETED_SIGNALS = ("vrp", "term", "skew", "fragility")
K_NEIGHBORS = 12

INTERPRET = {
    "rv30":      "quiet / normal / turbulent",
    "vrp":       "vol cheap / fair / vol rich",
    "term":      "inversion / flat / strong contango",
    "skew":      "tails cheap / normal / tails expensive",
    "trend":     "downtrend / sideways / uptrend",
    "dd":        "in drawdown / mid / near highs",
    "fragility": "calm / mid / fragile",
}

_PCT_EDGES = [-np.inf, 0.25, 0.50, 0.75, np.inf]
_PCT_LABELS = ["Q1", "Q2", "Q3", "Q4"]


def _interp(pct: float, sig: str) -> str:
    if pd.isna(pct):
        return "n/a"
    low, mid, high = INTERPRET[sig].split(" / ")
    if pct < 0.33:
        return low
    if pct > 0.67:
        return high
    return mid


def _today_quartile(today_val: float) -> str:
    if pd.isna(today_val):
        return "n/a"
    if today_val < 0.25: return "Q1"
    if today_val < 0.50: return "Q2"
    if today_val < 0.75: return "Q3"
    return "Q4"


def _bucket_by_pct(values: np.ndarray) -> pd.Categorical:
    return pd.cut(values, bins=_PCT_EDGES, labels=_PCT_LABELS, include_lowest=True)


def _primary_underlying(panels: Panels) -> str:
    cols = list(panels.prices_panel.columns)
    return "SPX" if "SPX" in cols else cols[0]


def _forward_returns(prices: pd.Series, horizons: list[int] = [21, 63]) -> dict[int, pd.Series]:
    """Total % return from each date over the next h trading days."""
    return {h: prices.shift(-h) / prices - 1 for h in horizons}


def _forward_iv_change(iv: pd.Series, horizons: list[int] = [21]) -> dict[int, pd.Series]:
    """Absolute IV change (vol pts) from each date over next h trading days."""
    return {h: iv.shift(-h) - iv for h in horizons}


def section_environment_context(sigs: Signals) -> str:
    last_dt = sigs.latest_date()
    out = [
        f"## Market Environment — {last_dt.date()}",
        "",
        "Causal 5y rolling percentile rank. 0 = 5y min, 0.5 = median, 1 = 5y max.",
        "Extremes (>= 0.80 or <= 0.20) flagged with <<.",
        "",
    ]

    underlyings = sigs.pct["vrp"].columns.tolist()
    for u in underlyings:
        out.append(f"### {u}")
        out.append("")
        out.append(f"  {'signal':12s}  {'pct':>5s}  reading")
        out.append("  " + "-" * 48)
        for sig in sigs.pct:
            v = sigs.pct[sig].loc[last_dt, u]
            flag = "  <<" if (not pd.isna(v) and (v >= 0.80 or v <= 0.20)) else ""
            vstr = f"{v:.2f}" if not pd.isna(v) else " n/a"
            out.append(f"  {sig:12s}  {vstr:>5s}  {_interp(v, sig)}{flag}")
        out.append("")

    out.append("### Cross-signal notes")
    out.append("")
    for u in underlyings:
        def _v(sig):
            return sigs.pct[sig].loc[last_dt, u]

        vrp_v, skew_v = _v("vrp"), _v("skew")
        trend_v, dd_v = _v("trend"), _v("dd")
        frag_v = _v("fragility")

        notes = []
        if not (pd.isna(vrp_v) or pd.isna(skew_v)):
            if vrp_v > 0.67 and skew_v < 0.33:
                notes.append("VRP elevated but skew cheap — vol rich ATM, tails not bid")
            elif vrp_v < 0.33 and skew_v > 0.67:
                notes.append("Vol cheap ATM but tails expensive — skew steep vs VRP")
        if not (pd.isna(trend_v) or pd.isna(frag_v)):
            if trend_v > 0.67 and frag_v > 0.67:
                notes.append("Uptrend but fragility elevated — extended with expensive options")
            elif trend_v < 0.33 and frag_v < 0.33:
                notes.append("Downtrend but fragility calm — vol not confirming price stress")
        if not (pd.isna(dd_v) or pd.isna(frag_v)):
            if dd_v < 0.25 and frag_v < 0.33:
                notes.append("In drawdown but fragility low — vol hasn't spiked with price")

        if notes:
            out.append(f"  {u}:")
            for note in notes:
                out.append(f"    - {note}")
        else:
            out.append(f"  {u}: No notable cross-signal divergences")
        out.append("")

    return "\n".join(out)


def _last_trading_day_per_month(daily_df: pd.DataFrame, before: pd.Timestamp) -> pd.DataFrame:
    """Return daily_df rows at the last trading day of each calendar month, before `before`."""
    # Resample the index (trading days) to get the actual last trading day of each month
    actual_month_ends = pd.DatetimeIndex(
        daily_df.index.to_series().resample("ME").last().dropna().values
    )
    actual_month_ends = actual_month_ends[actual_month_ends < before]
    return daily_df.loc[actual_month_ends].dropna()


def section_market_outcomes(sigs: Signals, panels: Panels) -> str:
    """Historical SPX returns + IV changes by signal quartile.

    Monthly-sampled signal values to reduce autocorrelation.
    Today's quartile marked '*'.
    """
    last_dt = sigs.latest_date()
    primary = _primary_underlying(panels)
    price_col = panels.prices_panel[primary]
    iv_col = panels.iv_panel[primary]

    fwd_ret = _forward_returns(price_col, [21, 63])
    fwd_iv = _forward_iv_change(iv_col, [21])

    # Monthly sample: actual last trading day of each month (avoids calendar month-end mismatch)
    all_sigs_daily = pd.concat(
        {sig: sigs.pct[sig][primary] for sig in BUCKETED_SIGNALS}, axis=1
    ).dropna()
    all_sigs_monthly = _last_trading_day_per_month(all_sigs_daily, before=last_dt)
    monthly_dates = all_sigs_monthly.index

    out = [
        "## Market Outcomes by Signal Quartile",
        "",
        f"Signal sampled monthly (month-end). Forward outcomes: {primary} returns + IV change.",
        "Mean % return and hit rate (% > 0) over next 1m (21d) and 3m (63d).",
        "Today's quartile marked '*'. Base rates only — no predictive warrant.",
        "",
    ]

    for sig in BUCKETED_SIGNALS:
        sig_monthly = all_sigs_monthly[sig]
        today_val = sigs.pct[sig][primary].loc[last_dt] if last_dt in sigs.pct[sig][primary].index else np.nan
        today_q = _today_quartile(today_val)

        rows = []
        for dt in monthly_dates:
            sig_val = sig_monthly.loc[dt] if dt in sig_monthly.index else np.nan
            if pd.isna(sig_val):
                continue
            r21 = fwd_ret[21].loc[dt] if dt in fwd_ret[21].index else np.nan
            r63 = fwd_ret[63].loc[dt] if dt in fwd_ret[63].index else np.nan
            iv21 = fwd_iv[21].loc[dt] if dt in fwd_iv[21].index else np.nan
            rows.append({"sig_val": sig_val, "r21": r21, "r63": r63, "iv21": iv21})

        if not rows:
            continue

        df = pd.DataFrame(rows)
        df["q"] = _bucket_by_pct(df["sig_val"].values)

        agg = df.groupby("q", observed=False).agg(
            n=("r21", "count"),
            r21_mean=("r21", lambda x: x.dropna().mean() * 100 if x.notna().any() else np.nan),
            r21_hit=("r21", lambda x: (x.dropna() > 0).mean() * 100 if x.notna().any() else np.nan),
            r63_mean=("r63", lambda x: x.dropna().mean() * 100 if x.notna().any() else np.nan),
            r63_hit=("r63", lambda x: (x.dropna() > 0).mean() * 100 if x.notna().any() else np.nan),
            iv21_mean=("iv21", lambda x: x.dropna().mean() if x.notna().any() else np.nan),
        ).round(2)

        out.append(f"### {sig}  (today: {today_val:.2f} → {today_q})")
        out.append("")
        header = (
            f"  {'Q':3s}  {'n':>4s}  {'1m ret%':>8s}  {'1m hit%':>7s}  "
            f"{'3m ret%':>8s}  {'3m hit%':>7s}  {'1m ΔIV':>7s}"
        )
        out.append(header)
        out.append("  " + "-" * (len(header) - 2))
        for q in _PCT_LABELS:
            marker = "*" if q == today_q else " "
            if q not in agg.index or agg.loc[q, "n"] == 0:
                out.append(f"  {q}{marker}   (no data)")
                continue
            row = agg.loc[q]
            r21m = f"{row['r21_mean']:>+8.2f}" if not pd.isna(row["r21_mean"]) else "     n/a"
            r21h = f"{row['r21_hit']:>7.1f}" if not pd.isna(row["r21_hit"]) else "    n/a"
            r63m = f"{row['r63_mean']:>+8.2f}" if not pd.isna(row["r63_mean"]) else "     n/a"
            r63h = f"{row['r63_hit']:>7.1f}" if not pd.isna(row["r63_hit"]) else "    n/a"
            iv21 = f"{row['iv21_mean']:>+7.2f}" if not pd.isna(row["iv21_mean"]) else "    n/a"
            out.append(
                f"  {q}{marker}  {int(row['n']):>4d}  {r21m}  {r21h}  {r63m}  {r63h}  {iv21}"
            )
        out.append("")

    return "\n".join(out)


def section_short_vol_environment(sigs: Signals, panels: Panels) -> str:
    last_dt = sigs.latest_date()
    primary = _primary_underlying(panels)

    all_sigs_daily = pd.concat(
        {sig: sigs.pct[sig][primary] for sig in BUCKETED_SIGNALS}, axis=1
    ).dropna()
    all_sigs_monthly = _last_trading_day_per_month(all_sigs_daily, before=last_dt)
    monthly_dates = all_sigs_monthly.index

    prices = panels.prices_panel[primary]
    iv = panels.iv_panel[primary]

    # Forward realized vol: annualized std of next 21 daily log returns
    log_rets = np.log(prices / prices.shift(1))

    def _forward_rv21(dt: pd.Timestamp) -> float:
        try:
            loc = prices.index.get_loc(dt)
            future_prices = prices.iloc[loc + 1: loc + 23]
            if len(future_prices) < 15:
                return np.nan
            lr = np.log(future_prices / future_prices.shift(1)).dropna()
            if len(lr) < 15:
                return np.nan
            return float(lr.std() * np.sqrt(252) * 100)
        except Exception:
            return np.nan

    rows = []
    for dt in monthly_dates:
        fwd_rv = _forward_rv21(dt)
        iv_open = iv.loc[dt] if dt in iv.index else np.nan
        vrp_capture = fwd_rv / iv_open if (not np.isnan(fwd_rv) and not np.isnan(iv_open) and iv_open > 0) else np.nan

        spot_fwd = prices.shift(-21).loc[dt] if dt in prices.index else np.nan
        spot_now = prices.loc[dt] if dt in prices.index else np.nan
        move_mag = abs(spot_fwd / spot_now - 1) * 100 if (not np.isnan(spot_fwd) and not np.isnan(spot_now) and spot_now != 0) else np.nan

        iv_fwd = iv.shift(-21).loc[dt] if dt in iv.index else np.nan
        iv_change = iv_fwd - iv_open if (not np.isnan(iv_fwd) and not np.isnan(iv_open)) else np.nan

        row = {"vrp_capture": vrp_capture, "move_mag": move_mag, "iv_change": iv_change}
        for sig in BUCKETED_SIGNALS:
            row[f"sig_{sig}"] = all_sigs_monthly.loc[dt, sig] if dt in all_sigs_monthly.index else np.nan
        rows.append(row)

    df = pd.DataFrame(rows, index=monthly_dates)

    non_nan_count = df["vrp_capture"].notna().sum()
    if non_nan_count < 150:
        return (
            "## Short-Vol Environment Historical Distributions\n\n"
            f"Insufficient data: only {non_nan_count} non-NaN forward_rv rows (need >= 150). "
            "Widen the start date or check data coverage.\n"
        )

    PCTS = [10, 25, 50, 75, 90]
    METRIC_COLS = ["vrp_capture", "move_mag", "iv_change"]
    METRIC_LABELS = ["VRP capture (rv/iv)", "Move magnitude (abs%)", "IV change (vol pts)"]

    out = [
        "## Short-Vol Environment Historical Distributions",
        "",
        "Signal-conditioned distributions of short-vol environment outcomes.",
        "Monthly sample ~2010–present. Today's quartile marked '*'.",
        "",
    ]

    for sig in BUCKETED_SIGNALS:
        today_val = sigs.pct[sig][primary].loc[last_dt] if last_dt in sigs.pct[sig][primary].index else np.nan
        today_q = _today_quartile(today_val)

        today_str = f"{today_val:.2f}" if not np.isnan(today_val) else "n/a"
        out.append(f"### {sig}  (today: {today_str} → {today_q})")
        out.append("")

        df["q"] = _bucket_by_pct(df[f"sig_{sig}"].values)

        # Build per-quartile stats
        q_stats: dict[str, dict] = {}
        for q_label in _PCT_LABELS:
            mask = df["q"] == q_label
            subset = df.loc[mask]
            q_stats[q_label] = {
                "n": int(subset["vrp_capture"].dropna().shape[0]),
                "pcts": {
                    col: [np.nanpercentile(subset[col].values, p) if subset[col].notna().any() else np.nan for p in PCTS]
                    for col in METRIC_COLS
                },
            }

        # Header row 1: quartile labels with n
        col_w = 30
        hdr1 = f"{'Metric':<24s}"
        hdr2 = f"{'':24s}"
        sep = f"{'':24s}"
        for q_label in _PCT_LABELS:
            marker = "*" if q_label == today_q else " "
            n = q_stats[q_label]["n"]
            label = f"{q_label}{marker} (n={n})"
            hdr1 += f"  {label:<28s}"
            hdr2 += f"  {'p10':>5s} {'p25':>5s} {'p50':>5s} {'p75':>5s} {'p90':>5s}   "
            sep += f"  {'—'*29}"

        out.append(hdr1.rstrip())
        out.append(hdr2.rstrip())
        out.append(sep.rstrip())

        for col, label in zip(METRIC_COLS, METRIC_LABELS):
            row_str = f"{label:<24s}"
            for q_label in _PCT_LABELS:
                pct_vals = q_stats[q_label]["pcts"][col]
                cells = []
                for v in pct_vals:
                    if np.isnan(v):
                        cells.append("  n/a")
                    elif col == "iv_change":
                        cells.append(f"{v:>+5.1f}")
                    else:
                        cells.append(f"{v:>5.2f}")
                row_str += "  " + " ".join(cells) + "   "
            out.append(row_str.rstrip())

        out.append("")
        out.append("Historical calibration only. ~48 obs per quartile. Not a forecast.")
        out.append("")

    return "\n".join(out)


def section_analog_periods(sigs: Signals, panels: Panels, k: int = K_NEIGHBORS) -> str:
    """K-nearest historical month-ends + realized market outcomes after each."""
    last_dt = sigs.latest_date()
    primary = _primary_underlying(panels)
    price_col = panels.prices_panel[primary]
    iv_col = panels.iv_panel[primary]

    out = [
        "## Past Periods That Looked Like Now",
        "",
        f"K={k} nearest historical month-ends, Euclidean distance over signal vector:",
        f"  features: {', '.join(NEIGHBOR_FEATURES)}",
        f"Realized market outcomes ({primary}): 1m (21d) and 3m (63d) after each match.",
        "",
    ]

    # Build monthly signal matrix using actual last trading days (not calendar month-ends)
    signal_daily = pd.concat(
        {sig: sigs.pct[sig][primary] for sig in NEIGHBOR_FEATURES}, axis=1
    ).dropna()
    historical = _last_trading_day_per_month(signal_daily, before=last_dt)

    today_vec = np.array([sigs.pct[s].loc[last_dt, primary] for s in NEIGHBOR_FEATURES])
    if np.isnan(today_vec).any():
        out.append("Today's signal vector has NaN — cannot compute neighbors.")
        return "\n".join(out)

    out.append("Today's vector: " + ", ".join(
        f"{s}={v:.2f}" for s, v in zip(NEIGHBOR_FEATURES, today_vec)
    ))
    out.append("")

    d = np.linalg.norm(historical.values - today_vec, axis=1)
    hist_with_d = historical.copy()
    hist_with_d["_d"] = d
    nn = hist_with_d.nsmallest(k, "_d")

    fwd_ret = _forward_returns(price_col, [21, 63])
    fwd_iv = _forward_iv_change(iv_col, [21])

    out.append(f"  {'Date':12s}  {'Dist':>5s}  {'1m ret%':>8s}  {'3m ret%':>8s}  {'1m ΔIV':>7s}")
    out.append("  " + "-" * 52)

    r21_vals, r63_vals, iv21_vals = [], [], []
    for dt in nn.index:
        dist = nn.loc[dt, "_d"]
        r21 = fwd_ret[21].loc[dt] if dt in fwd_ret[21].index else np.nan
        r63 = fwd_ret[63].loc[dt] if dt in fwd_ret[63].index else np.nan
        iv21 = fwd_iv[21].loc[dt] if dt in fwd_iv[21].index else np.nan
        r21_vals.append(r21)
        r63_vals.append(r63)
        iv21_vals.append(iv21)
        r21s = f"{r21*100:>+8.2f}" if not pd.isna(r21) else "     n/a"
        r63s = f"{r63*100:>+8.2f}" if not pd.isna(r63) else "     n/a"
        iv21s = f"{iv21:>+7.2f}" if not pd.isna(iv21) else "    n/a"
        out.append(f"  {str(dt.date()):12s}  {dist:>5.3f}  {r21s}  {r63s}  {iv21s}")

    out.append("")
    r21_arr = np.array([v * 100 for v in r21_vals if not pd.isna(v)])
    r63_arr = np.array([v * 100 for v in r63_vals if not pd.isna(v)])
    iv21_arr = np.array([v for v in iv21_vals if not pd.isna(v)])
    out.append(f"  Summary (n={len(nn)}):")
    if len(r21_arr) > 0:
        out.append(
            f"    1m:    mean={r21_arr.mean():+.2f}%  "
            f"hit={100*(r21_arr>0).mean():.0f}%  med={np.median(r21_arr):+.2f}%"
        )
    if len(r63_arr) > 0:
        out.append(
            f"    3m:    mean={r63_arr.mean():+.2f}%  "
            f"hit={100*(r63_arr>0).mean():.0f}%  med={np.median(r63_arr):+.2f}%"
        )
    if len(iv21_arr) > 0:
        out.append(
            f"    1m ΔIV: mean={iv21_arr.mean():+.2f}  med={np.median(iv21_arr):+.2f}"
        )

    return "\n".join(out)


def section_signal_dynamics(sigs: Signals) -> str:
    """Signal trends, extremes, and cross-signal divergences."""
    last_dt = sigs.latest_date()
    out = [
        "## Signal Dynamics",
        "",
        "Current vs ~1m (21 trading days) and ~3m (63 trading days) ago.",
        "Rising/falling: pct-rank shift > 0.05. Extremes (>= 0.80 or <= 0.20) flagged.",
        "",
    ]

    underlyings = sigs.pct["vrp"].columns.tolist()
    for u in underlyings:
        out.append(f"### {u}")
        out.append("")
        out.append(f"  {'signal':12s}  {'now':>5s}  {'1m ago':>6s}  {'3m ago':>6s}  {'trend':>8s}  reading")
        out.append("  " + "-" * 68)

        for sig in sigs.pct:
            ts = sigs.pct[sig][u].dropna()
            now_val = ts.iloc[-1] if len(ts) > 0 else np.nan

            v1m = ts.iloc[-22] if len(ts) > 21 else np.nan
            v3m = ts.iloc[-64] if len(ts) > 63 else np.nan

            if not pd.isna(now_val) and not pd.isna(v1m):
                diff = now_val - v1m
                trend = "rising" if diff > 0.05 else ("falling" if diff < -0.05 else "stable")
            else:
                trend = "n/a"

            flag = "  <<" if (not pd.isna(now_val) and (now_val >= 0.80 or now_val <= 0.20)) else ""
            ns = f"{now_val:.2f}" if not pd.isna(now_val) else " n/a"
            v1s = f"{v1m:.2f}" if not pd.isna(v1m) else "  n/a"
            v3s = f"{v3m:.2f}" if not pd.isna(v3m) else "  n/a"
            out.append(
                f"  {sig:12s}  {ns:>5s}  {v1s:>6s}  {v3s:>6s}  {trend:>8s}  {_interp(now_val, sig)}{flag}"
            )
        out.append("")

    return "\n".join(out)


def build_dashboard(sigs: Signals, panels: Panels) -> str:
    bar = "=" * 72
    parts = [
        bar,
        "  OPTIONS QUANT — MARKET INTELLIGENCE DASHBOARD",
        bar,
        "",
        section_environment_context(sigs),
        "",
        section_market_outcomes(sigs, panels),
        "",
        section_analog_periods(sigs, panels),
        "",
        section_signal_dynamics(sigs),
        "",
        bar,
        "  No score. No recommendation. Market intelligence, not a signal.",
        "  Caveats: synthetic 90mny IV (POC; calibrated, not Bloomberg-observed),",
        "  0% dividend yield. Historical base rates only; no predictive warrant.",
        bar,
    ]
    return "\n".join(parts)
