# Telegram setup

## Create the bot

1. Open `@BotFather`.
2. Send `/newbot` or use `/mybots` for an existing bot.
3. Copy the token locally. Do not send it in chat or commit it to Git.
4. Open `@McMeshubot` and send `/start`.

## Local configuration

Copy `.env.example` to `.env` and set:

```env
TELEGRAM_BOT_TOKEN=your-local-token
TELEGRAM_CHAT_ID=9282726837
```

The `.gitignore` excludes `.env`. The bot will only send notifications; it
cannot place an exchange order.
