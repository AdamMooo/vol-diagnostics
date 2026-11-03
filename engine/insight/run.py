"""
Risk Lens daily run — refresh, read, export, and email ONLY when an event fired.

    python -m engine.insight.run                 # refresh + print the read (no email)
    python -m engine.insight.run --send          # scheduled: email if events since last run
    python -m engine.insight.run --preview       # write out/insight/preview.html, no email
    python -m engine.insight.run --asof 2020-03-09 --no-refresh --preview   # replay a day

Silence is the default. The workflow fires three times per session; `sent.json`
records the last as-of date processed, so re-runs never double-send, and a run that
missed a session reports that session's events on the next run instead of losing them.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import pandas as pd

from engine.insight import render
from engine.insight.lens import build_lens, save_lens
from engine.insight.panel import STORE_DIR, load_panel

LEDGER = STORE_DIR / "sent.json"


def _read_ledger() -> dict:
    try:
        return json.loads(LEDGER.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_ledger(d: dict) -> None:
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(d, indent=2), encoding="utf-8")


def run(send: bool = False, refresh: bool = True, asof: str | None = None,
        preview: bool = False, force_email: bool = False) -> int:
    panel = load_panel(refresh=refresh)
    if refresh:
        # run_daily already refreshes vol indices; only fetch when this runs standalone.
        from engine.data.vol_index import refresh_vol_indices
        if os.getenv("RISK_LENS_SKIP_VOL_REFRESH") != "1":
            refresh_vol_indices()
            panel = load_panel(refresh=False)

    ledger = _read_ledger()
    since = None
    if send and not asof and ledger.get("last_asof"):
        since = pd.Timestamp(ledger["last_asof"])
    lens = build_lens(panel, asof=asof, since=since)
    print(render.to_text(lens))

    if asof is None:
        save_lens(lens)

    if preview:
        out = STORE_DIR / "preview.html"
        out.write_text(render.to_html(lens), encoding="utf-8")
        print(f"\n[insight] preview: {out}")

    if not send:
        return 0
    if since is not None and pd.Timestamp(lens["asof"]) <= since and not force_email:
        print(f"[insight] {lens['asof']} already processed — nothing to send.")
        return 0
    if not lens["events"] and not force_email:
        print("[insight] no events — staying silent.")
        _write_ledger({**ledger, "last_asof": lens["asof"]})
        return 0

    from engine.report import emailer
    try:
        emailer.send(subject=render.subject(lens), html_body=render.to_html(lens), attachments=[])
    except Exception as exc:
        print(f"[insight] email failed: {exc}")
        return 2   # ledger NOT advanced → next firing retries
    print(f"[insight] email sent: {render.subject(lens)}")
    _write_ledger({**ledger, "last_asof": lens["asof"], "last_sent": lens["asof"],
                   "last_subject": render.subject(lens)})
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--send", action="store_true", help="Email if events fired since the last run.")
    p.add_argument("--no-refresh", action="store_true", help="Use cached SPX/vol-index stores.")
    p.add_argument("--asof", help="Read as of a past session (YYYY-MM-DD); not saved.")
    p.add_argument("--preview", action="store_true", help="Write out/insight/preview.html.")
    p.add_argument("--force-email", action="store_true", help="Send even with no events (testing).")
    a = p.parse_args()
    sys.exit(run(send=a.send, refresh=not a.no_refresh, asof=a.asof,
                 preview=a.preview, force_email=a.force_email))


if __name__ == "__main__":
    main()
