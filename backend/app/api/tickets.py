"""Tickets API."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.schemas.ticket import TicketCreateIn, TicketOut, TicketUpdateIn
from app.services.support_orchestration import classify_support_message, route_ticket_to_agent
from app.storage.repositories import (
    chat_get_with_messages,
    ticket_create,
    ticket_escalate,
    ticket_get,
    ticket_get_by_chat,
    ticket_list,
    ticket_update,
)

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


def _ticket_out(t):
    return TicketOut(
        id=t.id,
        chatId=t.chat_id,
        status=t.status,
        category=t.category,
        assignedAgentId=t.assigned_agent_id,
        priority=t.priority,
        createdAt=t.created_at.isoformat(),
        updatedAt=t.updated_at.isoformat(),
    )


@router.post("", response_model=TicketOut)
async def create_ticket(body: TicketCreateIn, session: AsyncSession = Depends(get_db)):
    """Create ticket for chat, classify first user message, route to agent. Idempotent: if ticket exists, re-runs classify+route."""
    existing = await ticket_get_by_chat(session, body.chatId)
    if existing:
        ticket = existing
        chat = await chat_get_with_messages(session, body.chatId)
        first_user_text = ""
        if chat and chat.messages:
            for m in chat.messages:
                if m.role == "user":
                    first_user_text = m.content
                    break
        if first_user_text:
            category = await classify_support_message(first_user_text)
            await ticket_update(session, ticket.id, category=category)
            await route_ticket_to_agent(session, ticket.id, category)
        t = await ticket_get(session, ticket.id)
        return _ticket_out(t)
    ticket = await ticket_create(session, body.chatId)
    chat = await chat_get_with_messages(session, body.chatId)
    first_user_text = ""
    if chat and chat.messages:
        for m in chat.messages:
            if m.role == "user":
                first_user_text = m.content
                break
    if first_user_text:
        category = await classify_support_message(first_user_text)
        await ticket_update(session, ticket.id, category=category)
        await route_ticket_to_agent(session, ticket.id, category)
    t = await ticket_get(session, ticket.id)
    return _ticket_out(t)


@router.get("", response_model=list[TicketOut])
async def list_tickets(
    status: str | None = None,
    session: AsyncSession = Depends(get_db),
):
    tickets = await ticket_list(session, status=status)
    return [_ticket_out(t) for t in tickets]


@router.get("/{ticket_id}", response_model=TicketOut)
async def get_ticket(ticket_id: str, session: AsyncSession = Depends(get_db)):
    t = await ticket_get(session, ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return _ticket_out(t)


@router.patch("/{ticket_id}", response_model=TicketOut)
async def update_ticket(
    ticket_id: str,
    body: TicketUpdateIn,
    session: AsyncSession = Depends(get_db),
):
    t = await ticket_update(
        session,
        ticket_id,
        status=body.status,
        category=body.category,
        assigned_agent_id=body.assignedAgentId,
        priority=body.priority,
    )
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return _ticket_out(t)


@router.patch("/{ticket_id}/escalate", response_model=TicketOut)
async def escalate_ticket(ticket_id: str, session: AsyncSession = Depends(get_db)):
    t = await ticket_escalate(session, ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return _ticket_out(t)
