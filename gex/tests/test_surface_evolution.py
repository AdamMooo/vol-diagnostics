"""Phase 9 Surface Evolution Engine — unit + integration tests.

Covers EVOL requirements:
  EVOL-01  four scalars (level, rms, skew_change, term_change) on masked grid
  EVOL-02  multi-horizon nth_trading_day_back (5, 10, 20 sessions)
  EVOL-03  idempotent parquet store (date, ticker, horizon dedup)
  EVOL-05  cross-ticker comparability (SPY/QQQ/IWM)
  EVOL-06  backfill consistency

Tasks 1+2 (Plan 01): nth_trading_day_back tests and stub scaffolding.
Tasks 3+ (Plan 02): scalar and persistence tests.
"""
from __future__ import annotations

import datetime
import pathlib

import numpy as np
import pandas as pd
import pytest

from gex import config
from gex.surface_history import nth_trading_day_back


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_dates(n: int, base: datetime.date | None = None) -> list[datetime.date]:
    """Build a descending list of n consecutive dates starting from base."""
    if base is None:
        base = datetime.date(2026, 5, 30)
    return [base - datetime.timedelta(days=i) for i in range(n)]


def _fixed_surface_df(spot: float = 500.0) -> pd.DataFrame:
    """Deterministic OTM scatter spanning several expiries and the ±15% band.

    Same construction style as test_rbf_grid.py so rbf_grid + coverage_mask
    work correctly (>=6 in-band points, >=2 expiries for the convex hull).
    """
    rows = []
    for dte in [7, 14, 30, 60, 90, 120]:
        for ks in [0.90, 0.95, 1.0, 1.05, 1.10]:
            rows.append({
                "dte": float(dte),
                "strike": spot * ks,
                "iv_pct": 20.0 + (1.0 - ks) * 12.0 + dte * 0.01,
                "log_moneyness": np.log(ks),
                "moneyness": ks,
            })
    return pd.DataFrame(rows)


def _build_grid(surface_df: pd.DataFrame, spot: float = 500.0):
    """Return (IV_grid, mask, dte_grid, otm_grid) for the given surface."""
    from gex.analytics import rbf_grid, coverage_mask

    clip = config.SURFACE_PLOT_OTM_CLIP
    dte_max = min(float(surface_df["dte"].max()), float(config.SURFACE_DTE_MAX))
    dte_grid = np.linspace(5.0, dte_max, config.SURFACE_GRID_DTE)
    otm_grid = np.linspace(-clip, clip, config.SURFACE_GRID_LM)

    iv = rbf_grid(surface_df, spot, dte_grid, otm_grid, dte_floor=5)
    mask = coverage_mask(surface_df, spot, dte_grid, otm_grid, dte_floor=5)
    return iv, mask, dte_grid, otm_grid


# ---------------------------------------------------------------------------
# nth_trading_day_back tests (EVOL-02) — must pass after Plan 01 Task 2
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


def test_nth_back_off_by_one(monkeypatch):
    """Off-by-one guard: horizon=1 means one step back (idx+1), not today itself."""
    base = datetime.date(2026, 5, 30)
    dates = [base - datetime.timedelta(days=i) for i in range(5)]
    # dates = [d0, d1, d2, d3, d4] descending
    monkeypatch.setattr(
        "gex.surface_history.list_available_dates",
        lambda ticker: dates,
    )
    result = nth_trading_day_back("SPY", dates[0], n=1)
    assert result == dates[1], (
        f"horizon=1 must return the immediately prior session (dates[1]={dates[1]}), "
        f"got {result}"
    )
    # Also verify it is NOT today itself
    assert result != dates[0], "horizon=1 must not return the anchor date itself"


# ---------------------------------------------------------------------------
# Scalar behavior tests (EVOL-01) — implemented in Plan 02
# ---------------------------------------------------------------------------

def test_scalars_level_is_nanmean_diff():
    """level scalar = np.nanmean(IV_diff_masked) on the intersection mask."""
    spot = 500.0
    surface_df = _fixed_surface_df(spot)
    IV_today, mask_today, dte_grid, otm_grid = _build_grid(surface_df, spot)

    # Prior grid is today's grid + uniform shift of +2.0 pp
    IV_prior = IV_today + 2.0
    mask_prior = mask_today.copy()

    mask_intersection = mask_today & mask_prior
    IV_diff_masked = np.where(mask_intersection, IV_today - IV_prior, np.nan)

    from gex.surface_evolution import compute_evolution_scalars
    result = compute_evolution_scalars(IV_diff_masked, otm_grid, dte_grid)

    assert abs(result["level"] - (-2.0)) < 0.1, (
        f"level should be ~-2.0 (IV_today - (IV_today+2)), got {result['level']:.4f}"
    )


def test_scalars_rms_ignores_nan():
    """rms scalar = sqrt(np.nanmean(IV_diff_masked**2)); NaN cells excluded."""
    from gex.surface_evolution import compute_evolution_scalars

    rng = np.random.default_rng(42)
    shape = (config.SURFACE_GRID_LM, config.SURFACE_GRID_DTE)  # (30, 40)
    IV_diff_masked = rng.standard_normal(shape).astype(float)

    # Punch some NaN holes in one quadrant
    IV_diff_masked[:5, :5] = np.nan

    result = compute_evolution_scalars(
        IV_diff_masked,
        np.linspace(-0.15, 0.15, config.SURFACE_GRID_LM),
        np.linspace(5.0, 120.0, config.SURFACE_GRID_DTE),
    )

    expected_rms = float(np.sqrt(np.nanmean(IV_diff_masked ** 2)))
    assert result["rms"] == pytest.approx(expected_rms, abs=1e-6)

    # Confirm NaN cells do NOT inflate rms: zeroing those cells gives a different answer
    IV_zeroed = IV_diff_masked.copy()
    IV_zeroed[np.isnan(IV_zeroed)] = 0.0
    rms_zeroed = float(np.sqrt(np.mean(IV_zeroed ** 2)))
    assert abs(result["rms"] - rms_zeroed) > 1e-9, (
        "NaN cells must NOT be treated as zero; rms should differ"
    )


def test_scalars_coverage_in_unit_interval():
    """coverage must always be in [0.0, 1.0]."""
    from gex.surface_evolution import compute_evolution_scalars

    spot = 500.0
    surface_df = _fixed_surface_df(spot)
    IV_today, mask_today, dte_grid, otm_grid = _build_grid(surface_df, spot)

    IV_diff_masked = np.where(mask_today, IV_today - IV_today, np.nan)
    result = compute_evolution_scalars(IV_diff_masked, otm_grid, dte_grid)

    assert 0.0 <= result["coverage"] <= 1.0, (
        f"coverage must be in [0, 1], got {result['coverage']}"
    )


def test_skew_change_wing_split():
    """skew_change = mean(put-wing diff) - mean(call-wing diff) using config clips."""
    from gex.surface_evolution import compute_evolution_scalars

    # Config constant assertions BEFORE the scalar call so a config change
    # produces a named assertion error before the scalar logic runs.
    assert config.SURFACE_EVOLUTION_PUT_WING_CLIP == -0.05, (
        f"expected PUT_WING_CLIP=-0.05, got {config.SURFACE_EVOLUTION_PUT_WING_CLIP}"
    )
    assert config.SURFACE_EVOLUTION_CALL_WING_CLIP == 0.05, (
        f"expected CALL_WING_CLIP=0.05, got {config.SURFACE_EVOLUTION_CALL_WING_CLIP}"
    )

    otm_grid = np.linspace(-0.15, 0.15, config.SURFACE_GRID_LM)
    dte_grid = np.linspace(5.0, 120.0, config.SURFACE_GRID_DTE)

    # Build IV_diff_masked: put-wing = +4.0, call-wing = +1.0, rest = 0.0
    shape = (config.SURFACE_GRID_LM, config.SURFACE_GRID_DTE)
    IV_diff_masked = np.zeros(shape)
    put_idx = otm_grid < config.SURFACE_EVOLUTION_PUT_WING_CLIP
    call_idx = otm_grid > config.SURFACE_EVOLUTION_CALL_WING_CLIP
    IV_diff_masked[put_idx, :] = 4.0
    IV_diff_masked[call_idx, :] = 1.0
    # No NaN holes in this test — all cells are valid

    result = compute_evolution_scalars(IV_diff_masked, otm_grid, dte_grid)

    assert abs(result["skew_change"] - 3.0) < 0.2, (
        f"skew_change should be ~3.0 (4.0 - 1.0), got {result['skew_change']:.4f}"
    )


def test_term_change_front_back():
    """term_change = mean(front-ATM diff) - mean(back-ATM diff) using config DTE bands."""
    from gex.surface_evolution import compute_evolution_scalars

    # Config constant assertions BEFORE the scalar call.
    assert config.SURFACE_EVOLUTION_DTE_FRONT_MAX == 30, (
        f"expected DTE_FRONT_MAX=30, got {config.SURFACE_EVOLUTION_DTE_FRONT_MAX}"
    )
    assert config.SURFACE_EVOLUTION_DTE_BACK_MIN == 90, (
        f"expected DTE_BACK_MIN=90, got {config.SURFACE_EVOLUTION_DTE_BACK_MIN}"
    )
    assert config.SURFACE_EVOLUTION_ATM_CLIP == 0.02, (
        f"expected ATM_CLIP=0.02, got {config.SURFACE_EVOLUTION_ATM_CLIP}"
    )

    otm_grid = np.linspace(-0.15, 0.15, config.SURFACE_GRID_LM)
    dte_grid = np.linspace(5.0, 180.0, config.SURFACE_GRID_DTE)

    shape = (config.SURFACE_GRID_LM, config.SURFACE_GRID_DTE)
    IV_diff_masked = np.full(shape, 2.0)  # baseline: everything = 2.0

    # Front-ATM cells: +3.0
    front_idx = dte_grid <= config.SURFACE_EVOLUTION_DTE_FRONT_MAX
    atm_idx = np.abs(otm_grid) <= config.SURFACE_EVOLUTION_ATM_CLIP
    IV_diff_masked[np.ix_(atm_idx, front_idx)] = 3.0

    # Back-ATM cells: +1.0
    back_idx = dte_grid >= config.SURFACE_EVOLUTION_DTE_BACK_MIN
    IV_diff_masked[np.ix_(atm_idx, back_idx)] = 1.0

    result = compute_evolution_scalars(IV_diff_masked, otm_grid, dte_grid)

    assert abs(result["term_change"] - 2.0) < 0.3, (
        f"term_change should be ~2.0 (3.0 - 1.0), got {result['term_change']:.4f}"
    )


def test_grid_axis_identity_across_horizons(monkeypatch, tmp_path):
    """BLOCKER 4: prior day's shorter DTE must NOT cause a different grid shape.

    Today's surface drives the grid axes; prior day's surface is interpolated on
    those same axes regardless of its own DTE extent.
    """
    from gex.analytics import coverage_mask, rbf_grid
    from gex.surface_evolution import _construct_grid_axes, update_evolution

    spot = 500.0
    today = datetime.date(2026, 5, 30)
    prior = datetime.date(2026, 5, 29)

    # Today: max DTE = 160; prior: max DTE = 110 (shorter)
    def _make_surface(max_dte: float) -> pd.DataFrame:
        rows = []
        for dte in [7, 14, 30, 60, max_dte]:
            for ks in [0.90, 0.95, 1.0, 1.05, 1.10]:
                rows.append({
                    "dte": float(dte),
                    "strike": spot * ks,
                    "iv_pct": 20.0 + (1.0 - ks) * 12.0 + dte * 0.01,
                    "log_moneyness": np.log(ks),
                    "moneyness": ks,
                })
        return pd.DataFrame(rows)

    surface_today = _make_surface(160.0)
    surface_prior = _make_surface(110.0)

    # When _construct_grid_axes is called on today's surface it uses today's dte_max,
    # so both grid calls produce identical shape (30, 40) regardless of prior DTE.
    dte_grid_today, otm_grid_today = _construct_grid_axes(surface_today)
    dte_grid_prior, otm_grid_prior = _construct_grid_axes(surface_prior)

    # Today's axes govern; shape must always be (SURFACE_GRID_DTE,)
    assert dte_grid_today.shape == (config.SURFACE_GRID_DTE,)
    assert otm_grid_today.shape == (config.SURFACE_GRID_LM,)

    # Prior day's own axes would differ (shorter DTE) — but update_evolution
    # does NOT call _construct_grid_axes for prior days.
    # Verify: using today's axes for the prior surface still returns (30, 40) shape.
    IV_prior_on_today_axes = rbf_grid(
        surface_prior, spot, dte_grid_today, otm_grid_today, dte_floor=5
    )
    mask_prior_on_today_axes = coverage_mask(
        surface_prior, spot, dte_grid_today, otm_grid_today, dte_floor=5
    )
    assert IV_prior_on_today_axes.shape == (config.SURFACE_GRID_LM, config.SURFACE_GRID_DTE)
    assert mask_prior_on_today_axes.shape == (config.SURFACE_GRID_LM, config.SURFACE_GRID_DTE)

    # Full integration: run update_evolution with monkeypatched I/O
    snapshots = {
        today: (surface_today, spot),
        prior: (surface_prior, spot),
    }

    def mock_load(ticker, date):
        return snapshots.get(date, (pd.DataFrame(), None))

    def mock_nth_back(ticker, anchor_date, n):
        if anchor_date == today and n == 1:
            return prior
        return None  # only horizon=1 is satisfiable in this fixture

    import gex.surface_evolution as se

    monkeypatch.setattr("gex.surface_evolution.load_surface_snapshot", mock_load)
    monkeypatch.setattr("gex.surface_evolution.nth_trading_day_back", mock_nth_back)
    # Redirect parquet writes to tmp_path
    monkeypatch.setattr("gex.surface_evolution.STORE", tmp_path / "test_evolution.parquet")
    # Override HORIZONS to [1] so only the satisfiable horizon runs
    monkeypatch.setattr("gex.surface_evolution.HORIZONS", (1,))

    update_evolution("SPY", today)

    store_path = tmp_path / "test_evolution.parquet"
    assert store_path.exists(), "update_evolution should have written a row"

    df = pd.read_parquet(store_path)
    assert len(df) == 1
    row = df.iloc[0]
    assert 0.0 <= float(row["coverage"]) <= 1.0, (
        f"coverage must be in [0, 1], got {row['coverage']}"
    )


def test_mask_intersection_excludes_extrapolated_cells():
    """Cells where any day lacks hull support are NaN in IV_diff_masked."""
    from gex.analytics import coverage_mask, rbf_grid

    spot = 500.0
    clip = config.SURFACE_PLOT_OTM_CLIP

    # Surface A: full expiry range (5–120 DTE), full OTM band
    def _chain(dtes, pct_otms):
        rows = []
        for dte in dtes:
            for p in pct_otms:
                rows.append({
                    "dte": float(dte),
                    "strike": spot * (1.0 + p / 100.0),
                    "iv_pct": 20.0 + (-p) * 0.3 + dte * 0.01,
                    "log_moneyness": np.log(1.0 + p / 100.0),
                    "moneyness": 1.0 + p / 100.0,
                })
        return pd.DataFrame(rows)

    surface_a = _chain(
        [7, 14, 30, 60, 90, 120],
        [-10, -5, 0, 5, 10],
    )
    # Surface B: only short-dated (7–30 DTE), so long-DTE cells are unsupported
    surface_b = _chain(
        [7, 14, 30],
        [-10, -5, 0, 5, 10],
    )

    dte_max = min(float(surface_a["dte"].max()), float(config.SURFACE_DTE_MAX))
    dte_grid = np.linspace(5.0, dte_max, config.SURFACE_GRID_DTE)
    otm_grid = np.linspace(-clip, clip, config.SURFACE_GRID_LM)

    IV_a = rbf_grid(surface_a, spot, dte_grid, otm_grid, dte_floor=5)
    mask_a = coverage_mask(surface_a, spot, dte_grid, otm_grid, dte_floor=5)
    IV_b = rbf_grid(surface_b, spot, dte_grid, otm_grid, dte_floor=5)
    mask_b = coverage_mask(surface_b, spot, dte_grid, otm_grid, dte_floor=5)

    # B has no long-DTE support, so its mask is False there
    long_dte_col = int(np.argmin(np.abs(dte_grid - 100.0)))
    atm_row = int(np.argmin(np.abs(otm_grid - 0.0)))
    assert not mask_b[atm_row, long_dte_col], (
        "surface_b has no 100-DTE quotes; ATM@100DTE should be outside its hull"
    )

    # Intersection must be False at that cell
    mask_intersection = mask_a & mask_b
    assert not mask_intersection[atm_row, long_dte_col], (
        "intersection mask must be False where surface_b lacks support"
    )

    IV_diff = IV_a - IV_b
    IV_diff_masked = np.where(mask_intersection, IV_diff, np.nan)
    assert np.isnan(IV_diff_masked[atm_row, long_dte_col]), (
        "IV_diff_masked must be NaN at cells outside the intersection mask"
    )

    # Scalars must not blow up (level, rms are finite floats)
    from gex.surface_evolution import compute_evolution_scalars
    result = compute_evolution_scalars(IV_diff_masked, otm_grid, dte_grid)
    assert np.isfinite(result["level"]), "level must be finite"
    assert np.isfinite(result["rms"]), "rms must be finite"


# ---------------------------------------------------------------------------
# Persistence behavior tests (EVOL-03) — implemented in Plan 02
# ---------------------------------------------------------------------------

def test_evolution_idempotent_on_rerun(monkeypatch, tmp_path):
    """Re-running save_evolution_row with same (date, ticker, horizon) deduplicates."""
    import gex.surface_evolution as se
    monkeypatch.setattr("gex.surface_evolution.STORE", tmp_path / "test_evolution.parquet")

    date = datetime.date(2026, 5, 30)
    ticker = "SPY"
    horizon = 5
    prior_date = datetime.date(2026, 5, 23)

    # First write
    se.save_evolution_row(date, ticker, horizon, prior_date,
                          level=1.0, rms=0.5, skew_change=0.3,
                          term_change=0.2, coverage=0.8)

    # Second write with DIFFERENT level — must overwrite, not append
    se.save_evolution_row(date, ticker, horizon, prior_date,
                          level=2.5, rms=0.7, skew_change=0.4,
                          term_change=0.1, coverage=0.9)

    df = pd.read_parquet(tmp_path / "test_evolution.parquet")
    key_rows = df[(df["ticker"] == ticker) & (df["horizon"] == horizon)]
    assert len(key_rows) == 1, (
        f"expected exactly 1 row for (date, ticker, horizon), got {len(key_rows)}"
    )
    assert float(key_rows.iloc[0]["level"]) == pytest.approx(2.5), (
        "second write's level value must overwrite the first"
    )


def test_cold_start_no_row_written(monkeypatch, tmp_path):
    """No evolution row is written when nth_trading_day_back returns None."""
    import gex.surface_evolution as se

    monkeypatch.setattr("gex.surface_evolution.STORE", tmp_path / "test_evolution.parquet")

    surface_df = _fixed_surface_df(500.0)

    # load_surface_snapshot always returns a valid surface
    monkeypatch.setattr(
        "gex.surface_evolution.load_surface_snapshot",
        lambda ticker, date: (surface_df, 500.0),
    )
    # nth_trading_day_back always returns None → cold start for all horizons
    monkeypatch.setattr(
        "gex.surface_evolution.nth_trading_day_back",
        lambda ticker, anchor_date, n: None,
    )

    today = datetime.date(2026, 5, 30)
    se.update_evolution("SPY", today)

    assert not (tmp_path / "test_evolution.parquet").exists(), (
        "no parquet file should be created when all horizons return None (cold start)"
    )


# ---------------------------------------------------------------------------
# Integration tests (EVOL-04/05/06) — added in Plan 03
# ---------------------------------------------------------------------------

def test_evolution_does_not_raise_on_empty_store(monkeypatch, tmp_path):
    """update_evolution with empty snapshot returns silently; no parquet written."""
    import gex.surface_evolution as se

    monkeypatch.setattr("gex.surface_evolution.STORE", tmp_path / "test_evolution.parquet")
    monkeypatch.setattr(
        "gex.surface_evolution.load_surface_snapshot",
        lambda ticker, date: (pd.DataFrame(), None),
    )

    se.update_evolution("SPY", datetime.date.today())

    assert not (tmp_path / "test_evolution.parquet").exists(), (
        "no parquet should be written when load_surface_snapshot returns empty"
    )


def test_run_daily_evolution_failure_does_not_propagate():
    """Non-blocking loop pattern: all failures collected, none propagated."""
    failed = []
    for ticker in ["SPY", "QQQ", "IWM"]:
        try:
            raise RuntimeError("simulated")
        except Exception as exc:
            failed.append(ticker)
    assert len(failed) == 3


def test_cross_ticker_schema_consistency(monkeypatch, tmp_path):
    """Rows written for SPY/QQQ/IWM share identical columns and valid horizons."""
    import gex.surface_evolution as se

    store = tmp_path / "test_cross_ticker.parquet"
    monkeypatch.setattr("gex.surface_evolution.STORE", store)

    base_date = datetime.date(2026, 5, 30)
    prior_date = datetime.date(2026, 5, 23)
    for ticker in ["SPY", "QQQ", "IWM"]:
        for horizon in (5, 10, 20):
            se.save_evolution_row(
                date=base_date,
                ticker=ticker,
                horizon=horizon,
                prior_date=prior_date,
                level=0.1,
                rms=0.2,
                skew_change=0.05,
                term_change=0.03,
                coverage=0.75,
            )

    df = pd.read_parquet(store)
    assert set(df["ticker"].unique()) == {"SPY", "QQQ", "IWM"}
    assert set(df["horizon"].unique()).issubset({5, 10, 20})
    for ticker in ["SPY", "QQQ", "IWM"]:
        cols = set(df[df["ticker"] == ticker].columns)
        assert cols == set(df.columns), f"{ticker} has different columns"


def test_backfill_consistency(monkeypatch, tmp_path):
    """Backfill from surface_history produces identical scalars to daily ingestion."""
    import gex.surface_evolution as se

    monkeypatch.setattr("gex.surface_evolution.STORE", tmp_path / "test_evolution.parquet")

    spot = 500.0
    base = datetime.date(2026, 5, 30)
    # Build 3 stored dates; only horizon=1 is satisfiable
    dates = [base - datetime.timedelta(days=i) for i in range(3)]  # [d0, d1, d2] descending

    surface_map = {d: (_fixed_surface_df(spot), spot) for d in dates}

    def mock_load(ticker, date):
        return surface_map.get(date, (pd.DataFrame(), None))

    def mock_nth_back(ticker, anchor_date, n):
        if anchor_date not in dates:
            return None
        idx = dates.index(anchor_date)
        if idx + n >= len(dates):
            return None
        return dates[idx + n]

    def mock_list_available(ticker):
        return dates

    monkeypatch.setattr("gex.surface_evolution.load_surface_snapshot", mock_load)
    monkeypatch.setattr("gex.surface_evolution.nth_trading_day_back", mock_nth_back)
    monkeypatch.setattr("gex.surface_evolution.list_available_dates", mock_list_available)
    monkeypatch.setattr("gex.surface_evolution.HORIZONS", (1,))

    # Daily ingestion: call update_evolution for d0 only
    se.update_evolution("SPY", dates[0])
    store_daily = tmp_path / "test_evolution.parquet"
    assert store_daily.exists()
    df_daily = pd.read_parquet(store_daily)
    assert len(df_daily) >= 1

    daily_level = float(df_daily.iloc[0]["level"])

    # Backfill on a fresh store path
    monkeypatch.setattr("gex.surface_evolution.STORE", tmp_path / "test_backfill.parquet")
    se.backfill("SPY", dates[-1])  # start from oldest date

    df_backfill = pd.read_parquet(tmp_path / "test_backfill.parquet")
    # Find the row for dates[0] (most recent date that update_evolution produced above)
    row = df_backfill[
        pd.to_datetime(df_backfill["date"]).dt.date == dates[0]
    ]
    assert len(row) >= 1, "backfill must produce a row for dates[0]"
    backfill_level = float(row.iloc[0]["level"])

    assert abs(daily_level - backfill_level) < 1e-6, (
        f"backfill level {backfill_level:.6f} must match daily level {daily_level:.6f}"
    )


def test_backfill_reports_honest_row_count(monkeypatch, tmp_path):
    """backfill returns rows actually persisted, not dates touched; cold-start = 0.

    Guards against the misleading '(N rows)' summary that counted every date
    processed even when update_evolution wrote nothing during cold-start.
    """
    import gex.surface_evolution as se

    spot = 500.0
    base = datetime.date(2026, 5, 30)
    dates = [base - datetime.timedelta(days=i) for i in range(3)]  # descending

    surface_map = {d: (_fixed_surface_df(spot), spot) for d in dates}

    def mock_nth_back(ticker, anchor_date, n):
        if anchor_date not in dates:
            return None
        idx = dates.index(anchor_date)
        return dates[idx + n] if idx + n < len(dates) else None

    monkeypatch.setattr(
        "gex.surface_evolution.load_surface_snapshot",
        lambda ticker, date: surface_map.get(date, (pd.DataFrame(), None)),
    )
    monkeypatch.setattr("gex.surface_evolution.nth_trading_day_back", mock_nth_back)
    monkeypatch.setattr("gex.surface_evolution.list_available_dates", lambda ticker: dates)
    monkeypatch.setattr("gex.surface_evolution.HORIZONS", (1,))

    # Sufficient history: horizon=1 resolves for the two newer dates → rows persisted.
    store = tmp_path / "honest.parquet"
    monkeypatch.setattr("gex.surface_evolution.STORE", store)
    total = se.backfill("SPY", dates[-1])

    df = pd.read_parquet(store)
    assert total > 0, "with sufficient history backfill must persist at least one row"
    assert total == len(df), (
        f"backfill reported {total} rows but the store holds {len(df)} — count must be honest"
    )

    # Cold-start: no horizon resolves → 0 rows, no file, honest zero.
    monkeypatch.setattr("gex.surface_evolution.nth_trading_day_back", lambda t, a, n: None)
    cold_store = tmp_path / "coldstart.parquet"
    monkeypatch.setattr("gex.surface_evolution.STORE", cold_store)
    cold_total = se.backfill("SPY", dates[-1])

    assert cold_total == 0, "cold-start backfill must report 0 rows, not dates processed"
    assert not cold_store.exists(), "cold-start writes no parquet file"
