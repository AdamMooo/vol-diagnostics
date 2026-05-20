"""
GEX POC entry point.

Usage:
    cd options-quant
    python -m gex.run_gex                   # SPY, save charts to out/
    python -m gex.run_gex --ticker QQQ      # different underlying
    python -m gex.run_gex --no-save         # show charts interactively

What it proves:
    1. Can compute a stable gamma profile from public chain data
    2. Profile produces intuitive levels (walls, zero-gamma area)
    3. Regime classification is interpretable

NOTE: This is a lightweight CLI entry point. It intentionally bypasses
compute_ticker() (which fetches live ^IRX and computes vol surface/skew/slopes).
The gamma profile sweep uses config.RISK_FREE_FALLBACK. For production output,
use run_daily or the Streamlit dashboard (both call compute_ticker()).
"""
from __future__ import annotations

import argparse
import datetime
import pathlib

from gex.data_loader import load_chain
from gex.greeks_engine import add_greeks
from gex.exposure_engine import compute_gex, strike_gex, gamma_profile
from gex.analytics import summarise, plot_strike_gex, plot_gamma_profile

OUT_DIR = pathlib.Path(__file__).resolve().parents[1] / "out"


def run(ticker: str = "SPY", save: bool = True) -> dict:
    print(f"[gex] Loading chain for {ticker}...")
    snapshot = load_chain(ticker)
    print(f"[gex] Spot: {snapshot.spot:.2f}  |  "
          f"Options loaded: {len(snapshot.chains):,}  |  "
          f"Expiries: {snapshot.chains['expiry'].nunique()}")

    df = add_greeks(snapshot.chains, spot=snapshot.spot, today=snapshot.as_of)
    df = compute_gex(df, spot=snapshot.spot)

    strike_df = strike_gex(df)
    profile_df = gamma_profile(df, spot=snapshot.spot)
    summary = summarise(strike_df, profile_df, spot=snapshot.spot)

    _print_summary(summary, ticker)

    if save:
        OUT_DIR.mkdir(exist_ok=True)
        date_tag = snapshot.as_of.isoformat()

        fig1 = plot_strike_gex(strike_df, snapshot.spot, ticker, summary)
        path1 = OUT_DIR / f"gex_strikes_{ticker}_{date_tag}.html"
        fig1.write_html(str(path1))
        print(f"[gex] Saved: {path1}")

        fig2 = plot_gamma_profile(profile_df, snapshot.spot, ticker, summary)
        path2 = OUT_DIR / f"gex_profile_{ticker}_{date_tag}.html"
        fig2.write_html(str(path2))
        print(f"[gex] Saved: {path2}")
    else:
        fig1 = plot_strike_gex(strike_df, snapshot.spot, ticker, summary)
        fig2 = plot_gamma_profile(profile_df, snapshot.spot, ticker, summary)
        fig1.show()
        fig2.show()

    return summary


def _print_summary(s: dict, ticker: str) -> None:
    print(f"\n{'='*50}")
    print(f"  {ticker} GEX SUMMARY — {datetime.date.today()}")
    print(f"{'='*50}")
    print(f"  Spot:             {s['spot']:.2f}")
    print(f"  Net GEX:          ${s['net_gex']/1e9:.2f}B")
    zg = s.get("zero_gamma_level")
    print(f"  Zero-gamma level: {f'{zg:.2f}' if zg else 'not found in ±15% range'}")
    cw = s.get("call_wall")
    pw = s.get("put_wall")
    print(f"  Call wall:        {f'{cw:.0f}' if cw else 'none'}")
    print(f"  Put wall:         {f'{pw:.0f}' if pw else 'none'}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="SPY")
    parser.add_argument("--no-save", dest="save", action="store_false")
    args = parser.parse_args()
    run(ticker=args.ticker, save=args.save)
