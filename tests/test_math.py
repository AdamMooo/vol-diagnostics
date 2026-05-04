"""Math correctness tests. Run: python -m pytest tests/

These exercise the core math without touching network/data sources.
If any of these fail, downstream backtest/dashboard numbers can't be
trusted.
"""
from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm

from backtest import (
    bs_price,
    bs_strike_from_delta,
    iv_at_strike,
    third_fridays,
)
from signals import causal_pct_rank


# ---------------------------------------------------------------------------
# Black-Scholes reference values
# ---------------------------------------------------------------------------

class TestBlackScholes:
    """Reference values from Hull, Options Futures and Other Derivatives, 9th ed."""

    def test_hull_call_4_4(self):
        # Example 14.6: S=42, K=40, r=10%, σ=20%, T=0.5y → c = 4.759
        c = bs_price(S=42, K=40, T=0.5, r=0.10, sigma=0.20, kind="call")
        assert abs(c - 4.759) < 0.01, f"got {c}"

    def test_hull_put_4_4(self):
        # Same params → p = 0.808
        p = bs_price(S=42, K=40, T=0.5, r=0.10, sigma=0.20, kind="put")
        assert abs(p - 0.808) < 0.01, f"got {p}"

    def test_put_call_parity(self):
        # C - P = S*exp(-qT) - K*exp(-rT)
        S, K, T, r, sigma, q = 100, 100, 1.0, 0.05, 0.25, 0.0
        c = bs_price(S, K, T, r, sigma, q=q, kind="call")
        p = bs_price(S, K, T, r, sigma, q=q, kind="put")
        lhs = c - p
        rhs = S * np.exp(-q * T) - K * np.exp(-r * T)
        assert abs(lhs - rhs) < 1e-6, f"parity violated: {lhs} vs {rhs}"

    def test_zero_time_call_intrinsic(self):
        assert bs_price(S=110, K=100, T=0, r=0.05, sigma=0.20, kind="call") == 10.0

    def test_zero_time_put_intrinsic(self):
        assert bs_price(S=90, K=100, T=0, r=0.05, sigma=0.20, kind="put") == 10.0

    def test_atm_call_above_zero(self):
        c = bs_price(S=100, K=100, T=0.25, r=0.04, sigma=0.20, kind="call")
        assert c > 0


# ---------------------------------------------------------------------------
# Strike-from-delta round trip
# ---------------------------------------------------------------------------

class TestStrikeFromDelta:
    """If we ask for strike at target delta, the resulting strike should
    have ~that delta when we recompute it via finite-difference."""

    def _delta_finite_diff(self, S, K, T, r, sigma, kind):
        h = 0.01 * S
        up = bs_price(S + h, K, T, r, sigma, kind=kind)
        dn = bs_price(S - h, K, T, r, sigma, kind=kind)
        return (up - dn) / (2 * h)

    @pytest.mark.parametrize("target", [0.10, 0.25, 0.40])
    def test_call_round_trip(self, target):
        S, T, r, sigma = 100, 30/365, 0.04, 0.20
        K = bs_strike_from_delta(S, T, r, sigma, target, kind="call")
        recovered = self._delta_finite_diff(S, K, T, r, sigma, "call")
        assert abs(recovered - target) < 0.005, f"target {target} got {recovered}"

    @pytest.mark.parametrize("target", [-0.10, -0.25, -0.40])
    def test_put_round_trip(self, target):
        S, T, r, sigma = 100, 30/365, 0.04, 0.20
        K = bs_strike_from_delta(S, T, r, sigma, target, kind="put")
        recovered = self._delta_finite_diff(S, K, T, r, sigma, "put")
        assert abs(recovered - target) < 0.005, f"target {target} got {recovered}"

    def test_25d_call_above_spot(self):
        """OTM call → strike above spot."""
        S, T, r, sigma = 100, 30/365, 0.04, 0.20
        K = bs_strike_from_delta(S, T, r, sigma, 0.25, kind="call")
        assert K > S

    def test_25d_put_below_spot(self):
        """OTM put → strike below spot."""
        S, T, r, sigma = 100, 30/365, 0.04, 0.20
        K = bs_strike_from_delta(S, T, r, sigma, -0.25, kind="put")
        assert K < S


# ---------------------------------------------------------------------------
# Skew interpolation
# ---------------------------------------------------------------------------

class TestSkewInterp:
    def test_atm_returns_atm(self):
        # m = 1.0 → ATM IV
        iv = iv_at_strike(S=100, K=100, iv_atm_pts=15.0, iv_90mny_pts=20.0)
        assert abs(iv - 0.15) < 1e-9

    def test_90mny_returns_90mny(self):
        # m = 0.9 → 90mny IV
        iv = iv_at_strike(S=100, K=90, iv_atm_pts=15.0, iv_90mny_pts=20.0)
        assert abs(iv - 0.20) < 1e-9

    def test_below_90mny_capped(self):
        iv = iv_at_strike(S=100, K=80, iv_atm_pts=15.0, iv_90mny_pts=20.0)
        assert abs(iv - 0.20) < 1e-9

    def test_upside_flat_at_atm(self):
        iv = iv_at_strike(S=100, K=110, iv_atm_pts=15.0, iv_90mny_pts=20.0)
        assert abs(iv - 0.15) < 1e-9

    def test_linear_midpoint(self):
        # m = 0.95 → halfway between ATM and 90mny
        iv = iv_at_strike(S=100, K=95, iv_atm_pts=15.0, iv_90mny_pts=25.0)
        assert abs(iv - 0.20) < 1e-9

    def test_nan_90mny_falls_back_to_atm(self):
        iv = iv_at_strike(S=100, K=95, iv_atm_pts=15.0, iv_90mny_pts=float("nan"))
        assert abs(iv - 0.15) < 1e-9


# ---------------------------------------------------------------------------
# Realized vol recovers true vol on synthetic GBM
# ---------------------------------------------------------------------------

class TestRealizedVol:
    def test_recover_synthetic_vol(self):
        np.random.seed(42)
        n = 5_000  # ~20 years of daily
        true_vol = 0.20
        dt = 1 / 252
        # GBM log returns: N(-0.5σ²dt, σ√dt)
        log_ret = np.random.normal(loc=-0.5 * true_vol**2 * dt, scale=true_vol * np.sqrt(dt), size=n)
        s = pd.Series(log_ret)
        rv30 = s.rolling(21).std() * np.sqrt(252)
        # Mean of rolling RV should be near true vol within sampling error
        recovered = rv30.dropna().mean()
        assert abs(recovered - true_vol) < 0.01, f"true {true_vol} recovered {recovered}"


# ---------------------------------------------------------------------------
# Causal percentile rank — no lookahead
# ---------------------------------------------------------------------------

class TestCausality:
    def test_pct_rank_at_t_uses_only_past(self):
        """Ranking at time t should depend only on data up to t.

        Mutate values AFTER t and confirm rank at t is unchanged.
        """
        np.random.seed(0)
        n = 2000
        s = pd.Series(np.random.randn(n)).cumsum()
        df = s.to_frame("X")
        baseline = causal_pct_rank(df).copy()

        # Mutate the tail of the series
        df_mut = df.copy()
        df_mut.iloc[1500:] = df_mut.iloc[1500:] * 100 + 1e6
        mutated = causal_pct_rank(df_mut)

        # Values at t < 1500 should be unchanged
        head_baseline = baseline.iloc[:1500]
        head_mutated = mutated.iloc[:1500]
        pd.testing.assert_frame_equal(head_baseline, head_mutated)

    def test_pct_rank_in_unit_interval(self):
        s = pd.Series(np.random.RandomState(1).randn(2000)).to_frame("X")
        p = causal_pct_rank(s).dropna()
        assert (p["X"] >= 0).all() and (p["X"] <= 1).all()


# ---------------------------------------------------------------------------
# Roll-date generator
# ---------------------------------------------------------------------------

class TestRollDates:
    def test_third_friday_2024(self):
        # 3rd Fridays of 2024: known dates
        rolls = third_fridays(pd.Timestamp("2024-01-01"), pd.Timestamp("2024-12-31"))
        expected = [
            "2024-01-19", "2024-02-16", "2024-03-15", "2024-04-19",
            "2024-05-17", "2024-06-21", "2024-07-19", "2024-08-16",
            "2024-09-20", "2024-10-18", "2024-11-15", "2024-12-20",
        ]
        got = [d.strftime("%Y-%m-%d") for d in rolls]
        assert got == expected, f"got {got}"

    def test_rolls_are_all_fridays(self):
        rolls = third_fridays(pd.Timestamp("2010-01-01"), pd.Timestamp("2026-01-01"))
        assert all(d.weekday() == 4 for d in rolls)
