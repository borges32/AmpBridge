"""Configuration management API endpoints."""

from typing import List, Optional, Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.v1.deps import CurrentUser, require_permission, get_db
from app.core.services.config_service import ConfigService
from app.core.services.job_service import JobService
from app.core.utils.pagination import PaginationParams, PaginatedResponse
from app.security.rbac import Permission
from app.db.models import JobType

router = APIRouter()


class ConfigRequest(BaseModel):
    """Configuration application request."""
    config_yaml: str = Field(..., description="Configuration in YAML format")
    version: Optional[str] = Field(None, description="Configuration version")


class BulkConfigRequest(BaseModel):
    """Bulk configuration request."""
    agent_ids: List[str] = Field(..., description="List of agent IDs")
    config_yaml: str = Field(..., description="Configuration in YAML format")
    version: Optional[str] = Field(None, description="Configuration version")


class ConfigResponse(BaseModel):
    """Configuration response model."""
    id: int
    agent_id: str
    version: str
    timestamp: datetime
    applied_by: str
    checksum: str

    class Config:
        from_attributes = True


@router.post("/agents/{agent_id}/config", response_model=ConfigResponse)
async def apply_config(
    agent_id: str,
    config_request: ConfigRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.WRITE_CONFIGS))]
):
    """Apply configuration to a specific agent.
    
    Args:
        agent_id: Agent ID
        config_request: Configuration data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Applied configuration details
        
    Raises:
        HTTPException: If agent not found or config application fails
    """
    config_service = ConfigService(db)
    
    try:
        config = await config_service.apply_config(
            agent_id=agent_id,
            config_yaml=config_request.config_yaml,
            applied_by=current_user.username,
            version=config_request.version
        )
        
        return config
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply configuration: {str(e)}"
        )


@router.post("/configs/bulk")
async def bulk_config_update(
    bulk_request: BulkConfigRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.WRITE_CONFIGS))]
):
    """Apply configuration to multiple agents via background job.
    
    Args:
        bulk_request: Bulk configuration request
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Job information
    """
    job_service = JobService(db)
    
    # Create bulk configuration job
    job_payload = {
        "agent_ids": bulk_request.agent_ids,
        "config_yaml": bulk_request.config_yaml,
        "version": bulk_request.version,
        "applied_by": current_user.username
    }
    
    job = job_service.create_job(
        job_type=JobType.BULK_CONFIG_UPDATE,
        payload=job_payload,
        created_by=current_user.username,
        agent_ids=bulk_request.agent_ids
    )
    
    return {
        "job_id": job.id,
        "status": job.status,
        "total_agents": len(bulk_request.agent_ids),
        "created_at": job.created_at.isoformat(),
        "message": f"Bulk configuration job created for {len(bulk_request.agent_ids)} agents"
    }


@router.get("/agents/{agent_id}/configs", response_model=PaginatedResponse[ConfigResponse])
async def get_agent_configs(
    agent_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.READ_CONFIGS))],
    page: int = 1,
    size: int = 20
):
    """Get configuration history for an agent.
    
    Args:
        agent_id: Agent ID
        db: Database session
        current_user: Current authenticated user
        page: Page number
        size: Page size
        
    Returns:
        Paginated configuration history
    """
    config_service = ConfigService(db)
    pagination = PaginationParams(page=page, size=size)
    
    configs, total = config_service.get_agent_configs(agent_id, pagination)
    
    return PaginatedResponse.create(configs, total, pagination)


@router.get("/configs/{config_id}", response_model=ConfigResponse)
async def get_config(
    config_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.READ_CONFIGS))]
):
    """Get configuration by ID.
    
    Args:
        config_id: Configuration ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Configuration details
        
    Raises:
        HTTPException: If configuration not found
    """
    config_service = ConfigService(db)
    config = config_service.get_config_by_id(config_id)
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration {config_id} not found"
        )
    
    return config


@router.get("/configs/{config_id}/compare/{other_id}")
async def compare_configs(
    config_id: int,
    other_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.READ_CONFIGS))]
):
    """Compare two configurations.
    
    Args:
        config_id: First configuration ID
        other_id: Second configuration ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Configuration comparison
        
    Raises:
        HTTPException: If configurations not found
    """
    config_service = ConfigService(db)
    
    try:
        comparison = config_service.compare_configs(config_id, other_id)
        return comparison
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/configs/stats")
async def get_config_statistics(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.READ_CONFIGS))]
):
    """Get configuration statistics.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Configuration statistics
    """
    config_service = ConfigService(db)
    return config_service.get_config_statistics()