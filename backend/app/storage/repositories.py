"""Repositories for accounts, chats, messages, agents, tickets."""
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.storage.models import AccountModel, AgentModel, ChatModel, MessageModel, TicketModel


# ---------- Accounts ----------
async def account_get_or_create(
    session: AsyncSession,
    channel: str,
    external_id: str,
) -> AccountModel:
    r = await session.execute(
        select(AccountModel).where(
            AccountModel.channel == channel,
            AccountModel.external_id == external_id,
        )
    )
    acc = r.scalar_one_or_none()
    if acc:
        return acc
    acc = AccountModel(channel=channel, external_id=external_id)
    session.add(acc)
    await session.flush()
    return acc


async def account_get(session: AsyncSession, id: str) -> Optional[AccountModel]:
    r = await session.execute(select(AccountModel).where(AccountModel.id == id))
    return r.scalar_one_or_none()


async def account_get_by_channel(
    session: AsyncSession,
    channel: str,
    external_id: str,
) -> Optional[AccountModel]:
    r = await session.execute(
        select(AccountModel).where(
            AccountModel.channel == channel,
            AccountModel.external_id == external_id,
        )
    )
    return r.scalar_one_or_none()


async def account_set_mcp(
    session: AsyncSession,
    id: str,
    *,
    server_url: Optional[str] = None,
    secret: Optional[str] = None,
) -> Optional[AccountModel]:
    values = {"updated_at": datetime.utcnow()}
    if server_url is not None:
        values["zapier_mcp_server_url"] = server_url.strip() or None
    if secret is not None:
        values["zapier_mcp_secret"] = secret.strip() or None
    await session.execute(update(AccountModel).where(AccountModel.id == id).values(**values))
    await session.flush()
    return await account_get(session, id)


# ---------- Agents ----------
async def agent_list(session: AsyncSession) -> list[AgentModel]:
    r = await session.execute(select(AgentModel).order_by(AgentModel.created_at))
    return list(r.scalars().all())


async def agents_supporting_category(session: AsyncSession, category: str) -> list[AgentModel]:
    """Agents whose supported_categories (comma-separated) contains the given category."""
    all_agents = await agent_list(session)
    category_lower = category.lower().strip()
    return [
        a for a in all_agents
        if a.supported_categories and category_lower in [c.strip().lower() for c in a.supported_categories.split(",")]
    ]


async def agent_get(session: AsyncSession, id: str) -> Optional[AgentModel]:
    r = await session.execute(select(AgentModel).where(AgentModel.id == id))
    return r.scalar_one_or_none()


async def agent_create(
    session: AsyncSession,
    *,
    name: str,
    description: str = "",
    icon: str = "",
    system_prompt: str = "",
    model_id: Optional[str] = None,
    supported_categories: Optional[str] = None,
) -> AgentModel:
    a = AgentModel(
        name=name,
        description=description,
        icon=icon,
        system_prompt=system_prompt,
        model_id=model_id,
        supported_categories=supported_categories,
    )
    session.add(a)
    await session.flush()
    return a


async def agent_update(
    session: AsyncSession,
    id: str,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    icon: Optional[str] = None,
    system_prompt: Optional[str] = None,
    model_id: Optional[str] = None,
    supported_categories: Optional[str] = None,
) -> Optional[AgentModel]:
    values = {}
    if name is not None:
        values["name"] = name
    if description is not None:
        values["description"] = description
    if icon is not None:
        values["icon"] = icon
    if system_prompt is not None:
        values["system_prompt"] = system_prompt
    if model_id is not None:
        values["model_id"] = model_id
    if supported_categories is not None:
        values["supported_categories"] = supported_categories
    if not values:
        return await agent_get(session, id)
    await session.execute(update(AgentModel).where(AgentModel.id == id).values(**values))
    await session.flush()
    return await agent_get(session, id)


# ---------- Chats ----------
async def chat_list(
    session: AsyncSession,
    channel: Optional[str] = None,
    external_id: Optional[str] = None,
) -> list[ChatModel]:
    q = select(ChatModel).order_by(ChatModel.updated_at.desc())
    if channel is not None and external_id is not None:
        q = q.where(
            ChatModel.channel == channel,
            ChatModel.external_id == external_id,
        )
    r = await session.execute(q)
    return list(r.scalars().all())


async def chat_get(session: AsyncSession, id: str) -> Optional[ChatModel]:
    r = await session.execute(
        select(ChatModel).where(ChatModel.id == id)
    )
    return r.scalar_one_or_none()


async def chat_get_with_messages(session: AsyncSession, id: str) -> Optional[ChatModel]:
    r = await session.execute(
        select(ChatModel)
        .where(ChatModel.id == id)
        .options(selectinload(ChatModel.messages))
    )
    chat = r.scalar_one_or_none()
    if not chat:
        return None
    # messages already loaded via selectinload; keep order by created_at
    chat.messages.sort(key=lambda m: m.created_at)
    return chat


async def chat_create(
    session: AsyncSession,
    model_id: str = "openrouter/auto",
    channel: Optional[str] = None,
    external_id: Optional[str] = None,
) -> ChatModel:
    c = ChatModel(model_id=model_id, channel=channel, external_id=external_id)
    session.add(c)
    await session.flush()
    return c


async def chat_get_by_channel(
    session: AsyncSession,
    channel: str,
    external_id: str,
) -> Optional[ChatModel]:
    r = await session.execute(
        select(ChatModel).where(
            ChatModel.channel == channel,
            ChatModel.external_id == external_id,
        )
    )
    return r.scalar_one_or_none()


async def chat_get_or_create_for_channel(
    session: AsyncSession,
    channel: str,
    external_id: str,
    model_id: str = "openrouter/auto",
) -> ChatModel:
    existing = await chat_get_by_channel(session, channel, external_id)
    if existing:
        return existing
    return await chat_create(session, model_id=model_id, channel=channel, external_id=external_id)


async def chat_set_model(session: AsyncSession, id: str, model_id: str) -> Optional[ChatModel]:
    await session.execute(update(ChatModel).where(ChatModel.id == id).values(model_id=model_id, updated_at=datetime.utcnow()))
    await session.flush()
    return await chat_get(session, id)


async def chat_set_agent(session: AsyncSession, id: str, agent_id: Optional[str]) -> Optional[ChatModel]:
    await session.execute(update(ChatModel).where(ChatModel.id == id).values(agent_id=agent_id, updated_at=datetime.utcnow()))
    await session.flush()
    return await chat_get(session, id)


async def chat_update_title(session: AsyncSession, id: str, title: str) -> None:
    await session.execute(update(ChatModel).where(ChatModel.id == id).values(title=title, updated_at=datetime.utcnow()))
    await session.flush()


# ---------- Messages ----------
async def message_add(
    session: AsyncSession,
    chat_id: str,
    role: str,
    content: str,
) -> MessageModel:
    m = MessageModel(chat_id=chat_id, role=role, content=content)
    session.add(m)
    await session.flush()
    return m


async def messages_for_chat(session: AsyncSession, chat_id: str) -> list[MessageModel]:
    r = await session.execute(
        select(MessageModel).where(MessageModel.chat_id == chat_id).order_by(MessageModel.created_at)
    )
    return list(r.scalars().all())


# ---------- Tickets ----------
async def ticket_get_by_chat(session: AsyncSession, chat_id: str) -> Optional[TicketModel]:
    r = await session.execute(select(TicketModel).where(TicketModel.chat_id == chat_id))
    return r.scalar_one_or_none()


async def ticket_list(session: AsyncSession, status: Optional[str] = None) -> list[TicketModel]:
    q = select(TicketModel).order_by(TicketModel.updated_at.desc())
    if status:
        q = q.where(TicketModel.status == status)
    r = await session.execute(q)
    return list(r.scalars().all())


async def ticket_get(session: AsyncSession, id: str) -> Optional[TicketModel]:
    r = await session.execute(select(TicketModel).where(TicketModel.id == id))
    return r.scalar_one_or_none()


async def ticket_create(session: AsyncSession, chat_id: str) -> TicketModel:
    t = TicketModel(chat_id=chat_id)
    session.add(t)
    await session.flush()
    return t


async def ticket_update(
    session: AsyncSession,
    id: str,
    *,
    status: Optional[str] = None,
    category: Optional[str] = None,
    assigned_agent_id: Optional[str] = None,
    priority: Optional[int] = None,
) -> Optional[TicketModel]:
    values = {"updated_at": datetime.utcnow()}
    if status is not None:
        values["status"] = status
    if category is not None:
        values["category"] = category
    if assigned_agent_id is not None:
        values["assigned_agent_id"] = assigned_agent_id
    if priority is not None:
        values["priority"] = priority
    await session.execute(update(TicketModel).where(TicketModel.id == id).values(**values))
    await session.flush()
    return await ticket_get(session, id)


async def ticket_escalate(session: AsyncSession, id: str) -> Optional[TicketModel]:
    return await ticket_update(session, id, status="escalated")
