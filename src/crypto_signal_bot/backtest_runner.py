"""Causal historical replay built on the live signal and gate contracts.

Nothing in this module may place an order. It answers one question: if the live
scanner had been running over this window, which alerts would it have produced,
and how did those alerts resolve?
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from .backtest import (
    BacktestStats,
    TradeOutcome,
    evaluate_bracket_signal,
    evaluate_limit_signal,
    evaluate_signal,
    summarize,
)
from .binance import interval_minutes
from .config import Settings
from .context import MarketContext, candlestick_patterns, market_context
from .indicators import add_indicators
from .models import Signal
from .scanner import finalize_signal
from .strategy import build_signal


class RegimeTimeline:
    """Pre-computed BTC regime for every closed 1h candle in the window.

    Indicators are causal, so computing them once and slicing rows reproduces
    exactly what the live path would have seen at each point in time.
    """

    def __init__(self, btc_1h: pd.DataFrame, btc_4h: pd.DataFrame | None = None) -> None:
        self._times: list[datetime] = []
        self._contexts: list[MarketContext] = []
        prepared_1h = add_indicators(btc_1h.sort_values("open_time").reset_index(drop=True))
        prepared_4h = (
            add_indicators(btc_4h.sort_values("open_time").reset_index(drop=True))
            if btc_4h is not None and len(btc_4h)
            else None
        )
        close_times = prepared_1h["close_time"]
        for index in range(59, len(prepared_1h)):
            as_of = close_times.iloc[index].to_pydatetime()
            four_hour = None
            if prepared_4h is not None:
                four_hour = prepared_4h.loc[prepared_4h["close_time"] <= as_of]
            context = market_context(
                prepared_1h.iloc[: index + 1],
                four_hour if four_hour is not None and len(four_hour) >= 60 else None,
                prepared=True,
            )
            self._times.append(as_of)
            self._contexts.append(context)

    def at(self, as_of: datetime) -> MarketContext | None:
        index = bisect_right(self._times, as_of) - 1
        if index < 0:
            return None
        return self._contexts[index]

    def counts(self) -> dict[str, int]:
        counts: dict[str, int] = {"UP": 0, "HOLD": 0, "DOWN": 0}
        for context in self._contexts:
            counts[context.regime.value] += 1
        return counts

    def __len__(self) -> int:
        return len(self._times)


@dataclass(frozen=True, slots=True)
class BacktestTrade:
    signal: Signal
    outcome: TradeOutcome


@dataclass(frozen=True, slots=True)
class BacktestResult:
    pair: str
    start: datetime
    end: datetime
    stats: BacktestStats
    trades: tuple[BacktestTrade, ...]
    candidates: int
    blocked: int
    no_fills: int = 0

    @property
    def outcomes(self) -> list[TradeOutcome]:
        return [trade.outcome for trade in self.trades]

    @property
    def total_r(self) -> float:
        return sum(outcome.r_multiple for outcome in self.outcomes)


def _evaluate(signal: Signal, future: pd.DataFrame, settings: Settings) -> TradeOutcome | None:
    """Pick the evaluator that matches the published exit plan."""

    if settings.bracket_exits:
        return evaluate_bracket_signal(
            signal,
            future,
            entry_mode="limit" if settings.limit_entries else "market",
            max_wait_bars=settings.entry_wait_bars,
        )
    return (
        evaluate_limit_signal(signal, future, settings.entry_wait_bars)
        if settings.limit_entries
        else evaluate_signal(signal, future)
    )


def replay_pair(
    pair: str,
    entry_candles: pd.DataFrame,
    confirmation_candles: pd.DataFrame,
    settings: Settings,
    timeline: RegimeTimeline | None = None,
    forward_bars: int | None = None,
) -> BacktestResult:
    """Walk forward one closed 15m candle at a time and evaluate every alert."""

    entry = entry_candles.sort_values("open_time").reset_index(drop=True)
    confirmation = confirmation_candles.sort_values("open_time").reset_index(drop=True)
    entry_prepared = add_indicators(entry)
    confirmation_prepared = add_indicators(confirmation)
    forward = forward_bars or settings.backtest_forward_bars
    cooldown_bars = max(
        1, settings.signal_cooldown_minutes // interval_minutes(settings.entry_timeframe)
    )

    trades: list[BacktestTrade] = []
    candidates = 0
    blocked = 0
    no_fills = 0
    next_allowed = 59

    if len(entry) < 61:
        return BacktestResult(
            pair,
            datetime.min,
            datetime.min,
            summarize([]),
            (),
            candidates,
            blocked,
        )

    for index in range(59, len(entry) - 1):
        if index < next_allowed:
            continue
        as_of = entry.iloc[index]["close_time"].to_pydatetime()
        window = entry_prepared.iloc[: index + 1]
        confirm_index = int(confirmation_prepared["close_time"].searchsorted(as_of, side="right"))
        if confirm_index < 60:
            continue
        market = timeline.at(as_of) if timeline is not None else None
        signal = build_signal(
            pair,
            window,
            confirmation_prepared.iloc[:confirm_index],
            settings.min_signal_score,
            market_regime=market.regime.value if market else "HOLD",
            prepared=True,
            stop_atr=settings.stop_atr_mult,
            tp1_atr=settings.tp1_atr_mult,
            tp2_atr=settings.tp2_atr_mult,
        )
        if signal is None:
            continue
        candidates += 1
        patterns = candlestick_patterns(window)
        finalized, _reason = finalize_signal(signal, patterns, market, settings)
        if finalized is None:
            blocked += 1
            continue
        future = entry.iloc[index + 1 : index + 1 + forward]
        if future.empty:
            break
        outcome = _evaluate(finalized, future, settings)
        if outcome is None:
            no_fills += 1
        else:
            trades.append(BacktestTrade(finalized, outcome))
        next_allowed = index + 1 + cooldown_bars

    start = entry.iloc[0]["open_time"].to_pydatetime()
    end = entry.iloc[-1]["close_time"].to_pydatetime()
    outcomes = [trade.outcome for trade in trades]
    return BacktestResult(
        pair, start, end, summarize(outcomes), tuple(trades), candidates, blocked, no_fills
    )
