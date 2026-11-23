# Telegram signal contract

Every Telegram alert begins with the broader market view before showing a
pair-specific trade idea.

## Market header

```text
MARKET: UP / HOLD / DOWN
Confidence: 0–100%
Horizon: 1h/4h
Basis:
• BTC 1h EMA alignment bullish
• BTC 4h MACD positive
```

`UP`, `HOLD`, and `DOWN` describe the measured market regime, not a promise that
the next candle will move in that direction. `UP` and `DOWN` require the 1h and
4h evidence to agree; otherwise the regime is `HOLD`.

## Trade section

```text
PAIR: BTCUSDT
SIDE: LONG
TIMEFRAME: 15m entry / 1h confirmation
ENTRY ZONE: 33.5000 – 33.6500 USDT
STOP-LOSS: 32.9500 USDT (-1.55%)
TP1: 34.3000 USDT (+2.25%)
TP2: 35.1000 USDT (+4.63%)
R:R: TP1 1:1.45 · TP2 1:2.99
SCORE: 4/5 confirmations
```

Percentages are signed from the entry-zone midpoint and inverted for shorts, so
a negative percentage always means risk. "Exit" is never a single blind price:
TP1, TP2, stop-loss, inversion, and a 24-hour time stop are all explicit.

## Confirmation section

```text
CONFIRMATIONS
• 15m EMA 9/21/50 bullish alignment
• 15m RSI 61.2 supports upside
• 15m MACD histogram positive
• 1h trend confirmation bullish
• 15m volume at or above 20-candle average
• Candlestick double-check: bullish_engulfing
```

Candlestick patterns add context only after a closed candle. They cannot create
a signal, and they cannot override missing market data, a stale candle, bad
liquidity, or an invalid risk profile.

## Conflict handling

- Market `UP` + pair `LONG`: normal alignment.
- Market `DOWN` + pair `LONG`: blocked as counter-trend while
  `BLOCK_COUNTER_TREND=true`.
- Market `HOLD`: requires one confirmation above `MIN_SIGNAL_SCORE`.
- Opposing closed-candle pattern: no alert.
- Same pair, side, and closed candle: delivered once only.
- Same pair and side inside `SIGNAL_COOLDOWN_MINUTES`: suppressed.

## Implementation mapping

| Field | Source |
| --- | --- |
| Market regime | `context.market_context` (BTC 1h + 4h) |
| Confirmations | `strategy.build_signal` (5 possible) |
| Entry zone | Last closed 15m close ± 0.25 ATR |
| Stop-loss | 1.3 ATR against the idea |
| TP1 / TP2 | 2.0 ATR / 4.0 ATR in favour |
| Candlestick check | `context.candlestick_patterns` + `pattern_bias` |
| Duplicate key | pair + side + timeframe + entry candle open time |

## Source policy

Candlestick rules are implemented independently from publicly described
technical-analysis concepts. The project cites educational sources in
`SOURCES.md` but does not include copyrighted book text, scans, or images.
