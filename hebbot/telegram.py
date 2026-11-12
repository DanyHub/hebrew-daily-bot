"""Minimal Telegram sender (HTML parse mode)."""
import os
import sys

import requests


def post_message(text, chat_id, token, timeout=30):
    """Send one HTML message and return a plain dict; never raises on API or network errors.

    {"ok": bool, "error_code": int|None, "description": str, "retry_after": int|None}
    """
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=timeout,
        )
        data = resp.json()
    except (requests.RequestException, ValueError) as exc:
        return {"ok": False, "error_code": None, "description": type(exc).__name__, "retry_after": None}
    if data.get("ok"):
        return {"ok": True, "error_code": None, "description": "", "retry_after": None}
    return {
        "ok": False,
        "error_code": data.get("error_code"),
        "description": data.get("description", ""),
        "retry_after": (data.get("parameters") or {}).get("retry_after"),
    }


def send_html(text, token=None, chat_id=None):
    """Send one HTML-formatted message. Exits with a clear error if Telegram refuses it."""
    token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat_id):
        sys.exit("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required to send")
    result = post_message(text, chat_id, token)
    if not result["ok"]:
        sys.exit(f"Telegram refused the message: {result['error_code']} {result['description']}")
    return result
