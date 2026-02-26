# Agiens Telegram Bot

Бот для чата Agiens в Telegram: текст и голосовые сообщения (входящие и исходящие).

## Как создать бота в Telegram

1. Откройте [@BotFather](https://t.me/BotFather) в Telegram.
2. Отправьте команду `/newbot`.
3. Введите имя бота (например, `Agiens Chat`).
4. Введите username бота (должен заканчиваться на `bot`, например `agiens_chat_bot`).
5. BotFather пришлёт **токен** вида `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`.

## Что нужно скинуть / настроить

- **TELEGRAM_BOT_TOKEN** — токен от BotFather (см. выше).
- **BACKEND_URL** — URL вашего бэкенда (например `http://localhost:3001` или `http://backend:3001` в Docker).

## Запуск

```bash
cd bots/telegram
cp .env.example .env
# Вписать в .env: TELEGRAM_BOT_TOKEN=..., BACKEND_URL=...
pip install -r requirements.txt
python bot.py
```

Или через Docker (из корня репозитория): см. общий docker-compose в корне.

## Поведение

- `/start` — привязывает этот чат к бэкенду (создаётся или находится один чат на этот Telegram-диалог).
- Текстовое сообщение → отправляется в бэкенд → ответ текстом.
- Голосовое сообщение → отправляется в бэкенд (STT → LLM → TTS) → ответ текстом и голосом (если настроен ElevenLabs).
