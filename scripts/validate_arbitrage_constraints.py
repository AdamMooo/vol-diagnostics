#!/usr/bin/env python3
"""
Validation script: test arbitrage constraint system on live data.

Usage:
    python scripts/validate_arbitrage_constraints.py --ticker SPY --date 2026-08-16
    python scripts/validate_arbitrage_constraints.py --ticker QQQ --mode soft

Options:
    --ticker: SPY, QQQ, or IWM
    --date: YYYY-MM-DD (default: today)
    --mode: 'none', 'soft', 'strict' (default: 'none')
    --verbose: Print full constraint violations
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys

import numpy as np
import pandas as pd

# Add parent to path
sys.path.insert(0, str(__file__).split('/scripts/')[0])

from engine import config
from engine.data.data_loader import load_chain
from engine.surface.surface_constraints_integration import (
    fit_surface_with_diagnostics,
    export_constraint_audit,
)


def validate_ticker(ticker: str, date: dt.date | None = None,
                   mode: str = "none", verbose: bool = False) -> dict:
    """Run constraint validation on a ticker's surface."""
    if date is None:
        date = dt.date.today()

    print(f"\n{'='*70}")
    print(f"Validating {ticker} surface for {date}")
    print(f"Mode: {mode} | Verbose: {verbose}")
    print(f"{'='*70}")

    # Load chain
    try:
        chain_snap = load_chain(ticker, today=date)
        chain_df = chain_snap.chains
        if chain_df is None or chain_df.empty:
            print(f"❌ No chain data available for {ticker} on {date}")
            return {"status": "no_data", "ticker": ticker, "date": date}
        spot = chain_snap.spot
        if spot is None:
            print(f"❌ Spot price not found")
            return {"status": "no_spot", "ticker": ticker, "date": date}
    except Exception as exc:
        print(f"❌ Failed to load chain: {exc}")
        import traceback
        traceback.print_exc()
        return {"status": "load_error", "ticker": ticker, "date": date, "error": str(exc)}

    # Compute DTE from expiry and prepare for surface fitting
    chain_df = chain_df.copy()
    chain_df["expiry"] = pd.to_datetime(chain_df["expiry"])
    chain_df["dte"] = (chain_df["expiry"].dt.date - date).apply(lambda x: x.days)

    # Rename columns to match surface fitting API
    surface_df = chain_df[["strike", "dte", "iv"]].copy()
    surface_df.rename(columns={"iv": "iv_pct"}, inplace=True)
    surface_df["iv_pct"] = surface_df["iv_pct"] * 100  # Convert to percentages

    # Setup grid
    dte_max = min(180, float(chain_df["dte"].max()))
    dte_grid = np.linspace(5.0, dte_max, config.SURFACE_GRID_DTE)
    otm_grid = np.linspace(-config.SURFACE_INTERACTIVE_CLIP,
                           config.SURFACE_INTERACTIVE_CLIP,
                           config.SURFACE_GRID_LM)

    # Fit with diagnostics
    print(f"\nFitting {len(surface_df)} quotes with constraint checking...")
    try:
        result = fit_surface_with_diagnostics(
            surface_df, spot, dte_grid, otm_grid,
            smoothing=config.SURFACE_INTERACTIVE_SMOOTHING,
            constraint_check=True,
            constraint_repair=mode,
        )
    except Exception as exc:
        print(f"❌ Fitting failed: {exc}")
        return {"status": "fit_error", "ticker": ticker, "date": date, "error": str(exc)}

    # Report
    print(f"\n{export_constraint_audit(result)}")

    # Detailed violations if verbose
    if verbose and not result["constraints_clean"]:
        print("\n" + "="*70)
        print("DETAILED VIOLATIONS")
        print("="*70)

        # Butterfly violations
        bf = result["constraint_checks"].get("butterfly", {})
        if bf.get("violations"):
            print(f"\nButterfly Violations ({len(bf['violations'])} cells):")
            for v in bf["violations"][:5]:  # Show first 5
                print(f"  K/S={np.exp(v['log_moneyness']):.3f}, DTE={v['dte']:.0f}: "
                      f"ρ(K)={v['density']:.2e}")
            if len(bf["violations"]) > 5:
                print(f"  ... and {len(bf['violations']) - 5} more")

        # Calendar violations
        cal = result["constraint_checks"].get("calendar", {})
        if cal.get("violations"):
            print(f"\nCalendar Violations ({len(cal['violations'])} pairs):")
            for v in cal["violations"][:5]:
                print(f"  ln(K/S)={v['log_moneyness']:.4f}: "
                      f"σ²T drops from {v['total_var_1']:.6f} to {v['total_var_2']:.6f} "
                      f"({v['variance_decrease_pct']:.1f}%)")
            if len(cal["violations"]) > 5:
                print(f"  ... and {len(cal['violations']) - 5} more")

        # Tail instability
        tail = result["constraint_checks"].get("tail", {})
        if not tail.get("is_stable"):
            print(f"\nTail Instability:")
            if not tail.get("put_wing_linear"):
                print(f"  Put wing: curvature={tail.get('put_wing_curvature_max'):.2f}pp (unstable)")
            if not tail.get("call_wing_linear"):
                print(f"  Call wing: curvature={tail.get('call_wing_curvature_max'):.2f}pp (unstable)")

    # Greeks summary
    greeks = result.get("second_order_greeks", {})
    if greeks and "deformation_summary" in greeks:
        print(f"\nSurface Deformation:")
        print(f"  {greeks['deformation_summary']}")
        if "vanna_summary" in greeks:
            print(f"  Vanna: mean={greeks['vanna_summary'].get('mean', np.nan):.4f}, "
                  f"std={greeks['vanna_summary'].get('std', np.nan):.4f}")
        if "volga_summary" in greeks:
            print(f"  Volga: mean={greeks['volga_summary'].get('mean', np.nan):.4f}, "
                  f"std={greeks['volga_summary'].get('std', np.nan):.4f}")

    # Summary
    print(f"\n{'='*70}")
    if result["constraints_clean"]:
        print(f"✅ {ticker} surface is CLEAN")
    else:
        print(f"⚠️  {ticker} surface has VIOLATIONS")
        if result.get("repair_log"):
            print(f"   Repair applied: {result['repair_log']}")

    return {
        "status": "success",
        "ticker": ticker,
        "date": date,
        "constraints_clean": result["constraints_clean"],
        "butterfly_clean": result["constraint_checks"].get("butterfly", {}).get("is_clean", None),
        "calendar_clean": result["constraint_checks"].get("calendar", {}).get("is_clean", None),
        "tail_stable": result["constraint_checks"].get("tail", {}).get("is_stable", None),
        "rmse": result.get("fit_quality", {}).get("rmse", None),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Validate arbitrage constraints on option surfaces"
    )
    parser.add_argument("--ticker", default="SPY",
                       choices=["SPY", "QQQ", "IWM"],
                       help="Ticker to validate")
    parser.add_argument("--date", default=None,
                       help="Date (YYYY-MM-DD); default is today")
    parser.add_argument("--mode", default="none",
                       choices=["none", "soft", "strict"],
                       help="Repair mode")
    parser.add_argument("--all-tickers", action="store_true",
                       help="Validate all three tickers")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Print detailed violations")

    args = parser.parse_args()

    # Parse date
    if args.date:
        try:
            date = dt.datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            print(f"Invalid date format: {args.date}. Use YYYY-MM-DD.")
            return 1
    else:
        date = dt.date.today()

    # Run validation
    tickers = ["SPY", "QQQ", "IWM"] if args.all_tickers else [args.ticker]
    results = []

    for ticker in tickers:
        result = validate_ticker(ticker, date, args.mode, args.verbose)
        results.append(result)

    # Summary table
    if len(results) > 1:
        print(f"\n{'='*70}")
        print("SUMMARY")
        print(f"{'='*70}")
        print(f"{'Ticker':<10} {'Date':<12} {'Status':<20} {'Butterfly':<12} {'Calendar':<12} {'Tail':<10}")
        print("-" * 70)
        for r in results:
            if r["status"] == "success":
                bf = "✅ PASS" if r["butterfly_clean"] else "❌ FAIL"
                cal = "✅ PASS" if r["calendar_clean"] else "❌ FAIL"
                tail = "✅ OK" if r["tail_stable"] else "⚠️ UNSTABLE"
                print(f"{r['ticker']:<10} {str(r['date']):<12} {'success':<20} {bf:<12} {cal:<12} {tail:<10}")
            else:
                print(f"{r['ticker']:<10} {str(r.get('date', 'N/A')):<12} {r['status']:<20}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
