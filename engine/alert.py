"""
Send a failure alert email. Invoked from CI when a pipeline step fails.

Deliberately separate from engine.report.emailer's daily-report path: the daily
email was retired on 2026-08-18 as noise. This fires only on failure, so it stays
signal. It reuses the same SMTP transport and GEX_EMAIL_TO recipient list.
"""
from __future__ import annotations

import argparse
import os
import sys


def build_body(workflow: str, run_url: str, detail: str) -> str:
    rows = "".join(
        f"<tr><td style='padding:4px 12px 4px 0;color:#666'>{k}</td>"
        f"<td style='padding:4px 0'><b>{v}</b></td></tr>"
        for k, v in (("Workflow", workflow), ("Repository", os.getenv("GITHUB_REPOSITORY", "vol-diagnostics")))
    )
    note = f"<p style='margin:16px 0 0'>{detail}</p>" if detail else ""
    return (
        f"<div style='font-family:system-ui,sans-serif;font-size:14px'>"
        f"<h2 style='margin:0 0 12px'>Pipeline failure</h2>"
        f"<table>{rows}</table>{note}"
        f"<p style='margin:16px 0 0'><a href='{run_url}'>View the failing run</a></p>"
        f"<p style='margin:16px 0 0;color:#666;font-size:12px'>"
        f"Data collection has three scheduled attempts per session; if a later one "
        f"succeeds the gap self-heals and no further alert is sent.</p></div>"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a pipeline failure alert email.")
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--run-url", required=True)
    parser.add_argument("--detail", default="")
    args = parser.parse_args()

    # A silently-swallowed alert is the exact failure mode this exists to end, so
    # missing config is a hard error rather than a quiet no-op.
    if not os.getenv("GEX_EMAIL_TO", "").strip():
        print("[alert] FAILED: GEX_EMAIL_TO is not set — alert not sent.", file=sys.stderr)
        sys.exit(1)

    from engine.report.emailer import send

    try:
        send(
            subject=f"[vol-diagnostics] {args.workflow} failed",
            html_body=build_body(args.workflow, args.run_url, args.detail),
        )
    except Exception as exc:
        print(f"[alert] FAILED: could not send alert email: {exc}", file=sys.stderr)
        sys.exit(1)
    print("[alert] failure alert sent.")


if __name__ == "__main__":
    main()
