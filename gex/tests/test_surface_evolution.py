"""Phase 9 Surface Evolution Engine — test scaffolding.

Covers EVOL requirements:
  EVOL-01  four scalars (level, rms, skew_change, term_change) on masked grid
  EVOL-02  multi-horizon nth_trading_day_back (5, 10, 20 sessions)
  EVOL-03  idempotent parquet store (date, ticker, horizon dedup)
  EVOL-05  cross-ticker comparability (SPY/QQQ/IWM)
  EVOL-06  backfill consistency

Tasks 1+2 (Plan 01): nth_trading_day_back tests and stub scaffolding.
Tasks 3+ (Plans 02-03): scalar and persistence tests — stubs below.
"""
from __future__ import annotations

import datetime

import numpy as np
import pandas as pd
import pytest

from gex.surface_history import nth_trading_day_back


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_dates(n: int, base: datetime.date | None = None) -> list[datetime.date]:
    """Build a descending list of n consecutive dates starting from base."""
    if base is None:
        base = datetime.date(2026, 5, 30)
    return [base - datetime.timedelta(days=i) for i in range(n)]


# ---------------------------------------------------------------------------
# nth_trading_day_back tests (EVOL-02) — must pass after Task 2
# ---------------------------------------------------------------------------

def test_nth_back_resolves_to_correct_index(monkeypatch):
    """With 5 stored dates and anchor=newest, n=2 must return the 3rd entry."""
    dates = _make_dates(5)  # [d0, d0-1, d0-2, d0-3, d0-4] newest first
    monkeypatch.setattr(
        "gex.surface_history.list_available_dates",
        lambda ticker: dates,
    )
    result = nth_trading_day_back("SPY", dates[0], n=2)
    assert result == dates[2], f"expected {dates[2]}, got {result}"


def test_nth_back_cold_start_returns_none(monkeypatch):
    """anchor is in the list but there are not enough dates after it."""
    dates = _make_dates(3)  # only 3 dates; n=5 exceeds available history
    monkeypatch.setattr(
        "gex.surface_history.list_available_dates",
        lambda ticker: dates,
    )
    result = nth_trading_day_back("SPY", dates[0], n=5)
    assert result is None


def test_nth_back_anchor_not_in_store_returns_none(monkeypatch):
    """anchor_date is absent from the stored list — must return None."""
    dates = _make_dates(5)
    absent = datetime.date(2000, 1, 1)  # not in dates
    monkeypatch.setattr(
        "gex.surface_history.list_available_dates",
        lambda ticker: dates,
    )
    result = nth_trading_day_back("SPY", absent, n=1)
    assert result is None


# ---------------------------------------------------------------------------
# Scalar behavior stubs (EVOL-01) — implemented in Plan 02
# ---------------------------------------------------------------------------

def test_scalars_level_is_nanmean_diff():
    """level scalar = np.nanmean(IV_diff_masked) on the intersection mask."""
    pytest.skip("implemented in Plan 02")


def test_scalars_rms_ignores_nan():
    """rms scalar = sqrt(np.nanmean(IV_diff_masked ** 2)); NaN cells excluded."""
    pytest.skip("implemented in Plan 02")


def test_skew_change_wing_split():
    """skew_change = mean(put-wing diff) - mean(call-wing diff) using config clips."""
    pytest.skip("implemented in Plan 02")


def test_term_change_front_back():
    """term_change = mean(front-ATM diff) - mean(back-ATM diff) using config DTE bands."""
    pytest.skip("implemented in Plan 02")


def test_mask_intersection_excludes_extrapolated_cells():
    """Cells where any baseline day lacks support are excluded via AND mask."""
    pytest.skip("implemented in Plan 02")


# ---------------------------------------------------------------------------
# Persistence behavior stubs (EVOL-03) — implemented in Plan 03
# ---------------------------------------------------------------------------

def test_evolution_idempotent_on_rerun():
    """Re-running save_evolution_row with same (date, ticker, horizon) deduplicates."""
    pytest.skip("implemented in Plan 03")


def test_backfill_consistency():
    """Backfill from surface_history produces identical scalars to daily ingestion."""
    pytest.skip("implemented in Plan 03")


def test_cold_start_no_row_written():
    """No evolution row is written when nth_trading_day_back returns None."""
    pytest.skip("implemented in Plan 03")
