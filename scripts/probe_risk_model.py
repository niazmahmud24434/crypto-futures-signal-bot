"""Probe ATR risk multiples on one cached slice of real Binance history.

This is a research tool, not a signal generator. It fetches history once, then
replays several stop/target combinations so the comparison is apples-to-apples.
Results are in-sample and must be forward-tested before being trusted.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime, timedelta

from crypto_signal_bot.backtest_runner import RegimeTimeline, replay_pair
from crypto_signal_bot.binance import BinancePublicClient, drop_forming_candle
from crypto_signal_bot.config import get_settings
from crypto_signal_bot.time_machine import DEFAULT_FEE_BPS, DEFAULT_SLIPPAGE_BPS, WARMUP_DAYS


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="ATR risk-multiple probe")
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--pairs", default="BTCUSDT,ETHUSDT,SOLUSDT,TAOUSDT,LINKUSDT")
    parser.add_argument("--entry-mode", choices=("limit", "market"), default="limit")
    parser.add_argument("--telegram", action="store_true", help="send the comparison table")
    args = parser.parse_args(argv)

    settings = get_settings()
    pairs = tuple(item.strip().upper() for item in args.pairs.split(",") if item.strip())
    end = datetime.now(UTC)
    start = end - timedelta(days=args.days)
    history_start = start - timedelta(days=WARMUP_DAYS)
    client = BinancePublicClient(
        settings.binance_futures_base_url, settings.request_timeout_seconds
    )

    btc_1h = drop_forming_candle(
        client.klines_history("BTCUSDT", "1h", history_start, end, settings.request_pause_seconds)
    )
    btc_4h = drop_forming_candle(
        client.klines_history("BTCUSDT", "4h", history_start, end, settings.request_pause_seconds)
    )
    timeline = RegimeTimeline(btc_1h, btc_4h)

    frames: dict[str, tuple] = {}
    for pair in pairs:
        entry = drop_forming_candle(
            client.klines_history(
                pair, settings.entry_timeframe, history_start, end, settings.request_pause_seconds
            )
        )
        confirmation = drop_forming_candle(
            client.klines_history(
                pair,
                settings.confirmation_timeframe,
                history_start,
                end,
                settings.request_pause_seconds,
            )
        )
        if not entry.empty and not confirmation.empty:
            frames[pair] = (entry, confirmation)
    print(f"Loaded {len(frames)} pairs · {len(btc_1h)} 1h candles · window {args.days} days\n")

    combos = [
        ("baseline s3", {"min_signal_score": 3}),
        ("s3 + align", {"min_signal_score": 3, "require_regime_alignment": True}),
        ("s4", {"min_signal_score": 4}),
        ("s4 + align", {"min_signal_score": 4, "require_regime_alignment": True}),
        ("s5 + align", {"min_signal_score": 5, "require_regime_alignment": True}),
        (
            "s4 + align tp1.5",
            {
                "min_signal_score": 4,
                "require_regime_alignment": True,
                "tp1_atr_mult": 1.5,
                "tp2_atr_mult": 3.0,
            },
        ),
        (
            "s4 + align stop2",
            {
                "min_signal_score": 4,
                "require_regime_alignment": True,
                "stop_atr_mult": 2.0,
            },
        ),
    ]
    header = (
        f"{'config':<20} {'trades':>7} {'nofill':>7} {'win%':>6} {'grossR':>7} "
        f"{'netR':>7} {'PFnet':>6} {'maxloss':>7}"
    )
    print(header)
    print("-" * len(header))
    for label, updates in combos:
        variant = settings.model_copy(
            update={**updates, "limit_entries": args.entry_mode == "limit"}
        )
        trades = []
        wins = 0
        gross = 0.0
        net = 0.0
        no_fills = 0
        positive = negative = 0.0
        for pair, (entry, confirmation) in frames.items():
            result = replay_pair(pair, entry, confirmation, variant, timeline)
            no_fills += result.no_fills
            for trade in result.trades:
                if trade.signal.candle_open_time and trade.signal.candle_open_time < start:
                    continue
                trades.append(trade)
                gross += trade.outcome.r_multiple
                wins += trade.outcome.result == "target"
                risk = trade.outcome.risk
                cost = (
                    trade.outcome.entry
                    * 2
                    * (DEFAULT_FEE_BPS + DEFAULT_SLIPPAGE_BPS)
                    / 10_000
                    / risk
                    if risk > 0
                    else 0.0
                )
                net_r = trade.outcome.r_multiple - cost
                net += net_r
                if net_r > 0:
                    positive += net_r
                else:
                    negative -= net_r
        count = len(trades)
        win_rate = wins / count if count else 0.0
        net_avg = net / count if count else 0.0
        gross_avg = gross / count if count else 0.0
        factor = positive / negative if negative else 0.0
        streak = current = 0
        for trade in trades:
            if trade.outcome.r_multiple < 0:
                current += 1
                streak = max(streak, current)
            else:
                current = 0
        print(
            f"{label:<20} {count:7d} {no_fills:7d} {win_rate * 100:5.1f}% "
            f"{gross_avg:+7.2f} {net_avg:+7.2f} {factor:6.2f} {streak:7d}"
        )
    print("\nIn-sample probe only. Do not treat the best row as validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
