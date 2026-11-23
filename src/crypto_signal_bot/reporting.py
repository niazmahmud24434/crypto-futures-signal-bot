"""Human-readable market and pair-scan reports."""

from __future__ import annotations

from .scanner import ScanReport
from .telegram import format_market, format_signal


def _summary_line(report: ScanReport) -> str:
    parts = [f"Scanned: {len(report.pairs)} pairs"]
    blocked = report.blocked
    if blocked:
        parts.append(f"filtered: {len(blocked)}")
    errors = report.errors
    if errors:
        parts.append(f"data errors: {len(errors)}")
    return " · ".join(parts)


def _filtered_details(report: ScanReport, limit: int = 5) -> list[str]:
    lines: list[str] = []
    for item in report.blocked[:limit]:
        lines.append(f"• {item.pair}: {item.blocked}")
    if report.errors:
        for item in report.errors[:limit]:
            lines.append(f"• {item.pair}: data unavailable ({item.error})")
    return lines


def format_report(report: ScanReport) -> str:
    """Render the full scan as one Telegram-ready HTML message."""

    lines = [format_market(report.market), "", "────────────", ""]
    if not report.signals:
        lines.append("<b>No qualified signal — HOLD / WAIT.</b>")
    else:
        for item in report.signals:
            lines.append(format_signal(item.signal, report.market))
            lines.append("")
    details = _filtered_details(report)
    if details:
        lines.append("<b>FILTERED</b>")
        lines.extend(details)
        lines.append("")
    lines.append(_summary_line(report))
    return "\n".join(lines).strip()
