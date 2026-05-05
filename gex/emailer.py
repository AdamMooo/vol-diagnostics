"""
Send email via local Outlook (win32com — Outlook must be running).
Same pattern as selenium/core.py.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


def _recipients() -> list[str]:
    from dotenv import load_dotenv
    load_dotenv(_ENV_PATH, encoding="utf-8-sig", override=True)
    return [e.strip() for e in os.getenv("GEX_EMAIL_TO", "").split(",") if e.strip()]


def send(subject: str, html_body: str, attachments: list[Path] | None = None,
         to: list[str] | None = None) -> None:
    import win32com.client

    recipients = to or _recipients()
    if not recipients:
        raise ValueError("No recipients — set GEX_EMAIL_TO in .env")

    try:
        outlook = win32com.client.GetActiveObject("Outlook.Application")
    except Exception:
        outlook = win32com.client.Dispatch("Outlook.Application")
        time.sleep(3)

    mail = outlook.CreateItem(0)
    mail.To = "; ".join(recipients)
    mail.Subject = subject
    mail.HTMLBody = html_body

    for path in (attachments or []):
        mail.Attachments.Add(str(Path(path).resolve()))

    mail.Send()
