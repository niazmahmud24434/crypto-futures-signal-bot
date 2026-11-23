# Crypto Futures Signal Bot

Manual-only Binance Futures signal engine with Telegram alerts.

> **Status:** read-only scanner, market-regime engine, confirmation gates,
> duplicate protection, and the signal journal are implemented and tested
> against live Binance public data. The backtester and Crypto Time Machine are
> next. This project does not place Binance orders and does not provide
> financial advice.

## Scope

- Binance Futures public market data only
- BTCUSDT, ETHUSDT, SOLUSDT, TAOUSDT, LINKUSDT plus a controlled top-volume universe
- 15-minute entry timeframe with 1-hour confirmation
- EMA 9/21/50, RSI, MACD, ATR, and volume
- Minimum three confirmations before a signal is delivered
- Long and short signals
- Entry zone, stop-loss, TP1, TP2, R:R, and percentages
- Telegram delivery through `@McMeshubot`
- Crypto Time Machine decision-support module with causal replay on Binance history
- Market regime header: `UP`, `HOLD`, or `DOWN` before every pair signal
- Candlestick pattern double-checks, validated against Binance data rather than textbook claims
- Manual execution only; no Binance API key or secret is required

## How a signal is allowed through

1. **Closed candles only.** The forming candle is dropped, and stale data is rejected.
2. **Market regime.** BTC 1h and 4h trend, momentum, and RSI must agree before the
   market is called `UP` or `DOWN`; disagreement is reported as `HOLD`.
3. **Pair confirmation.** At least three of: EMA 9/21/50 alignment, RSI, MACD,
   volume at/above its 20-candle average, and 1h trend agreement.
4. **Regime gate.** Counter-trend ideas are blocked by default. A `HOLD` market
   needs one extra confirmation.
5. **Candlestick double-check.** A closed-candle pattern that opposes the idea
   blocks the alert. An aligned pattern is listed as extra evidence, never as the
   trigger.
6. **Duplicate protection.** Alerts are anchored to the closed entry candle and
   suppressed by fingerprint plus a per-pair/side cooldown window.
7. **Journal.** Every delivered signal is stored locally so outcomes can be
   reviewed and scored later.

The universe is discovered from `/fapi/v1/exchangeInfo` and restricted to
`PERPETUAL`, `TRADING`, `USDT` contracts whose `underlyingType` is `COIN`.
Tokenized equities, commodities, and index products are therefore excluded from
the published metadata rather than from a hand-maintained name list. A small
name blacklist and an optional `CRYPTO_ONLY_UNIVERSE=false` escape hatch remain
for diagnostics.

## Safety boundary

This software intentionally uses Binance public endpoints. There is no order
execution module, no API key, and no secret. Do not add exchange credentials
unless the project is explicitly redesigned, independently audited, and tested
in a sandbox first. Signals are research output, not a promise of profit.

## Telegram setup

1. Open `@BotFather` in Telegram.
2. Create or select your bot and copy its token.
3. Open `@McMeshubot` and send `/start`.
4. Put the token only in a local `.env` file based on `.env.example`.
5. Keep `TELEGRAM_CHAT_ID=9282726837` or replace it with your intended private chat ID.
6. Never commit `.env` or paste the token into chat, issues, logs, or GitHub.

See [docs/TELEGRAM_SETUP.md](docs/TELEGRAM_SETUP.md) for the full walkthrough.

## Windows development setup

```powershell
cd D:\JARVIS\crypto-futures-signal-bot
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
copy .env.example .env
```

Run checks:

```powershell
pytest
ruff check .
ruff format --check .
```

Run one console-only scan (no Binance credentials required):

```powershell
.\.venv\Scripts\python.exe scripts\run_scan.py
.\.venv\Scripts\python.exe scripts\run_scan.py --signals-only
```

To send the report to Telegram, configure the local `.env` first and explicitly
use:

```powershell
.\.venv\Scripts\python.exe scripts\run_scan.py --telegram
```

## Configuration

All settings are optional except `TELEGRAM_BOT_TOKEN`, which is needed only for
delivery. Values are read from `.env` or the process environment.

| Variable | Default | Meaning |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | empty | BotFather token, local only |
| `TELEGRAM_CHAT_ID` | `9282726837` | Target private chat |
| `MIN_SIGNAL_SCORE` | `3` | Minimum confirmations (of 5) |
| `SIGNAL_COOLDOWN_MINUTES` | `180` | Per-pair/side repeat window |
| `BLOCK_COUNTER_TREND` | `true` | Block ideas against the BTC regime |
| `TOP_VOLUME_LIMIT` | `20` | Extra pairs discovered from 24h volume |
| `CRYPTO_ONLY_UNIVERSE` | `true` | Require `underlyingType: COIN` |
| `MAX_CANDLE_AGE_BARS` | `3` | Reject stale market data |
| `JOURNAL_PATH` | `data/signals.sqlite3` | Local journal database |
| `BACKTEST_FORWARD_BARS` | `96` | Outcome window in entry candles |
| `TIME_MACHINE_DAYS` | `30` | Default replay window |

## Project map

- `src/crypto_signal_bot/` — application code
- `tests/` — offline unit tests with deterministic fixtures
- `config/` — safe, non-secret configuration examples
- `data/` — ignored runtime journal and market data
- `docs/` — architecture, signal contract, and operations documentation
- `ATTRIBUTION.md` — credit for the project that inspired the workflow separation
- `SOURCES.md` — books, public references, and candlestick research acknowledgements

## License

MIT. See [LICENSE](LICENSE) and [ATTRIBUTION.md](ATTRIBUTION.md).
