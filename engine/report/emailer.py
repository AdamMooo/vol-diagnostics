"""
Send email via local Outlook (win32com — Outlook must be running).
Same pattern as selenium/core.py.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


def _recipients(env_key: str = "GEX_EMAIL_TO") -> list[str]:
    from dotenv import load_dotenv
    load_dotenv(_ENV_PATH, encoding="utf-8-sig", override=True)
    raw = os.getenv(env_key, "").strip()
    if not raw and env_key != "GEX_EMAIL_TO":
        raw = os.getenv("GEX_EMAIL_TO", "").strip()
    return [e.strip() for e in raw.split(",") if e.strip()]


def send(subject: str, html_body: str, attachments: list[Path] | None = None,
         to: list[str] | None = None, env_key: str = "GEX_EMAIL_TO") -> None:
    import win32com.client

    recipients = to or _recipients(env_key)
    if not recipients:
        raise ValueError(f"No recipients — set {env_key} in .env")

    try:
        outlook = win32com.client.GetActiveObject("Outlook.Application")
    except Exception:
        try:
            outlook = win32com.client.Dispatch("Outlook.Application")
            time.sleep(3)
        except Exception as exc:
            raise RuntimeError(
                "Cannot connect to Outlook — open Outlook and retry, "
                f"or use --dry-run to skip email. ({exc})"
            ) from exc

    mail = outlook.CreateItem(0)
    mail.To = "; ".join(recipients)
    mail.Subject = subject
    mail.HTMLBody = html_body

    for path in (attachments or []):
        mail.Attachments.Add(str(Path(path).resolve()))

    mail.Send()
