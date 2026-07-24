"""Tests for engine/monitor/hysteresis.py -- pure state-transition function.

Provisional bands (entry=97, escalate=99, exit_=87) per 26-02-PLAN.md, pending
Plan 03's calibration.
"""
from __future__ import annotations

from engine import config
from engine.monitor.hysteresis import check_alert_transition

ENTRY, ESCALATE, EXIT = 97, 99, 87
FLOOR = config.MONITOR_CREDIBILITY_FLOOR_SESSIONS


class TestCheckAlertTransition:
    def test_out_to_in_entry_on_band_entry(self):
        alert_type, new_state = check_alert_transition(
            today_rank=98, n=FLOOR, yesterday_state="out",
            entry=ENTRY, escalate=ESCALATE, exit_=EXIT,
        )
        assert alert_type == "entry"
        assert new_state == "in_entry"

    def test_in_entry_to_in_escalate_refires_on_escalation(self):
        alert_type, new_state = check_alert_transition(
            today_rank=99, n=FLOOR, yesterday_state="in_entry",
            entry=ENTRY, escalate=ESCALATE, exit_=EXIT,
        )
        assert alert_type == "escalation"
        assert new_state == "in_escalate"

    def test_in_entry_stays_no_refire_between_exit_and_escalate(self):
        alert_type, new_state = check_alert_transition(
            today_rank=98, n=FLOOR, yesterday_state="in_entry",
            entry=ENTRY, escalate=ESCALATE, exit_=EXIT,
        )
        assert alert_type is None
        assert new_state == "in_entry"

    def test_in_entry_exits_below_exit_band(self):
        alert_type, new_state = check_alert_transition(
            today_rank=80, n=FLOOR, yesterday_state="in_entry",
            entry=ENTRY, escalate=ESCALATE, exit_=EXIT,
        )
        assert alert_type is None
        assert new_state == "out"

    def test_in_escalate_exits_below_exit_band(self):
        alert_type, new_state = check_alert_transition(
            today_rank=80, n=FLOOR, yesterday_state="in_escalate",
            entry=ENTRY, escalate=ESCALATE, exit_=EXIT,
        )
        assert alert_type is None
        assert new_state == "out"

    def test_below_credibility_floor_never_fires(self):
        alert_type, new_state = check_alert_transition(
            today_rank=100, n=FLOOR - 1, yesterday_state="out",
            entry=ENTRY, escalate=ESCALATE, exit_=EXIT,
        )
        assert alert_type is None
        assert new_state == "out"

    def test_none_rank_holds_in_escalate_state(self):
        alert_type, new_state = check_alert_transition(
            today_rank=None, n=FLOOR, yesterday_state="in_escalate",
            entry=ENTRY, escalate=ESCALATE, exit_=EXIT,
        )
        assert alert_type is None
        assert new_state == "in_escalate"

    def test_none_rank_holds_in_entry_state(self):
        alert_type, new_state = check_alert_transition(
            today_rank=None, n=FLOOR, yesterday_state="in_entry",
            entry=ENTRY, escalate=ESCALATE, exit_=EXIT,
        )
        assert alert_type is None
        assert new_state == "in_entry"

    def test_none_rank_stays_out_when_already_out(self):
        alert_type, new_state = check_alert_transition(
            today_rank=None, n=FLOOR, yesterday_state="out",
            entry=ENTRY, escalate=ESCALATE, exit_=EXIT,
        )
        assert alert_type is None
        assert new_state == "out"

    def test_none_rank_resets_regardless_of_state_below_credibility_floor(self):
        alert_type, new_state = check_alert_transition(
            today_rank=None, n=FLOOR - 1, yesterday_state="in_escalate",
            entry=ENTRY, escalate=ESCALATE, exit_=EXIT,
        )
        assert alert_type is None
        assert new_state == "out"

    def test_three_rank_kinds_independent_no_cross_talk(self):
        deep = check_alert_transition(
            today_rank=98, n=FLOOR, yesterday_state="out",
            entry=ENTRY, escalate=ESCALATE, exit_=EXIT,
        )
        oneyr = check_alert_transition(
            today_rank=50, n=FLOOR, yesterday_state="in_entry",
            entry=ENTRY, escalate=ESCALATE, exit_=EXIT,
        )
        change = check_alert_transition(
            today_rank=99, n=FLOOR, yesterday_state="in_entry",
            entry=ENTRY, escalate=ESCALATE, exit_=EXIT,
        )
        assert deep == ("entry", "in_entry")
        assert oneyr == (None, "out")
        assert change == ("escalation", "in_escalate")
