"""Local SQLite signal journal with idempotent signal fingerprints."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from .models import Signal


class SignalJournal:
    """Store signals locally; the database path is ignored by Git."""

    def __init__(self, path: str | Path = "data/signals.sqlite3") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS signals (
                    fingerprint TEXT PRIMARY KEY,
                    pair TEXT NOT NULL,
                    side TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    entry_low REAL NOT NULL,
                    entry_high REAL NOT NULL,
                    stop_loss REAL NOT NULL,
                    take_profit_1 REAL NOT NULL,
                    take_profit_2 REAL NOT NULL,
                    score INTEGER NOT NULL,
                    outcome TEXT,
                    outcome_r REAL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    @staticmethod
    def fingerprint(signal: Signal) -> str:
        raw = "|".join(
            (
                signal.pair,
                signal.side.value,
                signal.timeframe,
                signal.created_at.isoformat(),
                f"{signal.entry_low:.8f}",
                f"{signal.stop_loss:.8f}",
            )
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def record(self, signal: Signal) -> bool:
        """Insert a signal; return False when it was already recorded."""

        fingerprint = self.fingerprint(signal)
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO signals
                (fingerprint, pair, side, timeframe, created_at, entry_low, entry_high,
                 stop_loss, take_profit_1, take_profit_2, score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fingerprint,
                    signal.pair,
                    signal.side.value,
                    signal.timeframe,
                    signal.created_at.isoformat(),
                    signal.entry_low,
                    signal.entry_high,
                    signal.stop_loss,
                    signal.take_profit_1,
                    signal.take_profit_2,
                    signal.score,
                ),
            )
            return cursor.rowcount == 1
