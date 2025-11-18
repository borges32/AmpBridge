"""
Configuration management router.
Provides endpoints for updating agent configurations.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.opamp_service import OpAMPService
from app.repositories.agent_repository import AgentRepository
from app.schemas import ConfigUpdateRequest, ConfigUpdateResponse
from app.dependencies import get_current_active_user
from app.models.models import User

router = APIRouter(prefix="/config", tags=["Configuration"])


@router.post("", response_model=ConfigUpdateResponse)
async def update_agent_config(
    instance_id: str,
    config_data: ConfigUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update configuration for a specific agent.
    Sends the new configuration to OpAMP server and creates a new version.
    Requires authentication.
    
    - **instance_id**: Agent instance ID (query parameter)
    - **config**: YAML configuration content (in request body)
    """
    # Verify agent exists
    agent_repo = AgentRepository(db)
    agent = await agent_repo.get_by_instance_id(instance_id)
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with instance_id '{instance_id}' not found"
        )
    
    # Send config to OpAMP
    opamp_service = OpAMPService(db)
    
    try:
        result = await opamp_service.send_config_to_opamp(
            instance_id=instance_id,
            config=config_data.config,
            user_id=current_user.id
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
        return ConfigUpdateResponse(**result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
