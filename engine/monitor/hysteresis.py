"""Pure hysteresis state-transition function for the alert engine (D-04, D-08).

check_alert_transition is called three times per metric x ticker per day (once
each for level_rank_deep, level_rank_1yr, change_rank), each with its own
independently-tracked band_state_* as yesterday_state -- no shared state, no
cross-talk between rank_kinds.

States: "out" -> "in_entry" -> "in_escalate", with hysteresis on exit (exit_
band is below entry, so a rank sitting between exit_ and entry does not
re-enter cleanly -- it must actually cross exit_ to leave "in_entry"/"in_escalate").

Entry/escalate/exit band values are NOT hardcoded here -- they are passed in as
parameters, sourced from config.py constants that Plan 03's calibration CLI
populates.
"""
from __future__ import annotations

from engine import config


def check_alert_transition(
    today_rank: int | None,
    n: int,
    yesterday_state: str,
    entry: int,
    escalate: int,
    exit_: int,
    credibility_floor: int = config.MONITOR_CREDIBILITY_FLOOR_SESSIONS,
) -> tuple[str | None, str]:
    """Pure state-transition function. Never raises.

    Returns (alert_type, new_state) where alert_type is "entry", "escalation",
    or None (no fire this transition).
    """
    if n < credibility_floor:
        return None, "out"

    if today_rank is None:
        if yesterday_state in ("in_entry", "in_escalate"):
            return None, yesterday_state
        return None, "out"

    if yesterday_state == "out":
        if today_rank >= entry:
            return "entry", "in_entry"
        return None, "out"

    if yesterday_state == "in_entry":
        if today_rank < exit_:
            return None, "out"
        if today_rank >= escalate:
            return "escalation", "in_escalate"
        return None, "in_entry"

    if yesterday_state == "in_escalate":
        if today_rank < exit_:
            return None, "out"
        return None, "in_escalate"

    # Unknown yesterday_state -- treat as "out" for safety.
    if today_rank >= entry:
        return "entry", "in_entry"
    return None, "out"
