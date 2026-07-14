"""Plan 08-03 Task 1: surface_diagnostics — fit RMSE/max-resid, leave-one-expiry-out CV,
coverage %, and report-only surface-coherence (calendar + butterfly) checks."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from engine.gex.exposure_engine import surface_diagnostics

SPOT = 500.0
KEYS = {"coverage_pct", "fit_rmse", "max_resid", "cv_rmse",
        "coherence_calendar", "coherence_butterfly", "coherence_violations"}


def _df(iv_fn, dtes=(7, 30, 60, 90, 120), pcts=(-10, -5, 0, 5, 10), spot=SPOT):
    rows = []
    for dte in dtes:
        for p in pcts:
            ks = 1.0 + p / 100.0
            rows.append({
                "dte": float(dte),
                "strike": spot * ks,
                "iv_pct": float(iv_fn(p, dte)),
                "log_moneyness": np.log(ks),
                "moneyness": ks,
            })
    return pd.DataFrame(rows)


def _smooth(p, dte):
    # contango (rises with DTE) + convex put-skewed smile
    return 18.0 + 0.03 * dte + 0.05 * p ** 2 - 0.15 * p


def test_returns_exact_key_set():
    d = surface_diagnostics(_df(_smooth), SPOT)
    assert set(d.keys()) == KEYS


def test_smooth_surface_is_coherent_with_small_finite_residuals():
    d = surface_diagnostics(_df(_smooth), SPOT)
    assert d["coherence_calendar"] is True
    assert d["coherence_butterfly"] is True
    assert d["coherence_violations"] == 0
    assert 0.0 < d["fit_rmse"] < 5.0
    assert math.isfinite(d["max_resid"])
    assert math.isfinite(d["cv_rmse"])          # >=4 training expiries per fold
    assert 0.0 <= d["coverage_pct"] <= 100.0


def test_calendar_violation_detected():
    # multiplicative level keeps the smile convex (butterfly OK) but makes
    # total variance fall from the 7d to the 30d slice (calendar FAIL).
    level = {7: 2.0, 30: 0.6, 60: 0.8, 90: 1.0, 120: 1.1}
    d = surface_diagnostics(_df(lambda p, dte: _smooth(p, dte) * level[dte]), SPOT)
    assert d["coherence_calendar"] is False
    assert d["coherence_violations"] >= 1


def test_butterfly_violation_detected():
    # an upward ATM bump at one expiry -> concave smile -> negative implied density
    def iv_fn(p, dte):
        if dte == 30 and p == 0:
            return 35.0
        return _smooth(p, dte)
    d = surface_diagnostics(_df(iv_fn), SPOT)
    assert d["coherence_butterfly"] is False
    assert d["coherence_violations"] >= 1


def test_sparse_input_degrades_to_nan_without_raising():
    df = _df(_smooth, dtes=(30,), pcts=(-5, 0, 5))  # 3 points
    d = surface_diagnostics(df, SPOT)
    assert math.isnan(d["coverage_pct"])
    assert math.isnan(d["fit_rmse"])
    assert math.isnan(d["max_resid"])
    assert math.isnan(d["cv_rmse"])
    assert d["coherence_violations"] == 0


def test_cv_rmse_nan_for_single_expiry_finite_for_many():
    single = surface_diagnostics(_df(_smooth, dtes=(30,),
                                     pcts=(-10, -5, 0, 5, 10, 12)), SPOT)
    assert math.isnan(single["cv_rmse"])         # one expiry -> no leave-one-out fold

    many = surface_diagnostics(_df(_smooth), SPOT)
    assert math.isfinite(many["cv_rmse"])


def test_skip_cv_returns_nan_but_keeps_other_diagnostics():
    # skip_cv=True must not touch coverage/fit_rmse/max_resid/coherence — only
    # cv_rmse changes. Also exercises the butterfly-violation path (needs
    # `expiries`, computed outside the skip_cv branch) to guard the refactor.
    full = surface_diagnostics(_df(_smooth), SPOT, skip_cv=False)
    skipped = surface_diagnostics(_df(_smooth), SPOT, skip_cv=True)

    assert math.isfinite(full["cv_rmse"])
    assert math.isnan(skipped["cv_rmse"])
    for key in ("coverage_pct", "fit_rmse", "max_resid",
                "coherence_calendar", "coherence_butterfly", "coherence_violations"):
        assert full[key] == skipped[key]

    def iv_fn(p, dte):
        if dte == 30 and p == 0:
            return 35.0  # forces a butterfly violation -> exercises `expiries` below the CV block
        return _smooth(p, dte)
    d = surface_diagnostics(_df(iv_fn), SPOT, skip_cv=True)
    assert d["coherence_butterfly"] is False
    assert d["coherence_violations"] >= 1


def test_empty_input_degrades():
    d = surface_diagnostics(pd.DataFrame(), SPOT)
    assert set(d.keys()) == KEYS
    assert math.isnan(d["fit_rmse"])
