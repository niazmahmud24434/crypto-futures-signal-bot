"""Telegram delivery client. It cannot place exchange orders."""

from __future__ import annotations

import httpx


class TelegramDeliveryError(RuntimeError):
    """Raised when Telegram cannot accept a notification."""


def send_message(token: str, chat_id: int, text: str, timeout: float = 20.0) -> None:
    if not token:
        raise TelegramDeliveryError("TELEGRAM_BOT_TOKEN is not configured")
    try:
        response = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=timeout,
        )
        response.raise_for_status()
        body = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise TelegramDeliveryError("Telegram request failed") from exc
    if not body.get("ok"):
        raise TelegramDeliveryError(
            f"Telegram rejected message: {body.get('description', 'unknown error')}"
        )
