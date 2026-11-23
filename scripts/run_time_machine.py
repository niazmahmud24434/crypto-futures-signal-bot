"""Replay a historical window across pairs and save a Crypto Time Machine report."""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime

from crypto_signal_bot.binance import BinancePublicClient
from crypto_signal_bot.config import get_settings
from crypto_signal_bot.telegram import to_plain
from crypto_signal_bot.telegram_client import TelegramDeliveryError, send_message
from crypto_signal_bot.time_machine import (
    format_time_machine_markdown,
    format_time_machine_message,
    run_time_machine,
)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Crypto Time Machine replay")
    parser.add_argument("--days", type=int, default=None, help="window length in days")
    parser.add_argument("--pairs", default=None, help="comma-separated symbols")
    parser.add_argument("--save", action="store_true", help="write a markdown report")
    parser.add_argument("--telegram", action="store_true", help="send the compact summary")
    args = parser.parse_args(argv)

    settings = get_settings()
    pairs = (
        tuple(item.strip().upper() for item in args.pairs.split(",") if item.strip())
        if args.pairs
        else None
    )
    client = BinancePublicClient(
        settings.binance_futures_base_url, settings.request_timeout_seconds
    )
    report = run_time_machine(client, settings, pairs=pairs, days=args.days, now=datetime.now(UTC))
    markdown = format_time_machine_markdown(report)
    if args.save:
        settings.report_directory.mkdir(parents=True, exist_ok=True)
        path = settings.report_directory / f"time-machine-{datetime.now(UTC):%Y%m%d-%H%M}.md"
        path.write_text(markdown, encoding="utf-8")
        print(f"Saved: {path}")
    print(markdown)

    if args.telegram:
        try:
            send_message(
                settings.telegram_bot_token,
                settings.telegram_chat_id,
                format_time_machine_message(report),
            )
        except TelegramDeliveryError as exc:
            print(f"Telegram delivery failed: {to_plain(str(exc))}")
            return 2
        print("Telegram summary sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
