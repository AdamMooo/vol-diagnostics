"""Dead-man's switch. Runs on the Oracle box via cron, NOT on GitHub Actions.

Failure-only CI alerting cannot detect the pipeline never running at all: if a
scheduled trigger is dropped (as on 2026-08-19) or GitHub disables the schedule
after ~60 days of repository inactivity, then nothing fails, so nothing alerts,
and silence is indistinguishable from health. That is the one failure mode
"set and forget" actually has to survive.

So this runs somewhere GitHub Actions is not, and alerts on the ABSENCE of new
data rather than on a step reporting an error. It also refreshes the box's own
out/ copy, so the dashboard stops drifting as a side effect.

Schedule it after the last collection attempt of the session (00:30 UTC), e.g.
  30 1 * * 2-6  cd ~/vol-diagnostics && docker compose exec -T dashboard \
                  python -m engine.watchdog >> ~/watchdog.log 2>&1
"""
from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

import pandas as pd
import pandas_market_calendars as mcal

from engine.session import ET, latest_session


def sessions_behind(latest: datetime.date, expected: datetime.date) -> int:
    if expected <= latest:
        return 0
    sched = mcal.get_calendar("NYSE").schedule(
        start_date=latest.strftime("%Y-%m-%d"), end_date=expected.strftime("%Y-%m-%d")
    )
    return sum(1 for d in sched.index if d.date() > latest)


def stored_latest_date(snapshot: Path) -> datetime.date | None:
    if not snapshot.exists():
        return None
    df = pd.read_parquet(snapshot)
    if df.empty or "date" not in df.columns:
        return None
    return pd.Timestamp(df["date"].max()).date()


def notify(subject: str, lines: list[str]) -> None:
    from engine.report.emailer import send

    body = (
        "<div style='font-family:system-ui,sans-serif;font-size:14px'>"
        "<h2 style='margin:0 0 12px'>Data collection has stopped</h2>"
        + "".join(f"<p style='margin:6px 0'>{line}</p>" for line in lines)
        + "<p style='margin:16px 0 0;color:#666;font-size:12px'>Sent by the watchdog on the "
        "Oracle box, which runs independently of GitHub Actions. It fires when new data "
        "stops arriving — including when the pipeline never ran and therefore never "
        "reported a failure.</p></div>"
    )
    send(subject=subject, html_body=body)


def main() -> None:
    parser = argparse.ArgumentParser(description="Alert when collected data stops arriving.")
    parser.add_argument("--dest", type=Path, default=Path("/app/out"))
    parser.add_argument("--max-sessions-behind", type=int, default=0)
    parser.add_argument("--skip-restore", action="store_true")
    args = parser.parse_args()

    if not args.skip_restore:
        # A restore that cannot run is itself a stall worth hearing about: the box
        # would keep serving whatever it already had, indefinitely and silently.
        try:
            import os

            from engine.restore_from_oci import restore_from_oci

            restore_from_oci(
                bucket="vol-diagnostics-backup", region="ca-toronto-1",
                namespace=os.environ["OCI_NAMESPACE"], dest=args.dest, force=True,
            )
        except Exception as exc:
            print(f"[watchdog] restore failed: {exc}", file=sys.stderr)
            notify("[vol-diagnostics] watchdog: cannot reach Object Storage",
                   [f"The nightly restore failed: <code>{exc}</code>",
                    "The dashboard is now serving whatever it last had."])
            sys.exit(1)

    latest = stored_latest_date(args.dest / "gex_snapshots.parquet")
    expected = latest_session(datetime.datetime.now(ET))

    if latest is None:
        notify("[vol-diagnostics] watchdog: no stored snapshots",
               ["No readable snapshot history was found after restoring."])
        sys.exit(1)

    behind = sessions_behind(latest, expected)
    if behind > args.max_sessions_behind:
        notify(
            f"[vol-diagnostics] no data for {behind} trading session(s)",
            [f"Latest stored session: <b>{latest}</b>",
             f"Most recent session that should exist: <b>{expected}</b>",
             "All three scheduled collection attempts have passed for that session.",
             "A missed session's option chain cannot be backfilled — Cboe serves only "
             "a current snapshot."],
        )
        print(f"[watchdog] STALE: {behind} session(s) behind ({latest} < {expected})")
        sys.exit(1)

    print(f"[watchdog] healthy: latest {latest}, expected {expected}")


if __name__ == "__main__":
    main()
