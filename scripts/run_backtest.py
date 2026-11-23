"""Replay one pair over recent Binance history with the live rules."""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime

from crypto_signal_bot.binance import BinancePublicClient
from crypto_signal_bot.config import get_settings
from crypto_signal_bot.time_machine import format_time_machine_markdown, run_time_machine


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Historical replay of one pair")
    parser.add_argument("--pair", default="BTCUSDT")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--show-trades", action="store_true")
    args = parser.parse_args(argv)

    settings = get_settings()
    client = BinancePublicClient(
        settings.binance_futures_base_url, settings.request_timeout_seconds
    )
    report = run_time_machine(
        client, settings, pairs=(args.pair.upper(),), days=args.days, now=datetime.now(UTC)
    )
    print(format_time_machine_markdown(report))
    if args.show_trades:
        print("\n## Trades\n")
        for trade in report.trades:
            when = trade.signal.candle_open_time or trade.signal.created_at
            print(
                f"{when:%Y-%m-%d %H:%M} {trade.signal.pair} {trade.signal.side.value:5} "
                f"{trade.outcome.result:7} {trade.outcome.r_multiple:+.2f}R "
                f"{trade.outcome.bars_held:3} bars"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
