# Telegram signal contract

Every Telegram alert must begin with the broader market view before showing a
pair-specific trade idea.

## Market header

```text
MARKET: UP / HOLD / DOWN
Market confidence: 0–100%
Market horizon: 15m / 1h / 4h
Market basis: BTC trend, breadth, volume, funding, open interest
```

`UP`, `HOLD`, and `DOWN` describe the measured market regime, not a promise
that the next candle will move in that direction.

## Trade section

```text
PAIR: BTCUSDT
SIDE: LONG / SHORT
ENTRY: 33.50–33.65 USDT
STOP-LOSS: 32.95 USDT (-1.55%)
TP1: 34.30 USDT (+2.25%)
TP2: 35.10 USDT (+4.63%)
R:R to TP1: 1:1.45
SIGNAL SCORE: 4/6
```

The bot will show both absolute prices and percentages. “Exit” is not a single
blind price: TP1, TP2, stop-loss, timeout, and invalidation are all explicit.

## Confirmation section

```text
INDICATORS:
✓ EMA 9/21/50 alignment
✓ RSI condition
✓ MACD condition
✓ ATR and volume filter
✓ 1h confirmation
✓ Candlestick double-check: bullish engulfing
```

Candlestick patterns add context only after a closed candle. They cannot
override missing market data, a stale candle, bad liquidity, or an invalid risk
profile.

## Conflict handling

- Market `UP` + pair `LONG`: normal alignment.
- Market `DOWN` + pair `LONG`: counter-trend warning; normally blocked or given
  a much higher threshold.
- Market `HOLD`: no aggressive signal unless local confirmation is unusually
  strong.
- Conflicting candlestick and indicator signals: no alert, or an explicit
  `HOLD / CONFLICT` message.

## Source policy

Candlestick rules are implemented independently from publicly described
technical-analysis concepts. The project cites educational sources in
`SOURCES.md` but does not include copyrighted book text, scans, or images.
