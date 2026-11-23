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


def evaluate_limit_signal(
    signal: Signal,
    future_candles: pd.DataFrame,
    max_wait_bars: int = 4,
) -> TradeOutcome | None:
    """Evaluate a limit-style entry inside the published zone.

    A trade only exists if price trades into the zone within ``max_wait_bars``.
    When a bar touches both the zone and the stop, the stop is assumed first, so
    the result is never better than the worst plausible intrabar path.
    """

    entry = signal.entry_low if signal.side is Side.LONG else signal.entry_high
    risk = abs(entry - signal.stop_loss)
    if risk <= 0:
        raise ValueError("signal risk must be positive")
    long = signal.side is Side.LONG
    filled = False
    bars_held = 0
    for bars_held, (_, candle) in enumerate(future_candles.iterrows(), start=1):
        high, low = float(candle["high"]), float(candle["low"])
        zone_touched = low <= entry if long else high >= entry
        stop_hit = low <= signal.stop_loss if long else high >= signal.stop_loss
        if not filled:
            if not zone_touched:
                if bars_held >= max_wait_bars:
                    return None
                continue
            filled = True
            if stop_hit:
                return TradeOutcome(
                    signal.pair, signal.side, "stop", entry, signal.stop_loss, risk, -1.0, bars_held
                )
            continue
        if stop_hit:
            return TradeOutcome(
                signal.pair, signal.side, "stop", entry, signal.stop_loss, risk, -1.0, bars_held
            )
        target_hit = high >= signal.take_profit_1 if long else low <= signal.take_profit_1
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

    if not filled or future_candles.empty:
        return None
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
        bars_held,
    )


def evaluate_bracket_signal(
    signal: Signal,
    future_candles: pd.DataFrame,
    entry_mode: str = "market",
    max_wait_bars: int = 4,
    split: float = 0.5,
) -> TradeOutcome | None:
    """Evaluate the published exit plan: half at TP1, stop to entry, rest to TP2.

    ``entry_mode="market"`` fills at the zone midpoint on the next candle.
    ``entry_mode="limit"`` requires price to trade into the zone first and
    returns ``None`` when it never does. A bar that touches both a stop and a
    target is always resolved as the stop, which keeps results pessimistic.
    """

    if entry_mode not in {"market", "limit"}:
        raise ValueError("entry_mode must be 'market' or 'limit'")
    long = signal.side is Side.LONG
    risk = abs(signal.entry_reference - signal.stop_loss)
    entry = signal.entry_reference
    if entry_mode == "limit":
        entry = signal.entry_low if long else signal.entry_high
        risk = abs(entry - signal.stop_loss)
    if risk <= 0:
        raise ValueError("signal risk must be positive")

    def r_of(price: float) -> float:
        move = (price - entry) if long else (entry - price)
        return move / risk

    filled = entry_mode == "market"
    stop_price = signal.stop_loss
    secured = False
    realized = 0.0
    bars_held = 0

    for bars_held, (_, candle) in enumerate(future_candles.iterrows(), start=1):
        high, low = float(candle["high"]), float(candle["low"])
        if not filled:
            zone_touched = low <= entry if long else high >= entry
            if not zone_touched:
                if bars_held >= max_wait_bars:
                    return None
                continue
            filled = True

        stop_hit = low <= stop_price if long else high >= stop_price
        if stop_hit:
            if not secured:
                return TradeOutcome(
                    signal.pair, signal.side, "stop", entry, signal.stop_loss, risk, -1.0, bars_held
                )
            return TradeOutcome(
                signal.pair,
                signal.side,
                "tp1_secured",
                entry,
                entry,
                risk,
                realized,
                bars_held,
            )

        tp2_hit = high >= signal.take_profit_2 if long else low <= signal.take_profit_2
        if secured and tp2_hit:
            realized += (1 - split) * r_of(signal.take_profit_2)
            return TradeOutcome(
                signal.pair,
                signal.side,
                "target",
                entry,
                signal.take_profit_2,
                risk,
                realized,
                bars_held,
            )

        tp1_hit = high >= signal.take_profit_1 if long else low <= signal.take_profit_1
        if not secured and tp1_hit:
            secured = True
            realized += split * r_of(signal.take_profit_1)
            stop_price = entry

    if not filled or future_candles.empty:
        return None
    exit_price = float(future_candles.iloc[-1]["close"])
    if not secured:
        return TradeOutcome(
            signal.pair,
            signal.side,
            "timeout",
            entry,
            exit_price,
            risk,
            r_of(exit_price),
            bars_held,
        )
    realized += (1 - split) * r_of(exit_price)
    return TradeOutcome(
        signal.pair, signal.side, "timeout", entry, exit_price, risk, realized, bars_held
    )


def summarize(outcomes: list[TradeOutcome]) -> BacktestStats:
    """Summarize outcomes without hiding timeouts or losing streaks."""

    wins = sum(outcome.result in {"target", "tp1_secured"} for outcome in outcomes)
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
