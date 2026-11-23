"""Human-readable market and pair-scan reports."""

from __future__ import annotations

from .scanner import ScanReport
from .telegram import format_signal


def format_report(report: ScanReport) -> str:
    market = report.market
    lines = [
        f"MARKET REGIME: {market.regime.value}",
        f"Market confidence: {market.confidence}%",
        f"Market horizon: {market.timeframe}",
        "Market basis:",
        *[f"• {reason}" for reason in market.reasons],
        "",
    ]
    signals = [item for item in report.pairs if item.signal is not None]
    if not signals:
        lines.append("No qualified pair signal. HOLD / WAIT.")
        return "\n".join(lines)
    for item in signals:
        lines.append(format_signal(item.signal))
        if item.patterns:
            lines.append(f"Candlestick double-check: {', '.join(item.patterns)}")
        lines.append("")
    return "\n".join(lines).strip()
