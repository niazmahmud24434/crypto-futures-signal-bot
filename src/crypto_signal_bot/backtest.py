"""Reusable bracket-outcome and performance calculations.

The live signal engine must never place orders. This module only evaluates
historical candles and is also the foundation for the crypto Time Machine.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .models import Side, Signal


@dataclass(frozen=True, slots=True)
class TradeOutcome:
    pair: str
    side: Side
    result: str
    entry: float
    exit: float
    risk: float
    r_multiple: float
    bars_held: int


@dataclass(frozen=True, slots=True)
class BacktestStats:
    trades: int
    wins: int
    losses: int
    timeouts: int
    win_rate: float
    average_r: float
    profit_factor: float
    max_consecutive_losses: int


def evaluate_signal(signal: Signal, future_candles: pd.DataFrame) -> TradeOutcome:
    """Evaluate one signal with conservative stop-first intrabar handling."""

    entry = (signal.entry_low + signal.entry_high) / 2
    risk = abs(entry - signal.stop_loss)
    if risk <= 0:
        raise ValueError("signal risk must be positive")
    long = signal.side is Side.LONG
    for bars_held, (_, candle) in enumerate(future_candles.iterrows(), start=1):
        high, low = float(candle["high"]), float(candle["low"])
        stop_hit = low <= signal.stop_loss if long else high >= signal.stop_loss
        target_hit = high >= signal.take_profit_1 if long else low <= signal.take_profit_1
        if stop_hit:
            return TradeOutcome(
                signal.pair, signal.side, "stop", entry, signal.stop_loss, risk, -1.0, bars_held
            )
        if target_hit:
            reward = abs(signal.take_profit_1 - entry)
            return TradeOutcome(
                signal.pair,
                signal.side,
                "target",
                entry,
                signal.take_profit_1,
                risk,
                reward / risk,
                bars_held,
            )

    if future_candles.empty:
        exit_price = entry
    else:
        exit_price = float(future_candles.iloc[-1]["close"])
    signed_move = (exit_price - entry) if long else (entry - exit_price)
    return TradeOutcome(
        signal.pair,
        signal.side,
        "timeout",
        entry,
        exit_price,
        risk,
        signed_move / risk,
        len(future_candles),
    )


def summarize(outcomes: list[TradeOutcome]) -> BacktestStats:
    """Summarize outcomes without hiding timeouts or losing streaks."""

    wins = sum(outcome.result == "target" for outcome in outcomes)
    losses = sum(outcome.result == "stop" for outcome in outcomes)
    timeouts = sum(outcome.result == "timeout" for outcome in outcomes)
    positive = sum(max(outcome.r_multiple, 0) for outcome in outcomes)
    negative = abs(sum(min(outcome.r_multiple, 0) for outcome in outcomes))
    streak = current = 0
    for outcome in outcomes:
        if outcome.r_multiple < 0:
            current += 1
            streak = max(streak, current)
        else:
            current = 0
    return BacktestStats(
        trades=len(outcomes),
        wins=wins,
        losses=losses,
        timeouts=timeouts,
        win_rate=wins / len(outcomes) if outcomes else 0.0,
        average_r=sum(outcome.r_multiple for outcome in outcomes) / len(outcomes)
        if outcomes
        else 0.0,
        profit_factor=positive / negative if negative else float("inf") if positive else 0.0,
        max_consecutive_losses=streak,
    )
