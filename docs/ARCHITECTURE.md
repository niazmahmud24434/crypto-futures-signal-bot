# Architecture

## Safety boundary

The first release is a signal publisher, not an execution bot. Market data is
read from Binance public Futures endpoints. No API key, secret, trading
permission, or withdrawal permission is used. There is no order module, and
adding one is out of scope for this release.

## Flow

```text
Binance public REST (klines, ticker, exchangeInfo)
            |
            v
    Candle validation (closed only, staleness gate)
            |
            v
    BTC 1h + 4h market regime
            |
            v
    15m pair indicators + 1h confirmation
            |
            v
    Signal construction (entry zone, stop, TP1/TP2, R:R)
            |
            v
    Gates: regime alignment, HOLD threshold, candlestick conflict
            |
            v
    Dedupe: candle-anchored fingerprint + cooldown
            |
            +--> SQLite journal (local, Git-ignored)
            |
            +--> Console report
            |
            +--> Telegram delivery (explicit opt-in)
```

## Modules

| Module | Responsibility |
| --- | --- |
| `binance.py` | Read-only public client, crypto-only universe, staleness helper |
| `indicators.py` | EMA, RSI, MACD, ATR, volume averages |
| `context.py` | Market regime, original candlestick rules, pattern bias |
| `strategy.py` | 15m entry + 1h confirmation, ATR-based risk model |
| `scanner.py` | Per-pair orchestration, gates, per-pair error isolation |
| `journal.py` | SQLite journal, fingerprints, cooldown, outcomes |
| `pipeline.py` | Scan + dedupe + journal + render for one run |
| `reporting.py` | Full-scan message assembly |
| `telegram.py` | Signal formatting; no delivery capability |
| `telegram_client.py` | `sendMessage` delivery boundary |
| `backtest.py` | Conservative stop-first outcomes and statistics |

## Design rules

1. Signals use closed candles only.
2. The 1-hour candle confirms direction; the 15-minute candle controls entry.
3. Every signal has an entry zone, stop, targets, score, reasons, and percentages.
4. Signals are anchored to the closed entry candle, so dedupe and cooldowns
   survive restarts, clock drift, and repeated scans.
5. Network failures produce a health event, never a fabricated signal.
6. Generated data, logs, and secrets stay outside Git.
7. A signal is journaled before delivery.
8. Counter-trend ideas are blocked by default and can only be enabled explicitly.

## Backtest and Time Machine relationship

`backtest.py` owns conservative stop-first outcome evaluation and performance
statistics. The Time Machine consumes the same signal contract, the same
`build_signal` function, and the same outcome contract. It will not produce an
independent strategy, silently change stop/target rules, or place orders.

Historical replay uses a strictly causal slice: at each simulated 15m close, the
entry frame contains only candles closed by that timestamp, and the 1h frame
contains only candles closed by that timestamp. No future candle is visible to
the strategy.
