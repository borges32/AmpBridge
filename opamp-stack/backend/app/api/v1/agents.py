"""Agents API endpoints."""

from typing import List, Optional, Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.v1.deps import CurrentUser, require_permission, get_db
from app.core.services.agent_service import AgentService
from app.core.utils.pagination import PaginationParams, PaginatedResponse
from app.security.rbac import Permission
from app.db.models import Agent

router = APIRouter()


class AgentResponse(BaseModel):
    """Agent response model."""
    id: str
    name: str
    env: Optional[str] = None
    os: Optional[str] = None
    arch: Optional[str] = None
    version: Optional[str] = None
    first_seen: datetime
    last_seen: datetime
    last_status: str
    last_config_version: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentStatsResponse(BaseModel):
    """Agent statistics response."""
    total_agents: int
    by_status: dict
    by_environment: dict
    environments: List[str]


@router.get("/agents", response_model=PaginatedResponse[AgentResponse])
async def list_agents(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.READ_AGENTS))],
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    env: Optional[str] = Query(None, description="Filter by environment"),
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in agent ID or name"),
    sync: bool = Query(False, description="Sync from OpAMP server before listing")
):
    """List agents with optional filtering and pagination.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        page: Page number (1-based)
        size: Items per page
        env: Environment filter
        status: Status filter
        search: Search term
        sync: Whether to sync from OpAMP server first
        
    Returns:
        Paginated list of agents
    """
    agent_service = AgentService(db)
    
    # Sync from OpAMP server if requested
    if sync:
        try:
            await agent_service.sync_agents_from_opamp(env_filter=env)
        except Exception as e:
            # Log error but don't fail the request
            pass
    
    # Get agents
    pagination = PaginationParams(page=page, size=size)
    agents, total = agent_service.get_agents(
        pagination=pagination,
        env_filter=env,
        status_filter=status,
        search=search
    )
    
    return PaginatedResponse.create(agents, total, pagination)


@router.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.READ_AGENTS))],
    from_opamp: bool = Query(False, description="Fetch fresh data from OpAMP server")
):
    """Get agent details by ID.
    
    Args:
        agent_id: Agent ID
        db: Database session
        current_user: Current authenticated user
        from_opamp: Whether to fetch from OpAMP server
        
    Returns:
        Agent details
        
    Raises:
        HTTPException: If agent not found
    """
    agent_service = AgentService(db)
    
    if from_opamp:
        # Try to get from OpAMP server and sync
        try:
            opamp_agent = await agent_service.get_agent_from_opamp(agent_id)
            if opamp_agent:
                # This will update the local database
                await agent_service.sync_agents_from_opamp()
        except Exception as e:
            # Log error but continue with database lookup
            pass
    
    agent = agent_service.get_agent_by_id(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )
    
    return agent


@router.get("/agents/{agent_id}/status-history")
async def get_agent_status_history(
    agent_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.READ_AGENTS))],
    limit: int = Query(50, ge=1, le=100, description="Maximum number of entries")
):
    """Get agent status history.
    
    Args:
        agent_id: Agent ID
        db: Database session
        current_user: Current authenticated user
        limit: Maximum number of entries
        
    Returns:
        Agent status history
        
    Raises:
        HTTPException: If agent not found
    """
    agent_service = AgentService(db)
    
    # Verify agent exists
    agent = agent_service.get_agent_by_id(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )
    
    history = agent_service.get_agent_status_history(agent_id, limit)
    
    return {
        "agent_id": agent_id,
        "history": [
            {
                "timestamp": snapshot.timestamp.isoformat(),
                "status": snapshot.status,
                "reason": snapshot.reason,
                "metadata": snapshot.status_metadata
            }
            for snapshot in history
        ]
    }


@router.post("/agents/sync")
async def sync_agents(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.WRITE_AGENTS))],
    env: Optional[str] = Query(None, description="Environment filter")
):
    """Manually sync agents from OpAMP server.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        env: Optional environment filter
        
    Returns:
        Sync results
    """
    agent_service = AgentService(db)
    
    try:
        synced_count = await agent_service.sync_agents_from_opamp(env_filter=env)
        return {
            "status": "success",
            "synced_agents": synced_count,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to sync agents: {str(e)}"
        )


@router.get("/agents/stats", response_model=AgentStatsResponse)
async def get_agent_statistics(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.READ_AGENTS))]
):
    """Get agent statistics.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Agent statistics
    """
    agent_service = AgentService(db)
    
    total_agents = db.query(Agent).count()
    by_status = agent_service.get_agent_counts_by_status()
    by_environment = agent_service.get_agent_counts_by_env()
    environments = agent_service.get_environment_list()
    
    return AgentStatsResponse(
        total_agents=total_agents,
        by_status=by_status,
        by_environment=by_environment,
        environments=environments
    )