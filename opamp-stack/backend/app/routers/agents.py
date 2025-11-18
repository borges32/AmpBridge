"""
Agents router.
Provides endpoints for agent management and querying.
"""
import csv
import io
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.agent_repository import AgentRepository
from app.repositories.agent_health_repository import AgentHealthRepository
from app.repositories.agent_config_repository import AgentConfigRepository
from app.schemas import AgentResponse, AgentListResponse, AgentHealthResponse, AgentConfigResponse
from app.dependencies import get_current_active_user
from app.models.models import User

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get("", response_model=AgentListResponse)
async def list_agents(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    db: AsyncSession = Depends(get_db)
):
    """
    List all agents with pagination.
    
    - **page**: Page number (starts at 1)
    - **page_size**: Number of items per page (max 500)
    """
    agent_repo = AgentRepository(db)
    
    skip = (page - 1) * page_size
    agents = await agent_repo.get_all(skip=skip, limit=page_size)
    total = await agent_repo.count()
    
    return AgentListResponse(
        total=total,
        page=page,
        page_size=page_size,
        agents=agents
    )


@router.get("/csv")
async def export_agents_csv(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Export all agents to CSV file.
    Requires authentication.
    """
    agent_repo = AgentRepository(db)
    agents = await agent_repo.get_all(skip=0, limit=10000)
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "Instance ID",
        "Host Name",
        "OS Type",
        "OS Description",
        "Healthy",
        "Status Sync",
        "Alert Config",
        "Connected",
        "Started At",
        "Last Seen At",
        "Created At",
        "Updated At"
    ])
    
    # Write data
    for agent in agents:
        writer.writerow([
            agent.instance_id,
            agent.host_name or "",
            agent.os_type or "",
            agent.os_description or "",
            agent.healthy,
            agent.status_sync,
            agent.alert_config,
            agent.is_connected,
            agent.started_at.isoformat() if agent.started_at else "",
            agent.last_seen_at.isoformat() if agent.last_seen_at else "",
            agent.created_at.isoformat(),
            agent.updated_at.isoformat()
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=agents_export.csv"
        }
    )


@router.get("/{instance_id}", response_model=AgentResponse)
async def get_agent(
    instance_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific agent.
    
    - **instance_id**: Agent instance ID
    """
    agent_repo = AgentRepository(db)
    agent = await agent_repo.get_by_instance_id(instance_id)
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with instance_id '{instance_id}' not found"
        )
    
    return agent


@router.get("/{instance_id}/health", response_model=list[AgentHealthResponse])
async def get_agent_health_history(
    instance_id: str,
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get health history for a specific agent.
    
    - **instance_id**: Agent instance ID
    - **limit**: Number of health records to return (max 1000)
    """
    # Verify agent exists
    agent_repo = AgentRepository(db)
    agent = await agent_repo.get_by_instance_id(instance_id)
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with instance_id '{instance_id}' not found"
        )
    
    health_repo = AgentHealthRepository(db)
    health_records = await health_repo.get_history_by_instance_id(instance_id, limit=limit)
    
    return health_records


@router.get("/{instance_id}/configs", response_model=list[AgentConfigResponse])
async def get_agent_config_history(
    instance_id: str,
    limit: int = Query(100, ge=1, le=1000, description="Number of versions to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get configuration version history for a specific agent.
    
    - **instance_id**: Agent instance ID
    - **limit**: Number of config versions to return (max 1000)
    """
    # Verify agent exists
    agent_repo = AgentRepository(db)
    agent = await agent_repo.get_by_instance_id(instance_id)
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with instance_id '{instance_id}' not found"
        )
    
    config_repo = AgentConfigRepository(db)
    configs = await config_repo.get_history_by_instance_id(instance_id, limit=limit)
    
    return configs


@router.get("/{instance_id}/config", response_class=StreamingResponse)
async def download_agent_config(
    instance_id: str,
    version: Optional[int] = Query(None, description="Specific version number, defaults to latest"),
    db: AsyncSession = Depends(get_db)
):
    """
    Download the effective configuration file (YAML) for an agent.
    
    - **instance_id**: Agent instance ID
    - **version**: Specific version number (optional, defaults to latest)
    """
    # Verify agent exists
    agent_repo = AgentRepository(db)
    agent = await agent_repo.get_by_instance_id(instance_id)
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with instance_id '{instance_id}' not found"
        )
    
    config_repo = AgentConfigRepository(db)
    
    if version is not None:
        config = await config_repo.get_by_version(instance_id, version)
    else:
        config = await config_repo.get_latest_by_instance_id(instance_id)
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )
    
    # Create file stream
    config_stream = io.StringIO(config.effective_config)
    
    filename = f"agent_{instance_id}_config_v{config.version}.yaml"
    
    return StreamingResponse(
        iter([config_stream.getvalue()]),
        media_type="application/x-yaml",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
