"""Run one read-only public-data scan.

Console output is always produced. Telegram delivery happens only when
``--telegram`` is passed and the local .env contains a bot token.
"""

from __future__ import annotations

import argparse
import sys

from crypto_signal_bot.binance import BinancePublicClient
from crypto_signal_bot.config import get_settings
from crypto_signal_bot.pipeline import run_once
from crypto_signal_bot.telegram import to_plain
from crypto_signal_bot.telegram_client import TelegramDeliveryError, send_message


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Read-only Binance Futures signal scan")
    parser.add_argument("--telegram", action="store_true", help="send the report to Telegram")
    relationship = parser.add_mutually_exclusive_group()
    relationship.add_argument("--signals-only", action="store_true", help="hide HOLD reports")
    args = parser.parse_args(argv)

    settings = get_settings()
    client = BinancePublicClient(
        settings.binance_futures_base_url, settings.request_timeout_seconds
    )
    result = run_once(client, settings)

    if args.signals_only and not result.delivered:
        print("No new signal. HOLD / WAIT.")
        return 0

    print(to_plain(result.text))
    print(f"\nNew signals: {len(result.delivered)} · suppressed: {len(result.suppressed)}")

    if args.telegram:
        if not result.delivered:
            print("Telegram skipped: nothing new to deliver.")
            return 0
        try:
            send_message(settings.telegram_bot_token, settings.telegram_chat_id, result.text)
        except TelegramDeliveryError as exc:
            print(f"Telegram delivery failed: {exc}")
            return 2
        print("Telegram report sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
