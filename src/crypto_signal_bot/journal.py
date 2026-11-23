"""Local SQLite signal journal with idempotent, candle-anchored fingerprints.

The journal is intentionally local and Git-ignored. It provides duplicate
protection, a cooldown window per pair/side, and outcome tracking used by the
Time Machine and by the live bot's ``/stats`` command.
"""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .models import Signal

_SCHEMA: dict[str, str] = {
    "fingerprint": "TEXT PRIMARY KEY",
    "pair": "TEXT NOT NULL",
    "side": "TEXT NOT NULL",
    "timeframe": "TEXT NOT NULL",
    "created_at": "TEXT NOT NULL",
    "candle_open_time": "TEXT",
    "entry_low": "REAL NOT NULL",
    "entry_high": "REAL NOT NULL",
    "stop_loss": "REAL NOT NULL",
    "take_profit_1": "REAL NOT NULL",
    "take_profit_2": "REAL NOT NULL",
    "score": "INTEGER NOT NULL",
    "regime": "TEXT",
    "patterns": "TEXT",
    "outcome": "TEXT",
    "outcome_r": "REAL",
    "outcome_bars": "INTEGER",
}


@dataclass(frozen=True, slots=True)
class JournalSummary:
    total: int
    resolved: int
    wins: int
    losses: int
    timeouts: int
    average_r: float


class SignalJournal:
    """Store signals locally; the database path is ignored by Git."""

    def __init__(self, path: str | Path = "data/signals.sqlite3") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            self._ensure_schema(connection)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _ensure_schema(connection: sqlite3.Connection) -> None:
        columns = ", ".join(f"{name} {definition}" for name, definition in _SCHEMA.items())
        connection.execute(f"CREATE TABLE IF NOT EXISTS signals ({columns})")
        existing = {
            row["name"] for row in connection.execute("PRAGMA table_info(signals)").fetchall()
        }
        for name, definition in _SCHEMA.items():
            if name in existing or "PRIMARY KEY" in definition:
                continue
            connection.execute(f"ALTER TABLE signals ADD COLUMN {name} {definition}")

    @staticmethod
    def fingerprint(signal: Signal) -> str:
        """Anchor identity to the closed candle, not to wall-clock scan time."""

        anchor = signal.candle_open_time or signal.created_at
        raw = "|".join(
            (
                signal.pair,
                signal.side.value,
                signal.timeframe,
                anchor.astimezone(UTC).isoformat(timespec="seconds"),
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
                (fingerprint, pair, side, timeframe, created_at, candle_open_time,
                 entry_low, entry_high, stop_loss, take_profit_1, take_profit_2,
                 score, regime, patterns)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fingerprint,
                    signal.pair,
                    signal.side.value,
                    signal.timeframe,
                    signal.created_at.isoformat(),
                    signal.candle_open_time.isoformat() if signal.candle_open_time else None,
                    signal.entry_low,
                    signal.entry_high,
                    signal.stop_loss,
                    signal.take_profit_1,
                    signal.take_profit_2,
                    signal.score,
                    signal.market_regime,
                    ",".join(signal.patterns),
                ),
            )
            return cursor.rowcount == 1

    def last_anchor(self, pair: str, side: str) -> datetime | None:
        """Latest candle anchor for this pair and side, ignoring wall-clock drift."""

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT MAX(COALESCE(candle_open_time, created_at)) AS latest
                FROM signals WHERE pair = ? AND side = ?
                """,
                (pair.upper(), str(side).upper()),
            ).fetchone()
        if row is None or row["latest"] is None:
            return None
        return datetime.fromisoformat(str(row["latest"]))

    def on_cooldown(
        self,
        pair: str,
        side: str,
        now: datetime | None = None,
        cooldown_minutes: int = 180,
    ) -> bool:
        """True when the same pair and side already alerted inside the window."""

        last = self.last_anchor(pair, side)
        if last is None:
            return False
        current = now or datetime.now(UTC)
        if last.tzinfo is None:
            last = last.replace(tzinfo=UTC)
        return current - last < timedelta(minutes=cooldown_minutes)

    def pending(
        self, older_than_minutes: int = 60, now: datetime | None = None
    ) -> list[dict[str, Any]]:
        """Unresolved signals old enough to have tradable future candles."""

        current = now or datetime.now(UTC)
        cutoff = (current - timedelta(minutes=older_than_minutes)).isoformat()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM signals
                WHERE outcome IS NULL AND created_at <= ?
                ORDER BY created_at ASC
                """,
                (cutoff,),
            ).fetchall()
        return [dict(row) for row in rows]

    def save_outcome(self, fingerprint: str, result: str, r_multiple: float, bars: int) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE signals
                SET outcome = ?, outcome_r = ?, outcome_bars = ?
                WHERE fingerprint = ?
                """,
                (result, r_multiple, bars, fingerprint),
            )

    def summary(self) -> JournalSummary:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN outcome IS NOT NULL THEN 1 ELSE 0 END) AS resolved,
                    SUM(CASE WHEN outcome = 'target' THEN 1 ELSE 0 END) AS wins,
                    SUM(CASE WHEN outcome = 'stop' THEN 1 ELSE 0 END) AS losses,
                    SUM(CASE WHEN outcome = 'timeout' THEN 1 ELSE 0 END) AS timeouts,
                    AVG(CASE WHEN outcome IS NOT NULL THEN outcome_r END) AS average_r
                FROM signals
                """
            ).fetchone()
        return JournalSummary(
            total=int(row["total"] or 0),
            resolved=int(row["resolved"] or 0),
            wins=int(row["wins"] or 0),
            losses=int(row["losses"] or 0),
            timeouts=int(row["timeouts"] or 0),
            average_r=float(row["average_r"] or 0.0),
        )

    def recent(self, limit: int = 10) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM signals ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]
