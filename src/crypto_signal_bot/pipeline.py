"""One scan run: analyse, gate, deduplicate, journal, and render.

Delivery is deliberately excluded. The CLI and the Telegram bot both call
:func:`run_once` and decide separately whether a message leaves the machine.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from .binance import BinancePublicClient
from .config import Settings
from .journal import SignalJournal
from .models import Signal
from .reporting import format_report
from .scanner import PairScan, ScanReport, scan


@dataclass(frozen=True, slots=True)
class RunResult:
    report: ScanReport
    delivered: tuple[Signal, ...]
    suppressed: tuple[Signal, ...]
    text: str


def run_once(
    client: BinancePublicClient,
    settings: Settings,
    journal: SignalJournal | None = None,
    now: datetime | None = None,
) -> RunResult:
    """Scan the configured universe and keep only alertable, unseen signals."""

    store = journal or SignalJournal(settings.journal_path)
    report = scan(client, settings, now=now)

    delivered: list[Signal] = []
    suppressed: list[Signal] = []
    pairs: list[PairScan] = []
    for item in report.pairs:
        signal = item.signal
        if signal is None:
            pairs.append(item)
            continue
        if store.on_cooldown(
            signal.pair,
            signal.side.value,
            now=now,
            cooldown_minutes=settings.signal_cooldown_minutes,
        ):
            suppressed.append(signal)
            pairs.append(
                replace(
                    item,
                    signal=None,
                    blocked=f"cooldown active ({settings.signal_cooldown_minutes} min)",
                )
            )
            continue
        if not store.record(signal):
            suppressed.append(signal)
            pairs.append(replace(item, signal=None, blocked="duplicate candle signal"))
            continue
        delivered.append(signal)
        pairs.append(item)

    filtered = ScanReport(report.market, tuple(pairs))
    return RunResult(filtered, tuple(delivered), tuple(suppressed), format_report(filtered))
