"""
Telegram bot for Agiens: list chats, select/create chat, agents, edit prompt, text + voice.
Uses effective_user.id as external_id so one user has many backend chats.
"""
import base64
import io
import logging
import os

import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:3001").rstrip("/")
CHANNEL = "telegram"


def _user_id(update: Update) -> str | None:
    if update.effective_user:
        return str(update.effective_user.id)
    return None


async def _list_chats(user_id: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(
            f"{BACKEND_URL}/api/chats",
            params={"channel": CHANNEL, "externalId": user_id},
        )
        if r.status_code != 200:
            return []
        return r.json()


async def _create_chat(user_id: str) -> dict | None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            f"{BACKEND_URL}/api/chats",
            json={"channel": CHANNEL, "externalId": user_id},
        )
        if r.status_code != 200:
            return None
        return r.json()


async def _list_agents() -> list[dict]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(f"{BACKEND_URL}/api/agents")
        if r.status_code != 200:
            return []
        return r.json()


async def _set_chat_agent(chat_id: str, agent_id: str) -> bool:
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.patch(
            f"{BACKEND_URL}/api/chats/{chat_id}/agent",
            json={"agentId": agent_id},
        )
        return r.status_code == 200


async def _update_agent_prompt(agent_id: str, system_prompt: str) -> bool:
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.patch(
            f"{BACKEND_URL}/api/agents/{agent_id}",
            json={"systemPrompt": system_prompt},
        )
        return r.status_code == 200


async def _send_text(chat_id: str, text: str) -> dict | None:
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(
            f"{BACKEND_URL}/api/chats/{chat_id}/send",
            json={"message": text, "modelId": None},
        )
        if r.status_code != 200:
            return None
        return r.json()


async def _send_voice(chat_id: str, audio_bytes: bytes, filename: str) -> dict | None:
    async with httpx.AsyncClient(timeout=120.0) as client:
        files = {"audio": (filename, audio_bytes)}
        r = await client.post(
            f"{BACKEND_URL}/api/chats/{chat_id}/send-voice",
            files=files,
        )
        if r.status_code != 200:
            return None
        return r.json()


# --- Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = _user_id(update)
    if not uid:
        await update.message.reply_text("Ошибка: не удалось определить пользователя.")
        return
    chats = await _list_chats(uid)
    keyboard = []
    for c in chats[:10]:
        title = (c.get("title") or "Чат")[:30]
        keyboard.append([InlineKeyboardButton(title, callback_data=f"chat:{c['id']}")])
    keyboard.append([InlineKeyboardButton("➕ Новый чат", callback_data="new_chat")])
    keyboard.append([
        InlineKeyboardButton("🤖 Агенты", callback_data="agents"),
        InlineKeyboardButton("✏️ Промпт агента", callback_data="edit_prompt"),
    ])
    await update.message.reply_text(
        "Выберите чат или создайте новый. Здесь же можно выбрать агента и изменить промпт.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()
    uid = _user_id(update)
    if not uid:
        await query.edit_message_text("Ошибка: не удалось определить пользователя.")
        return
    data = query.data
    if data == "new_chat":
        new_chat = await _create_chat(uid)
        if not new_chat:
            await query.edit_message_text("Не удалось создать чат.")
            return
        context.user_data["current_chat_id"] = new_chat["id"]
        await query.edit_message_text(f"Создан новый чат. Пишите сообщения.")
        return
    if data.startswith("chat:"):
        chat_id = data[5:]
        context.user_data["current_chat_id"] = chat_id
        await query.edit_message_text("Чат выбран. Пишите сообщения.")
        return
    if data == "agents":
        agents = await _list_agents()
        current = context.user_data.get("current_chat_id")
        if not current:
            await query.edit_message_text("Сначала выберите чат.")
            return
        if not agents:
            await query.edit_message_text("Нет доступных агентов.")
            return
        keyboard = [[InlineKeyboardButton(a.get("name", a["id"]), callback_data=f"agent:{a['id']}")] for a in agents]
        await query.edit_message_text("Выберите агента для этого чата:", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    if data.startswith("agent:"):
        agent_id = data[7:]
        current = context.user_data.get("current_chat_id")
        if not current:
            await query.edit_message_text("Сначала выберите чат.")
            return
        ok = await _set_chat_agent(current, agent_id)
        await query.edit_message_text("Агент назначен." if ok else "Ошибка.")
        return
    if data == "edit_prompt":
        agents = await _list_agents()
        if not agents:
            await query.edit_message_text("Нет доступных агентов.")
            return
        keyboard = [[InlineKeyboardButton(a.get("name", a["id"]), callback_data=f"prompt_agent:{a['id']}")] for a in agents]
        context.user_data["waiting_prompt_agent"] = True
        await query.edit_message_text(
            "Выберите агента, промпт которого хотите изменить:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return
    if data.startswith("prompt_agent:"):
        agent_id = data[13:]
        context.user_data["editing_agent_id"] = agent_id
        context.user_data["waiting_prompt_text"] = True
        await query.edit_message_text("Введите новый системный промпт для этого агента (одним сообщением):")
        return


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    uid = _user_id(update)
    if not uid:
        return
    text = update.message.text.strip()
    if not text:
        return

    if context.user_data.get("waiting_prompt_text") and context.user_data.get("editing_agent_id"):
        agent_id = context.user_data.pop("editing_agent_id", None)
        context.user_data.pop("waiting_prompt_text", None)
        if agent_id:
            ok = await _update_agent_prompt(agent_id, text)
            await update.message.reply_text("Промпт обновлён." if ok else "Ошибка обновления.")
        return

    chat_id = context.user_data.get("current_chat_id")
    if not chat_id:
        new_chat = await _create_chat(uid)
        if new_chat:
            context.user_data["current_chat_id"] = new_chat["id"]
            chat_id = new_chat["id"]
    if not chat_id:
        await update.message.reply_text("Ошибка связи с сервером. Отправьте /start.")
        return
    result = await _send_text(chat_id, text)
    if not result:
        await update.message.reply_text("Не удалось получить ответ.")
        return
    await update.message.reply_text((result.get("content") or "")[:4000])


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.voice:
        return
    uid = _user_id(update)
    if not uid:
        return
    chat_id = context.user_data.get("current_chat_id")
    if not chat_id:
        new_chat = await _create_chat(uid)
        if new_chat:
            context.user_data["current_chat_id"] = new_chat["id"]
            chat_id = new_chat["id"]
    if not chat_id:
        await update.message.reply_text("Ошибка связи с сервером. Отправьте /start.")
        return
    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)
    buf = io.BytesIO()
    await file.download_to_memory(buf)
    buf.seek(0)
    audio_bytes = buf.read()
    result = await _send_voice(chat_id, audio_bytes, "voice.ogg")
    if not result:
        await update.message.reply_text("Не удалось обработать голосовое.")
        return
    content = result.get("content", "")
    await update.message.reply_text(content[:4000])
    audio_b64 = result.get("audioBase64")
    if audio_b64:
        try:
            raw = base64.b64decode(audio_b64)
            await update.message.reply_voice(voice=InputFile(io.BytesIO(raw), filename="reply.mp3"))
        except Exception as e:
            logger.warning("Send voice reply failed: %s", e)


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in .env")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_query))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    logger.info("Telegram bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
