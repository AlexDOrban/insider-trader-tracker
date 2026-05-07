from __future__ import annotations
import os
import requests


class TelegramError(RuntimeError):
    pass


def send_message(text: str, parse_mode: str = "HTML", disable_preview: bool = True) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token:
        raise TelegramError("TELEGRAM_BOT_TOKEN not set")
    if not chat_id:
        raise TelegramError("TELEGRAM_CHAT_ID not set")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": disable_preview,
    }
    resp = requests.post(url, json=payload, timeout=30)
    data = resp.json() if resp.content else {}
    if resp.status_code != 200 or not data.get("ok", False):
        raise TelegramError(data.get("description", f"HTTP {resp.status_code}"))
