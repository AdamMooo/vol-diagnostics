"""Tests for vol_metrics.py — skew_25d, term_structure, rv20, vvix_level."""
from __future__ import annotations
from unittest.mock import patch
import numpy as np
import pandas as pd
import pytest
from engine.vol.vol_metrics import (
    compute_model_free_em,
    compute_skew_25d,
    compute_term_structure,
    _classify_term_structure,
    compute_rv20,
    compute_vvix_level,
)


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
# TestTermStructureEdgeCases
# ---------------------------------------------------------------------------

class TestTermStructureEdgeCases:
    def test_classify_empty_is_insufficient(self):
        # <2 points cannot support a curve-shape claim → distinct sentinel, not "normal"
        assert _classify_term_structure([]) == "insufficient_data"

    def test_classify_single_point_is_insufficient(self):
        assert _classify_term_structure([{"dte": 30.0, "atm_iv": 18.0}]) == "insufficient_data"

    def test_single_expiry_chain_insufficient_sentinel(self):
        # One expiry → one point → sentinel, but front/back atm_iv still populated
        df = pd.DataFrame([
            {"expiry": "2024-06-07", "T_years": 0.08, "type": "call", "strike": 500.0, "delta": 0.50, "iv": 0.18, "oi": 100},
        ])
        result = compute_term_structure(df, spot=500.0)
        assert result["classification"] == "insufficient_data"
        assert result["front_atm_iv"] == pytest.approx(18.0)
        assert result["back_atm_iv"] == pytest.approx(18.0)

    def test_empty_dataframe_returns_sentinel_and_none(self):
        # E9: literally empty chain (columns present, no rows)
        empty = pd.DataFrame(columns=["expiry", "T_years", "type", "strike", "delta", "iv", "oi"])
        result = compute_term_structure(empty, spot=500.0)
        assert result == {
            "points": [],
            "classification": "insufficient_data",
            "front_atm_iv": None,
            "back_atm_iv": None,
        }

    def test_missing_t_years_column_raises_keyerror(self):
        # E10: absent "T_years" column is a defined KeyError contract, not a silent miscompute
        df = pd.DataFrame([
            {"expiry": "2024-06-07", "type": "call", "strike": 500.0, "delta": 0.50, "iv": 0.18, "oi": 100},
        ])
        with pytest.raises(KeyError):
            compute_term_structure(df, spot=500.0)


# ---------------------------------------------------------------------------
# TestComputeRv20
# ---------------------------------------------------------------------------

class TestComputeRv20:
    def test_rv20_manual(self):
        prices = [100 * (1.01 ** i) for i in range(22)]
        series = pd.Series(prices)
        # compute expected: use last 21 prices → 20 log returns
        # iloc[-21:] gives the last 21 prices; log returns of those 21 prices = 20 returns
        last_21 = np.array(prices[-21:])
        expected = float(np.sqrt(252) * np.log(last_21[1:] / last_21[:-1]).std(ddof=1))
        assert compute_rv20(series) == pytest.approx(expected, rel=1e-6)

    def test_rv20_cold_start(self):
        assert compute_rv20(pd.Series([100.0] * 20)) is None

    def test_rv20_nan_price_returns_none(self):
        # E2: a NaN anywhere in the 21-price window → None (never a NaN vol)
        prices = [100.0 + i for i in range(21)]
        prices[10] = float("nan")
        assert compute_rv20(pd.Series(prices)) is None

    def test_rv20_nonpositive_price_returns_none(self):
        # E2: a ≤0 price makes log-return undefined → None
        prices = [100.0 + i for i in range(21)]
        prices[5] = 0.0
        assert compute_rv20(pd.Series(prices)) is None
        prices[5] = -3.0
        assert compute_rv20(pd.Series(prices)) is None

    def test_rv20_identical_prices_is_zero(self):
        # E3: zero realized vol is a valid answer — exactly 0.0, not None and not NaN
        result = compute_rv20(pd.Series([100.0] * 21))
        assert result == pytest.approx(0.0)
        assert result is not None


class TestComputeModelFreeEm:
    def test_model_free_em_positive_output(self):
        rows = [
            {"expiry": "2026-07-17", "T_years": 10/365, "type": "call", "strike": 95.0, "bid": 6.0, "ask": 6.4},
            {"expiry": "2026-07-17", "T_years": 10/365, "type": "put", "strike": 95.0, "bid": 0.8, "ask": 1.0},
            {"expiry": "2026-07-17", "T_years": 10/365, "type": "call", "strike": 100.0, "bid": 2.8, "ask": 3.2},
            {"expiry": "2026-07-17", "T_years": 10/365, "type": "put", "strike": 100.0, "bid": 2.7, "ask": 3.1},
            {"expiry": "2026-07-17", "T_years": 10/365, "type": "call", "strike": 105.0, "bid": 0.9, "ask": 1.1},
            {"expiry": "2026-07-17", "T_years": 10/365, "type": "put", "strike": 105.0, "bid": 5.5, "ask": 5.9},
        ]
        out = compute_model_free_em(pd.DataFrame(rows), spot=100.0, front_expiry="2026-07-17")
        assert out["expected_move_pct"] is not None
        assert out["expected_move_abs"] is not None
        assert out["expected_move_pct"] > 0
        assert out["expected_move_abs"] > 0
        assert out["em_expiry"] == "2026-07-17"
        assert out["em_dte"] == 10

    def test_model_free_em_excludes_invalid_mids(self):
        rows = [
            {"expiry": "2026-07-17", "T_years": 10/365, "type": "call", "strike": 95.0, "bid": 6.0, "ask": 6.4},
            {"expiry": "2026-07-17", "T_years": 10/365, "type": "put", "strike": 95.0, "bid": 0.8, "ask": 1.0},
            {"expiry": "2026-07-17", "T_years": 10/365, "type": "call", "strike": 100.0, "bid": 2.8, "ask": 3.2},
            {"expiry": "2026-07-17", "T_years": 10/365, "type": "put", "strike": 100.0, "bid": 2.7, "ask": 3.1},
            {"expiry": "2026-07-17", "T_years": 10/365, "type": "call", "strike": 105.0, "bid": 0.0, "ask": 0.0},
            {"expiry": "2026-07-17", "T_years": 10/365, "type": "put", "strike": 105.0, "bid": 5.5, "ask": 5.9},
            {"expiry": "2026-07-17", "T_years": 10/365, "type": "call", "strike": 110.0, "bid": 0.1, "ask": 0.2},
            {"expiry": "2026-07-17", "T_years": 10/365, "type": "put", "strike": 110.0, "bid": 10.1, "ask": 10.4},
        ]
        out = compute_model_free_em(pd.DataFrame(rows), spot=100.0, front_expiry="2026-07-17")
        assert out["expected_move_pct"] is not None

    def test_model_free_em_requires_three_valid_strikes(self):
        rows = [
            {"expiry": "2026-07-17", "T_years": 10/365, "type": "call", "strike": 95.0, "bid": 6.0, "ask": 6.4},
            {"expiry": "2026-07-17", "T_years": 10/365, "type": "put", "strike": 95.0, "bid": 0.8, "ask": 1.0},
            {"expiry": "2026-07-17", "T_years": 10/365, "type": "call", "strike": 100.0, "bid": 2.8, "ask": 3.2},
            {"expiry": "2026-07-17", "T_years": 10/365, "type": "put", "strike": 100.0, "bid": 2.7, "ask": 3.1},
        ]
        out = compute_model_free_em(pd.DataFrame(rows), spot=100.0, front_expiry="2026-07-17")
        assert out == {
            "expected_move_pct": None,
            "expected_move_abs": None,
            "em_expiry": "2026-07-17",
            "em_dte": 10,
        }


class TestComputeVvixLevel:
    @patch(
        "engine.data.vol_index.load_vol_index",
        return_value=pd.DataFrame([{"symbol": "VVIX", "date": "2026-06-23", "close": float("nan")}]),
    )
    def test_vvix_nan_close_is_none(self, mock_load):
        # Identical latent bug to _latest_close: a NaN last-row close must be None, not a truthy NaN float
        assert compute_vvix_level() is None

    @patch(
        "engine.data.vol_index.load_vol_index",
        return_value=pd.DataFrame([{"symbol": "VVIX", "date": "2026-06-23", "close": 95.5}]),
    )
    def test_vvix_valid_close_returns_float(self, mock_load):
        assert compute_vvix_level() == pytest.approx(95.5)

    @patch("engine.data.vol_index.load_vol_index", return_value=pd.DataFrame())
    def test_vvix_empty_store_is_none(self, mock_load):
        assert compute_vvix_level() is None


class TestSkewAtmAnchor:
    def test_skew_bucket_includes_atm_iv(self, chain_df):
        result = compute_skew_25d(chain_df, spot=500.0)
        assert "atm_iv" in result["front_month"]
        assert "atm_iv" in result["second_month"]
        assert result["front_month"]["atm_iv"] == pytest.approx(18.0)
