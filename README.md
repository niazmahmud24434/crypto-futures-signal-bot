# Crypto Futures Signal Bot

Manual-only Binance Futures signal engine with Telegram alerts.

> **Status:** Initial architecture phase. This project does not place Binance
> orders and does not provide financial advice.

## Scope

- Binance Futures public market data only
- BTCUSDT, ETHUSDT, SOLUSDT, TAOUSDT, LINKUSDT plus a controlled top-volume universe
- 15-minute entry timeframe with 1-hour confirmation
- EMA 9/21/50, RSI, MACD, ATR, and volume
- Minimum three confirmations before a signal is delivered
- Long and short signals
- Entry zone, stop-loss, TP1, TP2, and risk/reward
- Telegram delivery through `@McMeshubot`
- Crypto Time Machine decision-support module (planned after the backtester)
- Manual execution only; no Binance API key or secret is required

## Safety boundary

This software intentionally uses Binance public endpoints. There is no order
execution module in the initial design. Do not add exchange credentials unless
the project is explicitly redesigned, independently audited, and tested in a
sandbox first. Signals are research output, not a promise of profit.

## Telegram setup

1. Open `@BotFather` in Telegram.
2. Create or select your bot and copy its token.
3. Open `@McMeshubot` and send `/start`.
4. Put the token only in a local `.env` file based on `.env.example`.
5. Keep `TELEGRAM_CHAT_ID=9282726837` or replace it with your intended private chat ID.
6. Never commit `.env` or paste the token into chat, issues, logs, or GitHub.

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

## Project map

- `src/crypto_signal_bot/` — application code
- `tests/` — offline unit tests
- `config/` — safe, non-secret configuration examples
- `data/` — ignored runtime and market data
- `docs/` — architecture, strategy, and operations documentation
- `ATTRIBUTION.md` — credit for the stock day-trader project that inspired the workflow separation

## License

MIT. See [LICENSE](LICENSE) and [ATTRIBUTION.md](ATTRIBUTION.md).
