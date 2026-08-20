import datetime

import pandas as pd
import pytest

from engine import config
from engine.regime_alert import _required, assess

FLOOR = config.MONITOR_CREDIBILITY_FLOOR_SESSIONS
D = datetime.date(2026, 8, 20)


def _rows(states, n_deep=FLOOR):
    return pd.DataFrame([
        {"date": D, "ticker": f"T{i}", "metric": "vrp", "n_deep": n_deep, "band_state_deep": s}
        for i, s in enumerate(states)
    ])


def test_required_scales_with_inventory_not_a_fixed_count():
    # The whole point: 3-of-5 today must not become 3-of-17 in 2027.
    assert _required(5, 0.6, 3) == 3
    assert _required(17, 0.6, 3) == 11


def test_required_never_drops_below_the_floor():
    assert _required(2, 0.6, 3) == 3


def test_triggers_when_enough_metrics_are_active():
    r = assess(_rows(["in_entry", "in_escalate", "in_entry", "out", "out"]), D, 0.6, 3)
    assert r["triggered"] and r["active"] == 3 and r["qualifying"] == 5


def test_does_not_trigger_below_threshold():
    r = assess(_rows(["in_entry", "out", "out", "out", "out"]), D, 0.6, 3)
    assert not r["triggered"] and r["active"] == 1


def test_cold_start_metrics_are_excluded_from_both_counts():
    # Below the credibility floor: not qualifying, so it cannot make up the quorum.
    df = pd.concat([_rows(["in_entry", "in_entry"]), _rows(["in_entry"], n_deep=10)])
    r = assess(df, D, 0.6, 3)
    assert r["qualifying"] == 2 and r["active"] == 2


def test_no_qualifying_metrics_never_triggers():
    r = assess(_rows(["in_entry", "in_entry", "in_entry"], n_deep=5), D, 0.6, 3)
    assert not r["triggered"] and r["qualifying"] == 0


def test_names_identify_which_metrics_are_stressed():
    r = assess(_rows(["in_entry", "in_entry", "in_entry"]), D, 0.6, 3)
    assert sorted(r["names"]) == ["T0 vrp", "T1 vrp", "T2 vrp"]
