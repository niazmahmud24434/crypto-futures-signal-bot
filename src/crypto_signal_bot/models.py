"""Domain models shared by data, strategy, risk, and notification layers."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class Side(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass(frozen=True, slots=True)
class Signal:
    """A manual-trading idea tied to one closed entry candle.

    ``candle_open_time`` is the identity anchor for duplicate detection: the
    same pair, side and closed candle can only ever produce one alert.
    """

    pair: str
    side: Side
    timeframe: str
    created_at: datetime
    entry_low: float
    entry_high: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    score: int
    reasons: tuple[str, ...]
    source: str = "binance-public-futures"
    candle_open_time: datetime | None = None
    market_regime: str = "HOLD"
    patterns: tuple[str, ...] = ()

    @property
    def entry_reference(self) -> float:
        """Midpoint of the entry zone, used for risk and reward maths."""

        return (self.entry_low + self.entry_high) / 2

    @property
    def risk_per_unit(self) -> float:
        return abs(self.entry_reference - self.stop_loss)

    def _percent(self, price: float) -> float:
        if self.entry_reference == 0:
            return 0.0
        move = price - self.entry_reference
        if self.side is Side.SHORT:
            move = -move
        return move / self.entry_reference * 100

    @property
    def stop_percent(self) -> float:
        return self._percent(self.stop_loss)

    @property
    def take_profit_1_percent(self) -> float:
        return self._percent(self.take_profit_1)

    @property
    def take_profit_2_percent(self) -> float:
        return self._percent(self.take_profit_2)

    @property
    def risk_reward_tp1(self) -> float:
        risk = self.risk_per_unit
        if not risk:
            return 0.0
        return abs(self.take_profit_1 - self.entry_reference) / risk

    @property
    def risk_reward_tp2(self) -> float:
        risk = self.risk_per_unit
        if not risk:
            return 0.0
        return abs(self.take_profit_2 - self.entry_reference) / risk
