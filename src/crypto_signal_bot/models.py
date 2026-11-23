"""Domain models shared by data, strategy, risk, and notification layers."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class Side(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass(frozen=True, slots=True)
class Signal:
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

    @property
    def risk_reward_tp1(self) -> float:
        entry = (self.entry_low + self.entry_high) / 2
        risk = abs(entry - self.stop_loss)
        reward = abs(self.take_profit_1 - entry)
        return reward / risk if risk else 0.0
