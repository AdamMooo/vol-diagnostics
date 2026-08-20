import os
import subprocess
import sys

from engine.alert import build_body


def test_body_carries_run_url_and_workflow():
    body = build_body("Daily Data Collection", "https://gh/run/42", "")
    assert "Daily Data Collection" in body
    assert "https://gh/run/42" in body


def test_detail_is_included_when_given():
    assert "chain cannot be backfilled" in build_body("W", "u", "chain cannot be backfilled")


def test_detail_omitted_when_blank():
    body = build_body("W", "u", "")
    assert "<p style='margin:16px 0 0'></p>" not in body


def test_missing_recipient_is_a_hard_error():
    # A silently-swallowed alert is the failure mode this module exists to end,
    # so an unset GEX_EMAIL_TO must exit non-zero rather than no-op.
    proc = subprocess.run(
        [sys.executable, "-m", "engine.alert", "--workflow", "W", "--run-url", "u"],
        capture_output=True, text=True,
        env={"PATH": "/usr/bin:/bin", "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""), "GEX_EMAIL_TO": ""},
    )
    assert proc.returncode == 1
    assert "GEX_EMAIL_TO" in proc.stderr
