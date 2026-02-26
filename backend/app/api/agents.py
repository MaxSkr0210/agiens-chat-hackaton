"""Agents API."""
from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_db
from app.schemas.agent import AgentCreateIn, AgentOut, AgentUpdateIn
from app.storage.repositories import agent_create, agent_get, agent_list, agent_update
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("", response_model=list[AgentOut])
async def list_agents(session: AsyncSession = Depends(get_db)):
    agents = await agent_list(session)
    return [
        AgentOut(
            id=a.id,
            name=a.name,
            description=a.description,
            icon=a.icon or "",
            systemPrompt=a.system_prompt or "",
            modelId=a.model_id,
            supportedCategories=a.supported_categories,
        )
        for a in agents
    ]


@router.get("/{agent_id}", response_model=AgentOut)
async def get_agent(agent_id: str, session: AsyncSession = Depends(get_db)):
    agent = await agent_get(session, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentOut(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        icon=agent.icon or "",
        systemPrompt=agent.system_prompt or "",
        modelId=agent.model_id,
        supportedCategories=agent.supported_categories,
    )


@router.post("", response_model=AgentOut)
async def create_agent(body: AgentCreateIn, session: AsyncSession = Depends(get_db)):
    agent = await agent_create(
        session,
        name=body.name,
        description=body.description,
        icon=body.icon or "",
        system_prompt=body.systemPrompt,
        supported_categories=body.supportedCategories,
    )
    return AgentOut(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        icon=agent.icon or "",
        systemPrompt=agent.system_prompt or "",
        modelId=agent.model_id,
        supportedCategories=agent.supported_categories,
    )


@router.patch("/{agent_id}", response_model=AgentOut)
async def update_agent(agent_id: str, body: AgentUpdateIn, session: AsyncSession = Depends(get_db)):
    agent = await agent_update(
        session,
        agent_id,
        name=body.name,
        description=body.description,
        icon=body.icon,
        system_prompt=body.systemPrompt,
        model_id=body.modelId,
        supported_categories=body.supportedCategories,
    )
    if not a:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentOut(
        id=a.id,
        name=agent.name,
        description=agent.description,
        icon=agent.icon or "",
        systemPrompt=agent.system_prompt or "",
        modelId=agent.model_id,
        supportedCategories=agent.supported_categories,
    )
