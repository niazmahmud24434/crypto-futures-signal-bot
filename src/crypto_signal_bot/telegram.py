"""Telegram message formatting and delivery boundary.

This module deliberately has no exchange execution capability.
"""

from __future__ import annotations

import re
from html import escape

from .context import MarketContext
from .models import Signal


def _price(value: float) -> str:
    if value >= 1000:
        return f"{value:,.2f}"
    if value >= 1:
        return f"{value:,.4f}"
    return f"{value:.6f}"


def _percent(value: float) -> str:
    return f"{value:+.2f}%"


def format_market(market: MarketContext) -> str:
    """Render the mandatory market-regime header."""

    basis = "\n".join(f"• {escape(reason)}" for reason in market.reasons)
    return (
        f"<b>MARKET: {market.regime.value}</b>\n"
        f"Confidence: {market.confidence}% · Horizon: {escape(market.timeframe)}\n"
        f"Basis:\n{basis}"
    )


def format_signal(signal: Signal, market: MarketContext | None = None) -> str:
    """Render a human-readable manual-trading alert with absolute prices and percentages."""

    icon = "🟢" if signal.side.value == "LONG" else "🔴"
    header = (
        format_market(market)
        if market is not None
        else f"<b>MARKET: {escape(signal.market_regime)}</b>"
    )
    reasons = "\n".join(f"• {escape(reason)}" for reason in signal.reasons)
    entry_timeframe = signal.timeframe.split()[0]
    invalidation = f"any {escape(entry_timeframe)} close beyond {_price(signal.stop_loss)} USDT"
    stop_percent = _percent(signal.stop_percent)
    tp1_percent = _percent(signal.take_profit_1_percent)
    tp2_percent = _percent(signal.take_profit_2_percent)
    return (
        f"{icon} <b>CRYPTO {escape(signal.side.value)} SIGNAL</b>\n"
        f"{header}\n\n"
        f"<b>PAIR:</b> <code>{escape(signal.pair)}</code>\n"
        f"<b>SIDE:</b> {escape(signal.side.value)}\n"
        f"<b>TIMEFRAME:</b> {escape(signal.timeframe)}\n"
        f"<b>ENTRY ZONE:</b> {_price(signal.entry_low)} – {_price(signal.entry_high)} USDT\n"
        f"<b>STOP-LOSS:</b> {_price(signal.stop_loss)} USDT ({stop_percent})\n"
        f"<b>TP1:</b> {_price(signal.take_profit_1)} USDT ({tp1_percent})\n"
        f"<b>TP2:</b> {_price(signal.take_profit_2)} USDT ({tp2_percent})\n"
        f"<b>R:R:</b> TP1 1:{signal.risk_reward_tp1:.2f} · TP2 1:{signal.risk_reward_tp2:.2f}\n"
        f"<b>SCORE:</b> {signal.score}/5 confirmations\n\n"
        f"<b>CONFIRMATIONS</b>\n{reasons}\n\n"
        f"<b>EXIT PLAN</b>\n"
        "• TP1: close half and move stop to entry\n"
        "• TP2: close the remainder or trail with 1.5× ATR\n"
        f"• Invalidation: {invalidation}\n"
        "• Time stop: exit if neither target nor stop is hit within 24h\n\n"
        "⚠️ Manual trade only — no order was placed. Not financial advice."
    )


_TAG = re.compile(r"<[^>]+>")


def to_plain(text: str) -> str:
    """Strip Telegram HTML for console logging."""

    return _TAG.sub("", text)
