"""
OpAMP synchronization router.
Provides endpoints for manual synchronization with OpAMP server.
"""
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.opamp_service import OpAMPService
from app.schemas import SyncResponse, SingleAgentSyncResponse
from app.dependencies import get_current_active_user
from app.models.models import User

router = APIRouter(prefix="/opamp", tags=["OpAMP Sync"])


@router.post("/sync", response_model=SyncResponse)
async def manual_sync(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Manually trigger synchronization with OpAMP server.
    Fetches all agents from OpAMP and updates the database.
    Requires authentication.
    
    This endpoint:
    - Fetches all agents from OpAMP /agents/full
    - Updates agent information
    - Creates health records
    - Versions configurations when changes are detected
    - Marks disconnected agents
    """
    opamp_service = OpAMPService(db)
    result = await opamp_service.sync_all_agents()
    
    return result


@router.post("/sync/{instance_id}", response_model=SingleAgentSyncResponse)
async def sync_single_agent(
    instance_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Manually trigger synchronization for a specific agent.
    Fetches the agent from OpAMP server and updates the database.
    Requires authentication.
    
    This endpoint:
    - Fetches the specific agent from OpAMP /agents/full
    - Updates agent information
    - Creates health record
    - Versions configuration if it changed
    - Returns detailed sync results
    
    Args:
        instance_id: The instance ID of the agent to synchronize
        
    Returns:
        SingleAgentSyncResponse with sync results
        
    Raises:
        HTTPException 404: If agent not found in OpAMP server
    """
    opamp_service = OpAMPService(db)
    result = await opamp_service.sync_single_agent(instance_id)
    
    if not result["success"] and "not found" in result["message"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["message"]
        )
    
    return result
