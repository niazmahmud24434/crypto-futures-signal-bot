"""Telegram formatting and delivery boundary.

This module deliberately has no exchange execution capability.
"""

from __future__ import annotations

from html import escape

from .models import Signal


def format_signal(signal: Signal) -> str:
    """Render a human-readable manual-trading alert."""

    reasons = "\n".join(f"• {escape(reason)}" for reason in signal.reasons)
    return (
        f"{'🟢' if signal.side.value == 'LONG' else '🔴'} "
        f"<b>CRYPTO {escape(signal.side.value)} SIGNAL</b>\n\n"
        f"Pair: <code>{escape(signal.pair)}</code>\n"
        f"Market: Binance Futures\n"
        f"Timeframe: {escape(signal.timeframe)}\n"
        f"Entry: {signal.entry_low:.6g} – {signal.entry_high:.6g}\n"
        f"Stop-loss: {signal.stop_loss:.6g}\n"
        f"TP1: {signal.take_profit_1:.6g}\n"
        f"TP2: {signal.take_profit_2:.6g}\n"
        f"Confirmations: {signal.score}\n"
        f"R:R to TP1: 1:{signal.risk_reward_tp1:.2f}\n\n"
        f"<b>Reasons</b>\n{reasons}\n\n"
        "⚠️ Manual trade only — no order was placed."
    )
