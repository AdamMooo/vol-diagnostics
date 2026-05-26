"""Tests for vol_metrics.py — skew_25d, term_structure, rv20, vrp."""
from __future__ import annotations
import numpy as np
import pandas as pd
import pytest
from gex.vol_metrics import compute_skew_25d, compute_term_structure, compute_rv20, compute_vrp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def chain_df():
    """Synthetic chain with 3 expiries across front_month, second_month, beyond-90d."""
    rows = [
        # expiry A — T_years=0.10, ~37 DTE → front_month bucket
        {"expiry": "2024-06-21", "T_years": 0.10, "type": "put",  "strike": 480.0, "delta": -0.25, "iv": 0.22, "oi": 100},
        {"expiry": "2024-06-21", "T_years": 0.10, "type": "put",  "strike": 470.0, "delta": -0.30, "iv": 0.24, "oi": 80},
        {"expiry": "2024-06-21", "T_years": 0.10, "type": "call", "strike": 520.0, "delta":  0.25, "iv": 0.18, "oi": 90},
        {"expiry": "2024-06-21", "T_years": 0.10, "type": "call", "strike": 530.0, "delta":  0.20, "iv": 0.17, "oi": 70},
        # expiry B — T_years=0.18, ~67 DTE → second_month bucket
        {"expiry": "2024-07-19", "T_years": 0.18, "type": "put",  "strike": 475.0, "delta": -0.25, "iv": 0.21, "oi": 60},
        {"expiry": "2024-07-19", "T_years": 0.18, "type": "put",  "strike": 465.0, "delta": -0.32, "iv": 0.23, "oi": 50},
        {"expiry": "2024-07-19", "T_years": 0.18, "type": "call", "strike": 525.0, "delta":  0.25, "iv": 0.17, "oi": 55},
        {"expiry": "2024-07-19", "T_years": 0.18, "type": "call", "strike": 535.0, "delta":  0.22, "iv": 0.16, "oi": 45},
        # expiry C — T_years=0.35, ~128 DTE → beyond 90 DTE, must be skipped
        {"expiry": "2024-09-20", "T_years": 0.35, "type": "put",  "strike": 460.0, "delta": -0.25, "iv": 0.20, "oi": 40},
        {"expiry": "2024-09-20", "T_years": 0.35, "type": "call", "strike": 540.0, "delta":  0.25, "iv": 0.16, "oi": 35},
    ]
    return pd.DataFrame(rows)


@pytest.fixture
def term_df():
    """Synthetic chain with 3 expiries × 1 ATM call row each for term structure tests."""
    rows = [
        {"expiry": "2024-06-07", "T_years": 0.08, "type": "call", "strike": 500.0, "delta": 0.50, "iv": 0.18, "oi": 100},
        {"expiry": "2024-07-05", "T_years": 0.16, "type": "call", "strike": 500.0, "delta": 0.50, "iv": 0.20, "oi": 80},
        {"expiry": "2024-09-20", "T_years": 0.25, "type": "call", "strike": 500.0, "delta": 0.50, "iv": 0.22, "oi": 60},
    ]
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# TestComputeSkew25d
# ---------------------------------------------------------------------------

class TestComputeSkew25d:
    def test_skew_25d_known_strikes(self, chain_df):
        result = compute_skew_25d(chain_df, spot=500.0)
        assert result["front_month"]["put_iv"] == pytest.approx(22.0)
        assert result["front_month"]["call_iv"] == pytest.approx(18.0)
        assert result["front_month"]["skew"] == pytest.approx(4.0)

    def test_skew_bucket_assignment(self, chain_df):
        result = compute_skew_25d(chain_df, spot=500.0)
        assert result["second_month"]["put_iv"] == pytest.approx(21.0)
        assert result["second_month"]["skew"] == pytest.approx(4.0)
        # expiry beyond 90 DTE must NOT appear as a key
        assert set(result.keys()) == {"front_month", "second_month"}

    def test_skew_insufficient_strikes(self):
        # only 1 put per expiry → bucket returns None
        rows = [
            {"expiry": "2024-06-21", "T_years": 0.10, "type": "put",  "strike": 480.0, "delta": -0.25, "iv": 0.22, "oi": 100},
            {"expiry": "2024-06-21", "T_years": 0.10, "type": "call", "strike": 520.0, "delta":  0.25, "iv": 0.18, "oi": 90},
            {"expiry": "2024-06-21", "T_years": 0.10, "type": "call", "strike": 530.0, "delta":  0.20, "iv": 0.17, "oi": 70},
        ]
        df = pd.DataFrame(rows)
        result = compute_skew_25d(df, spot=500.0)
        assert result["front_month"] is None


# ---------------------------------------------------------------------------
# TestComputeTermStructure
# ---------------------------------------------------------------------------

class TestComputeTermStructure:
    def test_term_structure_normal(self, term_df):
        # IVs: 18, 20, 22 — increases with DTE → normal
        result = compute_term_structure(term_df, spot=500.0)
        assert result["classification"] == "normal"

    def test_term_structure_inverted(self, term_df):
        # reverse the IVs: 22, 20, 18 → inverted
        df = term_df.copy()
        df["iv"] = [0.22, 0.20, 0.18]
        result = compute_term_structure(df, spot=500.0)
        assert result["classification"] == "inverted"

    def test_term_structure_flat(self, term_df):
        # IVs: 0.185, 0.190, 0.195 — slope < 1pp per 30 DTE → flat
        df = term_df.copy()
        df["iv"] = [0.185, 0.190, 0.195]
        result = compute_term_structure(df, spot=500.0)
        assert result["classification"] == "flat"

    def test_term_structure_humped(self, term_df):
        # IVs: 18, 23, 19 — middle higher than front and back → humped
        df = term_df.copy()
        df["iv"] = [0.18, 0.23, 0.19]
        result = compute_term_structure(df, spot=500.0)
        assert result["classification"] == "humped"

    def test_term_structure_keys(self, term_df):
        result = compute_term_structure(term_df, spot=500.0)
        assert set(result.keys()) == {"points", "classification", "front_atm_iv", "back_atm_iv"}


# ---------------------------------------------------------------------------
# TestComputeRv20
# ---------------------------------------------------------------------------

class TestComputeRv20:
    def test_rv20_manual(self):
        prices = [100 * (1.01 ** i) for i in range(22)]
        series = pd.Series(prices)
        # compute expected: use last 21 prices → 20 log returns
        arr = np.array(prices)
        log_returns = np.log(arr[1:] / arr[:-1])
        # iloc[-21:] gives the last 21 prices; log returns of those 21 prices = 20 returns
        last_21 = np.array(prices[-21:])
        expected = float(np.sqrt(252) * np.log(last_21[1:] / last_21[:-1]).std(ddof=1))
        assert compute_rv20(series) == pytest.approx(expected, rel=1e-6)

    def test_rv20_cold_start(self):
        assert compute_rv20(pd.Series([100.0] * 20)) is None


# ---------------------------------------------------------------------------
# TestComputeVrp
# ---------------------------------------------------------------------------

class TestComputeVrp:
    def test_vrp_sign(self):
        assert compute_vrp(25.0, 20.0) == pytest.approx(5.0)

    def test_vrp_none_propagation(self):
        assert compute_vrp(None, 20.0) is None
        assert compute_vrp(25.0, None) is None
