"""
Append a GEX observation block to today's daily note for the 60-day observation log.

Called by engine.run_daily at end-of-session (4:30 PM ET). Idempotent — if the
observation block is already present in today's note, no-op.

The intent is to remove the "remembering" overhead from the observation period.
Defensible fields auto-prefill; the qualitative note ("did anything realize today
that the positioning snapshot suggested?") is the only manual step.
"""
from __future__ import annotations

import datetime
from pathlib import Path

DAILY_DIR = Path(r"C:\dev\_daily")
HEADER = "## GEX Observation"


def _fmt_row(s: dict) -> str:
    if s.get("error"):
        return f"| {s.get('ticker','?')} | ERROR — {s['error']} |  |  |  |"
    spot = s.get("spot", 0.0)
    zgl = s.get("zero_gamma_level")
    net_gex_b = (s.get("net_gex") or 0) / 1e9

    if zgl is not None:
        zgl_str = f"{zgl:.1f}"
        zgl_pct = f"{(spot - zgl) / zgl * 100:+.1f}%"
    else:
        zgl_str = "—"
        zgl_pct = "—"

    return (
        f"| {s['ticker']} | {net_gex_b:+.2f}B | "
        f"{zgl_str} | {spot:.2f} | {zgl_pct} |"
    )


def _build_block(summaries: list[dict], date: datetime.date) -> str:
    rows = "\n".join(_fmt_row(s) for s in summaries)
    return f"""
{HEADER} — {date.isoformat()}

Auto-prefilled by `engine.run_daily`. Add a one-line note about what realized today and whether the positioning snapshot looked aligned.

| Ticker | Net GEX | ZGL | Spot | vs ZGL |
|--------|---------|-----|------|--------|
{rows}

**Realized note:**

_(add observation: gap, vol expansion, pin, range-bound, anything notable)_
"""


def append_to_daily_note(summaries: list[dict],
                         date: datetime.date | None = None,
                         daily_dir: Path | None = None) -> Path | None:
    """
    Append observation block to today's daily note. Returns the note path on
    success, None if the daily directory doesn't exist (e.g., on a CI machine).

    Idempotent — if the block already exists in the note, the file is unchanged.
    """
    date = date or datetime.date.today()
    daily_dir = daily_dir or DAILY_DIR

    if not daily_dir.exists():
        return None

    note_path = daily_dir / f"{date.isoformat()}.md"
    block = _build_block(summaries, date)

    if note_path.exists():
        existing = note_path.read_text(encoding="utf-8")
        if HEADER in existing:
            return note_path  # already prefilled today
        new_content = existing.rstrip() + "\n" + block
        note_path.write_text(new_content, encoding="utf-8")
    else:
        # Create minimal daily note if missing
        content = (
            "---\ntype: session\n---\n\n"
            f"# Session - {date.isoformat()}\n"
            f"{block}"
        )
        note_path.write_text(content, encoding="utf-8")

    return note_path
