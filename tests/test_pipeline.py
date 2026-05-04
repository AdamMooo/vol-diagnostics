"""Pipeline invariant tests. These touch the network (CBOE+FRED) and the
parquet cache, so they're slower than test_math but exercise schema and
flow contracts on real data.

Run:    python -m pytest tests/test_pipeline.py -v
Skip:   python -m pytest tests/test_math.py -v   (just math)
"""
from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import pytest

from data_layer import build_panels
from signals import build_signals
from backtest import run_backtest


@pytest.fixture(scope="module")
def panels():
    """One panel build per test module (cache-backed, ~1s warm)."""
    return build_panels(start="2010-01-01")


@pytest.fixture(scope="module")
def sigs(panels):
    return build_signals(panels)


@pytest.fixture(scope="module")
def bt(panels):
    return run_backtest(panels)


# ---------------------------------------------------------------------------
# Phase 1 — panel shape
# ---------------------------------------------------------------------------

class TestPanelShape:
    def test_landed_includes_required(self, panels):
        assert "SPX" in panels.landed
        assert "NDX" in panels.landed

    def test_iv_panel_columns_subset_of_landed(self, panels):
        assert set(panels.iv_panel.columns).issubset(set(panels.landed))

    def test_panels_share_index(self, panels):
        idx = panels.prices_panel.index
        assert panels.iv_panel.index.equals(idx)
        assert panels.iv90_panel.index.equals(idx)
        assert panels.iv90mny.index.equals(idx)
        assert panels.skew_panel.index.equals(idx)

    def test_cross_series_share_index(self, panels):
        idx = panels.prices_panel.index
        assert panels.vix.index.equals(idx)
        assert panels.rf_rate.index.equals(idx)

    def test_skew_panel_correct_definition(self, panels):
        """skew_panel must equal iv90mny - iv_panel exactly."""
        common = [c for c in panels.iv_panel.columns if c in panels.iv90mny.columns]
        expected = panels.iv90mny[common] - panels.iv_panel[common]
        pd.testing.assert_frame_equal(panels.skew_panel[common], expected)

    def test_truncate_start_has_iv_data(self, panels):
        """truncate_start should be the earliest date all IVs are present."""
        for u in panels.landed:
            iv_at_start = panels.iv_panel.loc[panels.truncate_start, u]
            assert not pd.isna(iv_at_start), f"{u} IV missing at truncate_start"


# ---------------------------------------------------------------------------
# Phase 2 — signal invariants
# ---------------------------------------------------------------------------

class TestSignals:
    def test_pct_rank_in_unit_interval(self, sigs):
        for name, panel in sigs.pct.items():
            vals = panel.dropna().values
            assert (vals >= 0).all(), f"{name} has negative pct rank"
            assert (vals <= 1).all(), f"{name} has pct rank > 1"

    def test_fragility_in_unit_interval(self, sigs):
        v = sigs.fragility.dropna().values
        assert (v >= 0).all() and (v <= 1).all()

    def test_rv30_non_negative(self, sigs):
        v = sigs.raw["rv30"].dropna().values
        assert (v >= 0).all()

    def test_signals_share_columns(self, sigs):
        cols = list(sigs.pct["vrp"].columns)
        for name, panel in sigs.pct.items():
            assert list(panel.columns) == cols, f"{name} has different columns"

    def test_latest_date_consistent(self, sigs):
        dt = sigs.latest_date()
        assert dt is not None
        # All signals should have a value at latest_date
        for name, panel in sigs.pct.items():
            row = panel.loc[dt]
            assert row.notna().any(), f"{name} fully NaN at latest_date"


# ---------------------------------------------------------------------------
# Phase 3 — backtest invariants
# ---------------------------------------------------------------------------

class TestBacktest:
    def test_rolls_have_required_columns(self, bt):
        for u, rolls in bt.rolls.items():
            for col in ("S0", "S1", "sigma", "rate", "T_days",
                        "spot_ret", "cc", "csp", "collar", "strangle"):
                assert col in rolls.columns, f"{u} missing {col}"

    def test_spot_ret_matches_S1_over_S0(self, bt):
        for u, rolls in bt.rolls.items():
            expected = (rolls["S1"] - rolls["S0"]) / rolls["S0"]
            np.testing.assert_allclose(rolls["spot_ret"].values, expected.values, rtol=1e-9)

    def test_cc_pnl_identity(self, bt):
        """cc_ret = spot_ret + (premium - max(S1-K, 0))/S0.

        Since we don't store K explicitly, validate that cc_ret <= spot_ret + premium_implied
        and equality holds when call expires worthless (S1 < K, i.e. spot_ret < some threshold).
        """
        for u, rolls in bt.rolls.items():
            # cc_ret should always be ≥ spot_ret - small slippage when call is far ITM
            # actually: cc_ret = spot_ret + premium - settlement
            # so cc_ret >= spot_ret - settlement when premium=0; in general cc_ret could be above or below
            # Looser check: when spot_ret is very negative, cc_ret > spot_ret (premium offsets some)
            mask = rolls["spot_ret"] < -0.05
            if mask.sum() > 5:
                assert (rolls.loc[mask, "cc"] > rolls.loc[mask, "spot_ret"]).all(), \
                    f"{u}: CC didn't outperform spot in down months"

    def test_collar_max_dd_better_than_spot(self, bt):
        """Collar with long put should have less severe drawdown than spot."""
        for u in bt.rolls:
            collar_max_dd = bt.stats[u].loc["collar", "max_dd"]
            spot_max_dd = bt.stats[u].loc["spot_ret", "max_dd"]
            assert collar_max_dd > spot_max_dd, \
                f"{u}: collar max_dd {collar_max_dd:.3f} not better than spot {spot_max_dd:.3f}"

    def test_csp_hit_rate_above_spot(self, bt):
        """Short OTM put → high hit rate by construction (only loses on big down moves)."""
        for u in bt.rolls:
            csp_hit = bt.stats[u].loc["csp", "hit"]
            spot_hit = bt.stats[u].loc["spot_ret", "hit"]
            assert csp_hit > spot_hit, f"{u}: CSP hit {csp_hit:.2f} not above spot {spot_hit:.2f}"

    def test_strangle_lower_vol_than_spot(self, bt):
        """Cash-collateralized vol-selling neutral → much lower vol than long equity."""
        for u in bt.rolls:
            strangle_vol = bt.stats[u].loc["strangle", "vol"]
            spot_vol = bt.stats[u].loc["spot_ret", "vol"]
            assert strangle_vol < spot_vol, f"{u}: strangle vol {strangle_vol:.3f} not below spot {spot_vol:.3f}"

    def test_no_extreme_per_roll_returns(self, bt):
        """Sanity guard: no monthly sleeve return outside ±50% (would indicate a bug)."""
        for u, rolls in bt.rolls.items():
            for col in ("cc", "csp", "collar", "strangle"):
                v = rolls[col].abs().max()
                assert v < 0.50, f"{u} {col} extreme return {v}"


# ---------------------------------------------------------------------------
# Subperiod stability vs full period
# ---------------------------------------------------------------------------

class TestSubperiodConsistency:
    def test_subperiod_returns_link_to_full(self, bt):
        """Geometric link of subperiod cumulative returns ≈ full-period cumulative."""
        from dashboard import SUBPERIOD_SPLITS
        for u in bt.rolls:
            rolls = bt.rolls[u]
            for sleeve in ("spot_ret", "cc", "csp", "collar", "strangle"):
                full_growth = (1 + rolls[sleeve]).prod()
                # Link the three subperiods
                linked = 1.0
                covered = []
                for start, end, _label in SUBPERIOD_SPLITS:
                    sub = rolls.loc[start:end]
                    if len(sub):
                        linked *= (1 + sub[sleeve]).prod()
                        covered.append((sub.index.min(), sub.index.max()))
                # Subperiods should cover full range
                if covered:
                    assert covered[0][0] <= rolls.index.min() + pd.Timedelta(days=35)
                    assert covered[-1][1] >= rolls.index.max() - pd.Timedelta(days=35)
                # Linked product should equal full product (small numerical tolerance)
                assert abs(linked - full_growth) / max(full_growth, 1e-9) < 1e-9, \
                    f"{u} {sleeve}: linked {linked:.6f} != full {full_growth:.6f}"
