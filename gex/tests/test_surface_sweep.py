"""Plan 08-04 Task 1 (hull rev): surface_sweep scores the smoothing parameter and reports
parameter-free hull coverage. (The COVERAGE_KNN_K sweep was removed — coverage has no knob.)"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from gex.surface_sweep import sweep_smoothing, hull_coverage, SMOOTHING_CANDIDATES

SPOT = 500.0


def _chain():
    rows = []
    for dte in (7, 30, 60, 90, 120):
        for p in (-12, -8, -4, 0, 4, 8, 12):
            ks = 1.0 + p / 100.0
            rows.append({
                "dte": float(dte),
                "strike": SPOT * ks,
                "iv_pct": 18.0 + 0.03 * dte + 0.06 * p ** 2 - 0.2 * p,
                "log_moneyness": np.log(ks),
                "moneyness": ks,
            })
    return pd.DataFrame(rows)


def test_smoothing_sweep_one_row_per_candidate_all_finite():
    rows = sweep_smoothing(_chain(), SPOT)
    assert len(rows) == len(SMOOTHING_CANDIDATES)
    assert [r["smoothing"] for r in rows] == list(SMOOTHING_CANDIDATES)
    assert all(math.isfinite(r["fit_rmse"]) for r in rows)
    by_s = {r["smoothing"]: r["fit_rmse"] for r in rows}
    # more smoothing trades fit for smoothness -> residual does not shrink
    assert by_s[5.0] >= by_s[0.0] - 1e-9


def test_hull_coverage_is_a_percentage():
    cov = hull_coverage(_chain(), SPOT)
    assert 0.0 <= cov <= 100.0
    assert cov > 50.0  # a chain spanning the band is mostly interpolatable


def test_main_runs_clean_on_empty_store(monkeypatch):
    """With no stored data and a failing live fetch, main() prints a message and exits 0."""
    import gex.surface_sweep as ss
    monkeypatch.setattr(ss, "_load_surface", lambda t: (None, None, "unavailable (test)"))
    assert ss.main("SPY") == 0
