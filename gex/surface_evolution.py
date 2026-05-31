"""
Surface evolution engine.

Computes daily ΔIV scalars (level, rms, skew_change, term_change) by differencing
today's interpolated vol surface against an N-day rolling-mean baseline.  Results are
persisted idempotently to out/surface_evolution.parquet indexed by (date, ticker, horizon).

Public API
----------
compute_evolution_scalars(IV_diff_masked, otm_grid, dte_grid) -> dict
    Pure function — receives an already-masked ΔIV array + grid axes, returns four scalars.
    No I/O, no masking.

update_evolution(ticker, date) -> None
    Implements the canonical 8-step rolling-mean algorithm.  Owns grid construction,
    baseline loading, mask intersection, scalar dispatch, and persistence.

save_evolution_row(date, ticker, horizon, prior_date, level, rms, skew_change,
                   term_change, coverage) -> None
    Idempotent parquet write (3-key dedup on date + ticker + horizon).

load_evolution(ticker, horizon=None, days=30) -> pd.DataFrame
    Read filtered rows from the evolution store.

backfill(ticker, start_date) -> None
    Retro-compute evolution for all dates >= start_date in the surface history.
"""
from __future__ import annotations

import datetime
import pathlib

import numpy as np
import pandas as pd

from gex import config
from gex.analytics import coverage_mask, rbf_grid
from gex.surface_history import (
    list_available_dates,
    load_surface_snapshot,
    nth_trading_day_back,
)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

STORE = pathlib.Path(__file__).resolve().parents[1] / "out" / "surface_evolution.parquet"

_FLOAT_COLS = ("level", "rms", "skew_change", "term_change", "coverage")

HORIZONS = (5, 10, 20)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _construct_grid_axes(surface_df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Build shared DTE and %OTM grid axes from today's surface.

    Called exactly ONCE per update_evolution invocation.  The returned axes are
    passed unchanged to every rbf_grid and coverage_mask call for today AND all
    prior dates so all grids have identical shape (SURFACE_GRID_LM, SURFACE_GRID_DTE).
    """
    dte_max = min(float(surface_df["dte"].max()), float(config.SURFACE_DTE_MAX))
    dte_grid = np.linspace(5.0, dte_max, config.SURFACE_GRID_DTE)
    otm_grid = np.linspace(
        -config.SURFACE_PLOT_OTM_CLIP * 100.0,
        config.SURFACE_PLOT_OTM_CLIP * 100.0,
        config.SURFACE_GRID_LM,
    )
    return dte_grid, otm_grid


# ---------------------------------------------------------------------------
# Public — pure scalar function
# ---------------------------------------------------------------------------

def compute_evolution_scalars(
    IV_diff_masked: np.ndarray,
    otm_grid: np.ndarray,
    dte_grid: np.ndarray,
) -> dict:
    """Decompose a masked ΔIV array into four interpretable scalars.

    Pure function — no I/O, no masking.  Receives an already-masked ΔIV array
    (NaN where the intersection mask is False) and the shared grid axes.

    Parameters
    ----------
    IV_diff_masked : ndarray shape (SURFACE_GRID_LM, SURFACE_GRID_DTE) = (30, 40)
        IV_today minus IV_baseline_mean, with non-intersection cells set to NaN.
    otm_grid : ndarray shape (30,)
        %OTM axis (same axes used to build IV_diff_masked).
    dte_grid : ndarray shape (40,)
        DTE axis (same axes used to build IV_diff_masked).

    Returns
    -------
    dict with keys: level, rms, skew_change, term_change, coverage — all floats.
    NaN is never replaced with 0.
    """
    # level — parallel shift; positive = IV rose on average
    level = float(np.nanmean(IV_diff_masked))

    # rms — total movement magnitude regardless of direction
    rms = float(np.sqrt(np.nanmean(IV_diff_masked ** 2)))

    # skew_change — put-wing minus call-wing mean ΔIV
    put_wing_idx = otm_grid < config.SURFACE_EVOLUTION_PUT_WING_CLIP
    call_wing_idx = otm_grid > config.SURFACE_EVOLUTION_CALL_WING_CLIP
    skew_change = float(
        np.nanmean(IV_diff_masked[put_wing_idx, :])
        - np.nanmean(IV_diff_masked[call_wing_idx, :])
    )

    # term_change — front-ATM minus back-ATM mean ΔIV
    dte_front_idx = dte_grid <= config.SURFACE_EVOLUTION_DTE_FRONT_MAX
    dte_back_idx = dte_grid >= config.SURFACE_EVOLUTION_DTE_BACK_MIN
    atm_idx = np.abs(otm_grid) <= config.SURFACE_EVOLUTION_ATM_CLIP
    front_atm = IV_diff_masked[np.ix_(atm_idx, dte_front_idx)]
    back_atm = IV_diff_masked[np.ix_(atm_idx, dte_back_idx)]
    term_change = float(np.nanmean(front_atm) - np.nanmean(back_atm))

    # coverage — fraction of grid cells included in the intersection mask
    coverage = float(np.sum(~np.isnan(IV_diff_masked))) / IV_diff_masked.size

    return {
        "level": level,
        "rms": rms,
        "skew_change": skew_change,
        "term_change": term_change,
        "coverage": coverage,
    }


# ---------------------------------------------------------------------------
# Public — idempotent persistence
# ---------------------------------------------------------------------------

def save_evolution_row(
    date: datetime.date,
    ticker: str,
    horizon: int,
    prior_date: datetime.date,
    level: float,
    rms: float,
    skew_change: float,
    term_change: float,
    coverage: float,
) -> None:
    """Append or replace a single (date, ticker, horizon) row in the evolution store.

    Idempotent: re-running with the same key produces one row, never two.
    Mirrors the read-filter-concat-write pattern from gex/validation.py.
    """
    row = {
        "date": date,
        "ticker": ticker,
        "horizon": horizon,
        "prior_date": prior_date,
        "level": float(level),
        "rms": float(rms),
        "skew_change": float(skew_change),
        "term_change": float(term_change),
        "coverage": float(coverage),
    }

    try:
        if STORE.exists():
            hist = pd.read_parquet(STORE)
            for col in _FLOAT_COLS:
                if col in hist.columns:
                    hist[col] = hist[col].astype("float64")
            mask = (
                (hist["date"] == row["date"])
                & (hist["ticker"] == ticker)
                & (hist["horizon"] == horizon)
            )
            hist = hist[~mask]
            hist = pd.concat([hist, pd.DataFrame([row])], ignore_index=True)
        else:
            STORE.parent.mkdir(parents=True, exist_ok=True)
            hist = pd.DataFrame([row])

        hist.to_parquet(STORE, index=False)
        print(
            f"[surface_evolution] {ticker} {date} horizon={horizon}: "
            f"level={level:.2f}pp rms={rms:.2f}pp saved"
        )
    except Exception as exc:
        print(f"[surface_evolution] save_evolution_row failed for {ticker} {date} horizon={horizon}: {exc}")


def load_evolution(
    ticker: str,
    horizon: int | None = None,
    days: int = 30,
) -> pd.DataFrame:
    """Load evolution metrics from the store for a single ticker.

    Mirrors gex/validation.py load_history pattern.  Optionally filters by horizon.
    Returns an empty DataFrame if the store does not exist or on exception.
    """
    if not STORE.exists():
        return pd.DataFrame()
    try:
        hist = pd.read_parquet(STORE)
        hist["date"] = pd.to_datetime(hist["date"]).dt.date
        hist = hist[hist["ticker"] == ticker].sort_values("date", ascending=False)
        if horizon is not None:
            hist = hist[hist["horizon"] == horizon]
        return hist.head(days).reset_index(drop=True)
    except Exception as exc:
        print(f"[surface_evolution] load_evolution failed for {ticker}: {exc}")
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Public — canonical 8-step rolling-mean algorithm
# ---------------------------------------------------------------------------

def update_evolution(ticker: str, date: datetime.date) -> None:
    """Compute and persist ΔIV evolution scalars for all horizons on a given date.

    Implements the canonical 8-step rolling-mean baseline algorithm:

    Step 1.  Load today's surface and spot.  Return early if empty or spot is None.
    Step 2.  Construct shared grid axes ONCE from today's surface.
    Step 3.  Compute today's IV grid and coverage mask on those shared axes.
    For each horizon N in HORIZONS (5, 10, 20):
      Step 4.  Resolve all N prior session dates.  Skip horizon if the Nth date is None.
      Step 5.  Load each prior day's surface+spot; compute its grid and mask on the SAME axes.
      Step 6.  Stack prior grids → nanmean baseline.  Skip horizon if stack is empty.
      Step 7.  Intersect all masks (today AND all N prior).
      Step 8.  Diff → mask → compute_evolution_scalars → save.
    """
    # Step 1 — today's surface
    surface_today, spot_today = load_surface_snapshot(ticker, date)
    if surface_today.empty or spot_today is None:
        return

    # Step 2 — construct grid axes ONCE (loop-invariant)
    dte_grid, otm_grid = _construct_grid_axes(surface_today)

    # Step 3 — today's grid + mask
    IV_today = rbf_grid(
        surface_today, spot_today, dte_grid, otm_grid, dte_floor=5
    )
    mask_today = coverage_mask(
        surface_today, spot_today, dte_grid, otm_grid, dte_floor=5
    )

    for horizon in HORIZONS:
        # Step 4 — resolve prior dates; skip entire horizon if the Nth back is None
        prior_date_label = nth_trading_day_back(ticker, date, horizon)
        if prior_date_label is None:
            continue  # cold-start: not enough history for this horizon

        prior_dates = [
            nth_trading_day_back(ticker, date, k)
            for k in range(1, horizon + 1)
        ]
        prior_dates = [d for d in prior_dates if d is not None]

        # Step 5 — load each prior day's surface on the SAME shared axes
        IV_grids: list[np.ndarray] = []
        mask_list: list[np.ndarray] = []

        for pd_date in prior_dates:
            surface_prior, spot_prior = load_surface_snapshot(ticker, pd_date)
            if surface_prior.empty or spot_prior is None:
                continue
            IV_prior = rbf_grid(
                surface_prior, spot_prior, dte_grid, otm_grid, dte_floor=5
            )
            mask_prior = coverage_mask(
                surface_prior, spot_prior, dte_grid, otm_grid, dte_floor=5
            )
            IV_grids.append(IV_prior)
            mask_list.append(mask_prior)

        if not IV_grids:
            continue  # no valid prior data for this horizon

        # Step 6 — stack and nanmean baseline
        IV_baseline_stack = np.stack(IV_grids, axis=0)  # (n_prior, 30, 40)
        IV_baseline_mean = np.nanmean(IV_baseline_stack, axis=0)  # (30, 40)

        # Step 7 — mask intersection: AND of today + all N prior masks
        mask_intersection = mask_today.copy()
        for m in mask_list:
            mask_intersection &= m

        # Step 8 — diff, apply mask, compute scalars, persist
        IV_diff = IV_today - IV_baseline_mean
        IV_diff_masked = np.where(mask_intersection, IV_diff, np.nan)

        scalars = compute_evolution_scalars(IV_diff_masked, otm_grid, dte_grid)
        save_evolution_row(
            date=date,
            ticker=ticker,
            horizon=horizon,
            prior_date=prior_date_label,
            **scalars,
        )


# ---------------------------------------------------------------------------
# Public — cold-start backfill
# ---------------------------------------------------------------------------

def backfill(ticker: str, start_date: datetime.date) -> None:
    """Retro-compute evolution metrics for all stored dates >= start_date.

    Writes idempotently — safe to re-run; duplicate (date, ticker, horizon)
    rows are replaced, not appended.
    """
    available_dates = list_available_dates(ticker)
    valid_dates = [d for d in available_dates if d >= start_date]

    if not valid_dates:
        print(f"[surface_evolution] backfill: no dates >= {start_date} for {ticker}")
        return

    print(
        f"[surface_evolution] backfill: {ticker} — {len(valid_dates)} dates "
        f"from {min(valid_dates)} to {max(valid_dates)}"
    )
    for date in reversed(valid_dates):  # oldest first for progress clarity
        update_evolution(ticker, date)

    print(f"[surface_evolution] backfill: {ticker} complete")


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Surface evolution engine CLI")
    parser.add_argument("--backfill", action="store_true", help="run backfill")
    parser.add_argument("ticker", nargs="?", default=None, help="ticker (SPY/QQQ/IWM)")
    parser.add_argument(
        "--start",
        type=datetime.date.fromisoformat,
        default=None,
        help="backfill start date (YYYY-MM-DD); defaults to 90 days ago",
    )
    args = parser.parse_args()

    if args.backfill and args.ticker:
        start = args.start or (datetime.date.today() - datetime.timedelta(days=90))
        backfill(args.ticker, start)
    else:
        parser.print_help()
