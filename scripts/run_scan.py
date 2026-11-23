"""Run one read-only public-data scan.

Use ``--telegram`` only after configuring the local .env file. The default is
console-only and never sends anything.
"""

import argparse
import sys

from crypto_signal_bot.binance import BinancePublicClient
from crypto_signal_bot.config import get_settings
from crypto_signal_bot.journal import SignalJournal
from crypto_signal_bot.reporting import format_report
from crypto_signal_bot.scanner import ScanReport, scan
from crypto_signal_bot.telegram_client import send_message


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--telegram", action="store_true", help="send the report to the configured Telegram chat"
    )
    args = parser.parse_args()
    settings = get_settings()
    client = BinancePublicClient(
        settings.binance_futures_base_url, settings.request_timeout_seconds
    )
    report = scan(client, settings)
    journal = SignalJournal()
    fresh_pairs = tuple(
        pair for pair in report.pairs if pair.signal is None or journal.record(pair.signal)
    )
    text = format_report(ScanReport(report.market, fresh_pairs))
    print(text)
    if args.telegram:
        send_message(settings.telegram_bot_token, settings.telegram_chat_id, text)
        print("Telegram report sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
