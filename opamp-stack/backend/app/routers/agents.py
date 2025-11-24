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
from app.repositories.agent_pipeline_health_repository import AgentPipelineHealthRepository
from app.schemas import (
    AgentResponse, 
    AgentListResponse, 
    AgentHealthResponse, 
    AgentConfigResponse,
    AgentStatsResponse,
    AgentPipelineHealthResponse
)
from app.dependencies import get_current_active_user
from app.models.models import User

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get("", response_model=AgentListResponse)
async def list_agents(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    os_type: Optional[str] = Query(None, description="Filter by OS type"),
    connected: Optional[bool] = Query(None, description="Filter by connection status"),
    healthy: Optional[bool] = Query(None, description="Filter by health status"),
    search: Optional[str] = Query(None, description="Search by hostname, instance ID, or service name"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all agents with pagination and filters.
    Requires authentication.
    
    - **page**: Page number (starts at 1)
    - **page_size**: Number of items per page (max 500)
    - **os_type**: Filter by operating system type
    - **connected**: Filter by connection status (true/false)
    - **healthy**: Filter by health status (true/false)
    - **search**: Search in hostname, instance ID, or service name
    """
    agent_repo = AgentRepository(db)
    
    skip = (page - 1) * page_size
    agents = await agent_repo.get_all_filtered(
        skip=skip, 
        limit=page_size,
        os_type=os_type,
        connected=connected,
        healthy=healthy,
        search=search
    )
    total = await agent_repo.count_filtered(
        os_type=os_type,
        connected=connected,
        healthy=healthy,
        search=search
    )
    
    return AgentListResponse(
        total=total,
        page=page,
        page_size=page_size,
        agents=agents
    )


@router.get("/stats", response_model=AgentStatsResponse)
async def get_agent_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get agent statistics including counts and distributions.
    Requires authentication.
    """
    agent_repo = AgentRepository(db)
    stats = await agent_repo.get_statistics()
    return AgentStatsResponse(**stats)


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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get detailed information about a specific agent.
    Requires authentication.
    
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get health history for a specific agent.
    Requires authentication.
    
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get configuration version history for a specific agent.
    Requires authentication.
    
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Download the effective configuration file (YAML) for an agent.
    Requires authentication.
    
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


@router.get("/{instance_id}/pipelines/health", response_model=list[AgentPipelineHealthResponse])
async def get_agent_pipeline_health_history(
    instance_id: str,
    component_name: Optional[str] = Query(None, description="Filter by specific component name"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get pipeline/component health for a specific agent.
    Requires authentication.
    
    - **instance_id**: Agent instance ID
    - **component_name**: Optional filter for a specific component
    """
    # Verify agent exists
    agent_repo = AgentRepository(db)
    agent = await agent_repo.get_by_instance_id(instance_id)
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with instance_id '{instance_id}' not found"
        )
    
    pipeline_health_repo = AgentPipelineHealthRepository(db)
    
    if component_name:
        # Get history for specific component
        pipeline_records = await pipeline_health_repo.get_history_by_component(
            instance_id, 
            component_name,
            limit=100
        )
    else:
        # Get all components
        pipeline_records = await pipeline_health_repo.get_history_by_instance_id(
            instance_id, 
            limit=1000
        )
    
    return pipeline_records


@router.post("/{instance_id}/config/restore")
async def restore_config_version(
    instance_id: str,
    version: int = Query(..., description="Version number to restore"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Restore a previous configuration version for an agent.
    This creates a new version with the content from the specified version
    and sends it to the OpAMP server.
    Requires authentication.
    
    - **instance_id**: Agent instance ID
    - **version**: Version number to restore
    """
    # Verify agent exists
    agent_repo = AgentRepository(db)
    agent = await agent_repo.get_by_instance_id(instance_id)
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with instance_id '{instance_id}' not found"
        )
    
    # Get the config version to restore
    config_repo = AgentConfigRepository(db)
    config_to_restore = await config_repo.get_by_version(instance_id, version)
    
    if not config_to_restore:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration version {version} not found for agent {instance_id}"
        )
    
    # Send config to OpAMP (this will create a new version with source="RESTORE")
    from app.services.opamp_service import OpAMPService
    opamp_service = OpAMPService(db)
    
    try:
        result = await opamp_service.send_config_to_opamp(
            instance_id=instance_id,
            config=config_to_restore.effective_config,
            user_id=current_user.id
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
        # Update the source of the newly created config to "RESTORE"
        new_version = result["version"]
        new_config = await config_repo.get_by_version(instance_id, new_version)
        if new_config:
            new_config.source = "RESTORE"
            await db.commit()
        
        return {
            "success": True,
            "message": f"Configuration version {version} restored successfully as version {new_version}",
            "restored_from_version": version,
            "new_version": new_version,
            "instance_id": instance_id
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{instance_id}", status_code=status.HTTP_200_OK)
async def delete_agent(
    instance_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete an agent and all its associated history.
    Requires authentication.
    
    This endpoint permanently removes:
    - Agent basic information
    - All health history records
    - All configuration versions
    - All pipeline/component health records
    
    **Warning:** This action cannot be undone!
    
    - **instance_id**: Agent instance ID to delete
    """
    agent_repo = AgentRepository(db)
    
    deleted = await agent_repo.delete_with_history(instance_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with instance_id '{instance_id}' not found"
        )
    
    return {
        "success": True,
        "message": f"Agent '{instance_id}' and all its history have been permanently deleted",
        "instance_id": instance_id
    }
