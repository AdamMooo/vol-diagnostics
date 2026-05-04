"""Property-based math tests — invariants that must hold for ANY input.

These complement test_math.py reference tests by sweeping parameter
ranges and verifying mathematical properties (monotonicity, bounds,
identities) instead of single-point values.
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
)


# ---------------------------------------------------------------------------
# BS pricer monotonicity
# ---------------------------------------------------------------------------

class TestBSMonotonicity:
    @pytest.mark.parametrize("kind", ["call", "put"])
    def test_price_monotone_in_sigma(self, kind):
        """Higher vol → higher option price (vega > 0 for both calls and puts)."""
        S, K, T, r = 100, 100, 0.25, 0.04
        sigmas = np.linspace(0.05, 1.0, 20)
        prices = [bs_price(S, K, T, r, s, kind=kind) for s in sigmas]
        diffs = np.diff(prices)
        assert (diffs > 0).all(), f"non-monotone in sigma: {diffs}"

    @pytest.mark.parametrize("kind", ["call", "put"])
    def test_price_monotone_in_T(self, kind):
        """Longer T → higher price (theta < 0 for ATM)."""
        S, K, r, sigma = 100, 100, 0.04, 0.20
        Ts = np.linspace(0.01, 2.0, 30)
        prices = [bs_price(S, K, T, r, sigma, kind=kind) for T in Ts]
        diffs = np.diff(prices)
        assert (diffs >= -1e-9).all(), f"non-monotone in T: {diffs.min()}"

    def test_call_price_decreasing_in_K(self):
        """Higher strike → lower call price."""
        S, T, r, sigma = 100, 0.25, 0.04, 0.20
        Ks = np.linspace(80, 120, 20)
        prices = [bs_price(S, K, T, r, sigma, kind="call") for K in Ks]
        diffs = np.diff(prices)
        assert (diffs <= 1e-9).all()

    def test_put_price_increasing_in_K(self):
        """Higher strike → higher put price."""
        S, T, r, sigma = 100, 0.25, 0.04, 0.20
        Ks = np.linspace(80, 120, 20)
        prices = [bs_price(S, K, T, r, sigma, kind="put") for K in Ks]
        diffs = np.diff(prices)
        assert (diffs >= -1e-9).all()

    @pytest.mark.parametrize("kind", ["call", "put"])
    def test_price_non_negative(self, kind):
        """Option prices cannot be negative."""
        np.random.seed(7)
        for _ in range(50):
            S = float(np.random.uniform(50, 200))
            K = float(np.random.uniform(50, 200))
            T = float(np.random.uniform(0.001, 2.0))
            r = float(np.random.uniform(-0.01, 0.10))
            sigma = float(np.random.uniform(0.05, 1.0))
            p = bs_price(S, K, T, r, sigma, kind=kind)
            assert p >= -1e-9, f"negative price {p} at S={S} K={K} T={T} r={r} σ={sigma}"

    def test_call_bounded_above_by_S(self):
        """C ≤ S * exp(-qT) ≤ S (with q=0)."""
        for sigma in [0.10, 0.30, 0.80]:
            for K in [50, 100, 150]:
                p = bs_price(100, K, 0.5, 0.04, sigma, kind="call")
                assert p <= 100 + 1e-9

    def test_put_bounded_above_by_K_pv(self):
        """P ≤ K * exp(-rT)."""
        S, T, r = 100, 0.5, 0.04
        for sigma in [0.10, 0.30, 0.80]:
            for K in [80, 100, 120]:
                p = bs_price(S, K, T, r, sigma, kind="put")
                bound = K * np.exp(-r * T)
                assert p <= bound + 1e-9


# ---------------------------------------------------------------------------
# Sleeve P&L exact identities
# ---------------------------------------------------------------------------

class TestSleeveIdentities:
    """At a single roll, with known prices, sleeve P&L formulas must match
    by-hand calculation."""

    def setup_method(self):
        self.S0 = 100.0
        self.S1 = 105.0  # +5%
        self.K_call = 110.0
        self.K_put = 90.0
        self.P_call = 1.50
        self.P_put = 1.20

    def _spot_ret(self):
        return (self.S1 - self.S0) / self.S0

    def _cc(self):
        return self._spot_ret() + (self.P_call - max(self.S1 - self.K_call, 0)) / self.S0

    def _csp(self, rf_ret):
        return rf_ret + (self.P_put - max(self.K_put - self.S1, 0)) / self.S0

    def _collar(self):
        spot = self._spot_ret()
        short_call = (self.P_call - max(self.S1 - self.K_call, 0)) / self.S0
        long_put = (-self.P_put + max(self.K_put - self.S1, 0)) / self.S0
        return spot + short_call + long_put

    def _strangle(self, rf_ret):
        return rf_ret + (self.P_call - max(self.S1 - self.K_call, 0)) / self.S0 \
                     + (self.P_put  - max(self.K_put  - self.S1, 0)) / self.S0

    def test_collar_equals_cc_plus_long_put(self):
        cc = self._cc()
        long_put = (-self.P_put + max(self.K_put - self.S1, 0)) / self.S0
        assert abs(self._collar() - (cc + long_put)) < 1e-12

    def test_strangle_minus_csp_equals_short_call_minus_rf_no_double(self):
        """Strangle = short call + short put + rf earned.
        CSP = short put + rf. So Strangle - CSP should equal short-call P&L."""
        strangle = self._strangle(rf_ret=0.001)
        csp = self._csp(rf_ret=0.001)
        short_call = (self.P_call - max(self.S1 - self.K_call, 0)) / self.S0
        assert abs((strangle - csp) - short_call) < 1e-12

    def test_cc_capped_above_strike(self):
        """When S1 > K_call, CC return = (K_call - S0 + P_call) / S0."""
        self.S1 = 200.0
        cap = (self.K_call - self.S0 + self.P_call) / self.S0
        assert abs(self._cc() - cap) < 1e-12

    def test_csp_floor_below_strike(self):
        """When S1 < K_put, CSP loss = (S1 - K_put + P_put) / S0 + rf."""
        self.S1 = 50.0
        floor = (self.S1 - self.K_put + self.P_put) / self.S0 + 0.001
        assert abs(self._csp(rf_ret=0.001) - floor) < 1e-12


# ---------------------------------------------------------------------------
# Strike-from-delta numerical stability at extremes
# ---------------------------------------------------------------------------

class TestStrikeStability:
    @pytest.mark.parametrize("delta", [0.05, 0.10, 0.20, 0.30, 0.40, 0.45])
    def test_call_strike_finite_and_above_spot(self, delta):
        S, T, r, sigma = 100, 30/365, 0.04, 0.20
        K = bs_strike_from_delta(S, T, r, sigma, delta, kind="call")
        assert np.isfinite(K)
        assert K > 0
        # OTM call → above spot
        if delta < 0.5:
            assert K > S

    @pytest.mark.parametrize("delta", [-0.05, -0.10, -0.20, -0.30, -0.40, -0.45])
    def test_put_strike_finite_and_below_spot(self, delta):
        S, T, r, sigma = 100, 30/365, 0.04, 0.20
        K = bs_strike_from_delta(S, T, r, sigma, delta, kind="put")
        assert np.isfinite(K)
        assert K > 0
        if abs(delta) < 0.5:
            assert K < S

    def test_strike_monotone_in_delta(self):
        """Higher target call delta (closer to ATM) → lower strike (closer to spot from above)."""
        S, T, r, sigma = 100, 30/365, 0.04, 0.20
        deltas = np.array([0.10, 0.20, 0.30, 0.40])
        Ks = np.array([bs_strike_from_delta(S, T, r, sigma, d, kind="call") for d in deltas])
        diffs = np.diff(Ks)
        assert (diffs < 0).all()


# ---------------------------------------------------------------------------
# iv_at_strike — defensive paths
# ---------------------------------------------------------------------------

class TestIVSurface:
    def test_inverted_smile_handled(self):
        """If iv_atm > iv_90mny (rare 'put-skew inverted'), interpolation still monotone."""
        iv = iv_at_strike(S=100, K=95, iv_atm_pts=20.0, iv_90mny_pts=15.0)
        # at m=0.95, w=0.5 → iv = 20 + 0.5*(15-20) = 17.5 → 0.175
        assert abs(iv - 0.175) < 1e-9

    def test_extreme_S_K_ratio_doesnt_explode(self):
        """Far OTM strikes: m ≪ 0.9 → capped at iv_90mny."""
        iv = iv_at_strike(S=100, K=10, iv_atm_pts=15.0, iv_90mny_pts=20.0)
        assert abs(iv - 0.20) < 1e-9

    def test_zero_skew_collapses_to_atm(self):
        """If iv_90mny == iv_atm, every strike returns ATM IV."""
        for K in [85, 90, 95, 100, 105, 110, 115]:
            iv = iv_at_strike(S=100, K=K, iv_atm_pts=15.0, iv_90mny_pts=15.0)
            assert abs(iv - 0.15) < 1e-9
