"""
Send email — Outlook COM on Windows, SMTP on Linux/Docker.
Auto-detects platform and uses the appropriate transport.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


def _load_env() -> None:
    from dotenv import load_dotenv
    load_dotenv(_ENV_PATH, encoding="utf-8-sig", override=True)


def _recipients(env_key: str = "GEX_EMAIL_TO") -> list[str]:
    _load_env()
    raw = os.getenv(env_key, "").strip()
    if not raw and env_key != "GEX_EMAIL_TO":
        raw = os.getenv("GEX_EMAIL_TO", "").strip()
    return [e.strip() for e in raw.split(",") if e.strip()]


def send(subject: str, html_body: str, attachments: list[Path] | None = None,
         to: list[str] | None = None, env_key: str = "GEX_EMAIL_TO") -> None:
    recipients = to or _recipients(env_key)
    if not recipients:
        raise ValueError(f"No recipients — set {env_key} in .env")

    if sys.platform == "win32":
        _send_outlook(subject, html_body, attachments, recipients)
    else:
        _send_smtp(subject, html_body, attachments, recipients)


def _send_outlook(subject: str, html_body: str, attachments: list[Path] | None,
                  recipients: list[str]) -> None:
    import win32com.client

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


def _send_smtp(subject: str, html_body: str, attachments: list[Path] | None,
               recipients: list[str]) -> None:
    """SMTP transport for Linux/Docker environments."""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.base import MIMEBase
    from email import encoders

    _load_env()
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASS", "")
    sender = os.getenv("SMTP_FROM", user)

    if not user or not password:
        raise ValueError("SMTP_USER and SMTP_PASS must be set in .env for Linux/Docker email")

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html_body, "html"))

    for path in (attachments or []):
        p = Path(path)
        if not p.exists():
            continue
        part = MIMEBase("application", "octet-stream")
        part.set_payload(p.read_bytes())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{p.name}"')
        msg.attach(part)

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.sendmail(sender, recipients, msg.as_string())
