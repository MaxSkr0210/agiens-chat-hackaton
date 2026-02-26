"""Chats API: list, get, create, send message, send voice, set model/agent."""
from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.chat import (
    ChatSummaryOut,
    ChatWithMessagesOut,
    CreateChatIn,
    MessageOut,
    SendMessageIn,
    SendMessageOut,
    SetAgentIn,
    SetModelIn,
)
from app.services.chat_service import generate_reply
from app.deps import get_db, get_optional_account
from app.storage.models import AccountModel
from app.storage.repositories import (
    chat_create,
    chat_get,
    chat_get_or_create_for_channel,
    chat_get_with_messages,
    chat_list,
    chat_set_agent,
    chat_set_model,
    chat_update_title,
    message_add,
)

router = APIRouter(prefix="/api/chats", tags=["chats"])


def _last_preview(messages: list) -> str:
    for m in reversed(messages):
        if m.role == "assistant" and m.content:
            return (m.content[:80] + "…") if len(m.content) > 80 else m.content
        if m.role == "user" and m.content:
            return (m.content[:80] + "…") if len(m.content) > 80 else m.content
    return "No messages"


@router.get("", response_model=list[ChatSummaryOut])
async def list_chats(
    channel: str | None = None,
    externalId: str | None = None,
    for_me: bool = False,
    session: AsyncSession = Depends(get_db),
    account: AccountModel | None = Depends(get_optional_account),
):
    """List chats. Use channel+externalId (bot) or for_me=1 with Bearer token (web, same account as Telegram)."""
    if for_me and account:
        channel = account.channel
        externalId = account.external_id
    chats = await chat_list(session, channel=channel, external_id=externalId)
    result = []
    for c in chats:
        full = await chat_get_with_messages(session, c.id)
        messages = full.messages if full else []
        last = messages[-1].created_at.isoformat() if messages else c.updated_at.isoformat()
        result.append(
            ChatSummaryOut(
                id=c.id,
                title=c.title,
                model=c.model_id,
                lastMessagePreview=_last_preview(messages),
                lastMessageAt=last,
            )
        )
    return result


@router.get("/by-channel", response_model=ChatSummaryOut)
async def get_or_create_chat_by_channel(
    channel: str,
    externalId: str,
    session: AsyncSession = Depends(get_db),
):
    """For bots: get or create chat for channel user. Returns chat summary."""
    chat = await chat_get_or_create_for_channel(session, channel, externalId)
    full = await chat_get_with_messages(session, chat.id)
    messages = full.messages if full else []
    last = messages[-1].created_at.isoformat() if messages else chat.updated_at.isoformat()
    return ChatSummaryOut(
        id=chat.id,
        title=chat.title,
        model=chat.model_id,
        lastMessagePreview=_last_preview(messages),
        lastMessageAt=last,
    )


@router.get("/{chat_id}/ticket")
async def get_chat_ticket(chat_id: str, session: AsyncSession = Depends(get_db)):
    from app.storage.repositories import ticket_get_by_chat
    t = await ticket_get_by_chat(session, chat_id)
    if not t:
        return None
    return {
        "id": t.id,
        "chatId": t.chat_id,
        "status": t.status,
        "category": t.category,
        "assignedAgentId": t.assigned_agent_id,
        "priority": t.priority,
        "createdAt": t.created_at.isoformat(),
        "updatedAt": t.updated_at.isoformat(),
    }


@router.get("/{chat_id}", response_model=ChatWithMessagesOut)
async def get_chat(chat_id: str, session: AsyncSession = Depends(get_db)):
    chat = await chat_get_with_messages(session, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return ChatWithMessagesOut(
        id=chat.id,
        title=chat.title,
        modelId=chat.model_id,
        agentId=chat.agent_id,
        messages=[
            MessageOut(
                id=m.id,
                role=m.role,
                content=m.content,
                createdAt=m.created_at.isoformat(),
            )
            for m in chat.messages
        ],
    )


@router.post("", response_model=ChatSummaryOut)
async def create_chat(
    body: CreateChatIn | None = Body(None),
    session: AsyncSession = Depends(get_db),
):
    model_id = (body.modelId if body else None) or "openrouter/auto"
    if body and body.channel and body.externalId:
        chat = await chat_create(
            session, model_id=model_id, channel=body.channel, external_id=body.externalId
        )
    else:
        chat = await chat_create(session, model_id=model_id)
    return ChatSummaryOut(
        id=chat.id,
        title=chat.title,
        model=chat.model_id,
        lastMessagePreview="",
        lastMessageAt=chat.created_at.isoformat(),
    )


@router.post("/{chat_id}/send", response_model=SendMessageOut)
async def send_message(
    chat_id: str,
    body: SendMessageIn,
    session: AsyncSession = Depends(get_db),
):
    from app.storage.repositories import ticket_create, ticket_get_by_chat, ticket_update
    from app.services.support_orchestration import classify_support_message, route_ticket_to_agent

    chat = await chat_get_with_messages(session, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    await message_add(session, chat_id, "user", body.message)
    # Auto support: create ticket on first message, classify, route to agent
    ticket = await ticket_get_by_chat(session, chat_id)
    if not ticket:
        ticket = await ticket_create(session, chat_id)
        category = await classify_support_message(body.message)
        await ticket_update(session, ticket.id, category=category)
        await route_ticket_to_agent(session, ticket.id, category)
    if body.modelId:
        await chat_set_model(session, chat_id, body.modelId)
    content = await generate_reply(session, chat_id, body.message, body.modelId)
    await message_add(session, chat_id, "assistant", content)
    title = (body.message[:50] + "…") if len(body.message) > 50 else body.message
    await chat_update_title(session, chat_id, title)
    # Level 2 Voice: optional TTS response for text messages (ElevenLabs)
    audio_base64 = None
    if body.withVoice:
        from app.voice.elevenlabs_client import text_to_speech_base64
        audio_base64 = await text_to_speech_base64(content) or ""
    return SendMessageOut(content=content, audioBase64=audio_base64)


@router.post("/{chat_id}/send-voice")
async def send_voice(
    chat_id: str,
    session: AsyncSession = Depends(get_db),
    audio: UploadFile = File(...),
    modelId: str | None = Form(None),
):
    """Accept audio upload → ElevenLabs STT → LLM → ElevenLabs TTS; return content + audioBase64."""
    from app.voice.elevenlabs_client import speech_to_text, text_to_speech_base64

    raw = await audio.read()
    filename = audio.filename or "audio.webm"
    user_text = await speech_to_text(raw, filename)
    if user_text is None or not str(user_text).strip():
        user_text = (
            "[Голос: не удалось распознать. Проверьте ELEVENLABS_API_KEY в .env, "
            "что запись не пустая и не слишком короткая; поддерживаются форматы в т.ч. WebM. Подробности — в логах backend.]"
        )
    chat = await chat_get_with_messages(session, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    await message_add(session, chat_id, "user", user_text)

    from app.storage.repositories import ticket_create, ticket_get_by_chat, ticket_update
    from app.services.support_orchestration import classify_support_message, route_ticket_to_agent

    ticket = await ticket_get_by_chat(session, chat_id)
    if not ticket:
        ticket = await ticket_create(session, chat_id)
        category = await classify_support_message(user_text)
        await ticket_update(session, ticket.id, category=category)
        await route_ticket_to_agent(session, ticket.id, category)
    if modelId:
        await chat_set_model(session, chat_id, modelId)
    content = await generate_reply(session, chat_id, user_text, modelId)
    await message_add(session, chat_id, "assistant", content)
    audio_base64 = await text_to_speech_base64(content) or ""
    return {"content": content, "audioBase64": audio_base64}


@router.post("/{chat_id}/model")
async def set_model(
    chat_id: str,
    body: SetModelIn,
    session: AsyncSession = Depends(get_db),
):
    chat = await chat_set_model(session, chat_id, body.modelId)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"ok": True}


@router.patch("/{chat_id}/agent")
async def set_agent(
    chat_id: str,
    body: SetAgentIn,
    session: AsyncSession = Depends(get_db),
):
    chat = await chat_set_agent(session, chat_id, body.agentId)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"ok": True}


