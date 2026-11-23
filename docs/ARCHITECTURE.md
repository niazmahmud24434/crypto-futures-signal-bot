# Architecture

## Safety boundary

The first release is a signal publisher, not an execution bot. Market data is
read from Binance public Futures endpoints. No API key, secret, trading
permission, or withdrawal permission is used.

## Flow

```text
Binance public REST/WebSocket
            |
            v
       Market data
            |
            v
       Candle validation
            |
            v
       Indicator pipeline
       15m + 1h context
            |
            v
       Confirmation engine
            |
            v
       Risk and signal contract
            |
            +--> SQLite/JSON journal
            |
            +--> Telegram delivery

## Time Machine boundary

The planned crypto Time Machine will consume the same signal and backtest
contracts as the live scanner. It will not produce an independent strategy or
place orders. Its report will include historical setup outcomes, fee/slippage
assumptions, funding costs, long/short results, and a sample-size warning.
```

## Design rules

1. Signals use closed candles only.
2. The 1-hour candle confirms direction; the 15-minute candle controls entry.
3. Every signal has an entry zone, stop, targets, score, and reasons.
4. Duplicate signals are idempotent and do not spam Telegram.
5. Network failures produce a health event, never a fabricated signal.
6. Generated data, logs, and secrets stay outside Git.
