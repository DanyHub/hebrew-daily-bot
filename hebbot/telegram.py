"""Minimal Telegram sender (HTML parse mode)."""
import os
import sys

import requests


def send_html(text, token=None, chat_id=None):
    """Send one HTML-formatted message. Exits with a clear error if Telegram refuses it."""
    token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat_id):
        sys.exit("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required to send")
    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
        timeout=30,
    )
    result = resp.json()
    if not result.get("ok"):
        sys.exit(f"Telegram refused the message: {result}")
    return result
